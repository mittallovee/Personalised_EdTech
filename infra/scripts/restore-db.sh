#!/usr/bin/env bash
# Restores a backup made by backup-db.sh into a NEW database (K-03, docs/operations/backup-and-restore.md).
#
#   PGHOST=... PGUSER=... PGPASSWORD=... infra/scripts/restore-db.sh backup.dump qbank_restored
#
# Never overwrites: it stops if the database already exists, so a restore can never destroy data.
# To replace a database, restore beside it, check the copy, then switch over (the document says how).
# The roles qbank_app and qbank_worker must already exist (infra/db/ensure-app-role.sh creates them).
# Set PG_DOCKER_IMAGE (e.g. postgres:17) to use a matching client from Docker.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=pg-tools.sh
. "$here/pg-tools.sh"

dump="${1:?usage: restore-db.sh DUMPFILE NEW_DATABASE}"
target="${2:?usage: restore-db.sh DUMPFILE NEW_DATABASE}"
[ -f "$dump" ] || { echo "No such file: $dump" >&2; exit 1; }

if [ -f "$dump.sha256" ]; then
  (cd "$(dirname "$dump")" && sha256sum --check --quiet "$(basename "$dump").sha256") \
    || { echo "The backup does not match its checksum; it is damaged or was changed." >&2; exit 1; }
else
  echo "Warning: no $dump.sha256 next to the backup, so it cannot be checked for damage." >&2
fi

export PGDATABASE=postgres

# What the backup says about the database itself and about permissions. --create makes pg_restore print
# the database's own properties too; with --schema-only no data is read.
header="$(pg_tool pg_restore --create --schema-only --no-owner -f - < "$dump")"

# The backup keeps who may do what (GRANT lines, and default privileges set FOR a role), so every role it
# names must exist on this server, or the restore would stop part-way.
roles="$({
  # who is granted or revoked: ... GRANT ... TO role;   REVOKE ... FROM role;
  printf '%s\n' "$header" | sed -n -E \
    's/^(ALTER DEFAULT PRIVILEGES.* )?(GRANT|REVOKE) .* (TO|FROM) ("[^"]+"|[A-Za-z0-9_$]+)( WITH GRANT OPTION)?;$/\4/p'
  # whose future objects get privileges: ALTER DEFAULT PRIVILEGES FOR ROLE role ...
  printf '%s\n' "$header" | sed -n -E \
    's/^ALTER DEFAULT PRIVILEGES FOR ROLE ("[^"]+"|[A-Za-z0-9_$]+) .*/\1/p'
} | tr -d '"' | sort -u | grep -vx 'PUBLIC' || true)"
if [ -n "$roles" ]; then
  missing="$(printf '%s\n' "$roles" \
    | pg_tool psql -X -At -c "CREATE TEMP TABLE wanted (r text)" -c "COPY wanted FROM STDIN" \
        -c "SELECT r FROM wanted WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) ORDER BY r" \
    | grep -v -e '^CREATE TABLE$' -e '^COPY ' || true)"
  if [ -n "$missing" ]; then
    echo "The backup grants privileges to roles that do not exist on this server:" >&2
    printf '  %s\n' $missing >&2
    echo "Create them first (infra/db/ensure-app-role.sh does qbank_app and qbank_worker), then restore again." >&2
    exit 1
  fi
  # qbank_worker reaches the application tables only as a member of qbank_app (ensure-app-role.sh), and
  # a backup cannot carry that: without it the restore succeeds and the worker then fails at run time.
  if printf '%s\n' "$roles" | grep -qx 'qbank_worker'; then
    not_member="$(echo "SELECT 1 WHERE NOT pg_has_role('qbank_worker', 'qbank_app', 'MEMBER')" \
      | pg_tool psql -X -At)"
    if [ -n "$not_member" ]; then
      echo "On this server qbank_worker is not a member of qbank_app, so the restored worker could not" >&2
      echo "read the application tables. Run infra/db/ensure-app-role.sh (or GRANT qbank_app TO qbank_worker), then restore again." >&2
      exit 1
    fi
  fi
fi

exists="$(echo "SELECT 1 FROM pg_database WHERE datname = :'target'" | pg_tool psql -X -At -v "target=$target")"
if [ -n "$exists" ]; then
  echo "Database $target already exists; restore into a new name." >&2
  exit 1
fi

# The new database gets the old one's encoding and locale (a server with other defaults would behave
# differently: sorting, case rules), and afterwards its per-database settings and connect permissions.
# The backup names the old database in these statements; the new name replaces it.
new_name="$(echo "SELECT quote_ident(:'target')" | pg_tool psql -X -At -v "target=$target")"
create_line="$(printf '%s\n' "$header" | grep -m1 -E '^CREATE DATABASE ' || true)"
old_name="$(printf '%s\n' "$create_line" | sed -n -E 's/^CREATE DATABASE ("([^"]|"")+"|[A-Za-z0-9_$]+) .*/\1/p')"
create_options="$(printf '%s\n' "$create_line" | sed -n -E 's/^CREATE DATABASE ("([^"]|"")+"|[A-Za-z0-9_$]+) (.*)/\3/p')"
properties=""
if [ -n "$create_options" ]; then
  create_sql="CREATE DATABASE $new_name $create_options"
  while IFS= read -r line; do
    properties+="${line/" DATABASE $old_name "/" DATABASE $new_name "}"$'\n'
  done < <(printf '%s\n' "$header" | grep -E "^(ALTER DATABASE|GRANT .* ON DATABASE|REVOKE .* ON DATABASE) " || true)
else
  # Not seen with pg_restore 16 or later, which always names one; kept for any other client.
  echo "Warning: this backup has no database properties (made without --create); using this server's defaults." >&2
  create_sql="CREATE DATABASE $new_name;"
fi
printf '%s\n' "$create_sql" | pg_tool psql -X -v ON_ERROR_STOP=1 > /dev/null
# Stop at the first error, and leave the half-restored database in place to look at.
pg_tool pg_restore --exit-on-error --no-owner --dbname "$target" < "$dump"
if [ -n "$properties" ]; then
  printf '%s' "$properties" | pg_tool psql -X -v ON_ERROR_STOP=1 > /dev/null
fi
echo "Restored $dump into database $target"

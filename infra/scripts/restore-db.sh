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

# The backup keeps who may do what (GRANT lines), so every role it names must exist on this server, or the
# restore would stop part-way. Look at the permissions only (--schema-only: no data is read for this).
roles="$(pg_tool pg_restore --schema-only --no-owner -f - < "$dump" \
  | sed -n -E 's/^(ALTER DEFAULT PRIVILEGES.* )?(GRANT|REVOKE) .* (TO|FROM) ("[^"]+"|[A-Za-z0-9_$]+)( WITH GRANT OPTION)?;$/\4/p' \
  | tr -d '"' | sort -u | grep -vx 'PUBLIC' || true)"
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
fi

exists="$(echo "SELECT 1 FROM pg_database WHERE datname = :'target'" | pg_tool psql -X -At -v "target=$target")"
if [ -n "$exists" ]; then
  echo "Database $target already exists; restore into a new name." >&2
  exit 1
fi
echo 'CREATE DATABASE :"target"' | pg_tool psql -X -v ON_ERROR_STOP=1 -v "target=$target" > /dev/null
# Stop at the first error, and leave the half-restored database in place to look at.
pg_tool pg_restore --exit-on-error --no-owner --dbname "$target" < "$dump"
echo "Restored $dump into database $target"

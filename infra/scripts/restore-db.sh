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
exists="$(echo "SELECT 1 FROM pg_database WHERE datname = :'target'" | pg_tool psql -X -At -v "target=$target")"
if [ -n "$exists" ]; then
  echo "Database $target already exists; restore into a new name." >&2
  exit 1
fi
echo 'CREATE DATABASE :"target"' | pg_tool psql -X -v ON_ERROR_STOP=1 -v "target=$target" > /dev/null
# Stop at the first error, and leave the half-restored database in place to look at.
pg_tool pg_restore --exit-on-error --no-owner --dbname "$target" < "$dump"
echo "Restored $dump into database $target"

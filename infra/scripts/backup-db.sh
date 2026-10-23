#!/usr/bin/env bash
# Logical backup of one PostgreSQL database into one file (K-03, docs/operations/backup-and-restore.md).
#
#   PGHOST=... PGUSER=... PGPASSWORD=... PGDATABASE=qbank_dev infra/scripts/backup-db.sh backup.dump
#
# Writes OUTFILE (PostgreSQL "custom" format, mode 600) and OUTFILE.sha256. Needs the standard PG*
# variables; set PG_DOCKER_IMAGE (e.g. postgres:17) to use a matching client from Docker.
#
# The connecting role must be a superuser or have BYPASSRLS. Every tenant table has forced row-level
# security, so any other role would get a dump with some rows missing, or none; this script refuses
# to start rather than write a backup that looks complete and is not.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=pg-tools.sh
. "$here/pg-tools.sh"

out="${1:?usage: backup-db.sh OUTFILE}"
: "${PGDATABASE:?Set PGDATABASE to the database to back up}"

can_see_everything="$(echo "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user" \
  | pg_tool psql -X -At)"
if [ "$can_see_everything" != "t" ]; then
  echo "Refusing to back up: this role cannot bypass row-level security, so the dump would be" >&2
  echo "incomplete. Use a superuser or a role with BYPASSRLS (see docs/operations/backup-and-restore.md)." >&2
  exit 1
fi

umask 077
partial="$out.partial"
trap 'rm -f "$partial"' EXIT
# --no-owner: the restoring role owns what it restores (a different cluster may name it differently).
# Grants to qbank_app and qbank_worker are kept; those roles must exist before a restore.
pg_tool pg_dump --format=custom --no-owner > "$partial"
pg_tool pg_restore --list < "$partial" > /dev/null   # the file must at least be readable as a backup
mv "$partial" "$out"
trap - EXIT
(cd "$(dirname "$out")" && sha256sum "$(basename "$out")" > "$(basename "$out").sha256")
echo "Backup written: $out ($(wc -c < "$out") bytes)"

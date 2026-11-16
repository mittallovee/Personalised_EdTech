#!/usr/bin/env bash
# Daily off-machine backup (K-16, ADR-0021, docs/operations/offsite-backups.md).
#
#   infra/scripts/backup-offsite.sh --init   once: create the encrypted backup store in the bucket
#   infra/scripts/backup-offsite.sh          every day: dump the database, add the pictures, upload,
#                                            drop copies past the retention, check the store
#
# What goes up is ONE restic snapshot holding the database dump (made by backup-db.sh, so the same
# row-level-security safety check applies) and the `assetdata` Docker volume (the uploaded pictures).
# restic encrypts everything on this PC before it leaves, so the bucket only ever holds ciphertext.
#
# Settings come from .env (the POSTGRES_* values) and from .env.offsite (the bucket, its keys and the
# restic password: see infra/backup/offsite.env.example). Neither is ever committed.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
# shellcheck source=pg-tools.sh
. "$here/pg-tools.sh"
# shellcheck source=restic-tools.sh
. "$here/restic-tools.sh"

mkdir -p "$root/backups"
exec > >(tee -a "${OFFSITE_LOG:-$root/backups/offsite-backup.log}") 2>&1

config="${OFFSITE_ENV:-$root/.env.offsite}"
[ -f "$config" ] || { echo "No $config. See docs/operations/offsite-backups.md." >&2; exit 1; }
set -a
# shellcheck source=/dev/null
[ -f "$root/.env" ] && . "$root/.env"
# shellcheck source=/dev/null
. "$config"
set +a
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-auto}"   # Cloudflare R2 has one region, "auto"
require_offsite_settings

if [ "${1:-}" = "--init" ]; then
  restic_tool init
  echo "Backup store created. Keep RESTIC_PASSWORD in your password manager: without it nothing can be restored."
  exit 0
fi
[ $# -eq 0 ] || { echo "usage: backup-offsite.sh [--init]" >&2; exit 2; }

# The monitoring address (healthchecks.io or similar) hears about every start, success and failure, and
# emails the owner when a day passes without a success. It is a secret-ish URL: never printed.
ping_monitor() {
  [ -n "${HEALTHCHECK_URL:-}" ] || return 0
  curl -fsS -m 15 --retry 3 -o /dev/null "${HEALTHCHECK_URL%/}$1" 2> /dev/null \
    || echo "(could not reach the monitoring address)" >&2
}

stage="$root/backups/offsite-stage"
finish() {
  local code=$?
  rm -rf "$stage"   # the plain dump must not stay on disk
  if [ "$code" -ne 0 ]; then
    echo "$(date -u +%FT%TZ) offsite backup FAILED (exit $code)" >&2
    ping_monitor /fail
  fi
}
trap finish EXIT
echo "$(date -u +%FT%TZ) offsite backup started"
ping_monitor /start

# Which Docker volume holds the pictures. Docker would silently create an empty volume for a wrong name
# and the backup would "succeed" with no pictures, so the volume must already exist.
volume="${ASSET_VOLUME:-}"
if [ -z "$volume" ]; then
  matches="$(docker volume ls -q | tr -d '\r' | grep -E '(^|_)assetdata$' || true)"
  if [ "$(printf '%s' "$matches" | grep -c . || true)" != 1 ]; then
    echo "Cannot tell which Docker volume holds the pictures. Set ASSET_VOLUME in $config." >&2
    exit 1
  fi
  volume="$matches"
fi
docker volume inspect "$volume" > /dev/null || { echo "No Docker volume named $volume." >&2; exit 1; }

restic_tool cat config > /dev/null \
  || { echo "Cannot open the backup store: wrong address, keys or password, or run --init once." >&2; exit 1; }

rm -rf "$stage"
mkdir -p "$stage"
export PGHOST="${PGHOST:-localhost}" PG_DOCKER_IMAGE="${PG_DOCKER_IMAGE:-postgres:17}"
export PGUSER="${PGUSER:-${POSTGRES_USER:-}}" PGPASSWORD="${PGPASSWORD:-${POSTGRES_PASSWORD:-}}"
export PGDATABASE="${PGDATABASE:-${POSTGRES_DB:-}}"
"$here/backup-db.sh" "$stage/qbank.dump"

# Fixed names inside the container (/stage, /assets) and a fixed --host keep the snapshots comparable,
# so "keep 14 daily" means the same thing every day wherever the PC's folders are.
restic_mounts=(-v "$(host_path "$stage"):/stage:ro" -v "$volume:/assets:ro")
restic_tool backup --host qbank --tag k16 /stage /assets
listing="$(restic_tool ls latest --host qbank /stage)"
printf '%s\n' "$listing" | grep -q '/stage/qbank.dump$' \
  || { echo "The new snapshot has no database dump in it." >&2; exit 1; }
restic_tool forget --host qbank --keep-daily 14 --keep-weekly 8 --keep-monthly 6 --prune
restic_tool check --read-data-subset=2%   # structure, plus a different 2% of the stored data read back

echo "$(date -u +%FT%TZ) offsite backup finished"
ping_monitor ""

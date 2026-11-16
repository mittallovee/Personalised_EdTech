#!/usr/bin/env bash
# Brings a backup made by backup-offsite.sh back from the bucket (K-16, docs/operations/offsite-backups.md).
#
#   infra/scripts/restore-offsite.sh list                    which snapshots exist
#   infra/scripts/restore-offsite.sh latest  /some/new/folder
#   infra/scripts/restore-offsite.sh 1a2b3c4d /some/new/folder   (an id from "list")
#
# It only ever writes into a NEW (or empty) folder, never over the live database or the live pictures. It
# reads every file back and checks it, then checks the database dump against its checksum. Putting the
# data into use is a separate, deliberate step (printed at the end; the document explains it).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
# shellcheck source=restic-tools.sh
. "$here/restic-tools.sh"

config="${OFFSITE_ENV:-$root/.env.offsite}"
[ -f "$config" ] || { echo "No $config. See docs/operations/offsite-backups.md." >&2; exit 1; }
set -a
# shellcheck source=/dev/null
. "$config"
set +a
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-auto}"
require_offsite_settings

what="${1:?usage: restore-offsite.sh list | restore-offsite.sh (latest|SNAPSHOT_ID) NEW_FOLDER}"
if [ "$what" = list ]; then
  restic_tool snapshots --host qbank
  exit 0
fi
target="${2:?usage: restore-offsite.sh (latest|SNAPSHOT_ID) NEW_FOLDER}"
if [ -e "$target" ] && [ -n "$(ls -A "$target")" ]; then
  echo "$target is not empty. Restore into a new folder so nothing is overwritten." >&2
  exit 1
fi
mkdir -p "$target"
target="$(cd "$target" && pwd)"

restic_mounts=(-v "$(host_path "$target"):/restore")
restic_tool restore "$what" --host qbank --target /restore --verify

(cd "$target/stage" && sha256sum --check --quiet qbank.dump.sha256) \
  || { echo "The restored database dump does not match its checksum." >&2; exit 1; }

cat << EOF

Restored into $target
  database dump  $target/stage/qbank.dump  (checksum matches)
  pictures       $target/assets/

To use them (nothing has been touched yet):
  1. Database, into a NEW database beside the old one (see docs/operations/backup-and-restore.md):
       infra/scripts/restore-db.sh "$target/stage/qbank.dump" qbank_restored
  2. Pictures, into a NEW Docker volume:
       docker volume create assetdata_restored
       docker run --rm -v assetdata_restored:/to -v "$(host_path "$target")/assets:/from:ro" alpine cp -a /from/. /to/
EOF

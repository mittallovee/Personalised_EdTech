#!/usr/bin/env bash
# The off-machine backup drill (K-16, docs/operations/offsite-backups.md): the whole chain, with a
# throwaway PostgreSQL, throwaway pictures volume and a local S3 server standing in for Cloudflare R2.
#
#   infra/scripts/offsite-drill.sh
#
# It runs the real scripts (backup-offsite.sh, restore-offsite.sh, restore-db.sh) and checks that what
# comes back is the same as what went in. Needs Docker; touches nothing of yours (it uses its own
# containers, network and volumes, all removed at the end, and its own log and stage files).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
# shellcheck source=restic-tools.sh
. "$here/restic-tools.sh"

run="drill$$"
net="qbank-$run"
vol="qbank-$run-assets"
work="$(mktemp -d)"
restored="$root/backups/$run-restored"
fail() { echo "DRILL FAILED: $*" >&2; exit 1; }
cleanup() {
  docker rm -f "$run-s3" "$run-pg" > /dev/null 2>&1 || true
  docker volume rm "$vol" > /dev/null 2>&1 || true
  docker network rm "$net" > /dev/null 2>&1 || true
  rm -rf "$work"
  # The restore ran as root inside a container, so on Linux the files are root's: remove them the same way.
  rm -rf "$restored" 2> /dev/null \
    || MSYS_NO_PATHCONV=1 docker run --rm -v "$(host_path "$root/backups"):/b" alpine rm -rf "/b/$run-restored" \
    || true
}
trap cleanup EXIT

docker network create "$net" > /dev/null
docker run -d --name "$run-s3" --network "$net" -e initialBuckets=drill adobe/s3mock@sha256:ab01a6946750f451ca215a47e91030695b260e4003b8a5a6201d25029b8fca92 > /dev/null
docker run -d --name "$run-pg" --network "$net" -e POSTGRES_USER=qbank_owner -e POSTGRES_PASSWORD=drillpw \
  -e POSTGRES_DB=qbank_dev postgres:17 > /dev/null
for _ in $(seq 1 60); do
  docker exec "$run-pg" pg_isready -U qbank_owner -d qbank_dev > /dev/null 2>&1 && break
  sleep 1
done
for _ in $(seq 1 60); do
  docker run --rm --network "$net" alpine wget -q -O /dev/null "http://$run-s3:9090/drill/" 2> /dev/null \
    && break
  sleep 1
done

psql_owner() { docker exec -i "$run-pg" psql -X -q -v ON_ERROR_STOP=1 -U qbank_owner "$@"; }
psql_owner -d postgres << 'SQL'
CREATE ROLE qbank_app NOLOGIN;
CREATE ROLE qbank_worker NOLOGIN;
GRANT qbank_app TO qbank_worker;
SQL
psql_owner -d qbank_dev << 'SQL'
CREATE TABLE notes (id int PRIMARY KEY, body text NOT NULL);
INSERT INTO notes SELECT n, 'row ' || n FROM generate_series(1, 250) AS n;
GRANT SELECT ON notes TO qbank_app;
SQL
docker volume create "$vol" > /dev/null
docker run --rm -v "$vol:/a" alpine sh -c \
  'mkdir -p /a/sub && echo one > /a/one.png && head -c 300000 /dev/urandom > /a/sub/two.png'

cat > "$work/offsite.env" << EOF
RESTIC_REPOSITORY=s3:http://$run-s3:9090/drill
RESTIC_PASSWORD=drill-password-$run
AWS_ACCESS_KEY_ID=drill
AWS_SECRET_ACCESS_KEY=drill
ASSET_VOLUME=$vol
PGHOST=$run-pg
PGUSER=qbank_owner
PGPASSWORD=drillpw
PGDATABASE=qbank_dev
EOF
export OFFSITE_ENV="$work/offsite.env" OFFSITE_LOG="$work/backup.log"
export RESTIC_NETWORK="$net" PG_DOCKER_NETWORK="$net"

# Another backup (a scheduled one, say) may be running while this one starts or fails. Its staging folder
# must survive: this stands in for it, at the path an older version of the script shared between runs.
mkdir -p "$root/backups/offsite-stage"
echo "someone else's dump" > "$root/backups/offsite-stage/qbank.dump"

echo "--- 1. a backup before the store exists is refused (and says what to do)"
"$here/backup-offsite.sh" > /dev/null 2>&1 && fail "backup ran without a store"
grep -q -- '--init' "$work/backup.log" || fail "the refusal did not mention --init"

echo "--- 2. create the store, back up twice"
"$here/backup-offsite.sh" --init > /dev/null
"$here/backup-offsite.sh" > /dev/null
psql_owner -d qbank_dev -c "INSERT INTO notes VALUES (251, 'added between backups')"
"$here/backup-offsite.sh" > /dev/null
[ -f "$root/backups/offsite-stage/qbank.dump" ] || fail "a failing or finished run deleted another run's staging folder"
rm -rf "$root/backups/offsite-stage"
[ -z "$(ls -d "$root"/backups/offsite-stage.* 2> /dev/null)" ] || fail "the plain dump was left on disk"

echo "--- 3. a wrong password cannot read the store"
(
  set -a
  # shellcheck source=/dev/null
  . "$work/offsite.env"
  set +a
  RESTIC_PASSWORD=wrong restic_tool snapshots > /dev/null 2>&1 && fail "wrong password was accepted"
  true
)

echo "--- 4. a wrong volume name is refused and no empty volume is created"
(
  export OFFSITE_ENV="$work/bad.env"
  sed "s/^ASSET_VOLUME=.*/ASSET_VOLUME=$run-no-such-volume/" "$work/offsite.env" > "$OFFSITE_ENV"
  "$here/backup-offsite.sh" > /dev/null 2>&1 && fail "backup ran with a missing volume"
  docker volume inspect "$run-no-such-volume" > /dev/null 2>&1 && fail "an empty volume was created"
  true
)

echo "--- 5. restore the latest snapshot into a new folder, and refuse a folder that is not empty"
"$here/restore-offsite.sh" latest "$restored" > /dev/null
"$here/restore-offsite.sh" latest "$restored" > /dev/null 2>&1 && fail "restored into a non-empty folder"

echo "--- 6. the restored pictures are the same as the originals"
# One "hash  path" line per file. (Git Bash's sha256sum marks binary files with "*"; the container's does not.)
sums() { (cd "$1" && find . -type f | sort | xargs sha256sum | sed -E 's/^([0-9a-f]+) [ *]/\1  /'); }
original="$(docker run --rm -v "$vol:/a:ro" alpine sh -c 'cd /a && find . -type f | sort | xargs sha256sum')"
[ -n "$original" ] || fail "the test pictures were not created"
[ -d "$restored/assets" ] || fail "the restored backup has no pictures folder"
again="$(sums "$restored/assets")"
[ "$original" = "$again" ] \
  || fail "restored pictures differ from the originals:
$(diff <(printf '%s\n' "$original") <(printf '%s\n' "$again") || true)"

echo "--- 7. the restored database is the same as the original"
export PGHOST="$run-pg" PGUSER=qbank_owner PGPASSWORD=drillpw PG_DOCKER_IMAGE=postgres:17
"$here/restore-db.sh" "$restored/stage/qbank.dump" qbank_restored > /dev/null
rows="$(psql_owner -d qbank_restored -At -c 'SELECT count(*) FROM notes')"
[ "$rows" = 251 ] || fail "restored database has $rows rows, expected 251"

echo "OFF-SITE BACKUP DRILL PASSED"

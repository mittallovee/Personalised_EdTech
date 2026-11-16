# Sourced by backup-offsite.sh, restore-offsite.sh and offsite-drill.sh (K-16, ADR-0021).
# Runs restic from a pinned Docker image, so nothing has to be installed on the PC. The caller sets
# RESTIC_REPOSITORY, RESTIC_PASSWORD, AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY (Cloudflare R2 uses the
# AWS names), and may add folders to look at by filling the array restic_mounts, for example
# restic_mounts=(-v "/some/folder:/stage:ro").
RESTIC_IMAGE="${RESTIC_IMAGE:-restic/restic:0.18.1}"
restic_mounts=()

# Windows (Git Bash): Docker wants C:/... paths, not /c/... ones. Elsewhere the path is unchanged.
host_path() {
  if command -v cygpath > /dev/null 2>&1; then cygpath -m "$1"; else printf '%s\n' "$1"; fi
}

# Stops with a clear message if a setting the backup cannot work without is missing.
require_offsite_settings() {
  local name
  for name in RESTIC_REPOSITORY RESTIC_PASSWORD AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY; do
    if [ -z "${!name:-}" ]; then
      echo "Missing $name. Copy infra/backup/offsite.env.example to .env.offsite and fill it in" >&2
      echo "(docs/operations/offsite-backups.md)." >&2
      return 1
    fi
  done
}

# restic_tool ARGS...  runs "restic ARGS..." in the container.
#   --no-cache: the container is thrown away each time, so a cache would only be written and lost.
#   RESTIC_NETWORK: a Docker network to join; only the drill sets it (to reach its test server).
restic_tool() {
  local network=()
  [ -n "${RESTIC_NETWORK:-}" ] && network=(--network "$RESTIC_NETWORK")
  MSYS_NO_PATHCONV=1 docker run --rm -i \
    ${network[@]+"${network[@]}"} \
    -e RESTIC_REPOSITORY -e RESTIC_PASSWORD -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY \
    -e AWS_DEFAULT_REGION \
    ${restic_mounts[@]+"${restic_mounts[@]}"} \
    "$RESTIC_IMAGE" --no-cache "$@"
}

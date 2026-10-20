#!/usr/bin/env bash
# M1 restart check (T10): stopping and starting the stack keeps the data and comes back healthy.
#
# Signs in through the web app, restarts the whole stack with `docker compose down` + `up`, then shows
# that the same sign-in session (a row in PostgreSQL) still works and every health check is "ok".
# Run from the repository root while the stack is up:
#
#   QBANK_CHECK_EMAIL=you@example.com make restart-check     # asks for the password
#
# Optional: QBANK_CHECK_URL (default http://localhost:3000), QBANK_CHECK_PASSWORD (skips the prompt).
set -euo pipefail

url="${QBANK_CHECK_URL:-http://localhost:3000}"
export QBANK_CHECK_EMAIL="${QBANK_CHECK_EMAIL:?Set QBANK_CHECK_EMAIL to your platform admin email}"
if [[ -z "${QBANK_CHECK_PASSWORD:-}" ]]; then
  read -rsp "Password for $QBANK_CHECK_EMAIL: " QBANK_CHECK_PASSWORD
  echo
fi
export QBANK_CHECK_PASSWORD

jar="$(mktemp)" before="$(mktemp)" after="$(mktemp)"
trap 'rm -f "$jar" "$before" "$after"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

# call METHOD BODY_FILE PATH [curl options...]: prints the HTTP status, saves the body to BODY_FILE.
call() {
  local method="$1" body_file="$2" path="$3"
  shift 3
  # --max-time: a server that accepts but never answers must not hang the check.
  curl -sS --max-time 10 -o "$body_file" -w '%{http_code}' -b "$jar" -c "$jar" -X "$method" \
    -H "Origin: $url" "$@" "$url$path"
}

echo "1/4 Signing in as $QBANK_CHECK_EMAIL"
# JSON-encode the credentials (a password may contain quotes or backslashes).
login_body="$(python3 -c 'import json, os
print(json.dumps({"email": os.environ["QBANK_CHECK_EMAIL"], "password": os.environ["QBANK_CHECK_PASSWORD"]}))')"
status="$(call POST /dev/null /api/v1/auth/login -H 'Content-Type: application/json' -d "$login_body")"
[[ "$status" == 200 ]] || fail "sign-in returned HTTP $status (wrong email or password?)"
[[ "$(call GET "$before" /api/v1/me)" == 200 ]] || fail "/api/v1/me did not work right after sign-in"

echo "2/4 Restarting the stack (docker compose down, then up; the data volume is kept)"
docker compose down
docker compose up -d

echo "3/4 Waiting for the app to be ready"
deadline=$((SECONDS + 120))
until [[ "$(call GET "$after" /health/ready 2>/dev/null)" == 200 ]]; do
  ((SECONDS < deadline)) || fail "not ready after 2 minutes (see: docker compose logs)"
  sleep 2
done
grep -q '"database":"ok"' "$after" && grep -q '"migrations":"ok"' "$after" \
  || fail "health is not ok after the restart: $(cat "$after")"

echo "4/4 Checking that the data survived"
status="$(call GET "$after" /api/v1/me)"
[[ "$status" == 200 ]] || fail "the session from before the restart was lost (HTTP $status)"
cmp -s "$before" "$after" || fail "/api/v1/me changed across the restart"

# Leave no extra session behind (sign-out needs the CSRF token the server set as a cookie).
csrf="$(awk '$6 == "qb_csrf" { print $7 }' "$jar")"
call POST /dev/null /api/v1/auth/logout -H "X-CSRF-Token: $csrf" > /dev/null

echo "PASS: the account and its sign-in session survived the restart; API, database and migrations ok."

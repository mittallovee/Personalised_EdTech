#!/bin/sh
# Checks that the monitoring stack works end to end: a test trace and a test log line go in through
# the Collector and come back out of Tempo and Loki through Grafana, Grafana knows its three data
# sources, refuses anonymous visitors, and every dashboard query is accepted.
#
# Run it after starting the stack (COMPOSE_PROFILES=observability docker compose up -d), and after
# every upgrade of Grafana, Tempo, Loki, Prometheus or the Collector (their configuration formats
# change between versions). From the repository root:
#
#   docker run --rm --network <project>_default \
#     -v "$PWD/infra/observability:/obs:ro" \
#     -e GRAFANA_ADMIN_PASSWORD=change-me-grafana-local \
#     --entrypoint sh curlimages/curl:latest /obs/smoke-test.sh
#
# <project> is the compose project name: "qbank" for the normal stack. Exit code 0 = all good.
set -u
PW="${GRAFANA_ADMIN_PASSWORD:-change-me-grafana-local}"
G="http://grafana:3000"
fail=0
check() { # check "what" "yes|no"
  if [ "$2" = yes ]; then echo "ok    $1"; else echo "FAIL  $1"; fail=1; fi
}
contains() { case "$1" in *"$2"*) echo yes ;; *) echo no ;; esac; }

now=$(date +%s)000000000
end=$(($(date +%s) + 1))000000000
TID=$(cat /proc/sys/kernel/random/uuid | tr -d '-')
LINE="{\\\"event\\\":\\\"smoke_test\\\",\\\"level\\\":\\\"info\\\",\\\"trace_id\\\":\\\"$TID\\\"}"

code=$(curl -s -o /dev/null -w "%{http_code}" -H 'Content-Type: application/json' \
  http://otel-collector:4318/v1/traces -d '{"resourceSpans":[{"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"qbank-smoke"}}]},"scopeSpans":[{"spans":[{"traceId":"'"$TID"'","spanId":"00f067aa0ba902b7","name":"GET /smoke","kind":2,"startTimeUnixNano":"'"$now"'","endTimeUnixNano":"'"$end"'","attributes":[{"key":"http.url","value":{"stringValue":"http://x/y?token=SMOKE_SECRET"}},{"key":"request.id","value":{"stringValue":"smoke-'"$TID"'"}}]}]}]}]}')
check "collector accepts a trace" "$([ "$code" = 200 ] && echo yes || echo no)"
code=$(curl -s -o /dev/null -w "%{http_code}" -H 'Content-Type: application/json' \
  http://otel-collector:4318/v1/logs -d '{"resourceLogs":[{"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"qbank-smoke"}}]},"scopeLogs":[{"logRecords":[{"timeUnixNano":"'"$now"'","severityText":"INFO","body":{"stringValue":"'"$LINE"'"}}]}]}]}')
check "collector accepts a log line" "$([ "$code" = 200 ] && echo yes || echo no)"

sleep 15
trace=$(curl -s -u "admin:$PW" "$G/api/datasources/proxy/uid/tempo/api/traces/$TID")
check "Tempo returns the trace" "$(contains "$trace" 'GET /smoke')"
check "the Collector removed the URL attribute (no secret in the trace)" \
  "$([ "$(contains "$trace" SMOKE_SECRET)" = no ] && echo yes || echo no)"
logs=$(curl -s -u "admin:$PW" -G "$G/api/datasources/proxy/uid/loki/loki/api/v1/query_range" \
  --data-urlencode "query={service_name=\"qbank-smoke\"} |= \"$TID\"")
check "Loki returns the log line by trace id" "$(contains "$logs" smoke_test)"
# Tempo 3 makes a new trace searchable after about a minute (fetching it by id works at once).
found=""
for _ in 1 2 3 4 5 6; do
  found=$(curl -s -u "admin:$PW" -G "$G/api/datasources/proxy/uid/tempo/api/search" \
    --data-urlencode "q={ span.request.id = \"smoke-$TID\" }")
  [ "$(contains "$found" "$TID")" = yes ] && break
  sleep 15
done
check "Tempo finds the trace by request id (the 'follow one request' search)" "$(contains "$found" "$TID")"

sources=$(curl -s -u "admin:$PW" "$G/api/datasources")
for name in Prometheus Loki Tempo; do check "Grafana has the $name data source" "$(contains "$sources" "\"name\":\"$name\"")"; done
anon=$(curl -s -o /dev/null -w "%{http_code}" "$G/api/datasources")
check "Grafana refuses anonymous visitors" "$([ "$anon" = 401 ] && echo yes || echo no)"
dash=$(curl -s -u "admin:$PW" "$G/api/search?tag=qbank")
check "both dashboards are loaded" "$([ "$(contains "$dash" qbank-overview)$(contains "$dash" qbank-follow-request)" = yesyes ] && echo yes || echo no)"
check "Prometheus answers a query through Grafana" "$(contains "$(curl -s -u "admin:$PW" -G "$G/api/datasources/proxy/uid/prometheus/api/v1/query" --data-urlencode 'query=vector(1)')" '"status":"success"')"

[ "$fail" = 0 ] && echo "All checks passed." || echo "SOME CHECKS FAILED."
exit "$fail"

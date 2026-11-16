# Sourced by backup-db.sh and restore-db.sh (K-03). Runs a PostgreSQL client tool either from this
# machine or, when PG_DOCKER_IMAGE is set (for example postgres:17), from that image, so the client
# can match the server's version: pg_dump refuses to dump a server newer than itself.
# Files go through stdin/stdout, so the container needs no mounted folders.
pg_tool() {
  if [ -n "${PG_DOCKER_IMAGE:-}" ]; then
    # PG_DOCKER_NETWORK: a Docker network to join instead of the host's (only the K-16 drill sets it).
    docker run --rm -i --network "${PG_DOCKER_NETWORK:-host}" \
      -e PGHOST -e PGPORT -e PGUSER -e PGPASSWORD -e PGDATABASE -e PGSSLMODE \
      "$PG_DOCKER_IMAGE" "$@"
  else
    "$@"
  fi
}

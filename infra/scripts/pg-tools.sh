# Sourced by backup-db.sh and restore-db.sh (K-03). Runs a PostgreSQL client tool either from this
# machine or, when PG_DOCKER_IMAGE is set (for example postgres:17), from that image, so the client
# can match the server's version: pg_dump refuses to dump a server newer than itself.
# Files go through stdin/stdout, so the container needs no mounted folders.
pg_tool() {
  if [ -n "${PG_DOCKER_IMAGE:-}" ]; then
    docker run --rm -i --network host \
      -e PGHOST -e PGPORT -e PGUSER -e PGPASSWORD -e PGDATABASE -e PGSSLMODE \
      "$PG_DOCKER_IMAGE" "$@"
  else
    "$@"
  fi
}

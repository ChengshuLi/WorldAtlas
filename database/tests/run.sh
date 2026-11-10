#!/usr/bin/env bash
set -euo pipefail

tests=$(cd -- "$(dirname -- "$0")" && pwd)
scratch=$(mktemp -d /tmp/worldatlas-db-tests.XXXXXX)
cleanup() {
  pg_ctl -D "$scratch/data" -m fast -w stop >/dev/null 2>&1 || true
  find "$scratch" -depth -delete
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

initdb -D "$scratch/data" -U postgres -A trust --no-locale --encoding=UTF8 >/dev/null
pg_ctl -D "$scratch/data" -o "-k $scratch -p 5432 -c listen_addresses=''" -l "$scratch/postgres.log" -w start >/dev/null
sql() {
  psql -Xq -v ON_ERROR_STOP=1 -h "$scratch" -p 5432 -U postgres "$@"
}

sql -d postgres -c 'CREATE DATABASE fresh'
for migration in "$tests"/../migrations/*.sql; do
  sql -d fresh -f "$migration"
done
for check in "$tests"/*.sql; do
  sql -d fresh -f "$check"
  printf 'PASS %s\n' "$(basename "$check")"
done

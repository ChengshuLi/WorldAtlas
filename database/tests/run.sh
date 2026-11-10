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

sql -d postgres -c 'CREATE DATABASE fresh' -c 'CREATE DATABASE upgrade'
for migration in "$tests"/../migrations/*.sql; do
  sql -d fresh -f "$migration"
done
for check in "$tests"/*.sql; do
  sql -d fresh -f "$check"
  printf 'PASS %s\n' "$(basename "$check")"
done

sql -d upgrade -f "$tests/../migrations/001_initial_schema.sql" -f "$tests/upgrade/before.sql"
sql -d postgres -c 'CREATE DATABASE blocked TEMPLATE upgrade'
sql -d blocked -c "UPDATE atlas.decision_revisions SET status = 'rejected' WHERE revision = 'working'"
if sql -d blocked -f "$tests/../migrations/002_release_candidates.sql" >"$scratch/rejected.log" 2>&1; then
  printf 'Migration should stop when it finds a historical review\n' >&2
  exit 1
fi
if ! grep -q 'archive existing decision and entity reviews before upgrading' "$scratch/rejected.log"; then
  cat "$scratch/rejected.log" >&2
  exit 1
fi
review=$(sql -d blocked -Atc "SELECT status FROM atlas.decision_revisions WHERE revision = 'working'")
if [[ "$review" != rejected ]]; then
  printf 'Failed migration changed the historical review\n' >&2
  exit 1
fi
for migration in "$tests"/../migrations/*.sql; do
  if [[ "$migration" != */001_initial_schema.sql ]]; then
    sql -d upgrade -f "$migration"
  fi
done
sql -d upgrade -f "$tests/upgrade/after.sql"
printf 'PASS upgrade from the V8 schema\n'

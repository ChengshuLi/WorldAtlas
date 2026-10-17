#!/bin/bash
# One stock physical execution, with sampled filesystem usage and full outer logs.
# These observations are not a hard process-tree, elapsed-time or output cap.
set -u -o pipefail -o noclobber
repo=$1
logroot=$2
prefix=coordination/engineering/argentina-repair-delivery-20261017
baseline=d4968ddc37aa3aa6105e9610c9e6fadbb368ba14
expected_thread=01a14784-198b-734e-b6ce-4c7c5e3ad008
[[ $# == 2 && "${CODEX_THREAD_ID:-}" == "$expected_thread" ]] || exit 2
[[ -d "$repo" && -d "$logroot" && ! -e "$repo/$prefix/physical-001" ]] || exit 3
[[ ! -e "$logroot/physical-001.stdout.log" && ! -e "$logroot/physical-001.stderr.log" && ! -e "$logroot/physical-001.storage.tsv" ]] || exit 4
cd "$repo" || exit 5
[[ -z "$(git diff "$baseline" -- scripts/prepare-delivery-handoff.mjs scripts/qualify-source-cohort.py)" ]] || exit 6
free=$(df -B1 --output=avail . | tail -1 | tr -d ' ')
# Admission estimate only: approximately200MB extra staging/publication and50MB margin.
[[ "$free" -ge 250000000 ]] || exit 7
printf 'utc\tavailable_bytes\tstaging_bytes\tpublished_bytes\n' > "$logroot/physical-001.storage.tsv"
start=$(date -u +%Y-%m-%dT%H:%M:%SZ)
env -u NODE_OPTIONS -u NODE_PATH node scripts/prepare-delivery-handoff.mjs physical "$prefix/config/physical-001.json" "$prefix/physical-001" > "$logroot/physical-001.stdout.log" 2> "$logroot/physical-001.stderr.log" &
pid=$!
printf '%s\n' "$pid" > "$logroot/physical-001.pid"
while kill -0 "$pid" 2>/dev/null; do
  available=$(df -B1 --output=avail . | tail -1 | tr -d ' ')
  staged=$(du -sb .cache/delivery-handoff 2>/dev/null | cut -f1); staged=${staged:-0}
  published=$(du -sb "$prefix/physical-001" 2>/dev/null | cut -f1); published=${published:-0}
  printf '%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$available" "$staged" "$published" >> "$logroot/physical-001.storage.tsv"
  sleep 2
done
wait "$pid"; status=$?
printf 'started_utc=%s\nfinished_utc=%s\nexit_code=%s\n' "$start" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$status" > "$logroot/physical-001.exit.txt"
cat "$logroot/physical-001.stdout.log"
cat "$logroot/physical-001.stderr.log" >&2
exit "$status"

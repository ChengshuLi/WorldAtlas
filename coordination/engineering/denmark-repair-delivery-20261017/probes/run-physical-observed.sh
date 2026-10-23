#!/usr/bin/env bash
# One whole-source stock execution with observed storage, no arbitrary byte ceiling.
set -uo pipefail
W=$1
P=coordination/engineering/denmark-repair-delivery-20261017
cd "$W" || exit
O="$P/physical-observations-001"
[[ ! -e "$O" && ! -L "$O" && ! -e "$P/physical-001" ]] || exit 1
mkdir "$O" || exit
printf 'time_utc\tavailable_bytes\tstaging_bytes\toutput_bytes\n' > "$O/physical-001.storage.tsv"
env -u NODE_OPTIONS -u NODE_PATH node scripts/prepare-delivery-handoff.mjs physical "$P/config/physical-001.json" "$P/physical-001" > "$O/physical-001.stdout.log" 2> "$O/physical-001.stderr.log" &
pid=$!
while kill -0 "$pid" 2>/dev/null; do
 free=$(df -B1 --output=avail . | tail -1 | tr -d ' ')
 stage=$(du -sb .cache/delivery-handoff 2>/dev/null | cut -f1); stage=${stage:-0}
 output=$(du -sb "$P/physical-001" 2>/dev/null | cut -f1); output=${output:-0}
 printf '%s\t%s\t%s\t%s\n' "$(date -u +%FT%TZ)" "$free" "$stage" "$output" >> "$O/physical-001.storage.tsv"
 sleep 1
done
wait "$pid"; code=$?
printf '%s\n' "$code" > "$O/physical-001.exit.txt"
cat "$O/physical-001.stdout.log"
exit "$code"

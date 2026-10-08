#!/bin/bash
set -euo pipefail
if [[ $# -ne 3 ]]; then
  echo 'usage: native_archive_extract.sh EXECUTION_COMMIT PHASE_PLAN_SHA256 NATIVE_TOOLS_LOCK_SHA256' >&2
  exit 2
fi
BASE=$1
PLAN_SHA=$2
TOOLS_SHA=$3
BOOTSTRAP_GIT=/Library/Developer/CommandLineTools/usr/bin/git
BOOTSTRAP_GIT_SHA=4c5ca299b5311572b4f948d11efd7c66dcadf30950fbf260688ee32f4a63f6a4
BOOTSTRAP_SHA256SUM=/sbin/sha256sum
BOOTSTRAP_SHA256SUM_SHA=911cfe6fc220c41ee02d18ea71c89f8ff788bdf8a6d4f0d6f94dc965aa18521f
BOOTSTRAP_WC=/usr/bin/wc
BOOTSTRAP_WC_SHA=6dd1ce80825c439ef6dc4812cdb0711bf191446728b8a13ed655f22ce210aeee
test "$("$BOOTSTRAP_SHA256SUM" "$BOOTSTRAP_SHA256SUM")" = "$BOOTSTRAP_SHA256SUM_SHA  $BOOTSTRAP_SHA256SUM"
test "$("$BOOTSTRAP_SHA256SUM" "$BOOTSTRAP_GIT")" = "$BOOTSTRAP_GIT_SHA  $BOOTSTRAP_GIT"
test "$("$BOOTSTRAP_SHA256SUM" "$BOOTSTRAP_WC")" = "$BOOTSTRAP_WC_SHA  $BOOTSTRAP_WC"
git() { "$BOOTSTRAP_GIT" "$@"; }
ROOT=$(cd "${BASH_SOURCE[0]%/*}/../../.." && pwd -P)
PACKET=$ROOT/research/geography/arctic-seven-source-fit-20261008
PLAN=$PACKET/phase-plan-r10.json
SCRIPT_REL=research/geography/arctic-seven-source-fit-20261008/native_archive_extract.sh
TOOLS_JSON=research/geography/arctic-seven-source-fit-20261008/native-tools-lock-r10.json
TOOLS_SHELL=research/geography/arctic-seven-source-fit-20261008/native-tools-lock-r10.sh
VINTAGES=$PACKET/vintages
RUN=$VINTAGES/r10-native-extract
CAP=268435456
DECODED=162109440
MEMBER_BYTES=2756674
SCRATCH_RESERVE=4194304
OUTPUT_RESERVE=65536
RECEIPT_RESERVE=4096

test "$BASH" = /bin/bash
test "$("$BOOTSTRAP_SHA256SUM" /bin/bash)" = "b46e8d4eac541d79f77000550b4254b47599df8dd8c52cc5b0f37cca1c3b02d4  /bin/bash"
test "$(git -C "$ROOT" rev-parse HEAD)" = "$BASE"
LC_ALL=C
PLAN_SIZE=$("$BOOTSTRAP_WC" -c < "$PLAN")
PLAN_SIZE=$(( PLAN_SIZE ))
if [[ ! "$PLAN_SIZE" =~ ^[0-9]+$ ]] || (( PLAN_SIZE < 1 || PLAN_SIZE > 1048576 )); then
  echo 'phase plan is empty or exceeds 1 MiB' >&2
  exit 1
fi
PLAN_PREFIX=
IFS= read -r -n "$PLAN_SIZE" PLAN_PREFIX < "$PLAN" || true
if (( ${#PLAN_PREFIX} != PLAN_SIZE - 1 )); then
  echo 'phase plan is not one bounded ASCII JSON line with a final newline' >&2
  exit 1
fi
PLAN_ACTUAL=$("$BOOTSTRAP_SHA256SUM" "$PLAN"); test "${PLAN_ACTUAL%% *}" = "$PLAN_SHA"
if [[ "$PLAN_PREFIX" != *"\"execution_commit\":\"$BASE\""* ]]; then
  echo 'phase plan execution commit mismatch' >&2
  exit 1
fi
if [[ "$PLAN_PREFIX" != *"\"native_tools_lock_sha256\":\"$TOOLS_SHA\""* ]]; then
  echo 'phase plan native-tools lock mismatch' >&2
  exit 1
fi
TOOLS_LOCK_ACTUAL=$("$BOOTSTRAP_GIT" -C "$ROOT" show "$BASE:$TOOLS_JSON" | "$BOOTSTRAP_SHA256SUM")
test "${TOOLS_LOCK_ACTUAL%% *}" = "$TOOLS_SHA"
TOOLS_LOCAL_ACTUAL=$("$BOOTSTRAP_SHA256SUM" "$ROOT/$TOOLS_JSON")
test "${TOOLS_LOCAL_ACTUAL%% *}" = "$TOOLS_SHA"
TOOLS_SHELL_ACTUAL=$("$BOOTSTRAP_GIT" -C "$ROOT" show "$BASE:$TOOLS_SHELL" | "$BOOTSTRAP_SHA256SUM")
TOOLS_LOCAL_ACTUAL=$("$BOOTSTRAP_SHA256SUM" "$ROOT/$TOOLS_SHELL")
test "${TOOLS_SHELL_ACTUAL%% *}" = "${TOOLS_LOCAL_ACTUAL%% *}"
SCRIPT_BASE=$("$BOOTSTRAP_GIT" -C "$ROOT" show "$BASE:$SCRIPT_REL" | "$BOOTSTRAP_SHA256SUM")
SCRIPT_LOCAL=$("$BOOTSTRAP_SHA256SUM" "$ROOT/$SCRIPT_REL")
test "${SCRIPT_BASE%% *}" = "${SCRIPT_LOCAL%% *}"
source "$ROOT/$TOOLS_SHELL"
test "$NATIVE_TOOLS_LOCK_SHA256" = "$TOOLS_SHA"
test "$NATIVE_GIT" = "$BOOTSTRAP_GIT"
test "$NATIVE_BASH" = /bin/bash

# Reject any existing or symlinked output path before reading source bodies.
path=$PACKET
while [[ "$path" == "$ROOT/"* || "$path" == "$ROOT" ]]; do
  if [[ -L "$path" ]]; then echo "symlink output ancestor: $path" >&2; exit 1; fi
  [[ "$path" == "$ROOT" ]] && break
  path=${path%/*}
done
for path in "$VINTAGES" "$RUN"; do
  if [[ -L "$path" ]]; then echo "symlink output ancestor: $path" >&2; exit 1; fi
done
if [[ -e "$RUN" || -L "$RUN" ]]; then echo 'fresh native extraction vintage already exists' >&2; exit 1; fi

PARTS=(part-00.bin part-01.bin part-02.bin part-03.bin part-04.bin part-05.bin)
HASHES=(8917630246c7e4df6e767e1bf886c1cdb8de7713408a1eb9e95a6f0782243939 5399dea4d3facb3606370e3c3df324145dc65b1a069dc273bd4c10e3c731a928 21cf68cc1544cce4969e9a2275370eeeebea588de7cb5c102c3debae26107a6b db2db7c0e7bbf7d45cb3f2bba6b02e840137867bae06ede3ca7cf6c011c9dbe0 a509feaf415d8e724044081a9318c18cbb44a9089d43c91ae9d1bb18afed334b 9dc67da0f76dcdef7ef6194a812d2836e0c12e32598a2d73a20d79dfecae6e32)
EXPECTED_SIZES=(8388608 8388608 8388608 8388608 8388608 3658640)
INPUT_BYTES=0
for i in "${!PARTS[@]}"; do
  source_path=data/semantic-evidence/${PARTS[$i]}
  size=$(git -C "$ROOT" cat-file -s "$BASE:$source_path")
  test "$size" = "${EXPECTED_SIZES[$i]}"
  INPUT_BYTES=$((INPUT_BYTES + size))
done
NATIVE_PATH=research/geography/arctic-seven-source-fit-20261008/sources/aafc-ecoregions.native.geojson
REGISTRY_PATH=data/semantic-sources.json
REGISTRY_SHA=287a7ae13787b9e9fb97051afb977c8ea054ca1a6fed389c6672d6455d24bf7e
REGISTRY_SIZE=$(git -C "$ROOT" cat-file -s "$BASE:$REGISTRY_PATH")
test "$REGISTRY_SIZE" = 4849
native_size=$(git -C "$ROOT" cat-file -s "$BASE:$NATIVE_PATH")
test "$native_size" = "$MEMBER_BYTES"
INPUT_BYTES=$((INPUT_BYTES + native_size + REGISTRY_SIZE * 10))
SCRIPT_BYTES=$(git -C "$ROOT" cat-file -s "$BASE:$SCRIPT_REL")
TOOLS_JSON_BYTES=$(git -C "$ROOT" cat-file -s "$BASE:$TOOLS_JSON")
TOOLS_SHELL_BYTES=$(git -C "$ROOT" cat-file -s "$BASE:$TOOLS_SHELL")
# Code and lock bytes are read from Git and from the materialized checkout.
CODE_BYTES=$((SCRIPT_BYTES * 3 + TOOLS_JSON_BYTES * 2 + TOOLS_SHELL_BYTES * 3))
PLAN_BYTES=$(( PLAN_SIZE * 5 ))
PROSPECTIVE=$((INPUT_BYTES + CODE_BYTES + PLAN_BYTES + NATIVE_TOOLS_TOTAL_BYTES + DECODED + SCRATCH_RESERVE + OUTPUT_RESERVE + RECEIPT_RESERVE))
if (( PROSPECTIVE > CAP )); then
  echo "native extraction prospective charge exceeds 256 MiB: $PROSPECTIVE" >&2
  exit 1
fi

# Installed binaries and OS release are whole-hash checked before source reads.
verify_native_tools
REGISTRY_BASE=$(git -C "$ROOT" show "$BASE:$REGISTRY_PATH" | sha256sum)
test "${REGISTRY_BASE%% *}" = "$REGISTRY_SHA"
REGISTRY_LOCAL=$(sha256sum "$ROOT/$REGISTRY_PATH")
test "${REGISTRY_LOCAL%% *}" = "$REGISTRY_SHA"
for hash in "${HASHES[@]}" 9ed454c129cc92cd999dae6877587997c25cec47bdfdc35a8b3f20863858430e a565563a6aef794df831dc9251fb4108018e20a4f0172acbc36b599f9b7f4abf; do
  grep -Fq "$hash" "$ROOT/$REGISTRY_PATH"
done
TMP=$(mktemp -d)
cleanup() {
  [[ ! -e "$TMP/archive.sha256" ]] || unlink "$TMP/archive.sha256"
  for i in "${!PARTS[@]}"; do [[ ! -e "$TMP/part-$i.sha256" ]] || unlink "$TMP/part-$i.sha256"; done
  [[ ! -e "$TMP/aafc-ecoregions.geojson" ]] || unlink "$TMP/aafc-ecoregions.geojson"
  rmdir "$TMP"
}
trap cleanup EXIT HUP INT TERM
{
  for i in "${!PARTS[@]}"; do
    part=${PARTS[$i]}
    git -C "$ROOT" show "$BASE:data/semantic-evidence/$part" | tee >(sha256sum > "$TMP/part-$i.sha256")
  done
} | tee >(sha256sum > "$TMP/archive.sha256") | tar -xzOf - aafc-ecoregions.geojson > "$TMP/aafc-ecoregions.geojson"
wait
for i in "${!PARTS[@]}"; do
  read -r part_hash _ < "$TMP/part-$i.sha256"
  test "$part_hash" = "${HASHES[$i]}"
done
read -r archive_hash _ < "$TMP/archive.sha256"
test "$archive_hash" = 9ed454c129cc92cd999dae6877587997c25cec47bdfdc35a8b3f20863858430e
member_hash=$(sha256sum "$TMP/aafc-ecoregions.geojson"); member_hash=${member_hash%% *}
test "$member_hash" = a565563a6aef794df831dc9251fb4108018e20a4f0172acbc36b599f9b7f4abf
cmp "$TMP/aafc-ecoregions.geojson" <(git -C "$ROOT" show "$BASE:$NATIVE_PATH")

# Reserve a fresh contained destination and write complete products exclusively.
if [[ ! -d "$VINTAGES" ]]; then mkdir "$VINTAGES"; fi
if [[ -L "$VINTAGES" || -L "$PACKET" ]]; then echo 'symlink output path appeared during extraction' >&2; exit 1; fi
mkdir "$RUN"
set -o noclobber
printf '{"version":1,"status":"native-member-extracted","archive_bytes":45601680,"archive_sha256":"%s","archive_parts":[{"path":"data/semantic-evidence/part-00.bin","bytes":8388608,"sha256":"%s"},{"path":"data/semantic-evidence/part-01.bin","bytes":8388608,"sha256":"%s"},{"path":"data/semantic-evidence/part-02.bin","bytes":8388608,"sha256":"%s"},{"path":"data/semantic-evidence/part-03.bin","bytes":8388608,"sha256":"%s"},{"path":"data/semantic-evidence/part-04.bin","bytes":8388608,"sha256":"%s"},{"path":"data/semantic-evidence/part-05.bin","bytes":3658640,"sha256":"%s"}],"member_path":"aafc-ecoregions.geojson","member_bytes":%s,"member_sha256":"%s","member_byte_identical_to_retained_file":true,"baseline_commit":"%s","phase_plan_sha256":"%s"}\n' \
  "$archive_hash" "${HASHES[0]}" "${HASHES[1]}" "${HASHES[2]}" "${HASHES[3]}" "${HASHES[4]}" "${HASHES[5]}" \
  "$MEMBER_BYTES" "$member_hash" "$BASE" "$PLAN_SHA" > "$RUN/native-archive-extraction.json"
EXTRACTION_HASH=$(sha256sum "$RUN/native-archive-extraction.json"); EXTRACTION_HASH=${EXTRACTION_HASH%% *}
EXTRACTION_SIZE=$(wc -c < "$RUN/native-archive-extraction.json" | tr -d ' ')
printf '{"version":1,"status":"complete","phase":"native-archive-extract","baseline_commit":"%s","plan_sha256":"%s","native_tools_lock_sha256":"%s","native_runtime_bytes":%s,"archive_input_bytes_read_once":%s,"candidate_input_bytes":%s,"decoded_source_reserved_bytes":%s,"scratch_reserved_bytes":%s,"output_reserved_bytes":%s,"prospective_charge_bytes":%s}\n' \
  "$BASE" "$PLAN_SHA" "$TOOLS_SHA" "$NATIVE_TOOLS_TOTAL_BYTES" "$((INPUT_BYTES - native_size))" "$native_size" "$DECODED" "$SCRATCH_RESERVE" "$OUTPUT_RESERVE" "$PROSPECTIVE" > "$RUN/execution-receipt.json"
EXECUTION_HASH=$(sha256sum "$RUN/execution-receipt.json"); EXECUTION_HASH=${EXECUTION_HASH%% *}
EXECUTION_SIZE=$(wc -c < "$RUN/execution-receipt.json" | tr -d ' ')
printf '{"version":1,"status":"complete","outputs":[{"path":"research/geography/arctic-seven-source-fit-20261008/vintages/r10-native-extract/native-archive-extraction.json","bytes":%s,"sha256":"%s","hash_kind":"file-bytes"},{"path":"research/geography/arctic-seven-source-fit-20261008/vintages/r10-native-extract/execution-receipt.json","bytes":%s,"sha256":"%s","hash_kind":"file-bytes"}]}\n' \
  "$EXTRACTION_SIZE" "$EXTRACTION_HASH" "$EXECUTION_SIZE" "$EXECUTION_HASH" > "$RUN/.publication-incomplete"
sync
ln "$RUN/.publication-incomplete" "$RUN/publication.json"
unlink "$RUN/.publication-incomplete"
echo "{\"status\":\"complete\",\"phase\":\"native-archive-extract\",\"prospective_bytes\":$PROSPECTIVE,\"member_sha256\":\"$member_hash\"}"

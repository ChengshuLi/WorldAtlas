#!/bin/bash
set -euo pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
PACKET=$ROOT/research/geography/arctic-seven-source-fit-20261008
BASE=960ba2f4fef0fc9881b8a106a944e6e3874e98c9
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
ARCHIVE=$TMP/aafc-source.tar.gz
: > "$ARCHIVE"
names=(part-00.bin part-01.bin part-02.bin part-03.bin part-04.bin part-05.bin)
hashes=(8917630246c7e4df6e767e1bf886c1cdb8de7713408a1eb9e95a6f0782243939 5399dea4d3facb3606370e3c3df324145dc65b1a069dc273bd4c10e3c731a928 21cf68cc1544cce4969e9a2275370eeeebea588de7cb5c102c3debae26107a6b db2db7c0e7bbf7d45cb3f2bba6b02e840137867bae06ede3ca7cf6c011c9dbe0 a509feaf415d8e724044081a9318c18cbb44a9089d43c91ae9d1bb18afed334b 9dc67da0f76dcdef7ef6194a812d2836e0c12e32598a2d73a20d79dfecae6e32)
for i in "${!names[@]}"; do
  digest=$(git -C "$ROOT" show "$BASE:data/semantic-evidence/${names[$i]}" | tee -a "$ARCHIVE" | shasum -a 256)
  test "${digest%% *}" = "${hashes[$i]}"
done
archive_hash=$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')
test "$archive_hash" = 9ed454c129cc92cd999dae6877587997c25cec47bdfdc35a8b3f20863858430e
tar -xzOf "$ARCHIVE" aafc-ecoregions.geojson > "$TMP/aafc-ecoregions.geojson"
cmp "$TMP/aafc-ecoregions.geojson" "$PACKET/sources/aafc-ecoregions.native.geojson"
member_hash=$(shasum -a 256 "$TMP/aafc-ecoregions.geojson" | awk '{print $1}')
test "$member_hash" = a565563a6aef794df831dc9251fb4108018e20a4f0172acbc36b599f9b7f4abf
printf '{"archive_bytes":45601680,"archive_sha256":"%s","member_bytes":2756674,"member_sha256":"%s","member_byte_identical_to_retained_file":true,"baseline_commit":"%s"}\n' "$archive_hash" "$member_hash" "$BASE" > "$PACKET/native-archive-verification.json"

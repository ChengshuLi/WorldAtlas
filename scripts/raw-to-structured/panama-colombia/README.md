# Assemble and verify the Panama–Colombia boundary

A source archive is one ZIP file stored in R2. It contains OpenStreetMap JSON
responses and a `manifest.json` listing the border segments, their filenames
and checksums, and the starting node. Neon holds the selected boundary, its
source links, and rationale.

The shared [assembler](../shared/assemble_osm_ways.py) reads the extracted local
files, joins the segments into one continuous line, and writes a local GeoJSON
file. Its three arguments are the manifest path, the directory containing the
source responses, and the output path. The output file must not already exist.

The shared [verifier](../shared/osm_source_handoff.py) takes a local archive path,
its expected SHA-256, and the expected boundary geometry SHA-256. It checks that:

1. The ZIP matches the supplied archive checksum.
2. Its contents match the manifest, including each source file's checksum.
3. The segments join into one continuous boundary.
4. The resulting geometry matches the supplied boundary checksum.

These shared tools work with local files. The Panama–Colombia
[entry script](build_boundary.py) connects them to Neon and R2:

1. Look up the requested raw source version in Neon's `atlas.source_assets`.
2. Download its ZIP from R2 and check its cataloged size and checksum.
3. Assemble the boundary, optionally checking an expected geometry checksum.
4. Save the geometry in `atlas.decision_mainland_boundaries` and its source link
   in `atlas.decision_mainland_boundary_sources`, together in one transaction.

The destination decision revision must already exist. Repeating the command
updates the same boundary. Existing notes and supporting source links are kept;
the construction source link follows the selected source version.

Use Python 3.11 or later with `boto3` and `psycopg`. Set `NEON_DATABASE_URL` to the
working database and configure the existing R2 credentials through `AWS_PROFILE`.
The entry script contains the Panama–Colombia source ID, boundary ID and rationale.
Assembly, verification, downloading and database writes live in [shared code](../shared/)
for other boundary tools to reuse.

## Example: V8.0 release

Run from the repository root with the credentials above. This command downloads
the cataloged source and saves the 5,254-point boundary selected by `v8-mainland`:

```bash
PANAMA_WORK_DIR="$(mktemp -d)"
python3 scripts/raw-to-structured/panama-colombia/build_boundary.py \
  --source-version capture-20261105-04fe1adb295e \
  --revision v8-mainland \
  --r2-endpoint https://8551d6a44afbf7d8080fb67cefe241fc.r2.cloudflarestorage.com \
  --work-dir "$PANAMA_WORK_DIR" \
  --expected-geometry-sha256 cfbfbb514d0f6efff1c0c803ae5f0f0835225015568747bb8b1164f3bb6d0e17
```

For another revision, pass its destination and source version. The optional
geometry checksum checks an existing result when replaying a release. Omit it
when constructing a changed boundary.

To run the shared tools separately on the downloaded archive, set:

```bash
PANAMA_OSM_ARCHIVE="$PANAMA_WORK_DIR/04fe1adb295e93d78ee029b48351d2b0380d69ac631b47c909dffd538bbaf6c1/source.zip"
```

First, extract the archive into a new temporary directory and run the assembler:

```bash
PANAMA_OSM_DIRECTORY="$(mktemp -d)"
python3 -m zipfile -e "$PANAMA_OSM_ARCHIVE" "$PANAMA_OSM_DIRECTORY"
PYTHONPATH=scripts/raw-to-structured python3 -m shared.assemble_osm_ways \
  "$PANAMA_OSM_DIRECTORY/manifest.json" \
  "$PANAMA_OSM_DIRECTORY" \
  "$PANAMA_OSM_DIRECTORY/boundary.geojson"
```

For this V8.0 source, the assembler prints 5,254 vertices and SHA-256
`cfbfbb514d0f6efff1c0c803ae5f0f0835225015568747bb8b1164f3bb6d0e17`.

Then run the verifier to check the archive and reconstructed boundary against
the V8.0 checksums:

```bash
PYTHONPATH=scripts/raw-to-structured python3 - "$PANAMA_OSM_ARCHIVE" <<'PY'
import sys
from shared.osm_source_handoff import verified_geometry

line = verified_geometry(
    sys.argv[1],
    "04fe1adb295e93d78ee029b48351d2b0380d69ac631b47c909dffd538bbaf6c1",
    "cfbfbb514d0f6efff1c0c803ae5f0f0835225015568747bb8b1164f3bb6d0e17",
)
print(len(line["coordinates"]))
PY
```

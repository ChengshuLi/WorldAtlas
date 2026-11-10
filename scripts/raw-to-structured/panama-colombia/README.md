# Panama–Colombia boundary

Build the Panama–Colombia administrative border used to separate North and
South America on the map.

The construction record `panama-colombia-osm-construction` in Neon's
`atlas.structured_documents` selects:

| Setting | Value |
| --- | --- |
| Processing method | `osm_way_chain` |
| Raw source in Neon's catalog | `osm-panama-current-way-full-bundle` |
| Editable boundary ID in Neon | `panama_colombia_osm_admin_boundary` |
| How the boundary is built | Join archived OpenStreetMap border segments at their shared point IDs, preserving their coordinates. |

The record also selects the raw source version. The
[shared OSM command](../shared/build_osm_boundary.py) reads those settings and
builds the boundary. Its arguments select the construction record's version and
the destination decision revision. See the [shared guide](../shared/README.md)
for the record format, setup, and command arguments.

## Example: V8.0 release

Run from the repository root with the [shared setup](../shared/README.md#neon-and-r2-workflow).
This command downloads the source and saves the 5,254-point boundary in the
existing `v8-mainland` decision revision:

```bash
PANAMA_WORK_DIR="$(mktemp -d)"
PYTHONPATH=scripts/raw-to-structured python3 -m shared.build_osm_boundary \
  --recipe panama-colombia-osm-construction 1 \
  --revision v8-mainland \
  --r2-endpoint https://8551d6a44afbf7d8080fb67cefe241fc.r2.cloudflarestorage.com \
  --work-dir "$PANAMA_WORK_DIR" \
  --expected-geometry-sha256 cfbfbb514d0f6efff1c0c803ae5f0f0835225015568747bb8b1164f3bb6d0e17
```

Construction record version `1` selects raw source version
`capture-20261105-04fe1adb295e`. To change those settings, add a new version of the
construction record and select it with `--recipe`. Use `--revision` to choose
where the resulting boundary is saved. Omit the optional geometry checksum when
constructing a changed boundary.

To run the shared tools separately on the downloaded archive, set:

```bash
PANAMA_OSM_ARCHIVE="$PANAMA_WORK_DIR/04fe1adb295e93d78ee029b48351d2b0380d69ac631b47c909dffd538bbaf6c1/source.zip"
```

First, extract the archive into a new temporary directory and run the assembler:

```bash
PANAMA_OSM_DIRECTORY="$(mktemp -d)"
python3 -m zipfile -e "$PANAMA_OSM_ARCHIVE" "$PANAMA_OSM_DIRECTORY"
PYTHONPATH=scripts/raw-to-structured python3 -m shared.osm_ways \
  "$PANAMA_OSM_DIRECTORY/manifest.json" \
  "$PANAMA_OSM_DIRECTORY" \
  "$PANAMA_OSM_DIRECTORY/boundary.geojson"
```

For this V8.0 source, the assembler prints 5,254 vertices and SHA-256
`cfbfbb514d0f6efff1c0c803ae5f0f0835225015568747bb8b1164f3bb6d0e17`.

Then call `assemble_archive()` with the expected geometry checksum to check the
archive and reconstructed boundary against the V8.0 checksums:

```bash
PYTHONPATH=scripts/raw-to-structured python3 - "$PANAMA_OSM_ARCHIVE" <<'PY'
import sys
from shared.osm_ways import assemble_archive

line = assemble_archive(
    sys.argv[1],
    "04fe1adb295e93d78ee029b48351d2b0380d69ac631b47c909dffd538bbaf6c1",
    expected_geometry_sha256="cfbfbb514d0f6efff1c0c803ae5f0f0835225015568747bb8b1164f3bb6d0e17",
)
print(len(line["coordinates"]))
PY
```

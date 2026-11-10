# Verify the Panama–Colombia boundary input

Download the `osm-panama-current-way-full-bundle` archive selected in Neon.
The [archive verifier](osm_source_handoff.py) checks the archive and the
individual OpenStreetMap responses, joins the ways in order, and checks the
resulting geometry. Neon holds the selected line, source links, and rationale.

Set `PANAMA_OSM_ARCHIVE` to the local archive path and run from the repository
root. Use the archive and geometry hashes for the revision you are verifying.
This example checks the 5,254-point line selected by `v8-mainland`.

```bash
PYTHONPATH=scripts/raw-to-structured/panama-colombia python3 - "$PANAMA_OSM_ARCHIVE" <<'PY'
import sys
from osm_source_handoff import verified_geometry

line = verified_geometry(
    sys.argv[1],
    "04fe1adb295e93d78ee029b48351d2b0380d69ac631b47c909dffd538bbaf6c1",
    "cfbfbb514d0f6efff1c0c803ae5f0f0835225015568747bb8b1164f3bb6d0e17",
)
print(len(line["coordinates"]))
PY
```

## Assemble the V8 boundary into a local file

After verifying the archive above, extract it into a new temporary directory
and run [the assembler](assemble_osm_ways.py) from the repository root:

```bash
PANAMA_OSM_DIRECTORY="$(mktemp -d)"
python3 -m zipfile -e "$PANAMA_OSM_ARCHIVE" "$PANAMA_OSM_DIRECTORY"
python3 scripts/raw-to-structured/panama-colombia/assemble_osm_ways.py \
  "$PANAMA_OSM_DIRECTORY/manifest.json" \
  "$PANAMA_OSM_DIRECTORY" \
  "$PANAMA_OSM_DIRECTORY/boundary.geojson"
```

The three arguments are the extracted manifest, the directory containing the
OpenStreetMap responses named in that manifest, and the output file to create.
The output file must not already exist. For this V8 source, the assembler prints
5,254 vertices and SHA-256
`cfbfbb514d0f6efff1c0c803ae5f0f0835225015568747bb8b1164f3bb6d0e17`.
The generated GeoJSON stays on local disk; this command does not update Neon.

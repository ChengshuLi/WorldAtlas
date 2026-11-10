# Assemble and verify the Panama–Colombia boundary

A source archive is one ZIP file stored in R2. It contains OpenStreetMap JSON
responses and a `manifest.json` listing the border segments, their filenames
and checksums, and the starting node. Neon holds the selected boundary, its
source links, and rationale.

The [assembler](assemble_osm_ways.py) reads the extracted local files, joins the
segments into one continuous line, and writes a local GeoJSON file. Its three
arguments are the manifest path, the directory containing the source responses,
and the output path. The output file must not already exist.

The [verifier](osm_source_handoff.py) takes a local archive path, its expected
SHA-256, and the expected boundary geometry SHA-256. It checks that:

1. The ZIP matches the supplied archive checksum.
2. Its contents match the manifest, including each source file's checksum.
3. The segments join into one continuous boundary.
4. The resulting geometry matches the supplied boundary checksum.

Both tools work with local files; neither downloads from R2 nor reads or
updates Neon.

## Example: V8

Download the `osm-panama-current-way-full-bundle` archive selected in Neon,
set `PANAMA_OSM_ARCHIVE` to its local path, and run from the repository root.
These checksums verify the 5,254-point line selected by `v8-mainland`.
For another boundary revision, use its archive and geometry checksums.

First, verify the archive and reconstructed boundary:

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

To also save the boundary as a local file, extract the verified archive into a
new temporary directory and run the assembler:

```bash
PANAMA_OSM_DIRECTORY="$(mktemp -d)"
python3 -m zipfile -e "$PANAMA_OSM_ARCHIVE" "$PANAMA_OSM_DIRECTORY"
python3 scripts/raw-to-structured/panama-colombia/assemble_osm_ways.py \
  "$PANAMA_OSM_DIRECTORY/manifest.json" \
  "$PANAMA_OSM_DIRECTORY" \
  "$PANAMA_OSM_DIRECTORY/boundary.geojson"
```

For this V8 source, the assembler prints 5,254 vertices and SHA-256
`cfbfbb514d0f6efff1c0c803ae5f0f0835225015568747bb8b1164f3bb6d0e17`.

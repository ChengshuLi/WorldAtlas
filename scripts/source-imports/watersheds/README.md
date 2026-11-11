# Watershed boundaries

**TL;DR:** Read a construction record from Neon, download its verified raw files
from R2, calculate drainage on the source elevation grid, and save the complete
boundary in Neon. The same code handles different boundaries. Geographic
selections live in the construction record.

## Code

| File | Responsibility |
| --- | --- |
| [`build_boundary.py`](build_boundary.py) | Read settings, call the functions, and save the result. |
| [`terrain.py`](terrain.py) | Crop native grids and fill missing heights from real secondary data. |
| [`drainage.py`](drainage.py) | Calculate eight-neighbor flow and downstream destinations. |
| [`waterways.py`](waterways.py) | Read natural waterways and source basin polygons. |
| [`sources.py`](sources.py) | Read selected provider vertices, ways and river relations. |
| [`boundary.py`](boundary.py) | Find connected divides and shared joins, then assemble the final line. |
| [`../source_io.py`](../source_io.py) | Resolve catalog versions, verify downloads, and write geometry and source links together. |

## Run

Use the [pipeline's Python/GDAL environment](../../map-build/pipeline/README.md).
The tested package versions are in [`requirements.txt`](requirements.txt), with
native dependency versions in [`environment.yml`](environment.yml).
Set `NEON_DATABASE_URL` and an AWS credential profile outside the code. Then run:

```bash
PYTHONPATH=scripts/source-imports python3 -m watersheds.build_boundary \
  --recipe CONSTRUCTION_ID VERSION \
  --revision DECISION_REVISION \
  --r2-endpoint R2_ENDPOINT \
  --work-dir /absolute/path/to/worldatlas-work/inputs/source-imports
```

The command reads `atlas.structured_documents` and resolves exact source versions
through `atlas.source_assets`. A large provider file can reference ordered,
individually cataloged byte parts. Each download and the assembled file are
checked against their sizes and SHA-256 hashes.

The result updates `atlas.decision_mainland_boundaries` and its raw-source links
in one transaction. Existing notes and unrelated source relationships remain.
Region references and derived polygon hashes update in that same transaction.
A failed calculation or invalid join leaves the existing boundary unchanged.
This command does not publish a website.
Its receipt records catalog lookup, source verification, construction phases and
database-write times. R2 transfer time is reported separately; cached verification
and multipart reassembly count as source processing.

The current construction IDs are `caucasus-boundary-construction` and
`ural-boundary-construction`, both version `2`. Their geographic choices and
exact source versions are in `atlas.structured_documents`.

## Construction settings

The record's method is `watershed_boundary`. It contains:

- `boundary_id` and `basis`: the editable boundary and a plain-language explanation.
- `sources`: local aliases for exact catalog source IDs and versions.
- `lines`: selected shapefile vertices, GeoJSON features, OSM ways or river relations.
- `terrains`: primary and secondary sources, height conversion, analysis domains,
  drainage groups, waterway references and the group pairs whose divides are needed.
- `sections`: the final ordered source lines, calculated divides, drainage paths
  or explicit geodesic connectors.
- `joins`: geographic anchors for choosing actual intersections between sections.
- `start` and `end`: source endpoints, selected intersections or explicit geographic points.

Optional `evidence_sources` name catalog records supporting geographic review.
They are linked to the boundary but are not downloaded during construction.
Files read by the calculation belong in `sources`.

Source basin values identify drainage groups; unknown drainage has its own value,
`-1`. Group IDs need not be consecutive. A group can contain several source basins.
Use `waterway_groups` for explicitly identified downstream ways; otherwise natural
networks are traced to their source-backed exit basins. Unassigned, ambiguous and
incomplete networks are reported.
If source evidence establishes that a mapped way points upstream, list its ID in
`reverse_waterways`. The constructor reverses its direction before tracing the
network; its coordinates and source version stay unchanged. Keep the supporting
measurements and reason in the construction record.
The receipt lists unresolved and ambiguous ways in the analysis domains;
unrelated waterways elsewhere in a larger provider extract are excluded from
those lists. Counts refer to OSM ways, not distinct rivers or drainage groups.

Mapped rivers can continue through several estuary ways beyond the basin
polygons. Trace back through that uncovered geometry to the downstream-most
basin intersection on each path. Report the selected way, group and intersection.
Stop at an unselected or ambiguous source basin; a path without a source-backed
destination remains unassigned.

OSM inputs can be XML, ZIP archives of XML responses, or provider PBF files.
The PBF reader streams memberships and coordinates in two passes. Natural
drainage includes rivers and streams; full coordinates remain available for
geometry. Shared nodes and way endpoints preserve downstream connections without
turning every shape vertex into a separate graph junction. Raster seeding selects
intersecting ways without clipping their geometry or downstream relationships.

## Terrain and flow

Keep the primary grid's native cell alignment and valid heights. Fill missing
cells only from the selected secondary source, bilinearly aligned to that grid.
Add the cataloged height-reference offset before combining different height
systems. Reject any remaining missing or non-finite elevations.

Flow chooses the steepest downhill neighbor using WGS84 distances. This works for
geographic and projected source grids. Edge cells can flow inward; the edge alone
does not identify a drainage destination. Source basin polygons can identify an
exit when mapped natural waterways do not.

Depression filling creates a separate working surface up to each spill elevation.
Exact flat cells follow the priority-flood route to a reachable outlet. The source
heights remain unchanged. Known closed drainage destinations can be supplied as
`closed_sinks`, each with a source point and group ID. Canals and drains are
excluded from natural drainage; an explicitly selected geographic boundary can
still follow their source geometry.

For coastal terrain, `ocean_mask` selects provider mask sources and their ocean
codes. Read categorical masks with nearest-neighbor alignment. Stop drainage at
observed ocean cells and adjoining land outlets; do not route across flat sea
cells to an arbitrary crop edge. Basin identities classify the land outlets,
with mapped river destinations taking precedence. Unknown outlets stay unknown.

Check the chosen boundary against larger terrain domains when sources or
construction settings change. Once that comparison passes, reuse the validated
domains. An ordinary run does not perform an automatic crop-expansion search.

For overlapping calculation areas, a domain can specify `bounds` for its full
terrain context and `output_bounds` for the portion contributing divide edges.
Both are WGS84 rectangles. Use adjoining output areas and overlapping context;
this keeps inconsistent interfaces at calculation edges out of the assembled
graph. Larger-crop validation expands the context while retaining those output
areas and the native grid.
Domains may specify `crs` when their bounds and output areas are projected
rectangles. This avoids enlarging a native raster crop by converting its rectangle
to longitude and latitude and back. Source lookups and final coordinates still
use WGS84; elevation cells retain their original positions and values.

## Boundary assembly and tests

Construct the complete interface between selected drainage groups. Route between
actual source intersections using WGS84 edge lengths, including connected pieces,
branches and loops. Disconnected joins are reported rather than bridged.
Repeated consecutive source coordinates appear once in the final line; their
coordinates are unchanged.

A stream-head connection follows a real drainage path and adds a geodesic to the
exact selected source point. Its receipt records the connector length. The source
point need not fall in the cell traversed by raster drainage. Explicit connectors
are construction choices, assembled with the other sections in one pass.
This also supports a selected mapped junction where streams assigned to different
groups meet. Connect the divide to the exact source node; report that intended
contact separately from additional crossings along the stream. A shared mapped
node alone does not establish whether a physical bifurcation exists.

Where source grids have different native resolutions, a connector endpoint can
select the nearest divide corner to a geographic anchor:
`{"nearest_divide": "TERRAIN_NAME", "near": {"point": [longitude, latitude]}}`.
The constructor measures the connector and retains both native grids.

Tests beside these files cover terrain, flow, destinations, waterways, source
selection, graph paths, assembly and database writes. Run all source-import tests:

```bash
PYTHONPATH=scripts/source-imports python3 -m unittest discover \
  -s scripts/source-imports -p 'test_*.py'
```

Set `WORLDATLAS_TEST_DATABASE_URL` to a disposable PostgreSQL database loaded with
[`001_initial_schema.sql`](../../../database/migrations/001_initial_schema.sql)
to include actual SQL, source-link and rollback tests. Tests roll back their rows.

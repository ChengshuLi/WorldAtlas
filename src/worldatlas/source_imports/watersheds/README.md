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
| [`sources.py`](sources.py) | Read source GeoJSON lines, OSM ways and river relations. |
| [`boundary.py`](boundary.py) | Find connected divides and shared joins, then assemble the final line. |
| [`../atlas_sources/catalog.py`](../atlas_sources/catalog.py) | Resolve catalog versions and verify downloaded or multipart files. |
| [`../source_io.py`](../source_io.py) | Save boundary geometry and source links together; refresh assembled region checksums. |

The split follows the work: read source features, prepare terrain, calculate
drainage, then assemble the boundary. `build_boundary.py` connects those steps to
Neon and R2. `waterways.py` keeps river networks and basin polygons together
because both establish drainage destinations. Source reading does not join
separate features; that responsibility belongs to boundary assembly.
`__init__.py` marks the Python package and lets our test discovery find its tests.

## Run

Use the [pipeline's Python/GDAL environment](../../map_build/README.md).
The shared [project environment](../../../../environment.yml) pins both Python
packages and native libraries. It also provides the disposable PostgreSQL used
by tests and the packages needed by related pipeline checks in CI.
Set `NEON_DATABASE_URL` and an AWS credential profile outside the code. Then run:

```bash
worldatlas-import \
  --recipe CONSTRUCTION_ID VERSION \
  --revision DECISION_REVISION \
  --r2-endpoint R2_ENDPOINT \
  --work-dir /absolute/path/to/worldatlas-work/inputs
```

The command reads `atlas.construction_records` and resolves exact source versions
through `atlas.source_assets`. A large provider file can reference ordered,
individually cataloged byte parts. Each download and the assembled file are
checked against their sizes and SHA-256 hashes.

The result updates `atlas.decision_mainland_boundaries` and its raw-source links
in one transaction. Existing notes and unrelated source relationships remain.
Region references and derived polygon hashes update in that same transaction.
A failed calculation or invalid join leaves the existing boundary unchanged.
Database connections are open only while reading inputs or saving the result;
terrain calculation does not keep an idle cloud connection open.
This command does not publish a website.
Its receipt records catalog lookup, source verification, construction phases and
database-write times. R2 transfer time is reported separately; cached verification
and multipart reassembly count as source processing.

The current construction IDs are `caucasus-boundary-construction` and
`ural-boundary-construction`. Their versioned geographic choices and exact source
selections are in `atlas.construction_records`.

## Construction settings

The record's method is `watershed_boundary`. It contains:

- `boundary_id` and `basis`: the editable boundary and a plain-language explanation.
- `sources`: local aliases for exact catalog source IDs and versions.
- `lines`: one complete GeoJSON feature, OSM way or river relation per named line.
  Joining different source features belongs in `sections` with explicit joins.
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
networks are traced to their source-backed exit basins. Track destinations between
real junctions, independently of how the provider divides a river into way records.
An incoming section feeding two drainage groups retains both destinations.
Shared drainage is known information; an unknown destination has no known route.
Receipts identify shared sections by source way, node IDs and destination groups.
The saved boundary's `provenance.shared_drainage` retains those references in Neon.
Unassigned and incomplete networks are also reported.
Before terrain processing, check the rivers intersecting the analysis areas and
their downstream connections. If any route is unresolved, including one branch
of an otherwise known fork, stop with its way and node IDs. Fix the source data
or source-backed destination references and rerun. Two known destinations are
valid. Unrelated unresolved rivers elsewhere in a provider extract do not block
the calculation. Missing coordinates on a relevant river also stop the run.
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
The reader merges memberships from every input before filtering PBF coordinates,
so later sources can use points supplied by earlier files.
The PBF reader streams memberships and coordinates in two passes. Natural
drainage includes rivers and streams; full coordinates remain available for
geometry. Shared nodes and way endpoints preserve downstream connections without
turning every shape vertex into a separate graph junction. Raster seeding selects
intersecting ways without clipping their geometry or downstream relationships.

## Terrain and flow

Use the provider's 10 m ArcticDEM mosaics where available and Copernicus
GLO-30 elsewhere. Copernicus also fills missing ArcticDEM heights after height
conversion. Construction records select exact catalog versions and coverage.

Keep the primary grid's native cell alignment and valid heights. Fill missing
cells only from the selected secondary source, bilinearly aligned to that grid.
Add the cataloged height-reference offset before combining different height
systems. Reject any remaining missing or non-finite elevations.

Flow chooses the steepest downhill neighbor using WGS84 distances. This works for
geographic and projected source grids. Independent row blocks calculate the exact
distances across available CPU cores. Edge cells can flow inward; the edge alone
does not identify a drainage destination. Source basin polygons can identify an
exit when mapped natural waterways do not.

Depression filling creates a separate working surface up to each spill elevation.
Exact flat cells follow the priority-flood route to a reachable outlet. The source
heights remain unchanged. Known closed drainage destinations can be supplied as
`closed_sinks`, each with a source point and group ID. Canals and drains are
excluded from natural drainage; an explicitly selected geographic boundary can
still follow their source geometry. Apply a closed sink only in crops containing
it; report a sink outside every analysis crop instead of silently omitting it.

For coastal terrain, `ocean_mask` selects provider mask sources and their ocean
codes. Read categorical masks with nearest-neighbor alignment. Stop drainage at
observed ocean cells and adjoining land outlets; do not route across flat sea
cells to an arbitrary crop edge. Basin identities classify the land outlets,
with mapped river destinations taking precedence. Unknown outlets stay unknown.
If the basin polygons stop inland of that shoreline, follow the outlet's actual
incoming flow paths back to the first mapped river or source-covered cells.
Use their destination only when the references agree. Missing or conflicting
references remain unknown; an unconnected nearby basin supplies no destination.

Check the chosen boundary against larger terrain domains when sources or
construction settings change. Once that comparison passes, reuse the validated
domains. An ordinary run does not perform an automatic crop-expansion search.

For overlapping calculation areas, a domain can specify `bounds` for its full
terrain context and `output_bounds` for the portion contributing divide edges.
Both rectangles use WGS84 by default. Use adjoining output areas and overlapping context;
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
For shared drainage, both outer catchment edges remain possible routes. Do not
invent a divide through the interior of a catchment whose destinations are the
same on both sides. The existing connected-path selection chooses the route
between the declared joins; no upstream area is forced into one group.
Repeated consecutive source coordinates appear once in the final line; their
coordinates are unchanged.

A stream-head connection follows a real drainage path and adds a geodesic to the
exact selected source point. Its receipt records the connector length. The source
point need not fall in the cell traversed by raster drainage. Explicit connectors
are construction choices, assembled with the other sections in one pass.
This also supports a selected mapped junction where streams assigned to different
groups meet. List its source node in a divide section's ordered `via` points and
set `max_step_m` for the geodesic connections. Attachments are derived from the
current ordered divide, extending the replaced interval to enclose connector
crossings of that divide. Nearby overlapping connections retain their declared
point order. Source endpoints and coordinates outside the replaced intervals stay
unchanged. Receipts record the calculated attachments and lengths; attachment
coordinates are not stored settings to retune after a source changes.

The constructor checks the complete final line against the drainage reference
rivers before saving. A crossing through a river section fails the run. Contact
at a real fork, confluence or river endpoint is allowed; an arbitrary OSM record
split does not create an allowed contact. The same general checker runs in tests
and production, with no location-specific exemptions. Following a river along
its length is allowed. Receipts and Neon provenance record the check results.
A shared mapped node alone does not establish whether a physical bifurcation exists.

Where source grids have different native resolutions, a connector endpoint can
select the nearest divide corner to a geographic anchor:
`{"nearest_divide": "TERRAIN_NAME", "near": {"point": [longitude, latitude]}}`.
The constructor measures the connector and retains both native grids.
The same `nearest_divide` selection can start or end a boundary directly on a
divide; its grid-edge identity is retained for routing.

An explicit point endpoint cuts its source line at the nearest position and
retains the exact chosen endpoint coordinate. Use a geodesic section for a
deliberate connection between separated source sections.

Each test file covers a distinct responsibility:

| File | What it verifies |
| --- | --- |
| `test_terrain.py` | Native cell alignment, missing heights, secondary data and height conversion. |
| `test_drainage.py` | Flow directions, flat terrain, distances, known/shared/unknown destinations and cycles. |
| `test_waterways.py` | OSM versions and connections, missing routes, river seeds and the crossing check. |
| `test_basins.py` | Basin identities, source coverage and coastal outlet classification. |
| `test_sources.py` | Exact source-feature selection, archive access and river-relation order. |
| `test_boundary.py` | Connected routes, joins, geographic connections and final geometry. |
| `test_build_boundary.py` | The steps working together, early failures, database writes and rollback. |

Run all source-import tests:

```bash
python .github/scripts/run_tests.py --suite source_imports
```

The runner creates a disposable database for the SQL, source-link and rollback tests.

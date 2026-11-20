# Watershed boundaries

The watershed importer reads a construction record from Neon, downloads its verified raw files from R2, calculates drainage on the source elevation grid, and saves the complete boundary in Neon. The same code handles different boundaries. Geographic selections live in the construction record.

## Code

| File | Responsibility |
| --- | --- |
| [`build_boundary.py`](build_boundary.py) | Read settings, call the functions, and save the result. |
| [`terrain.py`](terrain.py) | Crop native grids and fill missing heights from real secondary data. |
| [`drainage.py`](drainage.py) | Calculate eight-neighbor flow and downstream destinations. |
| [`waterways.py`](waterways.py) | Read natural waterways and trace their drainage destinations. |
| [`basins.py`](basins.py) | Read provider basin polygons with GDAL and classify terrain outlets. |
| [`sources.py`](sources.py) | Select source lines and points and resolve the files needed by each reader. |
| [`boundary.py`](boundary.py) | Find connected divides and shared joins, then assemble the final line. |
| [`worldatlas.source_assets`](../../source_assets/README.md) | Resolve catalog IDs and verify downloaded or multipart files. |
| [`../shared/storage.py`](../shared/storage.py) | Validate and save geometry with its construction reference. |

The split follows the work: read source features, prepare terrain, calculate drainage, then assemble the boundary. The typed `watershed_boundary()` entry point in `build_boundary.py` declares the construction fields and connects those steps to Neon and R2. It uses source basin polygons and river networks to establish drainage destinations. Boundary assembly joins the selected source features and calculated sections. `__init__.py` marks the Python package and lets our test discovery find its tests.

## Run

Use the [pipeline's Python/GDAL environment](../../map_build/README.md). The shared [project environment](../../../../environment.yml) pins both Python packages and native libraries. It also provides the disposable PostgreSQL used by tests and the packages needed by related pipeline checks in CI. Set `NEON_DATABASE_URL` and an AWS credential profile outside the code. Then run:

```bash
worldatlas-import \
  --recipe CONSTRUCTION_ID \
  --r2-endpoint R2_ENDPOINT \
  --work-dir /absolute/path/to/worldatlas-work/inputs
```

The command reads `atlas.construction_records` and resolves exact source IDs through `atlas.source_assets`. A large provider file can reference ordered, individually cataloged byte parts. Each download and the assembled file are checked against their sizes and SHA-256 hashes.

The result updates `atlas.source_features` in one transaction. Its construction links to the raw inputs through `construction_sources`. Existing geographic relationships remain. A failed calculation or invalid geometry leaves the existing boundary unchanged. Map building validates the selected lines and joins against its current division scope. Database connections are open only while reading inputs or saving the result; terrain calculation does not keep an idle cloud connection open. This command does not publish a website. The JSON result reports catalog lookup, source verification, construction phases and database-write times. R2 transfer time is reported separately; cached verification and multipart reassembly count as source processing.

The current construction IDs are `caucasus-boundary-construction` and `ural-boundary-construction`. Their editable geographic choices and exact source selections are in `atlas.construction_records`.

## Construction settings

Set the record's method to `watershed_boundary`. Put the geographic reasoning and supporting measurements in its `basis` column. The construction arguments specify inputs to the calculation and catalog links for supporting evidence.

- `feature_id`: the ID of the editable boundary.
- `sources`: local file names mapped directly to catalog source-ID strings. Multipart inputs instead specify ordered source-ID strings in `parts`, the complete file's checksum, size and filename. There are no one-field wrappers.
- `lines`: one selector object per named line, such as `{"coast": {"source": "anapa", "way": 396539058}}`. Each selector identifies a complete GeoJSON feature, OSM way or river relation. Joining different source features belongs in `sections` with explicit joins.
- `terrains`: primary and secondary sources, height conversion, analysis domains, drainage groups, waterway references and the group pairs whose divides are needed.
- `sections`: the final ordered source lines, calculated divides, drainage paths or explicit geodesic connectors.
- `joins`: geographic anchors for choosing actual intersections between sections.
- `start` and `end`: source endpoints, selected intersections or explicit geographic points.

Optional `evidence_sources` is a list of catalog source-ID strings supporting geographic review. They are linked to the boundary but are not downloaded during construction. Files read by the calculation belong in `sources`.

The recipe groups source basin values by the side of the intended boundary they drain toward. For example, `groups = {"3": [41, 42], "100": [99]}` and `interfaces = [[3, 100]]` describe one divide between groups 3 and 100. The divide between basins 41 and 42 contributes no edges because they are in the same group. When HydroBASINS is selected, `MAIN_BAS` identifies the main basin containing the source polygon, so several polygons can have the same value.

Group IDs are local to the recipe. The value `-1` represents unknown drainage. Use `waterway_groups` for explicitly identified downstream ways. The constructor traces other waterways to their source-backed exit basins and tracks destinations between actual junctions. A section feeding two known groups retains both destinations.

When `basins` selects a Shapefile in a ZIP, GDAL opens the selected `.shp` member and reads its companion files inside the archive. The provider attribute named by `basin_attribute` supplies the IDs used in `groups`. Basin lookups for terrain exits and coastal land outlets are batched, with all basin matches retained for each cell.

Terrain readers also open selected ZIP members through GDAL. GeoJSON readers stream selected members through Python's ZIP library.

Before processing terrain, the constructor checks rivers that intersect the analysis areas and follows their downstream connections. Missing coordinates or an unresolved route stop the run with the relevant way and node IDs. This includes a fork with one known branch and one unresolved branch. Correct the raw data or the source-backed destination references and rerun. Unrelated waterways outside the analysis do not block construction.

If source evidence establishes that a mapped way points upstream, list its ID in `reverse_waterways` and record the supporting measurements and reason in the construction record. The constructor reverses the direction for tracing while preserving the way's coordinates and source ID.

The result includes the river-crossing check, shared sections with their source way IDs, node IDs and destination groups, and unresolved or ambiguous ways within the analysis domains. Counts are for OSM ways, which can each represent only part of a river.

Mapped rivers can continue through several estuary ways beyond the basin polygons. Trace back through that uncovered geometry to the downstream-most basin intersection on each path. Report the selected way, group and intersection. Stop at an unselected or ambiguous source basin; a path without a source-backed destination remains unassigned.

Pyosmium reads both OSM XML and PBF. ZIP members are unpacked to temporary files for the same streaming reader. For natural drainage, the reader merges way versions from all files before loading the node coordinates they reference. This lets a way use points supplied by another file. Natural drainage includes rivers and streams. Shared nodes and way endpoints preserve downstream connections without turning every shape vertex into a separate graph junction. Raster seeding selects intersecting ways without clipping their geometry or downstream relationships. The shared GDAL writer passes all lines in one Arrow batch, and GDAL marks each terrain cell they touch.

## Terrain and flow

Use the provider's 10 m ArcticDEM mosaics where available and Copernicus GLO-30 elsewhere. Copernicus also fills missing ArcticDEM heights after height conversion. Construction records select exact catalog assets and coverage.

Keep the primary grid's native cell alignment and valid heights. Fill missing cells only from the selected secondary source, bilinearly aligned to that grid. Add the cataloged height-reference offset before combining different height systems. Reject any remaining missing or non-finite elevations.

Flow chooses the steepest downhill neighbor using WGS84 distances. This works for geographic and projected source grids. Independent row blocks calculate the exact distances across available CPU cores. Edge cells can flow inward; the edge alone does not identify a drainage destination. Source basin polygons can identify an exit when mapped natural waterways do not.

Depression filling creates a separate working surface up to each spill elevation. Exact flat cells follow the priority-flood route to a reachable outlet. The source heights remain unchanged. Known closed drainage destinations can be supplied as `closed_sinks`, each with a source point and group ID. Canals and drains are excluded from natural drainage; an explicitly selected geographic boundary can still follow their source geometry. Apply a closed sink only in crops containing it; report a sink outside every analysis crop instead of silently omitting it.

For coastal terrain, `ocean_mask` selects provider mask sources and their ocean codes. Read categorical masks with nearest-neighbor alignment. Stop drainage at observed ocean cells and adjoining land outlets; do not route across flat sea cells to an arbitrary crop edge. Basin identities classify the land outlets, with mapped river destinations taking precedence. Unknown outlets stay unknown. If the basin polygons stop inland of that shoreline, follow the outlet's actual incoming flow paths back to the first mapped river or source-covered cells. Use their destination only when the references agree. Missing or conflicting references remain unknown; an unconnected nearby basin supplies no destination.

Check the chosen boundary against larger terrain domains when sources or construction settings change. Once that comparison passes, reuse the validated domains. An ordinary run does not perform an automatic crop-expansion search.

Each item in a terrain's `domains` is an object with `bounds` in `[west, south, east, north]` order, such as `{"bounds": [37.2, 44.5, 38.1, 45.1]}`. An optional `output_bounds` rectangle limits which edges the crop contributes. Both rectangles use WGS84 unless the domain sets `crs`. Use adjoining output areas and overlapping context to keep calculation-edge artifacts out of the assembled graph. Larger-crop validation expands the context while retaining those output areas and the native grid. Projected bounds avoid changing the extent through a round trip to longitude and latitude. Source lookups and final coordinates still use WGS84.

## Boundary assembly and tests

Construct the complete interface between selected drainage groups. Shapely finds intersections in batches and retains the original grid-edge IDs. SciPy finds the shortest connected route between the selected intersections using WGS84 edge lengths. The search includes branches and loops. Disconnected joins fail the construction. For shared drainage, both outer catchment edges remain possible routes. A catchment with identical destinations on both sides contributes no interior divide. The declared joins select the route without forcing the upstream area into one group. Repeated consecutive source coordinates appear once in the final line.

A stream-head connection follows a real drainage path and adds a geodesic to the exact selected source point. The result includes the connector length. The source point need not fall in the cell traversed by raster drainage. Explicit connectors are construction choices, assembled with the other sections in one pass. This also supports a selected mapped junction where streams assigned to different groups meet. List its source node in a divide section's ordered `via` points and set `max_step_m` for the geodesic connections. Attachments are derived from the current ordered divide, extending the replaced interval to enclose connector crossings of that divide. Nearby overlapping connections retain their declared point order. Source endpoints and coordinates outside the replaced intervals stay unchanged. The result includes the calculated attachments and lengths. The constructor recalculates the attachments on each run.

The constructor checks the complete final line against the drainage reference rivers before saving. At a point of intersection, it looks for water entering from one side and leaving on the other, including at confluences and across OSM way splits. A river endpoint or a tangent contact alone is allowed, as is following a river along its length. A fork explicitly selected by a source node in a divide section's `via` can be a shared-drainage contact when the mapped outlets on the two sides lead to the two drainage groups the divide separates. Record the evidence for selecting that fork in the construction's `basis`. The JSON result lists these forks as `shared_drainage_contacts`.

Where source grids have different native resolutions, a connector endpoint can select the nearest divide corner to a geographic anchor: `{"nearest_divide": "TERRAIN_NAME", "near": {"point": [longitude, latitude]}}`. The constructor measures the connector and retains both native grids. The same `nearest_divide` selection can start or end a boundary directly on a divide; its grid-edge identity is retained for routing.

An explicit point endpoint cuts its source line at the nearest position and retains the exact chosen endpoint coordinate. Use a geodesic section for a deliberate connection between separated source sections.

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

Follow the [database test setup](../../../../database/README.md#tests) to make PostgreSQL and `pg_jsonschema` available. Then run all source-import tests:

```bash
python .github/scripts/run_tests.py --suite source_imports
```

The runner creates a disposable database for the SQL, source-link and rollback tests.

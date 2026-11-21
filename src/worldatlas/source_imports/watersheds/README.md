# Watershed boundaries

The watershed importer uses elevation maps and rivers to find where water drains in different directions. For example, where one cell drains to group 3 and the cell next to it drains to group 7, the edge between them can become part of the boundary. The construction record in Neon names the files, groups, and places to join. The importer reads the verified files from R2 and saves the finished line in Neon.

## Use

Use the shared [project environment](../../../../environment.yml) for Python, GDAL and PostgreSQL. Set `NEON_DATABASE_URL` and configure R2 credentials as described in the [source-import instructions](../README.md). Then run:

```bash
worldatlas-import \
  --recipe CONSTRUCTION_ID \
  --r2-endpoint R2_ENDPOINT \
  --work-dir /absolute/path/to/worldatlas-work/inputs
```

The command reads `atlas.construction_records` and resolves exact source IDs through `atlas.source_assets`. A large provider file can reference ordered, individually cataloged byte parts. Each download and the assembled file are checked against their sizes and SHA-256 hashes.

The importer checks the joins and river crossings before saving the finished line to `atlas.source_features` in one transaction. The construction links to the raw inputs through `atlas.construction_sources`. A failed calculation or invalid geometry leaves the existing boundary unchanged. Map building uses the saved line when it divides the rule's scope. The JSON result reports catalog lookup, source verification, construction phases and database-write times. R2 transfer time is reported separately from cached verification and multipart reassembly.

The current construction IDs are `caucasus-boundary-construction` and `ural-boundary-construction`. Their editable geographic choices and exact source selections are in `atlas.construction_records`.

## How it works

### Construction settings

Set the record's method to `watershed_boundary`. Put the geographic reasoning and supporting measurements in its `basis` column. The construction arguments specify inputs to the calculation and catalog links for supporting evidence.

- `feature_id`: the ID of the editable boundary.
- `sources`: local file names mapped directly to catalog source-ID strings. Multipart inputs instead specify ordered source-ID strings in `parts`, the complete file's checksum, size and filename. There are no one-field wrappers.
- `lines`: one selector object per named line, such as `{"coast": {"source": "anapa", "way": 396539058}}`. Each selector identifies a complete GeoJSON feature, OSM way or river relation. Joining different source features belongs in `sections` with explicit joins.
- `terrains`: primary and secondary elevation sources, height conversion, analysis domains, the name of a drainage definition and the group pairs whose divides are needed.
- `drainage`: named definitions of basin sources, the provider field that identifies each basin, and how to group basins by destination. Each definition can also select waterways, correct their directions and supply known stream destinations.
- `sections`: the final ordered source lines, calculated divides, drainage paths or explicit geodesic connectors.
- `joins`: geographic anchors for choosing actual intersections between sections.
- `start` and `end`: the geographic points where the boundary begins and ends. Select coordinates, an OSM node, an intersection, or a divide corner.

When selecting an OSM river relation, give its relation ID and the member role, such as `main_stream`. The reader joins the ways at shared OSM nodes and starts the coordinate list at the endpoint with the lower node ID. To end the actual boundary at a particular OSM point, use a selector like `{"source": "river", "node": 241464871}`. The boundary assembler puts the selected section in order from its first join to its last join or endpoint.

Optional `evidence_sources` is a list of catalog source-ID strings supporting geographic review. They are linked to the boundary but are not downloaded during construction. Files read by the calculation belong in `sources`.

Each terrain selects one definition by name. For example, the Ural recipe's `arctic`, `copernicus`, and `spring` terrains all set `"drainage": "ural"`. They use different elevation settings and share the basin and stream choices stored once under `drainage.ural`. A terrain that needs different basin or stream data can select a different definition in the same recipe.

The drainage definition groups source basin values by where they drain. For example, `groups = {"3": [41, 42], "100": [99]}` puts basins 41 and 42 in group 3 and basin 99 in group 100. A terrain using that definition can set `interfaces = [[3, 100]]` to draw the divide between the two groups. The divide between basins 41 and 42 contributes no edges because they are in the same group. When HydroBASINS is selected, `MAIN_BAS` identifies the main basin containing the source polygon, so several polygons can have the same value.

Group IDs are local to the recipe. A stream’s group can come from the basin covering its outlet, or the recipe can name known destinations with `waterway_groups`. For example, if `A → B` reaches a fork at B and the two branches drain to groups 3 and 7, the stretch from A to B belongs to both groups. An unknown destination uses `-1` where the code needs a single label.

When `basins` selects a Shapefile in a ZIP, GDAL opens the selected `.shp` member and reads its companion files inside the archive. The provider attribute named by `basin_attribute` supplies the IDs used in `groups`. Basin lookups for terrain exits and coastal land outlets are batched, with all basin matches retained for each cell.

Terrain readers also open selected ZIP members through GDAL. GeoJSON readers stream selected members through Python's ZIP library.

Before processing terrain, the constructor checks rivers that intersect the analysis areas and follows their downstream connections. Missing coordinates or an unresolved route stop the run with the relevant way and node IDs. This includes a fork with one known branch and one unresolved branch. Correct the raw data or the source-backed destination references and rerun. Unrelated waterways outside the analysis do not block construction.

If source evidence establishes that a mapped way points upstream, list its ID in the drainage definition's `reverse_waterways` and record the supporting measurements and reason in the construction record. The constructor reverses the direction for tracing while preserving the way's coordinates and source ID.

The result includes the river-crossing check, shared sections with their source way IDs, node IDs and destination groups, and unresolved or ambiguous ways within the analysis domains. Counts are for OSM ways, which can each represent only part of a river.

The mapped river can continue out into an estuary after the basin outline ends. If the river runs `A → B → C` and leaves its basin at B, the code starts at C and works back to B. It records that point and the group there. If the first basin it reaches belongs to an unknown group, the route stays unknown.

Pyosmium reads both OSM XML and PBF. ZIP members are unpacked to temporary files for the same streaming reader. For drainage tracing, the reader uses ways tagged `waterway=river` or `waterway=stream`. It merges way versions across all files before loading the referenced node coordinates. This lets a way use points supplied by another file. Shared nodes and way endpoints preserve downstream connections without turning every shape vertex into a separate graph junction. Raster seeding selects intersecting ways without clipping their geometry or downstream relationships. The shared GDAL writer passes all lines in one Arrow batch, and GDAL marks each terrain cell they touch.

### Terrain and flow

Use the provider's 10 m ArcticDEM mosaics where available and Copernicus GLO-30 elsewhere. Copernicus also fills missing ArcticDEM heights after height conversion. Construction records select exact catalog assets and coverage.

Keep the primary grid's native cell alignment and valid heights. Fill missing cells only from the selected secondary source, bilinearly aligned to that grid. Add the cataloged height-reference offset before combining different height systems. Reject any remaining missing or non-finite elevations.

Flow looks at the eight neighboring cells and chooses the steepest drop per metre. For example, a 2 m drop over 10 m is steeper than a 3 m drop over 20 m. Distances are measured on WGS84 and calculated for several sets of rows in parallel. A cell at a crop edge can still drain inward. Where flow stops at the edge, a basin outline can supply the destination.

If the floor of a pit is at 3 m and water can first spill out at 5 m, the code uses 5 m for that cell in a working copy. On flat ground it follows the route it found out of the pit. Use `closed_sinks` to name places where water really stops inland, with a point and group ID for each. The builder applies a sink to the crops covering it and raises an error if none do. Canals and drains are available as explicit source lines for a boundary. Flow tracing uses ways tagged as rivers or streams.

For coastal terrain, `ocean_mask` selects provider mask sources and their ocean codes. Read categorical masks with nearest-neighbor alignment. Stop drainage at observed ocean cells and adjoining land outlets; do not route across flat sea cells to an arbitrary crop edge. Basin identities classify the land outlets, with mapped river destinations taking precedence. Unknown outlets stay unknown. If the basin polygons stop inland of that shoreline, follow the outlet's actual incoming flow paths back to the first mapped river or source-covered cells. Use their destination only when the references agree. Missing or conflicting references remain unknown; an unconnected nearby basin supplies no destination.

Check the chosen boundary against larger terrain domains when sources or construction settings change. Once that comparison passes, reuse the validated domains. An ordinary run does not perform an automatic crop-expansion search.

Each item in a terrain's `domains` is an object with `bounds` in `[west, south, east, north]` order, such as `{"bounds": [37.2, 44.5, 38.1, 45.1]}`. An optional `output_bounds` rectangle limits which edges the crop contributes. Both rectangles use WGS84 unless the domain sets `crs`. Use adjoining output areas and overlapping context to keep calculation-edge artifacts out of the assembled graph. Larger-crop validation expands the context while retaining those output areas and the native grid. Projected bounds avoid changing the extent through a round trip to longitude and latitude. Source lookups and final coordinates still use WGS84.

### Boundary assembly

Construct the complete interface between selected drainage groups. Shapely finds intersections in batches and retains the original grid-edge IDs. SciPy finds the shortest connected route between the selected intersections using WGS84 edge lengths. The search includes branches and loops. Disconnected joins fail the construction. For shared drainage, both outer catchment edges remain possible routes. A catchment with identical destinations on both sides contributes no interior divide. The declared joins select the route without forcing the upstream area into one group. Repeated consecutive source coordinates appear once in the final line.

A stream-head connection follows a real drainage path and adds a geodesic to the exact selected source point. The result includes the connector length. The source point need not fall in the cell traversed by raster drainage. Explicit connectors are construction choices, assembled with the other sections in one pass. This also supports a selected mapped junction where streams assigned to different groups meet. List its source node in a divide section's ordered `via` points and set `max_step_m` for the geodesic connections. Attachments are derived from the current ordered divide, extending the replaced interval to enclose connector crossings of that divide. Nearby overlapping connections retain their declared point order. Source endpoints and coordinates outside the replaced intervals stay unchanged. The result includes the calculated attachments and lengths. The constructor recalculates the attachments on each run.

Before saving, the constructor checks the complete line against the mapped rivers. A stream that touches the line and turns back to the same side passes. A stream that follows a calculated stretch and leaves on the opposite side counts as a crossing. If the recipe deliberately uses the river as the boundary, water can join and leave along that shared stretch. Direct crossings still count there. A mapped fork named in a divide section’s `via` can pass when its branches lead to the two groups being separated, one on each side. Explain why the fork was selected in the recipe’s `basis`. The result lists the approved contacts under `shared_drainage_contacts`.

Where source grids have different native resolutions, a connector endpoint can select the nearest divide corner to a geographic anchor: `{"nearest_divide": "TERRAIN_NAME", "near": {"point": [longitude, latitude]}}`. The constructor measures the connector and retains both native grids. The same `nearest_divide` selection can start or end a boundary directly on a divide; its grid-edge identity is retained for routing.

An explicit point endpoint cuts its source line at the nearest position and retains the exact chosen endpoint coordinate. Use a geodesic section for a deliberate connection between separated source sections.

## Code and tests

| File | Responsibility |
| --- | --- |
| [`build_boundary.py`](build_boundary.py) | Read settings, call the functions, and save the result. |
| [`terrain.py`](terrain.py) | Read just the needed rows and columns of a height map and fill gaps from another map. |
| [`drainage.py`](drainage.py) | Pick which neighboring cell water flows to and follow it to a known destination. |
| [`waterways.py`](waterways.py) | Read OSM rivers and streams and trace where they drain. |
| [`basins.py`](basins.py) | Use basin outlines to tell where water goes when it leaves a terrain crop or reaches the shore. |
| [`sources.py`](sources.py) | Select source lines and points and resolve the files needed by each reader. |
| [`boundary.py`](boundary.py) | Choose a connected route along cell edges and join it to the other boundary sections. |
| [`worldatlas.source_assets`](../../source_assets/README.md) | Resolve catalog IDs and verify downloaded or multipart files. |
| [`../shared/storage.py`](../shared/storage.py) | Validate and save geometry with its construction reference. |

Start with `watershed_boundary()` in `build_boundary.py` to follow the work in code. It reads the files, prepares the terrain, works out where water goes, and joins the boundary sections. Its typed arguments describe the construction fields that Neon checks.

Each test file covers a distinct responsibility:

| File | What it verifies |
| --- | --- |
| `test_terrain.py` | Native cell alignment, missing heights, secondary data and height conversion. |
| `test_drainage.py` | Flow directions, flat terrain, distances, known/shared/unknown destinations and cycles. |
| `test_waterways.py` | OSM versions and connections, missing routes, river seeds and the crossing check. |
| `test_basins.py` | Basin identities, source coverage and coastal outlet classification. |
| `test_sources.py` | Exact source-feature selection, archive access and river-relation order. |
| `test_boundary.py` | Connected routes, joins, geographic connections and final geometry. |
| `test_build_boundary.py` | The steps working together, shared and distinct drainage definitions, early failures, database writes and rollback. |

Follow the [database test setup](../../../../database/README.md#tests) to make PostgreSQL and `pg_jsonschema` available. Then run all source-import tests:

```bash
python .github/scripts/run_tests.py --suite source_imports
```

The runner creates a disposable database for the SQL, source-link and rollback tests.

# Map building

Map building turns raw coastline and inland-water files from R2 and geographic rules from Neon into a grid of assigned cells. For each cell, it determines the physical class, the geographic owner and the numeric code for that pair. The [release tools](../map_releases/README.md) package the completed grid with the viewer and legend.

## Use

Install the [project environment](../../../README.md#pipeline-code), set `NEON_DATABASE_URL` for the working database, and configure R2 credentials. Run from the repository root.

```bash
mkdir -p /absolute/path/to/worldatlas-work/runs
worldatlas-build \
  src/worldatlas/map_build/config.json \
  /absolute/path/to/worldatlas-work/runs/preview \
  --work-dir /absolute/path/to/worldatlas-work
```

The work directory holds the shared `inputs/` cache. Each new build needs a new output directory inside the work directory. Omitting the output argument selects `WORK_DIR/run`. After completion, open the run's `report.json` to find the final files and timings.

| Option | When to use it |
| --- | --- |
| `--divide PARENT_ID` | Select a parent and its required ancestors. Repeat for several parents. By default, divide all parents with rules in the frozen selection. |
| `--reuse-from PREVIOUS_RUN` | Start a new build using verified physical outputs. The builder can reuse a shorter, aligned northern grid, an unchanged parent division, or an unchanged land calculation after a water-only edit. |
| `--physical-from PREVIOUS_RUN` | Reuse the verified physical grid and calculate every geographic assignment with the current code. Use this when testing a rule-engine change. |
| `--resume` | Continue the same output directory with its saved selection, checkpoints, parent choices, comparison and reuse source. Resume accepts the saved options when repeated and rejects different choices. |
| `--selection INPUT_SELECTION.json` | Rebuild using saved geographic values. For a retained release, first [restore its inputs](../map_releases/README.md#restore-inputs) and use its configuration and captured code. |
| `--compare-release VERSION_OR_RC` | Compare with an official version or numbered candidate from the release catalog. This option also needs database and R2 access for the comparison. |

The first attempt caches the decoded comparison streams and any category mapping, and records their checksums. Resume uses the same files even if the comparison preview has since been retired.

### Exact physical rasterization

The project environment provides GDAL 3.10.3, its Python bindings and PROJ 9.6.0. For byte-identical physical rasterization, build that GDAL library with `-ffp-contract=off`. A stock prebuilt library may round a raster boundary differently. Install CMake 3.16 or newer, a C/C++ compiler and Git separately; they are setup tools, not pipeline runtime dependencies. Then run once inside the project environment, choosing an absolute work directory:

```bash
export WORLDATLAS_WORK=/absolute/path/to/worldatlas-work
mkdir -p "$WORLDATLAS_WORK/runtime"
git clone --depth 1 --branch v3.10.3 https://github.com/OSGeo/gdal.git \
  "$WORLDATLAS_WORK/runtime/gdal-source"
cmake -S "$WORLDATLAS_WORK/runtime/gdal-source" \
  -B "$WORLDATLAS_WORK/runtime/gdal-build" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$CONDA_PREFIX" \
  -DCMAKE_INSTALL_PREFIX="$CONDA_PREFIX" -DCMAKE_INSTALL_LIBDIR=lib \
  -DCMAKE_INSTALL_RPATH="$CONDA_PREFIX/lib" \
  -DCMAKE_C_FLAGS=-ffp-contract=off -DCMAKE_CXX_FLAGS=-ffp-contract=off \
  -DBUILD_TESTING=OFF -DBUILD_APPS=OFF \
  -DBUILD_PYTHON_BINDINGS=OFF -DBUILD_JAVA_BINDINGS=OFF -DBUILD_CSHARP_BINDINGS=OFF
cmake --build "$WORLDATLAS_WORK/runtime/gdal-build" --parallel
cmake --install "$WORLDATLAS_WORK/runtime/gdal-build"
python3 -c 'from osgeo import gdal; print(gdal.VersionInfo("RELEASE_NAME"))'
```

This replaces the environment's native GDAL library; its existing Python bindings use the same ABI. Do not point `DYLD_LIBRARY_PATH`, `LD_LIBRARY_PATH`, or `PROJ_DATA` at a different installation. Reinstalling the Conda GDAL package replaces this custom build. See the [GDAL build guide](https://gdal.org/en/stable/development/building_from_source.html). Use `--reuse-from` to reuse verified physical outputs.

## How it works

### Inputs

- [`config.json`](config.json) chooses the grid, raw physical inputs, coastal distance and execution settings. The checked-in grid has 131,072 columns and 54,613 rows. Longitude wraps at the antimeridian. Cell centres sit half a cell in from their raster edges.
- [`inputs/selection.py`](inputs/selection.py) reads working records in one repeatable-read, read-only transaction. `input-selection.json` contains actual geometry coordinates and rules, entity hierarchy and category bindings, contributing construction records, and raw-source catalog entries. The transaction closes before downloads or grid processing.
- The `land_config`, `water_config` and `raw_manifest` inputs select the global coastline polygons and complete inland-water shard set. They support inline requests, local file pins, cataloged R2 references and selected ZIP members. `physical_controls.source_staging` supplies the R2 endpoint. The builder verifies the raw files against their pinned sizes and checksums. [Source imports](../source_imports/README.md) have already saved the geometry for boundaries, scope areas and reference points in Neon.

### From source files to cells

| Stage | Reads | Produces |
| --- | --- | --- |
| Prepare | Build configuration and working Neon records or a saved selection | Frozen geography and resolved physical requests. Inland-water downloads can happen during the next stage. |
| Build the physical grid | Coastline polygons, inland-water polygons and the grid definition | Coastline mask, per-shard water masks, their union and the final land/water grid. A cell is land when the coastline mask includes it and the inland-water mask leaves it dry. |
| Divide each parent | Physical grid, exact parent membership, child entities and geographic rules | Ownership by entity ID. Start at World. For deeper divisions, replace only the cells previously assigned to that parent. |
| Encode | Deepest assigned entity, physical class and category bindings | Map codes in the final row-run streams and counts by code. A mixed entity has separate codes for its land and water. |
| Verify and compare | Final streams, source pins and optional comparison streams | Completed build report and, when requested, changed intervals and transition counts. |

### Inside one parent division

A rule can select polygons and physical connected components within its parent. Multiple selectors form a union. With neither selector, use the parent. The geometric scope determines where boundary lines divide the domain. Physical class and `unassigned_only` constrain the cells the rule can claim. In component mode, a polygon selects the whole component when it covers more than half its cells. A division in component mode assigns the whole component to the child labelling the single face that contains more than half of its cells.

| Order | Rule operations | Calculation |
| --- | --- | --- |
| 1 | Explicit `assign_area` and `divide_area` | Apply area and boundary rules. Area rules name one child. Boundary rules cut the scope and use points to label the resulting faces. |
| 2 | Land or mixed `assign_area` and `divide_area` with `unassigned_only` | Fill scoped gaps using the ownership produced so far, when configured. |
| 3 | `nearest_land` | Assign remaining land components by their shortest distance to eligible reference shores. Reference points identify the components whose physical shores supply the distances. Check complete land coverage. |
| 4 | `nearest_coastal_water` and `nearest_basin_water` | Assign coastal water within 22,224 m in the current config. For each named basin, discover eligible owners on shores bordering the full basin, then use the physical shores of those owners. Both operations see the same land ownership and must agree on overlapping claims. |
| 5 | Water `assign_area` and `divide_area` with `unassigned_only` | At World, four area rules claim residual water in their S-130 ocean polygons. Explicit `connected_to` points restrict each claim to residual-water components that contain at least one of the rule's points. |
| 6 | `nearest_water` | Assign the remaining scoped water using eligible assigned physical shores. At World, this completes pockets left by the ocean rules. Check complete parent coverage. |

Rules in a group read one ownership snapshot and can run in parallel. Consolidation rejects different owners for the same cell or an owner incompatible with its physical class. A physical shore is a land cell with a water neighbor on one of its four edges. Distances use WGS84 and cell centres. The smaller computed distance wins. Exact equality follows category-code order. See the [division guide](division/README.md) for scope preparation and the [water guide](water/README.md) for how searches prove that they found the nearest shore.

### Reading the output

The physical, ownership and final layers use row-run streams. `rows.u32le` gives each row's starting offset in the run array plus an ending offset. Each pair in `runs.u32le` gives an exclusive ending column and a value. For example, `(3, 17), (5, 1)` on a five-column physical row means columns 0 through 2 are land and columns 3 through 4 are water. Ownership layers store entity IDs and use zero outside their assignments. The final layer stores map codes.

| File or directory | Contents |
| --- | --- |
| `request.json`, `input-selection.json`, `run-identity.json` | Build configuration, frozen Neon values and exact run inputs. |
| `configs/`, `physical/` | Generated physical requests and local physical-stage products. The run report points to any reused physical grid. |
| `division/parent-ID/` | Parent definition, result receipt and any local calculation layers. Reused results can point to an earlier run. |
| `report.json` | Final file paths, hashes and stage timings. Follow `final.report.path` to the counts by map code. |
| `comparison/` | Optional comparison summary in `report.json` and exact changed spans. Comparisons use entity ID and physical class when both mappings are available. Bare streams compare numeric codes. Removed southern rows are counted separately. |
| `checkpoints/`, `logs/`, `failure.json` | Completed receipts, logs and failure details for interrupted runs. |

`timing-events.jsonl` records stage, rule and checkpoint events. The build report summarizes wall time by stage and measures downloads separately. Concurrent work contributes overlapping time once to each stage total. When an interruption loses an endpoint, the report marks that time incomplete and records a lower bound. Time between attempts is excluded.

Each attempt saves its WorldAtlas source and setup files in `attempts/ATTEMPT_ID/source-code.json.gz` and pins the archive in its producer record. Keep the code stable within each attempt. Resume records the code for the new attempt and verifies the saved inputs and completed outputs. [Release staging](../map_releases/README.md#archived-code) includes those snapshots in the release archive.

To stop a build, interrupt it with Ctrl+C. A failed rule also requests cancellation for its group. Queued rules skip computation and running workers check for cancellation between batches. Completed checkpoints remain available to resume.

## Code and tests

Start at [`build.py`](build.py), where `main()` creates a `Pipeline` and `run()` calls each stage. Follow the subsystem guides for individual files.

| Area | Where to read |
| --- | --- |
| Input selection | [`inputs/`](inputs/README.md) reads [`geography.sql`](inputs/geography.sql), freezes rules and sources, and resolves comparison releases. |
| Physical | [`physical/`](physical/README.md) runs coastline, water shards, union and composition. [`crop.py`](physical/crop.py) handles aligned physical prefixes. |
| Hierarchy | [`division/hierarchy.py`](division/hierarchy.py) selects parents, checks reuse and substitutes child outputs. |
| Rule execution | [`division/`](division/README.md) compiles rules, prepares scopes, computes and consolidates claims, and encodes the final cells. |
| Land | [`land/`](land/README.md) builds physical components and performs complete nearest-reference searches. |
| Water | [`water/`](water/README.md) indexes shores, checks basin participants and shares proven distance bounds across cells. |
| Core | [`grid.py`](core/grid.py) defines cell coordinates. [`rle.py`](core/rle.py) and [`layers.py`](core/layers.py) read and write layers. [`geometry.py`](core/geometry.py), [`wrapping.py`](core/wrapping.py) and [`partition.py`](core/partition.py) rasterize areas and divide faces. [`distances.py`](core/distances.py) measures distances between runs. [`comparison.py`](core/comparison.py) locates changes. |
| Execution | [`runtime.py`](execution/runtime.py) manages checkpoints, pins and timing. [`control.py`](execution/control.py) carries cancellation and logging. [`code_archive.py`](execution/code_archive.py) captures and restores code. |
| Review | [`assignment_report.py`](land/assignment_report.py) shows area-based component selections. [`basin_images.py`](review/basin_images.py) renders comparisons from completed grids and a supplied basin mapping. |

Run the suite from the repository root after the [database test setup](../../../database/README.md#tests).

```bash
python .github/scripts/run_tests.py --suite map_build
```

[`test_end_to_end.py`](test_end_to_end.py) exercises import, physical rasterization, division and encoding on a small grid. [`test_resume.py`](test_resume.py) checks saved inputs, checkpoints and changed files. Subsystem tests cover wrapping, face labels, competing claims, component membership and exact distance searches, including independent reference comparisons. Tests use local fixtures and disposable PostgreSQL.

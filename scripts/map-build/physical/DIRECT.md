# V8 physical stage

This stage produces the **physical land and water grid** consumed by the
V8 pipeline. It rasterizes the pinned OSM land polygons and all selected
Overture GeoParquet shards. It then unions the water masks, subtracts them
from the land mask, and encodes the resulting dry mask as physical runs.
Historical rasters and label streams can be supplied for validation.

Grid for this project: width 131072, height 54614, west -180°, north 90°, step 360/131072°, rows north-to-south, EPSG:4326. Physical rows are little-endian uint32 offsets, one per row plus terminal offset, into little-endian `(exclusive_end_column, code)` uint32 pairs. Every row covers the full width. Physical code 17 means dry land, 1 means water. Consumers must use the streams' recorded SHA-256 hashes. Continent assignment and component generation are separate stages.

## Orchestrated run

`build_physical.py PIPELINE_CONFIG NEW_OUTPUT_DIRECTORY` wires the four stages below from hash-pinned input configs and the complete raw shard manifest. Copy `pipeline-config.example.json` and replace all placeholders. References are optional; the same stage isolation, hash checks and free-space reserve apply. `max_parallel_shards` sets the requested number of concurrent water-shard workers. The current example uses 3 based on a complete 32-shard run on the full grid; choose a count that fits available disk and CPU, and leave headroom beyond the configured disk reserve. `union_rows_per_block` and `physical_rows_per_block` set raster read/write band sizes; 512 aligns with the output TIFF tile height. The pipeline report records each tuning value and generated hashes. Run `python -m unittest -v test_build_physical.py` for the small raw-source end-to-end test.

## Reproducible steps

Requires Python 3, NumPy, GDAL/OGR Python bindings with GEOS, the GeoTIFF, Memory vector and raster drivers, and PyArrow Parquet support. The proven setup is Python 3.13.5, NumPy, GDAL 3.10.3, GEOS 3.13.1 and PyArrow 26.0.1. Use the same versions when byte-for-byte reproducibility matters. Disk requirements are substantial; each stage stops if the configured free-space reserve is crossed. Output directories must be new, outside all input directories, and must not contain inputs. A failure can leave partial output without a success report; preserve it until disposal is authorized.

1. Copy `land-config.example.json`, specify each land dataset and **all** sidecars as explicit path/SHA-256 pins, and explain provenance/selection in `selection_notes`. V8 uses the November 3, 2026 OSM coastline capture. `where: null` deliberately selects all features. Run `python rasterize_land.py CONFIG NEW_OUTPUT_DIRECTORY`. The builder verifies hashes before and after, requires EPSG:4326, valid non-empty polygon geometries, and does not repair or reproject. It writes `land.tif` and report. GDAL polygon defaults apply with ALL_TOUCHED off.
2. Copy `overture/config.example.json` and pin a reviewed water policy and grid. For each **raw** Overture GeoParquet shard, run `python overture/rasterize_water_shard.py SOURCE SOURCE_SHA256 CONFIG NEW_OUTPUT_DIRECTORY`. The `batch_size` setting (default 8192; current full-source benchmark uses 32768) controls Arrow row batches. `--batch-size` overrides the config for a direct run. The rasterizer validates each selected geometry once and reuses its OGR object across tile burns. Each report binds raw digest, policy, grid, batch size and output digest; unclassified or invalid selected geometry marks it incomplete. Do not union an incomplete shard. This implementation trusts Overture's inland-water subtype classification: it excludes `ocean` and `physical` subtypes, burns polygon/multipolygon geometry for all other nonempty subtypes, and applies no source or class filter. Missing subtypes fail completeness. The full subtype-based V8 replay matched all 32 selected water shard masks and both physical streams.
3. Copy `overture/aggregate-config.example.json`. Supply the hash-pinned complete raw-source manifest (`file_count` and `files` entries with `sha256`), each shard TIFF and its hash-pinned report. The code checks the manifest's distinct source hashes are covered exactly once, all shard outputs match their reports, grid and policy agree, and reports are complete. Run `python overture/aggregate_compare.py CONFIG NEW_OUTPUT_DIRECTORY`. `rows_per_block` (default 128; current full-source profile uses 512) controls aligned read/write blocks. It writes `water-union.tif` and report. The comparison reference is optional; adding `reference` with `path` and `sha256` records full-cell differences but does not alter the union. Raw source files are individually checked during step 2; retain the source manifest, reports, policy and durable source files for audit.
4. Copy `compose-config.example.json`; pin the two resulting mask TIFFs and describe provenance. Run `python compose_physical.py CONFIG NEW_OUTPUT_DIRECTORY`. `rows_per_block` (default 128; current full-source profile uses 512) controls the aligned mask blocks. The run stream is encoded in vectorized row blocks. It writes `physical-dry.tif`, `rows.u32le`, `runs.u32le`, and a report including grid, input pins, counts and output hashes. Optional validation can add **both** `reference_mask` and `reference_streams` (with `rows` and `runs`, each path and sha256); the builder checks consistency and emits every mismatch. Comparison does not determine or change the candidate.

Land rasterization builds a row-strip FID index during the existing geometry
validation pass. Random-readable layers then reread only envelope candidates
for each strip in source order; GDAL still burns the unchanged geometry. Drivers
without random feature reads use the original spatial-filter scan. Set
`feature_index: "scan"` in the land config for the reference path. No source
sidecars are created or changed. Physical composition converts binary values to
codes only for emitted runs, avoiding a full-grid integer code copy.

## Tests

`python -m unittest -v test_rasterize_land.py test_compose_physical.py`, then from `overture/`: `python -m unittest -v test_aggregate_compare.py test_rasterize_water_shard.py`

Synthetic tests cover polygon rasterization, source/digest checks, geometry and output isolation, stripe/batch behavior, report/manifest lineage, incomplete or inconsistent water shards, optional reference-free and reference-checked composition, run encoding and nonbinary masks. They do not establish real-world source correctness. Provision sufficient memory and disk for the full grid; these tools do not impose an application memory cap.

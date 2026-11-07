# Direct candidate physical stage

This isolated prototype produces **physical land versus water**, not continent labels or a released map. No historical/V2 raster or label data is needed to build it. A pinned OSM-style land polygon snapshot is rasterized to land; a complete pinned Overture GeoParquet shard set is rasterized as selected water, unioned, and subtracted from land. The resulting binary dry mask is encoded as physical runs. Reference comparisons are optional validation only.

Grid for this project: width 131072, height 54614, west -180°, north 90°, step 360/131072°, rows north-to-south, EPSG:4326. Physical rows are little-endian uint32 offsets, one per row plus terminal offset, into little-endian `(exclusive_end_column, code)` uint32 pairs. Every row covers the full width. Physical code 17 means dry land, 1 means water. Consumers must use the streams' recorded SHA-256 hashes. Continent assignment and component generation are separate stages.

## Orchestrated run

`build_physical.py PIPELINE_CONFIG NEW_OUTPUT_DIRECTORY` wires the four stages below from hash-pinned input configs and the complete raw shard manifest. Copy `pipeline-config.example.json` and replace all placeholders. References are optional; the same stage isolation, hash checks and free-space reserve apply. `max_parallel_shards` sets the requested number of concurrent water-shard workers. The current example uses 3 based on a complete 32-shard run on the full grid; choose a count that fits available disk and CPU, and leave headroom beyond the configured disk reserve. `union_rows_per_block` and `physical_rows_per_block` set raster read/write band sizes; 512 aligns with the output TIFF tile height. The pipeline report records each tuning value and generated hashes. Run `python -m unittest -v test_build_physical.py` for the small raw-source end-to-end test.

## Reproducible steps

Requires Python 3, NumPy, GDAL/OGR Python bindings with GEOS, the GeoTIFF, Memory vector and raster drivers, and PyArrow Parquet support. The proven setup is Python 3.13.5, NumPy, GDAL 3.10.3, GEOS 3.13.1 and PyArrow 26.0.1. Use the same versions when byte-for-byte reproducibility matters. Disk requirements are substantial; each stage stops if the configured free-space reserve is crossed. Output directories must be new, outside all input directories, and must not contain inputs. A failure can leave partial output without a success report; preserve it until disposal is authorized.

1. Copy `land-config.example.json`, specify each land dataset and **all** sidecars as explicit path/SHA-256 pins, and explain provenance/selection in `selection_notes`. The tested candidate used the November 3, 2026 OSM mirror, not the missing historical OSM snapshot. `where: null` deliberately selects all features. Run `python rasterize_land.py CONFIG NEW_OUTPUT_DIRECTORY`. The builder verifies hashes before and after, requires EPSG:4326, valid non-empty polygon geometries, and does not repair or reproject. It writes `land.tif` and report. GDAL polygon defaults apply with ALL_TOUCHED off. No claim is made that boundary/tie or antimeridian behavior matches historical code.
2. Copy `overture/config.example.json` and pin a reviewed water policy and grid. For each **raw** Overture GeoParquet shard, run `python overture/rasterize_water_shard.py SOURCE SOURCE_SHA256 CONFIG NEW_OUTPUT_DIRECTORY`. The `batch_size` setting (default 8192; current full-source benchmark uses 32768) controls Arrow row batches. `--batch-size` overrides the config for a direct run. The rasterizer validates each selected geometry once and reuses its OGR object across tile burns. Each report binds raw digest, policy, grid, batch size and output digest; unclassified or invalid selected geometry marks it incomplete. Do not union an incomplete shard. This implementation trusts Overture's inland-water subtype classification: it excludes `ocean` and `physical` subtypes, burns polygon/multipolygon geometry for all other nonempty subtypes, and applies no source or class filter. Missing subtypes fail completeness. The historical predicate is unknown. The earlier full-grid 674-cell comparison used a narrower provenance/class policy and has not been rerun with this policy.
3. Copy `overture/aggregate-config.example.json`. Supply the hash-pinned complete raw-source manifest (`file_count` and `files` entries with `sha256`), each shard TIFF and its hash-pinned report. The code checks the manifest's distinct source hashes are covered exactly once, all shard outputs match their reports, grid and policy agree, and reports are complete. Run `python overture/aggregate_compare.py CONFIG NEW_OUTPUT_DIRECTORY`. `rows_per_block` (default 128; current full-source profile uses 512) controls aligned read/write blocks. It writes `water-union.tif` and report. The comparison reference is optional; adding `reference` with `path` and `sha256` records full-cell differences but does not alter the union. Raw source files are individually checked during step 2; retain the source manifest, reports, policy and durable source files for audit.
4. Copy `compose-config.example.json`; pin the two resulting mask TIFFs and describe provenance. Run `python compose_physical.py CONFIG NEW_OUTPUT_DIRECTORY`. `rows_per_block` (default 128; current full-source profile uses 512) controls the aligned mask blocks. The run stream is encoded in vectorized row blocks. It writes `physical-dry.tif`, `rows.u32le`, `runs.u32le`, and a report including grid, input pins, counts and output hashes. Optional validation can add **both** `reference_mask` and `reference_streams` (with `rows` and `runs`, each path and sha256); the builder checks consistency and emits every mismatch. Comparison does not determine or change the candidate. No V2 continent labels enter this stage.

Land rasterization builds a row-strip FID index during the existing geometry
validation pass. Random-readable layers then reread only envelope candidates
for each strip in source order; GDAL still burns the unchanged geometry. Drivers
without random feature reads use the original spatial-filter scan. Set
`feature_index: "scan"` in the land config for the reference path. No source
sidecars are created or changed. Physical composition converts binary values to
codes only for emitted runs, avoiding a full-grid integer code copy.

`benchmark_physical.py land|compose CONFIG BASELINE_CHECKOUT NEW_OUTPUT --repeats 2`
times full inputs in alternating order against the baseline checkout, verifies
every mask pixel, and requires identical physical run bytes for composition.
`--discard-matching-outputs` removes only newly generated byte-identical grid
copies after verification, retaining reports, hashes and cleanup receipts.
The raw-water native kernel, dependencies and full-shard benchmark are documented
in [`overture/README.md`](overture/README.md).

Two alternating full-input comparisons on 2026-11-07 measured land rasterization
at 197.00 → 115.16 and 188.82 → 102.30 seconds (1.71–1.85×), and composition at
133.48 → 63.68 and 108.23 → 68.28 seconds (1.59–2.10×). The complete land TIFF,
physical TIFF and both physical streams matched the fresh baseline and sealed
full run byte-for-byte. The complete slowest raw-water shard improved
2.37–3.35×. These are separate stage/shard measurements, not a new complete
32-shard or end-to-end time. See the [pinned receipt](../../docs/benchmarks/physical-native-20261107.json).

`build.py` supplies strict shared pin, geometry, and optional reference utilities; it is not the entry point for the recommended flow. Mask outputs, reports, inputs and configs are all checked for change; the configuration itself is retained with outputs. Reports and comparisons do not prove geographic correctness or historical provenance. Explicit review of source selection and any differences remains necessary.

## Tests

`python -m unittest -v test_rasterize_land.py test_compose_physical.py`, then from `overture/`: `python -m unittest -v test_aggregate_compare.py test_rasterize_water_shard.py`

Synthetic tests cover polygon rasterization, source/digest checks, geometry and output isolation, stripe/batch behavior, report/manifest lineage, incomplete or inconsistent water shards, optional reference-free and reference-checked composition, run encoding and nonbinary masks. They do not establish real-world source correctness. Provision sufficient memory and disk for the full grid; these tools do not impose an application memory cap.

## Shard concurrency baseline

On 2026-11-04, two runs processed the first 20,000 rows from each of two real Overture shards on the full grid. Serial elapsed times were 2.526 and 3.641 seconds; two workers took 1.315 and 1.561 seconds. Sampled combined RSS was about 159–160 MiB serial and 305–309 MiB with two workers. Each corresponding mask matched byte-for-byte. The subsets came from Overture shard 22 and shard 13 and had SHA-256 values `90a10a4f5bc9042c56c2ea044a271b25c4bc6a57ca03c074f05d00cf49f05ffd` and `492d2d58ab4efb1cfafccde3dd015a4c04ef81119b8fdd4edf2a247cb8ffed10`. The run used Python 3.13.5, PyArrow 26.0.1 and GDAL 3.10.3 on a container reporting nine CPUs. Run order was reversed for the repeat, but cache and external load were uncontrolled. These subsets used the previous narrower water policy; they are not a complete release or a full-pipeline throughput guarantee; choose worker concurrency for available machine resources and benchmark the real workload.

## Complete-source timing profile

A 2026-11-06 full-grid profile used all 32 Overture water shards. Its download-excluded critical path was 2,436.81 seconds for the baseline and 1,909.69 seconds with three parallel shard workers, 32,768-row water batches, and 512-row union and composition blocks (21.6% less time). Land, union, final dry mask, and run-stream output hashes matched; 31 shard TIFFs matched byte-for-byte and the remaining shard matched every pixel but had different TIFF bytes. Cache, host load and staging effects were not controlled, so this is a measured profile, not a guaranteed speedup. Outputs remain candidates and require independent source and geographic review.

## R2 staging for a full physical run

`run_with_r2_staging.py` wraps the physical builder and fetches each missing
water shard from the R2 bucket and key in its hash-pinned source manifest.
Each entry must also provide the byte size. The wrapper checks the downloaded
bytes before running the unchanged rasterizer. It retains existing inputs and,
by default, downloaded shards. `--remove-completed-downloads` removes only
newly downloaded temporary copies after a matching complete shard report; failed
or partial downloads remain for inspection. Use an official installed Wrangler
entrypoint and authenticate separately; never put credentials in source files.
The staging log directory and pipeline output directory must be new and separate.
For example:

`python run_with_r2_staging.py PIPELINE_CONFIG NEW_OUTPUT --wrangler /path/to/wrangler/bin/wrangler.js --wrangler-config /path/to/wrangler.jsonc --log-dir NEW_LOG_DIR`

Run `python -m unittest -v test_r2_staging.py` for synthetic staging checks.
These do not test a real R2 connection or establish source selection, global
coverage, or equivalence to a published map. The exact local harness used in
the 2026-11-07 physical rerun is retained under `research-run-provenance/` for
provenance; its fixed environment paths make it non-portable.

### Continue after interruption

For a new output directory, `run_with_r2_staging.py` can copy completed land
and water checkpoints from `--reuse-checkpoint`, leaving the original run
untouched. Supply `--checkpoint-events`, `--checkpoint-land-report-sha256`,
`--checkpoint-land-code-sha256` and `--checkpoint-land-shared-code-sha256`.
It checks the land configuration, input sidecars, report and TIFF; each saved
water report is checked against its source and config pins, current rasterizer
hash, completion event and TIFF, then each copied file is rehashed. A present
but invalid checkpoint stops the run; only absent stages are run anew. Failed
partial R2 downloads must be preserved separately before restaging.

The prior land report does not itself attest which code bytes executed. The
land code hashes are operator-supplied assertions and matching them is not
independent proof of the earlier process. Record that limitation and the exact
wrapper, source, runtime and event pins in the resumed run's evidence.

The 2026-11-07 upstream rerun checkpoint is documented in
[`RERUN-20261107.md`](RERUN-20261107.md). Physical and component identity at
that checkpoint is not a complete final-map equivalence result.

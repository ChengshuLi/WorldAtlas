For the reference-optional direct physical stage, see [DIRECT.md](DIRECT.md).

# Experimental raw-to-physical mask builder

This is an isolated, configurable prototype, not the recovered historical builder and not a deployable replacement. It rasterizes selected EPSG:4326 polygon datasets in order: OSM-style land burns physical code 17 onto a code-1 water background, then selected inland-water polygons burn code 1. Outputs use little-endian uint32 row offsets and `(exclusive end column, physical code)` runs. The example grid is the V7/V2 grid: 131,072 × 54,614, west −180°, north 90°, step 360/131,072°; rows proceed north to south. The intended test is a full-grid comparison with the preserved physical mask, never a claim inferred from source names alone.

## Run

- Requires Python 3 with NumPy, GDAL/OGR Python bindings and GEOS. Driver availability depends on the GDAL build; Parquet support is required for native Overture input. An independently reviewed and hash-pinned source conversion may be necessary for Overture shards. Preserve and document the original bytes and conversion code, versions and filters too.
- Copy `config.example.json` outside any live artifact directory, replace **every** placeholder, add each selected input partition to `land` or `water`, and pin all input bytes. `where` is a GDAL/OGR attribute filter; set it to `null` only for deliberately preselected data or a deliberate all-feature selection. State selection rationale and uncertainty in `selection_notes`. Supply every shapefile sidecar, including `.shp`, `.shx`, `.dbf`, `.prj` and any other existing companion; all are hash-checked. Layer CRS must be EPSG:4326 and features must be valid nonempty Polygon/MultiPolygon; no implicit reprojection, geometry repair or feature filtering is performed.
- `python3 build.py /path/to/config.json /path/to/new-output-directory`. The directory must not already exist. Inputs are read-only and checked before and after. A failed/interrupted run can leave partial files, but does not write `report.json`; preserve or remove those partial files only with appropriate authorization. Successful output includes the exact config, streams and a report with runtime, feature counts and file hashes.
- Optionally replace the example reference placeholders with the preserved physical reference row/run paths and hashes. Remove the reference block when no comparison is needed. The builder validates every reference row, emits a count and **all** mismatched intervals in `mismatch-spans.jsonl`, and includes a small sample in the report. A zero mismatch supports physical-grid equivalence, not proof of historical source identity or correctness. Independently examine every mismatch and review its geographic meaning before replacement.
- Run tests: `cd scripts/v7-raw-mask && python3 -m unittest -v test_build.py`. Tests use synthetic GeoJSON and cover polygon selection, water subtraction, reference match and differences, input integrity, invalid geometry, output collision, multiple partitions and strip-size invariance. They do not verify the historic sources or full-grid performance.

## Explicit unresolved inputs and choices

1. The exact OSM land snapshot and all companion files are missing. The inventory records only the `.shp` SHA-256 `f1636460ab634d1f06a0bd72b957fbc8a8a85eabeabf5919f790573990ba0f33`, insufficient to pin a shapefile. The historical source URL, acquisition time and licensing details also need confirmation.
2. The raw Overture `2026-10-21.0` water release was downloaded and pinned. The current direct candidate follows Overture’s inland-water subtype classification; the historical builder’s exact predicate is unknown. See `DIRECT.md` and `overture/README.md` for the current method and limitations.
3. The historical builder and its geometry repair/invalidity policy, boundary-on-cell-center behavior, antimeridian handling, GDAL and dependent library versions, rasterization options and any processing simplifications are unknown. This prototype rejects invalid geometry, assumes input polygons already correctly handle the antimeridian and uses the GDAL default polygon rasterization (`ALL_TOUCHED` off). Boundary tie behavior must be characterized before calling it equivalent to an ideal point-in-polygon center test or the historical builder.
4. The earlier, narrower water policy was run and compared with the preserved physical streams, with 674 differing cells. The current subtype-only policy has not been run globally. End-to-end runtime and resource requirements remain unmeasured; the saved mask cannot by itself establish water-source decomposition.
5. This builds **only** physical land versus water. It does not reconstruct continent assignments, reviewed island or mainland-cut decisions, or later V2-to-V7 land changes. Those require independently pinned, reviewed geographic decisions and further verification.

## Overture water shard candidate

`overture/` contains a separate, configurable GeoParquet-to-water-mask experiment. It processes one hash-pinned shard at a time, records the selection policy and runtime, and reports invalid inputs. Separate union and composition stages produce a candidate physical mask; this does not assign continents or establish historical equivalence. See its README before use.

### Optional serial R2 staging

`build_physical.py` reads local shards when available. To stage missing
shards from R2, install `boto3`, set `max_parallel_shards` to `1`, and set
`source_staging` to `{"mode": "r2-s3", "endpoint_url": "https://<ACCOUNT_ID>.r2.cloudflarestorage.com"}`.
Each missing manifest entry needs its R2 bucket, key, byte size and SHA-256.
Use read-only R2 S3 credentials through the boto3 credential chain. The
pipeline verifies the size and SHA-256 before rasterization and removes
temporary downloads after their shard completes. It retains existing local
inputs and partial or failed downloads.

The physical stage writes `pipeline-identity.json` and an append-only `processing-events.jsonl` in its own output directory. If interrupted, run the same command with `--resume`. It verifies the original configuration, source and code identity and checks each completed land, shard, union and physical output before reuse. Incomplete files are moved into an `interrupted` directory for inspection; existing local source files are never removed. A partial downloaded source is preserved there; a complete matching download may be reused. A completed output can also be verified by a later `--resume` invocation. Never change an input or code file between attempts.

The report's `processing_elapsed_seconds` is the accumulated attempt wall time excluding serialized source downloads, when every attempt has a durable end event; `source_download_elapsed_seconds` is reported separately. If a process is killed without recording its end, `timing_complete` is false, `processing_elapsed_seconds` is null, and `recorded_processing_elapsed_seconds` is only a measured lower bound. A fresh uninterrupted timing run is required for an exact total in that case. Staging requires one shard worker so downloads do not overlap processing. Checkpoints and timing files survive process interruption only while the workspace itself survives; they are not remote backups.

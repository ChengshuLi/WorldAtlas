The [V8 pipeline](../pipeline/README.md) calls the
[direct physical stage](DIRECT.md) with the selected OSM coastline archive
and 32 Overture water shards. The standalone builder below also supplies
shared utilities used by that stage.

# Experimental raw-to-physical mask builder

The standalone builder rasterizes selected EPSG:4326 polygon datasets.
Land polygons burn code 17 onto a code-1 water background, and selected
inland-water polygons burn code 1. Outputs use little-endian uint32 row
offsets and `(exclusive end column, physical code)` runs. The V8 grid is
131,072 × 54,614, west −180°, north 90°, with a step of 360/131,072°.
Rows proceed north to south.

## Run

- Requires Python 3 with NumPy, GDAL/OGR Python bindings and GEOS. Driver availability depends on the GDAL build; Parquet support is required for native Overture input. An independently reviewed and hash-pinned source conversion may be necessary for Overture shards. Preserve and document the original bytes and conversion code, versions and filters too.
- Copy `config.example.json` outside any live artifact directory, replace **every** placeholder, add each selected input partition to `land` or `water`, and pin all input bytes. `where` is a GDAL/OGR attribute filter; set it to `null` only for deliberately preselected data or a deliberate all-feature selection. State selection rationale and uncertainty in `selection_notes`. Supply every shapefile sidecar, including `.shp`, `.shx`, `.dbf`, `.prj` and any other existing companion; all are hash-checked. Layer CRS must be EPSG:4326 and features must be valid nonempty Polygon/MultiPolygon; no implicit reprojection, geometry repair or feature filtering is performed.
- `python3 build.py /path/to/config.json /path/to/new-output-directory`. The directory must not already exist. Inputs are read-only and checked before and after. A failed/interrupted run can leave partial files, but does not write `report.json`; preserve or remove those partial files only with appropriate authorization. Successful output includes the exact config, streams and a report with runtime, feature counts and file hashes.
- Optionally replace the example reference placeholders with the preserved physical reference row/run paths and hashes. Remove the reference block when no comparison is needed. The builder validates every reference row, emits a count and **all** mismatched intervals in `mismatch-spans.jsonl`, and includes a small sample in the report. A zero mismatch supports physical-grid equivalence, not proof of historical source identity or correctness. Independently examine every mismatch and review its geographic meaning before replacement.
- Run tests: `cd scripts/map-build/physical && python3 -m unittest -v test_build.py`. Tests use synthetic GeoJSON and cover polygon selection, water subtraction, reference match and differences, input integrity, invalid geometry, output collision, multiple partitions and strip-size invariance. They do not verify the historic sources or full-grid performance.

## Selected inputs

The V8 configuration pins the November 3, 2026 OSM coastline archive and
the Overture `2026-10-21.0` water shards. The selected water policy uses
Overture’s inland-water subtype classification. See [the physical
stage](DIRECT.md) for the source layout and entry points.

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

The physical stages run through Python functions and the supported GDAL/OGR
Python bindings. No ctypes bridge, physical-stage compiler, custom native helper
or subprocess is required. See [the Overture water rasterizer](overture/README.md).

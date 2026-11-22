# Physical land and water

Rasterize the selected global coastline polygons and inland-water shards on the current grid. These large raw sources feed rasterization directly; they do not need a second copy as vector records in Neon.

## Use

The map builder passes the same `Grid` to the coastline and inland-water rasterizers. To run just the physical build, pass the generated `RUN/physical-build-config.json`. This file contains one top-level grid, the coastline inputs and settings, and the inland-water inputs and settings. The command creates the grid once from the file. Choose an output directory separate from the recorded source directory and supply R2 credentials for uncached remote inputs.

```bash
python3 -m worldatlas.map_build.physical.build \
  RUN/physical-build-config.json /absolute/path/to/new-physical-output
```

Use `--resume` after interruption. Completed land, water shards, union and composition are checked against their actual inputs and output hashes. Code changes are recorded as provenance and do not block resume. Partial calculation outputs are retained for inspection. The cache discards incomplete downloads.

## How it works

The final `physical/` directory contains `physical-dry.tif`, `rows.u32le`, `runs.u32le` and `report.json`. Physical streams use code 17 for land and code 1 for water. Entity assignments are calculated later using registry bindings.

R2 uses the normal boto3 credential chain, with credentials outside the code. The physical stage caches the coastline ZIP and extracts its required files before drawing land. It can download the next water file while rasterizing the current file. Verified water files stay in the shared input cache for the next build. The current 32 files take about 29 GB. The timing report includes both kinds of downloads and counts overlapping rasterization as processing. A build that reuses a completed physical grid skips both downloads.

## Code and tests

| File | Responsibility |
| --- | --- |
| `sources.py` | Check source files and coordinate references; open selected polygons. |
| `land.py` | Rasterize global coastline polygons. |
| `water.py` | Read GeoParquet water records and apply the selected inland-water policy. |
| `water_batch.py` | Validate and rasterize ordinary batches through GDAL's Python API. |
| `union.py` | Combine all water shards into one water mask. |
| `composition.py` | Subtract inland water from land and write the physical grid. |
| `build.py` | Connect the functions, stage missing R2 files, retain checkpoints and record timing. |

Tests beside the code exercise real small GeoJSON and Parquet inputs, equivalent rasterization paths, land/water composition, source integrity, checkpoint reuse, interruption and timing. The physical calculation uses Python APIs throughout.

Run the [map-building suite](../README.md#code-and-tests).

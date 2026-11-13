# Physical land and water

Rasterize the selected global coastline polygons and inland-water shards on the
current grid. These large raw sources feed rasterization directly; they do not
need a second copy as vector records in Neon.

The supported map command calls these Python functions directly. For a focused
physical build:

```bash
PYTHONPATH=scripts/map-build python3 -m map_build.physical.build \
  PIPELINE_CONFIG.json /absolute/path/to/new-physical-output
```

Use `--resume` after interruption. Completed land, water shards, union and
composition are checked against their actual inputs and output hashes. Code
changes are recorded as provenance and do not block resume. Partial outputs and
failed downloads are retained for inspection.

| File | Responsibility |
| --- | --- |
| `sources.py` | Check source files and coordinate references; open selected polygons. |
| `land.py` | Rasterize global coastline polygons. |
| `water.py` | Read GeoParquet water records and apply the selected inland-water policy. |
| `water_batch.py` | Validate and rasterize ordinary batches through GDAL's Python API. |
| `union.py` | Combine all water shards into one water mask. |
| `composition.py` | Subtract inland water from land and write the physical grid. |
| `build.py` | Connect the functions, stage missing R2 files, retain checkpoints and record timing. |

The final `physical/` directory contains `physical-dry.tif`, `rows.u32le`,
`runs.u32le` and `report.json`. Physical streams use code 17 for land and code 1
for water. Entity assignments are calculated later using registry bindings.

R2 uses the normal boto3 credential chain, with credentials outside the code.
Downloads are timed separately from processing. Missing inputs, invalid source
classification and inconsistent output coverage stop the build.

Tests beside the code exercise real small GeoJSON and Parquet inputs, equivalent
rasterization paths, land/water composition, source integrity, checkpoint reuse,
interruption and timing. The physical calculation uses Python APIs throughout.

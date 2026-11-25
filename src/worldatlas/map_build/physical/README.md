# Physical land and water

Rasterize the selected global coastline polygons and inland-water shards on the current grid. These large raw sources feed rasterization directly; they do not need a second copy as vector records in Neon.

## Use

The map builder passes its grid and resolved settings directly to the physical stages. It saves those settings in `RUN/physical-build-config.json` so you can run just the physical build. The standalone command reads that file and creates the grid once. Choose an output directory separate from the recorded source directory and supply R2 credentials for uncached remote inputs.

```bash
python3 -m worldatlas.map_build.physical.build \
  RUN/physical-build-config.json /absolute/path/to/new-physical-output
```

Press Ctrl+C to stop the standalone build. Its workers check for cancellation at safe points, just as they do in a full build. Use `--resume` after interruption. Completed land, water shards, union and composition are checked against their actual inputs and output hashes. Partial calculation outputs go to `preserved/` for inspection. The cache discards incomplete downloads.

The standalone command gets coastline and inland-water files through `SourceCache`. The saved configuration contains the R2 references and the cache location. A warm cache lets both builds reuse the files already on disk.

## How it works

The coastline rasterizer lists the polygon IDs that could touch each strip of map rows. GDAL fetches those polygons by ID when it draws the strip. Coastline sources must support direct lookup by feature ID.

For inland water, the builder skips the `ocean` and `physical` subtypes. The ocean is already represented by the coastline. Overture's `physical` records name features such as bays and straits, and can overlap the polygons used to fill water. A missing, blank, or non-text subtype leaves the shard incomplete. The builder draws valid polygons and multipolygons from the rows that pass this check. [Overture water guide](https://docs.overturemaps.org/guides/base/#water)

Both rasterizers use GDAL's default polygon fill, which selects cells by their centres. The water rasterizer combines polygons in batches, and its report records the tile width in cells as `tile_size`. The merge and composition steps read masks with one unsigned-byte band containing only 0 and 1.

For each water batch, the rasterizer reads and checks the selected shapes before drawing. It lists which shapes can reach each tile and keeps the original edges needed to draw that tile. It then updates the water mask one tile at a time.

The physical build saves one settings file per step under `configs/`. The coastline, water-shard, union and composition reports record the checksum of the settings they used. Each water task checks that it processed all rows. It identifies geometry problems by their zero-based row numbers in the original Parquet file. Invalid polygon rows are saved to `invalid-feature-rows.json` beside the shard report. Before merging the masks, the builder checks that every shard used the same rasterizer. After the merge, it verifies that the input files still match their checksums.

Each completed task has a receipt in the shared `checkpoints/` directory. Its receipt pins the task's inputs and outputs. The shared `timing-events.jsonl` records work and downloads. In a full build, both live at the run root alongside the receipts and timings for the other stages. In a standalone build, they live in its output directory. The standalone command prints timing with the grid report.

Both commands save the project code and setup files for each attempt in `attempts/{ATTEMPT_ID}/source-code.json.gz`. The matching `producer.json` records the archive checksum.

The physical build report's `directory` field points to the finished grid. That directory contains `physical-dry.tif`, `rows.u32le`, `runs.u32le` and `report.json`. Physical streams use code 17 for land and code 1 for water. Entity assignments are calculated later using registry bindings.

R2 uses the normal boto3 credential chain, with credentials outside the code. The physical stage caches the coastline ZIP and extracts its required files before drawing land. It can download the next water file while rasterizing the current file. Verified water files stay in the shared input cache for the next build. The current 32 files take about 29 GB. The physical report's `downloaded_shard_count` counts the water files downloaded during the attempt that saved the report. The timing report includes both kinds of downloads and counts overlapping rasterization as processing. A build that reuses a completed physical grid skips both downloads.

## Code and tests

| File | Responsibility |
| --- | --- |
| `sources.py` | Check source files and coordinate references; open selected polygons. |
| `land.py` | Rasterize global coastline polygons. |
| `water.py` | Read GeoParquet water records, apply the Overture subtype rules, and record the policy name in each report. |
| `water_batch.py` | Validate and rasterize ordinary batches through GDAL's Python API. |
| `union.py` | Combine all water shards into one water mask. |
| `composition.py` | Subtract inland water from land and write the physical grid. |
| `build.py` | `PhysicalBuild.run()` shows the order of the raster tasks. Each task uses the shared cache, checkpoints and timing tools. |

Tests beside the code check the raster cells produced from small GeoJSON and Parquet files. They also cover land and water composition, source integrity, checkpoint reuse, interruption and timing.

Run the [map-building suite](../README.md#code-and-tests).

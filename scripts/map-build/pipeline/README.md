# Build a map

The pipeline reads a saved selection of geographic records, creates the current
grid and writes a versioned map. Building does not publish the website.

## Run

Use the project environment on macOS or Linux. Set `NEON_DATABASE_URL` to the
working database and provide R2 credentials through the normal boto3 credential
chain, for example `AWS_PROFILE=worldatlas-r2`. Credentials stay outside code and
configuration.

```bash
PYTHONPATH=scripts/map-build python3 scripts/map-build/pipeline/run_pipeline.py \
  scripts/map-build/pipeline/config.json \
  /absolute/path/to/worldatlas-work/runs/preview \
  --work-dir /absolute/path/to/worldatlas-work
```

Create the `runs/` parent directory first. The work directory holds the reusable
`inputs/` cache; each build has its own output directory.

For identical physical inputs, add
`--physical-from /absolute/path/to/previous-run`. The pipeline verifies the
existing physical grid and reuses it. Geographic decision edits then require
land and water assignment, without another physical rasterization.

For consistent physical rasterization, use GDAL 3.10.3 and PROJ 9.6.0. Build GDAL
with `-ffp-contract=off` in both `CMAKE_C_FLAGS` and `CMAKE_CXX_FLAGS`; its Python
bindings must load that library.

## Inputs and stages

The configuration selects four working revisions: mainland, regional land,
named water and oceans. At startup, the pipeline reads them and their source
catalog references in one repeatable-read, read-only transaction. It saves that
selection and closes the transaction before downloads or computation.

Use `--selection /absolute/path/to/input-selection.json` to replay a saved
selection. Resume uses the run's saved selection rather than rereading Neon.
Source IDs and exact versions resolve through `atlas.source_assets`; downloads
are checked against the catalog's byte sizes and SHA-256 checksums.

The three physical inputs are `land_config`, `water_config` and `raw_manifest`.
They select the global coastline polygons and complete inland-water shard set.
They may contain inline JSON, local file pins, cataloged R2 references or selected
archive members. The endpoint is in `physical_controls.source_staging`.

The calculation is:

1. **Physical:** rasterize coastline and inland-water sources, then compose the
   physical land/water mask.
2. **Land:** build connected components, identify selected mainland groups,
   assemble mainland seeds and calculate WGS84 component distances. Apply
   explicit affiliations, geographic lines, island groups, direct satellites and
   scoped partitions during one final land composition.
3. **Water:** build one complete shoreline index. Assign coastal water first,
   then remaining selected basin water, followed by oceans and enclosed water.
   Basin participants come from current physical shores and final land.
4. **Comparison:** optionally compare every final cell with the release selected
   by `--compare-release VERSION` or explicit reference streams.

Geographic features are imported beforehand through the supported
[source imports](../../source-imports/README.md). Map building reads their saved
geometry rather than reopening those source archives. Large global physical
sources feed rasterization directly.

Implementation details are beside the code:
[physical](../map_build/physical/README.md), [land](../map_build/land/README.md),
[water](../map_build/water/README.md) and [input selection](../map_build/inputs/README.md).

## Outputs, resume and timing

`report.json` appears after the requested calculation and comparison succeed. It
points to the final streams and producer report; follow those paths rather than
assuming a fixed output subdirectory. Generated requests are in `configs/`;
phase receipts and failed attempts are retained under the run directory.

Continue an interrupted run with the same configuration and `--resume`. The
pipeline checks the actual saved inputs, grid and completed outputs. Code changes
are recorded as provenance and do not prevent reuse of compatible data.

Checkpoints retain completed physical units, components, mainland seeds, seed
indexes, distance assignments, regional land and the complete water calculation.
A producer with its own partial checkpoints can resume those units. Other partial
outputs are preserved before that phase restarts.

`timing-events.jsonl` records durable start/completion events. Stage totals use
elapsed wall-clock time, with overlapping child work counted once. Downloads are
reported separately. Reusing an earlier physical result charges this run's
verification time rather than the earlier run's processing or downloads.

Durations never subtract clocks from different attempts. Downtime between
attempts is excluded. If an abrupt interruption loses a completion event, the
report marks the affected timing incomplete and retains a measured lower bound;
it does not invent the missing duration. Run checkpoints and timing survive only
while their local files are retained.

Release staging and publication are separate from cell generation. Keep the
published release fixed while reviewing a numbered candidate. Publish only after
the user approves that candidate.

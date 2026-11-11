# End-to-end map build

`run_pipeline.py` is the supported single entrypoint from pinned raw OSM and
Overture inputs to the final WorldAtlas grid. It calls the ordinary repository
Python stage functions in one interpreter and generates each downstream request
from the files just produced. The standalone stage commands use the same entry
functions. The stages use GDAL’s Python bindings and boto3 for R2 reads. Compilers and
native kernels still run as external commands.
It does not call dated local coordinators, reuse old land/water output grids,
patch producer reports, relocate historical paths, or repair lineage sidecars.

The runner builds a local grid from the selected inputs. Publication is a separate workflow.

## Run

Use one Python installation with NumPy, SciPy, PyProj, GDAL/OGR, PyArrow,
boto3 and psycopg. The same command runs on macOS and Linux. The selected
regional PDF evidence reader needs Poppler's `pdftotext` on `PATH`.

For consistent rasterization, use GDAL 3.10.3 and PROJ 9.6.0.
Compile GDAL with `-ffp-contract=off` in both `CMAKE_C_FLAGS` and
`CMAKE_CXX_FLAGS` to preserve rounding in the tile coordinate transform.
The Python bindings must load that GDAL library. A minimal build needs the
GeoTIFF, ENVI, Shapefile and GeoJSON drivers.
[GDAL build instructions](https://gdal.org/en/stable/development/building_from_source.html)

The runner disables PROJ network access and checks the local `proj.db` against
the pin in the regional template. Set `NEON_DATABASE_URL` to a read-only
connection to the selected Neon database. Supply R2 credentials through a boto3
profile such as `AWS_PROFILE=worldatlas-r2` or the AWS credential environment
variables. The R2 endpoint is set in the configuration.

    python3 scripts/map-build/pipeline/run_pipeline.py scripts/map-build/pipeline/config.json \
      --work-dir /absolute/path/to/worldatlas-work

The checked-in configuration selects raw source IDs and versions. The runner
resolves them through `atlas.source_assets`, checks the catalog digest, and
verifies the R2 downloads against the selected sizes and checksums. It also
reads the pinned documents from `atlas.structured_documents` and verifies their
serialized bytes. `stored-json-text` preserves the stored JSON text.
`spaced-ascii` serializes sorted ASCII JSON with default spacing and a final
newline. Other documents specify their serialization in the configuration.

## Build from working mainland decisions

Set `NEON_DATABASE_URL` to the integration branch containing your working decisions and the published release records. Use a new output directory for each preview.

    python3 scripts/map-build/pipeline/run_pipeline.py scripts/map-build/pipeline/config.json \
      /absolute/path/to/worldatlas-work/run-v9-preview \
      --work-dir /absolute/path/to/worldatlas-work \
      --land-revision YOUR_REVISION

The runner saves the selected decisions in one read-only transaction and recalculates the
line and region checksums. It uses the revision’s source evidence, the configured
raw inputs and the selected regional and water decisions. The saved decisions and resolved input checksums are recorded with the run. Resume with the same arguments and `--resume` to reuse those exact inputs.

The preview compares with `v8.0` by default. Use `--compare-release VERSION` to
choose another map in `atlas.map_release_objects`. Read `comparison.json` for
the changed-cell count and category transitions.

`regional_revision` selects the working regional decisions in Neon. At the start
of a build, the runner reads that revision, its selected island rule, and its
current boundary in one transaction. It freezes them for this run; resuming
reuses that selection. The release catalog retains the frozen input records.
Editing a boundary therefore needs no manual snapshot export or config-pin edit.

`--work-dir` chooses and creates the local input/run directory, overriding
`input_root`; the configuration can omit that field when using this option.
The default output is `WORK_DIR/run`. An explicit output and `--resume` retain
their existing behavior. Source downloads and ZIP extraction happen within this
invocation, before processing; they are excluded from setup processing time.

Use one shared work directory for repeated builds. It holds the reusable
`inputs/` cache, while each build gets its own output directory, for example
`WORK_DIR/runs/RELEASE`. Create `runs/` before starting a build. Keeping inputs
at the work-folder level lets later builds reuse verified downloads.
If a cache moves, a link at its original path preserves access for completed
build records. File verification follows the link and checks the stored checksum.

A raw R2 input can use `{r2_source: {source_id: ..., version: ...}}`.
Setup looks up the selected raw versions in `atlas.source_assets` in one
read-only query. The `raw_catalog_sha256` config field pins the sorted result,
including each bucket, key, size, and checksum. The pipeline downloads and
verifies the bytes directly from R2.

A `sources` entry can also be a local `{path, sha256}` pin, an explicit R2
pin with `r2_bucket`, `r2_key`, `sha256`, and integer `size_bytes`, or
`{json: ...}` containing the ordinary stage document directly. A pinned Neon document uses
`{neon: {source_id: ..., version: ...}, sha256: ..., size_bytes: ...}`.
Inline stage documents can use the same
R2 pins in their dataset/static-file fields and nested `{json: ...}` file inputs.
For an OSM sidecar, use `{archive: R2_PIN, member: EXACT_ZIP_MEMBER, sha256: ...,
size_bytes: ...}`. Each archive and consumed member is independently checked.
Generated local paths and normal input documents stay inside the work directory;
the configuration requires no machine-specific source paths. In an inline regional
template, `bering_proj_db: {sha256: ...}` binds the active local PROJ database.
Raw-manifest shard entries retain the existing physical-stage R2 staging contract,
so they are not downloaded eagerly. Immutable source documents are never rewritten.
Keep structured decisions/configuration data in Neon or inline here, and R2 for
used raw sources and the final map. Credentials remain outside the configuration.
An inline document can declare its source `serialization` when exact original
byte identity matters. The water selection pins the named-water and ocean
exports separately and binds them to the land produced in the same run.

    python3 scripts/map-build/pipeline/run_pipeline.py \
      /workspace/selection/config.json /workspace/runs/fresh-run

For the first invocation, the output must be new. To continue a checkpoint-enabled
run after an interruption, use the identical configuration, code and runtime:

    python3 scripts/map-build/pipeline/run_pipeline.py \
      /workspace/selection/config.json /workspace/runs/fresh-run --resume

The runner takes an exclusive run lock and refuses to duplicate a still-running
runner or an external command still holding the run lock after interruption.
Temporary files are directed into `fresh-run/scratch`. No application memory cap, memory floor
or memory watchdog is added. Component construction runs directly without its
retired monitor/guardian wrappers. Existing stage disk reserves and source/output validation remain enforced.
Use a run path on the same filesystem as its generated component work.

## Configuration inputs

All `sources` are explicit `{path, sha256}` pins:

- `land_config`, `water_config`, `raw_manifest`: current raw physical-stage input
  contracts. The land config pins all required source sidecars. The raw manifest
  lists the complete official Overture shard set and, for missing local files,
  their R2 bucket, key, byte size and SHA-256. `source_staging` in
  `physical_controls` uses read-only S3 GETs against R2, never intermediate R2 writes.
- `land_snapshot`, `neon_selection`, `osm_receipt`: selected source/decision data
  and custody evidence consumed by the normal Stage 2 lineage validator. The
  runner binds the editable mainland selection to the physical grid from this
  run and verifies its three water closures against that grid.
- `resolution_template`: mainland witness/source selection data. Its source
  files are preserved; physical/component pins and current executable hashes
  are generated afresh. Historical output artifacts are not reused.
- `regional_template`: selected regional decision request and raw source versions.
  The editable regional revision exports through
  [export_regional.sql](../land/research-mixed-runtime/stage3-mixed-leeward-full-20261105/export_regional.sql).
  Supply the `revision` parameter on a read-only psycopg connection. A named-island
  decision uses the GeoNames record to find the physical component and links
  independent geographic evidence to the editable continent choice.
  The normal preparer validates the fresh Stage 2 artifacts and binds current
  code and preserves the template’s source policy.
- `water_snapshot.selected_water` pins separate editable named-water and ocean
  exports. The runner binds them to the mainland and regional land generated
  by the current run. `seavox_archive` supplies named-basin geometry, and
  `coastal_plan` supplies the full coastal tessellation. Every basin receives
  an independent raster-to-span coverage check before prefill. The selected
  ocean routes and seeds run once, followed by enclosed-water assignment.
  Ocean routes are imported from IHO S-130 using a
  [construction record in Neon](../../source-imports/iho/README.md). This selection
  leaves the named-sea inputs unchanged. Updating the ocean snapshot changes the
  next build; it does not alter an already published release.
- `reference_rows`, `reference_runs`: optional explicit full-grid reference pins,
  named `rows.u32le` and `runs.u32le` in one directory. The normal comparator
  checks every cell and fails the run if any differ. Reference equality is a
  regression check, not proof that geographic decisions are correct.

`basin_workers` controls basin concurrency; one independent coastal task runs
alongside that pool. Before those jobs, one SeaVoX extraction stage scans the
pinned archive for the complete selected feature set. It validates every bound
geometry and seals `extractions/batch-manifest.json`, retaining the identical
canonical per-decision `source.geojson` and ordinary extraction manifest used by
the basin builder. Completed batch checkpoints pin every emitted file; partial
attempts are preserved and regenerated, never treated as a reusable cache.
The standalone single-feature extraction CLI remains available for targeted work.
See [the complete extraction replay contract](../../../docs/implementation/seavox-extraction.md).

The coastal CLI generates independent tiles in parallel
using the available CPU count, or the explicit positive `coastal_workers`
setting (`1` selects serial execution). Tile threads share the sealed RLE mappings and read-only shoreline span index.
Each thread constructs its own crop-specific centers and distance trees. The parent alone
publishes durable tile checkpoints, in canonical tile order, and writes batch
completion only after every tile and metadata recheck succeed. These are
execution tuning controls, not memory limits. Account for the simultaneously
running basin pool when choosing explicit worker counts.

Shared basins use exact WGS84 two-dimensional rectangle certificates by default,
with complete point classification for unresolved centers. The standalone basin
builder retains `--research-interval` and `--pointwise-nearest` as reference engines. See [the nearest-shore certificate](../../../docs/implementation/named-sea-intervals.md).

## Stage, review, and publish a release

Give each geography worker a Neon branch from the same starting point and a
Git branch for any code changes. Keep each worker's database changes in a
reviewable SQL change set. Apply the reviewed changes to one integration Neon
branch, combine the pipeline and viewer changes in Git, and run the build
against the integration database. Keep the published site on its existing
release while reviewing the combined result.

The Worker serves staged and published files from R2. Deploy it with
`npx wrangler deploy` when its server code or configuration changes.
The release commands below stage and publish the viewer and map files.
They use the
candidate catalog defined in the [database schema](../../../database/migrations/001_initial_schema.sql).
Use a direct `NEON_DATABASE_URL` and an R2 profile with write
access to the map bucket. Pass the path to the combined viewer source from the
integration branch.

    python3 scripts/map-build/pipeline/manage_release.py stage v9.0-rc.1 \
      /absolute/path/to/worldatlas-work/run-v9-preview --viewer web/viewer

The command uploads a new immutable set of viewer and map files. It saves the
file hashes, the build configuration, and the exact build inputs in Neon.
The viewer config uses the build's pinned category bindings and points to
`legend/continents.json`. That generated file has one entry per entity with
its ID, name, color, and total cell count. Names come from the selected snapshot,
land colors come from Neon, and counts come from the completed grid report.
Land and water counts are added for each continent. All water uses the viewer's
shared water color. Both generated files are included in the candidate's file hashes.
Open `/v9.0-rc` for the most recently staged candidate or
`/review/releases/v9.0-rc.1/index.html` for that exact candidate. Build and
stage `v9.0-rc.2` if anything needs to change.

Once you’ve reviewed the exact candidate and the release changes are ready,
record approval and publish that candidate.

    python3 scripts/map-build/pipeline/manage_release.py approve v9.0-rc.1 --reviewer NAME
    python3 scripts/map-build/pipeline/manage_release.py publish v9.0-rc.1

Approval belongs to the candidate. The working geography stays editable.
Publication verifies all uploaded bytes, records both map streams in one Neon
transaction, then switches the homepage with one conditional R2 write. A
failed homepage write can be retried with the same candidate.

## Outputs and timing

`report.json` is created only after every requested stage and reference check
succeeds. It pins final rows, runs and producer report. Per-job logs are under
`logs/`; generated requests are under `configs/`. The final map is under `final/`.

`timing-events.jsonl` is an append-only, fsynced start/completion/heartbeat ledger.
Each invocation has its own attempt ID and monotonic intervals. Durations are
never computed by subtracting timestamps from different attempts or boots. The stage totals in `report.json` are wall-clock
processing elapsed seconds:

- Setup: initial source/configuration hashing, validation and run setup.
- Physical: the complete parent stage interval, including CLI startup and
  configuration generation, excluding the producer's measured source downloads. R2 staging must use one shard worker, so a download
  does not overlap other shard processing. Parallel already-local shards are
  measured by the producer's wall clock, not summed CPU/job durations.
- Mainland/islands: complete request preparation, component generation, Stage 2,
  regional handoff preparation, and the mixed/regional producer.
- Water: complete preparation, all parallel basin/coast work, assembly, prefill,
  ocean, enclosed water and final composition. Nested and concurrent intervals
  are counted once.
- Verification: final source/output hash verification and the optional
  full-grid comparison.

## Interruption and resume guarantees

Before reusing completed work, `--resume` checks the original request, all selected
source pins, current repository source code, Python/dependency versions, runtime
paths, every completed command's input pins, and every output file/hash. Completed
command receipts also seal timing-journal prefixes, so losing or changing prior
recorded intervals cannot silently yield a new complete total. Generated requests
must remain byte-identical. Land seed rasterization, component construction and
tile verification execute pinned checked-in Python implementations through proper
library APIs. Run directories contain no copied land compiler helpers. A changed
pin or a live prior stage stops resume.

The runner records stage admission and timing before the call. Native commands
launched through the runner inherit its filesystem lock. The pinned seed writer
has its own parent-exit guard. Cancellation stops tracked commands and skips
queued work. Python work already running in a thread can stop at a stage or tile
boundary.

The supported recovery granularity is:

- Physical: validated completed land, individual water shards, union, and final
  physical composition. The normal raw producer resumes the same output root.
- Mainland/islands: completed components and Stage 2 are sealed. Stage 2 resumes
  its normal checkpointed core after a durable derived manifest. Before that
  manifest, partial work is preserved and its source preparation is rerun.
- Water: completed basin extractions, basin assignments, independent coverage
  checks and downstream stages are reused. The coastal batch copies validated
  completed tiles from all preserved earlier coast attempts into fresh output.
- The first failed coast or basin future cancels queued work and stops other
  active stage commands, so a coastal failure cannot remain hidden behind all
  basin results.
- A leaf with no supported internal checkpoint is preserved under `preserved/`
  and rerun from its pinned inputs. Partial data are never relabeled as complete,
  overwritten in place, or deleted automatically.

Downtime between attempts is excluded. Active intervals within each attempt are
unioned, so concurrent work is counted once, and the attempt totals are added.
Physical source downloads are excluded by the normal physical producer's own
journal; completed-report verification is counted as new validation work rather
than charging an old download or invocation again.

A graceful interruption with durable endpoints can retain exact measured active
time, including processing spent on a failed attempt. An abrupt kill can leave
an unmatched interval. Only its last durable heartbeat/checkpoint prefix is known;
its tail is not guessed. Such a stage reports `timing_complete: false`,
`processing_elapsed_seconds: null` and a
`recorded_processing_elapsed_seconds` lower bound. A successfully resumed final
map can therefore have complete outputs but incomplete timing. Use a fresh,
uninterrupted run if an exact whole-stage baseline is required.

`recorded_processing_is_lower_bound` labels that distinction explicitly.
`interrupted_interval_details` retains each unmatched interval's start, last
durable heartbeat (or start when no heartbeat exists), measured prefix and
unknown tail. The measured prefixes remain included in the stage's recorded
total. Do not sum the detail entries: parent and concurrent child intervals can
overlap, while the reported stage total unions them once per attempt.
`unrecorded_interruption_tail_seconds: null` means the lost tail is unknown,
not zero. A one-second heartbeat cadence does not prove a one-second error
bound because scheduling or a stopped process can delay a heartbeat.

Every new `group-complete` journal record includes a durable `timing_summary`
for the entire stage across all recorded attempts. It has the same timing
fields as the final report, so a completed stage can be read before later
stages finish. A single resumed `stage-total` interval is only that attempt's
work and must not be presented as the whole stage's processing time.

These are wall-clock processing intervals, not CPU-time measurements. Ordinary
OS scheduling delays within a live invocation remain included. An external
suspension of the same running process is not a separate measured restart gap;
the runner does not infer an exact suspension duration from heartbeat silence.

Logs and failed attempts are retained. Atomic JSON publication leaves an
unreferenced pending file if a writer is killed; only the final filename is a
checkpoint. A torn timing-journal tail is preserved before recovering its valid
prefix. Older runs without this identity/checkpoint contract are not silently
adopted. Existing uncheckpointed runs must retain their original code; this update does
not migrate them.
Cloud recovery also requires retaining/restoring the run directory and pinned
inputs at their original paths; missing storage cannot be reconstructed from a
chat transcript.

## Tests

Set `TMPDIR`, `TMP` and `TEMP` to a persistent workspace directory before running
synthetic tests, since `tempfile` is also used by the test framework:

    mkdir -p /workspace/test-scratch
    TMPDIR=/workspace/test-scratch TMP=/workspace/test-scratch \
      TEMP=/workspace/test-scratch PYTHONPATH=scripts/map-build/water \
      python3 -m unittest discover \
      -v -s scripts/map-build/pipeline -p 'test_*.py'

Tests execute actual raw polygon/Parquet rasterization and Python component
production through direct Python stage calls. Another real-processing fixture
chains ocean partition, enclosed-water classification, final-plan validation
and composition, checking every cell of its final grid. Timing tests cover
parallel union, idle gaps, failures, changed monotonic clock origins, simulated
process interruptions, resumed output equality, torn journals, live-process
safety, pin corruption and acquisition separation. These focused
fixtures do not replace the global source-to-final acceptance run or establish
its elapsed time.

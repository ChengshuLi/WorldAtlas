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

Use one Python installation with NumPy, SciPy, PyProj, GDAL/OGR and PyArrow.
The same command runs on macOS and Linux. Install a C++17 compiler available as
`g++` and `c++`, OpenSSL development files, and Poppler's `pdftotext` on
`PATH`. If OpenSSL lives outside the compiler's search paths, add its include
and library directories with `CPATH` and `LIBRARY_PATH`. Use GDAL 3.10.3 and
PROJ 9.6.0 to match the original build's geometry runtime.
It enforces `PROJ_NETWORK=OFF` throughout the runner, disables pyproj's
network API, and records the active local `proj.db` path and SHA-256 in runtime
identity. A regional template's `bering_proj_db` must match that exact active
database. This runtime file alone may be outside `input_root`; other selected
source files must remain inside it.
If the Python installation needs a dependency directory on `PYTHONPATH`, export
that directory when launching. For R2 staging, install `boto3` into the same
Python environment and set `physical_controls.source_staging` to
`{"mode": "r2-s3", "endpoint_url": "https://<ACCOUNT_ID>.r2.cloudflarestorage.com"}`.
Use an R2 S3 token with Object Read only access to the source bucket. Supply
the access key ID and secret access key through `AWS_ACCESS_KEY_ID` and
`AWS_SECRET_ACCESS_KEY` or a boto3 credentials profile. Keep credentials outside
the configuration. For a build with all shards already local, omit
`source_staging`.

Existing Wrangler-based build configurations need the new `source_staging`
block and credentials for a fresh run.

Copy `config.example.json`, replace the source paths and SHA-256 values, and
choose an existing `input_root` containing the selected sources and the new run
location. A relative `input_root` resolves beside the configuration.
Relative top-level source paths resolve beside the configuration.
Nested source documents retain their own declared paths; materialize their
pinned source files at those locations before starting. No path-prefix rewriting
is supported.

For one configuration that pulls its selected inputs directly, run:

    python3 scripts/v7-pipeline/run_pipeline.py scripts/v7-pipeline/config.json \
      --work-dir /persistent/worldatlas-work

`config.json` contains the reconstructed selected research inputs. Structured
snapshots are pinned Neon records or inline values; R2 is used for raw inputs.
Set `NEON_DATABASE_URL` to the selected research database using a read-only role
and install `psycopg` in the same Python environment. It is never saved in the
configuration. The source reader opens a read-only transaction, checks the
catalog identity, and accepts a document only when all bytes match the selected
size and SHA-256. `jsonb-text` preserves PostgreSQL's JSONB text exactly, without
adding a newline; `spaced-ascii` reconstructs sorted ASCII JSON with default
separator spacing and one newline. The selected regional snapshot and Lydekker
line use those representations respectively. Other existing serializations are
unchanged. Structured documents are read directly from Neon, never copied from
R2 as a fallback. Missing or changed source bytes fail closed; an empty work
directory needs no manual source-cache seeding.

The original top-level configuration and coastal-plan bytes were not recovered.
This configuration preserves the recovered geographic choices, uses the unchanged
water-overlay producer and strict reference comparison, and declares a new
224-tile coastal execution partition with conservative halos. It is not a claim
of a new full global run, geographic acceptance, or verified final-grid equality.
The original regional pending inventory remains a diagnostic stand-in.

`--work-dir` chooses and creates the local input/run directory, overriding
`input_root`; the configuration can omit that field when using this option.
The default output is `WORK_DIR/run`. An explicit output and `--resume` retain
their existing behavior. Source downloads and ZIP extraction happen within this
invocation, before processing; they are excluded from setup processing time.

A `sources` entry can be a local `{path, sha256}` pin, a pinned R2 file with
`r2_bucket`, `r2_key`, `sha256`, and integer `size_bytes`, or `{json: ...}` containing
the ordinary stage document directly. A pinned Neon document uses
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
byte identity matters. The `local_water_overlay` source calls the ordinary
producer and verifier, then compares every selected value and type with the
pinned reference. Only its declared local provenance paths/hashes may differ.

    python3 scripts/v7-pipeline/run_pipeline.py \
      /workspace/selection/config.json /workspace/runs/fresh-run

For the first invocation, the output must be new. To continue a checkpoint-enabled
run after an interruption, use the identical configuration, code and runtime:

    python3 scripts/v7-pipeline/run_pipeline.py \
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
  and custody evidence consumed by the normal Stage 2 lineage validator.
- `resolution_template`: mainland witness/source selection data. Its source
  files are preserved; physical/component pins and current executable hashes
  are generated afresh. Historical output artifacts are not reused.
- `prior_physical_report`: optional prior report required by a selected
  locally derived land snapshot's independent physical/seed reproof.
  Its presence does not replace fresh physical output or relabel the snapshot.
- `regional_template`: selected mixed/regional decision request.
  The normal preparer validates the fresh Stage 2 artifacts and binds current
  code and preserves the template’s source policy.
- `water_snapshot`, `seavox_archive`, `coastal_plan`: selected named-basin,
  coast, closed-water and baseline ocean policies, the pinned SeaVoX archive,
  and the complete coastal tessellation. All basins in the snapshot are built,
  including both direct and shared-shore assignments. Each completed basin runs
  the normal independent raster-to-span coverage verifier before prefill.
- `ocean_snapshot`: optional separately pinned final ocean revision. When given,
  the runner builds the baseline complete grid, executes the normal split-ocean
  producer, and uses the split compositor to verify unseeded-partition
  equivalence before reusing enclosed water. This is needed when the selected
  final revision includes an ocean change such as the V8 Iceland boundary.
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
See [the complete extraction replay contract](../../docs/seavox-extraction.md).

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
builder retains `--research-interval` and `--pointwise-nearest` as reference engines. See [the certificate and full-input
benchmark contract](../../docs/named-sea-intervals.md).

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
  ocean, enclosed water and final composition, including the optional split
  ocean. Nested and concurrent intervals are counted once, never added twice.
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

For an exact clean water-stage baseline after an interrupted run, use
`benchmark_water.py --reference-run COMPLETE_RUN --config ORIGINAL_CONFIG --out NEW_BENCHMARK`.
It retains the pinned completed physical and land inputs, runs the entire normal
water stage afresh, and separately compares every final cell and both output
streams against the complete reference. `stage-timing.json` separates the water
interval from process startup/setup; `comparison.json` is outside that interval.
Run it sequentially with other full-input timing workloads. This is a new clean
baseline, not a replacement for the interrupted run's historical timing.

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
      TEMP=/workspace/test-scratch /usr/bin/python3 -m unittest discover \
      -v -s scripts/v7-pipeline -p 'test_*.py'

Tests execute actual raw polygon/Parquet rasterization and Python component
production through direct Python stage calls. Another real-processing fixture
chains ocean partition, enclosed-water classification, final-plan validation
and composition, checking every cell of its final grid. Timing tests cover
parallel union, idle gaps, failures, changed monotonic clock origins, simulated
process interruptions, resumed output equality, torn journals, live-process
safety, pin corruption and acquisition separation. These focused
fixtures do not replace the global source-to-final acceptance run or establish
its elapsed time.

## Replay preserved land evidence without a pipeline launch

`stage_land_sweep_inputs.py` reads an existing catalog and exact core-config
pin. It stages metadata by default; `--stage-streams` reads the catalog-pinned
physical/component/seed RLE, hints and expected land streams. `--stage-search`
adds the pinned representatives, tile manifest and decision snapshot. Use an
existing read-only boto3 profile and an explicit HTTPS R2 account endpoint.
Every byte count and SHA-256 is checked. Original configurations and reports
remain byte-identical, including historical paths; the separate staging plan
maps those identities to the current files. No cloud object is changed.

`replay_land_sweep.py --staged-inputs DIR --out NEW_DIR` verifies all staged
pins and reruns complete physical/component/seed coverage and population checks.
Add `--search` to regenerate the seed index in Python, require its exact pinned
manifest, verify representatives against actual seed cells, rerun all source-bound
WGS84 decisions and then write and compare every land output byte and Ural count.
It can reconstruct missing assignment state without using expected output labels
as hints or assignments. Expected land output is used only for the final check.
Neither tool launches the complete pipeline, compiles code or starts a process.

This is preserved-evidence kernel replay, not a fresh raw-source build, geographic
acceptance or full end-to-end speed measurement. Keep complete timing comparisons
separate from other heavy runs. The user-owned full pipeline is independent.

`compare_land_sweeps.py` pairs the complete old and current Python preflight and
writer against the same staged inputs and fresh replay checkpoint. Pass
`--staged-inputs`, `--source-replay`, `--baseline-code` (the original Stage 2
source directory) and a new `--out`. It verifies checkpoint identity/checksum,
recomputes its final assignments, records both source fingerprints and exact
UTC trial intervals, and requires all reports and output bytes to match. It
loads the reference Python modules in process and never edits their source.
Run without other heavy workloads. `--candidate-first` reverses trial order;
one pair does not balance cache order and is not an end-to-end speed ratio.

For upstream cost inspection, `stage_land_sweep_inputs.py --metadata-source ID`
can stage an additional exact catalog-pinned JSON report with its receipt.
The option is repeatable and does not change the immutable main staging plan.
It accepts no unpinned object or path override, and reads no bulk stream unless
that separate staging option was explicitly requested.

## In-process admitted-stage benchmarks

`benchmark_stage.py` and the coastal, basin, closed-water and prefill wrappers
call the selected stage's `main(argv, emit=...)` Python API. They do not launch
an interpreter, subprocess or CLI. The admitted command remains in the receipt
as argument provenance; `actual_interpreter` and `execution_mode` describe what
ran. `stage_wall_seconds` excludes interpreter startup and comparison checks;
`process_wall_seconds` is the same value retained for older comparison tools.
UTC start/end anchors identify the actual measurement interval.

Use a fresh interpreter with the required Python bindings and run measurements
separately. Cached sibling modules from a different checkout are rejected,
API errors produce no success timing report, and the entrypoint is rehashed
after execution. Logs and failed output directories remain for inspection.
Older receipts that measured a child interpreter are not directly equivalent
to this timing scope.


## Replay seed raster sources through Python APIs

`prepare_seed_raster_replay.py --staged-inputs DIR --out NEW_DIR` reconstructs
source polygons with the ordinary regional producer and fresh water/terminal
closure checks. A local-derived decision snapshot requires
`--allow-local-provisional --prior-physical-report PINNED_FILE` and exact physical
stream equivalence. Recreated GeoJSON bytes must match archived source pins.
Historical reports and contracts are never rewritten or substituted for a fresh
closure proof. This is provisional research, not a final-land artifact.

`benchmark_seed_raster.py --staged-inputs DIR --recovered-regions SOURCE_DIR
--out NEW_DIR --workers N` runs complete serial and parallel GDAL-Python/NumPy
seed builds. It uses old seed outputs only after each build to check every
output hash and every rule/category population. Source polygons, component
streams, driver code and exact UTC intervals are pinned in separate receipts.
No compiler, ctypes bridge, child process or whole pipeline is used. Run alone
for comparable timing; one serial-first pair does not balance cache order.

# End-to-end research pipeline

`run_pipeline.py` is the supported single entrypoint from pinned raw OSM and
Overture inputs to the final WorldAtlas grid. It calls the ordinary repository
stage CLIs and generates each downstream request from the files just produced.
It does not call dated local coordinators, reuse old land/water output grids,
patch producer reports, relocate historical paths, or repair lineage sidecars.

This is **provisional, non-publishable research**. The current mainland producer
freeze and selected geographic decisions have not completed independent review.
The explicit research flag preserves those gates and source labels; it does not
approve geography, authenticate Neon, or publish a map.

## Run

Use one Python installation with NumPy, SciPy, PyProj, GDAL/OGR and PyArrow.
`g++`, OpenSSL headers/libraries, `ogr2ogr` and `gdal_rasterize` must also be
installed. The runner checks module/executable availability before processing.
It enforces `PROJ_NETWORK=OFF` in the runner and child stages, disables pyproj's
network API, and records the active local `proj.db` path and SHA-256 in runtime
identity. A regional template's `bering_proj_db` must match that exact active
database. This runtime file alone may be outside `input_root`; other selected
source files must remain inside it.
If a selected Python installation needs an existing dependency directory on
`PYTHONPATH`, export that directory when launching; child stages inherit it. For R2 source
staging, configure the installed official Wrangler entrypoint and authenticate
separately. If your existing authorized Wrangler login uses a nondefault
`XDG_CONFIG_HOME`, provide that directory in the launch environment. The runner
inherits it unchanged. No credentials belong in the configuration or logs.

Copy `config.example.json`, replace the source paths and SHA-256 values, and
choose an existing `input_root` containing the selected sources and the new run
location. Relative top-level source paths resolve beside the configuration.
Nested source documents retain their own declared paths; materialize their
pinned source files at those locations before starting. No path-prefix rewriting
is supported.

    /usr/bin/python3 scripts/v7-pipeline/run_pipeline.py \
      /workspace/selection/config.json /workspace/runs/fresh-run \
      --allow-provisional-research

For the first invocation, the output must be new. To continue a checkpoint-enabled
run after an interruption, use the identical configuration, code and runtime:

    /usr/bin/python3 scripts/v7-pipeline/run_pipeline.py \
      /workspace/selection/config.json /workspace/runs/fresh-run \
      --allow-provisional-research --resume

A committed downstream water fix can be applied before any water command has a
completed checkpoint. A closed-water-only fix can also reuse explicitly listed
earlier water stages, provided no closed-water or later stage is complete.
Unknown producers and shared-code changes are rejected. Explicitly identify the
old producer commit:

    /usr/bin/python3 scripts/v7-pipeline/run_pipeline.py \
      /workspace/selection/config.json /workspace/runs/fresh-run \
      --allow-provisional-research --resume --resume-code-from OLD_COMMIT

The complete old scripts identity must match that git commit, and the complete
new scripts identity must match the current committed `HEAD`. The request,
sources, runtime and paths must remain unchanged. Only runner control/test files
and downstream `v7-replay`/ocean code may change. Upstream/shared producer changes
and unknown completed producers are rejected. After any completed water checkpoint,
only a closed-water-only or split-final-only file domain may change, and only
explicitly listed earlier producers may be reused. The split-final domain excludes
the split-ocean runner and shared helpers; it permits a completed baseline grid,
not a completed final grid or later verification. Generated upstream requests must
still be byte-identical.

An append-only `code-versions` chain records both commits, every changed code
hash, unchanged checkpoint receipt pins and the timing-journal prefix. The
original run identity and producer reports/receipts are not rewritten. New
commands pin their own code version; the final report identifies both the
original run and current version. Old partial coastal batches are preserved but
not reused when a change could affect coastal production. Subsequent ordinary
`--resume` invocations validate this chain without needing the transition flag again. This is code
provenance, not scientific approval or a general migration of arbitrary changes.

The runner takes an exclusive run lock and refuses to duplicate a still-running
runner or an admitted stage process left alive by a killed parent. All temporary
files are directed into `fresh-run/scratch`,
including files created by child stages. No application memory cap, memory floor
or memory watchdog is added. Component construction runs directly without its
retired monitor/guardian wrappers. Existing stage disk reserves and source/output validation remain enforced.
Use a run path on the same filesystem as its generated component work.

## Configuration inputs

All `sources` are explicit `{path, sha256}` pins:

- `land_config`, `water_config`, `raw_manifest`: current raw physical-stage input
  contracts. The land config pins all required source sidecars. The raw manifest
  lists the complete official Overture shard set and, for missing local files,
  their R2 bucket, key, byte size and SHA-256. `source_staging` in
  `physical_controls` uses read-only R2 GETs, never intermediate R2 writes.
- `land_snapshot`, `neon_selection`, `osm_receipt`: selected source/decision data
  and custody evidence consumed by the normal Stage 2 lineage validator.
- `resolution_template`: mainland witness/source selection data. Its source
  files are preserved; physical/component pins and current executable hashes
  are generated afresh. Historical output artifacts are not reused.
- `prior_physical_report`: optional prior report required by a selected
  locally-derived provisional snapshot's independent physical/seed reproof.
  Its presence does not replace fresh physical output or relabel the snapshot.
- `regional_template`: explicit provisional mixed/regional decision request.
  The normal preparer validates the fresh Stage 2 artifacts and binds current
  code. Preserve its source policy; do not turn provisional flags into approval.
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
setting (`1` selects serial execution). Linux fork shares the sealed RLE input
mappings and complete read-only shoreline span index; only crop-specific
centers and distance trees are constructed per worker. The parent alone
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
No map is uploaded, published, or assigned accepted status.

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
must remain byte-identical. Seed rasterization and component/verifier compilation
execute the pinned checked-in source files directly; run directories contain no
copied Python/C++ source executables. A changed pin or a live prior stage stops
resume, except for the explicit restricted committed-code transition above.

Stages execute directly, without a new supervisor or guardian process. Before
launch, the runner durably records admission and timing. The ordinary stage
process inherits the filesystem run lease, so another runner cannot duplicate
it even if a later tool invocation has a different PID namespace.

A missing `/proc` PID is never treated as proof that an old writer is dead. If
an interruption left no normal stage exit record, resume stops until all old
writer processes have independently been confirmed exited. The operator can then pass
`--confirm-no-live-writers` with `--resume`; this explicit assertion is recorded
separately for the exact unchanged old attempts and does not replace any source,
checkpoint or output validation. The same confirmation is not requested again.
The runner does not kill an unverified old process or move potentially live
outputs based on a PID guess.

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

Tests execute actual raw polygon/Parquet rasterization and C++ component
production through ordinary subprocess CLIs. Another real-processing fixture
chains ocean partition, enclosed-water classification, final-plan validation
and composition, checking every cell of its final grid. Timing tests cover
parallel union, idle gaps, failures, changed monotonic clock origins, simulated
process interruptions, resumed output equality, torn journals, live-process
safety, pin corruption and acquisition separation. These focused
fixtures do not replace the global source-to-final acceptance run or establish
its elapsed time.

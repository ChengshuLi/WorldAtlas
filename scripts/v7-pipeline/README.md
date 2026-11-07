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

The output must be new. All temporary files are directed into `fresh-run/scratch`,
including files created by child stages. No application memory cap, memory floor
or memory watchdog is added. The component monitor observes RSS but does not cap
it. Existing stage disk reserves and source/output validation remain enforced.
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
alongside that pool. These are execution tuning controls, not memory limits.
The WGS84 point assignment is the normal basin engine. An interval/certificate
engine is not enabled implicitly.

## Outputs and timing

`report.json` is created only after every requested stage and reference check
succeeds. It pins final rows, runs and producer report. Per-job logs are under
`logs/`; generated requests are under `configs/`. The final map is under `final/`.
No map is uploaded, published, or assigned accepted status.

`timing-events.jsonl` is an append-only, fsynced start/completion ledger using one
monotonic clock for the run. The stage totals in `report.json` are wall-clock
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

The runner does not pause/resume or estimate historical gaps. A failed stage
leaves `failure.json`, partial files, and completed interval evidence; those
partial intervals are not a complete stage baseline. A killed process can leave
an unmatched start and no failure report. Preserve that run for diagnosis and
use a new output directory for a complete uninterrupted baseline. There is no
manual checkpoint relabeling or automatic destructive cleanup.

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
parallel union, idle gaps, failures and acquisition separation. These focused
fixtures do not replace the global source-to-final acceptance run or establish
its elapsed time.

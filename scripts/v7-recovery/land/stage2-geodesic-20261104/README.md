# Fresh stage-2 geodesic prototype

Research prototype, not an accepted or publishable map build. The current code
enables the seed-producer and selected-policy crosswalk checks: the orchestrator
requires the exact reviewed seed-source freeze and a matching selected policy.
Those checks and hash pins do not authenticate a Neon export or establish that
the selected geography and crosswalk have completed independent review. Existing
inputs and historical checkpoints are not accepted as seeds, hints or assignments.

The direct orchestration sequence is:

1. Verify pinned stage-1 mask/component provenance and independently re-resolve
   source-backed selected witnesses on those current streams.
2. Run the reviewed seed producer on the selected Neon mainland rules and
   boundaries. Validate geographic closure and physical/component coverage.
3. Generate seed tiles and representatives. Verify every tile against the seed
   with an independent NumPy interval verifier and check representative membership.
4. Generate source-only hints. Certify the candidate or run the exact WGS84
   search for every non-seed physical component; hints never become labels
   without one of those checks.
5. Write the research output atomically after all source, tile, coverage and
   output checks pass. Within the recorded Ural-delta scope, land-cell centers
   are assigned to Europe or Asia by which side of the selected Ural divider
   they fall on. The rule is bound to the selected Ural boundary and Caspian
   closure hashes, changes no geometry or physical mask, and leaves water and
   all cells outside the scope unchanged. Other List 1 overrides are excluded.

The producer freeze covers the invoked `seed_worker.py` entrypoint as well as
all producer modules. A historical code fingerprint does not freeze a changed
direct-run implementation; install a new fingerprint only after independent
review of the exact source closure and replay evidence. Until then, the
orchestrator remains gated. Fresh artifact paths, requests, source code and
hashes are bound to the work identity. Resume requires a complete derived manifest, matching paths and pins,
matching code and policy, and a valid core checkpoint if core work has started.
Incomplete or uncertain state must be inspected before retrying. This identity
is an integrity/provenance aid, not cryptographic authentication of Neon itself.

For authorized profiling only, `orchestrate_stage2.py --provisional-only` can
run without a reviewed seed freeze when both work and output directory names
end in `-provisional-only`. It records that mode in the work identity, derived
manifest, and final report; final status is `stage2-provisional-only` and
`publishable` is false. The stage-2 candidate validator rejects this status.
Use fresh isolated directories and never reuse this output as a production
candidate. The normal path still requires the reviewed freeze.

Independent review of source evidence, boundary semantics, numerical bounds and
the selected policy is still required. The physical mask differences relative
to V7 are not island overrides.

Run synthetic tests with:

    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -m unittest discover -q

Do not run production or publish the prototype based on these tests. The
terminal-aware closure integration and selected-policy crosswalk require
independent review against the real selected Neon data before an accepted build.

The checkout-level `test_repository_dependencies` verifies that the current
core, seed, closure, rasterizer and component-builder sources exist and match
their recorded code hashes. It checks code integrity, not source-data custody,
policy selection, live Neon access or geographic correctness.

## Orchestrated physical-lineage evidence

`verify_physical_lineage.validate_combined` still accepts the historical
`stage1-reported-lineage-request-v1` unchanged. It also accepts the distinct
`stage1-orchestrated-lineage-request-v1` for the 2026-11-07 interrupted and
resumed physical run. The latter request contains a `code_root` and `inputs`
with exact `{path, sha256}` pins for `pipeline_report`, `osm_receipt`,
`neon_selection`, `initial_events`, `resume_events`, and `part18_receipt`.
Those files must be preserved and re-pinned when moving environments. This
adapter describes the specific run: 18 checkpointed shards, one separately
prestaged shard 18, and 13 newly staged shards. It does not accept another
resume pattern under that schema.

The validator checks the orchestrator and stage reports, current producer code,
source and configuration pins, all 32 shard reports and masks, union, physical
streams, five OSM sidecars, checkpoint and download events, the part-18
receipt, and selected raw Neon source metadata. It rechecks file hashes before
returning. Its existing downstream status means the selected records match the
reported lineage, not that the sources or providers are independently
authenticated. It does not rerasterize the raw sources or prove geography. The
old land report did not record a producer-code digest, so matching that code is
an operator assertion, not proof of what executed. Preserve these limitations
when using the report.

## Exact local snapshot in provisional mode

`--provisional-only` may use the one explicitly allowlisted local-derived
research snapshot whose canonical content digest is `fddc8e6703d4bf8c089f5d94933f05bcf2c2f6580ef162508e772de9e0ed001f`.
The source label remains `local-derived-from-neon-export`. The orchestrator
passes an explicit provisional flag through witness resolution, seed building,
and hint generation, while the core checks the same provisional flag. A
modified snapshot or an unflagged local snapshot is rejected. Normal mode
continues to require the Neon-export path and its reviewed seed freeze; no
local snapshot is promoted or presented as authenticated. Outputs remain
research-only and cannot pass the normal candidate validator.

For this local candidate, `inputs.prior_physical_report` is required. Its
pinned prior report and the fresh physical report must identify the same grid,
rows, and runs. The selected historical route provenance remains unchanged;
trusted current checkers must freshly prove every selected closure against the
fresh contract and streams before the seed rasterizer starts. The resulting
seed report binds both report digests, the unchanged route provenance, and the
new proofs. The independent core validates this equivalence and cross-checks
every new proof, geometry and checker. This exception is available only to the
explicitly provisional exact snapshot; normal-mode provenance gates remain in
force. It establishes stream equivalence, not provider authentication or
geographic correctness.

## Python stream throughput

The physical/component/seed sweeps decode one complete row per input read and
write/hash one complete output row at a time. All assignment roots are indexed
once in an input-sized dictionary, replacing a binary search for every component
span. This is ordinary row buffering and a complete root index, without a
bounded cache or application memory limit. Codes and the assignment-seen bitmap
remain memory-mapped. Coverage checks, sorted/unique-root checks, missing/unused
roots, seed populations, output coalescing and Ural cell-side arithmetic are
unchanged. No process, subprocess or compiler step is added.

`test_land_stream_speed.py` checks per-row I/O, first/last/zero root IDs and a
complete randomized stream against independently constructed expected bytes.
The existing writer, seed-population and Ural tests cover malformed inputs and
boundary failures. The [complete preserved-source kernel replay](../../../../docs/benchmarks/land-kernel-replay-20261108.md)
now reproduces every global land output byte, with fresh source-bound decisions.
A fresh raw-source end-to-end build and controlled before/after timing ratio
remain unmeasured. `benchmark_land.py` remains the complete-mainland comparison when a completed
reference and an uncontended timing slot are available. For a local, in-process
coverage/writer-only check, use `scripts/v7-pipeline/benchmark_land_sweep.py` with
`--reference-run /path/to/completed-run --out /path/to/new-comparison`. It checks
all source, configuration, producer-report and checkpoint pins, every output
byte and the Ural populations. It starts no process, contacts no service and
compiles no code. Its timings exclude seed production, search and regional work.


### Python seed raster and index verification

The active seed producer uses GDAL's Python API and NumPy. Each raster worker
opens independent OGR dataset handles. Work is consumed in original strip order,
with unchanged full-width affine transforms and pixel-center conventions.
`seed_runtime.py` composes only actual mask transitions inside selected physical
component intervals, rather than dispatching a Python operation for every cell.
Whole-component rules emit intervals directly. No region name, root identity,
current map size or chosen label selects a special path.

The rasterizer's v2 report binds both Python source files and has no compiled
binary pin. The existing `seed_kernel` input field now pins `seed_runtime.py`;
it is an algorithm source pin, not an executable. Old C++ pins are rejected.
The historical reviewed seed freeze remains unchanged: changed source paths
remain explicit provisional research until independently reviewed.

`verify_seed_index.verify` independently reconstructs every canonical tile
record from complete source RLE using tile-row bands, checking all offsets,
row endpoints, categories, exact tile bytes and unexpected tile files. It
never compiles or starts a helper. Checkpoint identity pins the verifier's
Python source instead of a binary. This intentionally prevents resuming a
checkpoint authenticated under the retired verifier implementation.

Complete-world preserved-source seed parity and tile verification passed. The
serial/nine-thread pair measured 42.604 s/10.267 s with exact streams and all
populations, plus all 2,139 tiles independently verified. See
[receipts and limits](../../../../docs/benchmarks/land-python-api-pairs-20261108.md). Tiny fixtures cover different
nonbinary steps, strip sizes, concurrency, root IDs zero/UINT32_MAX, arbitrary
rules, empty rows, exact-center vertices, malformed streams and dangling output
symlinks. This is not a new full-pipeline acceptance claim.

Entire raster strips are omitted only when NO selected component interval
in the strip depends on ANY polygon. Whole-component/unselected intervals
do not inspect the mask. Otherwise every original polygon is burned in its
original order, even when its nominal bit is unused: GDAL MERGE_ALG=ADD can
carry/saturate boundary contributions into other bits. A hole/disconnected-part
fixture with exact-center vertices caught this distinction. Per-bit omission
was withdrawn before complete-world validation. All polygons remain pinned
and validated even when an entire raster strip is not needed.

### Numeric coverage integration

The Stage2 builder now selects `numeric_preflight.validate` with the shared
128-row default. Its normal code identity includes `numeric_preflight.py` and
`row_overlay.py`. The independent legacy Python row checker remains a baseline,
not the production coverage path.

This uses full-row NumPy I/O and common endpoint arrays, with every row offset,
physical/component/seed interval, root/category completeness and exact rule
population checked. Root zero stays distinct from a component gap. uint64
positions pack batches without pixel expansion or a memory-based admission rule.
Independent dense, UINT32-width and varied-batch-size oracles pass.

The complete candidate-first preflight pair matched every report field at
8.319 s versus 22.672 s (2.73x observed). See the
[receipt and limits](../../../../docs/benchmarks/land-batched-preflight-20261108.md).
`compare_land_preflights.py --batch-rows N` keeps diagnostic selection explicit;
its comparison default remains one-row mode. `compare_land_replays.py` pairs
complete fresh seed-index/WGS84/writer replays with legacy and integrated
coverage. The integrated full-kernel pair passed with every decision, output hash and
Ural count identical: 104.133 s legacy versus 89.160 s integrated. See the
[full receipt and scope](../../../../docs/benchmarks/land-batch-integration-20261108.md).
It is not raw-pipeline/geographic acceptance.

### Numeric writer integration

The Stage2 builder now selects `numeric_land_stream`, with its source in the
normal code identity. The complete integration pair passed before this default
was published: 90.238 s legacy versus 73.051 s numeric, with every decision,
output byte and Ural count identical. The legacy writer remains its independent
oracle. See the [complete receipt and scope](../../../../docs/benchmarks/land-writer-integration-20261108.md).

The full writer-only pair passed exact outputs and reports at 29.844 s legacy
versus 13.012 s numeric. See the
[receipt and scope](../../../../docs/benchmarks/land-numeric-writer-20261108.md).
Both row offsets and records stream in ordinary batches, with every span/root
condition checked. The Ural policy retains exact original scalar center
arithmetic; only compressed output transitions are retained, not pixel arrays.
Dense/MAX-width/failure oracles and the unchanged writer contracts pass.

`compare_land_replays.py --compare-writer` holds the already integrated numeric
coverage constant, then independently rebuilds seed indexes, reruns every
WGS84 decision/tie and writes full output bytes with legacy/numeric writers.
`replay_land_sweep.py --writer-engine legacy` retains an explicit baseline.
No accepted geography or user-owned raw pipeline is changed by these proofs.

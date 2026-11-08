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
   with an independent compiled verifier and check representative membership.
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
boundary failures. Full-world timing has not been measured for this change;
`benchmark_land.py` remains the complete-mainland comparison when a completed
reference and an uncontended timing slot are available.

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
   output checks pass. Water assignment and List 1 overrides are excluded.

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

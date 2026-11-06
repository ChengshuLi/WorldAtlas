# Fresh land pipeline research (work in progress)

This preserves the stage-2 source-derived mainland seed and geodesic prototypes,
including the Panama–Colombia direct-cut experiment. It is **not production-ready**
and does not change the selected build. The seed producer still constructs the
Americas polygon using an exterior route; the direct-cut experiment is not yet
integrated into the producer or the full pipeline. Do not publish its results.

- `stage2-geodesic-20261104/` is the guarded research orchestrator, seed and hint
  producers, writer and tests. See its README for required provenance and gates.
- `fresh-components-20261104/`, `fresh-witness-20261104/`, `simple-v2-baseline/`,
  and `mainland-source-verification-20261104/` preserve the component, witness,
  and closure-checker source dependencies.
- `neon-mainland-regions-20261104/rasterizer/` contains the pinned research seed
  rasterizer and kernel used by the existing producer.
- `panama-direct-split-research-20261104/` contains an experimental four-neighbor
  source-line graph and generic fail-closed fragment-side checks. A prior graph
  comparison found 515,685,972 of 515,685,972 Americas mainland cells matched the
  current stage-2 mainland baseline, including ten fragment cells. A generic row
  composition primitive is tested but not wired into the producer. This is not a
  fresh end-to-end run, proof for other geometries, or historical V7 equivalence.
- `mainland-source-recovery-20261104/` and `audit/` hold the research graph and
  rasterization dependencies for that experiment. These are preserved alongside
  it rather than replacing the separately maintained ocean implementation.

The direct-split scripts retain workspace-relative names and pinned hashes. They
need the matching physical components, witness resolution, decision export, and
baseline outputs placed at those paths; these large generated files and decisions
are intentionally not checked in. `verify_fresh.py` is an independent interval
sweep prepared for a successful fresh run. The fresh graph test was stopped by the
disk-space guard before completion; no output from that attempt is accepted.
Its full-pipeline runtime and exact final output remain unmeasured.

Before selection: integrate a source-only split into the seed producer without
stored Americas ocean closure, validate source and decision lineage, test general
fragment and finite-endpoint handling with no cell patches, independently check
complete land coverage and exact output equivalence, benchmark the **full**
pipeline under equivalent resource conditions, and obtain independent review.
Continue to fail closed on ambiguous geometry and resource/provenance violations.

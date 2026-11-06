# Direct mainland cut research

The direct-split runner is disabled because its nearest-side calculation used a planar geographic distance. It is an unselected research prototype, not part of the active WGS84 pipeline. See `README-NEAREST-RETIRED.md` for the retained validation utilities and what must happen before the prototype could be replaced or re-enabled. It does not authenticate exported snapshots or approve geography.

The former runner accepted a request supplied at runtime, not stored in this repository. That request included a grid; SHA-256 pins and paths for the Neon-export snapshot, witness report, component rows and component runs; selected rule and boundary IDs; and resource limits. Those inputs must be staged from their authorized stores. The boundary source references must match original-asset R2 metadata in the snapshot; the report retains whether the recorded lineage is complete or incomplete. Metadata consistency alone does not verify R2 availability or prove complete source custody. The former rule referenced one selected source boundary, with region witnesses providing graph seeds and side orientation. The retained checks do not make the disabled nearest-side calculation usable. The nearest-segment residual rule is experimental and is not a generally proven partition.

The direct runner and its nearest-side helper fail closed; do not use their old reports as results of a WGS84 run.

The report is research-only. Before replacing any current pipeline step, independently verify exact coverage and equality, rebuild the entire downstream output, and benchmark the complete old and new paths under comparable resources. No result from this package alone authorizes a switch.

Run synthetic tests with `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -m unittest -q test_direct_core test_watch_direct`.

`watch_compare.py REQUEST OUTPUT` runs an independent comparison of two complete, pinned full-width RLE grids. It checks every cell, tolerates different run segmentation, and reports equality or bounded mismatch examples without using either grid as an assignment input. The comparison request specifies the grid dimensions, four row/run input pins, and a disk reserve. The watchdog samples RSS for observation but imposes no memory floor or RSS cap. Equality is numerical only; it does not establish source provenance or approve a switch. Run its synthetic tests with `/usr/bin/python3 -m unittest -q test_compare_full`.

`compose.py` provides a row-level primitive for combining a direct split with a separately produced partial seed that already excludes the selected component. It takes the allowed category codes as input and rejects missing component coverage, invalid codes and overlap. It does not generate that partial seed or establish equivalence. Its synthetic tests use `/usr/bin/python3 -m unittest -q test_compose`.

`partial_plan.py` validates a research-only plan that omits one direct-split rule while retaining the other selected rules and their source-boundary dependencies. It does not build a partial seed. `compose_seed.py` is a streaming primitive that combines an independently produced partial seed and direct split while checking exact target-component coverage. Callers must authenticate and pin the source snapshot, witness and streams and supervise resources; these primitives do not switch the pipeline. Their synthetic tests are `test_partial_plan` and `test_compose_seed`.


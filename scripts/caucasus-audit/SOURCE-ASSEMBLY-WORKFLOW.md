# Guarded Caucasus source assembly

This is a research-stage implementation, not an automatic stage-2 input or proof of historic derivation or actual watershed. The source selectors were derived by comparing against the stored 2,292-position selected line. The explicit endpoint coordinates, source selections and joins preserve that existing decision; they have not independently established drainage. The original construction and original shoreline clip are still unknown.

## Sources and decisions

* HydroBASINS Europe level 12 v1c: R2 `sources/hydrosheds/hydrobasins/standard/europe/level-12/v1c/hybas_eu_lev12_v1c-21797d53e079.zip`, SHA-256 `21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03`. The replay verifies both the ZIP and its extracted SHP bytes.
* Trubetskoy author GeoJSON: R2 `sources/trubetskoy/7aa03ec54a262e8e97e8273f60621c530ec4e998/asia_europe_border.geojson`, SHA-256 `c9d56b1291522573fbb8b0baa1a39cecfd192eda8f5e51650b24f562d13688e6`. Author feature 463 positions [1,398) are used.
* The compact decision describes 165 contiguous source-vertex runs and 142 explicitly parameterized source-edge positions, 307 ordered operations total, together with two literal endpoint decisions and the author range. The selected guide and manual preservation choices are necessary inputs. The exact original shoreline extraction has not been recovered. The compact recipe SHA-256 is `59cae33e287b029465b27110057cc8f06d2dcdf982186b13815cca8f8bbb961c`; the expanded selector recipe SHA-256 is `c2107838b8dde06ff65a3ef61a7a15234137dc16a966fe2155edfac50f69a8d0`.

The compact recipe is currently a local research artifact, not persisted in Neon and not a selected stage-2 input. An attempted insertion into the selected Neon record was rejected by automatic approval review because the recipe was research-only and not used by the production pipeline. No database update resulted. Do not assume a future export contains the recipe.

## Current guarded workflow

Prepare the same source files and the selected GeoJSON guide. The existing scripts `caucasus_unmatched_edge_screen.py`, `caucasus_selector_recipe.py` and `caucasus_compact_selectors.py` can regenerate a compact recipe from that guide and the pinned SHP. Since numeric behavior and source ordering matter, verify the hashes against the pins instead of accepting silently different results.

Given the pinned compact recipe and raw inputs, run:

```sh
python caucasus_source_assembly.py \
  --decisions compact-recipe.json \
  --decisions-sha256 59cae33e287b029465b27110057cc8f06d2dcdf982186b13815cca8f8bbb961c \
  --hydro-zip hybas_eu_lev12_v1c.zip \
  --author asia_europe_border.geojson \
  --selected selected-caucasus.geojson \
  --output caucasus-reconstructed.geojson
```

The assembler verifies raw source hashes, extracts only the named SHP member, expands and hash-checks decisions, replays selectors, validates simple geometry and compares every vertex to the pinned selected line. It aborts on a hash mismatch, an existing output, more than 0.0002 m vertex displacement, or any native grid center within the conservatively padded swept-edge hulls. The selected line is still required for this guard; this does not eliminate the saved line from the workflow.

For the tested files, the result hash was `2f2f6c6777fe080fcbf13a526caad22b7b883fc982d3ff0492b91e082d6f06b6`; 2,164 of 2,292 positions were binary64-identical, the maximum WGS84 displacement was 0.000154444 m, and zero possible changed centers were found in 102 center tests against 249 changed-edge hulls. Equal endpoints and unchanged external closure are assumed. A deliberately incorrect decision hash was rejected. The screen does not execute the land compiler, establish its tie behavior, or report a new actual map or current mismatch count.

## Remaining integration

The actual stage-2 pipeline currently consumes the saved line, not these source selectors. Complete an independently reviewed integration which consumes the decision recipe as structured input, verifies the raw R2 bytes and source catalog identities, retains selected geometry until validated, and runs the full native-grid compiler and V7-style map comparison. Reconcile the 128 submillimetre vertex deviations and obtain a real end-to-end grid result before selecting the reconstructed geometry. Only after the recipe becomes an actual pipeline input should it be persisted as structured Neon data under the project's data strategy; coordinate any snapshot and schema change with the pipeline owner. No alternate boundary or labels are selected here.


## Feature output for the region builder

Pass `--feature-id caucasus_blacksea_anapa_to_caspian` to emit a GeoJSON FeatureCollection instead of a bare LineString. The output has a single feature whose `cut_id` equals that value and is compatible in shape with the `feature` selector in `../v2-baseline/build_regions.py`: pin the generated file bytes, set `id_property` to `cut_id`, set `id_value` to the feature ID, and set the appropriate direction. Region construction still requires the other segments, a valid closure, a pinned physical grid where applicable, and witness checks. The local run produced feature-file SHA-256 `a022157d877d8ace9916aed63eda0b1014520e965fd1db54a3ef61ffaf090b2b`, with the same line geometry digest and guard comparison described above. The feature wrapper was checked, but the full region builder and land compiler were not run in this environment; do not call this a completed pipeline integration.

The current project objective is a reproducible current pipeline, not recovering or matching the historical V7 implementation or its cells. Comparison with the saved selected line above is a guard for preserving the existing geography during this transition, not a requirement that the final geography match old V7.


## Source-derived seed integration prototype

The seed wrapper supplies the reconstructed source-derived line directly to the seed producer's boundary adapter. It does not add the 128 literal binary64 preservation points explored in an earlier prototype. The selected-line comparison is a guard against accidentally changing the current proposal during development, not a requirement to match historical V7. The choices remain derived from the currently selected guide, and the unresolved geographic questions documented in the synthesis still limit confidence in the line as a watershed.

The wrapper verifies the pinned selected Neon snapshot and raw-source catalog references, checks that the selected record contains the same compact recipe as the separately pinned input, reconstructs the line, and then injects it into the research seed producer in memory. Before replacing any region digest, it reconstructs the original ordered ring and verifies its selected hash. It then computes the hash for the same exact-join ring using the source-derived line. Existing region validation, closure checks, witnesses and raster checks must still run. The derived line has digest `2f2f6c6777fe080fcbf13a526caad22b7b883fc982d3ff0492b91e082d6f06b6`; the chosen endpoints are unchanged, while 128 positions differ from the selected guide by at most 0.155 mm.

This is an in-memory runtime wrapper around frozen producer code: the producer's own digest and certificate do not attest the wrapper, recipe or raw source inputs. Its gate report, derived-region digests, wrapper and dependency pins must be incorporated into the trusted orchestrator contract and independently reviewed before any production use. The wrapper is not yet selected in the actual orchestrator.

The proposed selected structured input is `atlas.decision_mainland_boundaries.provenance.source_assembly_v1` on revision `v2-land-mainland-boundary-draft-1`, boundary `caucasus_blacksea_anapa_to_caspian`: schema `caucasus-source-assembly-v1`, compact recipe object and its canonical SHA-256, and source IDs and versions. The current Neon export includes boundary provenance. A later write must verify the selected geometry and catalog pins, preserve unrelated provenance and be coordinated with the actual integrated snapshot and reviewed code. **No recipe write has been made**, and this proposal does not authorize bypassing the earlier review denial.

Four local unit tests pass, covering altered snapshots, missing source links, missing selected recipes and exact region joins/hash changes. A synthetic snapshot and a stub producer exercised the derived-line callback and a changed region digest. Neither is a test of the real Linux/GDAL region or seed builders. This Mac execution environment has no Linux/GDAL runtime; coordinate a bounded real-builder test with the existing cloud builder. No map rebuild has been initiated, per the user's instruction.


## Shared effective snapshot and orchestrator gap

The current prototype's `caucasus_effective_snapshot.derive` validates the selected line and the old region hashes, checks the unchanged closure endpoints, and returns a separate in-memory snapshot containing the source-derived line and recomputed affected region hashes. The seed wrapper uses this same function when loading the pinned original. The original snapshot and its digest are not rewritten. The helper alone does not authenticate the gate report or raw files; its caller must pin and independently verify the selected recipe, both raw R2 assets, assembly code, the gate result and the original snapshot.

Seven local tests pass. A synthetic snapshot, actual pinned R2 readback files, and a stub seed producer exercised the shared effective snapshot; the stub observed the source-derived boundary and recomputed region digest. The gate report explicitly distinguishes the original snapshot hash from the derived boundary and region hashes.

**Not integrated into the actual stage-2 orchestrator:** `orchestrate_stage2.py` freezes and attests its seed worker and producer; `contracts.validate_selected_seed_decisions` independently compares every seed trace and region hash with the original snapshot. Thus a seed containing the derived line must not be accepted by that validator as if it were the original stored geometry. The actual integration must add a reviewed and versioned source-derivation contract, pin raw inputs and all assembler/gate/helper code, recompute and validate the effective view independently for both seed production and seed-trace validation, and bind its report into the seed and final orchestrator provenance. It must preserve the original snapshot pin and fail closed on stale decisions or joins. It also needs selected recipe data in Neon only when this path is actually used.

A bounded run against the real Linux/GDAL region and seed builders and independent code review remain necessary. This Mac environment cannot perform that run and no real builder inputs were handed off here. No map rebuild was run.


## Independent validation adapter

`caucasus_stage2_validation.validate` is a prototype integration point for the frozen stage-2 validator. It independently reruns the raw-source reconstruction and effective-snapshot derivation, requires the seed report to reference the original pinned snapshot, and then calls the existing selected-seed validator with the effective view. It verifies its six source-derivation code files and raw/source inputs both before and after validation and returns a separate source-validation trace. The orchestrator must authenticate the request and independently trusted code pins, pin compatible runtime/library versions, and bind that trace to its final provenance; this adapter does not do those tasks by itself.

The production orchestrator does not currently call this adapter. Tests use mocks to check that a stale snapshot is rejected before validation, the independent validator receives the derived view, and incomplete code pins fail; they do not establish full real-seed integration. Ten local focused tests pass. No actual map or seed build was initiated.


## Bounded strict-validator result

A fresh macOS replay regenerated the compact recipe and derived line from the pinned raw source readbacks and the selected guide; the output bytes exactly matched the handoff. `test_caucasus_real_contract_adapter.py` then ran the actual stage-2 `contracts.validate_selected_seed_decisions` through the independent adapter with those source bytes and derived line. Three tests passed, including rejection of a stale boundary trace. The region, route, closure proof, component groups and seed trace were synthetic; the test did not execute a seed compiler, validate a real closure, or create a map. It did not claim historic V7 equivalence.

Run from `scripts/caucasus-audit` with the pinned stage-2 code directory and the four source fixture paths:

```sh
CAUCASUS_SELECTED=/path/to/selected-caucasus.geojson \
CAUCASUS_RECIPE=/path/to/compact.json \
CAUCASUS_HYDRO=/path/to/hybas.zip \
CAUCASUS_AUTHOR=/path/to/asia_europe_border.geojson \
PYTHONPATH=".:../v7-land/research-mixed-runtime/stage2-geodesic-20261104" \
python -m unittest -v test_caucasus_real_contract_adapter
```

Separately, the Linux builder's real GDAL region-builder fixture passed as recorded in [BOUNDED-GDAL-HANDOFF.md](BOUNDED-GDAL-HANDOFF.md). Neither bounded result integrates the wrapper and report into the frozen orchestrator or proves real land-cell output. The real builder must reproduce source-to-line independently in its environment, review the integration and pin code and runtime before the selected workflow is used. No recipe was written to Neon.


The source-and-validator fixture also confirms that the current strict validator rejects the derived seed trace when presented with the unchanged selected view; it accepts that trace only against the independently reconstructed effective view. The latest local focused run passed 35 tests. These are still bounded, synthetic-closure tests. In accordance with the user's instruction, do not install or use the separate dependency handoff and do not describe the Mac replay and Linux GDAL fixture as a single-environment run.


## Worker resource guard

The source gate's optional seed execution now invokes the pinned seed worker, which supplies its normal memory and disk guard to the producer. Pass `--worker-sha256` together with the producer pin and other worker arguments. The caller remains responsible for the process-group guardian, trusted code/input pins and binding the gate report to orchestrator provenance and resume checks. This is a tested prototype seam; it is not connected to the stage-2 orchestrator and has not run the real seed pipeline.

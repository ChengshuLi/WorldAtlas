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


## Seed gate prototype and proposed selected data

`caucasus_seed_gate.py` is a research wrapper around the existing mainland seed producer, not an alteration of its frozen files. Given a caller-authenticated, pinned seed request and snapshot, it checks that the selected Caucasus record references both catalog assets with the expected R2 bucket, keys, sizes and byte hashes; the recipe exported separately must exactly match a canonical recipe embedded in the same selected boundary record. The assembler then checks the raw files, reconstructs the line and applies the geometry and grid-center guard. With all producer options supplied, the wrapper invokes the unchanged, independently pinned `seed_producer.py`; without them it runs the gate only. The seed producer continues to consume the original selected line and exact closures. Thus this is a provenance/consistency gate, not a source-derived replacement of the line or a full production orchestrator integration.

The exact proposed structured selected Neon location is `atlas.decision_mainland_boundaries.provenance.source_assembly_v1` on revision `v2-land-mainland-boundary-draft-1`, boundary `caucasus_blacksea_anapa_to_caspian`. It must include schema `caucasus-source-assembly-v1`, the compact recipe object and its canonical-byte SHA-256, plus explicit source IDs and versions. The snapshot exporter already includes boundary provenance. A safe eventual write must check the existing boundary geometry hash, avoid overwriting an existing assembly, preserve all existing provenance, and be coordinated with snapshot/build pinning and independently reviewed. **No such write is authorized by this note or has been applied.** The current runtime takes a separately exported recipe file and independently checks it matches the object in the authenticated snapshot; it does not itself read Neon.

Local checks: three unit tests reject altered snapshot pins, missing source links and a recipe not present in the selected snapshot. A synthetic snapshot containing the recipe and the actual hash-pinned R2 readback files passed the gate; a fixture producer was invoked after it. This is not an actual Neon snapshot and the invoked producer was a stub. No real stage-2 seed, map build, or label comparison has been run through this wrapper; the Linux/GDAL environment and full pipeline integration, source-decision review, and independent code review remain. The wrapper's sidecar report is separate from the existing producer's certificate and must be bound into the orchestrator's provenance contract before production use. No boundary or label changed.


## Exact derived-line seed prototype (supersedes the gate-only description)

The prototype now supports 128 explicit binary64 coordinate-preservation decisions. These are stored as an ordered list of vertex indices and literal coordinates, and are bounded to 0.0002 m from the source-derived replay. They were derived from the selected guide; they are not original map vertices or independent evidence of the watershed. The canonical test file SHA-256 is `c40adf322d0dc51c7e51b1ba8e161a8913c86e830dda498e0a2907d9f64e5bc4`. The recipe and overrides together reconstruct the exact selected binary64 geometry digest `9f4ae3bc778ebbcd0258a19868acf0fa655763f5e849361196160fb4289c0d52`. This preserves existing exact endpoint joins and selected geography; no actual map or raster was built.

The seed wrapper requires both the compact recipe and the preservation decisions in the selected snapshot provenance, as well as separately pinned exported bytes. After source validation it intercepts the research seed producer's boundary-record adapter and supplies the **derived** geometry to the producer. The previously described gate-only version did not do this. Because this is a runtime wrapper rather than a change to the frozen producer, the unchanged producer's own code digest does not attest the wrapper or sources: its separate gate report must be explicitly incorporated into the orchestrator's trusted provenance contract before use. Do not represent the producer's existing certificate alone as proof that derived inputs were consumed. Obtain independent review, validate the wrapper and its dependency/code pins in the real Linux/GDAL environment, and create a new tested freeze as appropriate.

The selected structured decision proposal is the prior `source_assembly_v1` object plus `exact_overrides_sha256` and the `exact_overrides` object. No data has been added to Neon; the earlier write was denied while the data was not pipeline-used, and this prototype has not yet been integrated or reviewed for production. Any later data update must be coordinated with the actual selected snapshot and reviewed pipeline, preserve unrelated provenance and source links, and verify the selected geometry pin.

A synthetic selected-snapshot fixture containing both decisions and actual R2 source-readback bytes passed the wrapper, and a stub producer asserted that its boundary-record callback received the derived, hash-exact 2,292-vertex geometry. Three fail-closed unit tests also passed. The real seed producer and GDAL region builder have not been tested with this wrapper. The user's current instruction prohibits a map rebuild until all non-allowed mismatches are resolved; do not initiate one prematurely.

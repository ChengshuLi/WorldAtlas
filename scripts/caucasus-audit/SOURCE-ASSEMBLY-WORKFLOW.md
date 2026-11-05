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

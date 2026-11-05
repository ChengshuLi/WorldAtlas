# Combined Panama and Caucasus source-to-core fixture

This bounded integration fixture runs both source paths together: the actual
Panama OSM archive, real Caucasus HydroBASINS and author sources and compact
recipe, the `caucasus_stage2_binding.run_seed` subprocess, the frozen direct-v2
seed producer and the real v2 water checker. The generated gate and seed
reports then pass through `caucasus_stage2_binding.validate_seed` with the
actual strict `contracts.validate_selected_seed_decisions` callback, followed
by an independent `panama_core_validation.validate_panama_source` replay.
A forged Panama source trace and region geometry are rejected, as is stale
route-contract provenance. Both region closure proofs are checked.
The producer uses its literal executable allowlist, without test-time patching.

The snapshot, source-catalog metadata, 720×360 half-degree grid, physical mask,
components, witnesses and both closure routes are synthetic. The grid contains
only eight synthetic land cells; it is not a reconstructed production map.
The fixture does **not** invoke the outer orchestrator, use the selected Neon
export, establish actual physical producer lineage, prove the historical
construction of either line or certify the watershed. The synthetic closure
provenance pins match the new checker and contract; it does not test migration
from historical selected provenance to fresh proofs.

Run from `scripts/caucasus-audit`, using the same raw paths described in
`CAUCASUS-DIRECT-V2-FIXTURE.md`, plus the cataloged Panama archive:

```sh
PYTHONPATH=/path/to/scripts/v7-land/research-mixed-runtime/stage2-geodesic-20261104 \
DIRECT_SEED_DIR=/path/to/scripts/v7-land/mainland-seed-l2 \
CAUCASUS_SELECTED=/path/to/caucasus-line.json \
CAUCASUS_RECIPE=/path/to/compact-recipe.json \
CAUCASUS_HYDRO=/path/to/hydrobasins-europe.zip \
CAUCASUS_AUTHOR=/path/to/asia_europe_border.geojson \
PANAMA_REAL_OSM_ARCHIVE=/path/to/panama-way-full.zip \
python3 -m unittest -v test_combined_panama_caucasus_source_core
```

The Panama archive SHA-256 is
`04fe1adb295e93d78ee029b48351d2b0380d69ac631b47c909dffd538bbaf6c1`;
the selected Panama line is
`cfbfbb514d0f6efff1c0c803ae5f0f0835225015568747bb8b1164f3bb6d0e17`.
The independently reconstructed Caucasus line is
`2f2f6c6777fe080fcbf13a526caad22b7b883fc982d3ff0492b91e082d6f06b6`.
On macOS arm64 with Python 3.11.18 and GDAL 3.10.3, the synthetic rows and
runs SHA-256 were respectively
`fa311f33642523204236c02d8f7d23309174347304e8412d76e126643480c9dc`
and `e068228e97fa80bde0f7d937dc62e26c7ae36330604369c22459f1fea5079091`.
Temporary request paths make request hashes run-specific. No map rebuild or
Neon write occurred.

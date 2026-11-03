# V7 source recovery

These files preserve selected WorldAtlas V7 processing and audit source. They are historical recovery material, not a ready-to-run pipeline.

## Provenance

The ocean fill script, partition core, RLE input module, and the repository's `scripts/exclusive_outputs.py` match the hashes recorded when the final ocean-fill run launched. The closed-water classifier matches the hash in the final closed-water audit. The shore-audit and coastal scripts are preserved to retain source and dependencies; their inclusion here does not establish that this directory alone reproduces the published result.

## Recovery limitations

The scripts retain their original assumptions about directory layout, inputs, software dependencies, and run identifiers. Some import other modules not yet included in this directory. Do not run them against existing output directories: intermediate and final output files must not be overwritten. Use a new run directory for every run or retry.

The full V7 source dependency chain, pinned input locations, environment versions, and an isolated end-to-end rebuild have not yet been verified. The V7 release-builder accounting-file fix has a focused test, but a complete build from this checkout has not been run. Generated maps and large inputs are stored separately, not in this repository.

Before attempting a rebuild, identify and verify the actual inputs and remaining source dependencies, then run focused checks and a complete build in a new directory. Do not assume an unverified script variant was used in the published build.

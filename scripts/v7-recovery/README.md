# V7 source recovery

These files preserve selected WorldAtlas V7 processing and audit source. They are historical recovery material, not a ready-to-run pipeline.

## Provenance

The preserved partition core, RLE input module, and the repository's `scripts/exclusive_outputs.py` match the hashes recorded when the final ocean-fill run launched.

## Recovery limitations

The scripts retain their original assumptions about directory layout, inputs, software dependencies, and run identifiers. Some import other modules not yet included in this directory. Do not import or run these archival scripts as-is: some create directories at import time or write fixed output and cache paths. Intermediate and final output files must not be overwritten. Before any execution, make the code use a new run directory for every run or retry, including caches, and verify exclusive output handling.

The full V7 source dependency chain, pinned input locations, environment versions, and an isolated end-to-end rebuild have not yet been verified. The V7 release-builder accounting-file fix has a focused test, but a complete build from this checkout has not been run. Generated maps and large inputs are stored separately, not in this repository.

Before attempting a rebuild, identify and verify the actual inputs and remaining source dependencies, then run focused checks and a complete build in a new directory. Do not assume an unverified script variant was used in the published build.

## Known source gaps

The historical coastal manifest identifies three source versions: v2, v3 and v4. Some tiles used each version, and exact source-level reproduction is not established. Those historical water scripts are outside the current land-only work.

The final composition and V2-difference outputs have input/output provenance, but their exact executable versions have not been established. Do not describe a candidate script as the version used without further evidence.

The V6 UI dependency files in this directory are local candidates. Their bytes have not been compared with the separately hosted V6 modules used by the published V7 page.

The shipped metadata also cites an independent closed-water QA file by hash, but that file was not found at its recorded path or in the V7 archives checked. This is an evidence gap; the builder does not read that file as an input.

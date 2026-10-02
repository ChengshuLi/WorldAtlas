# Exhaustive repaired-world fixed-grid assessment

This assessment uses the frozen repaired macro stage, **49,589 locations**, with footprint hash `5d7236fe7e9d2f83c07c0b5cc1d5e703bf685f860fd49c850edd18eea27c61a8`. Complete macro hierarchy hash is `bb083958f4ccee3ca1aa4b9d0392433a79c4ebbf023c873168c0900ca4a36d58`. It includes all inspected source-identity unions and the full licensed Vatican footprint; it does not use their superseded tiny fragments. Every location is evaluated at every candidate, including newly disappearing locations, not only the old omission list.

| Fixed zoom | Width | Missing locations | WGS84 area errors above 25% | Projected errors above 25%, source at least one cell |
| --- | ---: | ---: | ---: | ---: |
| 7 | 32,768 | 50 | 202 | 118 |
| 8 | 65,536 | 9 | 55 | 43 |
| 9 | 131,072 | 1 | 9 | 8 |
| 10 | 262,144 | 0 | 0 | 0 |

**Zoom 10 is the coarsest fully compiled candidate meeting the numeric screen**: every current location receives an actual collision-resolved canonical cell, and every current location has projected and WGS84 area errors within 25%. Maximum WGS84 relative error is 21.998034%. Zoom 9 still loses Bajo Nuevo Bank; the coarser grids are unsuitable without separately sourced aggregation decisions. Finer cell-center alignments are not nested, so exhaustive world compilation is required.

The grid has 28,796,247 ownership runs. Compact version 2 uses **232,467,128 permanent CPU bytes**, **232,488,960 padded GPU bytes** under its default layout, and **47,562,760 bytes of byte-shuffled gzip transport**. Every one of **58,116,782 decoded integer words** was compared exactly. Preparation peak RSS was about 3.20 GB; that preparation happens outside browser navigation. A selected canonical cell owns precisely one location ID, irrespective of polygon boundary slivers. Every province membership and every canonical location bound is packaged alongside the stage; province memberships are geographic and independent of the selected historical owner.

The default 2,048-wide run texture is 7,031 rows. The adaptive renderer expands it to 4,096 columns on a device limited to 4,096, making its run texture 3,516 rows without changing ownership. Actual shader compilation, source interior pixels and zero navigation uploads are checked against the staged assets in Chromium WebGL2, including a simulated texture limit of 4,096. Device simulation verifies this addressing/layout path; it does not establish physical mobile hardware memory capacity or frame rates. Real mobile memory validation remains open because the compact arrays plus GPU copy are substantial.

All source/vintage issues remain separate. Namibia's 2007 constituency coordinates/names still require a verified licensed replacement; showing their current source polygons on a finer grid is not approval of those polygons. The exhaustive source-identity audit inventories every Namibian location, and the grid report retains their flags. Marshall island source-to-land differences also remain open where marine territory and coastline-vintage differences need evidence. Zero grid IDs denote water **or a source coverage gap**, never a claim of unowned land. This screen proves representation of the current footprint set; it does not certify complete dry-land coastline coverage or globally completed semantics.

## Durable results and reproducibility

`data/final-grid-resolution-review.json.gz` stores all location IDs, source WGS84 areas, candidate cell counts and grid WGS84 areas, exact omissions/distortion lists, source-algorithm hashes, timing and memory results. `data/final-grid-rendering-review.json` contains actual browser GPU/load/navigation measurements and simulated-versus-native device limits. The files are independent of `.cache` and should be retained with the geographic release.

```sh
node scripts/audit-grid-resolutions.mjs \
  --world-index=.cache/macro-boundary-repair-stage/after/world-index.json \
  --cache=.cache/final-grid-assessment \
  --report=data/final-grid-resolution-review.json.gz \
  --zooms=7,8,9,10 --isolated-max-zoom=14
node scripts/stage-canonical-grid.mjs \
  --world-index=.cache/macro-boundary-repair-stage/after/world-index.json \
  --cache=.cache/final-grid-assessment --zoom=10 \
  --output=.cache/final-grid-benchmark
node test/compact-ownership-benchmark.mjs --assets-only --zooms=10 \
  --directory=.cache/final-grid-benchmark --device-limit=4096
node test/compact-ownership-benchmark.mjs --assets-only --zooms=10 \
  --directory=.cache/final-grid-benchmark
```

For a fresh thread after installation, substitute the pinned Git `data/world-index.json` in these commands; both compile scripts accept explicit input snapshots. The geography footprint hash must match this report before reuse. Compilation outputs are staged and do not activate a resolution. Activation must consistently update the renderer's canonical `GRID_ZOOM`, use the selected immutable asset manifest, match hierarchy/footprint hashes, and pass actual hosting asset-size and whole-location rendering gates. Zoom/pan/resize must reuse the same assets, with zero ownership recompilations or uploads. Physical-device memory limitations and semantic source gaps must remain visible in coverage reporting.

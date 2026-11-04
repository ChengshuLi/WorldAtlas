# Provisional land comparison against preserved V2

This is an independent comparison of a completed, source-derived research land grid against the preserved V2 assignment grid. The V2 and V7 grids/ledger were never inputs to the candidate assignment build. The result is not a full land-and-water reconstruction, a legal boundary, or proof of V2's original algorithm. The candidate uses a provisional physical input with the earlier OSM-only Overture filter, plus V5-derived mainland cuts and exploratory water closures; original V2 source cut and exact raster/tie behavior are not recovered.

The two grids share 1,984,468,734 land cells. They agree by continent on 1,984,418,935 (99.9975%) and differ on 49,799. Separately, 305 cells are candidate land/V2 water and 369 are candidate water/V2 land. These 674 physical differences are not included in the 49,799.

## Why most of the 49,799 differ

- The candidate has 48,493 V2-Asia→candidate-Europe cells. Of those, 48,488 occur in the candidate's source-derived mainland seed and five outside it. The main effect is therefore the mainland partition, not the generic nearest-island fallback.
- A spatial group around the Caucasus (37.32–49.32°E, 40.82–44.91°N) accounts for 43,636 continent differences. Its count includes 43,554 Asia→Europe and 82 Europe→Asia cells. This cluster is defined by touching occupied ~0.099° grid bins, not by an authoritative geographic boundary.
- In a slightly rounded Caucasus diagnostic box, 43,553 seeded Asia→Europe cells occur. The independently checked V2→V7 land-change ledger records 41,815 as part of the later Europe–Asia mainland adjustment, with V7 matching the candidate. The other 1,738 retain the V2 category in V7. All 1,738 lie within ~153 m of the candidate Caucasus source cut (median ~53 m, EPSG:32638 planar approximation). A thin fringe is consistent with raster or small route differences, but the precise mechanism is not proven.
- As a contrast, among every 20th seeded Asia→Europe cell in the same box, median distance to the candidate cut is ~16 km and the 95th percentile ~46 km (2,178 samples). The broad difference is consistent with an intervening boundary convention, not merely a single-cell tie.
- Across all 49,799 land-continent differences, 42,025 carry the candidate class in V7 and 7,774 carry the original V2 class in V7. These are overlap observations, not a claim that every later decision is correct or that the candidate exactly reproduces V7.
- Other principal clusters include 3,672 cells along the Urals, 1,359 in the Ural River/Caspian lowlands, and 297 around the Panama–Colombia cut. The largest physical cluster has 593 changes around Hudson Strait. Smaller offshore differences are included, with no named-island exception in the candidate algorithm.

`v2-land-differences.html` is a self-contained interactive map. Its 42,025/7,774/674 color totals are checked against the span data; the background is a coarse center-sampled rendering for orientation. Open it locally and use the filter, cluster buttons, drag/zoom and click cell details. Green line is the candidate Caucasus cut, not a recovered V2 line. `node test_map.cjs` checks embedded counts, controls and canvas-call behavior; it is not a visual browser test.

`spans.tsv` contains exact half-open cell spans (`row`, `start`, `end`, old code, candidate code, candidate seed code). `report.json`, `clusters.json`, `ledger-overlap.json`, `caucasus-review-overlap.json`, `caucasus-distance.json`, and `caucasus-remainder-distance.json` preserve the comparison summaries and input digests. `extract_differences.py` produces the spans; subsequent scripts produce clusters, compare the saved ledger, and measure candidate-route distances. These research scripts currently use explicit local paths and require the pinned input grids; they are not a portable raw-source reconstruction.

The `report.json` here is the span-export report, while the independently generated whole-grid comparison report is `comparison-report.json`. The latter checks every row and includes the full transition matrix. Saved V2 row/run SHA-256: `f254d5ace508252f1a250d72e62073093b9ad8d0e1a6a6a66e6db96aa7f70a7f` / `1ea99e7823944d2510681c2e257e0db62b3fdfc8009c34abeb7222b3f6f5aef2`. Candidate row/run SHA-256: `a7e7a10d141c7bfc0517b003033114282c97251e77a11329da7d1ca8e023c6c0` / `2c67f4c4f31dfe109cbfdf3bfb0704c8960d6e5ff6bd2457e14d2356026969d6`.

## Reproduce the analysis

The scripts accept explicit input and output paths; use new output paths. The candidate directory needs `rows.u32le` and `runs.u32le`; the reference directory needs `v2-rows.u32` and `v2-runs.u32`; the seed directory needs `rows.u32le` and `runs.u32le`. Inputs must be the exact pinned versions; inspect each generated report and compare hashes before interpreting results. The candidate is a derived research result, not raw inputs.

```sh
python3 extract_differences.py --candidate-dir CANDIDATE --reference-dir V2_RAW --seed-dir SEED --output-dir OUTPUT
python3 cluster_differences.py --spans OUTPUT/spans.tsv --output OUTPUT/clusters.json
python3 compare_review_ledger.py --spans OUTPUT/spans.tsv --ledger LAND_LEDGER.gz --member-index LAND_MEMBER_INDEX.json --output OUTPUT/ledger-overlap.json
python3 caucasus_review_overlap.py --spans OUTPUT/spans.tsv --ledger LAND_LEDGER.gz --output OUTPUT/caucasus-overlap.json
python3 caucasus_remainder.py --spans OUTPUT/spans.tsv --ledger LAND_LEDGER.gz --output OUTPUT/caucasus-remainder.tsv
python3 caucasus_distance.py --spans OUTPUT/spans.tsv --source SOURCE_CUTS.geojson --output OUTPUT/caucasus-distance.json
python3 caucasus_distance.py --spans OUTPUT/caucasus-remainder.tsv --source SOURCE_CUTS.geojson --sample-stride 1 --output OUTPUT/remainder-distance.json
python3 build_change_map.py --spans OUTPUT/spans.tsv --ledger LAND_LEDGER.gz --candidate-dir CANDIDATE --source SOURCE_CUTS.geojson --clusters OUTPUT/clusters.json --output OUTPUT/map.html
node test_map.cjs OUTPUT/map.html
```

The distance step requires GDAL/OGR Python bindings and NumPy; extraction and map building additionally use NumPy and Pillow. `comparison-summary.json` is a path-free copy of the independently generated full-grid comparison, with its original report digest. `comparison-report.json` and `config.json` are local runtime records, not needed in a portable source release.

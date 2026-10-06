# Matanuska–Susitna physical seam source evidence

Issue #1205 asks whether the 282 declared interior seam components can be assigned to source-backed physical coverage. This packet preserves exact source records and a reproducible diagnostic comparison. It does not approve geography, assign an administrative owner, repair geometry, or authorize an import.

## Scope and pinned selection

The baseline is `cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1`. The selected roster is every row in the 34 immutable `investigations-*.json.gz` shards whose `partition` starts with `interior` and whose sorted `positive_length_neighbor_ids` equal `atlas:physical:2a15134ff18942dc8e5e` and `atlas:physical:a20d41a6587ce2e2996b`. It yields 282 unique component IDs; the compact JSON roster hash recorded by issue #1205 is `37b5efeb08f407cd19cc098186659a01899d748d8dd73b3c26bfccbd1d35fc66`.

The source overlay output retains those 282 full component geometries, all 283 bound candidate-fragment geometries, the complete component-to-fragment contact ledgers, and exact `exact_location_contacts` records. The geometry shapes are from the component custody aliases and detection-v4 candidates pinned at the baseline commit. Custody payload bytes were checked against their original file hashes before use.

## Sources and versions

* **geoBoundaries USA ADM2, full-resolution:** the complete exact #486 capture is pinned as a 10,500,644-byte issue-baseline input, SHA-256 `81fdd384df8012e5007ed2994a8ab306352f3c48e32cd8ea99182195e8647f43`, CRS84. The immutable release commit is `9469f09592ced973a3448cf66b6100b741b64c0d`; release metadata records boundaryYear 2018 and Public Domain. Only Matanuska–Susitna (`52423323B34523976645917`) and Denali (`52423323B25289890288494`) full-resolution features are extracted in this packet. This is retained as a distinct comparison product.
* **geoBoundaries USA ADM2, simplified:** the complete 3,233-feature product used by the issue-baseline `scripts/administrative.py` source loader is retained (7,938,450 bytes; SHA-256 `16249e8d795aaded6a72910a8c72115a073814b25ee902d61ccc9a9490c6641a`) from the same immutable release commit. That loader transforms the USA ADM2 `gjDownloadURL` to the `_simplified.geojson` path before downloading it. Release metadata records boundaryYear 2018, sourceDataUpdateDate 2023-01-19, buildDate 2023-12-12, and Public Domain. The same two shapeIDs and attributes appear in both product versions, but their geometries differ. Both product comparisons are retained separately below; neither proves Atlas output lineage or positional registration.
* **RESOLVE Ecoregions and Biomes:** the inherited source locator authenticates as ArcGIS item `37ea320eebb647c6838c23f72abae5ef`; the string with a trailing `2` was also queried and returned `CONT_0001` (“Item does not exist or is inaccessible”). The authentic item is CC BY 4.0, and its layer is “Biomes and Ecoregions 2017”. Captured layer metadata reports the last data edit as 2022-01-27; the item’s 2026 modification date is not a data-vintage assertion. Complete official query geometries for ECO_ID 371 (Cook Inlet taiga) and ECO_ID 405 (Alaska–St. Elias Range tundra) are retained with response receipts.
* **ECO_ID 0 (Rock and Ice):** the official query returned HTTP 200, but the complete response exceeded the 32 MiB per-file evidence cap. Only the first 32 MiB was read, its partial hash and scope are recorded in `sources/resolve-ecoid-0-receipt.json`, and those bytes were discarded. This is not a retained geometry or a complete source response. No Rock and Ice classification is inferred from its absence.

The four exact native contact subjects and their retained Atlas reference year are distinct from source dataset vintages. In particular, `reference_year: 2018` on the Atlas boundary feature does not change RESOLVE’s 2017 layer label or its 2022 data-edit metadata. The source locator itself is also retained in the exact contact records; this packet does not repin or repair it.

## Diagnostic results

Across the exact 282-component roster, unprojected planar Shapely comparisons in EPSG:4326 reported the separate full-resolution and simplified geoBoundaries predicates below. The latter is the product selected by the baseline administrative loader:

| Source feature | Predicate | Count |
| --- | --- | ---: |
| Matanuska–Susitna full-resolution ADM2 | intersects | 281 |
| Matanuska–Susitna full-resolution ADM2 | covers component | 279 |
| Denali full-resolution ADM2 | intersects | 3 |
| Denali full-resolution ADM2 | covers component | 1 |
| Matanuska–Susitna simplified ADM2 input | intersects | 281 |
| Matanuska–Susitna simplified ADM2 input | covers component | 279 |
| Denali simplified ADM2 input | intersects | 3 |
| Denali simplified ADM2 input | covers component | 1 |
| Matanuska full/simplified intersect status changes | components | 0 |
| Matanuska full/simplified covers status changes | components | 0 |
| Matanuska full/simplified positive-area status changes | components | 0 |
| Denali full/simplified intersect status changes | components | 0 |
| Denali full/simplified covers status changes | components | 0 |
| Denali full/simplified positive-area status changes | components | 0 |
| RESOLVE ECO_ID 371, Cook Inlet taiga | intersects | 0 |
| RESOLVE ECO_ID 371, Cook Inlet taiga | covers component | 0 |
| RESOLVE ECO_ID 405, Alaska–St. Elias Range tundra | intersects | 227 |
| RESOLVE ECO_ID 405, Alaska–St. Elias Range tundra | covers component | 40 |

Although the selected full-resolution and simplified polygons differ geometrically, for these 282 components each product yields the same per-component intersects, covers, and positive-area-intersection booleans for both selected ADM2 features (zero changed component predicates). This bounded result does not establish that the two complete products are generally interchangeable.

These are geometric observations in the source coordinate plane, not physical area measurements, ownership assignments, or proof of how any component was formed. No reprojection, snapping, tolerance, repair, closest-owner rule, or water/ice forcing was applied. The exact source-contact ledgers contain 571 contact rows across 283 fragments: ECO_ID 405 appears 283 times, Rock and Ice 283 times, ECO_ID 371 four times, and Denali once. Those contact rows are retained as source evidence, not interpreted as source-polygon coverage.

Because the complete ECO_ID 0 geometry was not available under the unchanged byte cap, the physical class of components whose proposed explanation depends on Rock and Ice remains unresolved. Likewise, polygon intersection or coverage alone does not establish an administrative owner or a source lineage. The output is evidence for the bounded source question only; it is not a global geometry correction or the later #1184 native-grid approval.

## Coordinate precision and registration

The retained geoBoundaries and ArcGIS metadata identify coordinate reference systems and axis order, but do not report authoritative XY resolution/tolerance or positional accuracy/registration values. Both full-resolution and simplified geoBoundaries products are pinned as separate byte sequences; their selected features differ geometrically. No rounding, reprojection, snapping, or registration adjustment was applied. The predicates therefore describe each supplied product independently and do not establish cross-product or cross-source alignment accuracy.

## Reproduction

Run `reproduce-source-overlays.py` with Python 3.12, Shapely 2.1.2, and the pinned baseline commit available in the Git object database. The script checks the complete 282-member roster, custody payload hashes, source feature IDs, exact contact closure, and then writes the selected component geometries and full ledger. All derived output paths are new files under this issue-owned directory.

## Archived processing hypothesis (not causal proof)

The issue-baseline copy of `scripts/refine-remote.py` is retained at `sources/refine-remote.py` (7,440 bytes, SHA-256 `6a6a5258328aa1153d567d9a98b90339421700d491f36fbdca216d3e0cbc2726`). It shows the repository's remote refinement recipe using `make_valid`, topology-preserving simplification at `0.001` degrees, overlays/differences with `grid_size=1e-8`, omission of intersection pieces under 5 km², and coastline buffer bands from `0.001` through `0.1` degrees. Its source builder also includes Natural Earth lakes. These operations are plausible sources of seam/coverage differences, but this snapshot alone does not prove they created any of the 282 components: the execution commit, exact cache inputs, and per-feature lineage through each operation must be established separately. The issue ledger therefore keeps every physical cause `unknown` rather than attributing it to the recipe.

## Exact recorded subject lineage

At the issue baseline, the exact containing-file pin for current subject features is `data/geography/part-26.json` (4,608,983 bytes; SHA-256 `44de5da3531f5641e0496ab7b01ed73871b40705e2a3eafdda470926872b6632`). The three native features are indexes 1290, 1291, and 1293; all record the same original member `gb:USA:ADM2:52423323B34523976645917`. Their source IDs are respectively `resolve:405`, `resolve:371`, and `resolve:0`. The pinned `refine-remote.py` implementation hashes the original administrative feature ID joined to the stringified `ECO_ID`, then uses the first 20 hex characters for the stable `atlas:physical:` ID. All three recorded IDs match that formula. Their `reference_year: 2018` is retained metadata and does not date the RESOLVE source geometry.

All three feature records also carry the same eight coastline-adjustment metadata entries (distance bands from `0.001` through `0.05` degrees, with their recorded area summaries). This links the metadata to the shared predecessor feature; it does not identify which exact output fragments any buffer changed. The source-token identity therefore checks out against the recorded implementation, while physical coverage, processing causation, and full Rock and Ice geometry remain unresolved. Exact file and per-feature hashes are in `sources/historical-subject-lineage.json`.

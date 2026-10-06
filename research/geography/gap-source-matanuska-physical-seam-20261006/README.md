# Matanuska–Susitna physical seam source evidence

Issue #1205 asks whether the 282 declared interior seam components can be assigned to source-backed physical coverage. This packet preserves exact source records and a reproducible diagnostic comparison. It does not approve geography, assign an administrative owner, repair geometry, or authorize an import.

## Scope and pinned selection

The baseline is `cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1`. The selected roster is every row in the 34 immutable `investigations-*.json.gz` shards whose `partition` starts with `interior` and whose sorted `positive_length_neighbor_ids` equal `atlas:physical:2a15134ff18942dc8e5e` and `atlas:physical:a20d41a6587ce2e2996b`. It yields 282 unique component IDs; the compact JSON roster hash recorded by issue #1205 is `37b5efeb08f407cd19cc098186659a01899d748d8dd73b3c26bfccbd1d35fc66`.

The source overlay output retains those 282 full component geometries, all 283 bound candidate-fragment geometries, the complete component-to-fragment contact ledgers, and exact `exact_location_contacts` records. The geometry shapes are from the component custody aliases and detection-v4 candidates pinned at the baseline commit. Custody payload bytes were checked against their original file hashes before use.

## Sources and versions

* **geoBoundaries USA ADM2:** the exact archived #486 source is 10,500,644 bytes, SHA-256 `81fdd384df8012e5007ed2994a8ab306352f3c48e32cd8ea99182195e8647f43`, CRS84 (longitude/latitude). The source was retrieved from the immutable `9469f09592ced973a3448cf66b6100b741b64c0d` release commit. Only Matanuska–Susitna (`52423323B34523976645917`) and Denali (`52423323B25289890288494`) features are retained here. The source represents a 2018 boundary vintage; its reuse metadata identifies public-domain terms.
* **RESOLVE Ecoregions and Biomes:** the inherited source locator authenticates as ArcGIS item `37ea320eebb647c6838c23f72abae5ef`; the string with a trailing `2` was also queried and returned `CONT_0001` (“Item does not exist or is inaccessible”). The authentic item is CC BY 4.0, and its layer is “Biomes and Ecoregions 2017”. Captured layer metadata reports the last data edit as 2022-01-27; the item’s 2026 modification date is not a data-vintage assertion. Complete official query geometries for ECO_ID 371 (Cook Inlet taiga) and ECO_ID 405 (Alaska–St. Elias Range tundra) are retained with response receipts.
* **ECO_ID 0 (Rock and Ice):** the official query returned HTTP 200, but the complete response exceeded the 32 MiB per-file evidence cap. Only the first 32 MiB was read, its partial hash and scope are recorded in `sources/resolve-ecoid-0-receipt.json`, and those bytes were discarded. This is not a retained geometry or a complete source response. No Rock and Ice classification is inferred from its absence.

The four exact native contact subjects and their retained Atlas reference year are distinct from source dataset vintages. In particular, `reference_year: 2018` on the Atlas boundary feature does not change RESOLVE’s 2017 layer label or its 2022 data-edit metadata. The source locator itself is also retained in the exact contact records; this packet does not repin or repair it.

## Diagnostic results

Across the exact 282-component roster, unprojected planar Shapely comparisons in EPSG:4326 reported:

| Source feature | Intersections | Source polygon covers component |
| --- | ---: | ---: |
| Matanuska–Susitna ADM2 | 281 | 279 |
| Denali ADM2 | 3 | 1 |
| RESOLVE ECO_ID 371, Cook Inlet taiga | 0 | 0 |
| RESOLVE ECO_ID 405, Alaska–St. Elias Range tundra | 227 | 40 |

These are geometric observations in the source coordinate plane, not physical area measurements, ownership assignments, or proof of how any component was formed. No reprojection, snapping, tolerance, repair, closest-owner rule, or water/ice forcing was applied. The exact source-contact ledgers contain 571 contact rows across 283 fragments: ECO_ID 405 appears 283 times, Rock and Ice 283 times, ECO_ID 371 four times, and Denali once. Those contact rows are retained as source evidence, not interpreted as source-polygon coverage.

Because the complete ECO_ID 0 geometry was not available under the unchanged byte cap, the physical class of components whose proposed explanation depends on Rock and Ice remains unresolved. Likewise, polygon intersection or coverage alone does not establish an administrative owner or a source lineage. The output is evidence for the bounded source question only; it is not a global geometry correction or the later #1184 native-grid approval.

## Reproduction

Run `reproduce-source-overlays.py` with Python 3.12, Shapely 2.1.2, and the pinned baseline commit available in the Git object database. The script checks the complete 282-member roster, custody payload hashes, source feature IDs, exact contact closure, and then writes the selected component geometries and full ledger. All derived output paths are new files under this issue-owned directory.

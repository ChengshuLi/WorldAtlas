# Exhaustive source-territory identity audit and land-repair proposals

The dry-run scans **all 49,614 current locations**, follows every direct and nested source-member identity, and records a resolved source key for every location. The result contains **67,257 distinct provenance identities and 1,083 repeated identities**. It does not mistake reuse of a source county by independent ecological subdivisions for duplicate geography. No current world feature, hierarchy, database claim or prepared record is modified.

Reproduce with:

```sh
python scripts/audit-source-territory-splits.py
```

The compressed report is `data/source-territory-splits.json.gz`. Every current location ID and source atom is inventoried. Source-file hashes, normalized canonical WKB hashes, input-part hashes, before/after IDs and geometry-file hashes make proposals inspectable and reject stale inputs. The script fails if geography changes while it runs. Its areas use the existing **WGS84 latitude-strip integral**, including antimeridian canonicalization, not a longitude/latitude planar approximation.

## General defect and exhaustive classification

| Classification | Source identities | Disposition |
| --- | ---: | --- |
| Intentional named physical/ecological subdivisions | 1,057 | Preserve independently sourced subdivisions; shared provenance is not grounds for merging. This does not approve their granularity or footprints. |
| Exact named source units split solely by political-reference masks | 16 | 12 Somali district pairs and four Morocco/Western Sahara province pairs have explicit existing-footprint union proposals. |
| Mixed ecological subdivision plus political-reference fragment | 1 | Boujdour requires a complete sourced ecological partition; collapsing its three physical locations would discard meaningful geography. |
| Unnamed/bad source replaced by named OSM district geography | 9 | Preserve independently matched Turkmen/Afghan source corrections; do not reconstitute anonymous source polygons. |

The 16 simple cuts come from `semantic-locations.py`, which intersected a single original SOM/MAR source shape with an independent `SOL+00?`/`SAH+00?` political envelope. A geography location should retain that coherent named source identity and resolve one owner separately. This is a worldwide provenance scan, not a special Borama fix.

The additional cross-collection audit accounts for **all nine** retained US parent-collection / American Samoa / Northern Mariana duplicates: five named Samoan districts/islands and four Mariana municipalities. It preserves both inspected original source vintages. Mariana matches have unique smaller-footprint overlap of 97.68–99.11%. American Samoa shows larger source-vintage differences: Western 87.32%, Manuʻa 64.59%, and Rose Island/Atoll are disjoint by a narrow coastline offset despite representing the same named atoll. Those counterparts are justified by named source identity and full original footprints, not a nearest-cell or nearest-town assignment. Their coastline and possible water-footprint differences remain visible for independent review.

## Existing-footprint union proposals

There are **25 union proposals**, comprising the 16 political-mask cases and nine duplicated territorial collections. **23 have no measured overlap with unrelated current locations**. Two Moroccan cases preserve existing numerical overlaps of approximately **0.913 m² and 0.929 m²** with named Mauritanian physical neighbours; they remain blocked pending explicit numerical topology reconciliation. All union proposals add **zero land** to current coverage. Original-source growth is never automatically substituted for the current union.

| Current duplicate names | Retained ID | Union km² | Original source covered | Modern reference evidence | Status |
| --- | --- | ---: | ---: | --- | --- |
| Province d'Aousserd إقليم أوسرد + Province d'Aousserd إقليم أوسرد | `gb:MAR:ADM2:96644757B25593504689486` | 61001.456683 | 99.9219% | Morocco | exact-union-ready |
| Assa-Zag Province + Assa-Zag Province | `gb:MAR:ADM2:96644757B62254917052717` | 21210.369081 | 99.9701% | Morocco | exact-union-ready |
| Province d'Es-Semara إقليم السمارة + Province d'Es-Semara إقليم السمارة | `gb:MAR:ADM2:96644757B70524131405695` | 65082.277701 | 99.9927% | Morocco | blocked-neighbor-overlap |
| Oued Ed-Dahab Province + Oued Ed-Dahab Province | `gb:MAR:ADM2:96644757B78111329468616` | 67592.436587 | 99.6807% | Morocco | blocked-neighbor-overlap |
| BOSSASO + BOSSASO | `gb:SOM:ADM2:84685775B12579203226949` | 6388.262857 | 99.9587% | Somalia | exact-union-ready |
| BERBERA + BERBERA | `gb:SOM:ADM2:84685775B1722628585645` | 16044.721241 | 99.9987% | Somaliland | exact-union-ready |
| LAS ANOD + LAS ANOD | `gb:SOM:ADM2:84685775B17415415044999` | 14628.962017 | 99.9984% | Somaliland | exact-union-ready |
| GAROWE + GAROWE | `gb:SOM:ADM2:84685775B27146927901695` | 11465.022321 | 99.9244% | Somalia | exact-union-ready |
| ERIGAVO + ERIGAVO | `gb:SOM:ADM2:84685775B34990175799989` | 12815.594212 | 99.9985% | Somaliland | exact-union-ready |
| BURTINLE + BURTINLE | `gb:SOM:ADM2:84685775B35872588308283` | 2767.005071 | 71.7305% | Somalia | exact-union-ready |
| BORAMA + BORAMA | `gb:SOM:ADM2:84685775B41100750476456` | 1746.939379 | 99.1030% | Somaliland | exact-union-ready |
| BURAO + BURAO | `gb:SOM:ADM2:84685775B49158080079573` | 13416.779402 | 100.0000% | Somaliland | exact-union-ready |
| ZEILA + ZEILA | `gb:SOM:ADM2:84685775B58560427797094` | 7235.265484 | 99.9682% | Somaliland | exact-union-ready |
| BADHAN + BADHAN | `gb:SOM:ADM2:84685775B5876262576033` | 22945.082517 | 99.9989% | Somaliland | exact-union-ready |
| TALEH + TALEH | `gb:SOM:ADM2:84685775B65673290719307` | 11536.365818 | 99.9980% | Somaliland | exact-union-ready |
| BUHODLE + BUHODLE | `gb:SOM:ADM2:84685775B82555432245075` | 5073.363922 | 99.9996% | Somaliland | exact-union-ready |
| Swain's Island + Swains Island | `ASM-5001` | 3.218416 | 88.1412% | United States of America | exact-union-ready |
| Western + Western | `ASM-5002` | 90.827794 | 98.9515% | United States of America | exact-union-ready |
| Rose Atoll + Rose Island | `ASM-5000` | 4.349933 | 74.6369% | owner:Q30 (source-record reference) | exact-union-ready |
| Manu's + Manu'a | `ASM-4999` | 82.455328 | 98.5794% | United States of America | exact-union-ready |
| Eastern + Eastern | `ASM-4998` | 83.665391 | 91.2112% | United States of America | exact-union-ready |
| Rota + Rota | `gb:MNP:ADM2:39175420B64217482742742` | 93.995392 | 99.9764% | United States of America | exact-union-ready |
| Saipan + Saipan | `gb:MNP:ADM2:39175420B42755231479115` | 142.978789 | 99.9815% | United States of America | exact-union-ready |
| Tinian + Tinian | `gb:MNP:ADM2:39175420B24162802066299` | 121.262241 | 99.9857% | United States of America | exact-union-ready |
| Northern Islands + Northern Islands | `gb:MNP:ADM2:39175420B77088391070908` | 188.835355 | 96.7047% | United States of America | exact-union-ready |

The report distinguishes two modern evidence methods: strict whole-footprint majority against independent pinned reference boundaries, and majority of current source-record footprints carrying the same stable reference polity. For example, all US/territory source records identify the same polity, while the coarse Natural Earth mask may cover only part of their finer coastlines. Both evidence sets remain inspectable. Reference data is not silently promoted to ancient ownership or a verified 2026 political snapshot. Missing majority, conflicts and uncertain reference classification remain explicit.

Union identity is separate from full source-boundary approval. **Borama** reunites a roughly 1.24 km² Somalia fragment with the much larger Somaliland fragment under one named source identity. The resulting current union is 1,746.939379 km², with 99.103% of the original 1,575.070881 km² source polygon covered; earlier bounded coastline adjustments also extended outside that polygon. **Burtinle** current coverage represents only about 71.73% of its raw source polygon. The report measures whole-original-source overlap with every other neighbour so these differences cannot be silently repaired by growth. They remain source/vintage/coverage work even after removal of the political cut.

## Vatican: inspected full-territory correction

The original premise that the pinned Natural Earth file contained a 0.44 km² Vatican territory was incorrect. **Both actual pinned ADM0 and ADM1 geometries are the same 0.0122058 km² cartographic placeholder.** Subsequent topology reduced the active location to 0.0105656 km². Switching source layers cannot fix it. The WGS84 result was cross-checked with pyproj equal-area projection and Geod.

The proposed correction uses the actual [OpenStreetMap relation 36989](https://www.openstreetmap.org/api/0.6/relation/36989/full.json), **version 117, edited 2026-07-31**, identifying `ISO3166-1:alpha3=VAT`, `wikidata=Q237`, and `official_name:en=Vatican City State`. Its **nine outer ways** were joined by their exact node IDs and polygonized without rescaling, buffering or an area target. The resulting valid polygon is **0.491620986 km²** and is geometrically identical to the independently retrieved Nominatim polygon. The source is [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) with © OpenStreetMap contributors attribution.

An independently inspected [gbOpen VAT ADM0 source](https://www.geoboundaries.org/api/current/gbOpen/VAT/ADM0/) has canonical role **Vatican City**, represented **2017**, public-domain license and a complete 0.512054239 km² polygon. It corroborates the full territory while exposing vintage/generalization differences; it does not override the newer OSM relation. The official Vatican geography request returned 403 and is not counted as inspected primary evidence.

The explicit repair retains `VAT+00?` and `atlas:location:ITA:SLL:1209` (Roma), assigns the licensed full Vatican footprint to the former, and subtracts its occupied land from the latter. **The proposed territory is entirely within the existing Vatican/Roma union, so this adds zero world land.** Both before/after hashes and polygons are in the receipt. The full-territory source directly identifies reference polity Q237; the superseded coarse NE mask's erroneous majority is also retained for transparency. No historical owner, culture, rank or population is inferred from the modern source tags. Grid representation must be rechecked after migration.

## Bad source coordinates and preserved history

All 111 current Namibian IDs are inventoried in `namibia_source_profile`; known problematic 2007-source locations include Hakahana, Uuvudhiya, Okankolo, Uukwiyu and Oshakati West. The small polygons and mismatched named/coordinate contexts require an independently verified licensed replacement source. **No 2007 polygon is grown just to gain a grid cell.** Five known flags are not a claim that the rest of Namibia has completed semantic review.

The proposed union/Vatican sets affect **52 existing IDs**, **2,268 prepared ownership intervals** and **309 prepared environmental/reference rows**. Read-only SQLite checks found no direct states, sourced attribute claims or entity-history rows on these IDs. This does not certify separately imported hosted claims: they require an independent publication-time check.

Every migration must:

1. Archive each before footprint, source hash, original name, parent chain and retired ID; the original archive hash is in the report.
2. Keep direct/history records on their original IDs and footprint context; never copy retired-ID evidence to a retained location merely because polygons are united.
3. Recompute source-derived ownership and environmental summaries only for the explicitly changed footprints, preserving unchanged records and export dictionaries.
4. Record geographic publication/version applicability and source-supported intervals. Reference source dates cannot manufacture historic names, rank or ownership.
5. Verify all after polygons, exact coverage, unrelated-neighbour overlaps, complete hierarchy chains, archived-record preservation and canonical-grid representation before publishing.

No source shape, country mask, inferred owner or statistical quota alone closes semantic geography. The report supplies concrete general corrections while retaining independent boundary, vintage, granularity and historical-evidence gaps.

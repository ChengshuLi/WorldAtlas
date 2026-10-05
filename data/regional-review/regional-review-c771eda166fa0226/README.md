# West Africa interior batch 5 geography evidence

**Issue:** [#471](https://github.com/ChengshuLi/WorldAtlas/issues/471)  
**Baseline main:** `7ffd4e35364ec8246b9add7459378b3f971fcd72`  
**Scope:** exactly 216 pinned location IDs, 18 province scopes, and three areas. This is a source and semantic review only.

`issue-scope-pinned.json`, `baseline-receipt.json`, and `baseline-members.geojson.gz` retain the exact workload and baseline. The accepted lease renewal receipt is retained in `reservation-renewal.json`. `evidence-review-index.json` binds every changed packet file by SHA-256. Issue #471 predates the evidence-quality v1 activation, so this legacy packet uses a supplemental review index instead of claiming a required v1 manifest. All packet files remain under the issue's declared owned directory. No Atlas geography, release, history, production data, or other worker path was changed.

## Assessment

`assessment.json` contains an individual status for every exact member and all 18 province scopes. It records **58 justified**, **157 insufficient-evidence**, and **one correction-needed** subject. These are research judgments about the represented source and pinned parent context; they do not approve a region, certify current legal boundaries, or authorize imports.

The source crosswalk ties 215 administrative source IDs to pinned geoBoundaries feature IDs. The one derived Atlas city has no direct child shape ID; its nine declared source members are inspected separately. All 199 exact atlas/source name matches, source parent-name matches, source vintages, licenses, geometric comparisons, and row-level Ghana official-source matches are retained in `source-crosswalk.json` and `.csv`.

### Gambia

The retained 2020 geoBoundaries ADM2 layer has 48 districts under eight ADM1 Local Government Areas (LGAs), licensed CC BY 4.0. Atlas represents 39 source districts as separate subjects; the other nine exact source IDs are the members of `atlas:city:GMB-2153`. Together these form an exact 48-ID partition of the retained source layer with no repeats or omissions. Of the 39 standalone district rows, 29 have at least 0.95 IoU with their exact source geometry and are justified for source representation. Ten are insufficient pending a current official district boundary comparison; these have lower Atlas-to-source overlap, including two below 0.90. The Banjul atlas city geometry has 0.946 IoU with the union of those nine districts, supporting the footprint of the aggregation against its declared members.

The pinned Natural Earth 10m admin-1 record `GMB-2153` calls Banjul an “Independent City,” but its reference footprint has only 0.538 IoU with the Atlas city and 0.542 with the union of its nine declared district members. Natural Earth is undated and generalized, so this is a useful record identity and classification check, not statutory boundary evidence. The Atlas aggregation is not coextensive with the Banjul LGA: 75.4% of its area falls in Brikama, 20.5% in Kanifing, and 2.6% in Banjul. Existing Atlas metadata describes the city as a single coextensive Banjul province. This parent/role assertion needs a bounded source and hierarchy decision; the packet proposes no geometry edit. GBoS sources establish an eight-LGA census framework but no current official district-boundary dataset was located.

### Ghana

The 2019 geoBoundaries ADM2 source has 260 Districts, attributed to USAID Ghana HPNO and Ghana Statistical Service, CC BY 4.0. The 113 issue subjects match exact source IDs, names and named source parents. GSS StatsBank's official 2021 `Districts_261` geometry contains 261 records. The [GSS StatsBank user guide](https://statsbank.statsghana.gov.gh/Resources/userguide/statsbank_userguide_1.3.pdf) describes regions and districts, with some metro areas divided into sub-metros; the Census materials also distinguish District Assemblies from statistical-district units. For 29 rows, a unique normalized name+region candidate has source-to-candidate IoU at least 0.95, Atlas-to-2019-source IoU at least 0.95, and the source child is at least 95% covered by its named 2021 geoBoundaries region parent. These rows are justified as source-represented districts across the inspected vintages.

The remaining 84 Ghana rows stay insufficient-evidence. A 260-to-261 change, spatially nearest-unit scores, and substantial overlays do not distinguish redistricting from legal changes or source differences. The 2021 GSS boundary archive is restoration-only because no redistribution terms were found. Exact source IDs, named candidates, nearest spatial candidates, overlap shares, and restoration hashes are in `source-crosswalk.json` and `reference-source-checksums.json`. Do not interpret an overlay union as completeness or accuracy.

### Côte d’Ivoire

All 63 scoped source IDs exactly match the 2021 geoBoundaries ADM3 layer, the source children fall in their named 2016 ADM2 parents, and the 2016 parent layer's 33 features are labeled “regions.” The child layer metadata says 510 “Departments,” CNTIG/OCHA ROWCA, CC BY 3.0 IGO. Sixteen original source name attributes have a reversible mojibake form; raw bytes and IDs are preserved, and Atlas labels are not used to replace the source attributes.

The formal role is unresolved. DGAT currently reports 31 regions, 108 departments and 509 sub-prefectures (plus two autonomous districts). ANStat's 2021 API documentation reports 111 departments and 526 sub-prefectures, with official codes and reference year 2021. The 2016 parent count of 33 may reflect 31 regions plus two autonomous districts, but that inference is not a crosswalk. The 510-feature child count resembles neither official 2021 count exactly; it is not proof that ADM3 is a sub-prefecture tier. No exact ANStat row-level crosswalk was available, so all 63 remain insufficient pending decree/code and feature reconciliation.

## Sources and licenses

Exact original and compressed payload hashes, byte lengths, HTTP retrieval windows, metadata/citation-file hashes, licenses, restoration URLs, and the immutable geoBoundaries commit are recorded in `sources/register.json` and `sources/retrieval-verified.json`. The first registry was retained as `sources/register-initial.json`; its hand-entered retrieval time was provisional. Use the later re-fetch window, which confirmed byte-for-byte equality to all six retained child and parent layers.

- [GBoS 2024 census preliminary report](https://www.gbosdata.org/downloads/157-2024-population-and-housing-census) and [official report file](https://www.gbosdata.org/downloads-file/544-2024-gphc-preliminary-report); [GBoS compendium of statistical concepts](https://www.gbosdata.org/downloads-file/228-the-gambia-compendium-of-statistical-concepts). Original PDFs have exact restoration hashes but are not copied into this packet because their redistribution terms were not verified.
- [GSS Census Atlas / StatsBank](https://statsbank.statsghana.gov.gh/censusatlas/) and [official 2021 Census catalog](https://microdata.statsghana.gov.gh/index.php/catalog/110). The official geofiles ZIP and nested `Districts_261.zip` are not retained; exact hashes and restoration instructions are in `reference-source-checksums.json` because no redistribution terms were found.
- [Côte d’Ivoire DGAT administrative-circumscriptions page](https://dgat.interieur.gouv.ci/creation-de-circonscriptions-administratives/); [ANStat API documentation](https://anstat.ci/public/api); and [ANStat reuse terms](https://www.anstat.ci/privacy). ANStat content states CC BY 4.0. The data API was not reachable from this environment, so its documented counts/codes support a source-role discrepancy but not an exact crosswalk.
- geoBoundaries source files are pinned to commit `9469f09592ced973a3448cf66b6100b741b64c0d`, with each layer's stated year, source, canonical role and license in the register.
- The Banjul city metadata cites the pinned [Natural Earth vector source](https://github.com/nvkelso/natural-earth-vector/tree/ca96624a56bd078437bca8184e78163e5039ad19). Its exact original shapefile components are retained losslessly compressed under `sources/natural-earth-10m-admin1/`, indexed with original and retained hashes and retrieval times; Natural Earth publishes [public-domain terms](https://www.naturalearthdata.com/about/terms-of-use/). The source record and its independently computed geometry comparisons are in `source-crosswalk.json`.

## Method and limits

`compare_source_crosswalk.py` reproduces the 216-row exact-ID/name/parent join and compares geometries in EPSG:6933 equal area. GSS's uniquely named+region candidate and nearest spatial candidate are calculated separately. Invalid GSS geometries use local diagnostic `make_valid` clones; original evidence bytes are unchanged. The script includes identical-polygon and disjoint-polygon controls. `analyze_packet.py` rebuilds the Gambia city union and LGA overlays and the per-member/province/area classifications from the retained baseline, source layers and crosswalk.

`source-crosswalk.json` is not a survey: exact coordinates/topology differ for every joined layer, overlapping polygon area only screens source/vintage relationships, and no statistic proves legal boundary currency or complete land/island/coastline coverage. Côté d’Ivoire's source-field encoding issue does not change the exact ID join. Ghana's unlicensed-for-redistribution comparator remains restoration-only. Gambia's city-member aggregation is not an official metropolitan boundary. Partial Ghana and Côte d’Ivoire area scopes remain partial.

## Bounded handoffs

`findings-and-handoffs.json` records exact affected IDs, status, evidence, expected output and dependencies for follow-ups: [Banjul's city-parent semantics #830](https://github.com/ChengshuLi/WorldAtlas/issues/830); [ten Gambia district footprints #835](https://github.com/ChengshuLi/WorldAtlas/issues/835); [Ghana's 84 unresolved 2019/2021 district matches #831](https://github.com/ChengshuLi/WorldAtlas/issues/831), with the disjoint sibling scope #810 considered; and [the 63 Côte d’Ivoire units' official role/code crosswalk #832](https://github.com/ChengshuLi/WorldAtlas/issues/832). All four children remain blocked on their declared dependencies. None authorizes editing geography, importing records or marking regional approval.

## Reproduction

With Python 3.12, Shapely 2, pyproj, and `PYTHONPATH=/tmp/worldatlas-geography-pydeps`, restore the GSS comparator to `/tmp/gss-geofiles-2021.zip` from its URL and verify both ZIP hashes in `reference-source-checksums.json`. Then run from repository root:

```sh
PYTHONPATH=/tmp/worldatlas-geography-pydeps python3 data/regional-review/regional-review-c771eda166fa0226/compare_source_crosswalk.py
PYTHONPATH=/tmp/worldatlas-geography-pydeps python3 data/regional-review/regional-review-c771eda166fa0226/analyze_packet.py
python3 data/regional-review/regional-review-c771eda166fa0226/verify_packet.py
```

The comparison script reads the GSS archive only from the explicit temporary path and retains only the checksum receipt and derived row measurements. The verifier checks exact pinned subject coverage, every retained original/compressed hash, role-specific status totals, the full Gambia source-layer partition, GSS named-vs-nearest handling, status coverage and both positive and negative geometric controls. Source restoration scripts are unnecessary for the retained geoBoundaries layers.

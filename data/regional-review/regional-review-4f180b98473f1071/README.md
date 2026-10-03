# Western Indian Ocean batch 1 source and semantic review

**Issue:** [#482](https://github.com/ChengshuLi/WorldAtlas/issues/482)
**Scope:** 144 pinned v5 locations, 47 provinces and 8 areas, from issue `4f180b98473f1071`.
**As of:** 2026-10-03.
**Purpose:** evidence and proposed follow-ups for engineering. This packet does not change or approve shared hierarchy, boundaries, certificates or imports.

## Scope accounting

- `subject-inventory.jsonl` has one sourced, classified assessment for every assigned location: 99 `justified`, 45 `insufficient-evidence`; no assigned location remains pending.
- `province-assessments.json` accounts for all 47 declared province IDs and their full in-scope child memberships. 18 are currently justified as groupings; 29 inherit unresolved semantic/source concerns or have explicit follow-up needs.
- `area-assessments.json` accounts for all 8 declared areas and every assigned location: 4 justified and 4 insufficient-evidence.
- `verify-scope.py` reproduces the frozen source-ID, name, membership and full-parent-chain checks. It reports the issue body’s secondary `member_location_ids_sha256` as unresolved: the frozen region-member fingerprint matches, while that secondary digest does not match the listed ID collection under the tested canonical forms. No digest is silently substituted.

These status labels are evidence disposition for this assigned packet, not a regional approval. `insufficient-evidence` means a named source-backed question remains open, not that the current data is known wrong.

## Sourced results

### Settlement and locality coverage

The per-location ledger records a settlement disposition for all 144 assigned locations. Administrative tiers and population totals are not treated as settlement coordinates. Madagascar’s 2018 OCHA source has 17,465 ADM4 fokontany rows, but they are administrative records without a complete point gazetteer. Seychelles has an NBS-provenance 2019/2010 region/district source and no retained geocoded settlement layer; official 2022 NBS URLs returned 404 when checked on 2026-10-03. Statistics Mauritius Census 2022 names municipal wards/Village Council Areas and Rodrigues localities, but these do not form an exhaustive geocoded settlement layer for the assigned units. Comoros HOTOSM/OSM is an incomplete candidate screen only. Natural Earth identities for the remaining single island/department/territory features do not prove settlement coverage. The three bounded follow-ups own the needed source searches; no location is passed off as settlement-complete.

### Madagascar

The exact pinned source set contains all 119 features of geoBoundaries MDG ADM2 (2020), each matching an OCHA 2018 population-statistics ADM2 code by name. Retained OCHA ADM3/ADM4 crosswalks account for all 1,579 commune and 17,465 fokontany rows under those 119 districts; every assigned district has descendants at both levels. These are administrative/population rows, not 17,465 settlement coordinates.

A second, newer package changes the disposition materially. OCHA COD-AB Madagascar (reviewed 2026-07-06; `valid_on` 2018-08-10) reports 120 ADM2 districts and 24 ADM1 regions. All 119 assigned location names crosswalk to that package, but it adds ADM2 `Antanimora Atsimo` (p-code `MG52519`) under Androy. Its retained source polygon has 3,974.299 km²; the equal-area overlay places 99.534% of it within current `gb:MDG:ADM2:10022922B3330352702203` Ambovombe-Androy, with small sliver intersections against Bekily, Amboasary-Atsimo, Beloha and Tsihombe. It is therefore a strong administrative split/source-history lead, not evidence of additional land outside the current Madagascar envelope.

The complete new 120 ADM2 source polygons have no pairwise interior overlaps above 0.001 km². Their union overlaps 99.928% of the current 119-member union, with 0.149% symmetric difference and a +0.005% relative area change, so the 120th unit is not an additional island-envelope finding. The source union has 84 connected components while the current assigned union has 14. A component screen found 55 source components over 0.01 km², totaling 64.588 km², with under 1% overlap against the current union across 10 assigned districts; none intersects GSHHG level-1 land. They may be offshore islets, boundary/vintage differences, or source artifacts. All exact names, component indexes, area, centroids, nearest points, intersections and uncertainty are listed in madagascar-disconnected-component-review.json. This requires island-scale review; neither the source nor GSHHG non-detection alone establishes land presence or absence. The 2026-reviewed COD-AB lists 24 ADM1 while the current scoped parent partition has 22. It contains `Vatovavy` and `Fitovinany` where the current parent is `Vatovavy-Fitovinany`, uses `Haute Matsiatra` where the current name is `Matsiatra Ambony`, and also includes `Ambatosoa`, with no obvious name match among the current parent groups. Resolve all 24 source ADM1 shapes against every assigned child and predecessor before proposing parent changes. Of 119 exact-name ADM2 overlays against current locations, 15 have symmetric difference above the 5% triage threshold (maximum 61.268%; see full per-ID table), while the older pinned geoBoundaries source comparison finds 28 above that threshold. Thresholds are review triage only.

**Recommended bounded follow-up:** create a Madagascar source-history/crosswalk work item for the exact 120 COD-AB ADM2 and 24 ADM1 units, including new `MG52519`, affected current district ID above and its four neighbor intersections, all existing 119 location IDs, and every current Madagascar parent group. Restore prior OCHA/BNGRC, source-side code/change documentation and exact current legal boundaries; classify split/renamed/changed entities and their parent footprints. Engineering should coordinate any resulting identity or boundary integration; this packet makes no change.

### Mauritius and outer islands

The 2017 geoBoundaries Mauritius ADM1 source is explicitly titled “Districts and Outer Islands of Mauritius”; the 12 source features are not 12 homogeneous districts. Statistics Mauritius 2022 Census Volume III Table G1 supports nine Mauritius Island districts, municipal/Village Council Areas, Rodrigues separately, and the six Rodrigues local regions. Appendix IV lists localities for each Rodrigues region. It records Agalega with 330 residents; census reporting identifies St Brandon as having no permanent residents/count-only. Population does not prove island geometry.

The two Agaléga-named locations have disjoint current geometry and distinct source roles: a Public Domain Natural Earth named dependency shape and an ODbL OpenStreetMap/Wambacher ADM1 shape. Treating them as duplicate was premature and is withdrawn in the issue checkpoint. GSHHG 2.3.7 level-1 land polygons intersect 142 of 144 assigned locations, but not the St Brandon or Natural Earth Agaléga footprints. Neither nonintersection proves the land is absent; reefs, rocks, low islands and source resolution require official island/reef crosswalks.

**Recommended bounded follow-up:** obtain current official Mauritius island/reef geometry and source crosswalks for St Brandon and both Agaléga shapes, identify which islands/rocks belong to each source record, and compare only after preserving the original records and shoreline scale metadata. Include neighboring island groups if an outer-region limit changes.

### Seychelles

All 8 pinned geoBoundaries ADM2 `Regions` names match the Seychelles NBS-provenance OCHA COD-PS regional list, which assigns 27 ADM3 districts. The reference is 2019/2010-derived and is not assumed current in 2026. Four current province parent labels differ from that source list: Central 1 Mahe→Bel Air, La Digue→La Digue a, Praslin→Baie Saint and Other Islands→Outer Isla. `Other Islands` is a grouped offshore region with 1,057 source components versus 7 current components. GSHHG is too coarse to certify missing small islands.

**Recommended bounded follow-up:** request a current Seychelles NBS region-to-island/district crosswalk and official all-island physical inventory. Resolve the four parent labels and each `Other Islands` component before proposing grouping or footprint changes.

### Comoros, Mayotte, Réunion and Iles Éparses

The Comoros composite reconstructs to three named OSM/Wambacher ADM1 island shapes, corroborated by OCHA COD-PS 2017’s three island statistical units and OCHA COD-AB’s 2019 count of 3 ADM1, 17 ADM2 and 55 ADM3 units. A retained HOTOSM/OSM populated-place extract has 565 features tagged to the three islands (295 have no name); it is volunteer mapping and is not a complete or official settlement gazetteer. Comoros here is the three input island shapes, with Mayotte separately represented; no sovereignty claim establishes land membership.

The Natural Earth 10m source features for Mayotte, Réunion and Indian Ocean Iles Éparses reproduce the corresponding assigned geometry to within the reported overlay differences. For small islands, reefs and offshore land completeness, Natural Earth 10m and GSHHG level 1 remain screening sources only. Iles Éparses is the Indian Ocean source feature; Antarctica remains excluded.

**Recommended bounded follow-up:** for Comoros, seek an official settlement/locality source with dated geography and a lawful coordinate dataset; use HOTOSM only to identify candidate omissions. For Iles Éparses, Mayotte and Réunion, source appropriate official island inventories and compare with retained coastlines before a completeness exception.

## Methods and files

- `sources.json` is the canonical source registry: references, producer, dates/vintages, licenses, exact retained source file hashes/sizes or URL-based restoration instructions, extraction and screening method, and uncertainty.
- Original pinned geoBoundaries geometry, metadata and citation files remain beside the retained OCHA, Natural Earth and HOTOSM source material in `sources/`. The Statistics Mauritius files have no explicit open redistribution license identified; their bytes are not in the packet. `sources.json` records official restoration URLs and local hashes for the inspected 2022 census table. GSHHG’s license text is retained.
- `geometry-comparison.json` compares every applicable pinned source/current location in equal-area EPSG:6933, all 22 Madagascar child unions against their retained 2017 region source, Comoros’ three-source union, and all four Natural Earth records. Geometry validity repairs are ephemeral only.
- `madagascar-current-COD-AB-review.json` and `compare-current-codab.py` reproduce the updated 120-district/24-region comparison and the Antanimora Atsimo overlay.
- `screen-gshhg-overlaps.py`, `gshhg-overlap-screen.json` and the retained compressed match records reproduce the all-location GSHHG screen; the centroid-only candidate screen is retained separately and is not used to claim completeness.
- `madagascar-2018-district-admin-crosswalk.json` and `seychelles-2019-region-district-crosswalk.json` contain the exact administrative row counts/name crosswalks.
- `settlement-administration-review.json` records physical screen, role, hierarchy, administrative and source limitations across the exact 144-ID scope.

## Bounded follow-up issues\n\nThree blocked follow-up work items were created from the source-backed recommendations: Madagascar source-history reconciliation [#632](https://github.com/ChengshuLi/WorldAtlas/issues/632), Western Indian Ocean offshore island inventories [#633](https://github.com/ChengshuLi/WorldAtlas/issues/633), and an authoritative Comoros gazetteer [#634](https://github.com/ChengshuLi/WorldAtlas/issues/634). Each depends on #482; none is marked ready or claimable.\n\n## Unresolved metadata and release boundary

The issue’s region ID set and frozen region-member fingerprint are stable and match the published v5 pin, but its second `member_location_ids_sha256` field does not reproduce from the listed 144 IDs in tested newline/sorted JSON forms. Retain both values and ask the scope publisher to state the canonical serialization and correct the metadata if needed.

This packet is only a source/semantic review. No geographic structure, source input, shared footprint, certificate or live data was changed. Engineering must integrate accepted evidence, review any linked cross-boundary consequences, and validate/publish the complete region before location-attribute imports become eligible.

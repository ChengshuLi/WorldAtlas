# Western North America batch 3: Pacific — evidence packet

Issue [#487](https://github.com/ChengshuLi/WorldAtlas/issues/487) assigns 100 of the 191 Pacific area locations: the complete Washington location cohort (39) and complete California cohort (61). The exact frozen IDs and regional release pins are in `scope.json`, `issue-metadata.json`, and `sources.json`. All 100 IDs have one row in `assessment.json`; none is omitted. The row-level record gives name, source identity, location granularity and role, complete parent chain through continent, settlement screen, political/history separation, physical-land screen, remainder/island notes, decision, rationale, sources and uncertainty. Summary decision counts are 96 `justified` and four `correction_needed`; “justified” here means the named source identity, county-equivalent tier and state parent are supported, not that a whole region, every shoreline, or every island is certified.

This review follows bottom-up geography: the assigned location memberships are the subjects and determine parent footprints. Top-down is only the order used to inspect state parent cohorts before their member locations. EU5 counts were not used as quotas. No hierarchy, geometry, grid, certificate, application code, schema or live data was changed. Antarctica is out of scope. This packet supplies evidence and proposed corrections for engineering integration; it does not approve the complete Pacific area, the larger region, or historical imports.

## Administrative cohorts and parent coverage

The pinned geoBoundaries USA ADM1 (2018) layer has 56 source features; the ADM2 layer has 3,233. State names California and Washington match the current `framework:province` parents. Their parent chains and complete state cohorts are recorded in every row and the `complete_state_parent_cohorts` section of `assessment.json`. California has 58 ADM2 county-equivalents and 58 2024 Census counterparts; its 61 assigned locations include four San Bernardino physical fragments. Washington has 39 source counties, 39 current direct rows and 39 2024 Census counterparts. In total, all 97 source counties in the two complete state cohorts are accounted for by 96 direct current county rows plus four physical pieces of the one San Bernardino predecessor; the source roster audit finds zero unaccounted counties.

The assessment reports the 2018 county-union and current parent-cohort overlays against each state's 2018 ADM1 source area. The table gives the exact recorded intersection percentage, the 2018 ADM1 denominator, union area and symmetric difference in km². It corrects the earlier rounded Washington narrative, which did not match the generated assessment:

<!-- parent-overlay-metrics:begin -->
| State | Compared union | Intersection / 2018 ADM1 | 2018 ADM1 denominator (km²) | Union area (km²) | Symmetric difference (km²) |
| --- | --- | ---: | ---: | ---: | ---: |
| California | 2018 ADM2 county union | 99.970514% | 409880.556195 | 409873.616938 | 234.771407 |
| California | current parent cohort union | 99.953610% | 409880.556195 | 409877.348260 | 377.076883 |
| Washington | 2018 ADM2 county union | 99.929218% | 175441.740964 | 175740.434010 | 547.055096 |
| Washington | current parent cohort union | 99.873452% | 175441.740964 | 175702.062926 | 704.357394 |
<!-- parent-overlay-metrics:end -->

The percentages are intersection areas divided by the corresponding 2018 ADM1 source area, as checked from the recorded union areas and symmetric differences. These are overlay diagnostics, not proof of water jurisdiction, detached-island completeness, federal or tribal parcel status, nor a basis for changing shared footprints. Parent roll-ups follow their member locations.

The row-by-row name/shape crosswalk uses the 2018 source shape IDs and exact source names. Census TIGER/Line 2024 provides an independent current-name/GEOID crosswalk (2024 County layer DBF update 2024-09-16). Every assigned source county has one 2024 state/name/GEOID counterpart. Full Census ALAND/AWATER values are retained in the assessment; the current released geometry often follows older land-focused extents and not the 2024 full county-water extents. Water-area inclusion must not be read as a sovereignty conclusion.

## San Bernardino physical pieces

Four locations explicitly name portions of the San Bernardino County predecessor. Their RESOLVE ecoregion IDs and names, exact source intersections, current overlay percentages and symmetric differences are in `derived-portion-audit.json`. The current four-piece union intersects the 2018 county predecessor at 99.9803% (24.52 km² symmetric difference); individual feature intersections range from 99.23% to 99.92%. Temporary equal-area overlay and any repair needed after projection did not modify either original source or baseline geometry.

The four features are ecological units (RESOLVE ECO_ID 422, 424, 433 and 435), not administrative county units. Their current `source_role=Counties` and county-selection rationale therefore need a source-role correction. This is the only direct correction proposed here: preserve the existing geometry pending engineering’s broader validation, and correct the four metadata/role descriptions to identify ecological portions of the San Bernardino predecessor. The exact four-ID follow-up is tracked in [#597](https://github.com/ChengshuLi/WorldAtlas/issues/597), created from this evidence. It is not a request to alter county ownership or boundaries.

## Settlements and land screening

The official 2024 Census Places archives cover 1,618 California and 639 Washington incorporated-place/CDP polygons (2,257 total). Each assigned location intersects at least one polygon, and its row lists the intersecting place names/counts and classes. Census Places are not a complete gazetteer: unincorporated settlements and named localities may be absent. This screen does not assert settlement coverage beyond its documented categories.

The independent GSHHG 2.3.7 full-resolution land screen found the row representative point on land for 99/100 locations. San Juan County is the single representative-point no-hit; its numerous separate land polygon-centroid hits (35) show why a single point is not a sufficient island test. Fifteen locations have one or more land polygon centroid hits, listed in `gshhg-pacific-screen.json`. These are candidates for visual/authoritative island and coastal review, not a completeness certificate. The full-resolution archive/member hashes, LGPLv3-or-later license text, and retained complete matched records are in `sources.json` and `sources/`.

## Neighboring consistency and coordinated leads

`neighbor-screen.json` compares temporary projected adjacency graphs for 2018 geoBoundaries, 2024 Census TIGER county data, and the current Atlas. Within the assigned two-state 2018 county graph, 219 shared-line pairs are present; the coarse current predecessor graph has 218. The sole 2018/current pair difference is Alameda–San Francisco: 357.251 m shared in the 2018 source, zero in current geometry, with current nearest separation 4,442.292 m. The 2024 graph has 234 edges and exposes 17 candidate edges absent from the current graph (no extra current edge); 16 are within California/Washington and one is Oregon Clatsop–Washington Pacific. For the latter, the 2024 Census shared line is 41,324.968 m while the current pair has zero shared line and 5,372.349 m separation. All pair metrics are listed in the JSON.

These vintage differences are leads, not confirmed boundary errors: Census county polygons include extensive county-water geometry, and the current geometry often has no equivalent water boundary. The packet does not infer ownership or propose a unilateral line edit. A focused source review of all 17 pairs is tracked in [#598](https://github.com/ChengshuLi/WorldAtlas/issues/598) and requests coordination with the neighboring interior packets, including #486. Issue #486 was notified of the Clatsop–Pacific lead. Alameda–San Francisco and all other pair-level differences still need authoritative, fit-for-purpose source review before engineering decides whether any representation change is justified.

A separate current contact screen found Whatcom County, Washington, touching Abbotsford, British Columbia, along 39,105.384 m. Inputs are current Whatcom ADM2 (geoBoundaries, 2018, public domain) and Abbotsford ADM3 (geoBoundaries Canada, 2016, ODbL 1.0). The Abbotsford source metadata reports one topology conflict and warns that original source boundaries may differ. Both retained inputs are valid and their current geometries share a line, but no official bilateral International Boundary Commission evidence was retrieved or compared. No border inconsistency is established and no political claim follows. Regional integration should coordinate #485 and #487 owners and compare the applicable official bilateral source before drawing any conclusion; #484 was notified.

## Sources, retention and reproduction

`sources.json` is the canonical source registry for this packet: source dates/vintages, publishers, licenses, URLs, metadata hashes, retained byte counts and SHA-256 values, restoration instructions, selection rules and limits. It includes pinned full USA 2018 administrative data; the official 2024 TIGER county archive hash and a reproducible six-state neighbor subset; both complete state Places archives; four RESOLVE ecoregion features and metadata; GSHHG archive/member hashes and retained matched records; and the exact Abbotsford feature plus its full Canada layer hash. Raw source materials are preserved or have explicit restoration instructions. The GSHHG global binary and complete Canada layer were not duplicated; only exact matched records/features were retained with checksums and canonical restoration steps.

From the repository root, with the named canonical GSHHG archive member restored and verified per `sources.json`, reproduce derived evidence using:

```sh
python3 data/regional-review/regional-review-2178b81fa886cfb6/screen_gshhg.py /path/to/gshhs_f.b
/usr/bin/python3 data/regional-review/regional-review-2178b81fa886cfb6/build_assessment.py
/usr/bin/python3 data/regional-review/regional-review-2178b81fa886cfb6/audit_neighbors.py
/usr/bin/python3 data/regional-review/regional-review-2178b81fa886cfb6/audit_canada_neighbors.py
python3 data/regional-review/regional-review-2178b81fa886cfb6/verify_parent_overlay.py
python3 data/regional-review/regional-review-2178b81fa886cfb6/verify.py
```

The scripts use temporary projected geometry for distance, area and adjacency measurements; original source and Atlas material remains intact. The focused parent-overlay check binds all four state/cohort rows to the generated assessment, confirms the recorded release/current baseline and rejects a changed metric. `verify.py` runs those checks alongside scope completeness, row-level accounting, source hashes and core findings. `parent-overlay-correction.json` records the original narrative/assessment byte hashes, the two-run current-baseline reproduction, corrected values and source pins. Read `limitations` in the assessment and individual neighbor records before using any derived metric as proposed correction evidence.

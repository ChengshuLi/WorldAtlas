# San Bernardino ecoregion source-role correction

Issue #597 assigns exactly four existing location IDs. Their source IDs point to named RESOLVE 2017 ecoregions, but the current `source_role` says `Counties` and the selection text treats each one as an administrative county. The retained RESOLVE item describes ecoregions as natural rather than political boundaries, and its four source features identify ECO_IDs 422, 424, 433 and 435. The San Bernardino county is a separate clipping/predecessor context, not the role of each resulting physical fragment.

## Proposed correction

Use `source_role: "Ecological ecoregion portion"` for each assigned feature. Keep its existing `administrative_level: "Named physical region portion"`, location ID, parent, source ID, predecessor source-member ID and footprint. The recommended selection rationale for each row is generated in `proposed-role-corrections.json`: it names the exact RESOLVE ECO_ID and explains that the 2018 San Bernardino ADM2 county defines only the intersection context. This is evidence for engineering review; it changes no shared metadata or geometry.

| Stable location ID | RESOLVE ECO_ID and ecoregion | Inherited current components | 2024 Census Places intersections |
| --- | --- | ---: | ---: |
| `atlas:physical:5dcc72971bb4b1ede2f5` | 433 · Mojave desert | 8 | 28 |
| `atlas:physical:9cfc4fc5de3925d6f841` | 435 · Sonoran desert | 2 | 2 |
| `atlas:physical:d76eb273e99a0f96a575` | 424 · California montane chaparral and woodlands | 5 | 19 |
| `atlas:physical:dcc393fbc988381d899c` | 422 · California coastal sage and chaparral | 1 | 31 |

All four complete parent chains remain location → California → Pacific → Western North America → Northern America → North America. The parent #487 assessment preserves each Census Places name/GEOID/class list, each physical-land representative-point screen, geometry component and ring counts, the political-history distinction, and its unresolved land, island, coastline, settlement and remainder limits. These inherited screens are not rerun here. Census Places is not a complete gazetteer, and GSHHG point/component screens do not prove land completeness.

The 2018 geoBoundaries ADM2 source and 2024 TIGER/Line Census feature identify San Bernardino / GEOID 06071 as the county context. The inherited equal-area screen says the four current pieces overlap 99.980296% of the 2018 county shape and have 24.520472 km² symmetric difference. It is a source-vintage diagnostic, not a legal county remainder or a reason to move a shared line. No neighboring boundary, hierarchy, political ownership or historical attribution is changed or inferred.

## Sources and limits

The original RESOLVE item/layer metadata, four-feature source extract, 2018 geoBoundaries source, and 2024 TIGER neighbor subset remain byte-pinned and unmodified in issue #487's parent packet at baseline commit `fbd3bf4991dbd5a9bf89a79b14e5b4deb6225ff9`. `sources-manifest.json` records canonical URLs, source dates, CC BY 4.0 attribution / public-domain terms, hashes, file vintages and restoration instructions. This packet references those retained bytes without duplicating or replacing them.

The source proposition is supported: the four source identities are ecological ecoregion portions, not counties. The inherited geometry, settlement, island/remainder and neighboring screens remain limited to the conclusions and caveats recorded in #487; no new geometry measurement or geographic approval is claimed. Antarctica remains excluded. No historical imports are enabled.

## Reproduction

Run from the repository root:

```sh
python data/regional-review/regional-supplement-san-bernardino-ecoregion-roles-2026/build_role_proposal.py
python data/regional-review/regional-supplement-san-bernardino-ecoregion-roles-2026/verify_role_proposal.py
node scripts/evidence-quality.mjs data/regional-review/regional-supplement-san-bernardino-ecoregion-roles-2026/evidence-quality.json
node scripts/check-handoff-scope.mjs --branch geography/san-bernardino-ecoregion-roles-597-20261004 --base origin/main --pr-body-file /tmp/pr597-body.txt --issue-file /tmp/issue597.json
```

The builder reads immutable files with `git show` at the pinned ancestor and writes only `proposed-role-corrections.json`. The verifier checks all four IDs, source identities and parents, confirms the stored geometry fingerprints, rejects a wrong ECO_ID, a county-role proposal and an incomplete roster, and runs the builder twice for byte-identical output. Inherited source/geometry screens remain frozen findings, not new measurements.

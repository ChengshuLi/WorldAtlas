# Kimvula four-key source-target diagnostic

**Status: bounded evidence and qualification attempt; all four keys remain held and unaccepted.** This is a subset of the original `gb-COD-ADM2--repair-evaluation` issue #2453, not a new scope or a package completion. It makes no repair, owner change, hold removal, or science-credit claim.

## Exact original slice and prior-work relation

The original denominator remains 3,905 cells, 2,323 intervals, and 50 owners. The four keys below are the complete Kimvula residual slice identified for owner 14593 in original partition B. Each is land, carries the original source-index pair `[449,18848]`, and remains unaccepted in the retained original partition. They are distinct from Irumu owner 14568's 112-key slice and the other 814 of the 930 residual keys after Irumu and Kimvula are separated.

| Owner | y | x | Original class | Original source IDs |
|---:|---:|---:|---|---|
| 14593 | 135367 | 142749 | land | AGO ADM1 index 449; COD ADM2 index 18848 |
| 14593 | 135368 | 142713 | land | AGO ADM1 index 449; COD ADM2 index 18848 |
| 14593 | 135369 | 142678 | land | AGO ADM1 index 449; COD ADM2 index 18848 |
| 14593 | 135370 | 142642 | land | AGO ADM1 index 449; COD ADM2 index 18848 |

The positive target is `gb:COD:ADM2:63176286B83971453832478` (Kimvula, ordinal 95) in the registered 2019 COD ADM2 product (recorded CC BY 3.0 IGO). The competing center candidate is `gb:AGO:ADM1:26408823B906914650007` (Uíge, ordinal 16) in the registered 2021 Angola ADM1 product (recorded Public Domain, attributed in metadata to the U.S. Census Bureau). The retained complete-family center overlay reports all four centers inside both Kimvula and Uíge. This is source conflict evidence, not a decision about which territorial interpretation applies.

## Complete source-evidence row

The row was assembled from the already retained original 50-target source-stage input at commit `7839ae9de7d57c732050df05e7f6d5c9b42afd88`, not from a new source download or geometry reconstruction. The stock source-evidence helper matched the selected Kimvula geometry to the exact original COD ADM2 feature and the original stage record. It retained the whole-target physical receipt and input pins and considered the complete registered set of 20 negative territorial source families.

The 2018 AGO ADM2 family is separately recorded as CC BY 3.0 IGO. Complete original-source processing found three conservative bounds-intersecting competitors for the Kimvula target: Uíge ADM1, Maquela do Zombo ADM2, and Quimbele ADM2. Only Uíge appears as a center hit in the retained complete-family overlay for these four keys; the two ADM2 entries are retained as target-level bounding candidates, not asserted per-key contacts. The remaining 1,376 disjoint source-feature IDs are listed in the provenance output, not silently treated as zero or omitted from the universe.

The exact source configuration, 4-key native patch, generated `source-evidence.json`, territorial-exclusion provenance, and their preparation receipts are included below. The raw family geometries are not copied into this packet; exact repository source locators and byte/hash pins are retained.

## Qualification result and limits

The stock source-evidence preparation has authenticated the positive Kimvula feature and the complete registered set of 20 negative families, retaining the three target-level bounding candidates and exact source pins. The stock native diagnostic ran against the exact committed source-evidence and four-cell patch. It requested 4 cells, supported 0, and held all 4. Every per-key decision is `territorial_exclusion_cells`; the summary `first_failure` is `unique-source-target-coverage`, which is not the per-key disposition. The diagnostic does not run the physical producer, full source scan, owner observation, or whole-cell comparison; those original results remain pinned and are reused without relabeling. The existing independent source review found no retained primary evidence deciding whether the Uíge source applies as a territorial exclusion under the source-specific contract. The center overlap and complete competitor coverage are therefore evidence of conflict, not a sourced resolution. Keep all four held; this result does not establish a territorial assignment or researched-unresolved acceptance.

No geometry is republished from an unapproved source. All four keys remain held until the original source-specific applicability evidence supports a disposition. No completion credit is requested here. The run used Node v24.19.0 and the installed Git 2.53.0 with `GIT_NO_LAZY_FETCH=1` and `GIT_NO_REPLACE_OBJECTS=1`. An initial launch resolved Apple Git 2.39.5 from the default shell PATH; it failed before producing a diagnostic because that version rejects the helper’s `--no-lazy-fetch` option and fell back to a missing current-tree source-stage path. The same unexecuted diagnostic was then run with the installed Git 2.53.0 first on PATH; only that successful output is used above.

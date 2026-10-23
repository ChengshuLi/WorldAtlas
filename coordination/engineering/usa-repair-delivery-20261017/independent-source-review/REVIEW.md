# USA original repair source-scope review

Read-only review at `d4968ddc37aa3aa6105e9610c9e6fadbb368ba14`, 2026-10-17 UTC, for issue #2358. Reviewer: `review_usa_source_scope`. The shared repository and author packet were not edited. No national archive was copied or downloaded, no global raster/physical production was run, and no delivery queue was dispatched.

## Consequential result

Preserve **all 107,131 original keys /46,575 original intervals /351 subjects**, including 95,729 land and11,402 inland-water keys. The presently evidenced union of specific holds is **600 distinct keys:575 land +25 inland water**. It comprises63 foreign-original contacts,536 keys within previously deferred USA31 components, and Fairfax’s1 identity key. The three sets are pairwise disjoint by exact `(y,x,owner)` comparison, not an assumed addition.

The resulting **106,531-key potential complement** has95,154 land /11,377 inland-water keys and46,324 split-original intervals. It contains347 positive owners. Four original owners are wholly held: Fairfax1; Boundary2 (`gb:USA:ADM2:52423323B63721358154647`); Essex2 (`gb:USA:ADM2:52423323B77822845094766`); Clinton3 (`gb:USA:ADM2:52423323B88569310946047`). They remain in the original351-subject disposition roster. This is a scope reconciliation, not approval of the complement or accepted repair credit.

Primary machine handoff: `hold-key-union.json` contains every exact held key, original six-column interval splits, reasons,31 preserved component dispositions, and source pins. The parent may preserve these review outputs under its own issue-owned evidence namespace.

## Source identity, role, vintage and reuse

The complete consumed source is `gb:USA:ADM2`,3,233 unique features,7,938,450 bytes, SHA-256 `16249e8d795aaded6a72910a8c72115a073814b25ee902d61ccc9a9490c6641a`. Authentication used complete original corpus products and the retained catalogue, including every encoded/decoded part hash and complete ordered source-ID roster. This is the upstream `_simplified.geojson`, not the10,500,644-byte full-resolution product with SHA-256 `81fdd384df8012e5007ed2994a8ab306352f3c48e32cd8ea99182195e8647f43`.

`data/administrative-sources.json` and the retained939-byte upstream metadata identify Counties/ADM2; U.S. Census Bureau MAF/TIGER; represented2018; source update2023-01-19; build2023-12-12; Public Domain. Update/build dates do not change the represented vintage. `scripts/administrative.py` consumes the simplified URL; feature metadata separately cites the unsimplified URL. Existing #981/#989 evidence resolves the hash distinction and does not authorize a catalog hash replacement. The national source's `shapeGroup=USA` does not encode each county’s state/GEOID; source IDs and current parent IDs are distinct from a current legal-boundary crosswalk.

The original metadata’s two Census URLs use malformed `https//` schemes; registry metadata uses scheme-less strings. Preserve the discrepancy and reuse the retained actionable Census restoration references rather than silently repairing historical metadata. Census cartographic boundaries are generalized mapping representations. Source identity/completeness is not current legal-boundary or precise-area certification.

Retained #1143 source-use evidence (`data/regional-review/south-atlantic-source-reuse-basis-429/`) distinguishes per-file Public Domain Census metadata, geoBoundaries project-generated derivative CC BY4.0 language, and its product/source attribution request. Preserve all statements and the narrow unresolved application of derivative rights to this particular file. Retain Census plus geoBoundaries credit, exact release and modifications; do not relabel the per-file source CC BY or infer unrestricted provider-product rights solely from its Public Domain field. Original LICENSE and CITATION-AND-USE text were read directly.

## Current identity and aggregate intent

`identity-obligations-review.json` authenticates the currently selected source-bank descriptors and all351 actual target records. All349 direct source IDs resolve uniquely to complete original features; original ID, name, source family, represented year, Public Domain metadata and captured current properties match. All checks reported zero mismatches. This is source/identity consistency, not county-boundary adjudication.

There are356 complete original members across all351 forensic targets. Removing Fairfax’s two members leaves354 members across350 target identities before exact-key foreign and prior-defer exclusions.

- **NYC:** current metadata, `data/semantic-report.json`, and the actual `scripts/semantic-locations.py` construction agree on the full union of Bronx, Kings, New York, Queens and Richmond counties. The constructor explicitly selects exactly these five under the New York parent; no narrower physical-only membership or carveout was found. Its197 original keys are not held by any evidence identified here.
- **Fairfax:** the semantic record describes disconnected components of the same named source district. `scripts/consolidate-fragments.py` actually aggregates via normalized name/source/parent plus small-area/distance heuristics. Open #976 directly contradicts the premise: Fairfax city GEOID51600 and Fairfax County GEOID51059 are distinct county equivalents. Preserve its sole key `(100551,74860,5777)` as held. The existing shared source lineage does not resolve the identity defect.

## Complete foreign negative-source scope

`complete-source-scope-screen.json` independently authenticates **all368 retained products /73,567 complete original features**, with no current-owner filtering. Each complete geometry was tested against only the107,131 original key centres using Shapely2.1.2 and the pinned binary64 latitude table. Every feature’s exact-ID contact set matched the retained original native source contacts; there were zero differences. All touching geometries were valid in this runtime. This bounded independent predicate screen is diagnostic, not a substitute for exact-native authority construction.

The only foreign families with contact are complete CAN ADM1 (37 keys), CAN ADM2 (28), and MEX ADM1 (13), a63-key union. **All13 touching foreign features are ownerless.** Excluding ownerless originals would discard every foreign contact. Complete CAN ADM3, MEX ADM2, RUS ADM1/2, and all other unlisted retained families were explicitly tested and have zero contact on these keys; they were not excluded merely because the queue omitted their names. The complete country-family operands should remain the negative inputs for applicable construction, with the all-family screen retained as the basis for zero-contact exclusions. Do not clip original negative polygons.

Domestic contacts are USA ADM2 on all107,131 keys and USA ADM1 on89,193. Parent-state/coarser coverage is context, not an automatic incompatible-owner veto.

The whole original-corpus point screen read620,368,518 decoded bytes sequentially, retained no source copies, completed in48.644 seconds, and measured625,913,856 peak Linux RSS bytes within a2 GiB address-space bound and180-second deadline. These are measured/declared operating facts, not a qualified execution receipt. It did not create a full native raster.

## Specific USA31 deferred-key evidence

The complete retained #1377/#1384 packet says all31 original components are `source-history-unresolved; retain original candidate and defer processing/repair`. Its complete original geometries intersect **536 exact original USA repair keys in21 components**, including514 Suffolk NY keys (492 land+22 water),20 Nassau NY land keys and2 Westchester NY land keys.

The initial independent point screen was then checked with the authenticated stock `witnessCellEffects` and `nativePolygonIntervals` from immutable `src/native-grid.js`: exact rational native longitudes, complete pinned binary64 latitude table, every complete component, and the full107,131-key original request. It reproduced exactly the same536-key set. `exact-USA31-component-keys.json` retains complete hits/geometry input pins and key-to-component joins. The exact witness took1.212 seconds and270,540,800 peak Linux RSS bytes. It establishes scope contact only, not source fitness or field physical truth.

Fresh GitHub reads on2026-10-17 found no applicable later resolution:

- #1377 is closed for the source-only assessment. Its six comments include [acceptance reconciliation](https://github.com/ChengshuLi/WorldAtlas/issues/1377#issuecomment-6037327763), expressly retaining all31 source-history-unresolved dispositions.
- Later open #1630 explicitly preserves the USA31 unresolved assessment. Its later four Aleutians West source-variant checks are expressly disjoint from USA31.
- Open #1534 is a preservation/reproduction/numerical-reporting successor, with no comments; it supplies no scientific resolution.
- Repository issue searches for1377 and USA31 returned these three issues. Complete fetched bodies/comments are retained alongside the review.

Therefore these536 keys carry specific existing defer obligations. They are not proved to belong elsewhere. Admission should remain held unless later applicable evidence resolves the actual source/physical question, rather than merely reproducing the same historical mask or observing source ancestry.

## Broad obligations retained without blanket county holds

Exact original-subject intersections include #954 (10 owners /1,582 keys), #967 (25 /1,351), #966 (14 /1,006), #968 (41 /6,222), #975 (53 /4,367) and #1079 (3 /1,405). These counts overlap. They are source/boundary-history obligations, not demonstrated numbers of erroneous keys. In particular Cook647, Lake619 and Koochiching139 Minnesota keys retain #1079’s generalization, county/state extent and fragment questions. An IoU difference alone does not establish a candidate-key contradiction or justify a whole-county hold.

The complete open-issue intersection list in `identity-obligations-review.json` also retains source/reproduction concerns #1141/#1145/#1149/#1257/#1311/#1407/#1534/#1582 and broader regional reviews. They are not closed or overwritten by this package. This review has not tested every county against modern legal surveys or resolved all upstream source-history questions.

## Remaining gates

No source/native authority quartet, accepted native repair, selected-bank owner-zero test, conservation result, emitted-consumer result, geographic approval, import or delivery is claimed here. The parent must preserve the complete original denominator, all held keys and every unresolved issue while qualifying any remaining positive scope and later serializing current-selected delivery.

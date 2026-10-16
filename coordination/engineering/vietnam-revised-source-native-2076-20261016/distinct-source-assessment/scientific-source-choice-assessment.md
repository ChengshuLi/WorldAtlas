# Distinct scientific source-choice assessment: original Vietnam 365

Assessor: `/root/assess_vietnam_revised_sources`. Date: 2026-10-16 UTC. Issue: https://github.com/ChengshuLi/WorldAtlas/issues/2076.
Accepted code and unchanged target-geography comparison: `cd68e89523901acf477d0365470410b8b970bb48`.

## Result and decision boundary

**348 proposed Chinese display-source choices are supported by the project's existing exclusive-country-reference shared-interior convention. The other 17 proposed Chinese choices are blocked because the same reference places them exclusively in Vietnam.** All 365 are actual shared interiors of their one new OSM county polygon and one retained Vietnamese ADM2 polygon, with no native boundary ties. All 258 retained country-reference features were tested; the result is not based on a preselected China/Vietnam pair or twelve sample points.

This is source-choice preparation for an actual parent acceptance, not accepted adoption. All source/native adoption flags and accepted repair credit remain false/zero. Complete current fine-geography competition, current owner-zero, source/physical/native qualification and conservation are outstanding. The exact supported and blocked original owner/y/x sets, proposed distinct OSM source IDs, stable target IDs/owners, reasons and every contrary original fine-source contact are in `source-choice348-supported17-blocked.json`. The complete assessment, twelve target records and input/observation pins are in `scientific-source-choice-assessment.json`.

The initial `scientific-source-assessment.md` and `independent-source-assessment-final.json` were provisional reads that treated unresolved contrary Vietnamese fine-source coverage as blocking all 365. That disposition is superseded here after examining the actual accepted display policy. Their raw identity, provenance and contrary-contact observations remain valid and retained. No fact was deleted to obtain the 348 subset.

## Actual accepted convention and its applicability

Current `docs/DATA_SOURCES.md`, line 25, defines partitioning of independently compiled **shared interiors** by supported Natural Earth country-reference borders, then finer source polygon and stable ID for leftovers. It explicitly describes a cartographic display convention, not a sovereignty ruling. The accepted `scripts/reconcile-topology.py` implements this by finding the actual shared polygon, calculating each country's reference intersection, assigning the exclusive portions, and using original polygon area/stable ID only on the remainder. Nonoverlapping coverage is preserved. This assessment does not run that geometry-mutating script or import its numerical cleanup tolerances into native predicates.

The recovered Myanmar source28 preparation/adoption used this same exclusive-reference branch for seven Myanmar and 21 Thailand choices, retaining the conflicting mappings. It did not establish generic source priority or native qualification. Its value here is a comparator for the convention's meaning; it is not authority for these new keys.

The distinct checks establish every condition needed for the bounded **country/display-choice branch** here:

1. Every original key lies uniquely in its literal proposed OSM county source under the accepted exact native rule.
2. Every key lies in the independently reread original Vietnamese ADM2 source product, with no boundary tie. All contacts equal those in the authenticated original global census. There is therefore an actual shared interior, not an invented country-mask extension into unsupported geography.
3. All 258 retained global country features yield exactly one country hit per key: 348 China, 17 Vietnam. No other-country, both-country, neither-country or boundary-tie key occurs.
4. The Chinese and Vietnamese country polygons are valid and need no `make_valid` changes. The only invalid retained country is Egypt, wholly outside the candidate longitude range; it cannot affect this result. No repair was applied to any operand.
5. Each proposed target is an existing stable Chinese county identity whose retained parent context, original roster record and same-ID representative point corroborate the crosswalk. No target is invented or selected by nearest distance.

Accordingly, the 348 recommendations choose the new OSM source for the Chinese display identity at those **exact original keys**, while retaining the old Vietnamese contacts as contrary source facts excluded for that bounded display choice. They do not declare Vietnamese geometry false, rewrite either source, supersede either source family, or adjudicate legal jurisdiction. The 17 Chinese proposals fail the very same convention and stay blocked. They do not automatically become approved Vietnamese native additions. No area/stable-ID fallback, date priority, name priority or metadata-2057 authority is used.

## Twelve sources and precise supported portions

| Distinct OSM relation/version | Existing county identity | Owner | Retained parent | Supported display choice | Blocked CHN proposal |
| --- | --- | ---: | --- | ---: | ---: |
| 2723220 / 26 | Funing | 11270 | Wenshan | 39 | 0 |
| 2773869 / 24 | Ningming | 11573 | Chongzuo | 23 | 0 |
| 2719410 / 32 | Jinping Miao, Yao and Dai Autonomous County | 11584 | Honghe | 31 | 2 |
| 2719407 / 32 | Hekou Yao Autonomous County | 11700 | Honghe | 10 | 0 |
| 2773865 / 25 | Daxin | 11762 | Chongzuo | 31 | 0 |
| 2722419 / 26 | Napo | 11764 | Baise | 6 | 0 |
| 2719413 / 18 | Lüchun | 11930 | Honghe | 4 | 1 |
| 2723223 / 30 | Malipo | 12076 | Wenshan | 8 | 5 |
| 2773976 / 22 | Jingxi City | 12115 | Baise | 6 | 0 |
| 2773868 / 21 | Longzhou | 12167 | Chongzuo | 148 | 7 |
| 2723222 / 27 | Maguan | 12908 | Wenshan | 1 | 2 |
| 6881348 / 14 | Pingxiang City | 13210 | Chongzuo | 41 | 0 |
| **Total** | | | | **348** | **17** |

The complete original scope remains 365 keys under 20 original question owners, a verified subset of the original remaining 553. The separately prepared nine are outside this assessment. The proposed 12 stable target owners remain separate from the original question owners. The other two acquired relations, Dongxing 2774209 and Fangcheng 2774210, are outside the proposed twelve. Neither twelve nor fourteen is represented as a complete national OSM source collection.

All twelve raw relations have administrative boundary tags and `admin_level=6`, consistent with county-level roles. Eleven have division codes; Lüchun does not, so no twelve-code proof is claimed. Jingxi retains `old_name=靖西县;Jingxi County`, supporting an explicit crosswalk to the older county-form identity without implying unchanged historical boundaries. The accepted selected-before feature is literally equal as parsed to the current target feature in `data/geography/part-4.json` for every target. Their same-ID representative points lie strictly inside the corresponding new source. Original roster SID/owner/name and retained parent joins are exact. This supports stable administrative correspondence; it does not turn old source SIDs into the new source identity.

Primary contextual corroboration supports the prefectural roles: the [Yunnan natural-resources planning report](https://dnr.yn.gov.cn/html/2024/xwdt_0705/4046926.html) lists Malipo, Maguan and Funing under Wenshan; [Honghe's government overview](https://www.hh.gov.cn/zjhh.htm) lists Lüchun, Jinping and Hekou. An [older Ministry of Education administrative-code reference](https://hudong.moe.gov.cn/srcsite/A16/s3342/201203/W020220704498224866735.pdf) lists Ningming, Longzhou, Daxin and Pingxiang under Chongzuo. [Guangxi's project portal](https://zxsp.fgw.gxzf.gov.cn/service/project.jspx?areaCode=451081&projectType=A00001) provides Jingxi/Napo parent context in search-extracted text; a related direct page returned 403, so no full-page claim is made. A [Guangxi natural-resources article](https://dnr.gxzf.gov.cn/xwzx/zrzx/t16030184.shtml) describes Jingxi's county-to-city conversion. These are identity/context sources, not exact border surveys.

## Literal geometry, source version and raw provenance

The complete saved Overpass response is 1,894,713 bytes, SHA256 `b625ee0e686f239dd8eecf3eb21799228371ca5a1eef1c34c79a38905cf2d692`. The snapshot timestamp is `2026-10-16T00:19:04Z`; the saved retrieval receipt reports HTTP 200 at 00:19:56 GMT. The query requested the fourteen explicitly named relations using `out meta geom`. The twelve relation edit timestamps range from 2025-08-06 through 2026-10-13. The raw response is external source data, not permission or scientific authority.

An independent complete read establishes that all proposed relation IDs, versions, timestamps and tags match the raw snapshot. Every boundary member has geometry. Undirected boundary-segment multisets match the staged feature exactly, including multiplicity, with no added or omitted segment. All twelve features are valid and nonempty, and their pairwise positive-area overlap set is empty. No clipping, buffering, snapping, simplification, unrecorded transformation or invented source geometry is introduced.

**Relation version alone is not a full geometry version.** Member-way entries contain reference, role and geometry but lack individual way/node versions and history. Ways can change independently of the relation. The exact whole raw snapshot and derived geometry hashes must therefore accompany ID/version, rather than refetching a live relation and treating it as the same input. The new OSM source must remain distinct from frozen 2017 geoBoundaries China shape IDs. The old PDDL metadata and metadata adoption issue 2057 do not approve the new shape.

## Rights, datum, time and territorial limitations

The response and saved attribution declare OpenStreetMap contributor data under ODbL. [OSM's copyright page](https://www.openstreetmap.org/copyright) describes attribution, license notice and share-alike obligations for adaptations. The source supports properly attributed research and a separately identified OSM-derived route. Final output must preserve the actual OSM attribution/license and satisfy applicable derivative-database distribution obligations; this assessment does not certify the final combined database's licensing design. Old target PDDL cannot be applied to OSM-derived additions. No agreement was accepted in this review.

[OSM's GIS FAQ](https://wiki.openstreetmap.org/w/index.php?title=GIS_FAQ&oldid=3065325) specifies WGS84 latitude/longitude. The raw `lon`/`lat` coordinates and literal GeoJSON longitude/latitude ordering support that interpretation. Native observations used the pinned normative binary64 latitude table and the accepted ideal-rational longitude rule, not rounded reporting coordinates or regenerated Mercator rows. No known material datum conflict was found in these operands. The source does not supply survey accuracy, coordinate realization/epoch or original contributor transformation history. Those are explicit accuracy limitations; an undocumented datum error is not invented as evidence, and no correction is guessed.

The 2026 snapshot is a current contributor cartographic source, not proof of the 2020 Vietnamese or 2017 Chinese historical boundary, and not an official survey. Whole OSM polygons describe administrative extents and can contain water. [OSM's disputed-boundary explanation](https://wiki.openstreetmap.org/wiki/Disputed_territories) makes clear that contributor mapping is not legal adjudication. Absence of a disputed tag does not establish absence of uncertainty. The persistent Chinese/Vietnamese source disagreement is handled only by the declared display convention at the supported 348 exact keys. Survey/treaty proof is not manufactured, and none is claimed necessary to turn a display convention into legal truth.

## Contrary source evidence retained in full

The authenticated original source corpus contains 368 products and 73,567 features, with no remaining excluded/unsupported source features in its retained summaries. Complete roster/catalogue and blocks 27/28 cover every original key. Independently joining those exact records gives:

- 280 keys: Vietnam ADM1 and ADM2 contacts
- 37 keys: Vietnam ADM2 only
- 26 keys: China ADM1 and Vietnam ADM2
- 22 keys: China ADM1, Vietnam ADM1 and Vietnam ADM2

All 365 have a mapped contrary Vietnamese ADM2 contact, 302 also Vietnamese ADM1, and 48 Chinese ADM1. There are no old China ADM2 contacts at these keys. None is erased or recast as agreement. The 48 province contacts are not the source of the 348 display choices. The complete 708-feature Vietnamese ADM2 reread independently reproduced the original ADM2 contacts and established no boundary ties. The catalogue's represented-year/license claims remain distinct: Vietnamese ADM2 2020/CC BY 3.0 IGO, Vietnamese ADM1 2008/public domain, Chinese ADM1 2019/public domain, old Chinese ADM2 2017/PDDL. These are source claims, not certified survey dates.

Original-corpus completeness is not complete-current fine-geography proof. The author identified the current accepted world-index inventory as 36 parts and 49,625 canonical features; its all-365 contact/tie join remains pending. Any new conflicting same-country target or supplemental source must receive explicit applicability treatment before native qualification. This review does not pretend the old census covers every later source.

## Genuine physical result and measured new observations

The complete genuine twelve-target physical output is now recovered at public commit `f63c26ef357a062f084ce6ea01b2f7c6cd0d7586`, path `coordination/engineering/vietnam-chn365-source-update-20261016/physical-001/whole-target-support.json`. It is 861,435 bytes, SHA256 `a3b6e2d42f5f136bf1ed4c23d0e6ee388ffddaefeb069fc92a0c4ac9f8c5cd66`, Git blob `4a58650b6c16469ab842f2d41b66f7fa3c1fceac`. All twelve target identities match and issues are empty. Its independent public review joins all 365 to mapped-land-only support. The original execution was 15.627870833 seconds; no physical replay was performed.

That original invocation did not enforce its stated numeric memory/deadline policy. Darwin child-lifetime maximum RSS 408,027,136 bytes is not aggregate process-tree memory. Its genuine scientific observation is retained, while its receipt limitation is not retroactively repaired by this read.

The new full-country/twelve-source exact-native observation took 0.815 seconds under a prospectively checked 768 MiB process-group RSS limit and 120-second wall deadline, with sampled peak RSS 216,420,352 bytes. The missing Vietnamese shared-interior/tie check took 0.405 seconds under the same limits, peak 101,625,856 bytes. Both enforce limits by process-group monitoring and termination, preserve actual stdout/exit receipts, and perform no source-bank replay. Peak values are sampled observed peaks, not a claim to continuously measured maxima. The earlier raw-identity/segment/source-contact read used a 768 MiB address-space limit, 45 CPU seconds and outer 60-second timeout. A later country-validity diagnostic initially failed before parsing because Git's pack mmap could not fit the inherited virtual-address limit; the exact small blob was then read before installing the parser's limit. No output from that failed attempt was used.

## Remaining acceptance and delivery requirements

1. Parent acceptance must identify the exact 348 supported display-source choices and twelve genuinely new source identities, retaining the entire original 365 roster and the adverse 17.
2. Finish the complete current fine-geography/source applicability and tie proof, and assess any newly exposed competing target before claiming completeness.
3. Keep the source-to-existing-target crosswalk explicit. Preserve canonical county geometry, all previously selected cells and all original proof scopes. Do not relax the intentional legacy original-catalogue guard globally.
4. Correctly retain OSM provenance, attribution and downstream license obligations.
5. Establish exact current owner-zero, required source/physical/native qualification, predecessor conservation and emitted selected-map behavior with genuine resource enforcement. No already-owned key may be reassigned.
6. Make no accepted repair/native count change from this assessment. A later deliverable must bind the actual accepted subset and evidence rather than assume all 365 pass.

## Exact evidence locations

Public original source operands are under commit `84fb2759220b80e5b44531de899283613f9cfa39`, prefix `coordination/engineering/vietnam-chn365-source-update-20261016/`: raw response, retrieval receipt, provenance, attribution and whole stage. The stage is 872,634 bytes, SHA256 `620c3aab733389f4511491ba5c1f916f22c9235188b6e00d6a20053ef1020988`, blob `ff12987f4bfb1df9fabc13e474614a4a31604ef0`. Physical execution/review/exact365 association records are under the same prefix at `f63c26ef357a062f084ce6ea01b2f7c6cd0d7586`.

The complete country reference is retained unchanged at current accepted commit, path `data/retained-geographic-sources/namibia/natural-earth-reference-countries.geojson.gz`, blob `235bf73f0890fa97c82d1471f840296f17cfcfca`, encoded 4,719,659 bytes/SHA256 `7b631cc2986f597d3378b72d86c11d42b0ef843e130f9194ffdd2e52797da075`, decoded 13,287,234 bytes/SHA256 `239eec57ac17f100a11e2536cffc56752c318b50ae765b0918ff7aab4ce8f255`. Its earlier public locator is `f7c358326d776398bc1cffe84df81eac7033091c` at the same path.

The normative latitude operand, also unchanged at current accepted commit, is `coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz`, blob `de6905e162dc031b1b93248fae91190c39c4ad53`, encoded SHA256 `ab0becdda100da3473d7bb5d34ccda6510aa1c0490c407082072c7201ad1e147`, decoded SHA256 `66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23` (262,166 rows).

The unchanged original VNM ADM2 raw product is `coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-VNM-ADM2-000.bin.gz`, blob `d6351672b369b2e6919b10b7c959b3b709a3040e`, encoded SHA256 `8fa769599000ab536b18b4a9d18c71fe0fecbe134d4443e36e6b2797b41273a8`, decoded 5,273,788 bytes/SHA256 `2dff75b58e71f736ca9fd6ef7c859be40c6f9a9b7ae5cd0806b36fe8cfa4c4f6`.

The final machine-readable assessment includes all observation/input pins. `assessment-artifact-manifest.json` identifies local deliverables, scripts and actual execution evidence, including explicitly superseded provisional reads. A hash is provenance, not adoption authority.

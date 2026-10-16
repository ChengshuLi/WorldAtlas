# Distinct source assessment: original Vietnam 365, twelve revised OSM targets

Assessor: `/root/assess_vietnam_revised_sources`. Assessment date: 2026-10-16 UTC.
Issue: https://github.com/ChengshuLi/WorldAtlas/issues/2076.
Current accepted code and selected target-feature comparison: `cd68e89523901acf477d0365470410b8b970bb48`.

## Decision

**The twelve source identities, literal source geometry and county-level administrative roles are supported as a bounded research input. No candidate key is approved for native adoption. All 365 remain blocked by unresolved contrary Vietnam fine-source coverage.** This is an actual independent source assessment, not source-adoption authority, a full current geographic comparison, a native receipt, a geometry migration, or a legal determination.

The exact approved native subset is empty. The exact blocked subset is the 365 `original_key` records in `independent-source-assessment-final.json`, each retaining its original Vietnam owner/y/x, distinct OSM identity, proposed Chinese stable target and all original fine-source contacts. This keeps all 20 original question owners distinct from the 12 proposed target owners. The scope is a verified subset of the original remaining 553. The separately prepared nine are outside this source assessment; no accepted count changes.

This result does not establish that the Vietnamese source is correct or the OSM source is wrong. It establishes that the acquired evidence does not substantively resolve their contradictory assignments. An exact source join, a later database timestamp, a country-level mask, more vertices, unchanged existing selections, or dry-land support cannot make that determination alone.

## Independently executed checks

The bounded read used the actual complete raw OSM snapshot, all twelve literal staged source features, all twelve selected-before features, the exact public 365 association records, the complete retained original source roster/catalogue and the actual census blocks containing those keys. Every local source alias was checked against its stated whole-byte SHA256, Git blob OID and size before decoding. The current selected target part was independently authenticated to the accepted commit.

The read established:

- Fourteen distinct raw relations are present. The proposed twelve are an explicit subset; the other two are Dongxing `2774209` and Fangcheng `2774210`. Neither fourteen nor twelve is a complete national OSM source family.
- Every proposed relation ID, version, edit timestamp and tag set equals the corresponding raw snapshot record.
- Every boundary member has geometry. The complete undirected boundary-segment multisets are preserved exactly, including multiplicity, without extra or omitted segments. Nonboundary label, administrative-centre and subarea references are not boundary geometry.
- All twelve geometries are valid, nonempty polygons. Their pairwise positive-area overlap set is empty. These are geometry checks, not a claim of absolute positional accuracy.
- The full selected-before feature for each target is literally equal as parsed to its feature in accepted `data/geography/part-4.json`. Canonical county geometry and metadata were not changed.
- Each proposed stable target matches its actual pinned original source-roster row, owner index and same-ID selected feature. The same-ID retained representative point is strictly inside the respective new OSM polygon. This corroborates the county identity without using a border point or nearest-owner choice.
- All 365 proposed point records join to the original crosswalk and remaining-553 roster with no omitted or duplicate original key. Each retained rounded lon/lat lies inside exactly its one proposed OSM feature and on none of the twelve OSM boundaries.
- All 365 retained physical-review rows join by original key and new OSM identity and report `mapped_land_only`.

The point tests deliberately do **not** claim exact native-grid qualification. They use the proposal's retained finite lon/lat values through Shapely; the eventual native route must independently consume the pinned normative latitude table and exact rational native longitude predicate, retain boundary ties and perform current owner-zero/conservation checks.

The bounded independent read took 1.178 seconds, with Linux process maximum RSS 244,612 KiB. It used a 768 MiB address-space limit, 45 CPU-second limit and 60-second outer timeout. The observed available memory before it was 7,301,184 KiB; disk remained above the repository's 10 GiB floor. No source bank or physical producer was replayed. These are this small inspection's limits and measurements, not retroactive admission for the prior physical execution.

## Twelve identities and proposed portions

All listed native counts are **blocked proposed keys**, not delivered cells.

| OSM relation/version | County identity | Existing owner | Retained parent | Proposed keys |
| --- | --- | ---: | --- | ---: |
| 2723220 / 26 | Funing | 11270 | Wenshan | 39 |
| 2773869 / 24 | Ningming | 11573 | Chongzuo | 23 |
| 2719410 / 32 | Jinping Miao, Yao and Dai Autonomous County | 11584 | Honghe | 33 |
| 2719407 / 32 | Hekou Yao Autonomous County | 11700 | Honghe | 10 |
| 2773865 / 25 | Daxin | 11762 | Chongzuo | 31 |
| 2722419 / 26 | Napo | 11764 | Baise | 6 |
| 2719413 / 18 | Lüchun | 11930 | Honghe | 5 |
| 2723223 / 30 | Malipo | 12076 | Wenshan | 13 |
| 2773976 / 22 | Jingxi City | 12115 | Baise | 6 |
| 2773868 / 21 | Longzhou | 12167 | Chongzuo | 155 |
| 2723222 / 27 | Maguan | 12908 | Wenshan | 3 |
| 6881348 / 14 | Pingxiang City | 13210 | Chongzuo | 41 |

The raw tags explicitly describe administrative boundaries at OSM `admin_level=6`; the retained Atlas sources describe county-level locations. Eleven relations have a division code. Lüchun does not, so it must not be claimed that twelve codes independently establish the join. Name, parent context, exact same-ID retained point and original roster support the Lüchun correspondence. Jingxi explicitly retains `old_name=靖西县;Jingxi County`; its selected identity retains the older county-form name. That supports an explicit identity crosswalk, not a claim that any two vintages have identical boundaries.

Primary contextual corroboration, read on 2026-10-16, agrees with the county/prefecture interpretation:

- [Yunnan Department of Natural Resources, 2024-07-05](https://dnr.yn.gov.cn/html/2024/xwdt_0705/4046926.html) describes the Wenshan prefectural planning approvals for Malipo, Maguan and Funing among its counties.
- [Honghe government's overview](https://www.hh.gov.cn/zjhh.htm), geographic-environment paragraph, lists Lüchun, Jinping and Hekou among the prefecture's counties and places Honghe on the Vietnam border.
- [Ministry of Education administrative-code reference](https://hudong.moe.gov.cn/srcsite/A16/s3342/201203/W020220704498224866735.pdf) lists Ningming, Longzhou, Daxin and Pingxiang under Chongzuo; it is an older code reference and is not a current boundary survey.
- [Guangxi's official investment project portal](https://zxsp.fgw.gxzf.gov.cn/service/project.jspx?areaCode=451081&projectType=A00001) presents Jingxi and Napo under Baise in its administrative navigation. Search-extracted text was available; direct opening of a related portal URL returned 403, so no stronger full-page or legal boundary claim is made.
- [Guangxi Department of Natural Resources, 2015-10-29](https://dnr.gxzf.gov.cn/xwzx/zrzx/t16030184.shtml) discusses Jingxi's county-to-city conversion. This contextual name evidence is not a geometric supersession instrument.

These sources establish broad identity/administrative context only. None supplies a surveyed line or a per-key territorial decision. OSM's whole polygons are administrative extents, not whole dryland and not historical 2020 county footprints. Whole-feature bounds are retained in the JSON rather than using an artificial buffer, clip or mask to select the proposed portions.

## Contrary coverage: complete original corpus, exact finite subset

The original complete corpus has 368 products and 73,567 features. Its pinned raster summary reports no remaining unsupported source features and the census no excluded source features. Its known Fiji normalization supplement remains in those original summaries; this review did not remove it or redefine global completeness.

The retained blocks cover all 365 exact rows/columns. Independently joining their actual source indices to the full source roster and catalogue yields these mutually exclusive sets:

| Original source-family contacts | Keys |
| --- | ---: |
| Vietnam ADM1 and ADM2 | 280 |
| Vietnam ADM2 only | 37 |
| China ADM1 and Vietnam ADM2 | 26 |
| China ADM1, Vietnam ADM1 and Vietnam ADM2 | 22 |

Thus every key has contrary mapped `gb:VNM:ADM2` coverage; 302 also have Vietnam ADM1 and 48 China ADM1. There are no old China ADM2 contacts at these keys. The 48 Chinese province contacts do not eliminate the conflicting Vietnamese finer-source contacts. The province contact cannot be used as a country-mask assignment rule. No conflict-free native subset was identified.

The catalogue records the contrary Vietnam ADM2 represented-year claim as 2020 and its license as CC BY 3.0 IGO; Vietnam ADM1 is the 2008 claim and China ADM1 the 2019 claim. The old China ADM2 predecessor is the 2017 PDDL source. These are distinct product claims, not independently proven survey dates. All original contacts and identifiers remain in the finite JSON disposition.

This is complete **for the pinned original corpus at its retained census vintage**. It does not prove that every accepted supplemental source, current country reference, alternative fine geography or external source is represented. The full then-current comparison and explicit adverse-contact disposition demanded by issue 2076 remain absent. No stale census is relabeled as a fresh global proof.

## Source provenance, rights and datum

The Overpass query requested fourteen named relations with `out meta geom`. The saved response is 1,894,713 bytes, SHA256 `b625ee0e686f239dd8eecf3eb21799228371ca5a1eef1c34c79a38905cf2d692`, from snapshot `2026-10-16T00:19:04Z`; its saved retrieval receipt reports HTTP 200 at 00:19:56 GMT. An HTTP response does not establish territorial truth. The twelve relation edit timestamps range from 2025-08-06 to 2026-10-13.

**A relation version is not a complete geometry version.** The saved member-way entries provide reference, role and geometry but no individual way/node version history, survey date or per-segment accuracy metadata. A member way can change independently of the containing relation. The complete immutable snapshot and exact derived geometry therefore remain essential operands alongside relation ID/version. Do not fetch a current live relation later and call it this same input.

The raw response declares ODbL. [OSM's copyright/licensing page](https://www.openstreetmap.org/copyright) identifies the database license and requires attribution and notice of ODbL, with share-alike obligations for adaptations. The reviewed source is usable as a properly attributed research input; this assessment does not certify the final combined database's distribution design. The existing 2017 target's PDDL metadata cannot be applied to OSM-derived additions. Preserve OSM attribution/license on the new-source path and assess the actual derivative distribution before publishing. No agreement was accepted and no publication was performed here.

[OSM's GIS FAQ](https://wiki.openstreetmap.org/w/index.php?title=GIS_FAQ&oldid=3065325) specifies WGS84 latitude/longitude. The literal raw fields are decimal `lon`/`lat` and the derived GeoJSON uses longitude/latitude order without conversion. That supports coordinate interpretation. It does not establish a particular geodetic realization/epoch, survey accuracy, boundary delineation method or an independently validated conversion from any upstream source. Those facts are not supplied by these raw relation/member records. There is no evidence here of a GCJ-02 transformation being applied; nor can its absence in provenance prove the correctness of every contributor's original measurement. No datum correction, buffer or tolerance was invented.

[OSM's boundary policy explanation](https://wiki.openstreetmap.org/wiki/Disputed_territories) describes contributor mapping and approximate lines where boundaries are unclear. The raw twelve lack a `disputed` tag, but absence of that tag is not evidence that the 365 exact locations have no territorial uncertainty. No treaty, surveyed demarcation, authoritative per-segment geometry or demonstrated source-generalization error was acquired that would resolve the conflicting fine-source assignments. Current contributor mapping is not an official Chinese survey or sovereignty adjudication.

## Physical evidence and remaining gates

The first physical execution is genuine retained work, and it must not be replaced with an old 2017 or Vietnam physical result. Its public independent review joins all 365 keys to mapped-land-only support in all twelve new whole source geometries with empty target issues. The publication view records 15.627870833 seconds, exit 0, and Darwin child-lifetime maximum RSS 408,027,136 bytes.

The original physical invocation did **not** enforce its stated numeric memory policy or a custom deadline. Child-lifetime maximum RSS is not aggregate process-tree RSS; a later capacity observation is not prospective admission. This source assessment cannot turn the execution view into a qualified SOURCE/NATIVE receipt or erase those limits.

The complete raw physical result is pinned at 861,435 bytes, SHA256 `a3b6e2d42f5f136bf1ed4c23d0e6ee388ffddaefeb069fc92a0c4ac9f8c5cd66`. Its publicly referenced original path is `bulk-completion/chn365-first-physical-001/actual-products-001/whole-target-support.json`; the complete body was not available in this cloud review. I inspected the authenticated public result review and execution view, not a reconstructed or fabricated whole result. Recover the genuine original if a downstream contract must consume it; this finding alone is not a reason to replay unchanged science.

Before any affected key can receive native credit, the missing evidence is a substantive bounded source-applicability decision resolving its contrary fine-source/territorial contacts, followed by the actual complete current country/fine-source comparison, exact boundary-tie checks, current-owner-zero, unchanged predecessor conservation and ordinary selected/package consumer verification. Keep original scopes and all adverse findings. If a key lacks that evidence it stays blocked. A parent may choose further source research, but an engineering boolean cannot make this assessment an approval.

## Exact artifact pins

The machine-readable final assessment contains all inspected input pins and every blocked key/contact. The principal public operands are:

- `84fb2759220b80e5b44531de899283613f9cfa39:coordination/engineering/vietnam-chn365-source-update-20261016/whole-new-source-stage-inputs.json`, 872,634 bytes, blob `ff12987f4bfb1df9fabc13e474614a4a31604ef0`, SHA256 `620c3aab733389f4511491ba5c1f916f22c9235188b6e00d6a20053ef1020988`.
- Same commit/prefix `osm-full-county-relations.json`, 1,894,713 bytes, blob `d1344471a7a39f157de2509de52fb42400ab20c9`, SHA256 above.
- `f63c26ef357a062f084ce6ea01b2f7c6cd0d7586`, same prefix, `physical-001/exact365-new-source-identity-inputs.json`, 119,549 bytes, SHA256 `53b6a1400802e8f73d25a2dcad6f14606e07add90ed54542f94b0895e4e1748b`.
- Same commit/prefix, `physical-001/actual-first12-result-review.json`, 345,035 bytes, SHA256 `09ae2569c5f07ce95f1a9f32866113839c06beb03e99d8ea9f0cef5af3061297`.
- Same commit/prefix, `physical-001/actual-execution-publication-view.json`, 14,107 bytes, SHA256 `6433f0fecd877c99c48a6d08007b6d19d586f141fefd595ae1c4d37d183dc0bf`.
- `cd68e89523901acf477d0365470410b8b970bb48:data/geography/part-4.json`, 4,835,479 bytes, blob `ccdefbb55c62b317f11e6078cd9291dae5339693`, SHA256 `e204a879e160f8b22ccfff698e8063a79d91cdba5ef7aa87df94661323b0bd3c`.
- Complete original census/roster/catalogue and block 27/28 pins at `6ef487cd8f29e714dd10ae963d9fd58c41fd1b54` are individually retained in the JSON. Their original inputs and outputs were not modified.

No external source acquired during this assessment was used as new geometry. The official contextual pages above were read as source corroboration, with explicit retrieval/failure limits; the only geometry consumed is the already retained immutable raw OSM snapshot and accepted target features.

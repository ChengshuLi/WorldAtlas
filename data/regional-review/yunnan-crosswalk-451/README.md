# Yunnan seven-feature crosswalk research (issue #914)

Research recorded 2026-10-08. This is a source and identity packet only. It preserves every native geoBoundaries ID and does not modify hierarchy, geometry, release pins, or production data. The retained source lives in the ancestor packet #451; this work does not copy or rewrite it.

## Findings

The ancestor source is the complete 2017-vintage geoBoundaries CHN ADM2 file (2,391 features; 7,618,692 bytes; SHA-256 `2b68d8a808742fc6d7acd769584db960d8fc2c25b9f1d20e3e98c72e9f1c4d34`). Its metadata describes `boundaryYear=2017`, `boundaryCanonical=County Level`, `boundaryType=ADM2`, and PDDL 1.0. Feature properties carry `shapeGroup`, `shapeID`, `shapeISO`, `shapeName`, `shapeType`; they do not carry official unit codes, county parent IDs, or lineage. The cited upstream attribution is preserved in the ancestor packet; the upstream authority behind the boundary download and its exact legal boundary vintage remain unverified.

The source-only reproduction locates all seven requested IDs exactly once. Each is a valid single-part Polygon in this file. It records WGS84 bounds and source-internal boundary neighbors in `source-findings.json`. Neighbor lengths are raw coordinate degrees. This only checks internal consistency/context; it cannot establish identity, legal boundaries, completeness, islands, or vintage correctness.

| Feature label | Evidence-based identity result | Boundary result |
|---|---|---|
| Qujingshi | The Qujing municipal government history page reports State Council approval (国函〔1997〕32号) abolishing the former county-level Qujing City and creating Qilin and Zhanyi from enumerated townships. It supports a historical split as the explanation for the obsolete source label and the present nine-unit roster, but does not prove this polygon equals the exact legal union of the two successor districts. | Unresolved: no adequate retained 2017 legal map or independent authoritative county polygon. |
| Zhaotongshi | The 2001 Gazette index and source packet identify the State Council approval chain (国函〔2001〕6号) by which former county-level Zhaotong became Zhaoyang District. The Gazette text could not be retrieved from the official portal during this review; exact feature-to-successor boundary identity therefore remains unproven. | Unresolved. |
| Ludingshi | No primary crosswalk from this feature label/shape to Ludian County was found. Similar romanization is insufficient. | Unresolved. |
| Jianshanxian | No primary crosswalk from this feature label/shape to Yanshan County was found. Similar romanization is insufficient. | Unresolved. |
| Milexian | Yunnan Government notice 云政发〔2013〕29号 states the former Mile County administrative area became Mile City. Entity continuity is supported; the feature polygon has not been shown to match that legal area. | Unresolved. |
| Wenshanxian | The cited 2010 approval is reported as preserving the former county administrative area when establishing Wenshan City; a primary official text was not retrievable in this review. Treat the name relation as a lead, not as verified map identity. | Unresolved. |
| Mengzixian | The cited 2010 approval is reported as preserving the former county administrative area when establishing Mengzi City; only a non-primary transcription/index was located. Treat the name relation as a lead, not as verified map identity. | Unresolved. |

The Yunnan Civil Affairs current roster page was indexed as listing the provincial administrative units, but direct retrieval timed out. The indexed official roster reports Qujing's nine current county-level units. The Qujing government history independently enumerates Qilin, Zhanyi, Luliang, Luoping, Huize, Malong, Fuyuan, Shizong, and Xuanwei while noting Xundian's 1998 transfer to Kunming. This reconciles the roster count at the entity level only. It does not identify which feature(s) need correction or validate geometry. Current code pages and county-level maps are needed for a defensible feature-to-code/map join.

## Source access, rights, and restoration

- **Retained original:** ancestor packet #451 `sources/geoboundaries-chn-adm2-2017.geojson`; exact hash above. Its ancestor source register records access and declared PDDL 1.0, with attribution requested. Reproduce from that exact ancestor file; never replace it with a later download.
- **Qujing government history:** <https://www.qj.gov.cn/html/2013/qjdsj_0419/3135.html>, retrieved/indexed 2026-10-08. Online page reports 国函〔1997〕32号 and successor township lists. The page was inspected through text indexing; original bytes were not retained here. Restore by GET of the URL. Government publication reuse terms for this specific page were not established; cite, do not redistribute page bytes.
- **Mile notice:** exact PDF URL is recorded in `evidence-quality.json`. Inspected PDF text states the former county administrative territory became the city. Restoration: GET that exact URL, retain original PDF bytes and compute SHA-256 before reuse. Government legal text; no separate document license notice inspected. Do not redistribute without checking applicable terms.
- **Yunnan Civil Affairs roster:** <https://ynmz.yn.gov.cn/bmfw/xzqh/xzqhsz/>, indexed 2026-10-08; direct retrieval timed out. Restoration: retry GET, save page and any linked roster attachment with response date and hashes. Terms/license unknown. Search excerpt is not treated as full row-level source verification.
- **Zhaotong Gazette:** <https://www.gov.cn/gongbao/2001/issue_67/>, retrieval returned 403. Restore from the official Gazette issue index or request the exact 国函〔2001〕6号 page/document from gov.cn; preserve bytes/hash and inspect successor-area text. Official document; reuse terms not inspected.
- **Wenshan and Mengzi 2010 approvals:** exact primary published pages were not retrieved. Restore/request 民函〔2010〕295号 and 民函〔2010〕219号 through Ministry/Provincial Gazette or Civil Affairs archives. Secondary transcriptions are discovery leads only. Rights and exact source vintages remain unknown.
- **Boundary evidence:** the provincial 2023 administrative map is prefecture scale, inadequate for county boundary checks. Yunnan's cited 1:50,000 boundary atlas is not openly retained in this packet. Request authorized access from Yunnan Civil Affairs/Natural Resources to the applicable contemporaneous county boundary map or authoritative polygon release; record scale/vintage/license/hash and compare every target boundary, including islands and disconnected areas.

No geometry correction is proposed. Engineering follow-up, after authoritative map evidence exists: resolve each source ID to its historic/current official code and parent; for Qujing test whether the historical polygon corresponds to successor territories rather than infer a union; validate all shared borders, multipart/island coverage and source vintage against an adequate authoritative map. Preserve IDs unless a separately reviewed migration plan justifies otherwise.

## Reproduction

From repository root with Python 3 and Shapely 2.x:

```sh
python data/regional-review/yunnan-crosswalk-451/reproduce_crosswalk.py > /tmp/yunnan-crosswalk-914.json
cmp /tmp/yunnan-crosswalk-914.json data/regional-review/yunnan-crosswalk-451/source-findings.json
```

The script reads only the exact ancestor source, requires all seven unique IDs, computes source-internal adjacency, and emits deterministic JSON. No network access is required. Running it twice and comparing output hashes is a reproducibility check; it is not a geographic correctness check.

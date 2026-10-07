# Cabinda inventory erratum for #411

This note supersedes one inventory sentence in the historical #1047/#1057 evidence handoff: the four 2018 geoBoundaries Cabinda ADM2 IDs listed below are **present in the retained Atlas partition** and **outside the frozen 223-member #411 workload**. They are not absent from all Atlas partitions. Each ID also occurs once with the same name in the original retained geoBoundaries AGO ADM2 source. This is an inventory correction only; it does not establish that these legacy features represent the ten municipalities listed in Angola Law 14/24, or that any current boundary source is complete, authoritative, or reusable.

| Atlas ID | Stored Atlas name | Stored parent |
| --- | --- | --- |
| `gb:AGO:ADM2:16411231B22766430211667` | Belize | `framework:province:cabinda:fb67d098df5d` |
| `gb:AGO:ADM2:16411231B679187258105` | Buco Zau | `framework:province:cabinda:fb67d098df5d` |
| `gb:AGO:ADM2:16411231B42954517222252` | Cabinda | `framework:province:cabinda:fb67d098df5d` |
| `gb:AGO:ADM2:16411231B63355352791940` | Cacongo (Landana) | `framework:province:cabinda:fb67d098df5d` |

## Source vintage and limits

The original retained source is geoBoundaries gbHumanitarian AGO ADM2 at upstream commit `9469f09592ced973a3448cf66b6100b741b64c0d`, reported boundary vintage 2018. Its 3,146,775-byte GeoJSON has SHA-256 `44e58b2a8c2fefb9369294a32e2adde3e3637b9e02e8f1e2c53b400bec04f404`; the 927-byte metadata file has SHA-256 `0f45ab188f1e12b2f4068ecddeb62b2fb73d4ee7d1a71e29a8a8992d4b7ad302`. The retained source receipt records retrieval at `2026-10-06T00:15:21Z`. The official geoBoundaries GitHub API at that immutable upstream commit returned LFS pointers whose SHA-256 object IDs and byte sizes match both retained artifacts.

The pinned metadata reports 161 national ADM2 units, boundary source lineage `www.gadm.org and Instituto Nacional de Estatística (INE); see methodology, HDX`, source data update `2023-01-19`, build `2023-12-12`, and `CC BY 3.0 IGO`. Preserve attribution to geoBoundaries and its listed underlying sources. The reported underlying-source URL is malformed (`https//data.humdata.org/dataset/cod-ab-ago`, missing the colon), so this packet does not retrieve or assess that underlying source. The 161 count is the 2018 national source count; it is not a coverage denominator for current Cabinda municipalities, and this four-ID check does not claim these are all historical units in Cabinda. The four source shapes’ names match the four retained Atlas names exactly. The Atlas parent IDs are recorded above, but this check does not establish that the stored province parent or 2018 territorial meaning remains current. Neighboring-unit granularity and post-2024 completeness are unresolved and remain with #896.

## Reproduction and byte provenance

From the repository root, run:

```sh
node data/regional-review/southern-africa-411-cabinda-inventory-erratum/reproduce.mjs
```

Run it twice and compare the complete JSON output bytes. The script loads the #1047 README from commit `762d7b5a568ca845d85a98a4d188678c126a5d58` and the #1057 README, frozen scope and complete part 29 from commit `c9f2ce1f4fe6434a42a8fbe4886dcfcaa73169e8`. It checks every expected byte count and SHA-256 before parsing. The two README vintages cannot both be baseline files at a single commit; the #1047 file therefore has an explicit historical restoration descriptor in `evidence-quality.json`, while the three co-resident #1057 files are pinned baseline inputs.

The deterministic result and positive, negative and two-run controls are retained alongside this note. The whole `part-29.json` input contains 1,500 features. The exact frozen `scope.member_location_ids` array contains 223 unique IDs. Each listed Cabinda ID occurs exactly once in the original 161-feature 2018 source and once in part 29, with matching names; none occurs in the frozen scope array. A fabricated ID is absent from both inputs, and the intentionally incorrect assertion that all four are in-scope fails.

The relevant original handoffs are [#1047](https://github.com/ChengshuLi/WorldAtlas/pull/1047) and [#1057](https://github.com/ChengshuLi/WorldAtlas/pull/1057); the frozen workload is [#411](https://github.com/ChengshuLi/WorldAtlas/issues/411), while current authoritative Cabinda boundaries remain owned by [#896](https://github.com/ChengshuLi/WorldAtlas/issues/896). This erratum is tracked in [#1284](https://github.com/ChengshuLi/WorldAtlas/issues/1284).

## Limits

The reproduction verifies repository byte identity, exact source-to-Atlas identity/name joins and workload membership, and reports the stored parent attributes. It does not validate geometry, legal territorial meaning, current municipality identity, source completeness, neighboring granularity, or the accuracy of the original 2018 boundaries. Metadata reports CC BY 3.0 IGO; this does not independently establish rights in underlying source material. It does not authorize a new Atlas ID, boundary change, import, geographic approval or publication. Preserve the original packet and all prior scientific classifications unchanged.

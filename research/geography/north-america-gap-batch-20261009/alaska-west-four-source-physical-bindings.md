# Aleutians West four: source and physical custody handoff

This source-only handoff resolves four rows from the complete GEO5 North America batch. It authenticates the original component features and joins them to the original physical report products and original administrative-routing records. It performs no source/GIS operation, geometry calculation, production write, or repair proposal.

## Exact cohort and current administrative binding

The four exact component IDs are:

- `physical-component:18bde5cda8660806ef3cf9f851a006be827c80bc6ebf9cc5a92abdfc3f2249d0`
- `physical-component:6941aa6f88a5581bf95d63718e554f6f37fb1d9fa70db7636b3b3f2914d49f6a`
- `physical-component:ac95cb3b778a830c88ed69150c06716eed6014ab0c067331c3196fb79c274df4`
- `physical-component:baf74325795539a3fcc7d27feb2a04c376a0e1d3c3287eba435ea85b99607be6`

Each original route record reports one compatible recorded subject, `gb:USA:ADM2:52423323B14067598441828`, named **Aleutians West**, parent `framework:province:alaska:d12fadcdd2dd`, reference year 2018. The four route rows agree with the full pointset feature hashes listed below. They also retain `surface_status=unverified` and `cause_status=unknown`; their source-fitness route remains unapproved.

On base commit `f0a0c5f1c252e68b3b987cef8625ba9d185c215f`, `data/geography/part-25.json` has exactly one target feature. The file is 4,525,239 bytes, SHA-256 `dada55df1b7f0f2a2b307f4aea071d0e48791e3105875755fe74a292a6763394`. Its feature metadata identifies `geoBoundaries gbOpen`, USA ADM2 / Counties, 2018, Public Domain. The administrative-source catalog records the upstream boundary source as the U.S. Census Bureau, with the same 2018 ADM2 product. This unique recorded-subject binding does not establish that a component is an accepted government land unit or prove physical authority.

## Exact original pointsets

The full original component features were restored byte-for-byte from custody source commit `450126d04c7e6bf85c8763c9bb6949c1fac68000` using the exact gzip-decompression receipt at restoration commit `79a41b0bfd412b0d431e57cb03a4aed46597b1af`. The shard byte hashes match the custody receipts; every full feature hash matches both the retained source-fitness row and its original physical-comparison row.

| Component suffix | Pointset shard | Feature array index (0-based) | Full feature SHA-256 | Geometry SHA-256 |
|---|---|---:|---|---|
| `…3f2249d0` | `components-001.json` | 400 | `0dc16e1a578761df22282129fcdd6dc1700ff6fe17b709e95873b2eda5e8a453` | `839a548dd505982c2404d9fec070840db0850d914e09c86c17ed24748ebc89d1` |
| `…14d49f6a` | `components-004.json` | 3868 | `4e0be0d0200f6a6109d1b8e509c39ce58a80617b85c8dd91ba5c5ada92140f0e` | `93ec17aba15e0ed2c7e4ec2e57b877249967e9c404af972f2121504a99ff729d` |
| `…9c274df4` | `components-007.json` | 2468 | `3d9631fbd175075c49d66c0068b445de0f396fb0bdd6e94f0afcda09aa50db7a` | `3b2659f3a633defc8c40e67cb2f9cfb16bb3ca1451a4301e33ec9d08292097d3` |
| `…99607be6` | `components-007.json` | 7741 | `d0607905ac28495ea8e761a17132bcc9f7c03aefc6a816408a5a6b568ff513dd` | `5edcb418f6c8bb057c8b05ce7b99dfdafeb661124e0bb2af275bf56b069a364b` |

## Original physical report and product joins

I retrieved the complete original report (57,840 bytes; SHA-256 `2a5b59198681d50f577bc4c2c321174f166aec14f57c7564100fc411ae940df0`) and its physical transport map (56,473 bytes; SHA-256 `644345be3d231431177c416b6ddbe3a1b2486597295af45fd5224857b5612d26`). Both pin execution commit `104091cfecd9c83a53f3e6e62f95b0a0c8074351`. The report's original descriptors match the transport map's original descriptors and the preserved original products byte-for-byte, including decoded hashes. The transport map separately records the transformed delivered descriptors. The four comparison shards in the checkout match those delivered descriptors; they are not the original report-pinned shard bytes.

| Component suffix | Original product row (1-based) | Original compressed SHA-256 | Original decoded SHA-256 | Source-relative mapped-land area |
|---|---:|---|---|---:|
| `…3f2249d0` | `components-006.jsonl.gz`, 1147 | `a5a540231d1eb0539b97ee4549cd16119d839e8b5126a52a85e8cd3e1fcb1f4c` | `e969e873dbcfec42b788ba161349c231d88d765e02a52e701176dfb5c5530d7a` | 1,220.092864610161 m² |
| `…14d49f6a` | `components-028.jsonl.gz`, 1173 | `583a2ab684718b5266c70a739218920f95d3adedd168e5ff29575f8ed654b14a` | `d563fce1a05e5115eeeae2ee3fdfa64608f11d172dd9e42b582a93dd1cb1b77d` | 60,037.24628970157 m² |
| `…9c274df4` | `components-047.jsonl.gz`, 665 | `e418e6cf92971f0afc047b2782fcb035e1f6305c136969469cb8be085089e82d` | `4c592e19b5d3fb42a2a539235999fb2e1a089cd5cde4219e37c5324c9af4438e` | 16,971.940633394315 m² |
| `…99607be6` | `components-051.jsonl.gz`, 557 | `66e0febf986ec0c177c3be12e9fc7a5d33a189f45758aa6348db8bdda01953b4` | `8e0bed9f09c8544341f64c06ee867eb44ced17458fbf2a9ffa369f2774fd82ec` | 74,865.1460036213 m² |

The original `sources-000.jsonl.gz` also matches the report-pinned compressed and decoded hashes. All eight query relations join to exact original source records: source IDs 2 and 176 for the first component; 0 and 2123 for the second and third; 0 and 4100 for the fourth. Each query's `source_record_sha256` and decoded pointset hash match the corresponding original source record fields. The report rows classify each as `mapped-land-support`; physical authority is unapproved and physical status is `unknown-source-fitness-and-observation-date`. The source vintage is GSHHG 2.3.7 / 2017-06-15; observation dates are heterogeneous. The areas are source-relative output, not accepted physical status.

The full features, report and transport-map receipts, original component and source rows, hashes, query joins, and original routing records are preserved in [the four-case evidence JSON](./alaska-west-four-source-physical-evidence.json). The previous draft's integrity caveat concerned comparison shards that differed from the original report. The report and transport map now explain that difference: the available checkout shards match the mapped delivered descriptors, while the original report-pinned products were independently retrieved and verified from the preserved cache.

## Issue overlap and disposition

A fresh live readback on 2026-10-09 checked public issue bodies/comments and the merged source PRs for all four exact IDs. None appears in #1488 (13 IDs), #1508 (13 IDs), #1620 (13 IDs), #1377 (31 IDs), #1362 (43 IDs), or their source PRs #1384 and #1378. The published USA31 and BC43 issue rosters have no exact-ID overlap with this quartet. Closed #486 describes Alaska physical-ecoregion portions but publishes no component IDs, so its relationship remains unknown. Open #1394 has an active claim for broader source-operand recovery, but publishes no exact roster for these cases; overlap remains unknown. The issue readback records the live issue states, timestamps, roster checks, and active claims.

## Four-case source-rule and physical decision

The exact decision record is [alaska-west-four-case-source-rule-and-physical-decision.json](./alaska-west-four-case-source-rule-and-physical-decision.json). It projects the already retained physical, query, route and source-fitness rows; it does not rerun their joins or any source, GIS, geometry, native or global operation.

The four cases match the source-relative product profile used by the merged Alaska additive batch: GSHHG 2.3.7 (released 2017-06-15), WVS source flag 1, level 1, and river/lake flag 0. For each component, one retained source record fully covers it and the paired checked comparison record is disjoint; each physical report row says `mapped-land-support`. Their recorded administrative route is the same geoBoundaries gbOpen USA ADM2 Counties 2018 product, release tag `9469f09`, and each has exactly one compatible Aleutians West subject. The metadata update date (2023-01-19) and build date (2023-12-12) describe the administrative dataset/catalog, not the physical observations. The cited GSHHG README describes WVS as public-domain data; this is the source documentation statement, not a separate legal determination.

The accepted Alaska rule is bounded to its exact 13 measurement IDs (11 source-compatible, 2 exceptions); none of these four IDs is in that roster. Its approved limits explicitly say GSHHG land support is source-relative only and leave per-feature observation date, positional precision/registration, and contemporary physical truth unresolved. The four therefore have a strong predicate match for a proposed source-relative extension, but the existing case-level approval does not automatically cover them. Independent exact-head review must accept or reject that extension.

For each of these four, the retained evidence supports only the source-relative label `mapped-land-support`. The physical report still says authority `unapproved`, status `unknown-source-fitness-and-observation-date`, and the pointset has `water_status=unverified` and touches the reference shore. No exact record establishes per-feature observation date, shoreline accuracy/registration, or whether the footprint is exposed land, intertidal rock/reef, or water. No dated authoritative shoreline/hydrographic record for these exact footprints is retained. Thus current physical land/water class, repair cause and repair authority remain unresolved. No geometry or repair proposal is made.

This four-case handoff preserves the entire #1630 batch scope (4,674 components / 152 families) and the global #1202 umbrella. It closes neither issue and creates no per-family issue. No current production assignment, source operator, GIS operation, native diagnostic, production write, or deployment was performed.

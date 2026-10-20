# Argentina held-residual disposition proposal

Issue #2373; original package `gb-ARG-ADM2--repair-evaluation`.

This additive packet proposes documented-unresolved dispositions for the exact retained residual of **6,149 original keys**. It does not accept exceptions, add repair credit, change selected ownership, or complete the package. All 6,149 keys remain held pending one distinct exact-head review and explicit root acceptance. The **22,697 previously accepted supported cells** remain the existing baseline and are not re-counted.

## Exact selected-owner readback

`selected-owner-observation.json.gz` is the lossless gzip transport of the complete `literal-selected-owner-observation-v1` report for all **28,846** original keys and **10,702** intervals at current main `cdce5b02d354431321436b8f8674d804df629c01`. Decoded JSON SHA-256: `05f0660ebdb400e5c916f87ded56498d2b8af09aab0365efd4ebd775e83329bd` (10,040,091 bytes). Gzip transport: 280,875 bytes; SHA-256 `2a84acf17ba0324ef4aa43a44d2c81e9d41d6d4c5a388cdffeda0eb6af529a79`. The report records executable code and consumed data pins; `pins.json` carries the complete pin inventory and exact source-reference pins used here.

The observation reports zero base owners, **22,697** accepted-additive/effective selected owners, **6,149** effective-owner-zero keys, and zero overlaps. The exact held-roster join finds all 6,149 held keys ownerless; every key outside the roster has a selected owner. There are no mismatches. The residual covers **1,937 complete original intervals**, with no partially held intervals; the remaining **8,765** original intervals are outside the residual roster. This is selected-product state only.

## Retained unresolved partitions

The disjoint reason combinations are copied verbatim from the original held roster:

| Existing hold reason combination | Keys |
| --- | ---: |
| `unresolved-pre-2020-Tierra-del-Fuego-unit-scope` | 5,088 |
| `foreign-whole-original-contact` | 1,024 |
| `unresolved-CABA-membership` | 32 |
| `unresolved-seven-component-source-fitness` | 4 |
| `foreign-whole-original-contact` + `unresolved-pre-2020-Tierra-del-Fuego-unit-scope` | 1 |

The tag totals for Tierra del Fuego (5,089) and foreign contact (1,025) overlap by one key; their union remains 6,149. The original queue mask labels are 6,142 land and 7 inland-water keys; these do not establish current physical classification. Per-key coordinates, reason tags, exact owner/feature interval joins, and zero-owner observations are in `reconciliation.json`.

The existing source/native handoff and delivery remain the evidence basis: [source/native review #2382](https://github.com/ChengshuLi/WorldAtlas/pull/2382#issuecomment-6230033473) and [accepted delivery #2399](https://github.com/ChengshuLi/WorldAtlas/pull/2399). This packet does not repeat their source or physical analysis.

## Status and limits

`reconciliation.json` records `proposed_unresolved_unaccepted`: accepted repairs 0; accepted exceptions 0; new repair/exception credit 0; selected owner changes 0; package complete false. It carries existing hold tags without upgrading them into applicability or boundary findings. No contemporary legal boundary, sovereignty, whole-cell physical fitness, regional approval, publication approval or historical import is claimed. All native holds remain pending root review and decision.

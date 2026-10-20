# Estonia held-residual disposition proposal

Issue #2381; original package `gb-EST-ADM2--repair-evaluation`.

This addendum proposes a documented-unresolved disposition for the exact
residual in the retained source/native handoff. It does **not** record accepted
exceptions, new repair credit, or package completion. All residual keys remain
held pending independent review and explicit root acceptance.

## Reconciled selected state

The committed `current-selected-owner-observation.json.gz` is a lossless gzip
transport of the complete `literal-selected-owner-observation-v1` from
`scripts/observe-selected-owners.mjs` for all **34,461** original keys, using
both data and executable code at main `a4390854c013c8891b187556ac4498888ee33633`.
The 279,574-byte gzip SHA-256 is
`d91993df4eac28efca346328053a6a44f10253e5f410ac27208edff27bb00937`; the
11,520,172-byte decoded JSON SHA-256 is
`6ea0e1bac4479729f2ae0f27d3eca8e18ce7273a6d4620e98eab3552ea7ff7d6`.
The observation reports zero base owners, 30,621 selected additive/effective
owners, 3,840 effective-owner-zero keys, and zero base/patch overlaps.

`reconciliation.json` records the exact-key join against the immutable
`qualified-native-inputs-001/held-original.json`: all 3,840 held keys have
effective owner zero; all 30,621 keys outside that roster have a nonzero
effective selected owner; there are no mismatches, overlaps, or zero-owner keys
outside the held roster. This is selected-product state only. It does not
establish source applicability, physical qualification, repair authority, or
acceptance.

## Proposed unresolved partitions

The retained held roster preserves the exact original key, owner and reason for
every held cell. The reasons partition 3,840 keys without overlap:

| Existing hold reason | Cells | Existing evidence |
| --- | ---: | --- |
| Territorial exclusion | 1,168 | `context-001/complete-context.json`, `negative-verification-001/verification.json`, and the original complete source/negative operands |
| Pre-represented-year municipal identity contradiction | 1,146 | `source-fitness-001/source-fitness-assessment.json`, `source-fitness-001/prior-hold-rows.json`, and the complete official XML records |
| Named merged-municipality footprint contradiction | 1,526 | The same source-fitness assessment and prior-hold roster, with the complete official merger records |

The two identity partitions total 2,672 and are disjoint from the 1,168
territorial exclusions. Within the identity group, the exact complete-owner
counts remain Maidla 45, Kaarma 1,101, and Lääne-Saare 1,526. The proposal
preserves these existing reasons and references their retained evidence rather
than reproducing source or geometry processing.

## Status and limits

The proposal status is `proposed_unresolved_unaccepted`: accepted repair cells
0; accepted exception cells 0; new repair and exception credit 0; selected
owner changes 0; package complete false. The previously source-qualified
30,621-cell subset remains the existing baseline and receives no additional
credit here.

No whole-polygon source-fitness clearance, represented-vintage/applicability
finding beyond the retained bounded identity evidence, contemporary legal
boundary, sovereignty, current physical classification, regional approval, or
publication authorization is asserted. The root-owned emitted-product and
serialized delivery gates remain separate. The observation’s `scientific_qualification`
field is false by design.

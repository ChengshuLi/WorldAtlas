# COD 930 held residual evidence proposal

**Status:** proposed documented-unresolved evidence only; `accepted: false`. All 930 residual keys remain held; this packet makes no owner changes, qualification decisions, accepted-repair claims, or credit claims. Explicit issue acceptance and downstream checks are still required.

## Package and denominator

Scope is issue #2453, package `gb-COD-ADM2--repair-evaluation`. The frozen original accounting has 3,905 cells in 2,323 intervals across 50 owners: 3,645 land and 260 inland-water cells. The retained native screening has 2,975 qualified/supported cells (2,780 land and 195 inland water) and 930 held cells (865 land and 65 inland water). The 2,975 are described here as qualified/supported outcomes, not as newly accepted repair credit. This proposal adds **zero accepted cells, zero repair credit, and zero owner changes**.

## Deterministic residual split

The full 930-key held ledger was expanded from its exact runs and sorted by `(owner_id, y, x)`. The split is indices [0,465) for A and [465,930) for B.

- A: 465 keys, from `(14440,128782,153513)` through `(14485,136937,144413)`; original class join gives 430 land and 35 inland-water cells.
- B: 465 keys, from `(14485,136938,144414)` through `(14616,127849,146318)`; the complement class counts are 435 land and 30 inland-water, preserving 865/65 for the whole held set. Partition B's JSON joins original_mask_class for all 465 keys; its exact source_class_join reports 435 land and 30 inland-water cells.

The shared-owner boundary at owner 14485 is separated by `(y,x)`; the partitions are disjoint and exhaustive.

## Evidence and source constraints

The held ledger is pinned at commit `81b808d4d73a225b6eacdae8b0554f9326b16270`, path `coordination/engineering/congo-original-repair-20261018/supported-inputs-001/held-original.json`, blob `d5d4d6850ffaade0a2ae8974b4307c7535e40c08`. That file is absent at current main `0d2b956d5cf2c9369ed787f2020f806171570e2d`; current main's retained supported-patch and source-evidence paths still match blobs `1f3255e8bcde0727854430ae89431accd7b45340` and `b70c4f7900ca0fa64476e162abe6dd4ad2bd37fa`.

Original tuple class/source candidates are joined through retained extraction blocks 031–034 (blob OIDs are recorded in both JSON files). `source-target-membership.json` is blob `8cd083399b9b4a8b343a272c5359541835902140`. The original accounting is blob `7303af8df856ae91d57a6caf86e96f7ad81ae62e`. Primary COD ADM2 source archive is pinned as `coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-COD-ADM2-000.bin.gz`, blob `dc4f2926dc0945eef1f35fa34c506a270b6239b2`; its retained metadata records 2019 representation and CC BY 3.0 IGO. This provenance does not itself establish current applicability or legal authority.

The source-evidence and whole-target physical artifacts are contextual evidence at target level. They do not establish per-key foreign contact, causal exclusion, physical classification, or adjudicated applicability. In A, 644 source-feature-index occurrences do not map through the retained primary-target membership file and remain numeric references. In B, source-target context is absent for wholly held owners 14568 and 14593. Physical flags/issues remain target-level. No geometry or contact reconstruction is claimed.

## Remaining gates and scope boundaries

A current-owner receipt is blocked/unavailable in this packet; no current-owner-zero claim is made. No conservation, emitted-consumer, or integration gate is claimed complete. All 930 remain held pending further exact evidence and explicit issue acceptance.

This COD-only packet does not decide or expand the separate #870/#878 water scopes or #1694 scope. It preserves the full original water denominator and recorded limits.

## Local artifact identities

- `partition-a.json`: 907,137 bytes; SHA-256 `cbab29ff875d9d5fdb79cefe1e8c84910f4a4f98c9b4f251d3c8ba6769ce7d4b`.
- `partition-b.json`: 441,665 bytes; SHA-256 `728335168e0003aacb1538b8c3d10799d984a2319d3ffe2a09c9cd274643f735`.


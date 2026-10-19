# Colombia ADM2 residual 830: held-key request and owner observation

Refs [issue #2441](https://github.com/ChengshuLi/WorldAtlas/issues/2441) and [accepted delivery PR #2459](https://github.com/ChengshuLi/WorldAtlas/pull/2459).

## Reconciliation

The original `gb-COL-ADM2--repair-evaluation` package contains 7,060 land cells in 3,575 original intervals across blocks 29–32 and 81 owners. The 6,230 supported/qualified outcomes previously delivered by PR #2459 remain preserved. This follow-up covers the exact remaining 830 held cells, split into disjoint partitions A (424) and B (406). It records **0 new accepted outcomes, 0 new repairs, and 0 owner changes**.

`partition-a.json` and `partition-b.json` retain the exact held tuples and their source/foreign-context joins. `per-key-unresolved-request.json` enumerates every one of the 830 keys and states the remaining per-key questions and next actions. It is a request for evidence and disposition, not evidence that any hold is resolved.

## Current selected-owner observation

`current-owner-observation-79c7802.json` is the actual output of `scripts/observe-selected-owners.mjs`, run once against current `main` commit `79c78026412f3d70117c0ba75317a68684d710eb` for the full 7,060-key package. It records the complete selector, sidecar and input pins, query digest, and owner rows. The result has base owner zero for all 7,060 keys; the 6,230 prior accepted owners match their recorded target; all 830 residual held keys remain effective-owner zero; there are no selected-product overlaps or mismatches.

`full-package-crosswalk-current-owner-79c7802.json` is a separate diagnostic key/interval join. It reconciles the full original scope to the prior accepted and held partitions and cites the owner receipt by exact path, size and SHA-256. The crosswalk is not the owner-observation command or a replacement for its receipt.

The owner observation reports product state only. It does not qualify DANE source applicability, represented vintage or license for a particular interval, establish per-key foreign-candidate contact or physical support, resolve authority/sovereignty, or create new acceptance. The original source and physical evidence limits remain in force; administrative polygons and target-level contacts do not prove sovereignty or exact per-cell contact.

## Next action

For each residual key, resolve the original source target and feature membership, source-family applicability and vintage, exact foreign-candidate contact, and the applicable pinned physical evidence under the original package contract. Keep each key held until that evidence supports a qualified additive repair or a documented exception. Preserve the 6,230 prior outcomes throughout. This packet changes no map ownership and grants no import, source-approval, or publication authority.

## Artifact pins

- Current owner receipt: 2,716,001 bytes; SHA-256 `7f8c29659b786d9c08baaf20e568a216e9672d91247b7b6c3347368be1ece6b3`.
- Full-package crosswalk with owner observation: 2,725,030 bytes; SHA-256 `0ad29cdb88bad56a324929c16a4a2b220c581b722ed6a9be33a4457cd43f05fd`.
- Partition A (424 keys): 1,404,031 bytes; SHA-256 `01f368d5ceabc4ad2b422b865046500460e57e1a50853cd67c9e6b1ac87823b6`.
- Partition B (406 keys): 1,167,535 bytes; SHA-256 `fe132aa15f8cef22ee61916e55451f762fded3dfdedba4cb17ae9bc9740311f5`.
- Explicit unresolved request (830 keys): 1,386,789 bytes; SHA-256 `b74c2c12e024327b32d7287684cdfa3ce46a95cf71954c2dde14edadf280c8f0`.

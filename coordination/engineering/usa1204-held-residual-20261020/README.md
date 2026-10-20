# USA #2358 held residual: evidence-only packet

This packet accounts for exactly the 1,204 held keys in the frozen `gb-USA-ADM2--repair-evaluation` package. It adds no repair, documented-exception, selected-owner, accepted-disposition or closure credit.

## Preserved denominator

The original denominator remains **107,131 cells / 46,575 intervals / 351 subjects**. PR #2371’s partial source/native handoff at [exact head `62dcd0b`](https://github.com/ChengshuLi/WorldAtlas/pull/2371/commits/62dcd0b393930e6c5bbef6904ce004d9c7ed4b9f) records **105,927 previously qualified cells** and 1,204 unresolved held keys. This packet leaves that PR and its existing outcome unchanged. Its independent partial review accepted the bounded source/native handoff with explicit limits ([review record](https://github.com/ChengshuLi/WorldAtlas/pull/2371#issuecomment-6229540770)); it did not approve selected delivery or close #2358.

The 1,204 held keys are partitioned exactly: **536 USA31 source-history**, **63 ownerless foreign-original contacts**, **1 Fairfax identity**, and **604 conservative unmeasured-physical-source** keys. The source/identity/foreign set has 600 keys and the physical hold has 604; their exact intersection is zero. The held classes remain 1,179 land and 25 inland water.

The roster contains one record per held key. Each key joins to exactly one row of the original 46,575-row interval table and retains that full original tuple and zero-based row index. The held keys touch **444 distinct original interval rows** (219 USA31, 56 foreign, 1 Fairfax, 168 physical); this is a count of original rows touched, not a replacement denominator.

## Evidence and limits

The roster and manifest pin the original interval table and the exact PR #2371 evidence blobs by immutable commit, Git blob ID, size and SHA-256. Original source and physical evidence are cited by their retained pins. No new national source data, geometry, boundary interpretation, or owner observation was produced.

- **USA31 (536):** retain the unresolved source-history defer and exact component IDs. These contacts are not findings that the cells belong elsewhere.
- **Foreign originals (63):** preserve the complete ownerless foreign-source contacts. Contact evidence is not a legal boundary adjudication.
- **Fairfax (1):** retain the distinct city/county identity hold under issue #976; no same-name merge is inferred.
- **Physical source (604):** preserve the conservative whole-owner hold. Invalid GSHHG source record 2380 has no measured relation for the Sagadahoc and Lincoln whole targets. This does not establish that every held key is physically wrong.

The source handoff preserves the consumed geoBoundaries USA ADM2 product’s 2018 represented-year claim and separate 2023 source-update/build dates, per-file Public Domain metadata, attribution, and derivative-language applicability caveat. Other source-vintage, boundary, Minnesota and reproduction obligations remain open. No present-day legal applicability or sovereignty conclusion is made.

A fresh USA-specific current-main selected-owner observation has not been asserted in this packet. The prior saved observation at 77609a1 is stale and excluded. Root owns the fresh selected-owner-zero/conservation and emitted-consumer checks. The 105,927 earlier qualified outcomes remain as previously reported; this packet adds zero accepted credit. The parent assigned this USA #2358 residual as a separate package scope from CAF and SSD; this packet does not include or verify a CAF/SSD cross-key comparator, so exact key-set disjointness is not asserted.

## Files

- `evidence-manifest.json`: denominator, disposition, evidence pins, checks and explicit limits.
- `held-key-roster.json`: all 1,204 held keys with exact original interval-row joins and per-category evidence pointers.

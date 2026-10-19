# Germany 374 residual evidence packets

Refs [issue #2410](https://github.com/ChengshuLi/WorldAtlas/issues/2410), [source/native handoff PR #2412](https://github.com/ChengshuLi/WorldAtlas/pull/2412), and [accepted selected delivery PR #2414](https://github.com/ChengshuLi/WorldAtlas/pull/2414).

## Reconciliation

The Germany original package has 27,555 original outcomes. Its existing accepted baseline is 27,181 outcomes; these evidence packets address the remaining 374 held outcomes. They do not change any disposition or add acceptance credit.

The three strata are 181 territorial exclusions, 99 unsupported-coverage keys, and 94 GF2 water-extension land-role keys. The literal coordinate keys in the three source packets are pairwise disjoint and contain 374 unique `(y, x)` coordinates in total.

## Packet contents

- [Territorial exclusions (181)](territorial-181/README.md): whole-target feature contacts and provenance rows. These contacts are not per-cell intersections and do not establish source currency, authority, sovereignty, or eligibility.
- [Coverage (99)](coverage-99/README.md): exact held tuples and target-level mapped-land support. Complete per-cell coverage remains unverified; all 99 remain held.
- [GF2 water-role (94)](water-role-94/README.md): exact land-class keys on administrative water-extension atoms. Atom-level water/land observations do not establish land ownership; all 94 remain held.

The packet JSON now binds every exact held key to its original land fragment, owner and source-atom membership, retained source-evidence rows, and any whole-target contact context. [The shared original/contact witness](shared/original-contact-witness.json) is a byte-verified 345,581-byte handoff artifact (SHA256 `810ec89ab4519428e86b4ebbc77ce170dd210f2437a410ca1ddd10b0e87687c8`). Historical pins identify source inputs; they do not state that the pinned commit is current main.

The complete-package literal selected-owner observation is recorded in [the observation receipt](literal-selected-owner-observation.json) (9,534,859 bytes; SHA256 `5c72e50271007f14aca411dc3f40f6204575cab281ce02c504965ec4fb2fae5c`). It queried all 27,555 original keys against main `4ee730a4754e7dde5ef299265126a7dd28cc10a6`: 27,181 have a nonzero effective selected owner and 374 have owner `0`. This is an owner-product observation only; it does not qualify sources or change any key's disposition.

## Limits and next action

The packets propose a documented-unresolved disposition for the exact 374 original land outcomes under the package contract. Each key retains a bounded unresolved question and links to its original source-set-preserving interval and owner context. This is distinct from positive repair qualification: all 374 native holds remain, repair and exception credit are zero, and no acceptance is recorded. The owner observation confirms those 374 keys still have selected owner `0`; the other 27,181 owners are recorded as product state, not new acceptance credit. Preserve the 181/99/94 strata, 27,181 previous original outcomes, and full 27,555-key / 7,499-interval / 82-owner / 100-atom contract. Independent exact-head review, durable delivery, and explicit root acceptance remain required before any accepted credit. Administrative boundaries and whole-target contacts do not establish per-key source applicability, authority, or sovereignty.

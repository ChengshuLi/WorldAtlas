# Germany 374 residual evidence packets

Refs [issue #2410](https://github.com/ChengshuLi/WorldAtlas/issues/2410), [source/native handoff PR #2412](https://github.com/ChengshuLi/WorldAtlas/pull/2412), and [accepted selected delivery PR #2414](https://github.com/ChengshuLi/WorldAtlas/pull/2414).

## Reconciliation

The Germany original package has 27,555 original outcomes. Its existing accepted baseline is 27,181 outcomes; these evidence packets address the remaining 374 held outcomes. They do not change any disposition or add acceptance credit.

The three strata are 181 territorial exclusions, 99 unsupported-coverage keys, and 94 GF2 water-extension land-role keys. The literal coordinate keys in the three source packets are pairwise disjoint and contain 374 unique `(y, x)` coordinates in total.

## Packet contents

- [Territorial exclusions (181)](territorial-181/README.md): whole-target feature contacts and provenance rows. These contacts are not per-cell intersections and do not establish source currency, authority, sovereignty, or eligibility.
- [Coverage (99)](coverage-99/README.md): exact held tuples and target-level mapped-land support. Complete per-cell coverage remains unverified; all 99 remain held.
- [GF2 water-role (94)](water-role-94/README.md): exact land-class keys on administrative water-extension atoms. Atom-level water/land observations do not establish land ownership; all 94 remain held.

The original JSON and README files are copied unchanged into their strata. Each JSON retains its own source refs, Git blob identities, hashes, and limits. Those historical pins identify the inputs used for each packet; they are not statements that the pinned commit is the current repository head.

## Limits and next action

This is an evidence-only assembly. No source or physical producer was rerun, and no held key is newly resolved. Administrative boundaries do not establish sovereignty or current authority. Any later disposition change requires evidence applicable to the exact key and its held reason, followed by independent review and the ordinary delivery gates. Until then, all 374 remain held and the Germany package remains incomplete.

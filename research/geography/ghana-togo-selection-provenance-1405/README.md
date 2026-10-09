# Ghana–Togo selection-rank erratum (#1553)

This additive packet corrects the eligible-component rank tuple reported during the #1405 selection audit. It preserves that original audit and all #1403 source, physical, and contact evidence. It does not change or approve geography.

## Reproduced selection

The immutable routing roster has 1,005 `land-source-fitness` rows across 711 fine families. All 1,005 have `dispatch_ready: false`; that field is a later source/readiness state, not a filter for this selection-rank audit. Each roster component joined one-to-one to the full native rank inventory of 95,173 components. The join also verified that native `actionable_batch_id` equals the roster's family ID, and each native rank axis is a complete unique total order.

For each eligible row, the reproducer formed the tuple `(source_locator_readiness, measured_impact, coordination_complexity)`. It selected each family's minimum tuple, using component ID to resolve within-family ties, then sorted the family minima and used family ID as a final deterministic tie-break. There were no tuple ties. Native positions are zero-based, as confirmed by the pinned rank producer's `enumerate` implementation; the family list position is one-based.

| Value | Original selection audit | Reproduced from pinned current rank records |
| --- | ---: | ---: |
| Eligible row tuple | `(2457, 94833, 52630)` | `(2457, 94832, 52630)` |
| Fine-family position | 30 of 711 | 30 of 711 |

The current native `measured_impact` position is **94,832**. The retained original audit's 94,833 is one position higher and is preserved as historical reporting; this packet found no retained historical rank vintage that authenticates 94,833 as an alternate current tuple. The selected family and its one-based position remain unchanged.

The separate `original_fine_family.best_rank` is `{source_locator_readiness: 619, measured_impact: 69149, coordination_complexity: 52146}`. The complete original family row from the d51 routing stream matches the original audit's broader `family_best_rank`. This broader family statistic is not the eligible-component tuple used to select family position 30.

## Preserved contact and source context

The pinned original family record retains all six physical components and the same four contact subjects: Ho Municipal and Ho West in Ghana, and Kloto and Agou in Togo. The pinned atlas registry records the Ghana contacts under Volta Region and the Togo contacts under Plateaux Region. Those are identity and recorded-parent lookups, not an independent adjudication of current administrative authority or boundary accuracy.

The original #1403 packet remains authoritative for its scoped source findings. It records one uniquely covering compatible Ghana contact and five partial or unresolved component relationships; source-date claims of 2019 for Ghana and 2017 for Togo; GHA CC BY 4.0 and TGO CC BY-SA 2.0 metadata; and an unresolved question about the Togo source-vintage terms. The physical surface is unverified, physical authority and cause are unapproved/unknown, boundary length is unknown, and the recorded 48,917.06359418356 m² fragment sum is inherited measurement evidence rather than a new measurement or proof of dry land. This erratum did not fetch or re-adjudicate those sources, legal terms, boundaries, or physical claims.

## Reproduction and controls

`rank_reproduction.py` reads exact Git blobs under the input, routing, and native-code commits declared in `evidence-quality.json`. It authenticates compressed and decoded bytes, reserves the complete operation before decompression, joins the actual eligibility rows to native component records, and checks the retained complete family record and contact IDs. The intermediate (`rank-v3-*`) output vintages are preserved. The final (`rank-v4-*`) output vintages are byte-identical and record the exact source hashes, tuple, family position, contact feature IDs and registry parents, complete family-record location/hash, helper and ranker hashes, and explicit limits.

The first two runs (`rank-v1-one` and `rank-v1-two`) are retained as superseded evidence: premerge ancestry correctly rejected their reported non-ancestor execution commit. The `rank-v2-*` runs then pinned the identical whole ranker and helper bytes at ancestor `cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1`, while retaining the report's `c9be...` execution-commit statement as an explicit lineage limit. The `rank-v3-*` runs repeat the same computation and expose the complete native component count directly for manifest metric binding. The exact-head reviewer caught that v3 documentation still invoked the PR checkout as the helper baseline; that command failed on PR head. The final `rank-v4-*` runs fix execution by loading helper bytes from the explicitly pinned ancestor commit `7110932cd2bcab7c2e03cadcda8eb02aa118eb9b`, authenticating the working helper against those bytes, and running with `--repo .` from the PR checkout. Matching file hashes establish source-byte identity; they do not prove the native report commit ancestry.

The adverse controls reject a missing native rank, duplicate native component, and duplicate eligibility component. A coherent swap of impact positions 94,832 and 94,833 preserves the total-order permutation but changes the selected tuple; its changed decoded bytes fail the immutable input hash. The probes use bounded in-memory copies and leave the source records and completed runs unchanged.

Executed from the repository root with bundled Python 3.12.14:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/ghana-togo-selection-provenance-1405/rank_reproduction.py --repo . --vintage rank-v4-one
PYTHONDONTWRITEBYTECODE=1 /Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/ghana-togo-selection-provenance-1405/rank_reproduction.py --repo . --vintage rank-v4-two
```

Each run name is exclusively reserved and must not be reused. For a later replay, choose two new unused vintage names. Exact source pins and decoded-file digests are in the evidence manifest and generated run records. The method is a bounded reproduction of retained routing arithmetic; it does not establish source authority, legal reuse, source completeness, territorial meaning, or geographic correctness. No import, publication, deployment, geometry or hierarchy edit, or regional approval occurred.

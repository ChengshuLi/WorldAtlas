# Norway ADM2 source-fit / no-loss evidence — issue #1492

This is a bounded source-only report for the issue’s 15 corrected component IDs. It keeps all 400 members and all 36 positive-length ADM2 neighbors in the scope artifacts. It does not alter map geometry, hierarchy, database contents, or publisher outputs. It makes no physical, political, historical, ownership, or water/ice classification.

## Result

The selected 15 component geometries were recovered from the manifest-pinned original component delivery and match the prior source-comparison geometry hashes. Under the pinned simplified geoBoundaries products, each has one positive-area ADM2 intersection with its unique recorded-compatible ADM2 subject; each is covered by that subject and by the complete ADM2 source union. No selected component has a second positive-area source overlap.

The current Atlas target is the matching ADM2 member in pinned `data/geography/part-17.json`; the candidate `C` is the selected physical component. The issue’s exact strict no-loss expression is evaluated as `T.difference(T.union(C)).is_empty`, with no tolerance, snap, buffer, normalization, or repair.

- 13/15 candidate components are covered by the recorded Nordland ADM1 parent. The two Rødøy components fail that exact parent predicate.
- 8/15 strict no-loss predicates pass; 7/15 retain nonempty exact residuals. The earlier issue text reported 7/15 passes, so this exact rerun differs by one component. The per-component geometries and predicates are preserved; the one-case discrepancy remains explicit.
- All 15 candidate components add area beyond their current Atlas ADM2 target.
- The prior component/source ledger has 31 bounding-box candidates, of which 16 have empty intersections. Those empty rows are not contacts. Its 15 nonempty contact rows exactly match the recomputed 15 positive-area contacts in the byte-identical simplified product; both vintages report zero zero-area contacts.
- The complete measured source-fit/no-loss conjunction passes 7/15. These cases pass unique source-subject coverage, current target identity, parent coverage, strict no-loss, current contact reconciliation, no extra positive-area overlap, and area addition. This remains a source-only proposal, not geographic approval.
- The physical delivery manifest declares 95,173 components, while the 11 byte-verified delivery shards contain 95,174 unique IDs. All selected IDs are present exactly once; the packet does not claim whole-delivery count closure.

| Component ID suffix | Recorded ADM2 target suffix | Parent | Strict no-loss | Contacts | Source-only gate |
|---|---|---|---|---|---|
| `9c7085f1` | `B2671252892867` | pass | fail | match | fail |
| `bc085efb` | `B63422016976384` | fail | fail | match | fail |
| `16f28f2b` | `B44883610080028` | pass | pass | match | pass |
| `d17f1e5c` | `B40270143357623` | pass | fail | match | fail |
| `a7ac3384` | `B3163335119560` | pass | pass | match | pass |
| `7704df35` | `B55953165899475` | pass | pass | match | pass |
| `ceca14a9` | `B75314465532393` | pass | pass | match | pass |
| `3a41c5ce` | `B44883610080028` | pass | fail | match | fail |
| `167d4803` | `B80996435697818` | pass | pass | match | pass |
| `a9b4253a` | `B95964377762384` | pass | pass | match | pass |
| `2e63ae94` | `B17604167467724` | pass | fail | match | fail |
| `e31b7a9f` | `B99132950125054` | pass | fail | match | fail |
| `fe062904` | `B63422016976384` | fail | pass | match | fail |
| `cb11db40` | `B90944773523196` | pass | pass | match | pass |
| `33659508` | `B2671252892867` | pass | fail | match | fail |

The seven passing component IDs are `1f5426f5180aa4f5b7fd9991b5ae4816d56cb642c31d0937a4977da516f28f2b`, `764b247eb21da38adac0b925bededbbb4dccaefa4b52b16976f20543a7ac3384`, `7bad7bdf9b1203fe6c676eb2efde10b09ce394ad7d6d554eb557709d7704df35`, `8fb9f3f0d7df1c96ac452792fd4a9dbc7a45a576437550dd5b198424ceca14a9`, `a92cac9c4c3d3a91286eca0e4890becd63441647c7fe7c4cdcc5e1aa167d4803`, `b6ba064b4525f0c75459a8d1aa05c25e9740cc46b9964f96983d61d6a9b4253a`, and the corrected Vevelstad ID `eb2b6c25d1a2b8ead2bcb67f7e0423b5f1cc5609ac3f600bb98cd6d5cb11db40`. The full component and neighbor rosters and all exact geometries are in the overlay JSON.

The negative controls independently start from an affirmative gate fixture and reject wrong source identity, edition, target, or parent; missing family or neighbor IDs; removed contact; changed source bytes; forced target loss; and forced additional positive-area overlap. The overlay computation was run twice with equal canonical result hashes. The evidence manifest binds each numeric ledger value to a generated metric-values output and binds positive/negative controls to separate result outputs; all are derived from the retained exact overlay and do not add independent geographic evidence.

The per-component geometry, exact residuals, full source contacts, historical bbox rows, measured gate outcome, and all 10 adverse-control outcomes are in `vintages/exact-overlay-acceptance-20261008/overlay-v1.json`. The byte checker reports `limited`: bytes and subject bindings verify, while project delivery, current Atlas target, and historical contact ledger remain project-internal evidence rather than independent external truth.

## Inputs and method

- Current official geoBoundaries NOR ADM2, represented year 2013, 431 features, CC BY 4.0; API response and simplified GeoJSON bytes are retained and hash-bound.
- Current official geoBoundaries NOR ADM1, represented year 2022, 11 features, CC BY 4.0; API response and simplified GeoJSON bytes are retained and hash-bound.
- The exact current Atlas target members and their recorded source/parent metadata are from baseline commit `088ab05aeb16ddfa8f0c43e596533f3f11d5fcec`.
- The issue’s evidence contract baseline-pins the pre-existing simplified ADM2 product. The simplified ADM1 product was newly captured here, so its bytes remain bound as a retained source rather than being misrepresented as a baseline-tree file; the exact issue-body contract correction and readback are preserved in `vintages/evidence-pin-contract-correction-20261008/`.
- Parent linkage uses the issue’s recorded `framework:province:nordland:03c9b4c95d9e` and the unique ADM1 product feature named `Nordland`. The ADM2 simplified product has no parent property, so the linkage basis is explicitly recorded.
- Runtime: Python 3.12.14, Shapely 2.1.2, GEOS 3.13.1. The overlay records the exact installed Shapely distribution and Python executable hashes.
- Complete phase input plus output reserve: 104,428,543 bytes of a 268,435,456-byte cap. Maximum process RSS was 205,635,584 bytes; free storage at run admission was 15,496,110,080 bytes; host memory was 8 GiB. Local workspace admission passed before the run.

The stage `physical-rows-*` artifacts are a retained failed discovery attempt: the 71 physical-comparison output shards contain diagnostic relations but no component geometries. The actual geometries were then read from the original candidate-delivery payloads. Exploratory overlay vintages are retained; `exact-overlay-acceptance-20261008/overlay-v1.json` is the final result.

## Reproduction

From the repository root, with the bundled Python 3.12 runtime:

```sh
/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12 research/geography/norway-adm2-source-fit-1492/capture_component_geometries.py
/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12 research/geography/norway-adm2-source-fit-1492/run_bounded_overlay.py
```

Each run uses a fresh named vintage and is intentionally non-overwriting. The first command reserves its entire output and phase before scanning the complete 11-shard source delivery. The second reserves all inputs, the installed numerical runtime, and the complete output inventory before importing Shapely or decoding geometry.

## Limits

The source comparisons do not establish complete ECO_ID0 geometry, registration accuracy, or Atlas feature-generation lineage. The geoBoundaries products and exact overlays do not establish physical land/water, correct administrative authority, historical boundaries, rights, ownership, or cause. The one-case strict no-loss count difference from the earlier issue text remains unresolved. No geometry change is proposed or approved.

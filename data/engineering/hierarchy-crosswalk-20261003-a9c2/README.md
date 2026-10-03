# Release 5 hierarchy-correction crosswalk

Partial preparation for [issue 6](https://github.com/ChengshuLi/WorldAtlas/issues/6). Worker `engineering-hierarchy-crosswalk-a9c25e14-20261003` holds confirmed claim `f176ea85-85a1-41c0-a8db-d0a23aec7416`; GitHub is authoritative for current reservations and progress. The immutable baseline is `dbbf8f736699940ec98efa83972f1784a83cb3a0`.

This consumes the frozen `data/reference-hierarchy-corrections/` proposal and source proof without changing their bytes or rerunning the older 49,589-location preparation. It resolves the current append-only manifest pointer to published reference release 5, verifies the actual 49,625-location / 5,734-group inventory, and compares every immediately affected source territory with the original member/geometry proof. Broader old ancestor proofs differ after intervening releases; they remain preserved in the original receipt. The new receipt computes current-to-candidate ancestor proofs rather than silently repinning an old audit.

The separate candidate renames the two sole-member area reference labels to Monaco and Luxembourg, moves Hancock to the retained 54-member West Virginia province, and retains the retired parent in the before archive with an explicit same-tier merge and no historical transfer. Exactly three location chains change. Candidate counts are 49,625 locations, 5,137 provinces, 480 areas, 81 regions, 29 subcontinents and six continents. This is preparation, **not installed or published geography**, and does not approve any regional interior.

The actual candidate footprint hash is `2ac42eeb9fef8af923a0d4c4e55af49ca0a103de891ffbfb2c1181ad75950286`, matching published release 5. The established JavaScript footprint-hash implementation checks the actual candidate. Every unchanged geography part is copied byte-for-byte; the Hancock part changes one parent string without parsing/reserializing geometry, preserving numeric lexemes. Every canonical ownership rows/runs part is individually read and hashed against its immutable pin; none is written. Full six-tier chains and containing South Atlantic membership are checked before and after.

`baseline-request.json` contains whole-file pins for all geometry parts, hierarchy, manifest predecessor/extension, gate, source proof/proposal, grid ownership parts and shared helpers. `before-hierarchy.json.gz` preserves the exact original hierarchy file bytes. The rebased migration receipt retains all current original unit records, complete affected descendant chains and ancestor member/footprint proofs. `crosswalk-audit.json.gz` records the actual footprint digest, geometry-entry ledger digest, candidate part hashes and every ownership-part pin. Whole-file compressed and expanded hashes are listed in the evidence manifest; they are distinct from entry hashes.

## Reproduce

Use Python 3 and Node 24 from a checkout containing the baseline commit. No source download, GIS dependency, live API, import or deployment is needed:

```sh
python scripts/rebase-reference-hierarchy.py --request data/engineering/hierarchy-crosswalk-20261003-a9c2/baseline-request.json --output /tmp/new-hierarchy-crosswalk-run
python test/reference-hierarchy-rebase.py
node scripts/evidence-quality.mjs coordination/engineering/hierarchy-crosswalk-20261003-a9c2/evidence-quality.json
```

The output directory must be new and cannot be beneath active `data/`. Compare all three compressed receipt files with the retained outputs; both executed preparation runs matched byte-for-byte. The candidate's full geography directory remains untracked and can be reconstructed from Git. Do not publish it until coherent installation and all matching release/grid/evidence gates are reviewed.

Eight synthetic controls cover complete chains, duplicate/missing identities, skipped/cyclic parents, exact reference-only merge, unchanged originals/geometry, stale before records, wrong endpoints, historical transfer and non-parent mutation. An initial test fixture accidentally used a valid adjacent-tier parent; its failed run remains separate, and the corrected negative fixture passed. The existing release metadata-relationship validator also accepted the complete actual current baseline and rebased merge receipt.

## Source and release limits

The frozen source proof preserves original successful inspection receipts, official labels, all 55 West Virginia registry rows and proposal diagnostics. This job reuses them; it does not claim new primary-source retrieval or new source-license verification. Original inspection dates absent from those receipts remain unknown. The hashes of the original Monaco page, GISCO label file and Census ZIP are provenance from those frozen inspections, not newly verified complete retained primary files. Reference labels and same-source county consolidation do not establish historical administration, legal certification or ideal atlas granularity.

Before issue 6 can close, a fresh second-part installation must update matching hierarchy/release/grid-parent lookup, derived validation and prepared-evidence proof chains, preserve source/claim/identity archives and all ownership bytes, and verify matching served map/inspector/parent boundaries through the designated publisher. Macro and regional certificate/import gates must be explicitly revalidated; no complete regional branches currently exist. The publication number must be checked afresh rather than reserving release 6 here. If the remaining scope exceeds the issue's remaining PR budget, record bounded follow-ups for coordinator review instead of expanding this candidate PR.

The matching release-5 publication status comes from the retained gate and committed manifest. This preparation does not perform a fresh private live API readback; the publisher must check the actual latest served release again before any installation or staging.

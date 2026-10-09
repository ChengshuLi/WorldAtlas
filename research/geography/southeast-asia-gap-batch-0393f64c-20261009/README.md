# Southeast Asia operational gap batch 0393f64c

Issue #1641 owns the complete `gap-operational-batch:0393f64c9f8549bcfca1ace9` scope: 318 exact physical-component IDs, 122 family locators, and the 30 already-prioritized source cases. This packet reconciles the full batch and deeply binds the existing 30 priority cases to the source product Atlas consumed, the whole current target feature, and the already-retained comparison row.

## Results

- The exact 318-ID roster maps to all 122 retained family locators. The refreshed complete membership outputs contain every ID exactly once. A fresh read of all nine open `status:claimed` issues and their canonical claim comments found no exact subject overlap outside this issue.
- All 318 remain `unresolved`: 314 are in pipeline state `evidence-ready`, and 4 are `awaiting-evidence`. `repair_ready`, `implemented`, `fully_integrated`, and `delivered` are each zero.
- The 30 priority cases each retain the full source feature, full target feature, matching canonical feature and geometry hashes, and the prior comparison result row. Source bytes match the original Atlas administrative registry's raw whole-product SHA values. Seven products and four existing comparison packets cover these cases.
- The source features are from Atlas's simplified geoBoundaries inputs, selected by the pinned original `scripts/administrative.py` recipe. Their hashes are kept distinct from historical stable-subject geometry hashes; simplification can change coordinates.
- Existing overlays are cited from their original packets and were not rerun. No core geography, class, water/ice status, cause, legal authority, repair, integration, or delivery decision was changed.

## Artifacts

- `evidence-quality.json` binds all 30 issue subjects, all 63 issue pins, the complete 318-ID state ledger, and the exact captured source products. Run the command there to verify bytes and identity bindings. `inputs/live-claim-scope-readback.json` preserves the contemporaneous issue/claim comparison.
- `vintages/roster-reconcile-001/component-state.json` contains one detailed row per component, its family locators, exact current membership record, unresolved facts, and next action.
- `vintages/roster-reconcile-001/summary.json` records the whole-batch counts and seven full membership artifacts.
- `vintages/priority-source-target-001/priority-source-target.json` contains the 30 complete source/target/comparison bindings, catalog rows, exact product and packet references, and limitations.
- `inputs/source-products/` contains byte-exact copies of the seven original consumed simplified products. `inputs/provenance/` preserves the exact historical administrative registry and recipe bytes used to authenticate product selection and SHA values.

## Limits and next work

The administrative inputs are reference geometry, not proof of present-day land/water, rightful territory, or repair authority. The source date and accepted physical class remain unresolved; water/ice classification and causal diagnosis were not established. The packet does not remeasure overlays, propose a source exception, alter Atlas geometry, or claim the 318 cases are repaired. Continue with source-backed physical-class/date and cause/authority evidence for the exact IDs; route any actual geometry change to the separate authorized engineering/publication workflow.

# Southern Africa #411 crosswalk validation erratum

Issue #1279 is a bounded validator correction for the 223 frozen #411 subjects. It does not redo country source adjudication, change any row disposition, repair geometry, or approve regional geography. The original #411 packet, #1047 merge, source files and follow-up ownership remain intact.

## Reproduced findings

The retained #411 crosswalk and assessment pipeline was run twice from this issue branch using the pinned source collections and the six recorded baseline files. The branch's Atlas parts, hierarchy, index and macro membership files have the same whole-file bytes at the frozen #411 baseline (`bd2c2aeed9fcaa0b209a4bec1fe18b7129bb7f60`) and the immutable #1047 merge (`762d7b5a568ca845d85a98a4d188678c126a5d58`).

Both fresh crosswalk outputs are byte-identical to the original `scope-reproduction.json` (SHA-256 `70a1a813a415e6159d703a81be2e54af62fb7d638e5bd92f13449a970cc55d15`). Both generated assessment outputs are byte-identical to the original `row-assessments.json` (SHA-256 `9c08840cc0dd52d44f0efe5f03e67b4015607268d666b64efa4c300f1b859bb3`). The exact 223 subjects comprise 157 Angola, 38 Mozambique and 28 Malawi rows. Preserved dispositions remain 0 justified, 1 correction-needed (`Cidade De Maputo`) and 222 insufficient-evidence.

The original validator checks its reported crosswalk counts and its assessment rows, but it does not derive the actual `scope-reproduction.rows` roster or join each assessment to its crosswalk row. This erratum's validator derives actual rows and unique IDs, requires exact equality with the frozen issue roster, resolves each ID against the retained native source feature and pinned Atlas feature, verifies the actual parent ID against the pinned hierarchy, and checks corresponding assessment IDs, names, vintages, source IDs and parent IDs. It binds the assessment's input digest to the complete consumed crosswalk bytes.

The directed controls retain the actual mutated inputs and outputs. The missing-row control removes one of 223 crosswalk rows, leaves self-reported counts unchanged, and recomputes the assessment's crosswalk hash to match the changed input. An input-locator adapter preserves the original validator's predicates while directing it to those exact control files: the original validator accepts the 222-row crosswalk and emits a success receipt reporting 223, while the superseding validator rejects it before writing a receipt. The new validator also rejects duplicate, foreign replacement, extra-row, parent mismatch, source-native-ID mismatch, and assessment-parent mismatch controls. The control result file records exact input hashes and diagnostics.

## Source and geographic limits

The actual native feature matches are derived from the retained geoBoundaries Angola ADM2 2018, Mozambique ADM2 2019 and Malawi ADM2 2020 collections. Their existing packet records pinned upstream revisions, complete-file hashes, retrieval dates and CC BY 3.0 IGO attribution terms. These are historical/reference source collections. They support the recorded source identity and row joins; they do not establish current administrative identity, legal boundaries, completeness or accuracy.

All source and territory uncertainty from the original packet remains open. In particular, the official follow-ups for current Angola boundaries (#1046), Malawi 28/32 ADM2 semantics (#1045), the complete Mozambique source/parent roster (#1042), the four out-of-scope Cabinda units (#896), and the disjoint Mozambique features (#412) remain separate. Original #411's official-source retrieval and reuse gaps, city-tier and parent ambiguity, neighboring granularity, topology and boundary uncertainty are preserved. No finding here certifies those matters.

## Reproduction

From the repository root on Node 24, after `node scripts/local-workspace.mjs check` succeeds:

```sh
node data/regional-review/regional-review-029dcbc646de003d/reproduce-scope.mjs --output data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum/runs/2026-10-07/run-1/scope-reproduction.json
node data/regional-review/regional-review-029dcbc646de003d/reproduce-scope.mjs --output data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum/runs/2026-10-07/run-2/scope-reproduction.json
node data/regional-review/regional-review-029dcbc646de003d/build-row-assessments.mjs --output data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum/runs/2026-10-07/run-1/row-assessments.json
node data/regional-review/regional-review-029dcbc646de003d/build-row-assessments.mjs --output data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum/runs/2026-10-07/run-2/row-assessments.json
node data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum/verify-crosswalk.mjs --crosswalk data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum/runs/2026-10-07/run-1/scope-reproduction.json --assessments data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum/runs/2026-10-07/run-1/row-assessments.json --output data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum/runs/2026-10-07/run-1/validation.json
node data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum/verify-crosswalk.mjs --crosswalk data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum/runs/2026-10-07/run-2/scope-reproduction.json --assessments data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum/runs/2026-10-07/run-2/row-assessments.json --output data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum/runs/2026-10-07/run-2/validation.json
node data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum/run-controls.mjs
node data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum/write-validation-receipts.mjs
```

The controls and validation receipts in this packet are the actual results of those executions. Passing them validates the exact-scope and row-correlation checks only; it does not change any geographic disposition or authorize a correction, import, publication or deployment.

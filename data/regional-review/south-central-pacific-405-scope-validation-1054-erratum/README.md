# Reproduce Pacific #405 frozen-scope validation

This is an evidence-validation erratum for issue #1281. It preserves the original #405 evidence and adds a strict frozen-roster gate plus an exact replay record. It does not decide geographic correctness.

## Reproduction

From the repository root, run with Python 3.12 and the pinned geometry dependencies available:

```sh
python3 data/regional-review/south-central-pacific-405-scope-validation-1054-erratum/reproduce.py
python3 data/regional-review/south-central-pacific-405-scope-validation-1054-erratum/scope-validator.py data/regional-review/south-central-pacific-405-scope-validation-1054-erratum/inputs/scope.json data/regional-review/south-central-pacific-405-scope-validation-1054-erratum/pinned-inputs
node scripts/evidence-quality.mjs data/regional-review/south-central-pacific-405-scope-validation-1054-erratum/evidence-quality.json
```

The replay obtains the complete original packet from merge `249e396178cfc160fd547ec4487c5d94832fc9af`, obtains all 16 baseline descriptors and both scientific helper modules from commit `a57085b7a5cfdbe3c1e0e4b0cd2e07c6240899fc`, and creates disposable temporary overlays. It preserves only the three result JSON files from each valid run under `runs/run-1/` and `runs/run-2/`. Both outputs are byte-identical to the originals and to each other. The recorded result is `reproduction-results.json`.

`scope-validator.py` first checks the exact immutable scope hash and raw 23-member list; it never coerces the roster to a set before validating length and uniqueness. It then verifies the 23 location-to-parent rows, 23 parent assessment rows, 10 area rows and their declared membership counts against the pinned original assessment tables. `controls/` retains executed duplicate, duplicate-replacement, missing, foreign, count and crosswalk corruption fixtures. The old verifier's reproduced acceptance of a 24-entry list with 23 unique IDs confirms the original defect.

## Scope and limits

The output reports source roles and unresolved neighboring granularity in `RESEARCH.md` and `SOURCES.md`. Full official pages that were not retained are identified by URL, retrieval time and response hash in `external-source-fingerprints.json`; restore them by GET from the recorded final URL. Original source objects lawfully retained for the source comparison are copied into `sources/` with metadata. Original source assessment/report files remain unchanged at their original Git commit.

This is not proof that the 23 source records are territorially correct or complete. It does not certify boundary meaning, current extent, island/shoreline completeness, source-policy eligibility or hierarchy. Existing follow-ups retain those questions. No production geography, import, deployment or release was changed.

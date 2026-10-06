# Southern South America source-to-Atlas crosswalk validation — issue #1111

**Evidence vintage:** current main `27be77596f23304de6a720735538427e6d23e242`; issue snapshot retrieved 2026-10-06. **Scope:** additive validation of the existing #446 / PR #922 Paraguay crosswalk and its retained row/parent ledgers. This packet does not edit or supersede that packet and does not change geography.

## Exact subjects and inputs

`source/issue-1111-api-2026-10-06.json` preserves the original issue contract and its 263 exact evidence subjects. The validator requires issue number 1111 and the exact issue-body SHA-256 `fc1cc2acd03e2882be490d8786b1ce0283498b808737875f2d6dfc8166565051`, so a changed snapshot cannot silently redefine this packet's scope. The validator reads only immutable Git blobs at the pinned main commit. Its `evidence-quality.json` binds the seven issue pins to their actual full files and maps each subject ID to its actual world-index containing part. The shared immutable helper scans all 36 part files for missing or duplicate identities; only the four actual containing parts are recorded in `baseline.subject_files`.

The #922 packet index contains 19 ordinary files (excluding itself). The validator checks its exact in-packet file roster, each indexed file's actual byte length and whole-file SHA-256, and the self-exclusion rule. It also follows the original `baseline-files.json` to the earlier 702a commit and verifies all nine historical source/input blobs without relabeling that old baseline as current.

## What is checked

The source roster is reconstructed from 241 native Paraguay ADM2 IDs and six `source_member_ids` from two Atlas aggregates. Every one of the 247 rows must map exactly once to the baseline target, target name, and mapping type. Native source names must equal the corresponding feature name; aggregate member names must be present in the aggregate's pinned `search_aliases` and unchanged from the pinned #446 row. All source levels must remain ADM2. The 243 distinct target IDs must match the issue's exact union of 215 scoped units and the 243 Paraguay target IDs.

The 215 unit-review IDs must match the pinned #446 scope exactly, without duplicates, and each row's name and parent ID must agree with its baseline feature. The 32 parent rows must match the exact issue parent roster; for every parent, its recorded child IDs and child count must equal the checked unit rows. Numeric reproduction results retained by #446 are recalculated from the checked crosswalk, review rows, baseline features, and retained Uruguay comparison inputs before comparison.

Twelve adversarial controls change a target ID, target name, mapping type, source name or level, duplicate/omit/foreign a source row, remove an index descriptor, duplicate a unit ID, or alter a parent's child inventory. The parent-table fixture also receives a recomputed packet-index byte count and SHA-256 before it is rejected. The crosswalk/index and unit/index mutations update candidate byte counts and SHA-256 descriptors consistently first. Packet byte/inventory verification accepts the deliberately rehashed wrong-target fixture, then the row-to-feature validator rejects its incorrect Paraguay ID-to-target mapping. This demonstrates that the semantic gate is independent of the candidate packet index hash.

## Source role and limits

The prior source register identifies the Paraguay input as geoBoundaries gbOpen PRY ADM2, vintage 2012, 247 features, licensed CC BY 4.0 in its pinned metadata. Its exact original bytes are 45,589,273 bytes, larger than the repository's 32 MiB evidence-file limit, and are not retained here. The prior packet records the exact URL and whole-file SHA-256 (`d42bd1f910070bf805e32dc46708230c91f58902a3c8792eda60928b22362858`) plus a restoration command. This work does not fetch, redistribute, or claim to reproduce that geometry. It validates the row mapping against the Atlas IDs/aggregate-member metadata pinned at current main and the preserved crosswalk row names.

Therefore, a pass establishes agreement with retained baseline identity and row evidence only. It does not establish source geometry correctness, Paraguayan statutory or current administrative boundaries, territorial completeness, the correctness of the old crosswalk's aggregate-member source-name pairing against the omitted original source file, Uruguay boundary accuracy, or regional approval. The #922 packet's open findings and the existing source-retention limits remain open.

## Reproduce

From repository root, with Python 3.12, run:

```sh
python3 data/regional-review/southern-south-america-crosswalk-validation-20261006/validate_crosswalk.py
node scripts/evidence-quality.mjs data/regional-review/southern-south-america-crosswalk-validation-20261006/evidence-quality.json .
```

The first command checks the original candidate packet, verifies the baseline-derived map and numeric results, and writes `expected-crosswalk-map.json`, `verification-results.json`, and `adversarial-controls.json` only inside this owned directory. Run it twice and compare the whole-file SHA-256 of those three outputs; both runs must match. No dependency installation is needed. The second command validates the manifest's pins, source limits, exact subjects, outputs, metrics and summaries. Neither check certifies geography or legal boundaries.

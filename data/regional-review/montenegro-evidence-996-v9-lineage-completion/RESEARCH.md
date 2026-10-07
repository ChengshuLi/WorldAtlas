# Montenegro #1235 v9 lineage completion

Retrieved 2026-10-07 UTC through the GitHub API and reproduced from the accepted #1214 merge commit `d401d1040c698d7273fda37c6449447548052083`. This is an additive metadata-lineage packet for the exact 23 subjects in the #1235 work contract. It neither changes nor endorses any geometry, area value, official source, legal territory, hierarchy, or earlier audit conclusion. The original #996, #1179, and #1214 packets remain unchanged.

## Result

The pinned #1214 selector preserved 18 earlier superseded run rows, selected the two retained `anchored-v10` runs as authoritative, and failed to classify the two retained `anchored-v9` run directories. The v9 control was already identified as superseded. `lineage-completion.json` preserves the 18 rows byte-for-byte as parsed values, adds one reasoned superseded row for each v9 member, and retains the v10 pair/control as authoritative. It records the exact v9 run output, control, and report-declared input references. The report-declared source paths are reproduced as references; the #1235 contract does not pin their original source-file bytes, so this packet does not claim to reauthenticate them.

The pinned #1214 run-one/run-two `result.json` files are byte-identical and each contains the same incomplete 18-row selector, with no v9 member. The immutable merge tree contains 22 retained run directories: 18 earlier runs through anchored-v8, two anchored-v9 runs, and two anchored-v10 runs. The roster classifies each directory exactly once: 20 superseded and two authoritative. All four pinned v9/v10 comparison outputs remain byte-identical at the accepted hash `8b5acd06c9d269979287277d498e6e9405543d46a681149a327062abe63f782b`. The final two executions produce byte-identical complete reports (their exact SHA-256 is recorded in `lineage-control.json`). Seven negative controls reject each missing v9 member, duplicate assignment, fabricated run, active/superseded overlap, version/control mismatch, and the old incomplete 18-row selector. Earlier harness outputs are retained as diagnostic history; the authoritative final controls and outputs are under `runs/2026-10-07/final-v4/`.

## Subject and source meaning

The exact issue roster contains 23 retained Atlas feature IDs. At the pinned merge, each feature carries source metadata `gb:MNE:ADM1`, role `Municipality`, reference year `2017`, and a declared ODbL 1.0 license. Each has a distinct retained Atlas `province`-level parent identity with `child_count: 1`, `framework_status: retained-reference`, and an open boundary review. The full names, IDs, and parent IDs are recorded in `lineage-completion.json`; the runner independently matched all 23 IDs exactly once in pinned `data/geography/part-15.json` and checked their parent metadata in pinned `data/hierarchy.json`.

These are identity and lineage attributes, not authoritative territorial definitions. The 2017 metadata does not establish an exact capture date or effective legal date. The source inventory inherited from the prior packet describes the comparison geometries as OpenStreetMap/Wambacher-derived geoBoundaries data and states ODbL 1.0 with attribution and share-alike obligations; this work does not redistribute that geometry or independently establish legal validity, license scope, or positional accuracy.

The earlier source review reports a 23-unit 2017 statistical area roster, a 24-unit post-Tuzi 2021 roster, and 25 current local-government entries in a 2025 catalog. Those counts concern different vintages and source roles; none proves current boundary completeness. The 2017 area sum has an unexplained 157 km² excess over the reported national total. The 2021 publication describes Tuzi's area as temporary pending demarcation. The retained record reports a 2026 Tuzi/Podgorica arbitration referral without a verified outcome. These are inherited findings, not newly retrieved facts or boundary measurements.

No settlement-level parent source, current complete legal municipal layer, comparable official historical vector, island/coast/water convention, or adequate adjacent-country municipal comparison is established by this lineage task. Tuzi/Podgorica and Podgorica/Zeta, current national completeness, legal parentage, effective boundaries, neighboring granularity, and source reuse rights for official records remain unresolved. No change to the source or hierarchy is proposed here. The original #1013 scientific review remains Incomplete; this packet does not certify a region or authorize geography approval, import, publication, deployment, or production writes.

## Inputs and reproduction

The issue contract and API response receipt are in `issue-scope-snapshot.json`. `evidence-quality.json` binds every one of the 28 exact issue pins to whole-file bytes at the common #1214 merge baseline; the executed runner independently verifies those hashes before producing output. The report also records the exact subject inventory and all 23 read-only parent contexts. Historical outputs remain referenced by immutable Git commit and have not been rewritten.

From the repository root, with Python 3 standard library and Git:

```sh
python3 data/regional-review/montenegro-evidence-996-v9-lineage-completion/reproduce.py run --output-dir data/regional-review/montenegro-evidence-996-v9-lineage-completion/runs/2026-10-07/final-v4/run-1
python3 data/regional-review/montenegro-evidence-996-v9-lineage-completion/reproduce.py run --output-dir data/regional-review/montenegro-evidence-996-v9-lineage-completion/runs/2026-10-07/final-v4/run-2
python3 data/regional-review/montenegro-evidence-996-v9-lineage-completion/reproduce.py finalize
node scripts/evidence-quality.mjs data/regional-review/montenegro-evidence-996-v9-lineage-completion/evidence-quality.json .
```

The source vintages, reuse statements, restoration links, and exact inherited raw-source digests are documented in `SOURCES.md`. They remain inherited evidence and uncertainty, not new observations made for #1235.

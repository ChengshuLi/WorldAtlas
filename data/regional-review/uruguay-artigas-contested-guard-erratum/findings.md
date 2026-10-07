# Findings and handoff

## Supported

- The retained original report is `3970173b2c2050c1099ec427e4d64076e96a3000635ba20db203fa204320e44a` and remains byte-for-byte unchanged in the prior packet and in this packet's expected-report capsule.
- Two fresh offline runs produced the exact same full report hash. The pinned subject is `gb:URY:ADM1:27058087B22084813565519`; IGM records 15 (Rincón de Maneco) and 16 (Isla Brasileña) remain source contexts, with the retained 19-feature geoBoundaries and 21-feature IGM files.
- Negative controls reject a pre-existing output with its sentinel preserved, traversal, a symlink destination, capsule-code drift, and full-source-byte drift.

## Unresolved and engineering handoff

- This fixes only the overwrite-capable reproduction destination. It makes no new geographic finding and does not close the source, legal, or boundary questions in #1173/#446.
- The treaty and Uruguay legal records remain restoration-only with the exact prior retrieval instructions, hashes, byte counts, licenses, and interpretation limits preserved in the source inventory. Their original hosted bytes were not re-retrieved or independently authenticated for this safeguard.
- Any future edit to the historical computation should be proposed as a separately reviewed source/code change with a fresh capsule and exact-head evidence review. Do not replace original reports or source bytes.
- Geography and legal uncertainty remain open; no regional approval, import, repair, or deployment is implied.

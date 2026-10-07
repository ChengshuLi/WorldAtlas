# South America batch 4 validator integrity erratum

**Issue:** [#1332](https://github.com/ChengshuLi/WorldAtlas/issues/1332)
**Claimed scope:** the 215 retained subjects from #1116 only (167 Chile candidate ADM3 rows, 47 Paraguay candidate ADM2 rows, and one Asunción aggregate).
**Evaluation baseline:** `e9190786dbf758524a3bde513fc4bb4d1ed6a3e7` (fresh `origin/main` when the reservation was accepted).
**Historical references:** #1116 correction merge `e7cd364e08a713825daa80a3d085d23bd58d5730`; earlier original-evidence vintage `7245eca6d56ee71fd1f40631c72116167ac5037d`.
**Retrieved:** 2026-10-07, GitHub issue snapshot via the connected GitHub API and committed baseline objects via Git.

## Findings

The captured #1116 audit function accepts a parent roster whose first child token is replaced with a fabricated identifier while still reporting 39 parent rows checked. The additive validator independently compares all 39 parent rows and all 215 raw child tokens to the exact indexed subject identities, their pinned hierarchy parent IDs/names, counts, and scope flags. Seven adverse child-roster cases reject: fabricated, missing, duplicate, blank, substituted children, wrong parent name, and inconsistent count. The earlier nine mapping controls remain and reject.

The unmodified #1116 CLI was run only in a disposable scratch repository linked read-only to the Git object database. It replaced four scratch sentinel files: the retained-root legacy report and all three requested run products. A separate scratch run reproduced the issue’s complete code-drift fixture at the actual `runpy` boundary: the modified helper executed successfully and reported 214 matches beside the independent 215-feature audit. The new run records the exact captured helper hashes and rejects changed materialized helper bytes before execution. The adjacent manifest builder was inspected and its overwrite-capable `write_text` call was recorded; it was not executed.

Four successful generations are retained. `run-one` and `run-two` are the earlier draft executions; `run-three` and `run-four` are preserved intermediate reproductions; `run-five` and `run-six` are the two final fresh runs produced after the manifest builder, full historical input ledger and issue snapshot whitespace were finalized. The final runs use the shared `Baseline` and `NewVintage` helpers; their six calculation/control products have matching whole-file hashes. Run names, timestamps, per-run publication receipts, and paths differ and are retained as truthful metadata. Each run reserves a complete output set first and installs `publication.json` last. The safety controls reject ordinary-file collisions, broken symlinks, traversal and escaped paths; a controlled final-receipt failure leaves a failed partial run without a completion receipt. These safety fixtures run in disposable scratch trees.

## Evidence and reproducibility

Run the two entry points with Python 3.12.14 (the version recorded by the reproducibility outputs), then build the final manifest:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B research/geography/south-america-batch4-validator-integrity-erratum-2026/reproduce.py --vintage run-five
PYTHONDONTWRITEBYTECODE=1 python3 -B research/geography/south-america-batch4-validator-integrity-erratum-2026/reproduce.py --vintage run-six
PYTHONDONTWRITEBYTECODE=1 python3 -B research/geography/south-america-batch4-validator-integrity-erratum-2026/build_manifest.py
```

The manifest inventories the entire 36-part index and every pinned baseline input, all 215 subject-to-part links, all four preserved run receipts, source-vintage records, methods, metrics, adverse controls, and change receipts. `reproduce.py` binds and executes the trusted immutable helper bytes and the affected validator bytes from Git. Its disposable historical CLI run supplies the old reproducer and its dynamically read support files from the same `7245` vintage. No network or credentials are used.

The original 2020 Chile and 2012 Paraguay source geometries were not retained or restored here. The inherited candidate labels, source IDs, vintages, license descriptions and source-member matches remain observations from the earlier packet, not fresh authoritative source verification. The 215-row/39-parent checks establish retained Atlas identities and parent links only. Current administrative meaning, legal parentage, completeness, boundaries, geometry accuracy, source rights, INE response content, Asunción's unit identity, adjacent seams, and equivalence between Chile ADM3, Paraguay ADM2, and the aggregate city remain unresolved. Five area records are validated as the inherited scope roster, not as administrative units.

This packet is additive. It leaves #935/#948/#1120 artifacts, IDs, source pins, and review history untouched; it does not certify #1116's source-content scope or certify the full South America region. Follow-up source restoration and legal/geometry review remain with their existing owners.

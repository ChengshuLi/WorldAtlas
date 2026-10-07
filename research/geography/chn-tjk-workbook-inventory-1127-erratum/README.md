# China–Tajikistan workbook member inventory erratum

This additive packet corrects one decoded ZIP-member digest in the retained Tajikistan Statistics Agency workbook inventory from issue #1118 / PR #1127. The retained workbook's whole-file bytes remain 11,242 bytes with SHA-256 `c0576b220fa3d2b7281d4c4680b3e143a523dec3a733c0fe3eba23ed91e47e40`. Its 12 unique members decode to 28,161 bytes. Eleven member records are unchanged. The historical inventory says `xl/styles.xml` is `7ccd4c42f9df7e401782679d46e7bd8b8c5a2d83205b23ca43104054ceaa971f0`; hashing the complete decoded member yields `7ccd4c42f9df7e401782679d46e7bd2f1c67a3b30fbaf8be3ed51331e9041a2b` (5,820 bytes). This is an inventory correction, not evidence that the workbook or its literal table data are corrupt.

## Reproduce

From the repository root, run the packet's verifier twice with fresh vintage names:

```sh
python3 research/geography/chn-tjk-workbook-inventory-1127-erratum/reproduce.py --vintage run-20261007-07
python3 research/geography/chn-tjk-workbook-inventory-1127-erratum/reproduce.py --vintage run-20261007-08
python3 research/geography/chn-tjk-workbook-inventory-1127-erratum/reproduce.py --compare run-20261007-07 run-20261007-08 --vintage compare-20261007-v4
```

The runner authenticates the workbook, old inventory, previous issue evidence manifest, original inspect script, shared immutable evidence helper, and subject-bearing data blobs at baseline commit `432c5b8e0ac9b9597738a31f5386569312c75966`. It captures and executes the helper bytes from that commit after matching their digest and materialized file; it also checks the original inspect script against its pin. ZIP member bodies are read to end through `ZipFile.open`, which also exercises ZIP CRC verification. The verifier requires the exact unique 12-name set, checks each complete decoded member's size and SHA-256, and reconciles their total size. Positive and negative controls run that same verifier against the corrected inventory, the historical wrong digest, a one-digest mutation, a duplicate-name archive, and an archive missing a member. The comparison command checks both complete publications and confirms that deterministic result files agree byte for byte.

The evidence manifest binds the three original subjects to their previously documented containing files: the two China IDs are in `data/geography/part-3.json`; the Tajikistan ID is in `data/geography/part-23.json`. These pins establish continuity of the scope and inputs, not new validation of geography.

## Limits and unresolved geography

The workbook states administrative counts as of 2025-01-01; it is not boundary geometry and cannot establish current territorial boundaries, exact parent relationships, completeness of the Atlas geometry, border placement, or neighboring-level granularity. The prior packet identifies CC BY 4.0 terms for the workbook, but this erratum does not perform a new legal review. No official source page was reacquired here. To restore the source-page context for a future review, revisit the official workbook URL above and the Statistics Agency analytical-tables page `https://www.stat.tj/en/analytical-tables/?lang=tj`; verify the page date and applicable reuse terms before relying on them. The workbook's original bytes, source-inventory file, previous outputs, IDs, and release pins are preserved unchanged. Territorial meaning, boundaries, source vintage/completeness for geometry, and rights review remain separate unresolved questions; no regional or publication approval is claimed.

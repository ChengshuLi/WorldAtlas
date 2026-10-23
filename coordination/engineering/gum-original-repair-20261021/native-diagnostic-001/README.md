# GUM 139-key native diagnostic

This is a stock read-only diagnostic of the exact original GUM request, not a native-authority result or accepted delivery.

- Base: `2bfc64ad6c622fd4e9c5f5f4cf763db22828e940`.
- Source evidence and requested patch: commit `44601c86cb6b805a66ec0aba6860f2d24610ef38`, respectively `source-evidence-001/generated/source-evidence.json` (49,085 B; SHA-256 `607237a492cedc144066f11998591295e686626ace1e5d53d4ec427c1a44c126`) and `source-evidence-001/native-requested-patch.json` (10,230 B; SHA-256 `95168d142276959f5cf9222d66aae378a78619e51e2334a983524f7b78e00689`).
- Diagnostic config SHA-256: `3a3ab9b2f34c2ad774d5ed177f4384cffd9baf1de2144a6afabe1b2262865171`.
- Output: `generated/native-diagnostic.json` (SHA-256 `9a4a3fb62d9aa6e2b17c31b0d7ad8c5a4caf0c3ae2b20ab256db82cda69fcc21`); preparation receipt SHA-256 `a8778e32882651b67da6db16bcf854d11f69eaca8a00c43c760a2722226198d3`.

The command completed with exit status 0. It evaluated 139 requested cells: 0 supported, 139 held. All per-cell diagnostic rows are classified `territorial_exclusion_cells`; the first failing predicate is `unique-source-target-coverage` at y=121084, x=236626–236631, owner 7117. The source-evidence rows list USA ADM1 feature `gb:USA:ADM1:66186276B63361112364184` and USA ADM2 feature `gb:USA:ADM2:52423323B58805530467838` as negative operands for each of the 13 GUM targets. Their retained contact/candidate status does not resolve whether either is an applicable territorial exclusion for this original package.

Original scope remains 139 land cells, 86 intervals, owner 7117; the separate 37-cell physical companion is excluded. Physical output records whole-target missing/extra reconstruction flags for Santa Rita, Piti, Yigo and Umatac; those target-level flags remain adverse context, not per-cell clearance. Source vintage/license labels and polygon contacts do not establish current applicability or legal authority. No owner change, qualification, acceptance, or credit is recorded.

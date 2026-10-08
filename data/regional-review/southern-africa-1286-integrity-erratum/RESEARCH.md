# Southern Africa #1286 integrity erratum

Issue #1459 is limited to a validator-integrity correction for the exact 223 subjects frozen by issue #411. It does not reassess territorial truth, alter any assessment, change geography, or request a release. This packet uses the previously retained #411 evidence and tests whether the replacement verifier actually binds its outputs to those immutable inputs.

## Geography and retained source evidence

The 223 IDs comprise 157 Angola, 38 Mozambique, and 28 Malawi geoBoundaries ADM2 features. The immutable Atlas roster, parent IDs and country parts come from the baseline recorded in the original `scope-reproduction.json`; each original source feature is matched by `shapeGroup`, `shapeType`, and `shapeID`. The input files are the pinned geoBoundaries Core revision `9469f09592ced973a3448cf66b6100b741b64c0d`, with these historical source vintages:

| Country | Source vintage | Retrieved (UTC) | Retained bytes | SHA-256 | License recorded in pinned metadata |
| --- | --- | --- | ---: | --- | --- |
| Angola | 2018 | 2026-10-06 00:15:21 | 3,146,775 | `44e58b2a8c2fefb9369294a32e2adde3e3637b9e02e8f1e2c53b400bec04f404` | CC BY 3.0 IGO |
| Mozambique | 2019 | 2026-10-06 00:15:22 | 24,879,690 | `5f04bb75bcb08092451f8626f7113830abfe726c1fad5309107309ab6cceab65` | CC BY 3.0 IGO |
| Malawi | 2020 | 2026-10-06 00:15:23 | 5,658,560 | `5fe9b6313ee3eaf6d2b8a4579b7a7fa75dc1b16b9324a436f5a359da23527ea6` | CC BY 3.0 IGO |

The source GeoJSON, pinned metadata and geoBoundaries citation/use statement remain in the original #411 packet at `data/regional-review/regional-review-029dcbc646de003d/`. Their immutable Git blobs at `762d7b5a568ca845d85a98a4d188678c126a5d58` are read and hash checked by the replacement verifier. This provides reproducible restoration from the repository history; no additional copy or upstream download was made for this erratum.

These source vintages support historical native-ID and name joins, reported unit roles, and the specific source geometries. They do not prove current units, legal boundaries, present-day completeness, or correct Atlas parents. The inherited findings concerning Angola's post-2024 changes, Mozambique's full roster and parentage, Malawi's 28/32-unit model, neighboring granularity, topology, and legal authority remain unresolved in their original follow-ups. No subject becomes geographically approved here.

## Integrity findings and method

The issue reports two reproducible false acceptances in the prior validator: a coherently refreshed false Angola source hash, and an exchange of the original Quela and Cidade De Maputo scientific dispositions. The valid original files still contain the original 0 justified, 1 correction-needed, and 222 insufficient-evidence decisions.

`verify-integrity.mjs` captures the complete candidate crosswalk and assessment byte buffers once, parses those buffers, checks the assessment's crosswalk digest against the captured bytes, and reports hashes from those same buffers. It also consumes the frozen scope, frozen original assessment rows, source review, source GeoJSON and pinned Atlas baseline. It independently derives each native source descriptor from its retained committed source blob and checks both country-summary descriptors and per-row source hashes against those exact path/byte/hash values. For each of the 223 IDs it also compares the complete assessment object, including structural diagnostics and unknown fields, with the frozen original row. It still checks exact roster membership, Atlas/native source joins, source vintage/role and hierarchy parent linkage. The output includes source file paths, byte counts and hashes, code hash, input limits, row counts and explicit geographic limits.

Every run must provide the exact validator file SHA-256. Each output uses one fresh `vintages/<name>/validation.json` destination; the run directory is reserved before inputs are consumed and publication uses an exclusive, fully flushed temporary file linked into place only after completion. Existing destinations, symlinks, path escape and partial-output fixtures are retained as negative controls.

## Reproduction

From the repository root with Node.js 24, pin the validator bytes and execute the two saved full runs using the commands recorded in `controls/` and `vintages/`. Run the directed controls with:

```sh
node data/regional-review/southern-africa-1286-integrity-erratum/run-controls.mjs
```

The control runner binds its own executed bytes and executes the replacement entry point against all seven retained directed mutations and eight newly generated cases: a coherent false source hash, false country-summary-only source descriptor, moved and incorrect per-ID dispositions, a wrong individual source descriptor, and missing, extra and duplicate subjects with refreshed counts and crosswalk hashes. It also executes the exact prior validator against both newly reproduced false-acceptance cases. The actual process exit status, exact fixture hashes, diagnostics, and receipt presence are recorded. The safe-destination controls exercise existing files and directories, symlink and traversal attempts, and interrupted-output sentinels.

The two accepted output records are byte-identical. They demonstrate successful and repeatable source/input joins and integrity checks only. They do not establish source completeness, territorial correctness, legal status, neighboring granularity, or regional approval, and they do not authorize an import or publication.

## Handoffs and remaining work

No shared-core engineering follow-up is required by this bounded integrity repair. The historical source and territorial questions remain with their existing research owners: Mozambique source and parent roster (#1042), Malawi 28/32-unit meaning (#1045), Angola post-2024 successor boundaries (#1046), four Cabinda units (#896), and the disjoint Mozambique subjects (#412). This packet hands no boundary or parent change to production and does not close those findings.

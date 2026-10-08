# Portugal–Spain producer and control preservation correction

Raised 2026-10-08. This additive packet addresses the local producer/control integrity defects recorded for #1482 and affected PR #1312. It does not reopen the source comparison or alter any original packet file.

## Frozen scope and inputs

The corrected command copies enforce exactly two source families, four complete component identities, four exact Atlas/contact subjects, five family-contact incidences, the frozen subject-to-part bindings, and the pinned parent IDs. The Atlas agricultural district remains a 28-member aggregate; the Encinasola source-member relation remains distinct.

| Subject | Pinned containing part | Pinned parent |
| --- | --- | --- |
| `atlas:district:ESP-2101:def08fa9` | `data/geography/part-29.json` | `framework:province:huelva:67e82699c154` |
| `gb:ESP:ADM3:28895703B56784737193540` | `data/geography/part-8.json` | `framework:province:huelva:67e82699c154` |
| `gb:PRT:ADM2:2272694B13078000098594` | `data/geography/part-19.json` | `framework:province:beja:2057344bed65` |
| `gb:PRT:ADM2:2272694B82300393258858` | `data/geography/part-19.json` | `framework:province:beja:2057344bed65` |

The original scope whole-file SHA-256 is `ca652688f051fbd44bed3cc5a4130bb9b4ada0d3b20667f6b3a91209bd68a6c5`. Before the producer reads scope, source capture, code or geometry inputs, it authenticates the complete PR #1312 packet against its preserved manifest SHA-256 `cb1a3e8d3c88b64807d735b4411423209c117e442073408e827618b83003ecd0` and merge `cbae22cc877f6f8a70650069d91d2b34240582f7`. This includes every descriptor in both the original candidate output inventory and retained source-file inventory. The six complete DGT/IGN item response bodies are covered by the latter. The original source capture index SHA-256 is `f63611c528ff85074b1e527e95d1647778d06473cb663b10fd1be5320f377f6d`.

The historical geography baseline remains `fbc3c4c3a7cb06e8d33d11992b0c26054a9d50d7`, with the issue-declared whole-file pins for world index, three containing parts, old packet scope, and original producer/control scripts. The exact original geometry helper (`0b8e5b155c7a68b802b99a3597c63ac48293f276e682d34e9167cb5105b2a334`) and ellipsoidal area helper are loaded from that immutable commit. The shared immutable-output helper is loaded from fresh-main commit `c8df65e1d5c4d235c33e2f488c3e29d26223860f` and its exact bytes are pinned in the manifest.

The original packet retains whole direct DGT CAOP2025 municipal item bodies and IGN administrative-unit/boundary item bodies, response headers, terms and legal/source pages, with their original retrieval timestamps, hashes, CRS declarations, URLs, completeness notes and reuse limitations. Those bytes and the earlier dated outputs remain at their original paths and hashes; this correction adds no duplicate source downloads and makes no new provider request. The original manifest and restoration paths remain authoritative for each source citation. The DGT approval/change-list and IGN license interpretation remain unaudited; header/hash authentication does not establish reuse rights, effective date, bilateral authority or current territorial meaning.

## Corrected entrypoints and results

Run from the repository root with the project Python 3.12 scientific environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHON=/path/to/python3 WORLDATLAS_TEST_PYTHON=/path/to/python3 /path/to/python3 -B research/geography/portugal-spain-official-boundaries-audit-followup-20261008/scripts/run-analysis.py run-01-r5
PYTHONDONTWRITEBYTECODE=1 PYTHON=/path/to/python3 WORLDATLAS_TEST_PYTHON=/path/to/python3 /path/to/python3 -B research/geography/portugal-spain-official-boundaries-audit-followup-20261008/scripts/run-analysis.py run-02-r5
WORLDATLAS_RUN_ONE=run-01-r5 WORLDATLAS_RUN_TWO=run-02-r5 WORLDATLAS_CONTROL_VINTAGE=controls-r6 PYTHONDONTWRITEBYTECODE=1 PYTHON=/path/to/python3 WORLDATLAS_TEST_PYTHON=/path/to/python3 /path/to/python3 -B research/geography/portugal-spain-official-boundaries-audit-followup-20261008/scripts/run-controls.py
PYTHONDONTWRITEBYTECODE=1 PYTHON=/path/to/python3 WORLDATLAS_TEST_PYTHON=/path/to/python3 /path/to/python3 -B research/geography/portugal-spain-official-boundaries-audit-followup-20261008/scripts/reproduce-adverse.py
```

Each science command admits the entire fresh output set through `Baseline` and `NewVintage` before computing. Each run is exclusively published under `vintages/<run>/`; `publication.json` is the final whole-file receipt. Existing paths, ordinary files, live/dangling symlinks, and unsafe vintage names reject before calculation or writes. A post-calculation failure preserves every computed scientific product in a separate failure vintage with an explicit failed record, omitting the success execution receipt.

The r5 paired run inventories match byte-for-byte across all 13 scientific products. The original family measurements reproduce:

| Family | Component area sum (m²) | Official item union covered (m²) | Coverage | Uncovered residual (m²) |
| --- | ---: | ---: | ---: | ---: |
| `gap-source-batch:509d6812e22b584f960be362` | 463,562.08602590323 | 462,147.28753493703 | 0.9969479848900172 | 1,414.7984911014807 |
| `gap-source-batch:4c43b39b2038f22dfdedebce` | 4,668,822.173517021 | 4,667,764.922989489 | 0.9997735509110778 | 1,057.2505274202927 |

The controls r6 execute the corrected control CLI, compare both whole run inventories, preserve the original source measurements, and pass seven controls, including a wrong-parent rejection through the same validator called by the producer. The corrected adverse-control r5 report contains 19 passed checks: duplicate/missing/fabricated subjects, components, family identities/incidences and reference files; missing or altered original inputs/code; coherently refreshed candidate scope hashes; ordinary-file collisions; live and dangling symlinks; output traversal; producer rerun collision against the existing `run-01-r5`; and failure after computation. The failure vintage `run-03-r99-failed-f2570926ff9e` retains 13 computed scientific products and an explicit failed receipt, with no success execution receipt. Its complete outputs are hash-checked by the adverse-control report. On repeat runs, the script selects the next unused owned `adverse-controls-rN` vintage.

The earlier adverse report r3 is retained as superseded evidence. Its producer-rerun probe named nonexistent `run-01-r4`, so that one reported collision did not establish rejection of an existing science vintage. The corrected r4 and r5 reproductions target the retained `run-01-r5` destination and record the actual entrypoint rejection; r4 is retained as the first corrected report, and r5 is the report generated by the final reproducible CLI. The other r3 results are preserved without relying on them for this corrected check.

One early superseded attempt, `vintages/run-01-failed/`, exposed a completion-receipt size overrun and records that failed outcome. Final accepted outputs are `run-01-r5`, `run-02-r5`, `controls-r6`, and corrected `adverse-controls-r5`; the original adverse report r3 remains preserved as explicitly superseded evidence, and intermediate successful vintages from code-preflight iterations were removed from this packet.

## Limits and handoff

No boundaries, source geometries, identities, hierarchy, release pins, or production records were changed. Numerical agreement verifies the correction preserves the previous comparison; it does not determine whether residual pieces are land, water, ice, or administrative error. The CAOP effective dates, missing Portuguese-side border line, bilateral authority, legal reuse, physical class/cause/ownership, and registration accuracy remain unresolved under #1299/#1202 and their existing owners. No boundary is approved, imported, certified, or published by this correction. The engineering handoff is limited to consuming this evidence-integrity correction and preserving the unchanged source/geometry acceptance.

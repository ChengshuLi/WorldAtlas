# Matanuska fresh-output reproduction correction

Dated 2026-10-06 (America/Los_Angeles). This correction addresses only the output-preservation defect in issue #1241. It owns this nested reproduction-erratum directory. The earlier campaign's sources, captures, controls, and outputs remain read-only.

## Finding and correction

The original producer only accepts the already archived run-one and run-two directory names, creates them with exist_ok=True, and writes its three output files with truncating write_bytes. It therefore has no fresh-vintage CLI path and can replace a retained output family on rerun.

reproduce-fresh-vintage.py is based on the exact producer bytes at merge d13250b2e7adb0f7fca00e8ee37acda4dc5cb490 (SHA-256 bfd3b6519d255128144b041143310eb25c5d857c248618d7ad6f1af98f344198). The transformation receipt records the original producer and helper pins. At startup the corrected producer verifies the complete input inventory: all 82 frozen inputs from the original issue baseline, the original source/output descriptors, their compressed and decoded hashes where applicable, and the producer/helper/control code. It also verifies that the exact local source files match their immutable commit pins.

The CLI accepts a new safe name such as --run-id fresh-third. It resolves and bounds the run root, run destination, receipt directory, and receipt path under this owned directory, refuses path traversal and symlinks, requires a non-existing run directory, creates that directory exclusively, checks resolved containment, and writes each output with exclusive xb creation. Each run gets a separate receipt with its concrete directory and file paths. Payload path templates use {run-id}; the per-run receipts state the concrete paths.

## Reproduction result

Two complete vintages, fresh-one and fresh-two, were generated using Python 3.12.14, Shapely 2.1.2, and GEOS 3.13.1. Their three corresponding output files are byte-identical:

| Reproduced measure | Value | Unit |
| --- | ---: | --- |
| Selected components | 282 | components |
| Bound candidate fragments | 283 | fragments |
| Exact contact rows | 571 | rows |

The selected geometry output and full source-overlay ledger are byte-identical to the preserved original run. All numeric and source-predicate values also match. The summary file differs only in output-path metadata: the original names results/{run-id}, while the new summary names reproduction-erratum/runs/{run-id} and the per-run receipts state the concrete paths. The original run directories and all 33 retained source/output files checked by the preservation receipt remain unchanged.

The full reproduction applies the pinned interior-roster predicate across all 34 priority shards, verifies the exact sorted 282-ID roster, closes all 283 fragment bindings and 571 retained contacts, checks the full and simplified administrative products separately, and reproduces the original source-coordinate predicates. All 282 component classifications remain unknown.

## Input vintages and preserved limits

input-pins.json carries the exact 82 frozen input descriptors at cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1, plus every retained source, output, and code descriptor from the earlier manifest, each with its truthful commit. The premerge evidence baseline is anchored at d13250b2e7adb0f7fca00e8ee37acda4dc5cb490 so the issue's seven declared hash pins bind to actual immutable files. Eighty-one of the 82 frozen input byte sequences are unchanged there. The later merge changed data/geographic-releases/current-manifest.json; the original issue-baseline version is retained separately at baseline-inputs/current-manifest-at-issue-baseline.json with its exact original hash and commit. The producer still reads the full frozen input set from the original cea80a8 commit.

The original licenses, source roles, vintages, retrieval dates, and limits are copied into the new evidence manifest. This correction does not authenticate the separate full-source records again. Complete RESOLVE Rock and Ice geometry remains unavailable under the prior 32 MiB cap. Source registration, full physical coverage, component-level cause, water/ice status, administrative ownership, and every physical classification remain unresolved. No geography is repaired or approved, and no import, publication, deployment, or production write is authorized.

## Controls and reproduction

validation.json and the typed control receipts retain the positive, changed-source, omitted-component, omitted-contact, vintage-laundering, existing-file, existing-directory, run-destination symlink, receipt-directory symlink, traversal, and outside-root cases. Rejected CLI attempts were checked for side effects; the existing-output hashes and sentinel stayed unchanged, and neither outside target was created.

From the repository root, run:

python3.12 research/geography/gap-source-matanuska-physical-seam-20261006/reproduction-erratum/reproduce-fresh-vintage.py --run-id fresh-third
python3.12 research/geography/gap-source-matanuska-physical-seam-20261006/reproduction-erratum/validate-fresh-vintages.py
node scripts/evidence-quality.mjs research/geography/gap-source-matanuska-physical-seam-20261006/reproduction-erratum/evidence-quality.json
node scripts/check-handoff-scope.mjs --branch geography/matanuska-reproduction-1241-20261007 --base origin/main --pr-body-file /tmp/pr-1241-body.md --issue-file /tmp/geo1241-claim-snapshot.json

This packet fixes safe reproduction and retention behavior only. It does not close or certify the independent physical-source questions listed above.

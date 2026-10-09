# Nordic v14 final report accounting correction

2026-10-08 (America/Los_Angeles) — Additive mechanical correction for issue #1559 and the accepted v14 output pair from issue #1389 / PR #1409. The original packet, all of its source pins, v3–v14 attempts, runner, and prior metrics remain unchanged. Older v12 commands and checks stay historical; this correction binds only to the accepted v14 report pair.

## Finding and corrected result

The prior summary reported a maximum of **157,734,275 bytes**, which equals `/families/fragments/phase_bytes`. Both accepted v14 whole reports also contain `/complete_fragment_scan/phase_bytes = 157,860,872`. A recursive inventory of every `phase_bytes` member found the same exact **12** phase pointers and values in both reports. The corrected maximum is therefore **157,860,872 bytes**, a **126,597-byte** increase over the prior summary. It remains **110,574,584 bytes** below the recorded **268,435,456-byte** phase cap.

These values describe byte accounting recorded in the accepted reports. They are not process RSS, do not establish a resource-cap violation, and do not newly certify every raw/decoded/runtime byte of the original computation. The original v14 report pair was authenticated from whole-file Git blobs at `643e4123ce9881a9d07f564166edae34aec7aa08`, and the reported executed runner hash was checked against the same pinned `reproduce.py` bytes. The existing issue/source lock and all 57 source pin identities remain intact.

## Reproduction and controls

Use Python 3.12.14 and the pinned `worldatlas-evidence-preparation-v1` helper. Each run reads the immutable v14 report pair, verifies the accepted runner/report pins and exact phase-pointer inventory, then publishes one JSON result with a completion receipt written last:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B research/geography/nordic-final-evidence-1409-erratum/reconcile_final_accounting.py --run-id report-correction-one-20261009
PYTHONDONTWRITEBYTECODE=1 python3 -B research/geography/nordic-final-evidence-1409-erratum/reconcile_final_accounting.py --run-id report-correction-two-20261009
PYTHONDONTWRITEBYTECODE=1 python3 -B research/geography/nordic-final-evidence-1409-erratum/reconcile_final_accounting.py --compare-runs report-correction-one-20261009 report-correction-two-20261009 --summary-id report-correction-summary-20261009
```

Both independent runs derived the same canonical assessment SHA-256 `1b58eb8072f10b9b22641fc0311c9f033926555cb6822d5fc53f9fbfc8c5c001`. Their distinct full result and publication hashes, and the final pairwise/control output hashes, are recorded in `evidence-quality.json` and the generated files.

The entry point rejected each of the 12 missing phase members, a missing maximum candidate, changed report bytes, a foreign v14 report in the v14-one slot, a v12 run ID or path, a stale prior summary, and a modified comparison result. The first run also exercised occupied-run and output destinations, a dangling run symlink, and an escaped run ID; sentinels and the literal link remained unchanged. These controls exercise the report/input and output-admission boundaries without rerunning GIS or changing original files.

## Scope and unresolved findings

This packet changes no geometry, source data, territorial identity, parent, source license, boundary conclusion, or geographic release. It performs no acquisition, import, migration, deployment, publication, or approval. The existing Norway/Sweden source-vintage and parent-crosswalk questions, source completeness and license limits, legal boundary meaning, and physical/hydrology uncertainties remain with their existing owners. A corrected report does not certify Nordic geography or the original end-to-end resource accounting.

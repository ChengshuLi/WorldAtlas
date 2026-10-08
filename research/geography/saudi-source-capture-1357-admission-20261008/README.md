# Saudi #1357 bounded admission and writer successor

This additive packet addresses issue #1511. It preserves the complete PR #1357
predecessor and supplies a bounded runner, a fail-closed freeze interface,
whole-file preservation checks, and adversarial writer reproductions. It does
not change or approve Saudi geography, source authority, license, physical
classification, legal status, or production data.

## Admission result

The pinned predecessor lock declares 90 encoded source files (100,728,427
bytes) and 75 unique decoded bodies. Deduplicating by exact SHA-256 gives a
682,797,443-byte raw-plus-decoded source minimum. The current plan also accounts
for the frozen local code/configuration and lock, both authenticated historical
execution receipts, the retained fourteen-product output inventory, a 32 MiB
runtime reserve, and a 4 KiB completion receipt. Its complete phase is
726,781,883 bytes against the unchanged 268,435,456-byte cap.

`run_safe.py` authenticates the frozen code and local input files against their lock hashes, then counts the small pinned lock, two pinned receipt files, the actual safe helper scripts and interpreter executable in the complete plan. The helper and
runtime bytes are individually hashed and counted; the separate 32 MiB runtime
reserve accounts for execution resources and loaded runtime support. It refuses with exit 78 and records
`execution/refusals/run-4-admission.json`; it does not read source blobs, start
decompression, launch the extractor, create output products, or publish a
completion receipt. `freeze_safe.py` records the same refusal before source
reconstruction or writing a new lock. The full source replay remains blocked
until a complete, independently reviewed admissible method is available. This
packet does not split the source closure or change either byte cap.

## Writer controls

`admission.py` checks all requested leaves and ancestors before work, rejects
existing paths, symlinks, traversal, and ancestor collisions, and publishes
new files with exclusive no-follow opens and fsync. `run_safe.py` reserves the
entire historical output filename set and its receipt before invoking the
preserved extractor. It records the execution receipt last; a failed child is
marked `failed-attempt` and never as complete. `freeze_safe.py` exposes an
exclusive freeze-lock writer for a separately admitted bounded operation; the
current full source freeze is refused.

`execution/runtime-launcher-mismatch.json` preserves why the preliminary bundled-runtime receipts are excluded. `execution/legacy-writer-reproduction.json` records the unchanged predecessor
wrapper's dangling-receipt and symlinked-`runs` escapes. Both probes use a
complete private copy of the seven relevant code/lock/local-input files and
change only its disposable issue API JSON. The real child rejects the altered
input before any Git source-body read. Each observed failure receipt truthfully
reports an incomplete run. Existing ordinary-receipt and partial-output
controls remain unchanged. The original seven files and all 148 files in the
predecessor packet are separately hash- and mode-verified against the PR base.

The two retained historical runs each contain fourteen whole-file products of
10,244,768 bytes. Their complete file inventories and hashes match. This is
preservation evidence, not a new source replay or a second scientific result.

## Reproduction

Run from the repository root with the bundled Python runtime. Use a fresh label
for each control receipt set:

```sh
/usr/local/bin/python3 -B research/geography/saudi-source-capture-1357-admission-20261008/run_safe.py --run-id run-5 --repo .
/usr/local/bin/python3 -B research/geography/saudi-source-capture-1357-admission-20261008/freeze_safe.py --repo . --run-id freeze-retry-4
/usr/local/bin/python3 -B research/geography/saudi-source-capture-1357-admission-20261008/test_safety.py
/usr/local/bin/python3 -B research/geography/saudi-source-capture-1357-admission-20261008/reproduce_legacy_writers.py --output execution/legacy-writer-reproduction-retry.json
/usr/local/bin/python3 -B research/geography/saudi-source-capture-1357-admission-20261008/verify_historical_products.py --repo .
/usr/local/bin/python3 -B research/geography/saudi-source-capture-1357-admission-20261008/verify_predecessor.py --repo . --commit HEAD
/usr/local/bin/python3 -B research/geography/saudi-source-capture-1357-admission-20261008/write_control_receipts.py --suffix <fresh-label>
```

Each run/freeze/refusal/receipt and reproduction output name is exclusive. Use
another fresh run ID or output path on later repetitions; existing results are
never overwritten.

The legacy packet's original `run_final.py` and `source_extract.py` remain
preserved historical artifacts and are unsafe as standalone writers. Use the
new safe interfaces for any bounded future attempt; a direct caller migration
or production change is outside this geography-owned path and requires its own
engineering owner. No full replay, approval, import, deployment, or publication
is authorized here.

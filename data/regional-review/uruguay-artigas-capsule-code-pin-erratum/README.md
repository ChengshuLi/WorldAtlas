# Artigas capsule code identity erratum

This packet reproduces the existing offline representation check while independently pinning the exact capsule code it executes. It is a preservation and execution-integrity correction for issue #1413. It makes no territorial, boundary, title, geometry, or source-authenticity determination.

## Reproduce

From the repository root, run two fresh output names:

```sh
python3 data/regional-review/uruguay-artigas-capsule-code-pin-erratum/reproduce.py --output baseline-run-one
python3 data/regional-review/uruguay-artigas-capsule-code-pin-erratum/reproduce.py --output baseline-run-two
```

Each run checks the exact issue contract snapshot, the complete required legacy manifest inventory, every captured input and code hash, and an independently fixed capsule SHA-256 before reserving its output. The manifest cannot supply or refresh the trust anchor for the executable. Successful runs retain the exact historical report and a completion receipt. Failed computation leaves its output, any report already computed, and a `failure.json`; it does not create a success receipt. Outputs are exclusive and never overwrite prior attempts.

`outputs/baseline-run-one/` records the first successful corrected run, before the final success-receipt step was added. Later runs use the receipt-writing entry point; `controls/corrected-baseline-runs.json` records the final two verified runs and captured process streams.

Run the directed controls with:

```sh
python3 data/regional-review/uruguay-artigas-capsule-code-pin-erratum/controls/verify_corrected_runner.py
```

The controls invoke the actual entry point in isolated fixture trees using hard links for unchanged source bytes. Mutated files are atomically replaced in their fixtures. Captured stdout/stderr and per-case outcomes are retained under `controls/`.

To capture two new successful executions and their full process streams, run:

```sh
python3 data/regional-review/uruguay-artigas-capsule-code-pin-erratum/controls/reproduce_corrected_runner.py
```

## Source context and limits

The retained geoBoundaries 2017 Uruguay ADM1 response has 19 features and represents Artigas as one ADM1 unit. Its ODbL status comes from the existing pinned Atlas source metadata; this packet preserves those bytes and does not independently authenticate the upstream publisher. The retained Uruguay IGM layer 3 response has 21 features; its source metadata records a 2024-09-18 data update and 2026-07-15 metadata update. Its `DEPTO`, `DEF`, and `TXT` fields record how the service labels the two contested feature records. The official metadata permits use with attribution to IGM, AGESIC, and IDE. These facts describe retained source representations only and do not establish bilateral title, territorial membership, an ordinary ADM2 roster, or completeness for another administrative purpose.

The five legal originals remain restoration-only. Their exact URLs, byte counts, SHA-256 values, retrieval dates, and restoration instructions remain in `inputs/original-source-inventory.json`. They were not fetched or authenticated again for this erratum. The full prior source inventory and original report are retained byte-for-byte.

The subject remains `gb:URY:ADM1:27058087B22084813565519`, with recorded parent `framework:province:artigas:dc4b2e0fed20` and `semantic_review.status` `open`. This work does not alter geography, hierarchy, IDs, or geometry and does not assess topology, area, overlap, or legal boundaries.

# #1485 output admission erratum for retained #1319 results

This evidence-only erratum repairs publication safety for the already-retained Madhya Pradesh #1319 report. It does not alter the original packet, source files, IDs, parents, results, pins or geographic decisions. Its only new outputs are under this issue-owned directory.

## What the reproductions establish

`producer_republish.py` admits a complete fresh output vintage before reading its report inputs, verifies the full 224-subject/27-group retained result, and republishes the exact compressed result bytes through the whole-set writer. Two fresh runs must have byte-identical `assessments.json.gz` products and complete `publication.json` receipts. This is a retained-output republish only. It is not a fresh execution of the original geometry producer and makes no new scientific finding.

`control_writer.py` rechecks the complete old-to-corrected report row join, the exact 16 null-to-source Agar fields, the unchanged 27 province assessments, classification totals and unresolved Sheopur source. It publishes the summary, complete correction ledger and positive, negative and reproducibility receipts as one fresh output set. The corrected report and every original input remain pinned to Git; the original control writer is preserved unchanged and not executed as the corrected writer.

Both entry points execute the exact `scripts/evidence/immutable.py` bytes at the current PR-base commit. The helper admits all named products, rechecks every pin before writing, creates products exclusively, and publishes `publication.json` last. `safe_outputs.py` adds preflight checks for all destination ancestors, including existing non-directory paths, live and dangling symlinks, complete output-set collisions and traversal. Historical producer inputs are individually admitted to the shared 256 MiB phase budget before any input bytes are materialized; each ordinary-file size is checked against the 32 MiB limit first.

## Source and geographic limits retained

No new upstream source was captured. The existing source inventory records the geoBoundaries file as native commit `9469f09`, a 2018 ADM3/Sub-District representation with 2023 metadata update/build, and a declared ODbL 1.0 license/attribution. This erratum did not independently determine the source release's legal reuse terms, territorial meaning, current boundary correspondence or district completeness. The original complete compressed file is pinned; its declared decoded size is 40,040,002 bytes, beyond the 32 MiB ordinary-file limit, so it was not decoded or replayed here.

The original source inventory records 6,822 retained features against 6,836 metadata units (difference 14). The retained 2026-10-05 IGOD Agar-Malwa roster capture records hash `190564a28ca08e96785ad20d9a6d2d235c7b0972d731c102ba361c16ac01374e`; page-specific reuse terms were not identified and its raw HTML was not retained. That roster is an administrative name crosswalk, not polygon or jurisdiction proof. Sheopur remains without a retained current roster. All legal/current-boundary, territorial-role, completeness, and neighboring-granularity questions remain as recorded in the original packet. No geographic approval, import or publication is established.

The initial issue snapshot is retained, and `issue-1485-current.json` records the current issue body/status separately. Their work-contract bodies match. The original source inventory, evaluation-input manifest, 27-file packet and source/report pins remain preserved or referenced by exact whole-file hashes. Historical evaluation inputs are individually verified from `cbb829672d18801e4310c30896a7ddb13a79b451`; the original #1319 report inputs are pinned at the current PR-base vintage. The first two output/control runs remain intact as evidence at the then-current `c8df65e1d5c4d235c33e2f488c3e29d26223860f` baseline. Intermediate `head088ab` runs and their results are retained, not overwritten. The final `head088ab2` set additionally validates the final historical-input admission and path checks from `088ab05aeb16ddfa8f0c43e596533f3f11d5fcec`. The 2026-10-08 progress checkpoint is on the original GitHub issue.

## Reproduction

Use the repository's Python 3.12 runtime. From the repository root, after running the managed-workspace storage check:

```sh
python3.12 -B research/geography/madhya-pradesh-output-preservation-1319-20261008/producer_republish.py --run-id producer-head088ab2-one
python3.12 -B research/geography/madhya-pradesh-output-preservation-1319-20261008/producer_republish.py --run-id producer-head088ab2-two
python3.12 -B research/geography/madhya-pradesh-output-preservation-1319-20261008/control_writer.py --run-id controls-head088ab2-one
python3.12 -B research/geography/madhya-pradesh-output-preservation-1319-20261008/control_writer.py --run-id controls-head088ab2-two
python3.12 -B research/geography/madhya-pradesh-output-preservation-1319-20261008/test_output_safety.py --tag head088ab2
python3.12 -B research/geography/madhya-pradesh-output-preservation-1319-20261008/build_manifest.py
node scripts/evidence-quality.mjs research/geography/madhya-pradesh-output-preservation-1319-20261008/evidence-quality.json
```

The checked-in run IDs and `head088ab2` validation tag are single-use; select a new unique suffix for another reproduction and leave existing results intact. `build_manifest.py` is a pre-commit step and requires the working-tree HEAD to equal the fresh `origin/main` baseline used for this packet. The actual entry-point safety exercise retains its case-by-case results under `validation/adversarial-controls-head088ab2.json`. A failed attempt never publishes a complete receipt; tests use only sentinels created beneath this owned namespace.

# Nukunonu–Bounty #1292 replay-preservation erratum — #1469

## Result

This packet adds a safe successor for the documented Nukunonu/Bounty coverage reproduction. It does not edit the original <code>reproduce_current_coverage.py</code>, either original packet, source inventory, indexed geometry, IDs, hierarchy, release, or historical/current comparison files.

The successor admits both a fresh success vintage and a separate failure vintage before computation. It loads the exact #1292 producer and area helper from their pinned Git commit, verifies every historical blob against the 61 hashes declared in #1469, redirects the producer’s two fixed output paths into a newly created private stage under this owned prefix, and retains the original producer’s complete stdout, stderr and exit status. A complete success record contains both generated report byte strings, whole-file hashes, the retained-output comparison, exact consumed Git input identities, the actual runner source, helper identity, runtime versions, and resource accounting. A shared <code>NewVintage</code> receipt is published last. Failure after computation is retained as a complete failure vintage without a success receipt.

## Original overwrite defect reproduced

<code>reproduce_original_overwrite_control.py</code> copied the exact complete Nukunonu/Bounty packet directories and the actual area helper from #1292 merge <code>c3ac95a5d72258d46c85e94590c8168edf32a3e3</code> into <code>original-overwrite-control/private-repo</code> under this owned prefix. For that run, a temporary regular <code>.git</code> locator pointed to the managed review Git directory so the intact original command could read the exact pinned history; the locator is omitted from the retained portable fixture.

Both private <code>current-coverage.json</code> files were replaced with the preserved <code>owned-existing-1292-coverage-marker</code> bytes. Running the actual documented original default command exited 0, replaced both existing markers with full outputs, and reproduced the retained report hashes exactly. The before markers, after reports, stdout, stderr, exit code, packet-copy hashes and outside-original before/after hashes are retained in <code>original-overwrite-control/evidence.json</code> and its private fixture. No original packet or report was changed. This is the defect being fixed; do not use the old default writer on retained evidence.

## Fresh reproduction

Run from the repository root with CPython 3.12.14, NumPy 2.3.5, Shapely 2.1.2 and GEOS 3.13.1:

~~~sh
PYTHONDONTWRITEBYTECODE=1 python3 data/regional-review/nukunonu-bounty-1292-replay-preservation-erratum/reproduce_safe_coverage.py run --vintage unique-lowercase-name
python3 data/regional-review/nukunonu-bounty-1292-replay-preservation-erratum/reproduce_safe_coverage.py check --vintage unique-lowercase-name
~~~

Choose a new run name each time. Never reuse an existing or failed vintage. <code>check</code> is read-only: it authenticates the complete receipt and report bytes, confirms the embedded runner source and pin table, re-reads each consumed historical Git blob, and verifies its hash against the issue pin inventory.

## Reproduced coverage

Two separate safe executions, <code>final-verified-a</code> and <code>final-verified-b</code>, produced byte-identical reports that match the original retained outputs exactly. These reproduce the report snapshot pinned at commit <code>9be99dfefb5871237ac464c6ef8a23e82be501f6</code>; they are not a fresh recomputation against the PR base. The metrics below are measurements of indexed overlap under the pre-existing method, not evidence of a complete modern coastline.

| Subject and source family | Measured result | Metric ID |
| --- | ---: | --- |
| Nukunonu OSM rings fully covered by indexed feature | 97/97 (1.0 fraction) | <code>nukunonu_osm_full_component_fraction</code> |
| Bounty Islands OSM rings fully covered by indexed feature | 27/27 (1.0 fraction) | <code>bounty_osm_full_component_fraction</code> |
| Nukunonu GSHHG components with positive-area overlap | 6/21 (0.2857142857 fraction) | <code>nukunonu_gshhg_positive_component_fraction</code> |
| Bounty Islands GSHHG components with positive-area overlap | 0/14 (0.0 fraction) | <code>bounty_gshhg_positive_component_fraction</code> |
| Nukunonu GSHHG source-union area covered | 0.15349689612035136 fraction | <code>nukunonu_gshhg_union_coverage_fraction</code> |
| Bounty Islands GSHHG source-union area covered | 0.0 fraction | <code>bounty_gshhg_union_coverage_fraction</code> |

The current OSM source rings have full overlap with their indexed features; the separate GSHHG comparator disagrees. The two datasets have different vintages, generalization and shoreline conventions. Neither demonstrates a complete present-day shoreline, legal boundary, approved hierarchy, or importable footprint. Nukunonu’s indexed feature and its parent review remain semantically open; the Bounty component inventory is not a crosswalk to DOC’s 22 rocks. Those findings and source limits remain in the original packet assessments. No regional or geographic approval is claimed.

## Source and historical evidence

The original Nukunonu and Bounty OSM extracts were retrieved 2026-10-02 and remain pinned by compressed and decompressed hashes in their original assessments and by the exact #1469 input inventory. They retain ODbL 1.0 attribution and share-alike terms. GSHHG Full Resolution 2.3.7 is the 2017 comparator under LGPLv3-or-later terms; the selected compressed and native byte hashes and extraction manifest are preserved. No source was newly acquired or copied into this packet. Original source bytes and restricted Government of Tokelau/DOC observations remain with their existing packets; follow those packets’ restoration-only instructions before any later reuse.

The pre-restoration comparison remains an archived measurement at <code>4afe1cb250fe68f5c63022d9583b3b89b9e607a2</code>. Current reports remain byte-for-byte unchanged:

- Nukunonu: <code>f8c0145f9bb44d7b6f1ee86e36bf1978583c27e9b682de8503b673b3a00031fb</code>
- Bounty Islands: <code>8fbefcb22d5b6a8eba7ffda440ddb03266f2f1e7c44e438df079687bf4f07e13</code>

The 61 immutable file pins, each with its actual commit and path, are listed in <code>source-pins.json</code> and expanded as whole-file descriptors in <code>evidence-quality.json</code>. The final run’s complete operation is **230,454,006 bytes**, below #1469’s 234,809,776-byte cap and the shared 256 MiB ceiling. Each decoded OSM/GSHHG source is below 32 MiB.

## Failure and preservation controls

- <code>failed-complete-failure-20261008</code> records a complete injected publication failure after both reports were computed with the final runner. The complete failure receipt retains the two matching reports; the success vintage has no completion receipt.
- <code>failed-run-20261008-a</code> and <code>failed-run-20261008-a2</code> retain earlier harness-wiring failures and their captured tracebacks. They are not geographic findings or successful reproductions.
- <code>test_safe_coverage_cli.py</code> checks the actual CLI against an existing output, a broken symlink, a symlink output and traversal; it verifies sentinels remain unchanged. Its shared-writer fixture exercises a symlink parent and failure after one output write, leaving no valid completion receipt.

## Verification

From the repository root:

~~~sh
PYTHONDONTWRITEBYTECODE=1 python3.12 data/regional-review/regional-supplement-e5d72b7004238f80/nukunonu/verify.py
PYTHONDONTWRITEBYTECODE=1 python3.12 data/regional-review/regional-supplement-b5299df90ec984cc/bounty-islands/verify.py
PYTHONDONTWRITEBYTECODE=1 python3.12 data/regional-review/regional-supplement-e5d72b7004238f80/nukunonu/reproduce_current_coverage.py --check
PYTHONDONTWRITEBYTECODE=1 python3.12 data/regional-review/nukunonu-bounty-1292-replay-preservation-erratum/test_safe_coverage_cli.py
node scripts/evidence-quality.mjs data/regional-review/nukunonu-bounty-1292-replay-preservation-erratum/evidence-quality.json
~~~

These checks establish reproducibility and safe output handling for this bounded packet. They do not certify geography, coastline completeness, legal meaning, shared-parent scope, regional acceptance, publication or imports.

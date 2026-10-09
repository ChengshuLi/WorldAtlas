# Cameroon measurement integrity erratum

This successor preserves the original #908/#1128/#1101 packets and adds a bounded reproduction for the two independently reproduced defects in #1343. It covers the exact 226 issue subjects. It does not change source geometries, IDs, hierarchy, scores, source disposition, core geography, or production data.

## Run

Use the repository's documented Python 3.12 environment with Shapely 2, GEOS 3, and pyproj 3. Run each entry point twice with a new lowercase vintage name each time:

```sh
python3 research/geography/cameroon-integrity-execution-1128-erratum/reproduce-corrected.py corrected-run-one
python3 research/geography/cameroon-integrity-execution-1128-erratum/reproduce-corrected.py corrected-run-two
python3 research/geography/cameroon-integrity-execution-1128-erratum/reproduce-legacy.py legacy-run-one
python3 research/geography/cameroon-integrity-execution-1128-erratum/reproduce-legacy.py legacy-run-two
python3 research/geography/cameroon-integrity-execution-1128-erratum/verify-pairs.py corrected-run-one corrected-run-two legacy-run-one legacy-run-two pair-verification
```

Each run admits its complete destination set before computation and creates one fresh directory below `vintages/`. `publication.json` is installed only after every output is written and synchronized. Never reuse a vintage name. A failed run with payloads but no `publication.json` remains failed and is retained for diagnosis.

## Evidence method

`input-pins.json` binds the authenticated source/code closure to the immutable `baseline_commit`. The initial issue-start baseline was `777b082b0a3447c39205255312ec69f453e85e7a`; after storage recovery, the branch and final pair evaluation used then-current main `7319f888aa203228c4990c479d7291b1b78e262f`. Main later advanced to `ea8614305fbf1488a4ec32aecb7cd96e761635de`; all 39 pinned file blobs were compared across those commits and are identical. No reproduction was rerun at `ea861430`, so its frozen metrics are classified as `baseline`, not `current`. Earlier exploratory vintages retain their original receipts and remain excluded from the final acceptance pair. The runner verifies whole-file hashes against Git objects, verifies the materialized bytes supplied to historical readers, bounds each ordinary/decoded file to 32 MiB and the whole phase to 256 MiB, and captures the old programs' reads. The corrected producer's numerical functions are executed from their pinned bytes; its direct writer is never called. The old wrapper and producer run with virtual reads, writes, and deletions, so the old destination paths cannot mutate the retained packet. Generated legacy products are captured before the wrapper's expected cleanup.

Raw records are checked before mapping. The issue roster and consumed crosswalk each require 226 unique exact IDs. Each scoped row joins to the prior review, a historical geoBoundaries feature, the matching Atlas feature and parent, an OCHA ADM3 candidate, and its native ADM2/ADM1 parent codes and names. Duplicate, missing, and fabricated rows are tested with refreshed fixture counts and hashes. The pair verifier retains the 2,486 archived numeric row values and checks each exact key/value against the output; the evidence ledger records the reconciliation count and binds the final scores and aggregate claims without duplicating the archived row ledger. All 678 selected-pair scores, the 14 aggregate counts, and the mixed-winding, hole, and disjoint geometry controls are reconciled. Inputs use retained GeoJSON coordinates as WGS84 longitude-latitude; no coordinate transformation is performed. The runtime's configured PROJ data directory is recorded in each receipt but fails pyproj validation; this workflow uses no PROJ coordinate operation or grid.

The currently retained source packet describes the OCHA COD-AB as an INC-attributed operational reference published by OCHA/HDX under CC BY-IGO 3.0. Its exact retained package metadata was retrieved 2026-10-05; it marks the dataset fresh, gives annual update frequency and a 2026-10-30 due date, declares coverage through 2025-10-30, and records source boundaries as created/last edited 1987-08-22. The 10/58/360 tier roster and every adjacent native parent-code/name join are validated here. These facts do not establish legal boundary authority or a coordinate refresh after 1987. The retained WRI/INC comparison layer is CC-BY 4.0, was retrieved 2026-10-05, has 360 features while its metadata describes 359, has no `code_arr` values, and explicitly lacks legal validation. The retained geoBoundaries ADM3 file has 360 features, represents 2017 boundaries with a 2023 data update, and is ODbL 1.0. Its use here validates source-feature joins and repeats a historical candidate comparison; it does not resolve whether modern boundaries are legally current. Source meaning, vintage, license, retention and limitations remain documented in the pinned source inventory; no source question is upgraded by this mechanical erratum.

The issue-reported duplicate-crosswalk fixture is described as 263,846 bytes with SHA-256 `3dba096bc814c323f99ccc5a86a5e7a4c977a58b1f7e85f6332f6088107e0818`, but those exact bytes are not retained in the source packet. The successor constructs and hashes its own complete fixture by replacing the final crosswalk row with a deep copy of the first. It reports both values and does not claim the unavailable issue-reported byte hash was reproduced.

## Limits and handoffs

The 226 subjects are the exact bounded issue scope, not a whole-region certification. Spatial identity remains candidate evidence. Known low-overlap units, historical label differences, disconnected parts, and candidate parent-name discrepancies retain their prior uncertainty. The original #1128 audit remains `Incomplete`: affirmative MINAT institutional/count/region/decree and OCHA maintenance claims lack retained supporting originals or a usable GitHub-only restoration route. Separate legal-source work in #897 remains open. This packet does not authorize geometry changes, historical imports, publication, legal determinations, or closure of #897.

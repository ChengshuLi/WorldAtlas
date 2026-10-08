# #1431 execution record and resource bounds

Contract SHA-256: `2aa9ab4ea222fc7a00668e1306c9e4be15f15de943607979605d1d91068750b3`.

The exact source overlay producer is bounded to the complete 15 local-family components against all 99 original simplified administrative features (1,485 pair rows), with all nine contacts retained as context. Two independent full-scope runs and their directed controls completed on frozen code/input head `b91d38254bc7fb901fefcb6112f5878fbc52d463` in coordinated window `root-1431-b91d3825-20261008-03`. No commit occurred between the runs. The run outputs, controls, RSS samples and supervisor receipts are retained under this directory's `vintages/`.

The execution bindings are: custody vintage `custody-10`, preflight commit `dc95bba1a135ef52eb9bca95188583579278bf2a`, preflight execution-pins SHA-256 `72fc8fc16e4f7c60e9c8bf5c8fa0c0546cb3347fd0fb4fc63069674e6ff3d07a`, final execution-pins SHA-256 at the frozen run head `44277e23ed4ca052c681f92841a6b4b1f900e30a0cb45db376a491178bc3e9e4`, and input-pins SHA-256 `93467639bf9393aa36970ec5404fa695d3d7a4ae9f936013363cfb01ead8d539`. The custody preflight verified the 74 source/runtime inputs, 15 complete components, all 9 contact features, 41 KGZ and 58 TJK complete source features, runtime bundle and exact code bindings before any geographic operation. It used 213,863,483 of 268,435,456 phase bytes, reached 155,910,144 bytes RSS, and completed in 69.8 seconds with `geographic_operations: 0`.

Both full runs completed 1,485 component/source rows and 27 intersecting pairs. All non-admission source-result fields match; the differing `precalculation_admission` objects preserve the distinct fresh per-run resource snapshots. Normalized source-result SHA-256 with only that per-run object removed: `ae443f40e0e2be0c0b2f7fb6f97a5e37192e6c4349c5774cc21877ed502adfe0`.

| Run | Fresh input phase | Admission page-supply candidate | Pre-geometry RSS | Sampled tree peak | Producer prepublication RSS | OS child-lifetime RSS | Directed controls |
|---|---:|---:|---:|---:|---:|---:|---|
| `source-fitness-run-01` | 213,892,322 B | 1,473,216,512 B | 158,220,288 B | 149,127,168 B | 158,220,288 B | 158,220,288 B | pass |
| `source-fitness-run-02` | 213,892,322 B | 1,366,654,976 B | 168,247,296 B | 166,313,984 B | 168,247,296 B | 168,247,296 B | pass |

The unchanged admission floor was 1,342,177,280 candidate bytes (768 MiB process ceiling plus 512 MiB host reserve); each row's snapshot exceeded it. Both supervisor receipts report exit code 0, no stop reason, no live descendants after reap, and a 640 MiB sampled-tree stop threshold. Each control receipt records the positive exact-source predicate and passes all four negative controls. Source-product descriptor checks also reject wrong-prefix, foreign-origin, missing-product and reordered-product inputs. Per-run exact hashes and receipt values are in the respective `run-summary.json`, `control-receipt.json`, `supervision.json` and `publication.json` files.

```sh
set -e
BASELINE_COMMIT="$(git rev-parse HEAD)"
RUNTIME_PYTHON="/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12"
"$RUNTIME_PYTHON" research/geography/kyrgyzstan-tajikistan-gap-source-fitness-20261007/supervise_run.py \
  --repo . --baseline-commit "$BASELINE_COMMIT" \
  --vintage source-fitness-run-01 \
  --coordinated-window-id '<COORDINATOR_ASSIGNED_WINDOW_ID>'
"$RUNTIME_PYTHON" research/geography/kyrgyzstan-tajikistan-gap-source-fitness-20261007/supervise_run.py \
  --repo . --baseline-commit "$BASELINE_COMMIT" \
  --vintage source-fitness-run-02 \
  --coordinated-window-id '<COORDINATOR_ASSIGNED_WINDOW_ID>'
"$RUNTIME_PYTHON" research/geography/kyrgyzstan-tajikistan-gap-source-fitness-20261007/controls.py \
  --repo . --baseline-commit "$BASELINE_COMMIT" \
  --source-run research/geography/kyrgyzstan-tajikistan-gap-source-fitness-20261007/vintages/source-fitness-run-01 \
  --control-vintage source-fitness-controls-01
"$RUNTIME_PYTHON" research/geography/kyrgyzstan-tajikistan-gap-source-fitness-20261007/controls.py \
  --repo . --baseline-commit "$BASELINE_COMMIT" \
  --source-run research/geography/kyrgyzstan-tajikistan-gap-source-fitness-20261007/vintages/source-fitness-run-02 \
  --control-vintage source-fitness-controls-02
```

## Frozen resource bounds and forecast

- Exact preflight on commit `0b8380ce6af3205d8c170b5bcf5bf05c7cea096e` passed without geographic operations: 213,821,152 input bytes of 268,435,456 allowed; peak RSS 148,701,184 bytes; elapsed 59.1 s. This includes the JRC metadata/capture and cohort plan.
- Producer ceiling per full source run: 1,200 seconds, 768 MiB peak RSS, 256 MiB pinned input, 12 MiB producer output. Supervisor logs and samples reserve another 6 MiB plus 36 KiB per run; two runs reserve up to 24 MiB of producer outputs and 12 MiB plus 72 KiB of supervision evidence. Two controls reserve 2 MiB, each capped at 1 MiB.
- The full input/runtime/output/storage checks run in each producer process before constructing geometry. The fixed-byte OS snapshot records `vm_stat` page size and exact free, inactive, and speculative counts. Their byte sum is explicitly a page-supply estimate that includes reclaimable pages; it is not reported as guaranteed available memory. Admission requires at least 1,342,177,280 estimated bytes (the unchanged 768 MiB process cap plus a 512 MiB explicit host reserve).
- The pinned external supervisor samples the full child process-group/tree RSS every 0.1 seconds and terminates at 671,088,640 bytes (640 MiB), leaving 134,217,728 bytes below the unchanged 768 MiB limit. It also enforces the 1,200-second wall limit, a 1 MiB cap for each child log, a 4 MiB RSS-sample log cap, and a 13,000-sample limit. A run qualifies only when the external receipt passes, producer prepublication `ru_maxrss` and OS-reported child-lifetime `ru_maxrss` after reap each remain at or below 805,306,368 bytes, and the supervisor verifies no live process-group descendants remain. RSS polling is not an OS hard memory limit; the receipt states that explicitly. Controls bind the run outputs to the supervisor receipt and recheck every sample and hash.
- Current packet is admitted up to 1 GiB worktree; scratch cap 512 MiB; final evidence cap 512 MiB; disk admission reserves 2 GiB. Recheck free disk, all destinations and the fixed-byte OS snapshot in the assigned window immediately before each run.
- JRC metadata-only capture is 325,312 bytes; no raster pixel values have been read. The planned exact support covers 256 unique blocks / 687,297 encoded bytes / 67,108,864 decoded-byte upper bound after global deduplication. Ten separate cohorts represent 306 block memberships, 50 repeated memberships, 855,570 encoded bytes and 80,216,064 decoded-byte upper bound; each cohort is capped at 64 blocks / 16 MiB, with the largest currently 63 blocks / 15.75 MiB.
- These are transfer/decode upper bounds, not a measured wall-clock forecast. The producer's 1,200-second ceiling is the enforceable runtime limit; capture, decode and comparison wall time must be observed in the coordinated run. The four metadata ranges are the only current JRC bytes in the packet.

The JRC product is long-period occurrence-frequency context. Spatial block support does not establish pixel values, present water, physical class, candidate cause, boundary authority, or rightful assignment. The nine contacts are context only, not independent water controls. Candidate water status remains unverified, family cause unknown, assignment null, and authority/source fitness unapproved.

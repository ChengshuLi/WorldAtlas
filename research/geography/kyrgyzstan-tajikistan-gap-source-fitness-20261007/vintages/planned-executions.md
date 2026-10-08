# Prepared #1431 execution handoff

Contract SHA-256: `2aa9ab4ea222fc7a00668e1306c9e4be15f15de943607979605d1d91068750b3`.

The exact source overlay producer is bounded to the complete 15 local-family components against all 99 original simplified administrative features (1,485 pair rows), with all nine contacts retained as context. Two independent full-scope runs are prepared. The user/coordinator must supply a fresh coordinated memory-window ID after the current #1295 B build window releases; until then these commands are intentionally not runnable.

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
- The pinned external supervisor samples the full child process-group/tree RSS every 0.1 seconds and terminates at 671,088,640 bytes (640 MiB), leaving 134,217,728 bytes below the unchanged 768 MiB limit. It also enforces the 1,200-second wall limit, a 1 MiB cap for each child log, a 4 MiB RSS-sample log cap, and a 13,000-sample limit. A run qualifies only when the external receipt passes and the producer's own lifetime `ru_maxrss` remains at or below 805,306,368 bytes. RSS polling is not an OS hard memory limit; the receipt states that explicitly. Controls bind the run outputs to the supervisor receipt and recheck every sample and hash.
- Current packet is admitted up to 1 GiB worktree; scratch cap 512 MiB; final evidence cap 512 MiB; disk admission reserves 2 GiB. Recheck free disk, all destinations and the fixed-byte OS snapshot in the assigned window immediately before each run.
- JRC metadata-only capture is 325,312 bytes; no raster pixel values have been read. The planned exact support covers 256 unique blocks / 687,297 encoded bytes / 67,108,864 decoded-byte upper bound after global deduplication. Ten separate cohorts represent 306 block memberships, 50 repeated memberships, 855,570 encoded bytes and 80,216,064 decoded-byte upper bound; each cohort is capped at 64 blocks / 16 MiB, with the largest currently 63 blocks / 15.75 MiB.
- These are transfer/decode upper bounds, not a measured wall-clock forecast. The producer's 1,200-second ceiling is the enforceable runtime limit; capture, decode and comparison wall time must be observed in the coordinated run. The four metadata ranges are the only current JRC bytes in the packet.

The JRC product is long-period occurrence-frequency context. Spatial block support does not establish pixel values, present water, physical class, candidate cause, boundary authority, or rightful assignment. The nine contacts are context only, not independent water controls. Candidate water status remains unverified, family cause unknown, assignment null, and authority/source fitness unapproved.

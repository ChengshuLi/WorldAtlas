# Prepared #1431 execution handoff

Contract SHA-256: `2aa9ab4ea222fc7a00668e1306c9e4be15f15de943607979605d1d91068750b3`.

The exact source overlay producer is bounded to the complete 15 local-family components against all 99 original simplified administrative features (1,485 pair rows), with all nine contacts retained as context. Two independent full-scope runs are prepared. The user/coordinator must supply the coordinated memory-window ID after the #1295 B terminal; until then these commands are intentionally not runnable.

```sh
BASELINE_COMMIT="$(git rev-parse HEAD)"
RUNTIME_PYTHON="/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12"
"$RUNTIME_PYTHON" research/geography/kyrgyzstan-tajikistan-gap-source-fitness-20261007/producer.py \
  --repo . --baseline-commit "$BASELINE_COMMIT" \
  --vintage source-fitness-run-01 \
  --coordinated-window-id '<COORDINATOR_ASSIGNED_WINDOW_ID>'
"$RUNTIME_PYTHON" research/geography/kyrgyzstan-tajikistan-gap-source-fitness-20261007/producer.py \
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
- Producer ceiling per full source run: 1,200 seconds, 768 MiB peak RSS, 256 MiB pinned input, 12 MiB output. Two runs reserve up to 24 MiB. Two controls reserve 2 MiB, each capped at 1 MiB.
- Current packet is admitted up to 1 GiB worktree; scratch cap 512 MiB; final evidence cap 512 MiB; disk admission reserves 2 GiB. Recheck free disk, all destinations and system memory in the assigned window before either run.
- JRC metadata-only capture is 325,312 bytes; no raster pixel values have been read. The planned exact support covers 256 unique blocks / 687,297 encoded bytes / 67,108,864 decoded-byte upper bound after global deduplication. Ten separate cohorts represent 306 block memberships, 50 repeated memberships, 855,570 encoded bytes and 80,216,064 decoded-byte upper bound; each cohort is capped at 64 blocks / 16 MiB, with the largest currently 63 blocks / 15.75 MiB.
- These are transfer/decode upper bounds, not a measured wall-clock forecast. The producer's 1,200-second ceiling is the enforceable runtime limit; capture, decode and comparison wall time must be observed in the coordinated run. The four metadata ranges are the only current JRC bytes in the packet.

The JRC product is long-period occurrence-frequency context. Spatial block support does not establish pixel values, present water, physical class, candidate cause, boundary authority, or rightful assignment. The nine contacts are context only, not independent water controls. Candidate water status remains unverified, family cause unknown, assignment null, and authority/source fitness unapproved.

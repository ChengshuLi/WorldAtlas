# Mainland search: component bounds before exact work

The completed full-run reference spent 302.27 seconds generating hints and
1,017.88 seconds in the exact component-to-mainland search. Its mainland stage
was 2,261.22 seconds overall. The changes below preserve the selected WGS84
metric, category order, tie tolerance, source cells and regional decisions.

## Algorithm

* Find the globally closest representative once, instead of finding a separate
  closest representative for all six categories. A spherical tree supplies
  conservative candidates; WGS84 inverses still determine the winner and exact
  ties still select the lowest code. Stream the inventory in blocks and insert
  each physical root into SQLite only once.
* Bound the whole component using actual endpoints across all its physical
  runs. Its first northern cell is a valid but often very loose upper witness.
  The minimum of additional real cell-to-representative distances is still an
  upper bound, and prevents expensive searches across entire large islands.
* Treat the authenticated 1024-cell seed tiles as storage units. Build occupied
  128-cell spatial leaves in memory, clipping runs exactly at leaf boundaries.
  Their union is the original seed-cell set. Original tiles remain hash checked.
* First use cheap coarse category bounds. Pass only categories not excluded by
  those bounds into the fine index. An inconclusive certificate still invokes
  exact WGS84 search. Fine indexing and samples never supply final labels.

There are no artificial memory limits, cache-size ceilings or watchdogs.

## Complete global workload

The isolated reference is `worldatlas-optimized-full-run-20261107`, produced by
PR4 commit `88483e3`. The final search replay used the integrated PR4 source
after physical acceleration at `8cf9749` plus this change.

* Hints: **302.27 → 14.28 seconds, 21.2× faster**. All 457,889 root IDs and every
  hint byte were identical. The hint hash is
  `1cb57e0cfc2a6f7f2af69e864287308d276d9c170a3426faf4e7d9fa18143f3b`.
* Final production search, including a fresh spatial index: **72.25 seconds**.
  Index construction was 7.60 seconds and the complete search runner was 64.65
  seconds. Every one of the 457,889 component codes and all six recorded ties
  matched the reference exactly. Code-vector hash:
  `b1bd185ef7bc379f4ab44aeb4132260e56c101241afebf2a4790e7bc78f201a6`.
* Exact phase: **1,017.88 → 31.75 seconds, 32.1× faster**. Exact interval queries
  fell from **270,537 to 14,280**. Peak RSS for the complete search replay was
  570,924 KiB, measured without a memory cap.

A complete fresh mainland replay also rebuilt components, seed rasterization,
hints, Stage2 output and regional output. All six row/run streams matched
byte-for-byte, and all six ties were identical. Final regional run hash:
`c15da5eb03d7c938194ea056cdfaf092d90f18fa4ed604f42466951316ed0b20`.
That exploratory replay used fine bounds for every query and took 1,769.28
seconds. Its expensive certificate led to the final hierarchical design above.
The final design was then checked on the complete global search, rather than
claiming an unmeasured end-to-end time. Source production, output writing and
regional application are excluded from the 72.25-second kernel measurement.

Receipts are in `worldatlas-land-benchmark-20261107/{stage-timing,comparison}.json`
and `worldatlas-land-search-hierarchical-20261107/{comparison.json,progress.jsonl}`.
The reference checkpoint is used only as an expected result after the replay,
never as a witness, upper bound, stopping condition or assignment input.

## Reproduce

Use the same supported interpreter and dependencies as the pipeline, with
`PROJ_NETWORK=OFF` and temporary directories inside the persistent workspace.
Run heavy workloads sequentially, using new output directories.

```sh
python scripts/v7-pipeline/benchmark_land.py \
  --reference-run /workspace/worldatlas-optimized-full-run-20261107 \
  --out /workspace/new-mainland-replay
python scripts/v7-pipeline/benchmark_land_search.py \
  --reference-run /workspace/worldatlas-optimized-full-run-20261107 \
  --out /workspace/new-global-search-replay
```

The complete stage replay checks all component, Stage2 and final land streams.
The search replay independently verifies every seed tile and representative,
runs the same production index/search functions, and checks every root code and
tie. Regional policy execution remains a separate performance target.

Final integrated checks passed: 240 Stage2 tests, 9 hint tests and 66 pipeline
tests. Tests include exhaustive WGS84 comparisons, seam/pole cases, ties,
authenticated leaf coverage, stream-block boundaries and checkpoint recovery.

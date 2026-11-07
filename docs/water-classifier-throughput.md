# Shared coastal-center execution

Coastal tiles and shared named seas now use the same RLE scanline shoreline extractor. It visits changes in physical and final-land runs, expands only selected coastal cells, and retains the original four-neighbor geometry, wrapped row/column ordering and input validation. This removes the shared-sea dense padded-crop decoder and the duplicate coastal-only extractor.

Nearest-class certificates compute conservative lower bounds for every participant and one exact WGS84 candidate upper bound. That candidate is not assumed to be the ellipsoidal winner. A classification is accepted only if its upper bound excludes every competing class and omitted shore; otherwise all relevant exact minima are computed. Outside-band rectangles need no inverse calls. Near antipodes the chord itself supplies a conservative lower bound without inverse-sine sensitivity.

Exact minima batch independent queries and grow their ordered-neighbor prefixes until the omitted-center lower bound proves completeness. Wide unresolved searches retain the complete-input streaming fallback. There is no candidate-count cutoff. Row-interval classification also batches disjoint point-fallback leaves, sorting them before span reconstruction.

The existing numerical guards remain research assumptions, not a formal floating-point proof. Geography, tie priority, band thresholds, crop-edge failure behavior and output span semantics are unchanged. These changes do not approve a decision revision or publish a grid.

## Verification

Independent tests compare sparse extraction to dense four-neighbor masks over 100 wrapped, full-width and polar crops; compare batched minima to complete WGS84 searches; force a best candidate beyond 4,096 equal-chord neighbors; and exercise a spherical-nearest class that is not the WGS84 winner. Existing point, interval and rectangle tests remain applicable.

Targeted local-input measurements against PR4 commit `a601f853011337cc38cf1fba4b5975b87532b848` used the matched V8 physical/final-land streams. These are single-run microbenchmarks, not complete stage timings:

- Coastal tile 135, four 64-row groups, identical selected-cell results: same 32-cell rectangle setting, 0.126 s to 0.086 s classification.
- Eight Bering rows, identical preserved V8 assignment spans: existing interval path 0.925 s to 0.794 s; the point path took 6.484 s.
- A sparse shoreline prototype reproduced all 1,846,461 Bering centers exactly, reducing extraction from 21.01 s to 6.99 s. The final common extractor instead reuses the established coastal scanline implementation because that was faster than the prototype on coastal tile 135. Its full-stage timing remains to be measured.

A full pinned-input pipeline replay and fresh whole-stage timings are required
before claiming an end-to-end speedup from those microbenchmarks.

## Relevant-class exact fallback

Point fallback now computes complete exact minima only for classes whose
conservative lower bound can still affect the answer. A class beyond a known
candidate upper bound plus the tie tolerance and numerical guard cannot win or
join the tie. For coastal-band queries, classes beyond the band plus those
margins cannot change membership or an in-band winner either. The candidate
class is always retained, including outside-band points, so existing threshold
ambiguity and omitted-shore checks still run. Every relevant class retains the
complete shoreline search; no candidate count is capped.

The new tests compare output to complete all-center WGS84 searches near the
band, poles and antimeridian; force tolerance ties; preserve band ambiguity;
and verify that excluded distant classes do not invoke exact minima.

For comparable complete coastal timings, use the admitted coastal command from
a completed pipeline run. Run each checkout sequentially on the same local
inputs, with a workspace-local temporary directory and the same runtime:

    TMPDIR=/workspace/bench-tmp PROJ_NETWORK=OFF PYTHONPATH=/checkout/scripts \
      /usr/bin/python3 scripts/v7-pipeline/benchmark_coastal.py \
      --admitted /workspace/run/checkpoints/coast/attempt-ID/admitted.json \
      --reference /workspace/run/coast --code-root /checkout \
      --out /workspace/bench-candidate

The reusable driver includes startup and all complete-stage processing in its
wall time, excludes subsequent comparison work, and performs no downloads.
Verification checks all tile inventories, input identities and artifact hashes,
then compares every decompressed assignment byte. Results and environment are
recorded in fresh output; source and reference artifacts are never modified.

## Reuse sealed-batch shoreline geometry

The coastal batch builds its exact four-neighbor coastal-land geometry once
from the sealed physical/final-land inputs. The reusable index stores every
coastal span, rather than expanding all global cell centers. Each crop then
expands only its selected spans, preserving wrapped row/column order and the
same land categories. Standalone tiles retain the reference crop extractor.
This removes repeated physical-neighbor and land-category reconstruction for
overlapping crops without changing nearest-distance or band classification.

Tile/batch provenance pins the index helper. Batch reports record index span
count, coastal-cell count, storage and construction time. Tile reports also
separate shoreline extraction, nearest-index construction and classification
times. No cache limit or memory watchdog is imposed; storage scales with the
complete input's coastal spans.

Tests compare every returned center/category/vector against the common
reference extractor over400 randomized wrapped, full-width and polar crops,
plus explicit seam/pole and invalid-input cases. A tile-level test compares
all assignment bytes with and without the index.

Complete local-input measurement: 546 tiles, 5,173,897,169 physical-water cells,
and 2,116,758,035 decompressed assignment bytes reproduced exactly. Sequential
isolated process wall time fell from 1,142.289 s to 791.148 s, including the
50.194 s global-index construction: 1.444× faster, or 30.74% less time.
All 244 replay tests passed. The index retains 31,598,879 spans representing
49,401,908 coastal cells in 284,826,831 bytes of arrays.

A separate complete coastal trial of exact midpoint rectangles reproduced all
assignments but took 1,201.801 s, so that adapter was not adopted. This differs
from the strong benefit for shared named seas. See the complete protocol,
pins and timing breakdown in
[`benchmarks/coastal-shore-index-20261107.json`](benchmarks/coastal-shore-index-20261107.json).

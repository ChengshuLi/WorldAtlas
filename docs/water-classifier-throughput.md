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

A full pinned-input pipeline replay and fresh whole-stage timings are required before claiming an end-to-end speedup. No benchmark or local compatibility scripts are part of this change.

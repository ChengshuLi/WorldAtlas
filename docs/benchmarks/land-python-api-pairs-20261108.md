# Complete land Python-API kernel pairs

Both pairs used preserved, checksum-authenticated global inputs at
131,072 × 54,614. The exclusive window was coordinated with the physical and
water workers. Neither pair launched the user-owned full pipeline, changed
geographic decisions, authenticated the upstream provider, or promoted a
provisional land artifact to accepted/final geography.

## Seed raster and independent tile proof

The normal regional producer had recreated both exact pinned polygon files
with fresh closure checks. The seed builder consumed these polygons, current
component RLE and selected source rules. Archived seed labels were expected
outputs only, never a rasterizer input.

- Serial GDAL-Python/NumPy: 42.603970 s, 06:51:56.773085–06:52:39.377083 UTC.
- Nine-thread same implementation: 10.266617 s,
  06:52:39.377559–06:52:49.644195 UTC.
- Observed serial/parallel ratio: 4.149758×, about 75.9% less elapsed time.
- Complete rows SHA-256:
  18358e4b343ea1ba0a812439ce43d155b6e337cb177a53e41a6e95bb195f08e9.
- Complete runs SHA-256:
  a3a13634e58d413bc84251cb435a70025db845c1d74b4302e98e93e4eb6d2ec1.

Both full output streams and all root/category populations exactly match the
archived seed: 1,756,653,801 selected mainland seed cells. All 854 full-width
64-row strips retain the original affine arithmetic. Only entirely
polygon-independent strips can omit rasterization: 1,500 actual polygon burns
versus 1,708 possible burns. When any selected interval reads a polygon bit,
EVERY original polygon is burned in original order. Per-bit omission was
withdrawn after the hole/MultiPolygon exact-center regression exposed GDAL ADD
interactions; the complete run used the corrected implementation.

The independent Python verifier then authenticated all 2,139 tiles and
11,844,679 records against the freshly produced complete seed in 1.564819 s.
Its source SHA, exact manifest pin and UTC interval are in the
[verbatim seed receipt](land-python-seed-pair-20261108.json).
No custom compiled helper, ctypes bridge or subprocess ran.

This compares serial versus parallel use of the SAME Python-API algorithm.
It is not a controlled comparison against the archived 102.7 s custom-helper
run, and not a whole-land or end-to-end speed ratio. One serial-first pair does
not balance cache order.

## General numeric preflight prototype

The optional prototype replaces Python dispatch per interval with full-row
NumPy I/O and common endpoint/owner arrays. It checks every interval and retains
all coverage, seed placement, root/category completeness and exact population
contracts. Production still imports the existing preflight implementation.

- Current Python preflight: 22.688613 s,
  06:53:50.779974–06:54:13.468618 UTC.
- Numeric prototype: 16.329138 s,
  06:54:13.468979–06:54:29.798126 UTC.
- Observed reference/candidate ratio: 1.389456×, about 28.0% less elapsed time.
- All report fields match, including 1,984,469,039 physical land cells,
  457,889 nonseed roots, four selected seed roots and all six category totals.

The [verbatim coverage receipt](land-numeric-preflight-pair-20261108.json)
binds complete input/code hashes and both UTC intervals. This is one
reference-first coverage-only pair. Writer/search/seed production were not
included, and the prototype remains opt-in. The next general question is
whether batching several ordinary rows can remove remaining NumPy call
setup, before considering a production switch or the analogous writer path.

## Runtime and tests

Linux x86-64; `/usr/bin/python3` 3.13.5; NumPy 2.2.4; SciPy 1.15.3;
PyProj 3.7.1; GDAL 3.10.3; CPU affinity 0–8. The final merged source passed
346 stage2, 111 pipeline, 21 seed-producer and eight rasterizer test executions.
The suites include independent dense oracles, arbitrary root/bit order,
UINT32 boundary identities/width, empty rows, exact-center vertices, holes,
disconnected polygons, strip/concurrency variation, malformed streams,
corruption, no-overwrite and process/ctypes prohibitions.

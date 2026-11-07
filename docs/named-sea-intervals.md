# Exact nearest-shore region certificates

The shared SeaVoX basin builder classifies physical-water **cell centers** against
the complete set of four-neighbor physical coastal land-cell centers. Distances
remain WGS84 geodesic center-to-center distances. The participant priority and
tie tolerance come from the pinned decision snapshot. No water-path distance,
coastline approximation, candidate cap, or changed geography is introduced.

## Certificate

Let `d_C(p)` be the shortest WGS84 distance from query center `p` to a center in
participant class `C`. The triangle inequality makes every `d_C` 1-Lipschitz.
For a row interval, choose an actual middle cell center `m`. Every center in the
interval is within distance `r` of `m`, where a conservative upper bound is the
length of the constant-latitude ellipsoidal path:

`r = a/(1-f) * cos(latitude) * maximum_longitude_offset_in_radians + 0.01 metres`.

Here `a` and `f` are the WGS84 equatorial radius and flattening. The true prime
vertical radius never exceeds `a/(1-f)`, and a geodesic is no longer than this
latitude path. The unwrapped interval and middle center are chosen in integer
grid columns, including intervals crossing the canonical longitude seam.

At `m`, let `U` upper-bound one candidate class's distance and let `L_C`
lower-bound each competing class. The existing crop-boundary lower bound also
bounds any shoreline omitted from a wrapped index. If every competitor and the
omitted shore satisfy `U + 2*r + tie_tolerance < L`, the same candidate class
strictly wins at **every** interval center. This follows by adding `r` to the
winner's upper bound and subtracting `r` from the competitors' lower bounds.

Cheap spherical/chord lower bounds certify most intervals. If they overlap,
the builder computes complete exact WGS84 class minima at the midpoint. Their
millimetre-expanded bounds often certify a whole interval even when the looser
spherical bounds cannot certify its individual centers. The existing exact
minimum search proves exclusion of every omitted shore center; unresolved wide
searches stream the complete input. No nearest-neighbor prefix is a hard cap.

An interval that cannot be proved is subdivided. Small unresolved intervals use
the unchanged point classifier, including priority, tolerance, numerical
ambiguity checks and full-shore fallback. Missing classes or an interval outside
the indexed crop also use the full-shore-capable point path. Floating-point
guards make certificates conservative; they do not enlarge the decision's tie
tolerance or permit an approximate label.

The default rectangle execution engine extends the same proof
across both columns and rows. It intersects the complete selected row spans with
canonical source windows and streams consecutive 64-row groups. Selected cells
are never dropped at a window, tile or group edge. For a rectangle, its middle
latitude/longitude and extreme cell-center offsets give a conservative radius
by integrating the straight latitude/longitude segment with the largest WGS84
principal radius and largest parallel cosine in the rectangle. Subdivision skips
only regions containing no selected cells. Point fallback and strict tie rules
are unchanged. `--research-interval` retains the row engine and `--pointwise-nearest`
retains the original point engine. The producer records a distinct rectangle execution method and
helper hash; the consumer verifies these rather than relabeling row provenance.

Before an expensive exact midpoint query, both engines also test whether any
class could possibly certify the region. Its spherical nearest distance gives
both a lower and an upper ellipsoidal bound using the minimum and maximum WGS84
metric radii. If even the most optimistic gap is no larger than twice the region
radius plus tolerance, exact refinement cannot certify it, so subdivision proceeds
directly. The antipodal chord-only lower-bound branch instead uses a conservative
half-circumference upper bound. This gate removes work, never shoreline candidates.

## Reproducible full-input benchmark

`scripts/v7-pipeline/benchmark_stage.py` replays a recorded stage admission using
its original interpreter and input/options. It changes only the source checkout,
a fresh output directory and explicitly supplied additional arguments. It records
the command, source hash, environment, CPU affinity/quota and complete process
wall time. It installs no resource limits, memory caps, watchdogs or supervisors.
Run competing benchmarks sequentially on comparable resources.

`scripts/v7-replay/benchmark_named_basin.py` adds named-basin checks: identical
source/grid/raster metadata, every ordered assignment record equal to the saved
baseline, independently counted rows/spans/cells, decompressed byte hashes, and
the independent full raster-to-physical-water coverage verifier. Its report keeps
the baseline's original stage timing distinct from the candidate's new processing
time and full process wall time. Verification time is reported separately and
is not counted as builder processing. Inputs must already be local; the driver
does not download data. A saved baseline is never modified.

The interval execution method, helper/source hashes, software versions and
certificate accounting are carried in the basin manifest and checked by the
prefill consumer. This optimization does not accept or publish draft geography.

## Full Bering result, 2026-11-07

The original complete point-classification stage took **5,141.516 seconds**.
The complete row-interval stage with exact midpoint tightening took
**571.565 seconds** processing, **572.382 seconds** full process wall time:
**8.995 times faster**, including rasterization, shoreline extraction/indexing,
all classification, output compression and repeated input integrity checks.

All **43,945,230 water cells**, **5,010 rows** and **29,539 spans** matched the
original output. Both decompressed streams have SHA-256
`e9587d3e6f9e88a6f71db612dd35ffb22d791f06909ddaf1f45472ebc687c174`.
The independent complete raster-to-physical-water coverage check also passed
in 11.398 seconds, outside the processing measurement. Source, policy, physical
grid, final-land grid and raster bytes were unchanged. The baseline is the
original completed run, not a second timing trial; the candidate ran alone on
the same environment with the same interpreter/environment and one-worker
classification. These are full-input measurements, not sample extrapolations.

The [machine-readable report](benchmarks/bering-row-interval-20261107.json)
preserves the commands, hashes and resource context. Source polygon semantics
and geographic approval are separate from this exact regression check.

### Final rectangle default

The final default engine completed the same full Bering stage in **105.837
seconds** processing and **106.409 seconds** full process wall time: **48.58 times
faster** than the original 5,141.516-second point stage. An earlier complete 2D
trial took 117.386 seconds, with the same exact output. These are actual complete
stage timings, not extrapolations from selected rows or classification kernels.

All 43,945,230 cells, 5,010 rows, 29,539 spans and both compressed/decompressed
assignment byte streams matched the original. The complete independent coverage
check passed in another 11.558 seconds. The engine certified 43,925,062 cells in
rectangles, leaving only 20,168 point fallbacks and zero streamed full-shore
fallbacks. Every original input pin and raster byte was unchanged.

The [final machine-readable report](benchmarks/bering-rectangles-20261107.json)
also includes the exact builder/helper hashes and execution audit. The baseline
timing is still the original completed run, not a fresh isolated baseline trial;
the two 2D trials ran sequentially with other heavy benchmarks stopped.

The final code passed all 241 replay tests, including randomized independent
WGS84 checks, wrapped/missing-shore fallback, source masks, consumer provenance,
coastal bands, ties, interrupted batch recovery and composition. The test process
used a workspace-local `TMPDIR` and inherited `scripts`, `scripts/v7-replay` and
`scripts/v7-pipeline` on `PYTHONPATH` so subprocess-import tests see the same
modules. No benchmark ran alongside the tests.

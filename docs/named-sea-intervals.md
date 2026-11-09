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

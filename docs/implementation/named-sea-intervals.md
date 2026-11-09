# How we assign water in a shared sea

**TL;DR.** In a shared sea, assign each water cell to the continent with the nearest shore. The build assigns a whole block at once when it can prove the same continent wins throughout. Otherwise it splits the block and checks any remaining cells individually.

## Where this runs in the code

- The [basin builder](../../scripts/map-build/water/build_seavox_basin.py) reads the sea’s decisions and selects the engine.
- The [rectangle engine](../../scripts/map-build/water/rectangle_nearest.py) checks blocks and splits those it cannot assign.
- The [individual-cell check](../../scripts/map-build/water/wrapped_bounds.py) calls the [nearest-shore search](../../scripts/map-build/water/shared_nearest.py) and uses a [full-shore scan](../../scripts/map-build/water/streamed_shore_fallback.py) when needed.
- The [row-only engine](../../scripts/map-build/water/interval_nearest.py) implements the single-row reference method.

## How it works

### The assignment rule

When two or more continents share a named sea, each water cell goes to the continent with the nearest shore. The build considers only the continents listed for that sea.

It measures the shortest distance along the WGS84 ellipsoid from the center of the water cell to the center of a coastal land cell. A land cell counts as coastal if it shares an edge with a water cell. The sea’s decision record sets how close distances must be to count as a tie and which continent wins a tie.

### How the build speeds this up

1. Take a rectangle of water cells and check distances near its middle.
2. If one continent’s shore is far enough ahead to win everywhere in the rectangle, give all the selected water cells there to that continent.
3. If the result is uncertain, split the rectangle and try again. Check any cells that remain unresolved individually.

The shortcut gives the same assignments as checking every cell separately. For example, suppose two continents share a sea and one shore is 10 km closer at the middle of a rectangle. If every cell is within 2 km of the middle, the lead can shrink by at most 4 km. At least 6 km of the lead remains, so the same shore wins throughout the rectangle if the tie tolerance is less than 6 km.

## How we verify the result

Call the middle point `m` and let `r` be a conservative upper bound on the distance from `m` to any selected cell center in the rectangle. The nearest-shore distance for any continent can change by at most `r` between those points. That follows from the triangle inequality.

At `m`, let `U` be an upper bound on the candidate’s nearest-shore distance and `L` a lower bound on a competitor’s. The candidate wins throughout the rectangle if this is true for every competitor and any shore outside the local search window.

```text
U + 2 × r + tie tolerance < L
```

The two copies of `r` cover the worst case. The candidate’s shore could get farther away by `r` while the competitor’s shore gets closer by `r`. The strict inequality keeps the shortcut out of tie cases.

## Implementation details

- **Distance bounds.** The rectangle bound uses its midpoint, the farthest offsets in latitude and longitude, and conservative WGS84 radii along that path. The row-only version uses an actual middle cell and bounds the distance along that latitude. It uses the WGS84 equatorial radius divided by one minus the flattening as an upper bound on the radius of curvature, scales by the latitude cosine and longitude offset in radians, and adds a 1 cm numerical margin. Both versions handle the map seam.
- **Fast checks first.** Bounds based on spherical distances often settle the result. When those bounds overlap, the build first checks whether a more precise midpoint measurement could possibly establish a large enough lead. If it could, the build computes the exact WGS84 minimum distance at that point for any continent still in contention and expands the bounds by a millimetre. Near antipodal points, the chord-only lower-bound calculation uses half the maximum ellipsoid circumference as a conservative upper bound.
- **Fallback.** If the build still cannot rule out a closer shore outside the local search window after subdivision, it checks the unresolved cells individually. It also uses this check if the index lacks one of the continents. That check can scan the full shoreline. It retains the decision’s tie rules and handles numerical uncertainty.
- **Coverage.** The rectangle engine works within source windows in groups of 64 rows. It divides or skips a region only as needed and skips a region only when it contains no selected cells. Every selected cell is accounted for, including at window, tile, and row-group edges.

The rectangle engine is the default. The standalone builder also offers `--research-interval` to check stretches of a single row and `--pointwise-nearest` to check one cell at a time. The basin output records which engine ran and the hash of its helper code. The next stage verifies those records.

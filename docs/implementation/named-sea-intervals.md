# How we assign water in a shared sea

**TL;DR.** In a shared sea, assign each water cell to the continent with the nearest shore. The build assigns a whole block at once when it can prove the same continent wins throughout. Otherwise it splits the block and checks any remaining cells individually.

## Where this runs in the code

- The [basin policy](../../src/worldatlas/map_build/division/policies.py) prepares each basin's full scope and references. [Basin helpers](../../src/worldatlas/map_build/water/basins.py) discover participating owners from the current shores.
- The [rectangle engine](../../src/worldatlas/map_build/water/rectangle_nearest.py) checks blocks and splits those it cannot assign.
- The [nearest-shore search](../../src/worldatlas/map_build/water/shared_nearest.py) checks unresolved cells against the complete shared shoreline index.

## How it works

### The assignment rule

When two or more continents share a named sea, each water cell goes to the continent with the nearest shore. The build considers the continents whose physical shores border that sea in the current map. Basin claims include coastal cells. Coastal and basin rules use the same land ownership; their claims must agree wherever they overlap.

It measures the shortest distance along the WGS84 ellipsoid from the center of the water cell to the center of a coastal land cell. A land cell counts as coastal if it shares an edge with a water cell. The strictly smaller computed distance wins. Only exact equality uses the stable category-code order; there is no near-equality threshold.

### How the build speeds this up

1. Take a rectangle of water cells and check distances near its middle.
2. If one continent’s shore is far enough ahead to win everywhere in the rectangle, give all the selected water cells there to that continent.
3. If the result is uncertain, split the rectangle and try again. Check any cells that remain unresolved individually.

Coastal and basin claims run independently against the same ownership snapshot.
They reuse the same physical shores and distance indexes, and their overlapping
claims must agree. Basin query masks are prepared once. A basin with one eligible
owner uses direct assignment instead of distance searches.

The shortcut gives the same assignments as checking every cell separately. For example, suppose one shore is 10 km closer at the middle of a rectangle. If every cell is within 2 km of the middle, the lead can shrink by at most 4 km. At least 6 km of the lead remains, so the same shore wins throughout the rectangle.

## How we verify the result

Call the middle point `m` and let `r` be a conservative upper bound on the distance from `m` to any selected cell center in the rectangle. The nearest-shore distance for any continent can change by at most `r` between those points. That follows from the triangle inequality.

At `m`, let `U` be an upper bound on the candidate’s nearest-shore distance and `L` a lower bound on a competitor’s. The candidate wins throughout the rectangle if this is true for every competitor. The calculation uses every participating shore.

```text
U + 2 × r < L
```

The two copies of `r` cover the worst case. The candidate’s shore could get farther away by `r` while the competitor’s shore gets closer by `r`. The strict inequality keeps the shortcut out of tie cases.

## Implementation details

- **Distance bounds.** The rectangle bound uses its midpoint, the farthest offsets in latitude and longitude, and conservative WGS84 radii along that path. Bounds include numerical safety margins and handle the map seam. These margins can require more exact calculations; they never make unequal distances count as equal.
- **Fast checks first.** Bounds based on spherical distances often settle the result. When those bounds overlap, the build first checks whether a more precise midpoint measurement could possibly establish a large enough lead. If it could, the build computes the exact WGS84 minimum distance at that point for any continent still in contention and expands the bounds by a millimetre. Near antipodal points, the chord-only lower-bound calculation uses half the maximum ellipsoid circumference as a conservative upper bound.
- **Individual cells.** Unresolved cells use the complete shoreline index, with conservative candidate bounds followed by exact WGS84 distances. Missing participant shores stop the calculation. Strict distance comparison and exact-equality tie handling apply throughout.
- **Coverage.** The basin builder supplies source windows in ordinary row batches. It divides or skips a region only as needed and skips a region only when it contains no selected cells. Every selected cell is accounted for, including at window, tile, and row-group edges.

Tests compare the rectangle engine with independent
individual-cell calculations. The complete shoreline
index supplies individual-cell searches when a block cannot be certified.

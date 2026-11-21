# Physical shores and water distances

The [parent-division engine](../division/README.md) selects and consolidates water claims. This folder contains its reusable numerical helpers.

## Use

Run the [map builder](../README.md#use) with a parent whose rules assign water. The division engine calls these helpers and records the shoreline-edge counts used to identify basin participants.

## How it works

The common engine extracts shore geometry once, intersects those shore spans with current land ownership, and reuses filtered reference indexes. Coastal water uses the configured 22,224 m limit. Named basins use all shores of their bordering owners. Remaining water uses all eligible assigned shores without a distance limit. Land-only children are excluded from water-owner candidates using the entity's stored physical eligibility. Coastal and basin claims run independently against the same land ownership and must agree where they overlap.

Ocean areas are `assign_area` rules on one shared residual-water snapshot. Their `connected_to` links select components containing the explicit points stored in Neon, leaving enclosed pockets for `nearest_water`. Conflicting claims fail.

The rectangle shortcut uses the triangle inequality. If every selected cell center is at most `r` from the rectangle center, an owner's nearest-shore distance can change by at most `r` within the rectangle. A candidate with upper distance bound `U` at the center wins throughout if `U + 2 × r < L` for every competing owner's lower bound `L`. The candidate can get farther away by `r` while a competitor gets closer by `r`, so the strict inequality proves a winner for every cell. When the bounds leave the result uncertain, the engine splits the rectangle or checks individual cells.

## Code and tests

- `shore_index.py` and `shore_spans.py` extract physical land-cell centres sharing an edge with water. Longitude wraps; artificial parent edges and ownership boundaries do not create physical shores.
- `basins.py` clips a basin to physical water and counts adjacent owned shores. Discovery uses the full original basin before any ownership filtering.
- `shared_nearest.py` performs complete WGS84 point searches. Coarse real shore witnesses bound distant searches. When the tree cannot prove a winner from nearby candidates, the search carries its best exact distance into a scan of the full reference set. Exact distances decide ownership.
- [`rectangle_nearest.py`](rectangle_nearest.py) shares proven distance certificates over rectangles and falls back to complete point searches where needed. Cell counts use compact local prefix tables instead of strided whole-width scans. Coverage accounting is batched rather than repeated for every excluded rectangle.

Tests compare optimized calculations with complete independent distance searches, including dateline wrapping, exact ties, cutoff edges and omitted-shore proofs.

Run the [map-building suite](../README.md#code-and-tests).

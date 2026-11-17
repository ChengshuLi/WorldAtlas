# Physical shores and water distances

The [parent-division engine](../division/README.md) selects and consolidates water
claims. This folder contains its reusable numerical helpers.

- `shore_index.py` and `shore_spans.py` extract physical
  land-cell centres sharing an edge with water. Longitude wraps; artificial
  parent edges and ownership boundaries do not create physical shores.
- `basins.py` clips a basin to physical water and counts adjacent owned shores.
  Discovery uses the full original basin before any ownership filtering.
- `shared_nearest.py` performs complete WGS84 point searches. Coarse real shore
  witnesses bound distant searches; exact distances decide ownership.
- `rectangle_nearest.py` shares proven distance certificates over rectangles and
  falls back to complete point searches where needed.

The common engine extracts shore geometry once, attaches current land owners,
and reuses filtered reference indexes. Coastal water uses the configured 22224 m
limit. Named basins use all shores of their bordering owners. Remaining water
uses all eligible assigned shores without a distance limit.

Ocean areas are ordinary `assign_area` rules on one shared residual-water
snapshot. `nearest_water` completes cells still unowned afterward. Conflicting
claims fail; there are no ocean seeds or separate enclosed-water operations.

Tests compare optimized calculations with complete independent distance searches,
including dateline wrapping, exact ties, cutoff edges and omitted-shore proofs.

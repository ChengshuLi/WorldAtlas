# WGS84 center-to-center water research

This research-only candidate assigns shared-basin, coastal-band and multi-continent closed water by shortest WGS84 ellipsoidal geodesic distance from the water-cell center to a represented coastal land-cell center. A land cell is coastal when at least one of its four orthogonal neighbors is physical water; diagonal-only contact does not count. Longitude wraps. The coastal-band threshold and tie priority are supplied by the selected draft policy. This is a geometric modeling choice, not a claim that historical water maps used the same implementation or that the result is a legal maritime boundary.

`coastline_assignment` and `closed_water_assignment` require the version-2 methods, `distance: wgs84_ellipsoidal_center_to_center`, `ellipsoid: WGS84`, and `shore_geometry: physical_coastal_land_cell_centers_4_neighbor_v1`. Prior spherical-edge policies are rejected, not silently reinterpreted. A shared named-basin draft additionally requires the explicit `wgs84-coastal-4neighbor-center-v2` research method. Select and validate a new versioned policy before any research run. Old spherical results and partial outputs must not be resumed or claimed as equivalent to the new method.

All final distances use `pyproj.Geod` with the WGS84 ellipsoid. Unit-sphere indexing and the minimum WGS84 curvature radius are used only for conservative candidate and crop lower bounds; they do not decide the final distance metric. The numeric safeguards include a one-millimeter search-bound cushion and fail closed when crop sufficiency, a tie threshold or a band threshold cannot be established. The cushion is tested engineering evidence, not a formal proof of every floating-point operation. Verify source, physical grid, code and software versions in any future run. No global performance or map-equivalence claim is made.

The coast, named-basin and closed-water paths require fresh land/physical inputs, source pins, separate output paths and the existing draft/research gates. No previous ocean or continent labels are used for construction. Water output is not selected or published by these scripts alone.

Run focused synthetic checks using the project's Python environment with NumPy, SciPy and pyproj:

    python -m unittest -q test_wgs84_centers test_coastal_core test_closed_water_core test_streaming_closed_water test_coastal_tile test_shared_nearest test_seavox_basin test_coast_planner_integration test_prefill_plan


## Named-basin interval research mode

For shared basins, `build_seavox_basin.py --research-interval` can certify an entire row interval when conservative midpoint WGS84 bounds prove a unique nearest participant for every cell. Unresolved intervals are recursively split and their leaves use the existing certified point classifier and streamed full-shore fallback. Direct, single-participant basins do not use this mode. The default point method is unchanged.

Interval results have a distinct shore-method value, `execution_method`, source-code hash, helper-code hashes, runtime-library versions and certified-cell count. The interval path intersects the source raster with physical water by looking up RLE values only for source-mask cells; empty source cells do not need RLE lookup. The current planner, prefill and composition tools reject this new method and its interval markers until an interval-aware adapter is separately reviewed. Do not relabel an interval manifest to bypass that gate. Input, geometry, lineage, policy and independent source-coverage requirements remain unchanged.

The interval bounds use a 1 cm floating-point cushion and avoid certifying near-antipodal queries. This is an engineering guard, not a formal proof for every NumPy, SciPy or libm implementation. Randomized, tie, polar, antimeridian and true streamed-fallback tests are included in `test_interval_nearest.py`. Broader real-data comparison is required before changing the default or allowing the method into prefill.

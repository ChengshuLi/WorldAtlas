# WGS84 center-to-center water research

This research-only candidate assigns shared-basin, coastal-band and multi-continent closed water by shortest WGS84 ellipsoidal geodesic distance from the water-cell center to a represented coastal land-cell center. A land cell is coastal when at least one of its four orthogonal neighbors is physical water; diagonal-only contact does not count. Longitude wraps. The coastal-band threshold and tie priority are supplied by the selected draft policy. This is a geometric modeling choice, not a claim that historical water maps used the same implementation or that the result is a legal maritime boundary.

`coastline_assignment` and `closed_water_assignment` require the version-2 methods, `distance: wgs84_ellipsoidal_center_to_center`, `ellipsoid: WGS84`, and `shore_geometry: physical_coastal_land_cell_centers_4_neighbor_v1`. Prior spherical-edge policies are rejected, not silently reinterpreted. A shared named-basin draft additionally requires the explicit `wgs84-coastal-4neighbor-center-v2` research method. Select and validate a new versioned policy before any research run. Old spherical results and partial outputs must not be resumed or claimed as equivalent to the new method.

All final distances use `pyproj.Geod` with the WGS84 ellipsoid. Unit-sphere indexing and the minimum WGS84 curvature radius are used only for conservative candidate and crop lower bounds; they do not decide the final distance metric. The numeric safeguards include a one-millimeter search-bound cushion and fail closed when crop sufficiency, a tie threshold or a band threshold cannot be established. The cushion is tested engineering evidence, not a formal proof of every floating-point operation. Verify source, physical grid, code and software versions in any future run. No global performance or map-equivalence claim is made.

The coast, named-basin and closed-water paths require fresh land/physical inputs, source pins, separate output paths and the existing draft/research gates. No previous ocean or continent labels are used for construction. Water output is not selected or published by these scripts alone.

Run focused synthetic checks using the project's Python environment with NumPy, SciPy and pyproj:

    python -m unittest -q test_wgs84_centers test_coastal_core test_closed_water_core test_streaming_closed_water test_coastal_tile test_shared_nearest test_seavox_basin test_coast_planner_integration test_prefill_plan

The deprecated V2-baseline spherical coastal and land builders are retired rather than migrated. Other historical scripts and maps are not proof of compatibility. No real global water run is claimed.

# WGS84 local flow screen

`local_flow_screen.py` is an exploratory local terrain screen, not a certified watershed, river, ocean-boundary decision, or published map. It uses WGS84 ellipsoidal inverse geodesics between raster-cell centers for downhill slope ranking and outlet separation, and WGS84 direct geodesics for cross-section offsets. The original source line remains linear in the caller-selected projection; station fractions are measured using sums of WGS84 chords at most 100.01 m long; this is a numerical path-length approximation, not a formal error bound. A short projected-line tangent is converted to a geodesic bearing, so its direction is a local numerical approximation.

The optional `--line`, `--diagnostic-point` and `--basin-outlets` interfaces remain available. Outlet pairs and the nearest modeled transition use WGS84 distances between grid-cell centers. Earlier outputs produced by the planar version are historical research only and must be rerun before comparison.

Inputs must use matching north-up EPSG:4326 grids. A requested window outside the input grid is rejected before reading; the returned array dimensions must match the requested window. Invalid or masked cells remain barriers. Output is a research screen and must not be treated as a validated watershed without independent source, quality-mask and geographic review.

The existing real-rasterio synthetic integration test requires rasterio. `test_wgs84_mocked_io.py` independently exercises the numerical and window checks using a rasterio-interface stub; it does not prove real rasterio I/O. In the environment where this change was prepared, rasterio was not installed, so the real-rasterio integration test was not run.

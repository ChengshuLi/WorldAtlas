# Coordinate-linear source geometry and WGS84 distance

`geodesic_line.py` interprets input LineStrings as the original
longitude/latitude coordinate-linear segments. It does not replace those
segments with geodesic arcs. Distances between points use the WGS84 inverse
geodesic. Stationing sums inverse-geodesic chords along source segments split
at most one kilometre apart. Closest-point distance minimizes over bounded
subsegments and checks endpoints; it is a numerical search, not a proof of a
global minimum. A 0.02 m ambiguity margin is used for near-line, threshold and
nearest-geometry comparisons. Validate tolerance for the application. Uncut
antimeridian-spanning edges are rejected and must be split before input.

`grid_line_side.py` reports nearest source-line side and distance for grid
centers. It marks near-line centers and equal-distance nearest locations as
unresolved. A line can self-approach or reverse, in which case an oriented
side need not encode a meaningful geographic rule. This tool diagnoses an
existing geometry and does not select geography.

`geodesic_d8.py` follows strict downhill raster neighbors using WGS84 inverse
geodesic center-to-center distances. All 3×3 neighbors must be valid under
MSK 0 and STK > 0, and the original WGS84 rasters must be aligned. The program
reports pits, invalid neighborhoods, edges, or a step cap; it does not fill
pits or establish a real stream. Inputs and outputs remain research data.

These utilities depend on NumPy, pyproj and SciPy; D8 additionally needs
rasterio. Tests live beside the scripts and can be run with unittest discovery.

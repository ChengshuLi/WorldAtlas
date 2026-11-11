# Experimental WGS84 seeded-flow screen

`seeded_flow_basins.py` provides array-level research primitives. `flow_graph`
fills depressions with the local priority-flood routine and uses WGS84 inverse
geodesic distances between raster-cell centers to compute eight-neighbor
steepest descent. Equal-height flats follow the flood parent. `trace_to_seeds`
propagates two supplied seed labels upstream; unknown outlets and cycles are
unresolved, not assigned to the nearest seed.

The caller must supply aligned raster arrays, an unrotated north-up affine
transform, and an explicit CRS argument resolving to EPSG:4326. The function
rejects projected CRSs, non-finite affine coefficients, and extents outside
longitude/latitude bounds. Apply original quality masks before calling, construct seed
masks from validated sources, and handle overlaps as unresolved. All crop edges
and valid cells adjacent to invalid data are artificial outlets. Source DSM
artifacts, depression filling, sparse or incorrect seed streams, flow direction,
flat routing, mask gaps and crop size can materially affect the result. An
assigned model label is not proof of a stream, named basin, or selected boundary.

Requires numpy, scipy and pyproj. Run `python -m unittest discover -s
scripts/source-imports/caucasus-audit -p 'test_seeded_flow_basins.py'`. Input and output data
and geographic decisions belong in the project's data stores.

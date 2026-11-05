# Exploratory terrain joins

`terrain_join_proposal.py` proposes local pixel paths between each endpoint of
a supplied candidate LineString and a selected LineString. It is a research
screen, **not** a watershed delineator, source authority or a tool for
selecting a boundary.

The user supplies two WGS84 GeoJSON LineString geometries, an aligned original
one-arcsecond JAXA DSM/MSK/STK tile. The tool reads a bounded window around each candidate endpoint
and requires MSK 0 and STK > 0 across each 9×9 neighborhood. Dijkstra routing
compares WGS84 geodesic distance-only and two weights that penalize pixels below their local
9×9 mean elevation. The paths terminate at raster pixels touched by the selected
line. Their endpoints are pixel centers, and neither the small connection to the
exact input endpoint nor the connection to the exact selected line is produced.
The script refuses to overwrite an existing output directory.

```sh
python terrain_join_proposal.py --selected LINE.json --candidate CANDIDATE.json \
  --dsm DSM.tif --mask MSK.tif --stack STK.tif \
  --output-dir NEW_PRIVATE_DIRECTORY
```

The selected GeoJSON line retains its coordinate-linear geometry; its raster target is a touched-pixel approximation. Closest-point stationing is numerical, and ties are reported. The arbitrary terrain penalty, source surface errors, low stack counts,
unmapped streams, cropped search extent, flats and local minima can all affect
the result. A high pixel is not proof of drainage separation. Independently
test joins, continuity, surface conditioning, actual outlets, source lineage
and native grid impacts before proposing a decision. Keep geographic inputs
and output geometries out of GitHub, and retain source hashes and decisions in
their appropriate data stores.

Requirements: numpy, rasterio, scipy, shapely and pyproj. The synthetic unit test
is `python -m unittest discover -s scripts/caucasus-audit -p 'test_terrain_join_proposal.py'`.

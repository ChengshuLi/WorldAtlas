# Basin terminal screen

`basin_screen.py` is a research-only comparison of a supplied WGS84 GeoJSON
LineString with a supplied HydroBASINS shapefile. It samples the line in a
WGS84 geodesic distances, constructs perpendicular offsets, identifies
the uniquely containing polygons, and follows `NEXT_DOWN` to a terminal
polygon. Missing polygons, overlaps, broken chains and cycles are reported as
unresolved. Provide a source window large enough to contain all offset points;
the script stops if an offset lies outside it.

Install `pyshp`, `shapely >= 2` and `pyproj` in an isolated environment.
For example:

```sh
python basin_screen.py --line LINE.json --basins BASINS.shp \
  --bounds WEST SOUTH EAST NORTH \
  --source-bounds EXPANDED_WEST EXPANDED_SOUTH EXPANDED_EAST EXPANDED_NORTH \
  --spacing 500 --offset 100 --offset 500
```

Bounding coordinates and offsets must be chosen for the actual study area.
The line input is a GeoJSON geometry, not a Feature. Verify WGS84 source coordinates,
source hashes, source window and polygon topology separately. On curves the
normal is estimated from a finite local window; results depend on its width,
spacing and offsets. Boundary ties are reported unresolved. The
script does not assign outlet names, compute catchments, condition elevations,
or propose a replacement boundary. A different terminal is not proof of a
watershed, especially across narrow catchments, lumped coastal areas and
virtual links. Keep inputs, outputs and geographic decisions out of this
source directory.

Run the unit tests using `python -m unittest discover -s scripts/caucasus-audit`.

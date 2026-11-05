# OSM waterway graph screen

`osm_water_graph.py` reads a user-supplied OpenStreetMap XML extract and
builds a directed graph from complete river, stream, canal, drain and ditch
ways, following their stored node order. It offers an approximate first-contact
search for a supplied sequence of WGS84 longitude/latitude points, with explicit
WGS84 geodesic point-to-way and point-to-node thresholds. Incomplete ways are counted and
excluded. Named river tags reachable downstream from the chosen node are
returned; cycles terminate through a visited-node set. Matches near a threshold or with tied ways or nodes are reported unresolved. Closest-point searches are numerical and carry a 0.02 m screening tolerance.

This is research code. Proximity to a mapped way is not proof that a terrain
trace enters a real stream, and choosing a nearby node can change downstream
attribution. Names, directions, shared nodes and coverage can be incomplete or
wrong. A local extract can end before the true outlet. Verify source lineage,
OSM topology, identity against an independent named source, and the effects
of matching thresholds before drawing geographic conclusions. OSM
attribution and ODbL terms apply. Keep source extracts, coordinates and
outputs in the project's data stores.

Requires Shapely 2 and pyproj. Run synthetic graph and CRS validation tests
with `python -m unittest discover -s scripts/caucasus-audit -p 'test_osm_water_graph.py'`.

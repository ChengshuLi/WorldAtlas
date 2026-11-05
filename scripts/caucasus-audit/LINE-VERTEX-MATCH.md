# Source vertex comparison

`line_vertex_match.py` compares the coordinates of a supplied GeoJSON
LineString with one feature of a supplied GeoJSON FeatureCollection after
binary64 parsing. It checks the selected geometry's binary64 sorted-compact
GeoJSON hash and the source file's byte hash before reporting consecutive
forward and reverse exact-coordinate runs. Duplicate source coordinates are
reported as ambiguous. Output is written exclusively to a new private file.

Coordinate agreement is not proof of original construction, correct source
selection, a watershed, or historic raster equivalence. This tool does not
identify geometry intersections, compare near matches, establish joins, or
check shoreline clipping. Keep source files and geographic outputs in the
project's data stores. Use `--help` for parameters and run the synthetic
tests with `python -m unittest discover -s scripts/caucasus-audit -p
'test_line_vertex_match.py'`.

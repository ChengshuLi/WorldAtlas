# Empty MultiPolygon parts in containment

This code-only overlay applies to the existing source-negative research runtime. It permits a water-only part of a valid split MultiPolygon while requiring at least one land hit across the full geometry. The ordinary per-feature intersection path still rejects an empty feature. Whole-component center containment, boundary-center rejection, witness restrictions and source pins are unchanged.

Compose the four Python files over the corresponding source-negative runtime and its already-reviewed dependencies. Run `test_polygon_intersection`, `test_polygon_resolution`, `test_source_negative_resolution`, and the source-negative extent tests in the composed runtime. This overlay does not include or enable reef or administrative-group methods and is not a complete runtime by itself. It does not select any geography or publish a map. Parts outside the grid and ambiguous boundary-center cases continue to fail closed.

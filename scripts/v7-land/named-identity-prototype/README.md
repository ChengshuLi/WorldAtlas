# Named identity corroboration (research prototype)

This checker verifies that one pinned raw source point lies strictly inside a uniquely identified, named polygon feature from a separate pinned raw source. OGR/GEOS checks a valid 2D, non-antimeridian-crossing Polygon or MultiPolygon. It rejects duplicate IDs, wrong selected name or class, geometry hash mismatches, invalid geometry, boundary hits and outside points. Names, property fields, expected class and feature IDs are decision data; none is a geographic constant in code.

The named polygon corroborates the selected point only. It is **not** used as a physical land boundary, an exclusive island roster, or evidence that every cell of a connected physical component belongs to the named island. Generalized labels can overlap broader archipelago labels and can include neighboring land. The separately generated physical component still needs independent review. The checker does not authenticate source custody or select a decision; the adjacent point resolver verifies source/version/bytes and calls it only for the explicitly selected `source_point_named_region_component_v1` method. The revision-bound identity feature and its raw source must come from the selected export.

Run synthetic tests with the system GDAL/GEOS Python environment:

```
/usr/bin/python3 -m unittest -v test_named_identity.py test_identity_watch.py
```

The caller must hash-pin and recheck this code and both raw source files. The adjacent resolver invokes the checker in a separate process through `identity_watch.py`, with process isolation, a 120-second execution timeout and bounded request/output sizes. It does not measure or constrain process or host memory. The report records GDAL and GEOS versions; geographic truth and floating-point behavior are not established by a successful test. The Natural Earth source examples researched locally are new evidence, not a recovered historical V7 source.

Source CRS must be absent (RFC 7946) or explicitly recognized as OGC CRS84. Nested CRS declarations on the selected feature or its geometry are rejected. Named-identity claim traces include both normalized CRS labels and `source_crs_scope: collection_feature_geometry`; this does not inspect unselected features.

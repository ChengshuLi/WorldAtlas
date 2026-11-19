# Interpreted geometry

[`geometry.py`](geometry.py) contains `interpreted_geometry`. It saves reviewed WGS84 points and polygons from the construction record, such as label points and computation scopes.

The recipe supplies `source_ids` for the supporting evidence, `basis` to explain the interpretation, and `selections` pairing each `feature_id` with its `geometry`. The importer checks the cited IDs in Neon. The coordinates come from the recipe, so the command needs only `worldatlas-import --recipe CONSTRUCTION_ID`.

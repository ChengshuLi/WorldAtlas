# Archive-polygon all-center containment

This research-only method, `osm_land_archive_component_containment_v1`, reuses the pinned split-land archive extractor and authenticated component streams. It requires exactly one archive feature whose extracted geometry is a single valid Polygon, with no additional features or witnesses. It retains only current physical components for which every represented cell center is inside that polygon, and records partially covered components as excluded. It does not infer names, continental conventions, coastline identity, or historical equivalence from the geometry.

The source archive and physical mask may share lineage. The current-generation component IDs and diagnostic comparison labels are never selectors. A change in source bytes, physical component generation, or policy requires a new source, containment, conflict, and protected-witness review. Exact cell-center/boundary ambiguity and an empty fully contained selection fail closed.

The integrated runtime includes other previously reviewed local methods; this independent overlay does not authorize or include unrelated reef or administrative method changes. Test the exact candidate code and source before use, and publish only after independent review and fresh-head checks.

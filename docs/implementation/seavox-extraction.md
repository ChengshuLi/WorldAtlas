# Pinned batched SeaVoX extraction

The supported pipeline extracts all selected named-sea features with one
`extract_seavox_features.py` invocation rather than starting a separate archive
scan for every basin. The existing single-feature CLI remains a reference and
targeted-work interface.

The batch reads the same pinned ZIP and decision snapshot. It materializes the
validated shapefile once in workspace scratch, then removes that transient
materialization. It scans attributes with geometry ignored, maps the complete
selection to native FIDs, and reads only those selected geometries. OGR still
organizes polygons and transforms them into the same target CRS. No source simplification, reprojection
change, polygon repair, feature substitution or geographic decision is added.
Exactly one polygon must match every selected ID. All canonical geometry hashes
must match the snapshot before output creation. Duplicate/unsafe decision IDs,
mixed archive pins, missing features and changed inputs fail closed.

The serializer constructs coordinates at the reference writer's precision and
accepts them only when their canonical SHA-256 matches the decision-bound
geometry hash. Any representation mismatch uses the exact OGR GeoJSON writer
instead, then validates its hash. This removes the large geometry JSON round
trip without weakening the binding. Properties retain OGR serialization.
GDAL roundoff cleanup attribution is in `scripts/water/GDAL_FORMATTING_LICENSE.txt`.
`--scan-reference` retains the original filtered-scan batch engine for comparisons.

Each decision receives the same canonical `source.geojson` bytes and existing
`worldatlas-seavox-archive-extraction-v1` manifest contract. The final sorted
`batch-manifest.json` binds the archive, snapshot, revision, GDAL version, all
geometry/file hashes and per-decision manifests. The pipeline checkpoints the
whole directory, verifies every output on resume and preserves incomplete
attempts without reusing or overwriting them. No cross-run unpinned cache exists.

The batch's `processing_elapsed_seconds` covers the complete extraction,
validation and serialization. Per-decision elapsed fields measure only their
file serialization inside that batch; they must not be added as separate archive
scan durations. Pipeline water timing includes the complete batch command once.

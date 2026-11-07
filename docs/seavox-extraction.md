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
GDAL roundoff cleanup attribution is in `scripts/v7-replay/GDAL_FORMATTING_LICENSE.txt`.
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

## Complete-selection benchmark

Run `scripts/v7-pipeline/benchmark_seavox.py` with a completed supported pipeline
run containing the original individual extraction checkpoints:

    /usr/bin/python3 scripts/v7-pipeline/benchmark_seavox.py \
      --reference-run /workspace/runs/reference \
      --code-root /workspace/WorldAtlas \
      --out /workspace/benchmarks/fresh-seavox-batch

The driver retains the original interpreter and source pins. It writes only a
fresh candidate directory and records source/code hashes, command, runtime
context and full process wall time. Temporary files stay in its workspace-local
scratch directory. It adds no resource caps, supervisors or watchdogs.

Verification is outside candidate processing time. Every selected canonical
feature file must match the original checkpoint bytes and every per-decision
scientific provenance field must match. Only elapsed-time fields may differ.
The reference's summed individual command durations are recorded separately: those
durations came from concurrent basin/coast work, so their ratio to a new isolated
batch is not a controlled full-pipeline wall-clock speedup. Run heavy tests and
benchmarks sequentially.

## Complete 92-feature result, 2026-11-07

The complete indexed batch took **81.961 seconds** process wall time, including archive
validation/materialization, OGR extraction, canonical serialization and input
rechecks. All **92 selected features**, **182,644,857 canonical feature bytes** and
every per-decision scientific provenance field matched the completed supported
pipeline's individual extraction checkpoints exactly. All 92 geometry candidates
matched their bound hashes, so this selection needed no OGR geometry fallback.

The original concurrent run recorded **4,312.713 seconds** summed extraction
command intervals. The earlier materialized filtered-scan batch took 166.449
seconds and a direct-ZIP batch took 172.780 seconds, both with identical outputs.
The indexed batch is 2.03 times faster than the complete materialized batch;
the original summed intervals establish removed repeated work, not a controlled
full-pipeline wall-clock speedup. No new full-pipeline trial is claimed here.

The final batch spent 2.724 seconds materializing the archive, 71.626 seconds
indexing/selecting/decoding and certifying geometry, and 6.103 seconds serializing
all canonical feature files. The geometry-free scan indexed all 249 source
records in 0.041 seconds. Complete timing includes the remaining work rather
than reporting only the index kernel. All 65 focused checks passed before timing,
including full-feature reference parity, projected coordinates, duplicate/missing
IDs, forced serializer fallback, and interrupted pipeline checkpoint recovery. After rebasing onto the latest
PR4 code, all 91 extraction and pipeline checks passed in 22.862 seconds, and
every measured executable source hash still matched.

The [machine-readable report](benchmarks/seavox-batch-20261107.json) preserves
the complete feature hashes, source/code pins, normalized commands, timings and comparison. Machine-specific
workspace paths are represented by relocatable role labels in the public report.

# Pinned batched SeaVoX extraction

The supported pipeline extracts all selected named-sea features with one
`extract_seavox_features.py` invocation rather than starting a separate archive
scan for every basin. The existing single-feature CLI remains a reference and
targeted-work interface.

The batch reads the same pinned ZIP and decision snapshot. It materializes the
validated shapefile once in workspace scratch, then removes that transient
materialization. Its OGR selection is
the union of the decision-bound numeric feature IDs; target CRS, GeoJSON driver
and coordinate precision are unchanged. No source simplification, reprojection
change, polygon repair, feature substitution or geographic decision is added.
Exactly one polygon must match every selected ID. All canonical geometry hashes
must match the snapshot before output creation. Duplicate/unsafe decision IDs,
mixed archive pins, missing features and changed inputs fail closed.

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

The complete batch took **166.449 seconds** process wall time, including archive
validation/materialization, OGR extraction, canonical serialization and input
rechecks. All **92 selected features**, **182,644,857 canonical feature bytes** and
every per-decision scientific provenance field matched the completed supported
pipeline's individual extraction checkpoints exactly.

The original concurrent run recorded **4,312.713 seconds** summed extraction
command intervals. A first direct-ZIP batch took 172.780 seconds with identical
outputs. These totals establish removed repeated work, not a controlled
full-pipeline wall-clock speedup.

The measured final batch spent 2.058 seconds materializing the archive, 140.925
seconds in OGR selection/JSON decode, 4.674 seconds binding geometries and 17.158
seconds serializing the canonical feature files. The remaining OGR cost is
reported rather than hidden by a partial or kernel-only timing.

The [machine-readable report](benchmarks/seavox-batch-20261107.json) preserves
the complete feature hashes, source/code pins, commands, timings and comparison.

# Mixed land research runtime

This directory preserves the exact mixed source-resolved land runtime used for the verified draft-22 research build. The sibling directory names are retained because the coordinator locates reviewed modules relative to its own path and verifies their SHA-256 digests before use. `SHA256SUMS` records the copied Python files. It includes the imported stage-2 validation dependencies, point and identity adapters, and OSM geometry extractors used by the coordinator.

This is code preservation, not an accepted geography release. No source datasets, snapshots, credentials, decisions, output grids, or geographic records are included. A real run requires independently obtained and validated private inputs, a source-based decision snapshot, the exact stage-2 approval closure, and a guarded process supervisor. Missing inputs or mismatched code pins must fail closed. The repository does not supply a preconfigured real-world run.

The small synthetic checks can be run with GDAL Python bindings, NumPy, SciPy and pyproj available:

```sh
cd scripts/v7-land/research-mixed-runtime/stage3-mixed-leeward-full-20261105
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 -m unittest -q \
  test_decision_contract test_entry_evidence test_full_coverage_policy \
  test_label_containment test_label_contracts test_mixed_claims test_mixed_driver \
  test_polygon_intersection test_polygon_loader test_polygon_policy \
  test_polygon_resolution test_polygon_source test_protected_witness \
  test_shared_coverage_index
```

The tests are synthetic and do not establish source rights, whole-component geographic identity, historical source equivalence, or correctness of a particular map.

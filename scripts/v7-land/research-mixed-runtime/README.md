# Regional land assignment

`stage3-mixed-leeward-full-20261105/apply_selected_mixed.py` builds the regional
land assignments from the current mainland streams and selected regional
snapshot. It resolves named points, source polygons and regional policies
against components produced by the same run. The
[V8 runner](../../v7-pipeline/README.md) prepares the request and code pins.

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

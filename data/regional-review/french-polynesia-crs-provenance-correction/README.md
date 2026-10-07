# French Polynesia RGPF evidence correction

This source-only packet corrects CRS provenance and quantifies a documented operation scenario for the five subjects in `RESEARCH.md`. It does not approve their geography or choose a production transformation.

From repository root, install the pinned tool versions in an isolated scratch environment (Node 24.19.0, Mapshaper 0.6.121, Python 3.12.14, NumPy 2.3.5, Shapely 2.1.2, pyproj 3.7.2 / PROJ 9.5.1 with EPSG database v11.022). Make the runtime available on `PATH` and the Python packages plus repository `scripts` on `PYTHONPATH`, then run:

```sh
python3 data/regional-review/french-polynesia-crs-provenance-correction/reproduce_crs_sensitivity.py
node scripts/evidence-quality.mjs data/regional-review/french-polynesia-crs-provenance-correction/evidence-quality.json
```

The reproduction checks exact archive/PRJ hashes, pinned baseline outputs, assignment controls, parent IDs, raw baseline reproduction, CRS operations and area sensitivity for all five subjects. It writes disposable geometry intermediates to a system temporary directory and the deterministic result ledger to this packet. Run it twice and compare the result hash recorded in `reproducibility-validation.json`. See `SOURCES.md` for retrieval, license, restoration and source limitations.

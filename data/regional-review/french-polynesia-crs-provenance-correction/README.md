# French Polynesia RGPF evidence correction

This source-only packet corrects CRS provenance and quantifies one documented operation scenario for the five subjects in `RESEARCH.md`. It does not approve their geography or select a production transformation.

From the repository root, use Node 24.19.0 and Python 3.12.14. Install the pinned Python packages and Mapshaper into the packet's disposable scratch area:

```sh
mkdir -p .scratch/french-polynesia-1294/mapshaper
python3 -m pip install --target .scratch/french-polynesia-1294/python numpy==2.3.5 shapely==2.1.2 pyproj==3.7.2
npm install --prefix .scratch/french-polynesia-1294/mapshaper --ignore-scripts mapshaper@0.6.121
```

Make Node 24.19.0 available on `PATH`, then run the following commands. The script locates Mapshaper at `.scratch/french-polynesia-1294/mapshaper/node_modules/mapshaper/bin/mapshaper` by default; use `--mapshaper-js PATH` to override that location. Python dependencies and the repository `scripts` directory must be on `PYTHONPATH`.

```sh
PYTHONPATH=.scratch/french-polynesia-1294/python:scripts python3 data/regional-review/french-polynesia-crs-provenance-correction/reproduce_crs_sensitivity.py
node scripts/evidence-quality.mjs data/regional-review/french-polynesia-crs-provenance-correction/evidence-quality.json
```

The reproduction checks exact archive/PRJ hashes, pinned baseline outputs, assignment and axis-order controls, parent IDs, raw-baseline reproduction, CRS operations and area sensitivity for all five subjects. Intermediate shapefiles and exported geometries go under `.scratch/french-polynesia-1294/`; only the deterministic result ledger is written into this packet. Run the reproduction twice, then compare `shasum -a 256 data/regional-review/french-polynesia-crs-provenance-correction/crs-sensitivity-results.json` with both identical hashes in `reproducibility-validation.json`. See `SOURCES.md` for source retrieval, license, restoration and uncertainty details.

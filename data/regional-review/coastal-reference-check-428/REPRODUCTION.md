# Reproduce issue #980 county checks

Run from repository root in the exact baseline checkout recorded in `scope.json` (commit `c42f4b7465964245ecbcd8eed4961eb76af3106b`). The geometry program loads Atlas features using `git show` at this immutable commit and reads the retained 2018/2025 source responses in the read-only #428 packet plus the eight-record 2026 response in this directory. It fails if the exact eight IDs are missing or duplicated.

## Environment and commands

Use Python 3.12.14 with the versions pinned by the parent packet's `source/reproduction-requirements.txt` (NumPy 2.3.5, Shapely 2.1.2, pyproj 3.7.2, PyShp 2.3.1, certifi 2026.7.22) and Node.js 24 for receipt reproduction. Geometry results can be regenerated with:

```sh
python3.12 -m venv .venv-geography
./.venv-geography/bin/python -m pip install -r data/regional-review/regional-review-528e53393a4376b4/source/reproduction-requirements.txt
./.venv-geography/bin/python data/regional-review/coastal-reference-check-428/reproduce.py
```

The program writes `runs/eight-county-comparison.json`, from the retained source bytes. Its equal-area overlays use EPSG:6933 and longitude/latitude source coordinates, matching the #428 comparison method. Source geometries are not edited. Invalid TIGER geometries remain invalid in the source and are passed to `make_valid` only in memory for overlap triage. A shared `worldatlas-evidence-geometry-v1` longitude/latitude axis-order control is run and recorded; the shared land-only area helper is not applied to the Census water-inclusive county polygons. Positive and negative measurement controls are retained in `runs/positive-control.json` and `runs/negative-control.json`: unchanged coastal source geometries must yield IoU 1, and an intentionally swapped lon/lat control must differ from the correct EPSG:6933 coordinate by over 1,000 km.

Validate issue pins, exact eight subject IDs, baseline bytes, source receipts, and output hashes with Node.js 24:

```sh
node scripts/evidence-quality.mjs data/regional-review/coastal-reference-check-428/evidence-quality.json
node scripts/check-handoff-scope.mjs --branch geography/coastal-reference-check-980-20261005-r1 --base origin/main --pr-body-file /tmp/worldatlas-980-pr-body.md --issue-file /tmp/worldatlas-980-issue.json
```

The first command checks file descriptors and exact baseline pins. The second is run with the current API-fetched issue JSON and the actual proposed PR body during pre-merge checks; no fabricated issue fixture is substituted.

## Retained source responses

- `source/census-2026/eight-counties.geojson` and `counties-layer-metadata.json` are the exact HTTP response bodies from the URLs in `retrieval.json`, retrieved 2026-10-05. `source/fetch-eight.mjs` records the exact query construction and verifies the expected eight GEOIDs and metadata vintage before it writes.
- `source/georgia-law/` retains a concise CC0 statutory-text excerpt for O.C.G.A. §§36-1-1, 36-1-2, 36-3-1 and 36-3-25, plus restoration instructions and exact hashes/times of the original section HTML responses; the annotated full HTML is not redistributed. These sections establish general county-boundary law and process, but do not replace the exact local Acts or a recorded dispositive survey. `source/census-change-notes/` retains original Georgia Census change-note files for 2011–2013, 2014–2020, and 2021–2025. `retrieval.json` records each retrieval URL, time, response size, and SHA-256. The authoritative landing page and 2025 TIGER/Line Technical Documentation are retained under `source/authorities/`; exact hashes and status are in that directory's `retrieval.json`.
- The 2018/2025 TIGERweb original responses and their metadata/receipts remain in the parent #428 evidence directory. They are deliberately referenced as read-only originals rather than copied or edited here. GeoBoundaries 2018 source bytes, catalog-vs-source hash lineage, public-domain metadata, and restoration instructions are also retained there.

Network retrieval reproduces a later service response, not the historical 2026 bytes. Use the retained exact response and hash to reproduce this packet's reported findings. A response that later changes must be retained as a new dated vintage, not silently substituted.

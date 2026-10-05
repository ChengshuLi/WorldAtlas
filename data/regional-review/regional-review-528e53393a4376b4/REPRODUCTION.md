# Reproduce the #428 evidence packet

Run from the repository root on a current checkout of this packet. The measurements are pinned to current-main commit `bfa1c56ef72c1bc3a9d1fcf8263d073a966bf46f` in `reproduce.py`; the issue's original v3/v5 workload pins remain recorded in `scope.json` and were not replaced.

## Environment

- Python 3.12.14
- `numpy==2.3.5`
- `shapely==2.1.2`
- `pyproj==3.7.2`
- `pyshp==2.3.1`
- `certifi==2026.7.22`
- Node.js 24 is needed only for the source retrieval/restoration scripts.
- The geographic positive/negative controls use `scripts/evidence/geometry.py` version `worldatlas-evidence-geometry-v1`. Overlap screening itself is planar equal-area IoU in EPSG:6933.

```sh
python3.12 -m venv .geo-review-venv
.geo-review-venv/bin/python -m pip install -r data/regional-review/regional-review-528e53393a4376b4/source/reproduction-requirements.txt
.geo-review-venv/bin/python data/regional-review/regional-review-528e53393a4376b4/reproduce.py --output-dir runs/reproduced
```

`--output-dir` is relative to the packet directory, must not exist, and may not resolve outside the owned directory. The script refuses a changed source hash, altered issue scope, missing or duplicate identity, duplicate partition membership, missing parent, wrong current source cohort, mismatched source counts, or broken positive/negative controls. It reads immutable Atlas inputs with `git show` at the pinned baseline. It does not fetch data, write outside the packet, repair retained geometries, or edit Atlas geography.

## Retained sources and checks

The national GeoBoundaries 2018 ADM2 GeoJSON and metadata, GeoBoundaries LFS pointer and immutable commit are under `source/`. `source/verify-geoboundaries-restoration.mjs` re-fetches the pinned upstream object in memory, then verifies HTTP response bytes against both the retained file and LFS pointer; its exact date, resolved URL, hash and byte count are in `source/geoBoundaries-restoration.json`.

Census TIGERweb layer/query responses for Georgia and Kentucky (2018 and 2025) and the 2018 county CBF ZIP are retained under `source/census-2018/` and `source/census-2025/`. Their exact URLs, descriptions, counts, dates, sizes and SHA-256 digests are in `retrieval.json` sidecars. The 2018/2025 state-filtered TIGERweb query returns 279 records each. The CBF response is generalized cartographic reference only. Official Census reference pages and the public-access policy are retained under `source/authorities/` with gzip byte and decompressed source-body hashes.

The original result files in `runs/archived-pre-430-baseline-65f7/` and the earlier initial/review/verified output directories are preserved historical work products, not the current final measurements. `runs/packet-nine/` and `runs/packet-ten/` are the final reproducibility pair. Their three JSON outputs are byte-identical; the exact files and hashes are listed in `runs/validation-controls.json`. The initial and archived results agree numerically, but their older generation did not run the final shared-helper and source-completeness controls.

The row classification `justified` covers identity, county tier, state parent, unique Census identity crosswalk, and absence of the stated diagnostic triggers. It does not establish boundary law, every island or shoreline, source completeness for legal purposes, or regional approval. `insufficient-evidence` records unresolved comparison screens or invalid reference geometry. A threshold hit is not a correction finding.

## Source restrictions and restoration

The GeoBoundaries upstream metadata declares Public Domain; Census is a U.S. federal source. Other official state-hosted source material is cited with exact response hashes and dates; verify its current terms before republication. The Georgia 2025 constitution PDF did not return bytes to the local retriever (HTTP 403); it was inspected through the web PDF text interface. `source/authorities/georgia-constitution-restoration.json` records that limit and the exact restore URL. No PDF body hash is claimed.

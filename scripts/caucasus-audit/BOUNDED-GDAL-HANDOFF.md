# Bounded Caucasus source-to-GDAL handoff

This is a fixture test, not a map rebuild, real physical closure proof, or proof that the candidate follows the correct watershed. The recipe is guide-derived and has not been selected in Neon. Do not write unused data to Neon. Run in a fresh Linux/GDAL environment with `pyshp`, Shapely 2, pyproj and the GDAL Python bindings; the existing region builder is `scripts/v7-land/mainland-seed-l2/regions.py`.

PR4 branch head when this handoff was prepared: `2bf97aab2afddde93e503802921bb20218631a7e`. All paths below are under `scripts/caucasus-audit/` at that commit:

| Code file | SHA-256 |
| --- | --- |
| caucasus_effective_snapshot.py | `4199325a6f6eddd5b89f2141c74555d49a74d16612ba169b347cb2a9dca4779f` |
| caucasus_seed_gate.py | `0e24958d3825f15cc58544d9f45b74f4c8cee05d9c7a80c8fed185dd56843317` |
| caucasus_source_assembly.py | `e6f7cb0da8306bc4944d9313631e96c53a43aa6306634e2a357fa98118504d79` |
| caucasus_compact_selectors.py | `615e5ea1a73f9f918b56fa1f7ac579b73e1974ea16277f1734b2fa2400fb90ea` |
| caucasus_selector_recipe.py | `39bd0fe6ec53037cde6d045a8701dfd39b7185beb1e0c26921856fb2b026b2b8` |
| caucasus_selector_replay.py | `e671edeceadfad6ef734ea814f2d4359ce60057edaaf2cd64b998e021eac4e23` |
| caucasus_unmatched_edge_screen.py | `7ed358da98c50c9faaff09f5fd674b259d675b3887c7545faaeaf16c44838a0f` |
| test_caucasus_gdal_handoff.py | `7bd3bf83d6c60b03894082e17d71983462edbb12724e61529815e5cade1afca5` |

Obtain and verify the provider source bytes already in R2:

* `sources/hydrosheds/hydrobasins/standard/europe/level-12/v1c/hybas_eu_lev12_v1c-21797d53e079.zip`, SHA-256 `21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03`.
* `sources/trubetskoy/7aa03ec54a262e8e97e8273f60621c530ec4e998/asia_europe_border.geojson`, SHA-256 `c9d56b1291522573fbb8b0baa1a39cecfd192eda8f5e51650b24f562d13688e6`.
* Export the current selected Caucasus LineString from the intended Neon snapshot. Its canonical binary64 sorted-compact GeoJSON SHA-256 is `9f4ae3bc778ebbcd0258a19868acf0fa655763f5e849361196160fb4289c0d52`. Authenticate the snapshot independently; a JSON label is not authentication.

The compact recipe is currently only a local research artifact on the Mac (`/tmp/caucasus-selector-runs.json`), SHA-256 `59cae33e287b029465b27110057cc8f06d2dcdf982186b13815cca8f8bbb961c`. It is not on PR4, R2 or Neon. It can be regenerated in a fresh temporary work directory from the selected guide and raw sources as follows; use new output paths:

```sh
cd scripts/caucasus-audit
# Set absolute paths to already verified read-only files and an empty work directory.
HYDRO_ZIP=/path/to/hybas.zip
AUTHOR=/path/to/asia_europe_border.geojson
SELECTED=/path/to/selected-caucasus.geojson
WORK=/path/to/empty-work
unzip -p "$HYDRO_ZIP" hybas_eu_lev12_v1c.shp > "$WORK/hydro.shp"
python caucasus_unmatched_edge_screen.py --selected "$SELECTED" --shp "$WORK/hydro.shp" --output "$WORK/edge-screen.json"
EDGE_SHA=$(sha256sum "$WORK/edge-screen.json" | cut -d' ' -f1)
python caucasus_selector_recipe.py --selected "$SELECTED" --shp "$WORK/hydro.shp" --edge-screen "$WORK/edge-screen.json" --edge-screen-sha256 "$EDGE_SHA" --output "$WORK/recipe.json"
python caucasus_compact_selectors.py compact --input "$WORK/recipe.json" --input-sha256 c2107838b8dde06ff65a3ef61a7a15234137dc16a966fe2155edfac50f69a8d0 --output "$WORK/compact.json"
sha256sum "$WORK/compact.json"
python caucasus_source_assembly.py --decisions "$WORK/compact.json" --decisions-sha256 59cae33e287b029465b27110057cc8f06d2dcdf982186b13815cca8f8bbb961c --hydro-zip "$HYDRO_ZIP" --author "$AUTHOR" --selected "$SELECTED" --output "$WORK/derived.geojson"
CAUCASUS_DERIVED_GEOJSON="$WORK/derived.geojson" PYTHONPATH=".:../v7-land/mainland-seed-l2" python -m unittest -v test_caucasus_gdal_handoff
```

Expected compact recipe hash is `59cae33e287b029465b27110057cc8f06d2dcdf982186b13815cca8f8bbb961c`; derived LineString hash is `2f2f6c6777fe080fcbf13a526caad22b7b883fc982d3ff0492b91e082d6f06b6`. The test prints a bounded fixture region hash and must pass the actual GDAL region builder's validity, exact join, trace and hash checks. The synthetic route/checker do not validate a real water closure. The script emits no seed or map files. Intermediate reproducibility depends on library versions; a pin failure needs investigation, not a relaxed check.

The active seed gate requires a pinned snapshot containing the recipe under the proposed source-assembly field, so use an explicitly synthetic copy for a bounded integration test; never label that fixture an authenticated current Neon export. A real selected snapshot and full stage-2 orchestrator integration remain separate work. The real orchestrator independently validates traces against the original snapshot and cannot accept the changed boundary/region hashes until its validator and provenance contract are updated and reviewed.


## Linux builder result

The Linux builder reported that this bounded test passed 1/1 in 0.517 s using GDAL 3.10.3 and GEOS 3.13.1. The fixture region geometry SHA-256 was `5d5c8c71464fef3a5d02c85206489eef426e7264ae8a4f44c9cbad3aa9512a24`. It verified the handed-off recipe digest `59cae33e287b029465b27110057cc8f06d2dcdf982186b13815cca8f8bbb961c` and derived GeoJSON digest `2f2f6c6777fe080fcbf13a526caad22b7b883fc982d3ff0492b91e082d6f06b6`. The closure and checker were synthetic; received geometry was used as input. This does not independently test the raw-to-line reproduction, validate actual water closure or run the seed compiler. No map was rebuilt.

The builder has GDAL on system Python and cached Shapely on a different Python, but the reported environments did not yet supply all pyshp/Shapely/GDAL dependencies together. The source-assembly step and this GDAL region test can run as separate processes under separately pinned Python environments: the assembler needs Shapely, pyshp, pyproj and SciPy; the bounded region test needs GDAL and the standard-library-only gate module. This split does not eliminate the need to verify each output and its source pins independently.


## Fresh local source replay

A fresh macOS run re-extracted the pinned HydroBASINS SHP and regenerated the edge screen, expanded recipe, compact recipe and derived GeoJSON using Python 3.7.3, pyshp 2.4.2, Shapely 2.0.7, pyproj 3.2.1 and SciPy 1.7.3. The expanded recipe SHA-256 was `c2107838b8dde06ff65a3ef61a7a15234137dc16a966fe2155edfac50f69a8d0`; regenerated compact and derived files matched the handoff byte-for-byte and had the pinned hashes above. This is a fresh rerun on the same host and selected guide, not an independent geographic assessment or a Linux source-reproduction result.

For a bounded Linux replay, check whether the Shapely-capable Python also has pyshp, pyproj and SciPy. If it does, run the source assembly in that Python and the GDAL region fixture in the GDAL-capable Python; verify the same intermediate hashes between processes. If any dependency is absent, name the exact package and Python environment instead of substituting a received derived file as source reproduction.


## Optional isolated Linux dependency handoff

A private Library archive `caucasus-linux-py312-dependencies.tar.gz` (ID `libfile_eb456da65e9081919f91287c738aea83`, SHA-256 `662d35a3948aa3969e199db06e4bae0198e4c487376953dc1f8205cbb7f6408a`) contains:

* Pure-Python PyShp 2.4.2 `shapefile.py`, SHA-256 `f936765fc0627158310b72975d5f30b3a761973683c6d2753a13aa066f37d74b`, with its MIT license. The file was copied from the local installed distribution and compared byte-for-byte with the [upstream 2.4.2 release source](https://github.com/GeospatialPython/pyshp/blob/158be67/shapefile.py).
* The [official PyPI PyProj 3.7.2](https://pypi.org/project/pyproj/3.7.2/#files) CPython 3.12 manylinux x86-64 wheel, SHA-256 `1edc34266c0c23ced85f95a1ee8b47c9035eae6aca5b6b340327250e8e281630`, matching PyPI's published hash. It requires Linux x86-64, CPython 3.12 and glibc ≥2.28; verify compatibility before use. The wheel includes its license.

The archive's README describes an offline, temporary target-directory setup and requires checking `certifi`, Shapely and SciPy separately. Do not install into a system interpreter. This was not tested on the Linux builder, and PyProj 3.7.2 differs from the macOS replay's 3.2.1; differing PROJ/GEOS versions may change numeric output. Recompute and compare all recipe and output hashes rather than presuming equivalence. No package is a raw map source or a selected Neon input.

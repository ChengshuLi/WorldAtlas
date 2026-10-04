# Bolivia portion reproduction follow-up (#675)

This packet repairs the reproducer/verifier for the nine exact physical fragments listed in #675. It is evidence and reproducibility work only. It does not change hierarchy, geometry, administrative ownership, historical claims, shared boundaries, source packets, publication, or imports.

## Immutable inputs and complete scope

The reproduction reads ordinary Git blobs from baseline commit `df7f37ac91f6c3897ad4d23cfb166bc308a1c5ef`. It pins the world index, hierarchy, containing `data/geography/part-2.json`, exact #594 scope, the complete retained #490 assessment, original #594 overlay result and producer, original source registry, both source archives and all four retained source metadata files. It scans every one of the 36 part paths referenced by the pinned world index, records each Git blob ID, byte length and SHA-256, and requires each assigned subject to occur exactly once. All nine complete parent chains are checked against the pinned hierarchy and prior row-level assessment. The existing unresolved settlement, named-land/remainder, political-ownership and historical-distinction findings are carried forward per subject without being upgraded or reinterpreted.

The scope is exactly:

- Nine `atlas:physical:*` subjects in `evidence-quality.json`.
- Their two complete 2015 predecessor ADM2 polygons: Cordillera (`80513517B19404624083023`) and Velasco (`80513517B10383084964738`).
- Seven complete mapped RESOLVE ecological polygons: ECO_IDs 476, 504, 523, 529, 567, 569 and 584.
- All 36 unordered fragment pairs, plus the two predecessor-union calculations.

The previous output `data/regional-review/regional-supplement-bolivia-ecoregion-roles-2026/derived-portion-audit.json` remains untouched. The new packet compares every JSON value and records any differing JSON Pointer. The pinned run currently records semantic equality: 9 fragments, 2 predecessors, 7 ECO_IDs and 36 pairs; the two internal neighbor graphs each contain 9 edges. The two independent full runs have matching canonical SHA-256 values. These results reproduce a geometric calculation; they do not establish that the Atlas units should be administrative provinces or that source lines are legally authoritative.

## Fail-closed behavior

Each SQL query must return one record with every exact selected alias once. Missing rows/fields, duplicate aliases/rows, `NULL`, malformed values and nonfinite numbers stop before output creation. Non-neighbor pairs produce an explicit numeric zero from a `CASE` branch only when the measured boundaries are spatially disjoint; the code never converts missing or null query output to zero. All inputs are hash-checked from the immutable commit before calculation. New results are written through the shared exclusive-vintage helper beneath this owned directory; check mode is read-only.

The negative controls cover missing, null, malformed, duplicate and nonfinite SQL results; duplicate or missing subjects; changed descriptors; a wrong containing part; and attempts to overwrite an existing output. The overwrite control confirms the old bytes remain intact.

## Source record, dates and limits

- [geoBoundaries / GeoBolivia 2015 ADM2 source](https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/BOL/ADM2/geoBoundaries-BOL-ADM2.geojson): the inherited metadata says the layer was updated 2023-01-19 and built 2023-12-12, labels its 110 features ADM2, attributes the underlying data to GeoBolivia, and states Public Domain/free access. Raw compressed and decompressed hashes and retained metadata are in the original #490 packet. That packet records HTTP 403 at the official GeoBolivia catalog endpoint; there is no independent current administrative crosswalk here.
- [RESOLVE Ecoregions / Esri service](https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/Resolve_Ecoregions/FeatureServer/0): vintage 2017, layer last edit 2022-01-27, exact seven-feature query retrieved 2026-10-03. The retained item and feature metadata state CC BY 4.0. Raw response and metadata hashes, attribution and the exact query receipt remain in #490.

Both original source archives are read from their lawful retained locations under `data/regional-review/regional-review-2d6fa291e9384c2f/sources/`; no source is copied, refreshed or replaced. The geographic methods preserve original invalid polygons and use `ST_MakeValid` only in private temporary overlay calculations. Areas are planar equal-area km² in EPSG:6933, edges are metres, and values are scale/precision diagnostics. The prior packet's explicit source, settlement, detached-land, water and neighboring-border uncertainty remains in the row-level inherited assessment; no new source coverage is inferred.

## Reproduction

From repository root with Python 3.12 and GDAL/OGR available:

```sh
python research/geography/bolivia-portion-reproduction-followup/build_packet.py --check --vintage 20261004-validated
python research/geography/bolivia-portion-reproduction-followup/test_negative_cases.py
python research/geography/bolivia-portion-reproduction-followup/verify_packet.py
node scripts/evidence-quality.mjs research/geography/bolivia-portion-reproduction-followup/evidence-quality.json
```

To create another result, choose a new vintage and run `build_packet.py --create --vintage NAME`. Existing output vintages are immutable and creation refuses overwrite. This packet is not a regional approval, boundary correction, or authorization for historical imports.

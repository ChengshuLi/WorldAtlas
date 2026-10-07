# Guinea-Bissau gap source-fitness research

This packet preserves the complete accepted component and contact scope for issue #1416. It reconstructs original custody geometries, joins all current route rows, compares each component and contact with the pinned full and policy-selected simplified GNB ADM2 products, and samples two retained ESA WorldCover tiles. The exact scope and full rosters are captured in `scope.json` and `sources/issue-1416.json`.

## Results

Generated counts and contact vertex diagnostics are listed in [`summary-table.md`](summary-table.md) and bound to individual metrics in `evidence-quality.json`. Per-subject and per-source-feature results are in `vintages/source-fitness-run-20261007-k/topology-relations.csv`; exact intersections are retained in `intersection-geometries.geojson`. Current contact geometries differ topologically from both source products. Full and simplified products have matching feature IDs and names, but their geometries are not topologically equal or coordinate-identical. Vertex counts and coordinate precision are diagnostics, not positional-accuracy estimates.

Original component geometries are in `component-features.geojson`; component-to-fragment identity/hash bindings are in `fragment-bindings.csv`; all current administrative-binding route records are in `component-route-rows.json`. The preserved historical observation remains an exact, separately retained row in `legacy-observation.json`. Its surface status is unverified, its recorded parent mapping is not legal authority, and cause remains unknown.

The selected administrative source is the pinned 2017 geoBoundaries GNB ADM2 product. The baseline registry selects its simplified URL by replacing `.geojson` with `_simplified.geojson`, as verified against the pinned administrative selector code. The baseline also retains the full product. Both products contain the same 39 shape IDs and names but different geometries. Metadata records OpenStreetMap/Wambacher, ODbL 1.0, source data updated 2023-01-19, and file built 2023-12-12. No positional accuracy is reported; GeoJSON has no explicit CRS member, and this analysis interprets coordinates as WGS84 longitude/latitude. Historical processing endpoint identity is not established by matching IDs and names.

The retained WorldCover inputs are official N09W018 tiles for 2020 V1.0.0 and 2021 V2.0.0, nominally 10 m, in EPSG:4326 on a 1/12,000-degree grid, with CC-BY 4.0 terms. Their bytes, metadata, and product-year tags are verified. Local staged-file timestamps are recorded; original HTTP retrieval timestamps and headers were not preserved. Pixel-center class counts describe product classifications only. They are not independent physical truth, and different algorithm versions mean this pair does not support temporal-change inference.

## Limits and unresolved work

Independent appropriate physical/water evidence and independent historical physical evidence were not obtained for this packet. The two WorldCover years share a classification product lineage and do not satisfy that independent-source requirement. The administrative source and prior #472/#812 evidence are not physical or legal authority. The 36-versus-39 Guinea-Bissau sector-count discrepancy remains unresolved; #812 SALB terms are restricted to non-commercial use, and no SALB geometry or overlap result is reused here.

Seasonal/coastal and mangrove water, tides, classification omissions, border uncertainty, source mismatch, temporal mismatch, and physical cause remain unresolved. Absence of a mapped class or administrative boundary does not establish dry land, cause, or territorial owner. Source fitness and physical authority remain unapproved. This is a partial research packet; it proposes no geometry/topology repair, boundary assignment, import, release, or publication.

## Reproduction and controls

From the repository root, using Python with NumPy, Rasterio/GDAL, Shapely/GEOS installed:

```sh
python -I research/geography/guinea-bissau-gap-source-fitness-20261007/reproduce.py --repo . --run-name NEW-RUN-NAME
python -I research/geography/guinea-bissau-gap-source-fitness-20261007/reproduce.py --repo . --controls --run-one source-fitness-run-20261007-k --run-two source-fitness-run-20261007-l --controls-name NEW-CONTROLS-NAME
node scripts/evidence-quality.mjs research/geography/guinea-bissau-gap-source-fitness-20261007/evidence-quality.json
```

The two independent complete data runs match byte for byte. Positive and negative controls cover exact rosters, source-byte and raster-metadata mutations, contact/source joins, nonvacuous class counts, topology classes, coordinate identity, and safe refusal to overwrite an occupied vintage. Receipts and generated run outputs are under `vintages/`.

## Sources

- [ESA WorldCover data access](https://esa-worldcover.org/en/data-access) and the [2021 product user manual](https://worldcover2021.esa.int/data/docs/WorldCover_PUM_V2.0.pdf).
- [Pinned full geoBoundaries GNB ADM2 product](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/GNB/ADM2/geoBoundaries-GNB-ADM2.geojson) and its [simplified product](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/GNB/ADM2/geoBoundaries-GNB-ADM2_simplified.geojson).
- Prior research references: [issue #472](https://github.com/ChengshuLi/WorldAtlas/issues/472) and [issue #812](https://github.com/ChengshuLi/WorldAtlas/issues/812). They are reused only for recorded source and identity findings.

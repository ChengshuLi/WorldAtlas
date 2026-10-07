# Portugal–Spain source-gap families: source-only research

This packet records source retrieval and bounded diagnostics for the complete pinned scope: **52 families, 70 components, and 57 contact IDs**. The complete source index and public-scope reconstruction are in [`inputs/`](inputs/); [`outputs/source-status-matrix.json`](outputs/source-status-matrix.json) joins every scoped family and component to the available source evidence.

The retained [`inputs/public-scope-body.md`](inputs/public-scope-body.md) is the pre-issue scope draft captured as provenance. Issue [#1274](https://github.com/ChengshuLi/WorldAtlas/issues/1274) is the current work authorization and final acceptance contract.

All component water, ice, cause, ownership, and historical classifications remain **unknown**. No boundary edit or release certification is proposed. Source contacts, overlaps, and raster observations are research diagnostics only.

## Administrative inputs actually consumed

The pinned baseline source registry and exact original payload descriptors are preserved in `inputs/complete-input-index.json`.

| Input | Recorded vintage | Features | Original bytes | SHA-256 | Recorded license |
| --- | --- | ---: | ---: | --- | --- |
| geoBoundaries ESP ADM3 simplified product | 2018 | 8,205 | 18,613,175 | `e5bfa1c3889ea763ca2bb82c7f1e8ff9eff715dcb99ce405293a03de7ac85862` | CC BY 4.0 |
| geoBoundaries PRT ADM2 simplified product | 2020 | 311 | 387,331 | `f7a9143190715b85812b03617adc4879898b8c6a6789b9c9732c9705ea6c21ac` | CC0 |

These are the administrative products Atlas recorded as consumed. Their simplified geometry is not interchangeable with unsimplified upstream files, and a recorded source-year claim does not establish a historical effective date for any component. Current MAPA service metadata leaves copyright/terms fields blank; no geometry license was established for the recent feature snapshot.

Both complete source products were reassembled from their pinned raw-byte shards and checked against the original-file byte count and SHA-256 before overlay. All 70 components were compared with all 8,205 ESP polygons and all 311 PRT polygons using EPSG:6933 equal-area intersections. The Spanish product has positive-area intersections with 65 components (116 component/feature pairs); the Portuguese product has positive-area intersections with 60 components (78 pairs). No individual component is fully covered by the union of either complete simplified source product. This is a geometric comparison of the actual consumed inputs, not an owner assignment or a verdict that every uncovered portion is water.

## Source retrieval

### MAPA agricultural-comarca layer

The [official MAPA MapServer layer 2](https://sig.mapa.gob.es/arcgis/rest/services/25830/comunComarcasAgrarias/MapServer/2) was captured as a recent current-service snapshot. The layer reports 339 object IDs. All 18 scoped `atlas:district:ESP-*` contact IDs joined by their numeric suffix to 17 unique current features; two contact IDs alias one current feature. The 18 historical Atlas-imported source byte streams are still missing. The current geometry response is not evidence of the historical import bytes, its date, or its license. A full-layer geometry query returned a service error; only the bounded target geometries were captured. Raw metadata, response headers, joins, and geometries are retained under `sources/mapa/`.

### APA WFD river network

The official APA WFS returned 1,428 records for the full envelope of the 70 components, captured in bounded pages with an exhaustion request and a second hit-count request. A complete line overlay finds 74 distinct WFD features intersecting 35 components. These are WFD planning river-line features (2015–2021 context), not measured wetted widths, water-surface polygons, or a complete land/water inventory. Separate HTTP requests were not transactional. Captures and pagination details are under `sources/apa-wfd/`.

The WFS capabilities state `Sem restrições` for fees and access constraints. The current machine-readable [catalog API record](https://dados.gov.pt/api/1/datasets/6543c7f7b801ee975665fca5/) lists the license as `notspecified` and was last updated 2025-03-11; it identifies the same WFS endpoint. A separate official catalog search record for a related INSPIRE listing reports CC BY 4.0, while an older catalog listing reports License Not Specified. Because the current API record does not specify a reuse license and catalog records conflict, this packet records APA reuse terms as unresolved rather than treating access constraints as a license. Captured capabilities, schema, and catalog API JSON/headers are retained locally.

### MITECO 2022–2027 planning data

The [official PHC download page](https://www.miteco.gob.es/es/cartografia-y-sig/ide/descargas/agua/masas-de-agua-phc-2022-2027.html) advertises water-body polygons and hydrographic-network products and permits free use with attribution: `Fuente: «© Ministerio para la Transición Ecológica y el Reto Demográfico».` The linked `.lyr` files are styling files, not datasets. The official dataset endpoints returned an HTML anti-automation challenge form, so no vector data were acquired. The challenge was not bypassed. Page, responses, and headers are retained under `sources/miteco/`.

### JRC Global Surface Water monthly history

The official [JRC data-access page](https://global-surface-water.appspot.com/download) and [2024 Data Users Guide v5](https://storage.googleapis.com/water-world/downloads_ancillary/DataUsersGuidev2024_v.5.pdf) document the product, code meanings, temporal scope, and attribution. All 24 monthly-history v1.5 GeoTIFFs for 2024 in tiles `10W_30N` and `10W_40N` are captured under `sources/jrc/monthlyhistory-v1_5-2024/`; their exact URLs, byte lengths, hashes, and TIFF tags are recorded in [`monthlyhistory-v1_5-2024-capture.json`](sources/jrc/monthlyhistory-v1_5-2024-capture.json).

The 24 files total **94,801,565 encoded bytes**; the largest is 19,949,439 bytes. This is within the ordinary 32 MiB per-file and 256 MiB batch source limits. Each first-resolution image is 40,000 × 40,000 unsigned 8-bit pixels (1.6 GB when expanded), stored in 1,024 × 1,024 Zstandard-compressed tiles with TIFF Predictor 2. Processing decoded only the **552** bounded internal tiles intersecting the pinned geometry windows (578,813,952 expanded bytes in total), not the full images. The tile windows use the exact baseline component geometries, whose selected-scope extract and hash are retained under `inputs/`.

The source guide assigns monthly-history values `0` = no observations, `1` = observed and not water, and `2` = water detected. Across pixel centers inside 69 sampled components over the 12 months, the diagnostic counts are 2,397,688 code-0, 17,837,166 code-1, and 3,314 code-2 pixel-months. Ten components in nine families include at least one center with a water detection in at least one month. One component has no source-grid pixel center at this resolution. These are pixel-center counts, not area measurements or whole-component classes. Code 0 and all unsampled or partial-cell remainder stay unknown; code 1 for a month does not establish dry ground. A positive detection is dated surface-water context only.

The current MAPA layer snapshot contributes 17 distinct target polygons for 18 contact IDs. Its full bounded overlay intersects 69 components in 79 component/feature pairs; its current-feature union fully covers none of the components. This recent, undated agricultural-comarca layer cannot replace the missing historical imports, and its metadata does not establish a geometry license. It is not a physical land/water source.

JRC describes the 2022–2024 extension as Landsat Collection 2, notes that its registration relative to Collection 1 can vary spatially and reach or exceed one 30 m pixel, and limits Monthly History v1.5 to 2022–2024. This product is therefore current seasonal context, not a historical substitute for the 2018/2020 administrative sources. The source is free of charge without use restriction; products should cite the JRC paper and use the attribution `Source: EC JRC/Google`.

## Scope-wide reading

- [`outputs/jrc-2024-component-month-summary.json`](outputs/jrc-2024-component-month-summary.json) contains bounded monthly code counts for each component and family, including the complete contact crosswalk.
- [`outputs/administrative-source-overlays.json`](outputs/administrative-source-overlays.json), [`outputs/apa-wfd-line-overlays.json`](outputs/apa-wfd-line-overlays.json), and [`outputs/mapa-current-snapshot-overlays.json`](outputs/mapa-current-snapshot-overlays.json) retain the complete geometry comparison details and source limits.
- [`outputs/source-status-matrix.json`](outputs/source-status-matrix.json) includes every family and component in the pinned rosters. All 52 family cause statuses and all 70 component water, ice, ownership, and historical statuses remain unknown; `boundary_edit` is false throughout.
- The 18 distinct missing MAPA historical contact records map to 17 recently captured service features. Repeated family references are listed per family and must not be mistaken for 59 distinct missing originals.
- Neither a positive water detection nor a monthly non-detection establishes rightful province, historical ownership, cause, or a boundary change. No source comparison resolves all land/water or ice uncertainty over any whole component.

## Reproduction

Run the complete frozen analysis twice with Python 3.12, Pillow, NumPy, Shapely 2, pyproj, and a Zstandard CLI. The captured environment is recorded in [`outputs/runtime-capture.json`](outputs/runtime-capture.json); it used Zstandard CLI 1.4.5. From the repository root, run:

```sh
python3 research/geography/portugal-spain-gap-source-families-20261007/scripts/run-complete-analysis.py run-1
python3 research/geography/portugal-spain-gap-source-families-20261007/scripts/run-complete-analysis.py run-2
```

The runner executes every producer and control validator in a fixed order, then preserves the complete output set in `runs/run-1/` and `runs/run-2/`. `outputs/reproducibility.json` compares the two runs by whole-file SHA-256. Separate positive and negative control receipts are retained for both simplified administrative products, APA line overlay, MAPA current snapshot, and JRC monthly-history detection. The extraction script verifies all 11 pinned component payload blobs and their decoded hashes before creating the 70-geometry extract. The administrative comparison reassembles both full source products and verifies their exact original SHA-256 values; the APA comparison parses every feature from both complete WFS pages; the MAPA comparison retains all 17 current feature polygons and applies [Esri documented ring winding](https://developers.arcgis.com/rest/services-reference/enterprise/geometry-objects/) for holes. The JRC summary checks the 70/52 scope, uses the downloaded TIFF tile offsets and byte counts, applies Zstandard compression and TIFF horizontal predictor, and counts only source-grid pixel centers strictly inside each source geometry.

The complete source-and-code closure is listed in [`inputs/frozen-input-code-manifest.json`](inputs/frozen-input-code-manifest.json), including whole-file hashes, byte sizes, source totals, scope-index descriptors, and per-file/aggregate size checks. The manifest excludes itself from its own file inventory. [`outputs/execution-code-input-binding.json`](outputs/execution-code-input-binding.json) binds that frozen source/input manifest and the exact producer-code digest to both preserved run receipts. The binding was computed after execution from the retained bytes; run manifests carry capture timestamps, so compare their `outputs` arrays rather than the run-manifest hashes when assessing deterministic output equality.

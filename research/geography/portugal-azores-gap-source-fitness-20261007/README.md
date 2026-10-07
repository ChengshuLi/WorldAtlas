# Azores complete gap-family source fitness

Issue: [#1390](https://github.com/ChengshuLi/WorldAtlas/issues/1390)  
Family: `gap-source-batch:3a814f72f5a24fbafdee8afb`  
Issue-pinned historical baseline: `83bed8c4c49e8f54077bb4abf0f32d41d0992f81`  
Scope: all 34 physical components, all 19 current PRT ADM2 contact features, including all 17 numeric-closure siblings.
Actual PR base for current metrics: `d51c43e878c797d215ba5bd8285571fa14add443`. All 23 whole-file baseline input pins were checked against that commit and match byte-for-byte; source-vintage routing remains tied to the original issue baseline.

This packet assesses source identity and candidate-scale polygon overlays. It changes no Atlas geometry, location assignment, source registry or release. No administrative, physical, water, ownership, cause or historical classification is approved.

## Scope and prior work

The pinned family shard independently reconciles the 34 component IDs, the 19 current contact IDs, and 17 numeric-closure members. The inherited route reports 5 components with no literal administrative source intersection and 29 with positive but mixed/partial/subject-unresolved source coverage. Its physical support categories remain distinct: 1 mapped-land, 13 mixed-source, 3 outside mapped L1 context and 17 unknown; it records 20 nonempty-support closure disagreements. These are preserved baseline diagnostics, not newly adjudicated classifications or approved land area. The inherited `measured_fragment_area_sum_m2` is not used as an approved area.

Completed #1274 / PR #1282 examined 52 Portugal–Spain families (70 components and 57 contacts). Exact family, component and contact comparison shows no overlap with this family. Its complete 311-feature simplified geoBoundaries PRT ADM2 capture is reused as the exact national product; all 19 target source IDs occur once in that full product. The target-specific 34-component comparisons here are new. Open #241 overlaps the same 19 contact IDs for an Iberia interior audit, but its contract contains none of these physical component IDs and its owned path is separate.

Global numeric recovery issue [#1394](https://github.com/ChengshuLi/WorldAtlas/issues/1394) now reports three exact component overlaps with this source-only family and is recovering original operands. This packet preserves the pinned source-vintage route row and old numerical labels as inherited context; it does not call them recovered/current or replace them. No verified successor results had been handed over when these source runs were made. Keep all 17 numeric siblings and their existing labels intact pending reconciliation of the three overlap members.

## Administrative product actually consumed

The baseline `scripts/administrative.py` at `cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1` rewrites the configured geoBoundaries PRT ADM2 URL to `_simplified.geojson`, downloads that simplified product, and records its raw-byte SHA. The #1274 retained whole-product capture is 387,331 uncompressed bytes, SHA-256 `f7a9143190715b85812b03617adc4879898b8c6a6789b9c9732c9705ea6c21ac`; its full compressed custody file is pinned in the issue contract. It has 311 features. This packet retains the exact 19 selected source features and points to the whole immutable capture rather than copying it again.

At the pinned geoBoundaries release commit `90a1d52`, the complete `geoBoundaries-PRT-ADM2-metaData.json` reports ADM2, 311 units, represented-year claim 2020, `boundarySource: Wikipedia`, source-update and build claims of 21 February 2024, and a CC0 1.0 data-license claim. The metadata's `boundarySourceURL` and `licenseSource` are both the incomplete string `https//en.wikipedia.org/wiki/File`; it does not identify an underlying file. The current Atlas registry normalizes these two strings to `https://en.wikipedia.org/wiki/File` and stores the exact simplified-product SHA, but still does not identify a specific Wikipedia source file. The same release's [pinned `CITATION-AND-USE` file](https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/90a1d52/releaseData/gbOpen/PRT/ADM2/CITATION-AND-USE-geoBoundaries.txt) requests attribution and says computer code and derivative works are CC-BY 4.0. Both whole files are retained under `sources/` with hashes in `evidence-quality.json`. Attribution is preserved; the exact license applicability to underlying source geometry and the derivative is unresolved. Source date, effective interval, authority, positional accuracy, registration and cause remain unknown.

## Candidate overlays

`outputs/assessment.json` is the machine-readable result. `outputs/selected-source-features.geojson` contains the 19 complete selected simplified source features without clipping or geometry alteration. `outputs/current-atlas-contact-features.geojson` independently preserves the 19 current Atlas geometries, and `outputs/complete-components.geojson` preserves all 34 complete components from the pinned custody payloads.

Using the exact simplified product, five components have no intersection, 24 intersect exactly one selected contact, and five intersect two; thus 29 components have positive-area source contact. Comparisons use all 646 component/contact pairs. The current Atlas geometries and selected simplified product are not topologically equal for any of the 19 contacts. Comparing component predicates against both products yields 10 different `intersects` outcomes and 19 different positive-area outcomes; `covers` differs in zero pairs. These results make the product distinction material. The differences do not identify why the products differ or establish a correction.

A separate comparison uses the official CAOP2025 Azores municipal polygons. It finds 39 component–municipality intersection pairs covering 32 distinct components and 19 municipality names; two components have no CAOP municipal intersection, and one component is covered by a single municipal feature. Source-to-CAOP name comparison gives 18 normalized exact name matches; geoBoundaries `Calheta` does not exactly match CAOP `Calheta de São Jorge`. The calculation retains native names and uses geometric intersections, not a guessed alias. DGT's CRS definitions are EPSG:5015 (central/eastern islands) and EPSG:5014 (western islands), both PTRA08/ITRF93 UTM in metres. pyproj reports 1 m accuracy for the coordinate operation; this is transform metadata, not source positional accuracy. Geodesic and Lambert azimuthal equal-area intersection values are diagnostic, source-relative areas only.

[CAOP2025](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop?language=pt) is a stronger current administrative comparator than the geoBoundaries metadata's Wikipedia source claim, but it is not the historical evidence for the simplified product, not a physical coastline, and not a finding about rightful administration. DGT says CAOP registers administrative delimitation/demarcation for cadastral and cartographic purposes, receives boundaries from multiple sources, and that the Portuguese Assembly has legal competence to set/alter administrative boundaries. CAOP2025 was approved on 28 January 2026 and published on 18 February 2026; it includes changes published from 16 March to 31 December 2025. The retained official GeoPackages carry no positional accuracy or registration statement applicable to these features. The [official open-data page](https://www.dgterritorio.gov.pt/dados-abertos) states CC-BY 4.0, so attribution to DGT is preserved.

## Physical and water evidence

The [SNIG catalog](https://snig.dgterritorio.gov.pt/rndg/srv/search?_source=e652bd46-4143-4371-b14c-a55d494c4d5c) lists 2024 orthophotos at 10 cm for Corvo and Graciosa and other island imagery at different vintages/resolutions. Three target components intersect those two CAOP municipality polygons, which is only administrative context. SNIG's metadata API returned HTTP 500/400 for the Corvo/Graciosa records. No source imagery was acquired, rendered or overlaid; acquisition dates, pixel registration accuracy, license terms and exact asset coverage remain unverified. The catalog listings cannot support a physical label. Complete ECO_ID0 geometry and candidate-scale independent land/water evidence remain unavailable in this packet. Every current physical category and unknown is preserved, with no component reclassification.

## Reproduction and controls

Run from the repository root with Python 3.12, Shapely 2.1.2 and pyproj 3.7.2:

```sh
PYTHONDONTWRITEBYTECODE=1 python research/geography/portugal-azores-gap-source-fitness-20261007/assess.py
```

The script reads only the pinned complete family shard, complete custody index and component payloads, whole current part, whole simplified-source payload and the retained CAOP2025 ZIP. It checks complete ID sets and raw whole-file digests, uses CRS84 longitude/latitude, keeps geometries unmodified, and produces geodesic area and independent LAEA overlay diagnostics. It does not download inputs or modify source data. The positive control checks all 34 valid component geometries and 19 unique source joins; the negative control translates all components 100 degrees east and verifies zero source intersections. The two full fresh runs and matching output hashes are recorded under `outputs/runs/` and `outputs/reproducibility.json`.

Source and output file hashes, baseline file pins and the exact contact-to-part mapping are recorded in `evidence-quality.json`. Bytes and calculations being reproducible does not establish source truth, effective dates, accuracy, physical land/water, ownership, or cause. Parent #1202 remains open.

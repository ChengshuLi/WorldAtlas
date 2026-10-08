# Western India complete-family source fitness assessment

## Scope and status

This packet assesses the complete source-fitness family selected for issue [#1432](https://github.com/ChengshuLi/WorldAtlas/issues/1432). It retains every declared component subject and all recorded contact context. The exact family and component-ID collision scan was repeated across 982 issues and 452 pull requests on 2026-10-08; it found no other issue or PR containing these subjects. Open issue #111 shares the recorded western India contacts but contains none of the 18 component subject IDs. Treat it as contact and territorial context only.

This is source-only research. All inherited physical statuses remain unknown and all geographic authority remains unapproved. No geometry was changed, and no correction, import, publication or production operation is proposed.

## Findings

The complete retained India ADM2 and ADM3 administrative products were authenticated from the geoBoundaries release at commit `9469f09`. The advertised-versus-retained count differences were reconciled against the matching `sourceData` archives and the release’s full-resolution GeoJSON. This identifies which stage contains the observed name-count gaps; the repository does not state why the release products differ from their source archives. Details and exact inputs are in the count-reconciliation section and manifest. Each candidate component intersects at least one feature in each retained product; this is administrative coverage evidence only. It cannot establish dated dry land versus inland water, legal boundary authority, or processing cause.

The complete-family rank is reproducible from the pinned source-fitness slice and all 14 immutable family output shards. The slice contains 1,005 rows for 711 unique families; the selected family is present in the full family outputs. Using the pinned priority code order `source_locator_readiness`, `coordination_complexity`, then `measured_impact`, its tuple `(22, 51987, 93320)` sorts to rank 8 of 711, with no tie. The method and exact input hashes are recorded in `selection-ranking/report.json`; this is selection accounting only.

The routing snapshot flags two family members for source-fitness review:

- `physical-component:36ffb10735d8d7d402912f989ff500524a686e86a2f636efc100acc56b9d2ba0`
- `physical-component:d8a7c45330ea4f423c70a95cd8bb8a510225b04bcea292ffb5574e19d323d1ca`

Their recorded ADM2 coverage witnesses are Thane and Raigarh, respectively. That relationship is source-relative and does not establish physical surface or authority. The inherited full-row projection classifies every family member as `mapped-land-support`, while retaining `unknown-source-fitness-and-observation-date` and `unapproved` authority for every member. See the per-member roster and inherited claims table below.

## Numeric result ledger

All values below are bound to generated JSON values in `evidence-quality.json`; the printed table rows are checked against that ledger.

| Metric | Value | Unit |
|---|---:|---|
| Complete family members | 18 | components |
| Family selection rank | 8 | rank |
| Ranked source-fitness families | 711 | families |
| Members requiring source-fitness assessment | 2 | components |
| India ADM2: Retained source features | 735 | features |
| India ADM2: Advertised source features | 736 | features |
| India ADM2: Advertised minus retained features | 1 | features |
| India ADM2: Bounding-box candidate pairs | 41 | pairs |
| India ADM2: Exact native-coordinate intersections | 31 | pairs |
| India ADM2: Subjects with an exact intersection | 18 | components |
| India ADM2: Source polygons covering candidate pointsets | 5 | pairs |
| India ADM2: Nonblank source shape IDs | 735 | IDs |
| India ADM2: Unique source shape IDs | 735 | IDs |
| India ADM2: Missing source shape IDs | 0 | features |
| India ADM2: Duplicate source shape ID groups | 0 | groups |
| India ADM2: Invalid source geometries | 0 | features |
| India ADM2: Topology predicate errors | 0 | pairs |
| India ADM3: Retained source features | 6822 | features |
| India ADM3: Advertised source features | 6836 | features |
| India ADM3: Advertised minus retained features | 14 | features |
| India ADM3: Bounding-box candidate pairs | 52 | pairs |
| India ADM3: Exact native-coordinate intersections | 39 | pairs |
| India ADM3: Subjects with an exact intersection | 18 | components |
| India ADM3: Source polygons covering candidate pointsets | 0 | pairs |
| India ADM3: Nonblank source shape IDs | 6822 | IDs |
| India ADM3: Unique source shape IDs | 6822 | IDs |
| India ADM3: Missing source shape IDs | 0 | features |
| India ADM3: Duplicate source shape ID groups | 0 | groups |
| India ADM3: Invalid source geometries | 0 | features |
| India ADM3: Topology predicate errors | 0 | pairs |
| Members in inherited comparison rows | 18 | components |
| Inherited mapped-land-support status | 18 | components |
| Inherited physical status unknown | 18 | components |
| Inherited physical authority unapproved | 18 | components |


### Release count reconciliation

The metadata’s advertised `admUnitCount` matches the corresponding `sourceData` archive row count for both products. The counts diverge in the `releaseData` outputs as follows:

| Product stage | Value | Unit |
|---|---:|---|
| ADM2 `sourceData` archive records | 736 | features |
| ADM2 full-resolution `releaseData` GeoJSON | 735 | features |
| ADM2 retained simplified GeoJSON | 735 | features |
| ADM3 `sourceData` archive records | 6836 | features |
| ADM3 full-resolution `releaseData` GeoJSON | 6824 | features |
| ADM3 retained simplified GeoJSON | 6822 | features |

By source-name multiset, `Charki Dadri` is present in the ADM2 `sourceData` archive and absent from both ADM2 `releaseData` GeoJSON files. Twelve ADM3 names present in the source archive are absent from the full-resolution release: `Bironkhal`, `Charakonda`, `Chilpched`, `Kalol`, `Kaloor Thimmandoddi`, `Khoupum`, `Kilpennathur`, `Mamdot`, `Rajoli`, `Sanawad`, `Suangdoh`, and `Udainagar`. Fourteen source names are absent from the simplified ADM3 product: those twelve except `Khoupum`, plus `Gadiguda`, `Lm`, and `Moosapet`.

The ADM3 full-resolution and simplified files also differ by `shapeID`: three full-resolution IDs (`7132399B10679805821500` / `Gadiguda`, `7132399B78300861263339` / `Moosapet`, and `7132399B97254734508703` / `Lm`) are absent from the simplified file, while the simplified file has `7132399B4028970572101` / `Khoupum`, which is absent from the full-resolution file. That is a net reduction of two records. ADM2 has the same `shapeID` set in full-resolution and simplified outputs.

The `sourceData` ADM3 archive is a shapefile DBF with `Name` records, not stable release `shapeID` values. These comparisons therefore reconcile row counts and source-name multisets, not authoritative identity across datasets; repeated names may occur. The pinned repository artifacts establish the observed release-stage differences but do not document why those records are absent or why the ADM3 ID set changes. No geometric or physical-surface inference follows from these count checks. See `feature-count-reconciliation/report.json` for part hashes, the complete name deltas, and the exact file inventory.

The comparisons use the [geoBoundaries India sourceData ADM2 archive](https://github.com/wmgeolab/geoBoundaries/blob/9469f09/sourceData/gbOpen/IND_ADM2.zip), [ADM3 archive](https://github.com/wmgeolab/geoBoundaries/blob/9469f09/sourceData/gbOpen/IND_ADM3.zip), and the corresponding [full-resolution ADM2](https://github.com/wmgeolab/geoBoundaries/blob/9469f09/releaseData/gbOpen/IND/ADM2/geoBoundaries-IND-ADM2.geojson) and [ADM3](https://github.com/wmgeolab/geoBoundaries/blob/9469f09/releaseData/gbOpen/IND/ADM3/geoBoundaries-IND-ADM3.geojson) release files. Both product metadata records the ODbL 1.0 license; the license text URI is listed above.

## Sources and method

These retained complete geoBoundaries databases are identified by their upstream release metadata as Open Data Commons Open Database License (ODbL) 1.0. The [ODbL 1.0 license text and URI](https://opendatacommons.org/licenses/odbl/1-0/) accompany this source attribution for both retained products.

- [geoBoundaries India ADM2 release](https://github.com/wmgeolab/geoBoundaries/tree/9469f09/releaseData/gbOpen/IND/ADM2): retained complete simplified GeoJSON, represented year 2021, ODbL 1.0 per release metadata.
- [geoBoundaries India ADM3 release](https://github.com/wmgeolab/geoBoundaries/tree/9469f09/releaseData/gbOpen/IND/ADM3): retained complete simplified GeoJSON, represented year 2018, ODbL 1.0 per release metadata.

Original whole-product SHA-256 values are `d68db39cd3e2d0892af268e2b0454166368ce3b5b8a78fcda63069ec92a641db` (ADM2) and `4ea6807d0a0c5aac0b46ee8e31ed7c30fbec273b44345bba1e4a2bb5f299f5fb` (ADM3). The ADM3 original is reconstructed from retained contiguous partitions and parsed by part because the original exceeds the per-file decoded-input limit. Original and compressed part digests are recorded in the evidence manifest and current source vintage.

For each complete component pointset, the assessment scanned every retained source feature, retained every bounding-box candidate, then evaluated exact native-coordinate intersection and coverage predicates where both unmodified geometries were valid. It used longitude/latitude pairs in stored order and made no projection, area, or distance calculation. The retained source GeoJSON does not provide a CRS or datum declaration; treating coordinates as geographic WGS84 is an assumption. Geometry validity was preserved without repair.

For each numeric metric, `input_sha256` identifies a registered immutable source, custody, priority, or input-inventory file; `input_set_sha256` records the corresponding whole analysis-input digest. The current report's `analysis_input_sha256` binds all 18 component feature hashes to both reconstructed original source-product hashes. `selection_input_sha256` in the coverage report binds its pinned selection inputs and the independently reconstructed rank report. The rank report separately hashes all 14 family shards, the full source-fitness slice, routing report, and pinned priority-order code. The inherited projection binds all 18 physical-comparison row shards. These values remain projections of prior evidence, not new observations.

## Limits and next action

The source-feature count differences are now reconciled by release stage and source name, but the upstream processing cause remains undocumented. This comparison does not establish whether the retained extracts are current-complete. No independent dated physical-surface source was found. The precise missing evidence is a dated, authoritative observation at adequate resolution for each candidate, distinguishing dry land from inland water where relevant. Keep all subjects unresolved pending that evidence. Engineering may use this packet for later source review; it does not authorize a boundary edit or regional approval.

Runs `coverage-screen-2026-10-07-03` and `coverage-screen-2026-10-07-04` are retained as superseded complete attempts. The earlier uncommitted attempts did not publish receipts. Run `coverage-screen-2026-10-07-05` was superseded after corrections to inherited-status reporting and input-byte accounting. Run `coverage-screen-2026-10-08-01` was superseded by explicit source-fitness witness reporting. The current complete screen is `coverage-screen-2026-10-08-04`; `inherited-claims-2026-10-08-01` is the current inherited-row projection. Every run has its own immutable completion receipt.


To reproduce the family rank and validate its bounded manifest, run `python3 research/geography/india-western-gap-source-fitness-20261007/selection-ranking/run.py` followed by `node scripts/evidence-quality.mjs research/geography/india-western-gap-source-fitness-20261007/selection-ranking/evidence-quality.json`. The full geography screen can be rerun with `python3 research/geography/india-western-gap-source-fitness-20261007/assess.py`; validate the packet with `node scripts/evidence-quality.mjs research/geography/india-western-gap-source-fitness-20261007/evidence-quality.json`.

To reproduce the release-count reconciliation and validate its bounded manifest, run `python3 research/geography/india-western-gap-source-fitness-20261007/feature-count-reconciliation/run.py` followed by `node scripts/evidence-quality.mjs research/geography/india-western-gap-source-fitness-20261007/feature-count-reconciliation/evidence-quality.json`.

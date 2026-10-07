# Angola–DRC shared-seam source assessment (#1243)

## Disposition

Source-only assessment of the complete `gap-source-batch:80eb2e392d5ef4fe3781d37a` family: ten complete Atlas component geometries, ten original detector fragments and all five contact subjects. No core geometry, political/territorial adjudication, engineering repair proposal, publication, or geographic approval is made. Cause remains unknown.

The complete earlier COD/AGO source screen, retained here with its original receipt, classifies two components as uniquely covered by one compatible recorded source subject and eight as mixed/partial or unresolved. The current exact overlays are independently reproduced against the complete consumed source products. All ten components remain **unresolved** for physical-water status and causal stage: administrative coverage and land-cover samples do not establish water boundaries or original processing loss.

## Immutable vintages

- **Atlas baseline:** `79ffb2ed04702e16f009e4675a8d74ef9bd09d4f`. Seven pinned source shards contain the ten full component records; the complete original fragment layer and report are pinned separately. The five full contact records come from the two pinned geography partitions.
- **Consumed admin products:** COD `gbOpen` ADM2 simplified product, 2019, exact full original 3,294,607 bytes, SHA-256 `922427143fcff23010af3931fb3f5e4ffea8b05c5d2b797ca02fc04c6c8b1baa`; AGO `gbHumanitarian` ADM2 simplified product, 2018, exact full original 813,152 bytes, SHA-256 `7cf2a401b36480f7c22d9783e4364d3eb93c3ac643e2d34778b1ce059c786dcf`. Both are CC BY 3.0 IGO. The separately advertised full product URLs are recorded apart from the consumed simplified URLs in `inputs/source-acquisition-receipt.json`.
- **Merged successor:** the exact `#1215` run-one outputs at commit `c6a26e1caba54e1b81a89fbda3a64fff56da323d` link all ten exact component IDs and hashes. Tile 759 was reused and its original/current queries are byte-equivalent after JSON parsing. This is retained separately from the original baseline. PR #1231 was open/unmerged when inspected and is not treated as delivered successor evidence.
- **Independent environmental references:** the full Natural Earth 1:10m land and lakes references at `ca96624a56bd078437bca8184e78163e5039ad19` are retained (public domain). The pinned lakes source has 1,355 features and documents major lakes/reservoirs only; it omits a complete river and small-water inventory. No intersection with that layer does not demonstrate dry land.
- **Current land-cover observation:** ESA WorldCover 10m 2021 v200, two exact adjacent tiles covering all ten component geometries. Full retrieval bytes and hashes were verified; retrieval metadata and source URLs are retained. The full tiles are restored by the pinned URLs in `sources/worldcover-v200/retrieval.json` and must match the recorded SHA-256 values. Class 80 (permanent water) pixel-centre samples occur in two components; class 90 (herbaceous wetland) samples occur in eight. These are 2021 land-cover observations, not full-shape hydrology or 2018/2019 water authority. No class-80 samples is not evidence of dry land.

## Geometry method and results

`reproduce.py` uses Shapely 2.1.2 and Rasterio 1.4.3. Geometry operations preserve literal source longitude/latitude coordinates in EPSG:4326 and use exact planar intersections and unions. No coordinate normalization, reprojection, snapping, buffering, simplification, MakeValid, nearest fill, or political assignment occurs. Areas are recorded only in source coordinate units squared (degrees²); they are not surface-area measurements.

`outputs/geometry-overlays.json` records every exact intersecting COD/AGO ADM2 source feature and bounding-box candidate for each component, full source-feature and intersection hashes, exact intersection WKB, the intersecting source union, and both directions of the component/source-union difference. It also overlays the complete pinned Natural Earth land reference, preserving exact hit/candidate features, the land-union geometry and both residual directions. `outputs/fragment-contact-overlays.json` records all ten original fragments and five complete contact features against every relevant candidate in the two full ADM2 products, including zero-area intersections. The immutable input files preserve original pointsets and source-provided contacts/diagnostics.

`outputs/worldcover-samples.json` samples only strict-interior pixel centres. It retains all observed class counts and NoData class 0 if present. It does not turn pixel absence into dry-land evidence. Natural Earth land and lake intersections are retained per component; both references' stated incompleteness limits interpretation.

`outputs/component-assessment.json` gives a whole-component disposition for each of the ten subjects and keeps the prior source-screen result in a separate field. `unresolved` is the finding for every component: neither positive administrative-source intersection, Atlas successor lineage, no Natural Earth lake hit, nor partial WorldCover samples establish the missing physical-water boundary, an executed processing failure, or a cause. Existing issues #411, #462, #878 and #1046 remain outside this scope.

## Reproduction and controls

Restore the two versioned WorldCover tiles from the URLs in `sources/worldcover-v200/retrieval.json`, verify both SHA-256 values, then run:

```sh
WORLD_COVER_DIR=/path/to/exact-worldcover-tiles python3 reproduce.py
# Restore the JRC 2018/2019 tiles and Lei 14/24 PDF to their pinned source paths.
python3 reproduce_additional.py
# For the recorded two-run execution, provide the pinned Python 3.12 environment at .venv312/bin/python.
python3 run_additional_twice.py
python3 verify_packet.py
```

The final producer was executed twice after its last change; both runs produced identical SHA-256 values for all five generated outputs. The positive control checks the exact Atlas shard, fragment, contact, admin and successor bindings. The negative control flips one byte in the consumed COD product in memory and confirms the pinned whole-file check rejects it. The controls establish byte/source consistency and deterministic output, not factual water classification or cause.

## Limits and handoff

There is no complete, date-matched authoritative river/lake/water-boundary source or original executed processing closure in this packet. The source products and independent land-cover references do not support a water/dry decision for any whole component. Do not infer that Atlas geometry is wrong, that any feature should be reassigned, or that the reviewed administrative names imply legal ownership. Any future repair needs separately authorized engineering work, full affected-neighbor review, preserved stable identities, and the explicit prepared-v7 successor chain.

## Candidate-scale water and current legal-text screening

Two additional independent references were assessed against every candidate component. JRC Global Surface Water v1.4 annual history provides Landsat-derived 30 m classifications for 1984–2021 ([official catalog](https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_YearlyHistory)). Exact 2018 and 2019 tile bytes, retrieval receipts and hashes are retained. The final producer counts pixel-centre classes and separately preserves all-touched counts and NoData. Seasonal-water pixels occur in two components; no permanent-water pixels occur in any component. Seven components have only NoData pixel-centre observations in both years. NoData is not land, and sparse positive pixels do not classify a whole component.

The current Angolan administrative law, Lei 14/24 in the official gazette of 5 September 2024, is retained as a full PDF ([official gazette PDF](https://c2a.portais.gov.ao/uploads/LEI_14_24_5_de_SETEMBRO_LEI_DA_DPA_043a0de85f.pdf)). Three component geometries intersect one or more infinite latitude parallels named in the text. The law describes rivers and endpoint locations but this screen does not derive the finite river segments or georeference the printed maps. These coordinate intersections are research leads only. This 2024 legal source postdates the consumed 2018/2019 source products and does not establish their historical boundary geometry, ownership, or the cause of the candidate fragments.

The exact assessment output preserves all ten candidate pointsets and all five contact IDs and geometry hashes. Contacts remain full neighboring administrative polygons; they are not treated as candidate gap footprints and are not classified by the raster or legal-parallel screen. `reproduce_additional.py` is frozen with its inputs in `inputs/additional-freeze.json`; `run_additional_twice.py` records the two completed executions. `verify_packet.py` verifies all additional source/code pins, output coverage, both run receipts, and in-memory negative controls for altered JRC and law bytes. The method is tile-based and can be applied globally for selected years, but a global annual sweep would require many distinct 10-degree tiles and is outside this ten-component assessment.

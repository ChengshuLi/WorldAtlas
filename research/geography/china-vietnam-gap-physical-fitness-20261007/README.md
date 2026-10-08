# China–Vietnam gap physical-source fitness (#1450)

## Finding

The selected independent source, ESA WorldCover 10 m 2021 v200, cannot adjudicate either exact restored component geometry as areal land or water. Both exact geometries contain zero native WorldCover pixel centers. The component records report fragment area sums of 0.0000002121602005 m² and 0.0000015668344844 m², and `water_status` remains `unverified`. This is a source-resolution and degenerate-footprint limitation, not evidence for land, water, or a physical boundary.

The subjects are complete `physical-component:` features from the custody restoration at baseline commit `c9518bafefb0e7c4bd53842284e0208ab5223dc6`:

| Component | Restored source file | Source SHA-256 | Reported fragment area sum (m²) | Native pixel centers |
|---|---|---|---:|---:|
| `physical-component:002641892e7354093a13a207fc47deb3141691473079e89537752c78dc5a92fa` | `components-000.json` | `eac8b87294e31722939ff834289c00be512312ab83e81720d4fabd577cd5da36` | 0.0000002121602005 | 0 |
| `physical-component:4716f097520ef2f6a7cecc0a5d7b4d00e4066aaa1252765726fa5a244a4b0b91` | `components-003.json` | `b02763e7ee4e514a6208432d5ec3d78713cdae5f15b19118a3ac8ba43184cf85` | 0.0000015668344844 | 0 |

The restored feature files are full FeatureCollections in `research/geography/indonesia-borneo-source-fitness-20261007/vintages/restore-450126d0/`. Their component IDs directly identify the exact features assessed here. Contact context is traced to the original `detection-v4/candidates-007.geojson.gz` file in the same baseline commit (1,120,843 bytes; SHA-256 `ff497d1127d47e9df308d118e89a4c3e893a0ed4078da82aaab82326cc9919c7`). The record-level candidate hashes are inside that gzip archive; they are not standalone file hashes.

The exact contact roster is CHN ADM2 `17275852B24445486288332`, VNM ADM2 `81297802B72919536287172`, and VNM ADM2 `81297802B22471082550929`. Four contact relationships are positive-length, zero-width lines; one is point-only and ambiguous. They provide contact context, not area evidence or physical authority.

## Source and method

ESA’s [WorldCover data access page](https://esa-worldcover.org/en/data-access) documents the 2021 v200 map, its 3×3-degree Cloud-Optimized GeoTIFF tiles, EPSG:4326, nominal 10 m grid, and CC BY 4.0 license. The [Product User Manual](https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/docs/WorldCover_PUM_V2.0.pdf) and [Product Validation Report V2.0](https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/docs/WorldCover_PVR_V2.0.pdf) are preserved with HTTP headers and SHA-256 receipts. ESA reports 76.7% overall accuracy for the global 2021 product; that statistic is not a local confidence estimate for these components.

The official N21E105 COG object is 102,974,131 bytes, with ETag `"a0c724f8d28f1c4d198ac6f69ff4fded-13"` and Last-Modified `Wed, 26 Oct 2022 12:47:57 GMT`. The packet retains the 128 KiB TIFF header range and the two complete native 1024×1024 Deflate blocks covering the full restored component bounds. Each request used `If-Match`; response status, content range, ETag, last-modified time, byte count, and SHA-256 are recorded. The retained ranges total 217,886 bytes; their decoded cost was 2,097,152 bytes. No full-object SHA-256 is claimed because this multipart object was only partially acquired.

`plan_worldcover_blocks.py` reads the exact restored component features from the pinned baseline commit and derives source ranges from their bounds and the native TIFF block table. `classify_worldcover_window.py` reads those same restored geometries, decompresses only the retained blocks, and counts native pixel centers covered by the geometries. It does not reproject, resample, repair, buffer, or fill them. Embedded WorldCover metadata identifies class 80 as permanent water bodies and class 90 as herbaceous wetland; class 90 is not open water.

## Access check and limits

The [Vietnam National Spatial Data Infrastructure portal](https://vnsdi.mae.gov.vn/) identifies the national topographic data portal. A point query against its national topographic map sheet service at a candidate coordinate returned HTTP 503 with an access-denied response; response headers and body are preserved. No map sheet or imagery was downloaded. The catalog is a possible follow-up source if access becomes available, but it provides no physical evidence in this assessment.

No physical-source approval, geometry proposal, administrative attribution, or release decision is made here. A further assessment would need an independently dated source with precision appropriate to the requested boundary context, or a decision that these near-zero-area candidate records are not amenable to physical-source adjudication.

`member-dispositions.json` binds both members to their complete restored feature files and gives each a per-source disposition. `packet-controls.json` records exact-roster, contact-roster, unknown-preservation, and class-semantics checks. `run_spatial_controls.py` runs synthetic positive, negative, altered-input, and missing-source checks against the classifier helper functions without reading raster blocks or candidate GIS inputs. These controls exercise the helper behavior; they do not independently validate a physical surface fact. The source-fitness conclusion remains limited, and no physical status is inferred.

## Evidence files

- `source-acquisition-receipts.json` indexes retained source bytes, resource admission, and checksums.
- `worldcover-block-plan.json` records exact component bounds, selected blocks, and memory/storage caps.
- `worldcover-window-findings.json` records pixel counts, contact geometry, and the limited source-fitness conclusion.
- `workspace-memory-admission.json` records captured host-memory and workspace-storage admission before raster decoding.
- `member-dispositions.json` records both complete member dispositions and the full three-contact roster.
- `packet-controls.json` and `spatial-control-results.json` record the packet checks and synthetic helper controls.
- `sources/` contains official ESA documents, COG byte ranges, and the restricted-service query receipt.

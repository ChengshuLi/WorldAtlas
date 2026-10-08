# JRC Occurrence source and exact block budget

Date: 2026-10-07. Current #1431 contract SHA-256: `2aa9ab4ea222fc7a00668e1306c9e4be15f15de943607979605d1d91068750b3`. This is a source-support supplement for the 15 complete candidate components and all 9 complete administrative contact features.

## Source and custody

The source is JRC/EC Global Surface Water v1.5 Occurrence (1984–2024), delivered as 10° GeoTIFF tiles via the JRC-linked CloudFerro object store. The [JRC source page](https://global-surface-water.appspot.com/download) says the data are free under Copernicus terms with attribution; the release uses Landsat Collection 1 for 1984–2021 and Collection 2 for 2022–2024. JRC reports a spatially varying Collection 1/2 co-registration offset, usually subpixel but at or above one nominal 30 m pixel in some WRS-2 path/rows. The [published occurrence legend](https://data.fao.org/catalog/iso/f1b1d45a-e360-44bd-95a9-d628c468a7f6) is 0=no detected water, 1–100=occurrence percentage, 255=NoData. The product is aggregate frequency context, not dated per-component evidence.

The four complete feature envelopes require `60E_40N`, `70E_40N`, `60E_50N`, and `70E_50N`. Their full TIFF objects are 20,517,553; 32,461,641; 63,277,308; and 38,518,800 bytes, respectively (154,775,302 bytes total). S3 ETags and Last-Modified values, response ranges, and byte hashes are in `source-capture.json`; ETags are validators, not SHA-256.

Each current metadata capture is bytes 0–81,327, 81,328 bytes per tile (325,312 bytes total), requested with `Range`, `If-Match`, and `Accept-Encoding: identity`; responses are 206 and match the object ETag. These prefixes include the first IFD, all overview IFDs, GeoTIFF keys, and all external offset/count arrays. Across all IFDs, metadata arrays end by byte 81,324, and the earliest `TileOffsets` image block begins at byte 81,328. Current retained ranges therefore exclude image-block bytes.

Acquisition correction: earlier 512 KiB range captures also contained small overview image blocks beginning at byte 81,328. They were used only while parsing TIFF metadata, never decoded or classified. All six original prefix bodies and HTTP metadata were restored under If-Match and preserved as quarantined history at `.cache/kgt-independent-water-source-review-20261007/recovery/previous-512k-prefixes/`; those bytes are excluded from current source inputs and all calculations. Four previously saved hashes match exactly; the two exploratory tile prefixes had no saved earlier hashes, and their recovered bytes are bound to the prior ETag and the new SHA-256 in the quarantine manifest. No full TIFF or base-resolution raster block has been acquired.

## TIFF metadata and tile indexing

All four TIFFs use a 40,000×40,000, one-band UInt8 grid, EPSG:4326/WGS84, `RasterPixelIsArea`, 0.00025° pixel scale, and 512×512 tile blocks (79×79). TIFF base IFDs each have 6,241 `TileOffsets` and `TileByteCounts`; each offset+length lies within the advertised object length. Seven overview levels follow. No `GDAL_NODATA` tag appears in the base IFD; the published legend carries 255 as NoData.

The GeoTIFF tiepoint is the west/north corner. The suffix names the northern edge: 40N tiles span 30–40°N and 50N tiles span 40–50°N. Pixel grid mapping used here is `column = 4,000 × (longitude − tile_west)` and `row = 4,000 × (tile_north − latitude)`, consistent with the [OGC GeoTIFF raster convention](https://docs.ogc.org/is/19-008r4/19-008r4.html). At ~40°N, 0.00025° is roughly 21.4 m east-west by 27.8 m north-south; the grid is angular and not a metric square.

## Exact block intersection and cohorts

The complete source geometries remain in their pinned original files. The vector-only routine converts their retained decimal coordinates to rational pixel coordinates and checks exact closed-set intersection against closed 512×512 block squares. It supports Polygon/MultiPolygon rings and holes, includes boundary-only touches, does not clip or rewrite geometry, and reads no raster image blocks. The source file references and whole-file SHA-256 values are included per member.

Exact union: **256 blocks** — 60 in `60E_40N`, 138 in `70E_40N`, 28 in `60E_50N`, and 30 in `70E_50N`. The tile block bytecount arrays sum to **687,297 encoded bytes** for this unique union. A full 512×512 UInt8 buffer per block is bounded by **67,108,864 bytes (64 MiB)** decoded. All 17 candidate support blocks also occur in the 256-block contact union; this is block-grid overlap only and is not independent negative/control evidence.

The typed cohort generator partitions by subject type and tile with a cap of 64 unique blocks (16 MiB decoded) per cohort. It produces 10 cohorts; all 15 unique candidate IDs and all 9 unique contact IDs are represented. Candidate tile membership count is 16 and contact tile membership count is 18 because complete features crossing tile boundaries appear in multiple tile cohorts. The cohorts contain 306 unique-block memberships, including 50 repeats across cohorts. No member is dropped or geographically clipped. The largest cohort has 63 blocks / 15.75 MiB decoded. If all cohorts are processed separately without caching duplicate blocks, their summed costs are 855,570 encoded bytes and 80,216,064 decoded bytes; the deduplicated union remains 687,297 encoded / 67,108,864 decoded bytes. Conditional inclusive byte ranges for each cohort are recorded in `jrc-bounded-cohorts.json`; no block ranges were requested.

The two candidate families preserve their original states: family `gap-source-batch:74be953b1fb31c15200742da` has 12 components; `gap-source-batch:65911e15791d12ebb2ccacf5` has 3. Both remain cause unknown, physical authority unapproved, and source fitness unapproved for all components. Candidate records retain `water_status=unverified` and null administrative assignment. Contact features are retained as full current source context only.

## Limits and review artifacts

No pixel values were seen, decoded, or classified. JRC Occurrence cannot establish present water, a fine boundary, land class, ownership, rights, or historical authority. Tile metadata gives no candidate-level registration/positional accuracy; component-level effective dates and lineage/cause remain unknown.

Reproducible artifacts in this folder:

- `exact-block-intersections.py` and `jrc-exact-block-intersections.json` (manifest SHA-256 `0526129fd4a61dab4127dd6d675eef8249ba304f8a7926ae89303e70bacced61`).
- `build-bounded-cohorts.py` and `jrc-bounded-cohorts.json` (SHA-256 `188f4eaa88f6f6f90cef7acf5a1ca7131ffb6c397a219d2cb732dc9c97f971fe`).
- `source-capture.json` (SHA-256 `3f7884b3baec157112f1d660e6646fdbdc333db46b50c9b61eb85d7a9d4cdeea`) and four 81,328-byte metadata-only IFD prefixes.

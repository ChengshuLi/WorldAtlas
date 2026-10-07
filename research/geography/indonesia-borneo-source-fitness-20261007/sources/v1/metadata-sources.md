# Primary source notes (retrieved 2026-10-07)

This note records source-level facts consulted for the packet. It does not grant rights beyond the terms shown by each provider.

## ESA WorldCover

- Source page: https://esa-worldcover.org/en/data-access
- Product: ESA WorldCover 10 m 2021 v200, map layer; official delivery as Cloud Optimized GeoTIFFs in EPSG:4326, 10 m nominal resolution. The area spans three tiles: N00E117, S03E117 and S03E114. The first two source tiles are retained whole; S03E114 is retained as a CC-BY crop preserving every all-touched source pixel within the exact 45-component footprint. The full S03E114 response was 47,311,452 bytes, so it was not retained as a single input; its URL, byte SHA-256, ETag and crop checksum are in `worldcover-extract-receipts.json`.
- ESA states CC BY 4.0 and attribution requirements on the data page. The same page reports 76.7% global overall accuracy for 2021 v200. This global metric is not a local accuracy estimate for East Kalimantan.
- The 2020 and 2021 maps use different algorithm versions; cross-year differences mix real land-cover changes with algorithm changes. This assessment uses 2021 v200 only.
- Tiles and extraction receipts: `worldcover/`, `worldcover-crops/`, `worldcover-whole-tile-receipts.json`, `worldcover-extract-receipts.json`.

## JRC Global Surface Water

- Data page: https://global-surface-water.appspot.com/download
- Download instructions: https://global-surface-water.appspot.com/gsw/Download_Instructions.html
- FAQ and original mapping description: https://global-surface-water.appspot.com/faq
- Source product: Global Surface Water v1.5 1984–2024, Occurrence (aggregate 1984–2024) and Seasonality for Seasonality 2024. The saved tile metadata labels this a single-year 2024 layer, while the provider download page describes the new-seasonality asset as covering 2022–2024; that period conflict is unresolved, so this packet treats it as 2024-only. The provider states the data are free of charge without restriction of use under the Copernicus Programme, with required attribution `Source: EC JRC/Google`.
- Full 10°x10° source tiles were retrieved and hashed; lawfully derived crops preserve all source pixels touched by the exact union of the 45 original component polygons, with 255 reserved as crop nodata outside the union. The complete source-tile SHA-256, source URL, ETag, and crop SHA-256 are in `jrc-source-receipts.json`; the retained GeoTIFFs are in `jrc-crops/`.
- The provider describes 30 m Landsat inputs. Occurrence combines Landsat Collection 1 through 2021 and Collection 2 after that; the provider warns that co-registration differences between collections vary spatially and can reach or exceed one 30 m pixel in some path/rows. The 2022–2024 seasonality layer is a recent-period product, not the complete historical series. These conditions prevent treating absent mapped water as proof of dry land or a cause.
- The provider's FAQ defines its detected signal as open water visible from space; vegetated water, water below the detection threshold, cloud/observation gaps, and local classification error can remain. The global validation summary is not a local estimate for these subjects.

## geoBoundaries administrative source

- Source/release: https://github.com/wmgeolab/geoBoundaries/tree/9469f09/releaseData/gbOpen/IDN/ADM2
- The original IDN ADM2 geoJSON product has 519 features, represented year 2020, raw bytes 11,002,896, SHA-256 `146653d488331086ddc43d159a261b01ea6dd08c7ed422e34a9886c3c690430c`. Its exact compressed payload is already retained at `coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-IDN-ADM2-000.bin.gz`; its SHA-256 is `ef394916ba97454b5592e66eba1df67199731ce7d9636cc3968843801ae904a8`.
- The retained product citation statement declares CC BY 4.0 with geoBoundaries and individual-source attribution. The exact underlying source metadata for Indonesia ADM2 records CC BY 3.0 IGO and an OCHA/HDX source. The original corpus preserves both layers of terms; it does not independently verify source authority, effective dates, or boundary truth.
- This product supports direct comparison with the Atlas subjects, not current legal authority or a local positional-accuracy statement.

## BIG administrative source

- 2022 KSP layer endpoint: https://kspservices.big.go.id/satupeta/rest/services/PUBLIK/BATAS_WILAYAH/MapServer/2?f=pjson
- 2023 RBI administrative service: https://geoservices.big.go.id/rbi/rest/services/BATASWILAYAH/Administrasi_AR_KabKota_50K/MapServer/layers
- The official service describes polygon features in WKID 4326. The official 2023 metadata describes a September 2023 geodatabase update over the December 2022 edition and identifies multiple upstream inputs, including April 2023 Kemendagri data for Kalimantan and previously agreed or Permendagri boundaries. A related official BIG metadata record warns about line topology problems in `ADMINISTRASI_LN`, including crossing and dangling line ends.
- `Copyright Text` identifies BIG on the public 2023 service, but neither inspected service metadata nor the public KSP site establishes an open redistribution license for the 2022 geometry. The KSP site describes controlled access/data-sharing governance. The 2022 service response timed out on this retrieval pass; an earlier exploratory metadata response was not retained as bytes. No BIG polygon response or derivative geometry is retained or used in the overlay. Thus the BIG polygon geometry/license assessment remains unresolved and needs direct terms or lawful access before reuse.

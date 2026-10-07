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
- Exact 2022 layer metadata is retained in `metadata/big-2022-ksp-layer.json` (6,924 bytes, SHA-256 `8b4f36f7046630098f99916210dffbe3c6ed2233eee87f632fb632439922fb28`). It identifies the polygon layer as the 2022 edition (revised December 2022), WKID 4326, and describes upstream inputs including RBI 1:25,000/1:50,000, 2013–2014 adjudication, Kemendagri boundary agreements through 2022, and Permendagri. It also explicitly notes unresolved `ADMINISTRASI_LN` overshoot/topology errors. This source scale list is not a product-level positional-accuracy estimate.
- Exact 2023 service layer metadata is retained in `metadata/big-2023-rbi-layer.json` (5,775 bytes, SHA-256 `b87c10ad9670f6be7ec2c26c3807b108ebfdd6929aceb290db4d3b6bd7237551`). It describes a polygon layer in WKID 4326; the separate official 2023 service record dates its geodatabase update to September 2023 over the December 2022 edition and lists April 2023 Kemendagri inputs for Kalimantan.
- The inspected BIG layer response has an empty `copyrightText`, not an open reuse license. The KSP site describes controlled access/data-sharing governance (https://onemap.big.go.id/). These metadata facts do not establish redistribution permission. No BIG polygon response or derivative geometry is retained or used in the overlay. BIG geometry/license and legal-authority findings therefore remain unresolved; obtain direct terms or lawful access before geometry reuse.

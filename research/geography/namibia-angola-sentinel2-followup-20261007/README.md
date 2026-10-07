# Namibia–Angola Sentinel-2 water observations

This is a source-only follow-up for #1358, a bounded child of #1202 and independent-source follow-up to #1268. It measures dated optical water-like signals in the unchanged 21 candidate polygons and in each of 10 source-contact polygons intersected with the candidate union. Contact measurements cover only those overlap masks, never the full administrative polygons. This packet does not edit geometry, assign territory, repeat the global GSHHG comparison, or claim boundary authority, historic course, or a processing cause. #1268 remains open.

## Data and selection

The scenes are Sentinel-2 Level-2A products from 2019 and 2020, selected as one low-cloud MGRS tile scene in each of four calendar windows (Jan–Mar and Aug–Oct in each year) for each of four tiles (33KZA, 34KBF, 34KCF, 34KDF). Scene dates are retained per observation; these are seasonal comparison bins, not same-day mosaics or proof of local rain or hydrologic state. Selection is frozen in `inputs/selected-sentinel2-items.json`; the complete paginated catalog responses and query receipts are retained under `inputs/`.

Official Copernicus documentation describes L2A surface reflectance and scene classification, with B03/B08 at 10 m and B11/SCL at 20 m. The pixels here were read from Element84's public AWS Cloud Optimized GeoTIFF mirror, not directly from the Copernicus Data Space. The catalog item, asset URL, product identity, acquisition/processing metadata, asset HEAD headers, object ETags, Last-Modified dates, sizes, CRS, affine transform, scale/offset, and native resolution are retained in the STAC snapshots and source receipts. Whole COG objects were not downloaded or assigned fabricated whole-file SHA-256 values: Rasterio/GDAL performed HTTP byte-range reads, with the raw verbose range session retained in `sources/cog-range-session.log`; the actual sampled source windows are retained as hash-pinned NPZ files under `sources/windows/`.

The selected products have processing baseline below 04.00, `earthsearch:boa_offset_applied=false`, and zero per-band reflectance offset. B03/B08/B11 DN values are converted using the retained scale of 0.0001; common multiplicative scale cancels in the normalized indices. B03/B08 10 m values are averaged over each native 20 m center's corresponding 2×2 cells. The 20 m SCL code is kept separately. Copernicus SCL water is class 6; no-data, defective, cloud shadow, low/medium/high cloud, cirrus, snow/ice and dark-area classes are separately counted. Dark-area and cloud/shadow/unclassified classes are not used in the clear-index denominators.

Primary documentation:

- [Copernicus Sentinel-2 product guide](https://documentation.dataspace.copernicus.eu/Data/SentinelMissions/Sentinel2.html)
- [Copernicus Sentinel data legal notice](https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice)
- [Copernicus Sentinel Hub Sentinel-2 L2A reference](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html)
- [Element84 Earth Search source and catalog notes](https://github.com/Element84/earth-search)

Attribution required by the Copernicus legal notice for the adapted samples retained here: “Copernicus Sentinel data 2019”; “Contains modified Copernicus Sentinel data 2019”; “Copernicus Sentinel data 2020”; “Contains modified Copernicus Sentinel data 2020.”
- [OKACOM Okavango Basin Transboundary Diagnostic Analysis](https://www.okacom.org/sites/default/files/documents/TDA_Final-English.pdf), used only as broad basin-season context, not as evidence of exact acquisition-date hydrology.

The mirror/catalog is a derivative access path; Copernicus is the product origin. The Copernicus legal notice provides free, full and open access/use subject to lawful use and exceptions stated in that notice. That notice governs the Copernicus product; it does not independently certify the mirror service's terms. The mirror/catalog is used as an access path, and source attribution is retained here.

## Method and reproducibility

`extract_sentinel2_windows.py` samples 20 m pixel centers inside original candidate masks without repairing, buffering, snapping or changing polygons. Contact bits identify candidate-union∩contact masks. Raw band samples, source grid coordinates, geometry membership bits and source object receipt references are retained. `analyze_sentinel2_windows.py` verifies source-window hashes, expected shapes, the #1268 whole-file geometry pins, selected scale/offset and processing-baseline conditions before calculating MNDWI=(Green−SWIR1)/(Green+SWIR1) and NDWI=(Green−NIR)/(Green+NIR). MNDWI and NDWI threshold sensitivity is reported at −0.1, 0 and +0.1. SCL6 plus positive MNDWI concordance is counted only at the same sampled center; separate positive totals are not described as concordant.

The full 31-mask × 16-scene table and subject summaries are in `runs/run-one.json` and `runs/run-two.json`. Both full runs completed from the retained windows and produced the same SHA-256: `fe903fb95a88c06236f0dba092275421a7eae480ec8c53c696d52d8f74d65f41`. The controls include all 21 original component identities and 10 contact identities, exact #1268 input-file pins, membership and array-shape checks, nonempty SCL water, no-data and cloud/shadow populations, monotonic MNDWI thresholds, zero-signal contact screening, and complete subject-by-scene row counts. Exact commands and package versions are recorded in the evidence manifest.

## Observations

SCL6 and positive-MNDWI centers occur together in the same sampled pixels in 20 of 21 candidate masks. Component `physical-component:cd9a7967a8f7f17c8fae2c8dbb4cc22f9ca5ac63271e2d003200ab381890ff17` has only 1,224 total sampled centers across dates/tiles, 1,017 usable index centers, three SCL6 centers, one nonnegative-MNDWI center, and zero concordant SCL6-plus-positive-MNDWI centers. Its signal is too sparse and mixed to characterize. Other components with low water-like counts are also observations for follow-up, not stable water delineations. Each per-date row carries valid/nodata/cloud counts so a low count can be interpreted against actual coverage.

Eight of ten contact-overlap masks include at least one concordant SCL6-plus-positive-MNDWI center. Contact `gb:NAM:ADM2:8085530B43563455443088` had 1,392 sampled centers and no SCL6 or nonnegative-MNDWI center in these selected scenes. Contact `gb:NAM:ADM2:8085530B54610932550654` has sparse and nonconcordant signals (5 SCL6, 9 nonnegative MNDWI, zero concordant centers across selected observations). Counts across dates and overlapping masks are explicitly nonadditive. These results do not characterize water outside the candidate-contact overlap pieces.

## Limits and next step

These are 20 m center observations on nominally georeferenced native UTM grids, not a ground-control registration assessment. No independent control-point registration check or absolute positional uncertainty was available. No exact bank, shoreline, channel-edge, narrow-channel, permanent-water or historical-course claim is warranted. Dates without water-like signal do not establish dry land; mixed pixels, cloud/shadow, missed seasonal timing, water turbidity/vegetation and geometric offset remain plausible. Sentinel-2 is independent of Landsat-derived JRC water summaries as a sensor/product source, but SCL and spectral thresholds remain imperfect observational screens. The images do not resolve the historical/current boundary authority, survey provenance, processing cause, or territorial assignment. Broader official boundary-scale map/survey retrieval and authority review remain for #1268.

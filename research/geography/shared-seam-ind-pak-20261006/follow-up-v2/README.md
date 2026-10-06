# India–Pakistan seam follow-up (2026-10-06)

This follow-up adds a current-main check and an independent physical-surface proxy without changing any of the earlier #1100 files. The fresh branch baseline is `0f08ca8c451e71bb3b06cb5fb82988e92d3048ab`.

## Fresh-main check

The exact 16 native/current subject pairs and both complete physical-gap fragments were checked again. All 16 current geometry digests match the prior retained current-feature digests exactly. On this fresh main baseline the combined fragment area remains 2,362,541,936.078026 m², with zero positive-length contacts to the three geoBoundaries source members and 18 to current Atlas features. Two runs are byte-identical. This confirms the earlier geometry comparison remains valid on the current main inputs; it does not identify whether the original differences arose from source simplification, different administrative tiers/years, or Atlas reconciliation.

## Independent physical-surface indicator

ESA WorldCover 2021 v200 is a 10 m land-cover classification released 2022-10-28 under CC BY 4.0. The official data-access page says WMS images are RGB-only and unsuitable for analysis; this check therefore reads the original classified GeoTIFF COGs from ESA's public S3 bucket. It counts valid pixel centers within each full fragment, separately by the four intersecting 3×3-degree tiles. The recorded tile URLs, full object byte counts, ETags, Last-Modified headers and SHA-256 digests are in `worldcover-window-summary.json`.

The 1,274 fragment contains 24,898,828 valid pixel centers, of which 25,191 (0.1012%) are WorldCover class 80 (permanent water). The 1,346 fragment contains 6,654,945 centers, of which 116,742 (1.7542%) are class 80. The rest of the pixels are assigned to non-water land-cover classes by this map. These are product classifications, not surveyed hydrology: ESA reports 76.7% global overall accuracy. They support treating the fragments as predominantly land-cover-classified land in the 2021 product, while leaving local surface status, the product's commission/omission errors, administrative ownership and disputed affiliation unresolved.

This proxy does not change either fragment or any Atlas boundary, locate a surveyed shoreline, establish historic water status, or determine sovereignty. The classification year is independently dated but does not supply per-pixel observation dates. Do not fill the fragments into a neighboring administration or make a boundary correction from these counts.

## Reproduction and original source restoration

Use Python 3.12, NumPy 2.5.3, Rasterio 1.5.2, Shapely 2.1.2 and pyproj 3.7.2. Install Rasterio into a task-local cache, then run:

```sh
python3 -m pip install --target research/geography/shared-seam-ind-pak-20261006/.cache/rasterio-runtime rasterio==1.5.2 numpy==2.5.3
PYTHONPATH=research/geography/shared-seam-ind-pak-20261006/.cache/rasterio-runtime python3 research/geography/shared-seam-ind-pak-20261006/follow-up-v2/reproduce_current_main.py run-1
PYTHONPATH=research/geography/shared-seam-ind-pak-20261006/.cache/rasterio-runtime python3 research/geography/shared-seam-ind-pak-20261006/follow-up-v2/reproduce_current_main.py run-2
PYTHONPATH=research/geography/shared-seam-ind-pak-20261006/.cache/rasterio-runtime python3 research/geography/shared-seam-ind-pak-20261006/follow-up-v2/sample_worldcover_2021.py
```

The WorldCover script restores each COG from the exact official S3 URL and checks its recorded byte length before hashing and reading; compare the resulting SHA-256, ETag and Last-Modified with the manifest. Original tiles are each larger than the 32 MiB evidence-file bound, so only full-object restoration instructions and exact object hashes are retained in Git; the downloaded originals stay in the ignored local cache. ESA's attribution is `© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium`.

Sources: [ESA WorldCover data access, license and validation](https://esa-worldcover.org/en/data-access); [WorldCover 2021 v200 release](https://doi.org/10.5281/zenodo.7254221).

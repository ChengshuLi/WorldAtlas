# Correction: Copernicus DEM GLO-90 pixel spacing

Issue #566; correction recorded 2026-10-03 UTC. This note supersedes three textual statements in the earlier evidence packet for #67: two in `research/campaigns/copdem-sahara-20261003-a44eff82017e/source-evaluation.md` (selected-product paragraph and finding 2) and one in `source-manifest.json` (`official_sources` entry for the AWS public dataset readme). The old packet is preserved as merged. No raster, hash, source identity, geographic scope, classification, or installed/published behavior is changed by this correction.

## Corrected reading

For the inspected `Copernicus_DSM_COG_30_N25_00_E010_00_DEM` tile, the GeoTIFF header reports 1200 × 1200 pixels and a one-degree tile, with geotransform increments of `0.0008333333333333` degrees. That angular spacing is:

- `0.0008333333333333 × 3600 = 2.99999999988` arc-seconds, approximately **3 arc-seconds**; and
- equivalently, `3600 arc-seconds / 1200 pixels = 3 arc-seconds per pixel` across one degree.

The raster therefore does **not** have 30 arc-second pixel spacing. The filename component `30` in `Copernicus_DSM_COG_30_...` is a distribution naming token and must not be reported as this file's measured grid spacing. The readme retrieved for this check explicitly labels the `[resolution]` token as arc-seconds and gives `30` for GLO-90; that statement conflicts with the inspected COG's numeric grid. We preserve this source-document discrepancy rather than silently treating the filename token as a physical pixel measurement. The measured header controls the selected tile's grid-spacing statement.

The corrected statements are: “the product README uses the filename token `30` for GLO-90; the selected COG has approximately 3 arc-second pixel spacing according to its 1200 × 1200, one-degree GeoTIFF header.” The filename is not evidence that cells are 30 arc-seconds. GLO-90 remains the product designation; this correction does not change the existing DSM/DTM distinction or imply a new elevation accuracy assessment.

## Recheck and provenance

On 2026-10-03 UTC, the public AWS readme at the manifest URL was retrieved again. It is an unversioned HTML object with SHA-256 `922461d55070e3c7e0cf2903ec54190d69e3773da2dc9e776a3f03566cfd56d2` (8,536 bytes), matching the earlier retained hash. The named S3 tile object reports ETag `"21d34038701c0af27eafe970c8d55679"` and Last-Modified `2022-05-09T12:51:59Z`; these identify hosted object metadata, not a product edition or terrain observation date. An HTTP `Range: bytes=0-8191` request returned 8,192 bytes (206 Partial Content), SHA-256 `c6cbabc9864020e8a3a41aa98a1571d64e563e5362f953216a002419e801b83e`. `gdalinfo -json -noct` on those TIFF header bytes independently reports size 1200 × 1200, EPSG:4326 and geotransform increments ±0.0008333333333333 degrees. The complete tile hash remains the previously recorded `d038b51d42a2686c203e1e87ee3866594e9d9905d67326e424ec45103373aafc`; no full raster is retained or altered here.

The readme contains no explicit edition/version identifier. Its retrieval date and full response hash are therefore the available version pin for this recheck. The original Copernicus Product Handbook v5.0 hash/date, official product page, GLO-90-F license, product-wide 2011–2015 acquisition frame, older gap-fill caveat, unknown selected-tile acquisition date, and modern DSM surface interpretation remain as recorded in the earlier packet. This correction supplies no new terrain observation interval and does not change license or attribution conclusions.

## Scope boundary

This PR corrects research wording only and closes the child correction scope. It does not alter code or product behavior, redownload/install data, edit the original campaign, make location assignments, change geography/schema/categories, or import facts. The selected tile remains modern terrain reference context; it does not establish ancient or other historical terrain conditions.

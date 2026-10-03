# Copernicus DEM GLO-90 central Sahara tile evaluation

Issue: [#67](https://github.com/ChengshuLi/WorldAtlas/issues/67)

Campaign: `copdem-sahara-20261003-a44eff82017e`

Evaluation date: 2026-10-03 (America/Los_Angeles); source responses inspected 2026-10-03 UTC.

## Selected product and tile

One public GLO-90 Cloud Optimized GeoTIFF was evaluated: `Copernicus_DSM_COG_30_N25_00_E010_00_DEM`. Its 1°×1° tile covers approximately 25–26°N and 10–11°E, used here as a central Sahara sample. The tile name is present in the distribution's `tileList.txt`; the product README documents the 1° tile naming scheme and 30 arc-second spacing for GLO-90. The product page describes GLO-90 as global coverage. The selected area label is a sampling descriptor, not an atlas territory or proposed boundary.

## Findings: nine metadata and product items

1. **Tile presence and source identity.** The public GLO-90 `tileList.txt` contains the exact selected object stem. Tile list response size and SHA-256 are retained in [`source-manifest.json`](source-manifest.json). The object URL and its full-object hash are also recorded; neither raster nor manifest bytes are duplicated in Git.
2. **Actual COG geometry and raster header.** `gdalinfo` on the public object reports 1200×1200 Float32 pixels, WGS 84 / EPSG:4326, a 1°×1° footprint, 0.0008333333° grid spacing (30 arc-seconds), `AREA_OR_POINT=Point`, and COG/DEFLATE metadata. Coordinates are read from the tile header, not inferred from modern administrative geography.
3. **The selected COG does not provide its acquisition date.** Its inspected metadata has no acquisition-date tag, SRC scene list, or source XML. The provider's `Last-Modified` value (2022-05-09) and ETag describe the hosted object, not the DEM's observation/acquisition date.
4. **Product-wide acquisition frame.** The official Copernicus Data Space product page says the DEM data were acquired by the TanDEM-X mission between 2011 and 2015. It also warns that older elevation models were used to fill data gaps, so some sensing dates can predate 2011. The Copernicus DEM Product Handbook v5.0 gives the global GLO-90 coverage timeframe as 2011–2015 and describes TanDEM-X/WorldDEM acquisitions from December 2010 to January 2015. These are product-wide periods, not a tile-specific date claim.
5. **Where finer source dates would reside.** The Product Handbook says the original Source Data Layer (SRC) KML contains source-scene IDs and acquisition date/time; product XML metadata describes the acquisition period, input products, and processing. Those source layers/XML are not included in the selected public COG distribution. No actual per-scene date for this tile was established.
6. **Surface type and limitations.** Copernicus describes the product as a Digital Surface Model: a top-reflective surface that includes buildings, infrastructure, and vegetation. It is not a bare-earth DTM. The DEM is edited (including water-body flattening, river consistency, coastlines, airports, and implausible structures) and may include gap-fill sources. It cannot by itself substantiate ancient terrain or an unchanged historical landform.
7. **GLO-90 license.** The official ESA/Copernicus license PDF contains a section titled `COP-DEM-GLO-90-F Global 90m Full, Free & Open`. It grants the general public worldwide, unlimited-time, free, non-exclusive rights to reproduce, distribute, communicate, adapt, modify, and combine the GLO-90 product. This is not CC0 and does not relinquish provider intellectual-property rights. When communicating or distributing it, the license requires the source notice: `© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.` It also requires a liability disclaimer and a non-endorsement condition for public distribution.
8. **EEA-10 is a distinct instance and terms.** The official product page separates EEA-10 (10 m, European coverage and user restrictions) from global GLO-90. The selected 90 m Sahara tile is in the GLO-90 distribution and is evaluated under the GLO-90-F license above; EEA-10 restrictions do not convert this global tile into restricted EEA-10 data.
9. **Documentation and hosting dates are not terrain dates.** The product page metadata gives publication 2024-05-15 and page modification 2026-05-05; the Product Handbook is v5.0 dated 2022-11-29. The AWS object listing reports a 2022-05-09 `Last-Modified`. None of these web/document/object dates is the selected tile's terrain acquisition date.

The page's product availability and the S3 mirror establish access to this single COG. The tile COG and supporting PDF/page source bytes were hashed and remain restorable from the canonical URLs in the manifest. Only a bounded COG range was fetched for header identification; the full tile was streamed to compute its hash, then discarded. No credentials or restricted account access were used.

## What this supports

This evaluation supports identifying a modern, global DSM product, its GLO-90 reuse conditions, the selected tile's actual grid/header, and the product-wide acquisition window with its fill-source caveat. The exact selected-tile/scene acquisition date remains unknown from the public COG header. The product is usable only as separately labeled modern physical reference context unless independent evidence supports a historical claim; its 2011–2015 product period does not establish terrain conditions in earlier years. Do not extend that period, infer an ancient stable surface, assign a fixed topography classification, or build annual records from this product.

No topographic classification, asset installation, atlas location mapping, factual claims, or imports were prepared. The campaign is source-only; no boundary or schema decision is made.

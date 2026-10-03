# ESA WorldCover 2021 v200: Kenya tile source evaluation

Issue #64; source-only review. Retrieved 2026-10-03 UTC. This records product semantics and a bounded tile inspection. It does not define or alter boundaries, assign values to Atlas locations, calculate zonal summaries, or import attributes.

## Product and provenance

ESA WorldCover 2021 v200 is a global 10 m land-cover map for the 2021 calendar year, produced from Sentinel-1 and Sentinel-2 inputs. The product manual describes the reference period as 2021-01-01 through 2021-12-31. Product release was 2022-10-28. The selected native tile is `S03E036`, whose nominal 3° × 3° footprint is 36–39°E and 3–0°S. The tile intersects contemporary Kenya according to a point/rectangle intersection using Natural Earth 1:10m country polygons, solely to choose a tile and retain bounded examples. That polygon is not an Atlas border source or a historical-territory assertion.

The tile was retrieved from the public ESA S3 URL in the manifest. Its SHA-256 is `89db764127e7d49d00247ae92a76e3f2d6147df41f7058653ba9882700cbf31d` (135,162,419 bytes). The S3 multipart ETag is recorded only as an object identifier, not treated as a content hash. The `Last-Modified` time is object metadata, not the observation date. GDAL header inspection found a 36,000 × 36,000 Byte palette raster, EPSG:4326, 1/12000° cells, NoData 0, pixel-is-area, COG/DEFLATE. Product metadata identifies algorithm V2.0.0, tile `S03E036`, start/end timestamps for 2021, and creation time 2022-10-21 (creation time is not observation time).

The ESA data access page states that the maps are CC BY 4.0. Required attribution: `© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium`. Dataset DOI: [10.5281/zenodo.7254221](https://doi.org/10.5281/zenodo.7254221). No private access or credentials were used.

## Legend and evaluation

The product legend is: 10 Tree cover; 20 Shrubland; 30 Grassland; 40 Cropland; 50 Built-up; 60 Bare/sparse vegetation; 70 Snow/ice; 80 Permanent water bodies; 90 Herbaceous wetland; 95 Mangroves; 100 Moss/lichen. Code 0 is NoData, not water. Classes are observed land-cover labels, not potential natural vegetation classes.

Possible semantic candidates for later review only: class 95 Mangroves is narrowly compatible with the existing `vegetation:mangroves`; class 40 Cropland may be compared to `vegetation:farmlands` as observed 2021 cover. Neither is approved as a mapping. Class 90 wetland is not synonymous with flooded grassland: the definition covers herbaceous fresh/brackish/salt wetlands and excludes tree swamp/mangroves. Tree cover includes plantations (including oil palm) and can include flooded cover; grassland may include pastures and uncultivated cropland. Shrubland and grassland are broad cover classes and do not determine a potential-natural biome. Remaining classes have no direct fixed vegetation-class equivalent in the reviewed taxonomy. Do not transfer these labels to Atlas territories or interpret observed farmland as a potential biome.

The Product Validation Report reports global overall accuracy 76.7 ± 0.5% and Africa 76.5 ± 1.3%; neither is Kenya- or tile-specific. Reference data span continents and were based on 2015–2019 sources updated for 2021. The InputQuality layer records Sentinel-1/Sentinel-2 observation counts and the percentage of invalid S2 observations discarded; these are input-quality indicators, not per-pixel class probabilities or accuracy. Known limitations include cloud artefacts, hard borders from input-orbit/block differences, confusion between agriculture and wetlands, and water detections on glaciers or mountain shadows. No local accuracy guarantee is inferred.

## Bounded cell examples

Twenty-three cell centres from a 5 × 5 equal-position candidate lattice fell within the contemporary Natural Earth polygon and were read from the selected tile. Coordinates and zero-based raster column/row are preserved in the manifest. This purposive set is only a reproducibility/example check: it is not random, representative, a class-frequency estimate, or a zonal algorithm. Two candidate centres were outside the polygon and were omitted. No location assignments, boundary rasterization, polygon statistics, or percentages were produced.

## Temporal limits and decision

The product represents 2021 observed land cover. It cannot establish earlier or later cover, a historical territorial boundary, or a location-wide condition. No interpolation, backcasting, extrapolation, or extension to another year is supported. Use as a bounded, dated source reference and retain uncertainty; keep any future semantic crosswalk as a candidate until separately reviewed. No import was attempted: there is no complete published regional approval certificate with exact permitted subjects and matching release pins for this target.

## Sources consulted

See `source-manifest.json` for URLs, retrieval status, hashes, sizes, methods and exact attribution. The ESA access page, tile grid GeoJSON, Product User Manual v2.0, Product Validation Report v2.0, selected tile, and the Natural Earth polygon source were consulted. Source payloads are not redistributed in this campaign; temporary downloads were kept outside the repository.

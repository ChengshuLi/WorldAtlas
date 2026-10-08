# Makira source-fitness assessment

Issue: #1457 · family: gap-source-batch:0e8b7e76cd964d21746a40aa · all 15 exact components and one shared contact.

## Finding

No source is qualified for any member. Six current Copernicus Data Space Sentinel-2 L2A STAC items and three SPREP-listed scenes form candidate screening metadata only. Their exact footprint coverage, valid pixels, member-local cloud, component-level positioning, byte lineage and all required rights checks are unresolved. The exact item IDs and values are in [source-register.json](source-register.json); the per-member candidate decisions and exact source-coverage statuses are recorded for every one of the 15 members.

The CDSE items have 10m GSD and these acquisition/item-cloud metadata: 2019-09-05 T57LYJ 8.73%, T57LZJ 8.39%; 2020-01-18 T57LYJ 34.13%, T57LZJ 24.83%; 2020-04-07 T57LYJ 15.57%, T57LZJ 26.64%. Clouds are item/tile level, not member-local. They were processed in 2023 as N0500; the SPREP page lists older N0213/N0214. SPREP’s 2020-01-18 entry says T57LZK, while current family-extent STAC results return T57LYJ and T57LZJ. Product-name history for the Jan T57LZJ has two recorded SHA-256 byte vintages and no populated input lineage, so an item ID alone does not bind unique raster bytes. Preserve this discrepancy.

The SPREP resource says 10m RGB and lists a SPREP Public Licence, but its exact derivative reuse terms remain unconfirmed. Sentinel-2 Collection 1 L1C documentation reports <12m absolute geolocation accuracy at 95.5%; this is not transferred to the SPREP RGB derivative or exact L2A asset. Members with approximate bbox short spans of 9m, 12m, 30m and 52m are not certified; other members are at most screening candidates.

OpenAerialMap queries returned no records for the full family extent. That is a bounded catalogue-not-found result, not proof no aerial imagery exists. SRTMGL1.003 (30m elevation) and the MoFR Makira 2020 map (30m Landsat-derived classification) are unsuitable as fine raw observations. Geoscience Australia/Australian searches found no Makira/SLB aerial or LiDAR metadata; unrelated Cocos LiDAR and marine sonar do not establish member coverage. The classified ArcGIS MakChange00to19_coord service (item 707bd27667a24eb98c6021b9f7ab2a4b) is not raw imagery; its service metadata has no license statement.

## Component/contact census

Each row in [source-register.json](source-register.json) retains the exact original subject ID, its custody-derived lon/lat bbox, existing routing prerequisite, approximate short spans, and individual evaluations for all source scenes/catalogue classes. No family member was dropped. The sole shared contact is gb:SLB:ADM1:17018030B43755880178831 (Makira ADM1), administrative context only. Its represented year is 2021; effective date and authority are unknown/unapproved.

## Limits and next evidence needed

All 15 members remain source_fitness=unapproved and physical_authority=unapproved. Require exact source asset IDs/checksums/processing lineage and licence text; exact native geometry-to-pointset overlays; member-local valid-pixel/cloud statistics; and component-level positional assessment before a source can qualify. No pixels, paid source access, GIS, physical approval, ownership inference or geography repair were performed.

## References

- [SPREP San Cristobal 10m RGB imagery resource](https://solomonislands-data.sprep.org/resource/10-meter-rgb-satellite-imagery-san-cristobal-island-years-2019-2020)
- [CDSE STAC API documentation](https://documentation.dataspace.copernicus.eu/APIs/STAC.html)
- [Sentinel-2 Collection 1 L1C product characteristics](https://sentinels.copernicus.eu/sentinel-data-access/sentinel-products/sentinel-2-data-products/collection-1-level-1c)
- [OpenAerialMap API documentation](https://docs.openaerialmap.org/api/api/)
- [SPC Solomon Islands data methodology](https://www.pacific-r2r.org/sites/default/files/2022-10/SLB_R2R_Data_Sources_and_Methodology_Brief_2.pdf)
- [Solomon Islands MoFR Makira Land Cover Map 2020](https://www.mofr.gov.sb/documents/ForestLCM/makira-land-cover-map-2020.pdf)
- [Geoscience Australia](https://www.ga.gov.au/)


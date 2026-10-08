# Lithuania–Latvia dated physical-observation follow-up

Issue #1452; complete family `gap-source-batch:d6347433d050d025e6e082c0`. Scope remains all 16 component subjects and all three contacts as enumerated in the issue contract. This is a source-research packet only. No image pixels, GIS overlays, candidate edits, imports, or geographic/legal approvals are included at this stage.

## Current status

Official-source metadata review confirms that potentially useful orthophoto services exist, but does not yet establish per-subject coverage or observation dates. The Lithuanian metadata record for ORT10LT 2025 is internally inconsistent. Latvia's current 2022–2024 cycle-8 imagery/time-map service requires a signed client license, and this packet has no evidence of that license or authorized access. Positional accuracy for Latvia cycle 8 is not stated in the public product pages reviewed. No water/shoreline, processing-cause, source-authority, or legal-boundary conclusion follows from service availability or nominal pixel size.

Exact per-subject spatial joins require the resource/window admission requested from the coordinator. Pixel inspection or retention additionally requires verified reuse/retention terms and authorized source access. Until those conditions are met, the candidate classifications remain unresolved.

## Lithuania: ORT10LT

The public [ORT10LT 2024–2026 ArcGIS service](https://www.geoportal.lt/mapproxy/nzt_ort10lt_2024_2026/MapServer) lists an orthophoto raster plus separate 2024 and 2025 aerial-photography-date polygon layers. The [REST layer catalogue](https://www.geoportal.lt/arcgis/rest/services/NZT/ORT10LT_2024_2026/MapServer/layers) identifies a date attribute on each year layer. These facts show that date footprints are exposed by the service; they do not show which of the 16 component geometries or 3 contacts they cover.

The current official [viewing-service metadata record](https://www.geoportal.lt/metadata-catalog/catalog/search/resource/details.page?uuid=%7B242F0DA8-39FE-4367-B648-7CF5D3EB5FDF%7D), published 2024-10-07, says the 2024–2026 view service is based on 2024–2026 aerial images and 2025 satellite imagery. The service's separate [REST ItemInfo](https://www.geoportal.lt/arcgis/rest/services/NZT/ORT10LT_2024_2026/MapServer/info/iteminfo) describes it as prepared from 2024 orthophoto material. These source descriptions do not resolve the actual imagery source or date at any subject; the service-level provenance is therefore unclear. The metadata gives only a generic “License” constraint, and the REST ItemInfo's `licenseInfo` field is empty. No reuse or pixel-retention permission is inferred.

The official [ORT10LT 2025 metadata record](https://www.geoportal.lt/metadata-catalog/catalog/search/resource/details.page?uuid=%7B7E08EDAD-FBD1-4E28-AEEA-691336E62B2D%7D) has a 2025 title. Its Lithuanian abstract describes 2025 April–June photography, about one third of national coverage, 0.2 m GSD (some listed sheets 0.25 m), and about 0.4 m RMSE. The English abstract on the same record instead says the photography occurred in 2024 April–June, and the record's temporal extent is 2024-04-25 to 2024-06-21. The separate [ORT10LT 2024 record](https://www.geoportal.lt/metadata-catalog/catalog/search/resource/details.page?uuid=%7B4AE76165-1C49-4F53-ACC1-A1D75C14B6F1%7D) describes 2024 April–June photography and a different temporal extent (2024-04-09 to 2024-07-10). The conflict remains unresolved for our subject locations; year labels alone are not accepted as per-location dates.

The [geoportal copyright page](https://www.geoportal.lt/geoportal/web/en/copyright) attributes ORT10LT copyright to the National Land Service (NŽT). The product records state only a generic “License” use constraint and do not expose the license terms in the reviewed page. They describe individual-sheet downloads and requests for broader coverage, but do not establish rights to retain or redistribute raster pixels. No pixels were downloaded or retained.

## Latvia: LGIA cycle 8

LGIA describes the [8th cycle (2022–2024)](https://www.lgia.gov.lv/en/8-cikla-2022-2024-gads-ortofotokartes) as a 20 cm national aerial-photography program delivering RGBI and CIR imagery. The page notes that eastern-border gaps would be supplemented by satellite imagery. This program description is not proof of coverage or acquisition date at any scoped subject.

The official [WMS service catalogue](https://www.lgia.gov.lv/en/wms-servisi) lists the 2022–2024 RGB/CIR orthophotos with an aerial-photography-time map and states that access is free but authorized only after the client signs the license. No executed license or authenticated cycle-8 service access is evidenced here. LGIA's [orthophoto page](https://www.lgia.gov.lv/en/ortofotokartes) says open data is available through cycle 6; cycle 8 reuse/retention must not be assumed from the fact that the WMS is listed.

LGIA's [LKS-2020 transition notice](https://www.lgia.gov.lv/en/node/1384) states that cycle 8 orthophoto datasets are issued in LKS-2020 from 2026-10-01. New web-service users receive LKS-2020 only; prior LKS-92 web services remain available to existing users through 2027-02-01. The notice reports a 7–12 cm coordinate shift between the systems. Any later overlay must pin the actual authorized endpoint, CRS, and transformation path. LGIA's published [2012 orthophoto accuracy annex](https://www.lgia.gov.lv/sites/lgia/files/document/ortofoto_not_1piel.pdf) is not treated as evidence of achieved accuracy for the 2022–2024 deliveries. Cycle-8 positional accuracy remains unverified.

## Latvia cycle-6 metadata review (2026-10-08)

GEO5 found an official LGIA cycle-6 metadata archive under CC BY 4.0 (attribution required). Its product page describes a 2016–2018, 0.25 m, whole-Latvia program in LKS-92 TM / TKS-93 sheets. That national program statement is not evidence of coverage or dates for any candidate. All 16 components and all three contacts remain in the original exact roster; inherited country and source-owner labels do not filter or explain coverage.

The archive hash is `3cd0f617b674ac51dc1a1451cfb4475a620c533dbe47ffdc0f645b7ca1e3b4e6` (14,506,864 bytes). Its DBF has 25 rows with `Datums` and `FOTO_DAT`; rows 20 and 25 conflict. The PRJ identifies EPSG:3059 / LKS_1992_Latvia_TM; the XML metadata is stale. The indexed source member is PolygonZ and decodes to 108,040,732 bytes, exceeding the current 32 MiB decoded-member limit. Public REST returned ArcGIS 403, the open metadata service has no layers, and the WMS capabilities endpoint failed normal TLS verification; no bypass was attempted.

Cycle 6 is older contextual evidence and cannot replace the original cycle-8/physical-observation acceptance. No candidate coverage/date join or image inspection is reported. GEO5’s capture, archive and SHX hashes, exact all-19 subject roster, current resource snapshot, and size/access limits are recorded in `sources/lva-cycle6-source-note.json`; raw source segments remain in an ignored local cache, not this packet. A prior solid-archive metadata extraction may have transiently materialized the oversized SHP without interpreting coordinates; the history and uncertainty are preserved. No extractor will be used again pending engineering direction.

## Remaining evidence

- Intersect all 16 exact candidate geometries and all three contact subjects with the Lithuania 2024/2025 date footprints and any authorized Latvia cycle-8 coverage/date layer; preserve zero, partial, and multiple-vintage results without snapping or geometry repair.
- Establish source access, per-location observation dates, actual data coverage, stated positional accuracy/QA, and lawful retention terms before interpreting imagery.
- If imagery cannot be lawfully accessed or retained, document that limit and use open secondary water products only as corroboration, with their pixel size, observation interval, and classification limits recorded.
- Preserve unknown physical status, source authority, historic applicability, processing cause, and legal boundary. Do not infer any from administrative-source overlap, service coverage, or GSD.

The official-source checks above were reviewed on 2026-10-08 UTC and are also logged in issue #1452 comments. No external web-page byte snapshots or source image data are retained in this packet.


## Included review records (2026-10-08)

- `subjects/components.geojson` preserves all 16 exact component features and their custody/feature/geometry hashes. `subjects/contacts.geojson` preserves the three exact contact features.
- `subjects/member-context.json` retains all 16 inherited physical-comparison rows and the complete prior administrative-source fit records. `subjects/contact-context.json` retains all three complete contact context records. These are prior evidence and do not establish physical surface or legal authority.
- `subjects/per-subject-source-status.json` lists each of the 19 exact subjects. No GIS joins, raster inspection, or source imagery acquisition occurred; coverage and actual observation date remain unknown for every subject.
- `sources/official-source-register.json` records reviewed official metadata, vintages, rights/retention, CRS/accuracy limits, and public URLs.

No source raster, licensed imagery, or restricted download is retained. This packet is not a classification, boundary proposal, import, or approval.

- source-pins.json records inherited pointset, contact and physical-row hash bindings. execution-ledger.json and reproducibility.json state what was performed and what was not run.

## Acceptance status: items 1–3 incomplete, item 4 preserved

This is not a physical-status determination. Acceptance item 1 is incomplete: for each of the 16 components and 3 contacts, the packet lacks an exact covering official tile/footprint identity, per-tile acquisition date, complete/partial/multiple-vintage/no-data status, layer-specific CRS/datum/axis order and transformation, achieved positional accuracy, and tile-level QA. Cycle-6 is not joined and cannot replace original acceptance. No per-subject source join was run.

Acceptance item 2 is incomplete: the conflicting Lithuania 2025 abstract/2024 temporal extent, current mosaic provenance, and Lithuania date-feature reuse/retention remain unresolved. Cycle-6 DBF fields conflict in two rows; the original cycle-8 source recovery remains open. No pixels were inspected or retained. GEO5’s product-specific review found only a generic “License” constraint and empty ArcGIS `licenseInfo` for both ORT_recent and ORT10LT_2024_2026. Public viewing is evidenced for ORT_recent, along with a service-use contact instruction; no one was contacted. No product-specific grant was found for offline research, retaining date-footprint vectors, or publishing derived observations. Data.gov.lt search returned HTTP 500 block pages, which is a retrieval limitation. Exact product IDs, response hashes, and rights analysis are in `sources/lithuanian-date-footprint-rights-findings.json` and `sources/lithuanian-date-footprint-capture-manifest.json`; captured response bodies remain in the ignored local cache.

Acceptance item 3 was not performed: no imagery was inspected, so no dry/water/mixed/ambiguous/unknown observation-date disposition is assigned. The physical status of every component and contact remains unknown. Acceptance item 4 is preserved explicitly in the per-subject status file with the missing facts listed for every row. These limits do not support a physical, historic water/ice, processing-cause, source-authority, or legal-boundary conclusion.

# Issue #492 — Colombia interior batch 3

## Scope and method

This packet accounts for the exact 194 pinned location IDs in `scope.json`, all in the Colombia area and all inside four complete province cohorts: Antioquia (125), Caldas (27), Caquetá (16) and Sucre (26). The area itself is partial: 194 of 1,122 current Colombia ADM2 members; other batches retain their own evidence directories. The packet pins the release, region geometry/member ID fingerprints and original member IDs from the issue. `issue-metadata.json` preserves the actual issue spec and body digest; `claim-receipt.json` records the confirmed reservation.

`assessment.json` contains one sourced row for every ID, with its full province→area→region→subcontinent→continent parent chain, exact source ID/name, source/current geometry component/ring/vertex/bbox counts, approximate area screen, parent candidate comparison, decision and explicit uncertainties. The 194 rows each match a unique DANE-declared geoBoundaries shape ID; all 194 names exactly match the pinned source. Repeated names are disambiguated by source ID and parent: Valparaíso, La Unión and San Pedro each occur twice. Name-only joining would be unsafe.

All decisions are `insufficient_evidence` for complete geography approval. This is not an assumption that the municipalities are incorrect: the administrative identity is source-backed, but current official 2024 unit rows, current settlements, physical land completeness and exact source/current boundaries are not established. No row is accepted from ADM2 numbering alone.

## Sources and dates

The pinned geoBoundaries Colombia ADM2 metadata names DANE as its underlying source, gives boundary year 2020, source update 2023-01-19, build date 2023-12-12, 1,122 units and CC BY 4.0. Its canonical-role field is blank. All 194 assigned features are `shapeType=ADM2` and each source ID/name was checked. The full 210,605,856-byte GeoJSON is retained gzip-compressed with raw and stored hashes in `sources.json`; its 74,845,471-byte compressed packet copy stays below GitHub's per-file limit. Restore from the exact pinned media URL and verify the uncompressed hash before using it.

Two official DANE service item records provide current-source leads. `DIVIPOLA MGN 2024` explicitly describes DIVIPOLA levels under Colombia's MGN version 2024 and names DANE as access-information authority. The official `Centros Poblados Divipola 2013I` item identifies DANE and an older settlement-point service. Their exact item metadata bytes, item/service URLs, retrieval dates and hashes are retained. The item metadata leaves `licenseInfo` blank. The public service endpoint returned a network-edge block page, not ArcGIS layer metadata or feature rows; the packet therefore does not claim a current row-level DANE crosswalk, settlement match, or license for those service rows. Restoration instructions are in `sources.json`.

For parent-name continuity only, the existing hierarchy's 2017 geoBoundaries ADM1 source is explicitly identified as OpenStreetMap/Wambacher, ODbL 1.0, canonical role Departments. Its complete metadata and compressed geometry are retained. This source can identify a department-name candidate but is not treated as an official DANE check. The DANE 2024 service row for each department remains to be restored.

## Granularity, parent roles and edge cases

The source's 1,122 features are all ADM2; the assigned 194 are each single Polygons with no interior rings or multipart components. Province-size screening uses approximate spherical area only to compare each 2020 municipality with its matched 2017 OSM department polygon. Caquetá's Solano (`gb:COL:ADM2:7082276B1556586451217`) is approximately 46.96% of that department's source area, a notable scale outlier that needs official DANE area comparison and a semantic suitability assessment. This ratio is not proof of an error and is not an EU5 quota. Largest-location shares for Antioquia, Caldas and Sucre are also recorded in the machine inventory.

All four province cohorts are exhaustively enumerated, including their full descendant counts; each parent currently has a DANE-declared municipality source family and a weaker OSM-derived department-name candidate. Their parent identities and complete chains are recorded, but the source-role/footprint and neighboring-purpose decisions remain open. Colombia's area record is partial, so it must be reconciled with the other Colombia packets before integration.

Current source and Atlas geometries are summarized for all 194. The packet has not established complete settlement inventories, town roles, coast/island names, hydrology, detached administrative territories, source-to-current edge precision, or neighbor consistency against Ecuador, Brazil, Peru, Panama and Venezuela. No inter-region correction is inferred. If the official-source restoration shows a shared-edge inconsistency, report it to #489 and the affected owner before proposing any change. Geographic identity is recorded separately from present political reference and historical sovereignty.

## Reproduction

From a fresh current-main checkout with this packet's retained inputs:

```sh
python3 data/regional-review/regional-review-b2e551685bf2e064/build_assessment.py
python3 data/regional-review/regional-review-b2e551685bf2e064/verify.py
```

The build rechecks the raw ADM2 digest, exact 1,122-member source count and unique IDs, all 194 assignment IDs, and the matched ADM1 reference count. `verify.py` checks every location and province decision, source hashes and that outputs remain an evidence packet; neither script changes baseline geography.

## Next bounded research

Restore the DANE DIVIPOLA MGN 2024 service layer metadata and municipality/department rows, obtaining its reuse license; compare all 194 IDs and names to the current official roster, including the three duplicate-name pairs. Retrieve DANE Centros Poblados point features with layer-level license and perform a complete point-to-polygon settlement screen for all 194. Obtain authoritative coastline/island/hydrography and land-component evidence for the coastal municipalities. Investigate Solano's relative scale using DANE 2024 statistics and full-area context. Preserve unknowns and route shared-edge findings to coordinated review. This evidence packet does not certify the regional branch or enable historical imports.

# Colombia batch 2: DANE current code and settlement crosswalk

This evidence packet addresses issue [#587](https://github.com/ChengshuLi/WorldAtlas/issues/587), a source-restoration follow-up to [#491](https://github.com/ChengshuLi/WorldAtlas/issues/491). It covers the exact 190 pinned Colombia municipality IDs and their seven Atlas department parents. The 190-member digest is `6032775e1f381a259382697c034ab51f61dcc1bbdc8ef90d51bb3bbb36c0037d`.

## Reproduced current DANE crosswalk

The DANE Geoportal's DIVIPOLA June 2026 municipal workbook contains 1,122 administrative rows nationwide. I matched every assigned 2020 geoBoundaries source identity to one DANE municipality by department and normalized name. The join produced 190 unique current five-digit DANE codes and 190 `Municipio` roles. It accounts for all seven department cohorts:

| DANE department | Code | Assigned municipalities | CM seat points | CP center points | Total point rows |
|---|---:|---:|---:|---:|---:|
| Cauca | 19 | 42 | 42 | 607 | 649 |
| Córdoba | 23 | 30 | 30 | 573 | 603 |
| Huila | 41 | 37 | 37 | 173 | 210 |
| Putumayo | 86 | 13 | 13 | 127 | 140 |
| Quindío | 63 | 12 | 12 | 84 | 96 |
| Risaralda | 66 | 14 | 14 | 155 | 169 |
| Valle del Cauca | 76 | 42 | 42 | 522 | 564 |
| **Total** |  | **190** | **190** | **2,241** | **2,431** |

182 municipality names match after only case and diacritic normalization. Eight source-name differences use explicit aliases, each unique within its department: Puracé (Coconuco) → Puracé; San Miguel (La Dorada) → San Miguel; López → López de Micay; Purísima → Purísima de la Concepción; Piendamó → Piendamó - Tunia; Cali → Santiago de Cali; Sotará (Paispamba) → Sotará; Buga → Guadalajara de Buga. The output records each alias and both original/current names. Each of the 190 municipalities has exactly one DANE `CM` row; its listed longitude and latitude exactly match the municipality workbook's localization. `CP` rows are retained as named point records, not polygons.

The generated [current crosswalk](current-crosswalk.json) has one row per assigned subject. The generated [settlement CSV](settlement-records.csv) has all 2,431 source rows selected by the DANE municipality code, including all 190 municipal-seat rows and 2,241 named `CP` rows. The [verification summary](verification.json) records these counts. The [subject input snapshot](subject-inputs.json) preserves exact parent issue IDs, source names and Atlas department parents; `verify.py` checks that snapshot against the original #491 scope and assessment Git blobs at commit `73be9d0801a3cab46a0e24a7b030bb8204d79a71` and their SHA-256 hashes.

## Source bytes, date, terms and method

The two retained source workbooks are original DANE Geoportal downloads, retrieved 2026-10-04:

- `sources/DIVIPOLA_Municipios.xlsx` — [DANE Geoportal download](https://geoportal.dane.gov.co/descargas/divipola/DIVIPOLA_Municipios.xlsx), worksheet title identifies DIVIPOLA June 2026; 299,758 bytes; SHA-256 `cfcf906ce39bc50d8413ae060969e93c446ba8da6785b6247621de719321506b`.
- `sources/DIVIPOLA_CentrosPoblados.xlsx` — [DANE Geoportal download](https://geoportal.dane.gov.co/descargas/divipola/DIVIPOLA_CentrosPoblados.xlsx), worksheet title identifies DIVIPOLA June 2026; 1,039,763 bytes; SHA-256 `4a5a3918140fe43c54392a24d86f153183c90a30c459e25ddaec3e21db96fbe5`.
- `sources/dane-geoportal-license.html.gz` preserves the exact compressed original bytes of DANE's [license and use terms](https://geoportal.dane.gov.co/acerca-del-geoportal/licencia-y-condiciones-de-uso/); the original HTML bytes are restored with `gzip -dc`. The page says DANE-produced georeferenced information is offered under CC BY 4.0 and gives the attribution: “Departamento Administrativo Nacional de Estadística - DANE: www.dane.gov.co”.
- Unmodified Datos Abiertos Colombia and DANE ArcGIS item metadata are retained under `sources/`; source dates, canonical references, byte counts and SHA-256 values are recorded in [sources.json](sources.json).

The reproducible method preserves source code strings and leading zeros, normalizes only case and diacritics for ordinary name joins, and uses eight explicit source-name aliases where DANE's current official name differs. Settlement rows are selected by their five-digit department/municipality code, then linked to the pinned location through the one-to-one crosswalk. No settlement coordinates were recalculated. This is an administrative identity/code crosswalk and settlement-point inventory; no area or boundary metric is calculated.

## DANE MGN 2024 geometry remains unresolved

DANE's public MGN/DIVIPOLA 2024 catalog and item metadata identify department layer 319, municipality layer 317, and settlement layer 305. The metadata supplies the official fields and roles. The ArcGIS item and catalog mark the services public but leave their per-item license fields blank; the DANE Geoportal's CC BY 4.0 terms page supplies the stated license for georeferenced information produced by DANE. Metadata responses and hashes are preserved.

The official DANE CDGE GeoJSON download route returned HTTP 500 for department layer 319 and municipality layer 317. Issue #587 already records that earlier direct layer metadata/row queries returned network-edge HTML; those same blocked queries were not repeated. `source-access.json` records the exact tested routes, results and restoration request. No MGN 2024 feature rows or polygons were obtained, so this packet does not claim those 2026 codebook rows are the 2024 MGN boundaries, and it does not certify any boundary, coastline, island, administrative remainder, disconnected territory, parent footprint or neighboring consistency. The source pointer `Centros Poblados Divipola 2013I` is historical and was not substituted for current coverage. The June 2026 workbook provides dated current DANE point records with the completeness limits stated above.

The remaining bounded request is for DANE or a maintainer to provide lawful, dated layer 319 and 317 feature exports with geometry, schema/CRS, DIVIPOLA IDs, version date, license/attribution and hashes through a supported route. If June 2026 is not the accepted settlement vintage, provide layer 305 rows on the same terms. No political ownership or historical attributes are inferred from these present-day administrative/settlement records. No regional approval or import authority follows.

## Reproduction

From this directory:

```sh
python3 build_evidence.py
python3 verify.py
```

The verifier checks all retained-byte hashes, the pinned parent source blobs, all 190 one-to-one municipality codes, all seven complete department cohorts, all 2,431 point rows, the 190 coordinate matches and a duplicate-code negative control. Generator output is deterministic. The settlement CSV has 2,431 data rows plus its header and is generated evidence for the complete assigned scope; line accounting is separate from handwritten code.

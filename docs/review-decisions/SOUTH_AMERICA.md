# South America: complete inventory and sourced correction batch

This review independently inventoried every current South American branch: **462 groups and 3,966 polygon locations**, including French Guiana, Falklands, South Georgia/South Sandwich and the Southern Patagonian Ice Field. All four subcontinents, five regions, 53 areas and 399 provinces were inspected top down. The JSON retains each original ID, source/vintage/license distribution, actual membership and geometry findings. **No complete regional branch or location has been declared semantically approved.**

## Directly implementable corrections

- `framework:province:belem:1c6524fe0af9`: **merge** Belém → `framework:province:belem:46a8c1974feb`.
- `framework:province:gurupi:f6109818fc8b`: **merge** Gurupi → `framework:province:gurupi:2f2786a71a4d`.
- `framework:province:salvador:ff278f1343f2`: **merge** Salvador → `framework:province:salvador:9f86adb6c8bd`.
- `framework:province:rio-de-janeiro:6c61645d2d0a`: **reparent** Rio de Janeiro → `framework:area:rio-de-janeiro:2755e059cb9c`.
- `framework:province:sao-paulo:13b8a9622e26`: **reparent** São Paulo → `framework:area:sao-paulo:2543c19d3cdd`.
- `framework:province:rio-verde:fbc819ad65e7`: **merge** Rio Verde → `framework:province:rio-verde:bb0c9195244c`.
- `framework:province:distrito-federal:56d6a7096ab7`: **reparent** Distrito Federal → `atlas:semantic-review:area:bra-distrito-federal`.
- `framework:province:caaguazu:46f0b385f436`: **rename** CAAGUAZU → CAAGUAZÚ.
- `framework:province:caazapa:8ad88cdcd6ab`: **rename** CAAZAPA → CAAZAPÁ.
- `framework:province:paraguari:44ec92460a9b`: **rename** PARAGUARI → PARAGUARÍ.
- `framework:province:neembucu:38570c4a9dad`: **rename** ÑEEMBUCU → ÑEEMBUCÚ.
- `framework:province:itapua:f690c4187941`: **rename** ITAPUA → ITAPÚA.
- `framework:province:concepcion:b0bf611fc49a`: **rename** CONCEPCION → CONCEPCIÓN.
- `framework:province:guaira:ef0d15a23b9e`: **rename** GUAIRA → GUAIRÁ.
- `framework:province:alto-parana:e2d2fcc6ce30`: **rename** ALTO PARANA → ALTO PARANÁ.
- `framework:province:canindeyu:07820ecea834`: **rename** CANINDEYU → CANINDEYÚ.
- `framework:province:boqueron:36a3b944f331`: **rename** BOQUERON → BOQUERÓN.
- `framework:area:surinam:a9cce4a3771f`: **rename** Surinam → Suriname.
- `framework:area:falkland-is:aa9151e086ab`: **rename** Falkland Is. → Falkland Islands.
- `framework:area:guyane-francaise:0490ec40938a`: **rename** Guyane française → French Guiana.
- `framework:province:guyane-francaise:661840254929`: **rename** Guyane française → French Guiana.
- `framework:area:south-georgia:2cb092c9700c`: **rename** South Georgia → South Georgia and the South Sandwich Islands.
- `atlas:parent-evidence:area:86f78eb492586db3`: **merge** Paraguay → `framework:area:paraguay:b8f36a1a90ee`.
- `atlas:parent-evidence:province:58ff7bb30b4e963b`: **merge** PRESIDENTE HAYES → `framework:province:presidente-hayes:49bc9023041b`.
- `atlas:semantic-review:area:bra-distrito-federal`: **create** (new area) → Distrito Federal → `framework:region:brazil:bc51c04eeaf4`.

All changes preserve identity, original aliases, geometry and history. Merge dispositions retain source identities in the archive; they consolidate duplicate geographic membership and do not transfer old evidence to a different location. Parent corrections have independent official code evidence and do not certify every child’s local granularity. Empty obsolete botanical ancestors must be archived by the integration migration.

## Exhaustive country and dependency findings

These are actual continent members, rather than national-profile totals. Chile's Rapa Nui and Colombia/Venezuela's Caribbean units illustrate why owner and continent membership must remain separate.

| Reference territory | Current locations in South America | Inspected role and unfinished correction |
| --- | ---: | --- |
| Argentina | 509 | 2020 departments/partidos plus one Federal District city envelope: compare all 509 current territories with the official Georef 529-entry department/comuna catalogue; Buenos Aires aggregation and source vintage prevent count equality from proving completeness. |
| Bolivia (Plurinational State of) | 117 | 2015 province polygons plus RESOLVE physical subdivisions are coarser than municipal local geography. Audit full licensed municipal coverage and each ecological split; do not invent anonymous residual polygons. |
| Brazil | 765 | Complete official code crosswalk supports hierarchy corrections but not immediate-region rural aggregation as equivalent local territories. Independently retained major cities and physical subdivisions need a settlement/functional review in every state. |
| Chile | 344 | 2020 commune source. Official INE APC 2023 page documents 80 field-enumerated plus 265 other communes excluding Antarctica and publishes a 2024 geodata framework; current 344 continental locations plus Rapa Nui in Oceania require source-vintage and island accounting. |
| Colombia | 1122 | 2020 municipios. Current continental branch has 1122 locations; its 1124-location owner profile spans other continental branches. Large Amazonian source units and country-sized area grouping remain open; the DANE DIVIPOLA request was blocked and is not counted as inspected evidence. |
| Ecuador | 224 | 2019 cantons are a plausible local territory role, but every canton/island and whole-country area requires dated administrative/functional assessment; failed INEC geoportal request does not approve boundaries. |
| Guyana | 27 | 2019 source canonical role is Neighbourhood Councils but only 27 polygons; independently compare NDCs, municipalities and interior geography rather than assume a complete current council inventory. |
| Peru | 204 | 2020 provinces plus named physical subdivisions remain too coarse compared with neighboring municipios/cantons. Acquire complete licensed district territories, preserving sparse geographic exceptions and original history. |
| Paraguay | 243 | 2012 source reference remains valid only at its recorded date. Official INE 2012 catalogue has 18 department/capital records and 250 district rows; current 243 locations cannot be certified from count similarity. Correct exact parent duplicates and spelling; review every municipality/source omission. |
| Suriname | 59 | 2021 ressort source comprises 59 current locations; official statistical page explicitly offers district and ressort profiles, supporting separate roles but not current polygon/municipal counts. City ressort fragmentation still requires functional evidence. |
| Uruguay | 19 | All 19 locations are 2017 departments with repeated department province tiers. Evaluated 124 municipality polygons lack complete rural coverage and cannot replace them with nearest-town filler; obtain licensed census/local geography with complete named rural territory. |
| Venezuela (Bolivarian Republic of) | 327 | 2015 municipios plus dependencies/physical adaptations. Continental branch 327 differs from the 339-location national profile due Caribbean geography; preserve cross-continent islands and evaluate municipality completeness/vintage and urban fragmentation independently. |
| Falkland Islands | 1 | One whole-archipelago location, 15 components. East/West Falkland, Stanley functional territory and smaller-island clusters need usable source footprints and a licensed subdivision proposal; a repeated single-member hierarchy is not yet a justified local-scale exception. |
| Southern Patagonian Ice Field | 1 | One uninhabited physical reference territory with an independent Natural Earth disputed-reference label; resolve physical source role and dated owner separately, and never manufacture a settlement rank. |
| France | 3 | French Guiana has three coarse biome fragments. Actual official geo API supplies 22 named commune contours, all valid, covering 99.1943% of the current footprint in an EPSG:6933 comparison. Confirm boundary source/vintage/license and preserve existing physical IDs in an explicit replacement migration. |
| South Georgia and the Islands | 1 | One 17-component disconnected territory spans South Georgia and the South Sandwich Islands. Complete source-name correction is supported; local archipelago subdivision and continent convention remain open. |

## Actual source evidence

- Re-fetched and decoded the [IBGE municipality JSON](https://servicodados.ibge.gov.br/api/v1/localidades/municipios), [intermediate-region JSON](https://servicodados.ibge.gov.br/api/v1/localidades/regioes-intermediarias), [immediate-region JSON](https://servicodados.ibge.gov.br/api/v1/localidades/regioes-imediatas), and [27-UF JSON](https://servicodados.ibge.gov.br/api/v1/localidades/estados). The responses contain 5,571 municipalities, 133 intermediate regions and 510 immediate regions. Actual code chains resolve all source members of 763/765 current Brazilian locations. Two municipal source names remain ambiguous (Campestre and Pinhão); their exact aggregate IDs are retained in the JSON. The 2020 geometry contains 5,570 municipalities: current API count is not silently treated as its vintage.
- Inspected [Brasília's exact code chain](https://servicodados.ibge.gov.br/api/v1/localidades/municipios/5300108): Brasília 5300108 → Distrito Federal immediate 530001 → Distrito Federal intermediate 5301 → Distrito Federal UF 53. The official province name is **Distrito Federal**, not Brasília; the missing area can therefore be created without inventing a tier.
- Inspected [Paraguay INE's actual 2012 department JSON](https://www.ine.gov.py/microdatos/register/localidades/Departamentos_Paraguay_Codigos_DGEEC.json) and [district JSON](https://www.ine.gov.py/microdatos/register/localidades/Distritos_Paraguay_Codigos_DGEEC.json). These provide 18 department/capital and 250 district entries, plus attested spellings. The source page explicitly identifies the Paraguayan public-information-use license. This is label/identity evidence; existing geometry licenses and represented dates remain intact. Presidente Hayes fragments were measured against the pinned source shape `63826900B99929286362746` / `PY-15`, not matched only by a similar name.
- Inspected [French Guiana's actual 22 commune contours](https://geo.api.gouv.fr/departements/973/communes?fields=nom,code,contour&format=geojson&geometry=contour), including Cayenne, Kourou, Matoury and the interior communes. All contours are valid. Their union covers 99.1943% of existing atlas land in EPSG:6933 equal-area calculation; original and candidate unions were repaired only for that calculation. Source boundary license/vintage and an explicit preserved-identity replacement migration are still required before import. The API software README is documentation, not a license certification for the contours.
- Inspected [Argentina Georef's actual department catalogue](https://apis.datos.gob.ar/georef/api/departamentos?campos=id,nombre,provincia&max=1000): 529 entries. That national catalogue includes different roles and vintages; it does not approve the current 509 atlas territories.
- [Chile INE Geodatos Abiertos](https://www.ine.gob.cl/herramientas/portal-de-mapas/geodatos-abiertos) explicitly distinguishes region, province, commune and census district, and states the APC2023 split of 80 field-updated plus 265 other communes excluding Antarctica. The published 2024 base is a source-update lead, not evidence already imported. [Suriname's official census page](https://statistics-suriname.org/en/census-statistics-2/) distinguishes district and ressort profiles.
- Actual South Georgia/South Sandwich [government page](https://gov.gs/south-georgia-the-south-sandwich-islands/) and the current 17-component member footprint support the complete area label. Local archipelago subdivision remains open. [UN M49](https://unstats.un.org/unsd/methodology/m49/overview/) supports the English reference-name corrections; [WGSRPD README](https://raw.githubusercontent.com/tdwg/wgsrpd/master/README.md) establishes the botanical purpose of the inherited framework rather than certifying atlas administrative tiers.

## Geometry and completion gates

All 3,966 current location geometries are valid and nonempty; all 462 actual member-derived parent unions are valid. This verifies source structure, **not local purpose, coverage, temporal validity or appropriate granularity**. Every province has its full exact member inventory and independent remaining reasons in `location_review`; no descendants are approved solely because a source is official. There are no geometry mutations or arbitrary cell assignments in this batch.

Still open throughout the continent: country-envelope regions/areas, all local aggregation purpose, broad Bolivian/Peruvian/Uruguayan units, fragmented urban localities, licensed complete finer coverage, island/sparse-territory exceptions, reference vintages and topological masking. The blocked official requests are recorded as failures rather than counted as evidence. Top-down semantic completion must revisit each exact open ID after source-backed correction and an independent child assessment.

## Additional finer-coverage leads inspected after the correction batch

**Bolivia:** all 339 pinned `gbOpen/BOL/ADM3` polygons were inspected (all valid), and their union covers **99.9793%** of existing continental land in EPSG:6933. The actual [metadata](https://www.geoboundaries.org/api/current/gbOpen/BOL/ADM3/) identifies 2015/public-domain boundaries but canonical role **Unknown**. This cannot be approved merely because the integer is ADM3; a primary dated municipal/administrative registry is still needed. The source GeoNetwork request was blocked. Geometry hash and exact remaining conditions are in `candidate_sources`.

**Peru:** the [gbHumanitarian ADM3 metadata](https://www.geoboundaries.org/api/current/gbHumanitarian/PER/ADM3/) provides a 1,873-unit, 2015, CC BY 3.0 IGO candidate. The actual [HDX package JSON](https://data.humdata.org/api/3/action/package_show?id=cod-ab-per) names **Instituto Geográfico Nacional (IGN)** as source, and explicitly separates 24 July 2015 boundary creation/edit, 14 July 2020 humanitarian valid-for-use, and 30 October 2025 quality review. It exposes complete GeoJSON, SHP, GDB and tabular resources. Those source dates are not interchangeable. Candidate geometries, primary tier purpose and coverage still need inspection; this is a concrete import lead, not an approved replacement. `gbOpen` and `gbAuthoritative` ADM3 queries failed, so their absent results are not counted as inspected geometry.

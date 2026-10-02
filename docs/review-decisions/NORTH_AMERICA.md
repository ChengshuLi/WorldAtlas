# North America semantic decisions

This batch inventories **all 557 current groups and 7,869 locations across 47 reference-owner groups**. The inventory and exact-ID dispositions are in [north-america.json](../../data/geographic-decisions/north-america.json). **Semantic completion is not claimed.** A sourced rename/parent correction does not certify every child footprint, settlement identity or 2026 administrative boundary.

## Executable corrections

* Reparent Bermuda’s area from Caribbean to existing Southeastern North America using a documented western-North-Atlantic convention. The Bermuda government explicitly places it opposite North Carolina and over 1,200 km north of the nearest Caribbean island. No Bermuda-sized macro-region is created.
* Merge 12 accidental Mexican state fragments only after checking all 2,441 original municipality geometries against every candidate pinned state. Exact source parent IDs, original hashes and per-location shares are recorded; names alone were not used. All 31 municipalities with state-source coverage below 95% remain open.
* Merge 16 duplicate Canadian physical provinces already sharing the same area, with identical verified AAFC ECOPROVINCE_ID. Retain clipped local IDs and archive retired group identities; do not merge different provinces or administrative source roles.
* Rename misleading Netherlands Antilles to its exact source-member geography Curaçao and Bonaire; expand source island abbreviations; adopt official current INEGI identity names while preserving source dates and historical aliases.
* Retain all nine US Census division areas after checking actual source-state membership against the official list. Their county/state children remain open; Pacific is explicitly the North-American component because Hawaii follows physical Oceania geography.

## Every current regional branch (before migration)

| Region | Areas | Provinces | Locations | Remaining regional work |
| --- | ---: | ---: | ---: | --- |
| Caribbean | 18 | 153 | 551 | Bermuda parent correction proposed; dissolved label correction proposed. Full island/commune granularity, dispersed territory exceptions and country-independent maritime scope remain open. |
| Central America | 8 | 105 | 1225 | Every department/province/district profile is inventoried. Salvador source count/reform, Costa Rican missing newer canton, Panama indigenous/current geography and country-envelope purposes remain open. |
| Northeastern North America | 6 | 58 | 464 | Canadian municipal/division/physical roles, all US source counties, modern Connecticut changes, city aggregations and Saint Pierre/Miquelon archipelago scope remain open. |
| Interior North America | 3 | 40 | 1108 | Canadian duplicate ecoprovince merges proposed; whole-state local-cluster purposes, all rural/city source aggregations and multi-jurisdiction physical boundaries remain open. |
| Western North America | 3 | 27 | 533 | Alaska remote ecological adaptation, administrative source truncations, municipal city extents and physically named local boundaries remain open. |
| Subarctic America | 4 | 49 | 125 | All Greenland and Canadian northern local territories inspected for footprint scale, names and sources. Rock/Ice class labels, national park scale, remote settlements, Pituffik and ecological clipping remain open. |
| Mexico | 6 | 44 | 2442 | All 2,441 source municipality/state relations checked;12 accidental fragment group merges proposed. Botanical macro-areas,31 source coverage discrepancies, city extent and finer functional province clusters remain open. |
| Southeastern North America | 3 | 18 | 1421 | Bermuda North Atlantic convention correction; whole-state local cluster purposes, independent cities and county/source-vintage changes remain open. |

## Every reference owner represented in this continent

| Reference owner | Locations | Actual source roles | Remaining work |
| --- | ---: | --- | --- |
| Anguilla | 1 | Compact source country/territory (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Antigua and Barbuda | 1 | Compact source country/territory (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Aruba | 1 | ADM1 fallback (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Bahamas | 32 | Districts (32) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Bajo Nuevo Bank (Petrel Is.) | 1 | ADM0 fallback (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Barbados | 1 | Compact source country/territory (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Belize | 6 | Districts (6) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Bermuda | 1 | Compact source country/territory (1) | A coherent small island territory is a defensible location role; area must leave Caribbean botanical convenience grouping. Published environment report has parish land-use information, but no new parish subdivision is implied. |
| British Virgin Islands | 1 | ADM1 fallback (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Canada | 478 | Named local administrative territory (33), Statistics Canada named county / regional district; separately mapped major cities excluded (176), Named physical region (269) | Municipality/census-division/physical-ecoregion roles are mixed. All 478 actual names were checked: no live numbered/unorganized administrative-remainder label remains. Retained municipalities, larger division aggregates and 269 ecological adaptations need independently significant settlement and source-clipping checks; sparse land is not automatically a settlement. |
| Caribbean Netherlands | 1 | Special Municipality (1) | Bonaire is a named island/special municipality; retain geography independently of ownership and remove misleading Netherlands Antilles area label. |
| Cayman Islands | 1 | ADM1 fallback (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Colombia | 2 | Municipality (2) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Costa Rica | 83 | Canton (83) | Named local references and source vintages were inspected, with independent secondary taxonomy corroboration; actual current groups and every member ID are inventoried, but primary dated boundaries/local-purpose checks remain open. |
| Cuba | 168 | Municipality (168) | Named local references and source vintages were inspected, with independent secondary taxonomy corroboration; actual current groups and every member ID are inventoried, but primary dated boundaries/local-purpose checks remain open. |
| Curaçao | 1 | ADM1 fallback (1) | Whole-island local territory is plausible; retain separate polity identity and review settlement/footprint role. Replace dissolved political area label with the source’s exact geographic components. |
| Dominica | 1 | Compact source country/territory (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Dominican Republic | 155 | Municipalities (155) | Named local references and source vintages were inspected, with independent secondary taxonomy corroboration; actual current groups and every member ID are inventoried, but primary dated boundaries/local-purpose checks remain open. |
| El Salvador | 271 | Municipalities (271) | The2007 source calls271 retained geometries municipalities (source 272). Secondary updated Spanish listing describes2023law762 replacing262 municipalities with 44 municipalities and former municipalities as districts. This cardinality/vintage/role discrepancy requires legal and full-source crosswalk; failed primarylaw download is not counted as confirmation. |
| France | 3 | Overseas department (2), Named territory (1) | Martinique and Guadeloupe are whole-department locations while ordinary local municipalities exist; this is a concrete granularity mismatch. Clipperton is a named remote atoll exception, independent from French political affiliation. |
| Greenland | 11 | Municipalities (11) | Five municipal identities and the huge national park are corroborated; actual11 locations include rock/ice and tundra portions. Rock and Ice is a class, not a named local territory; settlements, national park subdivisions, Pituffik enclave coverage and full island coastline remain open. |
| Grenada | 1 | Compact source country/territory (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Guatemala | 342 | Municipality (342) | Named local references and source vintages were inspected, with independent secondary taxonomy corroboration; actual current groups and every member ID are inventoried, but primary dated boundaries/local-purpose checks remain open. |
| Haiti | 42 | Arrondissement (42) | Named local references and source vintages were inspected, with independent secondary taxonomy corroboration; actual current groups and every member ID are inventoried, but primary dated boundaries/local-purpose checks remain open. |
| Honduras | 298 | Municipality (298) | Named local references and source vintages were inspected, with independent secondary taxonomy corroboration; actual current groups and every member ID are inventoried, but primary dated boundaries/local-purpose checks remain open. |
| Jamaica | 14 | parish (14) | Named local references and source vintages were inspected, with independent secondary taxonomy corroboration; actual current groups and every member ID are inventoried, but primary dated boundaries/local-purpose checks remain open. |
| Mexico | 2442 | municipios (2441), Source city territory: Federal District (1) | Inspected all 2,441 original municipality geometries against pinned source states; source administrative affiliation is supported, not blanket local geometry approval.2012 vintage,31<95% state-coverage cases, one Distrito Federal city aggregation, Oaxaca’s570 local members and regional botanical envelopes remain explicit issues. |
| Montserrat | 1 | Compact source country/territory (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Netherlands | 2 | Special Municipality (2) | Saba and St Eustatius are named island/special-municipality locations in Caribbean geography; political Netherlands must not move them to Europe. |
| Nicaragua | 153 | Named local administrative territory (153) | Named local references and source vintages were inspected, with independent secondary taxonomy corroboration; actual current groups and every member ID are inventoried, but primary dated boundaries/local-purpose checks remain open. |
| Panama | 76 | District (76) | Named local references and source vintages were inspected, with independent secondary taxonomy corroboration; actual current groups and every member ID are inventoried, but primary dated boundaries/local-purpose checks remain open. |
| Puerto Rico | 78 | Municipality (78) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Saint Barthelemy | 1 | ADM1 fallback (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Saint Kitts and Nevis | 1 | Compact source country/territory (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Saint Lucia | 1 | Compact source country/territory (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Saint Martin | 1 | ADM1 fallback (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Saint Pierre and Miquelon | 1 | Compact source country/territory (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Saint Vincent and the Grenadines | 1 | Compact source country/territory (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Serranilla Bank | 1 | ADM0 fallback (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Sint Maarten | 1 | ADM1 fallback (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Trinidad and Tobago | 14 | Named local administrative territory (14) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| Turks and Caicos Islands | 1 | Compact source country/territory (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| US Naval Base Guantanamo Bay | 1 | ADM1 fallback (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| United States Minor Outlying Islands | 1 | ADM1 fallback (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| United States Virgin Islands | 1 | Compact source country/territory (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |
| United States of America | 3162 | Counties (3161), Five boroughs of New York City (1) | County-equivalent local reference is defensible, but2018 vintage differs from modern Connecticut; county-based city aggregation and Alaska’s ecologically clipped census areas still need functional/local review. |
| Venezuela (Bolivarian Republic of) | 12 | Municipios (11), Federal Dependency (1) | Named whole-island/archipelago exception requires full subordinate island, settlement and source-footprint review; ownership never determines continental geography. |

## Source and verification limits

Official data actually inspected: US Census division/state text and county-level/change guidance; Statistics Canada SGC 2021; AAFC framework plus hash-pinned ecology snapshots; Bermuda government environment PDF; Dutch constitutional change page; INEGI 32-entity JSON; French official APIs enumerating34Martinique and 32Guadeloupe communes. WGSRPD2001 introduction/table is read directly: it admits Bermuda’s Caribbean placement is for convenience. Its botanical groupings are not automatically physical atlas tiers.

Secondary taxonomies corroborate local roles across Guatemala, Honduras, Nicaragua, Costa Rica, Panama, Haiti, Jamaica, Cuba, Dominican Republic and Greenland. Salvador’s updated Spanish listing identifies44 new municipalities/262 districts; primary law requests returned503, so legal confirmation stays open. Landing pages, JavaScript shells, failed403/404/503responses and empty country navigation were not accepted as full administrative listings. Source receipts retain failures and response hashes.

All 7,869 current polygon geometries passed local validity inspection. WGS84 diagnostic area/bounds/component counts are recorded for every location; these are screening measurements, not population/settlement classifications or approval of coastline coverage. No anonymous numbered/unorganized current location names remain in this continent, but source aliases and archival history are retained. Very large northern units, disconnected footprints, ecological adaptations, settlement aggregations, undated references, source-state coverage discrepancies, departmental island envelopes and dated reforms each carry exact open location IDs.

The JSON partition assigns every current location exactly once to an open location-review record and every current hierarchy group exactly once to a decision. No quotas, equal-area tessellation, invented settlements, ancient modern-name backfill or geometry mutation were used.

## Evidence links

* [Brummitt, WGSRPD second edition (2001)](https://raw.githubusercontent.com/tdwg/wgsrpd/52da7828aba9d461dd133c27b3bd7a4407161f54/109-488-1-ED/2nd%20Edition/TDWG_geo2.pdf)
* [Bermuda Government Department of Planning, State of the Environment](https://planning.gov.bm/wp-content/uploads/2018/11/State-of-the-Environment.pdf)
* [Government of the Netherlands, Caribbean parts of the Kingdom](https://www.government.nl/topics/caribbean-parts-of-the-kingdom)
* [Administrative taxonomy of Cuba (secondary)](https://en.wikipedia.org/wiki/Municipalities_of_Cuba)
* [Administrative taxonomy of Dominican Republic (secondary)](https://en.wikipedia.org/wiki/Municipalities_of_the_Dominican_Republic)
* [French official geographic API, Martinique communes](https://geo.api.gouv.fr/departements/972/communes?fields=nom,code&format=json)
* [French official geographic API, Guadeloupe communes](https://geo.api.gouv.fr/departements/971/communes?fields=nom,code&format=json)
* [Administrative taxonomy of Haiti (secondary)](https://en.wikipedia.org/wiki/Arrondissements_of_Haiti)
* [Administrative taxonomy of Honduras (secondary)](https://en.wikipedia.org/wiki/Municipalities_of_Honduras)
* [Administrative taxonomy of Jamaica (secondary)](https://en.wikipedia.org/wiki/Parishes_of_Jamaica)
* [Administrative taxonomy of Nicaragua (secondary)](https://en.wikipedia.org/wiki/Municipalities_of_Nicaragua)
* [US Census Bureau geographic levels](https://www.census.gov/programs-surveys/economic-census/guidance-geographies/levels.html)
* [US Census Bureau county-equivalent changes in 2020s](https://www.census.gov/programs-surveys/geography/technical-documentation/county-changes/2020.html)
* [Statistics Canada SGC 2021](https://www.statcan.gc.ca/en/subjects/standard/sgc/2021/index)
* [AAFC National Ecological Framework for Canada](https://sis.agr.gc.ca/cansis/nsdb/ecostrat/index.html)
* [Administrative divisions of Greenland (secondary)](https://en.wikipedia.org/wiki/Administrative_divisions_of_Greenland)
* [Administrative taxonomy of Costa Rica (secondary)](https://en.wikipedia.org/wiki/Cantons_of_Costa_Rica)
* [Updated municipalities of El Salvador (secondary)](https://es.wikipedia.org/wiki/Anexo:Municipios_de_El_Salvador)
* [Administrative taxonomy of Guatemala (secondary)](https://en.wikipedia.org/wiki/Municipalities_of_Guatemala)
* [INEGI geographic entity catalog API](https://gaia.inegi.org.mx/wscatgeo/v2/mgee/)
* [Pinned geoBoundaries Mexico state polygons](https://github.com/wmgeolab/geoBoundaries/raw/90a1d52/releaseData/gbOpen/MEX/ADM1/geoBoundaries-MEX-ADM1.geojson)
* [Administrative taxonomy of Panama (secondary)](https://en.wikipedia.org/wiki/Districts_of_Panama)
* [US Census Bureau regions/divisions and state FIPS codes](https://www2.census.gov/geo/docs/maps-data/maps/reg_div.txt)

Current hierarchy input SHA256: `ababc53ece8f080ff266af21a57276cab8e47a79be0763635f731dcc9df25fca`. Corrections require migration/validation before publication; retained child openings prevent a semantic-complete claim.

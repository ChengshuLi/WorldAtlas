# Oceania exhaustive geographic decision review

Reviewed 1 October 2026. Every current Oceania group and member location was inventoried top-down: **1 continent, 5 subcontinents, 10 regions, 50 areas, 263 provinces, 1,559 locations and 30 reference-owner profiles**. Antarctica is excluded. Exact IDs and dispositions are in [oceania.json](../../data/geographic-decisions/oceania.json). This batch proposes identity/label/role corrections; it does not silently approve unresolved source geometry or historical values.

## Concrete corrections

- Consolidate the duplicate New Zealand North area into North Island, and the three-member duplicate Auckland source parent into its other Auckland Region identity. Preserve old groups in the migration archive; locations keep their identities and histories.
- Correct 10 reversible NZ UTF-8/Latin-1 name corruptions, preserving source spellings as aliases.
- Correct 435 Australian IBRA-adaptation roles, 21 Auckland local-board roles and one outside-territorial-authority role. Every IBRA fragment was checked against its exact original LGA shapeID and IBRA code, with source geometry repair confined to the diagnostic calculation; no atlas geometry was altered.
- Expand 20 inherited island abbreviations/archipelago labels and the one-island Lord Howe parent name. Names do not approve member coverage.
- Place Johnston Atoll under its own geographic area in North-Central Pacific. The inspected FWS source places it 716 nautical miles southwest of Honolulu; political owner remains independent. This isolated-atoll exception is based on named physical geography, not a group-count quota.

## Top-down regional decisions

| Region | Areas / provinces / locations | Findings and open work |
| --- | --- | --- |
| Australia | 10 / 13 / 943 | State-sized province groups duplicate state areas; derive sourced intermediate functional/geographic clusters. Separate metropolitan LGA fragments from functional city geography. All 435 rural IBRA adaptations were individually checked against their exact original LGA and named IBRA polygon; nine have under 95% planar correspondence after coastline/coverage additions and remain geometry-open. Other Territories joins Jervis Bay and Norfolk fragments. |
| Equatorial Micronesia | 2 / 3 / 3 | Gilbert and Line Islands plus the mislabeled Phoenix source remainder do not certify all Kiribati island land. Source remainder sits in the western equatorial Pacific, not the actual Phoenix archipelago; restore Phoenix coverage from inspected independent licensed island geometry. Nauru may justify a whole-island local exception, but source completeness remains open. |
| New Zealand and Southwest Pacific Islands | 6 / 25 / 94 | The exact 2021 source has 21 named Auckland local-board polygons, despite the published canonical tier Territorial Authorities; those are not 21 independent territorial authorities. Merge the duplicate Auckland parent and North Island botanical remainder. Preserve island/board names but review coherent city versus rural/island local territories. Area Outside Territorial Authority is a disconnected offshore residue, not Bay of Plenty alone. |
| North-Central Pacific | 1 / 3 / 7 | Hawaiian county territories include island/multi-island functional units; Kalawao is a compact separate county, not an automatically inferred settlement rank. Midway belongs to the northwest Hawaiian chain. Johnston is a separate isolated atoll 716 nautical miles southwest of Honolulu according to the inspected FWS refuge page; separate its geographic area from Hawaii. |
| Northwestern Pacific | 4 / 51 / 54 | Palau and Marshall 2017 OSM metadata explicitly say canonical role Unknown; actual named state/atoll purpose is not certified by ADM1. Four FSM whole states hide several distant island groups. Four CNMI territories have separate USA-source coastal residual duplicates; preserve both original IDs until a source-based union/replacement migration. Missing Marshall atolls and Kayangel require source-coastline repair. |
| Papuasia | 3 / 99 / 377 | 2019 PNG LLGs are local territories within named district clusters. Large Indonesian province parents from 2020 require dated 2022-reform treatment, and whole New Guinea area needs intermediate physical/administrative areas. Split Tawae/Siassi source district branches cannot be automatically rejoined across New Guinea/Bismarck physical areas. PNG Kimbe/Kerema/Balimo land losses remain open. |
| South-Central Pacific | 10 / 23 / 23 | French Polynesian five administrative subdivisions are archipelagos, not automatically local territories. Cook locations cover only 11 named islands; survey Suwarrow, Nassau and other published islands before approving completeness. Kiribati Line whole group requires island-level geographic purpose. Isolated Howland/Baker and Pitcairn repeated tiers require full named-island coverage, not distant atoll mergers. |
| Southern Indian Ocean Islands | 4 / 4 / 4 | TAAF explicitly distinguishes Crozet, Kerguelen and Saint-Paul/Amsterdam from Antarctic Adélie Land and tropical Éparses. Antarctic land is excluded. These isolated remote archipelagos may justify repeated local tiers, but grouping them under Oceania is a documented atlas convention requiring explicit physical-continent rationale rather than French/Australian affiliation. |
| Southern Melanesian Islands | 4 / 15 / 25 | The official Vanuatu statistics page explicitly distinguishes all six provinces from urban Port Vila and Luganville; current province locations omit this local distinction. Fiji 15 locations are provinces plus Rotuma, not county-level municipalities; city territories and broad archipelago provinces need a complete local-source alternative. New Caledonia three provinces are far broader than named communes. Santa Cruz/Temotu must remain geographic independently of Solomon state ownership. |
| Western Polynesian Islands | 6 / 27 / 29 | Samoa is a whole-country local adaptation while neighbouring units are named island groups; the official Samoa district-profile service is evidence for finer sourced geography research. Tonga groups, Tuvalu atolls and Wallis/Futuna traditional districts serve different roles. Five American Samoa geographic units also have five independent USA-source residual polygons; source replacement requires archived crosswalks. Tokelau is three separated atolls in one local source territory. |

## Every reference-owner profile

| Reference owner | Locations | Actual source roles |
| --- | --- | --- |
| American Samoa | 5 | unspecified reference territory (5) |
| Australia | 943 | Local Government Areas (940), Named territory (3) |
| Chile | 1 | Communes (1) |
| Cook Islands | 11 | unspecified reference territory (11) |
| Fiji | 15 | Provinces (15) |
| French Polynesia | 5 | unspecified reference territory (5) |
| French Southern and Antarctic Lands | 3 | Named territory (3) |
| Guam | 1 | unspecified reference territory (1) |
| Heard Island and McDonald Islands | 1 | Named territory (1) |
| Indonesia | 42 | regency, city (42) |
| Kiribati | 3 | Named local administrative territory (3) |
| Marshall Islands | 24 | Named local administrative territory (24) |
| Micronesia (Fed. States of) | 4 | State (4) |
| Nauru | 1 | unspecified reference territory (1) |
| New Caledonia | 3 | unspecified reference territory (3) |
| New Zealand | 94 | Territorial authority (88), Named territory (6) |
| Niue | 1 | unspecified reference territory (1) |
| Norfolk Island | 1 | unspecified reference territory (1) |
| Northern Mariana Islands | 4 | Municipality (4) |
| Palau | 16 | Named local administrative territory (16) |
| Papua New Guinea | 326 | Local Government Areas (326) |
| Pitcairn Islands | 1 | unspecified reference territory (1) |
| Samoa | 1 | unspecified reference territory (1) |
| Solomon Islands | 10 | Province (10) |
| Tonga | 5 | Named local administrative territory (5) |
| Tuvalu | 8 | Named local administrative territory (8) |
| United States Minor Outlying Islands | 7 | unspecified reference territory (7) |
| United States of America | 14 | Counties (14) |
| Vanuatu | 6 | Named local administrative territory (6) |
| Wallis and Futuna | 3 | unspecified reference territory (3) |

## Geometry and granularity findings

The source-role assessment is not a polygon approval. All 1,559 locations have an explicit open assessment partition and an individual ID/name/parent/role/vintage/license/bounds/flags row. This prevents unreviewed descendants from being bulk marked complete.

Australian state provinces contain up to hundreds of local territories and duplicate areas. ABS ASGS distinguishes functional statistical geography from LGA legal-cartographic references; a source-supported intermediate hierarchy is still needed. The 435 rural physical fragments are **IBRA subregion portions of an LGA**, not complete LGAs. Planar diagnostic source-intersection shares range from0.8111 to1; nine are under0.95 after earlier coverage/coastline adjustments. This is a source-correspondence diagnostic, not a latitude-correct land-area ownership calculation.

`gb:AUS:ADM2:25037944B57060386363407` combines Jervis Bay and distant Norfolk coastal fragments (bounds150.5945,-35.1913 to167.998,-28.9954). Its Jervis Bay parent does not justify renaming the entire land to Jervis Bay. `gb:NZL:ADM2:76426892B9784131965054` spans disconnected North Island offshore fragments (bounds172.127,-37.6413 to176.4381,-34.144); a Bay of Plenty label cannot make that one coherent locality. Both remain open for named, sourced geographic split/replacement migrations.

American Samoa and CNMI contain duplicate reference-territory and USA-source local identities. The topology reconciler removed overlapping display land but preserved disjoint residual coastal polygons, which then look like separate locations. All affected IDs are flagged in the JSON; preserve original source geometries and histories before a complete island/district union or replacement. Do not just erase tiny coastal cells.

The missing-grid source report has 19 Oceania IDs. Marshall atoll source/current land differences, Kayangel, PNG urban territories, Tuvalu atolls, Darwin Waterfront and Swains require independent source-land review. Kiribati Phoenix source label/footprint mismatch is a separate omission, not merely a small-cell problem. Root handles fixed-grid changes; this review does not reassign cells.

## Evidence and limitations

- [ABS LGA guidance](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/non-abs-structures/local-government-areas): inspected substantive definitions, unincorporated territory naming and reference/cartographic cautions.
- [DCCEEW IBRA actual item](https://www.arcgis.com/sharing/rest/content/items/0e78c21ba12543019b92e10272f980fe?f=json): inspected actual service metadata, named IBRA7.1 subregions, 2025 distribution and CC BY4; compared all435 codes with cached source polygons and original LGA shapeIDs.
- [Pinned NZ local and regional data](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/NZL/ADM2/geoBoundaries-NZL-ADM2.geojson): inspected all88 local records and the single Auckland regional feature, not only a map UI.
- [UN M49](https://unstats.un.org/unsd/methodology/m49/overview/): inspected four Oceania statistical subregions; country-statistical conventions do not certify physical atlas boundaries.
- [Vanuatu statistics](https://vnso.gov.vu/index.php/en/): inspected explicit distinction between six provinces and Port Vila/Luganville urban centres.
- [Samoa district profiles](https://www.sbs.gov.ws/district-profiles/): inspected actual district-profile service; finer local geometry/license remains to acquire.
- [TAAF presentation](https://taaf.fr/collectivite/presentation/): inspected five district distinction, southern island groups versus Antarctic Adélie and tropical Éparses.
- [Johnston Atoll FWS](https://www.fws.gov/refuge/johnston-atoll): inspected isolated-atoll position and geographic scope.

Failed or title-only requests are recorded in JSON and never counted as substantive verification. Modern geometry vintage remains explicit. Samoa, Fiji, Vanuatu, FSM, New Caledonia and Indonesian Papua demonstrate unresolved scale differences throughout the continent, beyond the user’s China/Italy examples.

**Completion remains open.** Every current unit has a disposition, but source omissions, coastal residuals, functional-city membership and intermediate geographic clustering require sourced footprint corrections with explicit archived identity crosswalks. No count quota, inferred ancient attribute, owner-driven boundary or automatic smallest-island merge was used.

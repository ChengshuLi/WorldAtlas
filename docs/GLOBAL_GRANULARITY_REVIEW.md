# Worldwide granularity source review

The source-evidence screening accounts for all **49,614 active locations, 252 reference territories and 201 source-policy profiles**. Every represented territory receives a source-role, vintage, license, scale, name, membership and grid assessment. This is an exhaustive screening inventory; it does **not** certify semantic completion. All 252 territory reviews remain open until their individual flagged units and untested city/coverage questions have sourced corrections or justified exceptions.

The complete machine-readable evidence is [granularity-review-evidence.json](../data/granularity-review-evidence.json). It preserves actual flagged location IDs, source roles, upstream provenance, declared vintages, license details, source hashes, candidate metadata and inspected GeoJSON inventories. No footprint, identity, history or atlas ownership was changed by this review.

Run `python scripts/review-granularity-global.py` after the world review and pixel audit to refresh all screening flags, source-policy crosswalks and both complete matrices. The command works from any current directory when invoked by its absolute path. It retains the inspected candidate metadata, geometry hashes and country research notes; it performs no new source research and does not close semantic reviews. Hosting serves the report as a compressed download.

## What was inspected

- Every current location’s actual geometry type/component count and source metadata, across all geographic parts.
- Every location’s existing area and source-group match measurements and every canonical-grid representation result.
- All 201 source-policy selections and their recorded administrative source metadata, reconciled against all 252 distinct reference territories.
- 25 public candidate metadata endpoints, including unsuccessful retrievals; 10 candidate GeoJSON URLs, of which nine returned inspectable geometry.
- Existing city-membership/physical-subdivision records and source-coastline omission reviews.

Only source filenames, metadata and geometry inventories were inspected for the new candidate layers. Their full spatial coverage, geographic role and complete-city semantics have not yet been validated. No candidate was imported merely because it has a larger feature count.

## Crosswalk and conventions

The 201 source-policy profiles match **203 reference territories**. Morocco’s profile crosses to both Morocco and Western Sahara; Somalia’s crosses to both Somalia and Somaliland. These are source crosswalks, not political ownership assignments. The remaining **49 reference territories** require explicit territorial source decisions. Thus 252−201 is not the count of unmatched groups.

**28 profiles** still have an upstream canonical role of `Unknown` and a generic policy label of `Named local administrative territory`. Their existing claim to a reviewed district-equivalent role is insufficient evidence. Those profiles are: ARE, BFA, BHR, CAN, CMR, COG, COM, CPV, ETH, KIR, LIE, LKA, LUX, MCO, MDV, MHL, NIC, PLW, SGP, SMR, STP, TKM, TON, TTO, TUV, URY, VUT, WSM.

Source vintage is distinct from atlas selection year. A boundary described as 2014/2017/2021 is not evidence that its administrative role or name is unchanged in 2026, and is not an ancient geographic identity. Unknown evidence stays unknown.

## Common review rubric

| Screen | Observed locations | Interpretation |
|---|---:|---|
| large-territory-screen | 262 | Area >50,000 km² is a review trigger only; sparsely inhabited physical territories may warrant sourced exceptions. |
| anonymous-or-remainder-label | 3 | Numbered/remainder/unknown source labels need evidence; legitimate official numbered names are not automatically errors. |
| urban-fragment-role | 4 | Explicit police-department source names identify possible city fragments; verify source role and complete city footprint before any merge. |
| mixed-urban-role-needs-classification | 1,839 | Source role mixes municipalities and city wards/districts without per-feature classification; source country roles and individual identities must be verified. Arrondissements in France/Belgium/Haiti are not automatically urban fragments. |
| multipart-footprint | 4,081 | Multiple polygon components need source intent/island/enclave verification, not automatic splitting. |
| repeated-location-province-name | 1,782 | Identical adjacent-tier names require distinct roles or a documented compact exception. |
| local-cluster-scale-outlier | 51 | At least four province members, area >1,000 km² and >25 times median member area; compare rural purpose rather than impose equal sizes. |
| weak-source-parent-match | 2,548 | Existing source-group overlap <80%; match_field identifies framework, prefecture or geographic source basis. This is not always the immediate province and must not trigger automatic reparenting. |
| grid-unrepresented | 53 | No canonical cell-center representation; no arbitrary reassignment. |
| grid-high-distortion | 123 | Pixel audit flags area distortion; this alone cannot prove unsuitable source granularity. |

Flags overlap. Their counts must not be summed as distinct erroneous locations. Multiple components often represent valid islands or enclaves; repeated adjacent-tier names can describe a documented compact exception. France, Belgium and Haiti use arrondissements with different administrative purposes; the word is not proof of an urban neighbourhood. Mixed municipality/city-ward layer roles require per-feature classification where no sourced aggregate role is recorded. The report prioritizes current `location_basis` over inherited source-layer roles; original canonical roles remain separate provenance, so physical subdivisions are not mislabeled as LGAs.

The source-match screen is not uniformly an immediate-province match. Each flagged record includes `match_field`, identifying `framework_overlap`, `prefecture_overlap` or `geographic_overlap`. A weak botanical-area match must not automatically change a location’s province. The relative-size screen compares siblings in a province; a complete spatial-neighbour audit remains open. Coastline reference differences also cannot certify the presence of every small island.

## Concrete worldwide correction candidates

| Territory | Actual inspected source | Proposed action and unresolved checks |
|---|---|---|
| ROU | [3235 municipalities, 2016](https://www.geoboundaries.org/api/current/gbOpen/ROU/ADM2/) — Creative Commons Attribution 4.0 International (CC BY 4.0) | Prioritize county-to-local-territory correction using official ANCPI municipal/commune identities; reconcile repeated names, urban extent and full land coverage. |
| SLE | [165 Chiefdoms, 2016](https://www.geoboundaries.org/api/current/gbOpen/SLE/ADM3/) — Creative Commons Attribution 4.0 (CC BY 4.0) | Evaluate chiefdoms plus complete urban/Western Area territories; check later district and chiefdom reforms. |
| SLB | [50 Constituency, 2018](https://www.geoboundaries.org/api/current/gbOpen/SLB/ADM2/) — Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) | Constituencies split Honiara three ways; avoid introducing city fragmentation merely for finer counts. |
| BLZ | [31 Constituencies, 2008](https://www.geoboundaries.org/api/current/gbOpen/BLZ/ADM2/) — Public Domain | Constituencies are electoral geography. Research complete city and rural territory roles before selecting them. |
| BOL | [339 Unknown, 2015](https://www.geoboundaries.org/api/current/gbOpen/BOL/ADM3/) — Public Domain | Canonical role is Unknown despite 339 named polygons; verify GeoBolivia municipal identity before adoption. |
| COD | [188 Territoire, 2010.0](https://www.geoboundaries.org/api/current/gbOpen/COD/ADM3/) — Open Data Commons Open Database License 1.0 | Metadata says Territoire, 188 units; linked geometry returned 404. It is not proof of a finer source than the current 189 territories. |
| MLI | [701 Commune, 2017](https://www.geoboundaries.org/api/current/gbOpen/MLI/ADM3/) — Creative Commons Attribution 4.0 International (CC BY 4.0) | Evaluate complete communes, preserving coherent Bamako urban territory and named northern rural units. |
| FIN | [312 Unknown, 2017](https://www.geoboundaries.org/api/current/gbOpen/FIN/ADM3/) — Open Data Commons Open Database License 1.0 | Metadata claims 313 units; inspected file has 312. Resolve mismatch, canonical role and ODbL requirements. |
| GIN | [340 sub-prefecture, 2021](https://www.geoboundaries.org/api/current/gbOpen/GIN/ADM3/) — Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) | Evaluate source subprefectures and city communes against all existing prefectural land. |
| GUY | [27 Neighbourhood Councils, 2019](https://www.geoboundaries.org/api/current/gbOpen/GUY/ADM2/) — Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) | Neighbourhood councils contain coded source labels; verify complete interior coverage and meaningful locality identities. |

Additional checked metadata: Solomon Islands ADM3 contains 183 wards but uses `Other - Direct Permission`; the actual reuse permission requires examination. Peru humanitarian ADM3 declares 1,873 units with canonical role `Unknown`, under CC BY 3.0 IGO; the role and polygon coverage remain to be inspected. New Caledonia gbOpen ADM1/ADM2 endpoints returned 404, and an official data.gouv.fr search returned no matching dataset. These retrieval results describe the inspected catalogues, not the existence of all possible public sources.

Uruguay’s 124 municipality polygons, Pakistan’s 554 tehsils and Bhutan’s 205 gewogs were previously evaluated but not adopted because source coverage was incomplete. India accepted 3,998 subdistrict territories replacing 367 districts, while retaining 355 districts with failed coverage/clipping checks. Mixed retained/finer roles remain a semantic review obligation.

A new unresolved label found outside the previous regression examples is Australia's **Unincorp. Other Territories**: eight source components, about 65.4 km², and a weak geographic-source match. **Unnamed territory — Ladākh reference** and **Western equatorial Pacific source remainder** in Kiribati are also open. These provisional/source labels are not certified locality names.

## Full reference-territory matrix

Every row below has an open semantic status. Roles and metrics describe actual current source records. Detailed source URLs, licenses, individual flagged IDs and decisions are in the JSON evidence.

| Reference territory | Source policy | Locations / provinces | Actual source roles | Median km² | Flags |
|---|---|---:|---|---:|---|
| Afghanistan | AFG | 398 / 34 | wuleswali (394); Named source district and independently matched OSM border-vintage fragment (4) | 928.5 | multipart-footprint: 7; repeated-location-province-name: 6; weak-source-parent-match: 3 |
| Akrotiri Sovereign Base Area | Unmatched | 1 / 1 | ADM1 fallback (1) | 96.9 | repeated-location-province-name: 1 |
| Aland | Unmatched | 1 / 1 | Compact source country/territory (1) | 470.0 | multipart-footprint: 1; repeated-location-province-name: 1 |
| Albania | ALB | 36 / 12 | District (35); Disconnected components of the same named source district (1) | 829.2 | multipart-footprint: 7; repeated-location-province-name: 11; weak-source-parent-match: 1 |
| Algeria | DZA | 1,566 / 50 | Commune (1527); Published geographic subdivision within a source rural district (39) | 119.8 | grid-high-distortion: 6; grid-unrepresented: 1; large-territory-screen: 10; local-cluster-scale-outlier: 2; multipart-footprint: 20; repeated-location-province-name: 32; weak-source-parent-match: 34 |
| American Samoa | Unmatched | 5 / 5 | ADM1 fallback (5) | 46.9 | grid-high-distortion: 1; multipart-footprint: 1; repeated-location-province-name: 5; weak-source-parent-match: 4 |
| Andorra | AND | 1 / 1 | Compact source country/territory (1) | 469.2 | repeated-location-province-name: 1 |
| Angola | AGO | 161 / 19 | Published municipality territory, 2018 humanitarian source (161) | 4,837.7 | multipart-footprint: 17; repeated-location-province-name: 7 |
| Anguilla | Unmatched | 1 / 1 | Compact source country/territory (1) | 80.5 | multipart-footprint: 1; repeated-location-province-name: 1 |
| Antigua and Barbuda | ATG | 1 / 1 | Compact source country/territory (1) | 424.4 | multipart-footprint: 1; repeated-location-province-name: 1 |
| Argentina | ARG | 509 / 26 | departments (508); Source city territory: Federal District (1) | 3,306.2 | large-territory-screen: 1; multipart-footprint: 16; repeated-location-province-name: 2; weak-source-parent-match: 6 |
| Armenia | ARM | 39 / 11 | Municipal community (39) | 646.6 | multipart-footprint: 3; repeated-location-province-name: 5 |
| Aruba | Unmatched | 1 / 1 | ADM1 fallback (1) | 170.8 | repeated-location-province-name: 1 |
| Australia | AUS | 945 / 15 | Local Government Areas (507); Published geographic subdivision within a source rural district (435); Named source island / overseas territory (3) | 3,356.5 | anonymous-or-remainder-label: 1; grid-high-distortion: 7; grid-unrepresented: 1; large-territory-screen: 14; local-cluster-scale-outlier: 2; multipart-footprint: 434; repeated-location-province-name: 3; weak-source-parent-match: 20 |
| Austria | AUT | 94 / 9 | District (94) | 864.8 | multipart-footprint: 10; weak-source-parent-match: 1 |
| Azerbaijan | AZE | 79 / 2 | District (79) | 1,044.2 | multipart-footprint: 9; weak-source-parent-match: 1 |
| Bahamas | BHS | 32 / 32 | Districts (32) | 220.1 | multipart-footprint: 16; repeated-location-province-name: 32; weak-source-parent-match: 24 |
| Bahrain | BHR | 1 / 1 | Compact source country/territory (1) | 728.6 | multipart-footprint: 1; repeated-location-province-name: 1 |
| Bajo Nuevo Bank (Petrel Is.) | Unmatched | 1 / 1 | ADM0 fallback (1) | 0.0 | grid-unrepresented: 1; repeated-location-province-name: 1; weak-source-parent-match: 1 |
| Bangladesh | BGD | 64 / 8 | district (64) | 2,048.0 | multipart-footprint: 17; repeated-location-province-name: 7; weak-source-parent-match: 6 |
| Barbados | BRB | 1 / 1 | Compact source country/territory (1) | 430.4 | repeated-location-province-name: 1 |
| Belarus | BLR | 118 / 7 | Raion (118) | 1,639.9 | multipart-footprint: 6; repeated-location-province-name: 7 |
| Belgium | BEL | 43 / 11 | Arrondissements (43) | 609.7 | multipart-footprint: 3; weak-source-parent-match: 2 |
| Belize | BLZ | 6 / 6 | Districts (6) | 4,298.7 | multipart-footprint: 3; repeated-location-province-name: 6 |
| Benin | BEN | 77 / 12 | Commune (77) | 539.0 | multipart-footprint: 3; weak-source-parent-match: 2 |
| Bermuda | Unmatched | 1 / 1 | Compact source country/territory (1) | 53.5 | repeated-location-province-name: 1 |
| Bhutan | BTN | 20 / 20 | Dzongdeys (20) | 1,770.7 | multipart-footprint: 1; repeated-location-province-name: 20; weak-source-parent-match: 2 |
| Bir Tawil | Unmatched | 1 / 1 | ADM0 fallback (1) | 2,025.3 | repeated-location-province-name: 1; weak-source-parent-match: 1 |
| Bolivia (Plurinational State of) | BOL | 117 / 9 | Province (108); Published geographic subdivision within a source rural district (9) | 4,174.1 | large-territory-screen: 2; multipart-footprint: 15 |
| Bosnia and Herzegovina | BIH | 142 / 12 | Municipality (142) | 305.8 | multipart-footprint: 9; repeated-location-province-name: 2 |
| Botswana | BWA | 35 / 10 | Subdistrict (22); Published geographic subdivision within a source rural district (13) | 9,832.4 | large-territory-screen: 1; multipart-footprint: 13 |
| Brazil | BRA | 765 / 137 | municipality (140); IBGE immediate geographic region; separately mapped major cities excluded (473); Published geographic subdivision within a source rural district (152) | 4,846.2 | large-territory-screen: 27; local-cluster-scale-outlier: 1; multipart-footprint: 199; repeated-location-province-name: 110; weak-source-parent-match: 13 |
| British Indian Ocean Territory | Unmatched | 1 / 1 | ADM1 fallback (1) | 27.2 | repeated-location-province-name: 1; weak-source-parent-match: 1 |
| British Virgin Islands | Unmatched | 1 / 1 | ADM1 fallback (1) | 126.9 | multipart-footprint: 1; repeated-location-province-name: 1; weak-source-parent-match: 1 |
| Brunei Darussalam | BRN | 4 / 4 | Districts (4) | 1,292.8 | multipart-footprint: 1; repeated-location-province-name: 4 |
| Bulgaria | BGR | 265 / 29 | Municipality (265) | 359.2 | multipart-footprint: 1; repeated-location-province-name: 26; weak-source-parent-match: 8 |
| Burkina Faso | BFA | 351 / 45 | Named local administrative territory (351) | 579.8 | multipart-footprint: 6; weak-source-parent-match: 6 |
| Burundi | BDI | 119 / 18 | Commune (119) | 192.5 | multipart-footprint: 4; repeated-location-province-name: 13; weak-source-parent-match: 4 |
| Cabo Verde | CPV | 22 / 22 | Named local administrative territory (22) | 150.8 | multipart-footprint: 1; repeated-location-province-name: 22; weak-source-parent-match: 14 |
| Cambodia | KHM | 197 / 25 | District (197) | 549.7 | grid-high-distortion: 3; multipart-footprint: 13; repeated-location-province-name: 11; weak-source-parent-match: 5 |
| Cameroon | CMR | 360 / 60 | Named local administrative territory (360) | 547.8 | multipart-footprint: 14; weak-source-parent-match: 16 |
| Canada | CAN | 478 / 133 | Named local administrative territory (33); Statistics Canada named county / regional district; separately mapped major cities excluded (176); Named ecoregion portion; separately mapped municipalities excluded (265); Disconnected components of the same named source district (4) | 5,195.1 | grid-high-distortion: 3; large-territory-screen: 63; multipart-footprint: 229; repeated-location-province-name: 11 |
| Caribbean Netherlands | Unmatched | 1 / 1 | Named source island / overseas territory (1) | 270.2 | repeated-location-province-name: 1 |
| Cayman Islands | Unmatched | 1 / 1 | ADM1 fallback (1) | 310.4 | multipart-footprint: 1; repeated-location-province-name: 1; weak-source-parent-match: 1 |
| Central African Republic | CAF | 175 / 73 | Commune (175) | 1,860.0 | grid-high-distortion: 1; multipart-footprint: 1; repeated-location-province-name: 34; weak-source-parent-match: 3 |
| Chad | TCD | 81 / 23 | Departments (64); Published geographic subdivision within a source rural district (17) | 9,545.3 | large-territory-screen: 6; multipart-footprint: 16; repeated-location-province-name: 2 |
| Chile | CHL | 345 / 57 | Communes (345) | 630.0 | local-cluster-scale-outlier: 1; multipart-footprint: 26; weak-source-parent-match: 18 |
| China | CHN | 2,402 / 357 | County Level (2343); Published geographic subdivision within a source rural district (58); Source city territory: Municipality (1) | 1,986.1 | large-territory-screen: 13; local-cluster-scale-outlier: 4; multipart-footprint: 61; weak-source-parent-match: 29 |
| Colombia | COL | 1,124 / 34 | Municipality (1121); Published geographic subdivision within a source rural district (3) | 289.5 | local-cluster-scale-outlier: 1; multipart-footprint: 11; repeated-location-province-name: 4; weak-source-parent-match: 11 |
| Comoros | COM | 1 / 1 | Compact source country/territory (1) | 1,654.2 | multipart-footprint: 1; repeated-location-province-name: 1 |
| Congo | COG | 46 / 11 | Named local administrative territory (46) | 5,668.9 | multipart-footprint: 2 |
| Cook Islands | Unmatched | 11 / 11 | ADM1 fallback (11) | 11.2 | grid-high-distortion: 1; repeated-location-province-name: 11; weak-source-parent-match: 9 |
| Costa Rica | CRI | 83 / 7 | Canton (83) | 282.2 | local-cluster-scale-outlier: 1; multipart-footprint: 5; weak-source-parent-match: 1 |
| Croatia | HRV | 557 / 24 | Municipality / town (556); Source city territory: City (1) | 64.3 | grid-high-distortion: 1; grid-unrepresented: 2; multipart-footprint: 21; repeated-location-province-name: 1; weak-source-parent-match: 93 |
| Cuba | CUB | 168 / 16 | Municipality (168) | 612.1 | grid-high-distortion: 2; multipart-footprint: 10; repeated-location-province-name: 10; weak-source-parent-match: 17 |
| Curaçao | Unmatched | 1 / 1 | ADM1 fallback (1) | 462.9 | repeated-location-province-name: 1; weak-source-parent-match: 1 |
| Cyprus | CYP | 6 / 6 | District (6) | 1,245.6 | multipart-footprint: 4; repeated-location-province-name: 6; weak-source-parent-match: 2 |
| Cyprus No Mans Area | Unmatched | 1 / 1 | ADM0 fallback (1) | 331.6 | multipart-footprint: 1; repeated-location-province-name: 1 |
| Czechia | CZE | 77 / 14 | District (77) | 1,007.2 | multipart-footprint: 1; weak-source-parent-match: 2 |
| Côte d'Ivoire | CIV | 510 / 35 | Departments (510) | 467.2 | multipart-footprint: 4; weak-source-parent-match: 20 |
| Dem. People's Republic of Korea | PRK | 174 / 11 | county, city, special city (173); Source city territory: Special City (1) | 580.9 | multipart-footprint: 11; repeated-location-province-name: 1; weak-source-parent-match: 10 |
| Democratic Republic of the Congo | COD | 189 / 26 | territory, city (189) | 12,198.0 | grid-high-distortion: 2; multipart-footprint: 15; repeated-location-province-name: 1; weak-source-parent-match: 3 |
| Denmark | DNK | 98 / 6 | Municipality (98) | 370.5 | multipart-footprint: 20; weak-source-parent-match: 19 |
| Dhekelia Sovereign Base Area | Unmatched | 1 / 1 | ADM1 fallback (1) | 130.3 | repeated-location-province-name: 1 |
| Djibouti | DJI | 11 / 5 | Districts (11) | 1,779.9 | multipart-footprint: 1; repeated-location-province-name: 2; weak-source-parent-match: 1 |
| Dominica | DMA | 1 / 1 | Compact source country/territory (1) | 755.7 | repeated-location-province-name: 1 |
| Dominican Republic | DOM | 155 / 32 | Municipalities (155) | 205.0 | multipart-footprint: 3; repeated-location-province-name: 8; weak-source-parent-match: 10 |
| Ecuador | ECU | 224 / 24 | Cantons (224) | 590.0 | multipart-footprint: 14; repeated-location-province-name: 7; weak-source-parent-match: 10 |
| Egypt | EGY | 301 / 31 | marakiz and aqsam (282); Published geographic subdivision within a source rural district (6); Source city territory: Governorate (2); Disconnected components of the same named source district (11) | 171.8 | grid-high-distortion: 13; grid-unrepresented: 2; large-territory-screen: 2; local-cluster-scale-outlier: 9; multipart-footprint: 57; repeated-location-province-name: 2; urban-fragment-role: 4; weak-source-parent-match: 18 |
| El Salvador | SLV | 271 / 19 | Municipalities (270); Disconnected components of the same named source district (1) | 50.4 | grid-high-distortion: 6; grid-unrepresented: 1; multipart-footprint: 11; repeated-location-province-name: 3; weak-source-parent-match: 27 |
| Equatorial Guinea | GNQ | 28 / 9 | District (28) | 954.9 | grid-high-distortion: 1; grid-unrepresented: 1; multipart-footprint: 2; repeated-location-province-name: 1; weak-source-parent-match: 4 |
| Eritrea | ERI | 58 / 6 | districts (58) | 1,010.9 | multipart-footprint: 4; weak-source-parent-match: 3 |
| Estonia | EST | 214 / 18 | Municipality (214) | 180.1 | grid-high-distortion: 2; multipart-footprint: 12; weak-source-parent-match: 15 |
| Eswatini | SWZ | 53 / 5 | Inkhundla (53) | 282.4 | weak-source-parent-match: 9 |
| Ethiopia | ETH | 680 / 74 | Named local administrative territory (678); Disconnected components of the same named source district (1); Published city administrative territory; constituent districts combined (1) | 980.7 | multipart-footprint: 18; repeated-location-province-name: 4 |
| Falkland Islands | Unmatched | 1 / 1 | ADM1 fallback (1) | 11,521.2 | multipart-footprint: 1; repeated-location-province-name: 1 |
| Faroe Islands | Unmatched | 1 / 1 | ADM1 fallback (1) | 1,322.1 | multipart-footprint: 1; repeated-location-province-name: 1; weak-source-parent-match: 1 |
| Fiji | FJI | 15 / 5 | Provinces (15) | 1,131.4 | multipart-footprint: 11; repeated-location-province-name: 1; weak-source-parent-match: 6 |
| Finland | FIN | 70 / 19 | Subregion (70) | 3,069.2 | multipart-footprint: 22; weak-source-parent-match: 6 |
| France | FRA | 328 / 102 | Arrondissement (320); Published geographic subdivision within a source rural district (3); Named source island / overseas territory (5) | 1,653.0 | grid-high-distortion: 1; large-territory-screen: 1; multipart-footprint: 21; repeated-location-province-name: 7; weak-source-parent-match: 4 |
| French Polynesia | Unmatched | 5 / 5 | ADM1 fallback (5) | 490.4 | multipart-footprint: 5; repeated-location-province-name: 5; weak-source-parent-match: 5 |
| French Southern and Antarctic Lands | Unmatched | 4 / 4 | Named source island / overseas territory (4) | 204.8 | multipart-footprint: 4; repeated-location-province-name: 4 |
| Gabon | GAB | 49 / 10 | Department (49) | 3,753.6 | multipart-footprint: 3; repeated-location-province-name: 1; weak-source-parent-match: 2 |
| Gambia | GMB | 40 / 7 | District (39); Source city territory: Independent City (1) | 271.8 | multipart-footprint: 3; repeated-location-province-name: 3; weak-source-parent-match: 15 |
| Georgia | GEO | 68 / 12 | Municipality (68) | 863.9 | multipart-footprint: 7; repeated-location-province-name: 1; weak-source-parent-match: 2 |
| Germany | DEU | 409 / 41 | Independent City or District (390); Source city territory: State (1); Disconnected components of the same named source district (18) | 781.6 | multipart-footprint: 30; repeated-location-province-name: 3; weak-source-parent-match: 12 |
| Ghana | GHA | 260 / 17 | Districts (260) | 577.1 | grid-high-distortion: 2; multipart-footprint: 9; weak-source-parent-match: 16 |
| Gibraltar | Unmatched | 1 / 1 | ADM1 fallback (1) | 3.1 | grid-high-distortion: 1; repeated-location-province-name: 1 |
| Greece | GRC | 325 / 21 | Municipality (324); Disconnected components of the same named source district (1) | 357.2 | grid-high-distortion: 6; multipart-footprint: 34; repeated-location-province-name: 3; weak-source-parent-match: 79 |
| Greenland | GRL | 11 / 6 | Municipalities (2); Published geographic subdivision within a source rural district (9) | 41,896.5 | large-territory-screen: 5; multipart-footprint: 10; repeated-location-province-name: 2 |
| Grenada | GRD | 1 / 1 | Compact source country/territory (1) | 344.0 | multipart-footprint: 1; repeated-location-province-name: 1 |
| Guam | GUM | 1 / 1 | Compact source country/territory (1) | 561.5 | repeated-location-province-name: 1 |
| Guatemala | GTM | 342 / 24 | Municipality (342) | 136.1 | grid-high-distortion: 4; multipart-footprint: 5; repeated-location-province-name: 13; weak-source-parent-match: 4 |
| Guernsey | Unmatched | 1 / 1 | ADM1 fallback (1) | 65.3 | multipart-footprint: 1; repeated-location-province-name: 1; weak-source-parent-match: 1 |
| Guinea | GIN | 34 / 8 | prefecture (34) | 6,012.3 | multipart-footprint: 5; repeated-location-province-name: 8; weak-source-parent-match: 1 |
| Guinea-Bissau | GNB | 39 / 9 | Sector (39) | 845.0 | multipart-footprint: 6; weak-source-parent-match: 14 |
| Guyana | GUY | 27 / 10 | Neighbourhood Councils (27) | 2,529.9 | multipart-footprint: 2; weak-source-parent-match: 4 |
| Haiti | HTI | 42 / 10 | Arrondissement (42) | 617.7 | multipart-footprint: 4; weak-source-parent-match: 4 |
| Heard Island and McDonald Islands | Unmatched | 1 / 1 | Named source island / overseas territory (1) | 393.3 | repeated-location-province-name: 1 |
| Honduras | HND | 298 / 18 | Municipality (298) | 186.0 | multipart-footprint: 11; repeated-location-province-name: 5; weak-source-parent-match: 14 |
| Hong Kong S.A.R. | Unmatched | 1 / 1 | Compact source country/territory (1) | 1,033.3 | multipart-footprint: 1 |
| Hungary | HUN | 176 / 20 | District (175); Source city territory: Capital City (1) | 508.3 | multipart-footprint: 3; repeated-location-province-name: 4; weak-source-parent-match: 8 |
| Iceland | ISL | 74 / 9 | Municipality (74) | 594.6 | multipart-footprint: 8; weak-source-parent-match: 12 |
| India | IND | 4,355 / 399 | District (355); Mumbai City and Mumbai Suburban districts (1); Source city territory: Union Territory (1); Published named Sub-district / taluka / tehsil local territory; coherent source city unions preserved (3998) | 428.2 | anonymous-or-remainder-label: 1; grid-high-distortion: 5; grid-unrepresented: 1; multipart-footprint: 287; repeated-location-province-name: 240; weak-source-parent-match: 81 |
| Indonesia | IDN | 515 / 38 | regency, city (514); Source city territory: Special district (1) | 1,929.4 | multipart-footprint: 142; repeated-location-province-name: 3; weak-source-parent-match: 61 |
| Iran (Islamic Republic of) | IRN | 433 / 32 | Shahrestan (431); Published geographic subdivision within a source rural district (2) | 2,210.9 | large-territory-screen: 1; multipart-footprint: 17; repeated-location-province-name: 11; weak-source-parent-match: 4 |
| Iraq | IRQ | 102 / 21 | Districts (100); Published geographic subdivision within a source rural district (2) | 2,162.5 | multipart-footprint: 5; repeated-location-province-name: 4; weak-source-parent-match: 1 |
| Ireland | IRL | 34 / 4 | ADM1 fallback (34) | 1,848.0 | multipart-footprint: 5; weak-source-parent-match: 1 |
| Isle of Man | Unmatched | 1 / 1 | ADM1 fallback (1) | 572.0 | repeated-location-province-name: 1; weak-source-parent-match: 1 |
| Israel | ISR | 15 / 7 | Subdistrict (15) | 635.0 | multipart-footprint: 3; repeated-location-province-name: 2 |
| Italy | ITA | 610 / 106 | Published named commuting territory; multiple contiguous municipalities. Atlas parent grouping follows whole systems, not exact administrative province borders. (610) | 389.3 | multipart-footprint: 317; repeated-location-province-name: 98; weak-source-parent-match: 76 |
| Jamaica | JAM | 14 / 14 | parish (14) | 838.3 | repeated-location-province-name: 14; weak-source-parent-match: 2 |
| Japan | JPN | 1,688 / 62 | Municipality / city ward (1685); Source city territory: Metropolis (1); MLIT designated-city territory, including constituent wards (1); MLIT municipal territory with adjacent source coastline sliver (1) | 128.8 | grid-high-distortion: 3; local-cluster-scale-outlier: 1; mixed-urban-role-needs-classification: 1685; multipart-footprint: 104; repeated-location-province-name: 18; weak-source-parent-match: 170 |
| Jersey | Unmatched | 1 / 1 | ADM1 fallback (1) | 119.5 | repeated-location-province-name: 1; weak-source-parent-match: 1 |
| Jordan | JOR | 52 / 12 | Nahias (52) | 457.9 | local-cluster-scale-outlier: 3; repeated-location-province-name: 5 |
| Kazakhstan | KAZ | 186 / 16 | District (168); Published geographic subdivision within a source rural district (16); Named inland-water portion within a source district (2) | 9,616.7 | large-territory-screen: 4; multipart-footprint: 36; repeated-location-province-name: 1; weak-source-parent-match: 2 |
| Kenya | KEN | 274 / 47 | Sub-Counties (273); Source city territory: National Capital Area (1) | 542.5 | multipart-footprint: 8; repeated-location-province-name: 6; weak-source-parent-match: 1 |
| Kiribati | KIR | 3 / 3 | Named local administrative territory (3) | 120.2 | anonymous-or-remainder-label: 1; multipart-footprint: 3; repeated-location-province-name: 3; weak-source-parent-match: 3 |
| Kosovo | XKX | 7 / 7 | Municipalities (7) | 1,369.8 | multipart-footprint: 3; repeated-location-province-name: 7 |
| Kuwait | KWT | 6 / 6 | Governorate (6) | 198.3 | multipart-footprint: 2; repeated-location-province-name: 6; weak-source-parent-match: 2 |
| Kyrgyzstan | KGZ | 42 / 8 | Raions (41); Named source city territory (1) | 3,967.9 | multipart-footprint: 8; repeated-location-province-name: 1 |
| Lao People's Democratic Republic | LAO | 140 / 18 | Districts (139); Source city territory: Municipality\|Prefecture (1) | 1,530.4 | multipart-footprint: 6; repeated-location-province-name: 1; weak-source-parent-match: 2 |
| Latvia | LVA | 43 / 43 | Administratīvās teritorijas (43) | 1,682.8 | multipart-footprint: 4; repeated-location-province-name: 43; weak-source-parent-match: 1 |
| Lebanon | LBN | 26 / 9 | Districts (Aqdya) (26) | 277.2 | multipart-footprint: 3; weak-source-parent-match: 1 |
| Lesotho | LSO | 10 / 10 | District (10) | 2,970.8 | repeated-location-province-name: 10 |
| Liberia | LBR | 136 / 15 | District (136) | 525.2 | multipart-footprint: 9; weak-source-parent-match: 13 |
| Libya | LBY | 39 / 22 | Published geographic subdivision within a source rural district (26); District (13) | 17,269.2 | large-territory-screen: 9; multipart-footprint: 8; repeated-location-province-name: 13 |
| Liechtenstein | LIE | 1 / 1 | Compact source country/territory (1) | 158.4 | repeated-location-province-name: 1 |
| Lithuania | LTU | 60 / 10 | Municipality (60) | 1,210.0 | multipart-footprint: 2; weak-source-parent-match: 3 |
| Luxembourg | LUX | 1 / 1 | Compact source country/territory (1) | 2,576.1 | repeated-location-province-name: 1 |
| Macao S.A.R | Unmatched | 1 / 1 | Compact source country/territory (1) | 41.5 | weak-source-parent-match: 1 |
| Madagascar | MDG | 119 / 22 | District (119) | 4,636.8 | multipart-footprint: 8; weak-source-parent-match: 4 |
| Malawi | MWI | 28 / 3 | district (28) | 3,137.6 | multipart-footprint: 3; weak-source-parent-match: 1 |
| Malaysia | MYS | 159 / 15 | Districts (159) | 1,296.1 | multipart-footprint: 18; repeated-location-province-name: 3; weak-source-parent-match: 10 |
| Maldives | MDV | 23 / 23 | Named local administrative territory (19); Named source island / overseas territory (3); Source city territory: Capital (1) | 2.5 | grid-high-distortion: 2; grid-unrepresented: 3; multipart-footprint: 4; repeated-location-province-name: 23; weak-source-parent-match: 19 |
| Mali | MLI | 56 / 9 | Cercle (47); Published geographic subdivision within a source rural district (9) | 12,009.2 | large-territory-screen: 3; multipart-footprint: 10; repeated-location-province-name: 7 |
| Malta | MLT | 1 / 1 | Compact source country/territory (1) | 301.7 | multipart-footprint: 1; repeated-location-province-name: 1 |
| Marshall Islands | MHL | 24 / 24 | Named local administrative territory (24) | 1.6 | grid-high-distortion: 5; grid-unrepresented: 9; multipart-footprint: 1; repeated-location-province-name: 24; weak-source-parent-match: 22 |
| Mauritania | MRT | 69 / 13 | Mauritania (51); Published geographic subdivision within a source rural district (18) | 6,602.4 | large-territory-screen: 6; multipart-footprint: 11; weak-source-parent-match: 2 |
| Mauritius | MUS | 13 / 13 | Districts and Outer Islands of Mauritius (12); Named source island / overseas territory (1) | 176.2 | grid-unrepresented: 1; multipart-footprint: 1; repeated-location-province-name: 13; weak-source-parent-match: 10 |
| Mexico | MEX | 2,442 / 44 | municipios (2441); Source city territory: Federal District (1) | 236.6 | grid-high-distortion: 11; large-territory-screen: 1; local-cluster-scale-outlier: 3; multipart-footprint: 59; repeated-location-province-name: 11; weak-source-parent-match: 101 |
| Micronesia (Fed. States of) | FSM | 4 / 4 | State (4) | 106.8 | multipart-footprint: 2; repeated-location-province-name: 4; weak-source-parent-match: 4 |
| Monaco | MCO | 1 / 1 | Named local administrative territory (1) | 1.2 | grid-high-distortion: 1; repeated-location-province-name: 1; weak-source-parent-match: 1 |
| Mongolia | MNG | 339 / 22 | soum, düüregs (339) | 3,593.0 | multipart-footprint: 3; repeated-location-province-name: 1; weak-source-parent-match: 1 |
| Montenegro | MNE | 23 / 23 | Municipality (23) | 455.7 | multipart-footprint: 3; repeated-location-province-name: 23; weak-source-parent-match: 1 |
| Montserrat | Unmatched | 1 / 1 | Compact source country/territory (1) | 99.3 | repeated-location-province-name: 1 |
| Morocco | MAR | 77 / 12 | Province / prefecture (74); Published geographic subdivision within a source rural district (3) | 3,890.3 | multipart-footprint: 6; weak-source-parent-match: 2 |
| Mozambique | MOZ | 159 / 11 | districts (159) | 4,332.7 | grid-high-distortion: 1; multipart-footprint: 17; repeated-location-province-name: 1; weak-source-parent-match: 4 |
| Myanmar | MMR | 330 / 75 | Township (330) | 1,535.7 | grid-high-distortion: 3; grid-unrepresented: 5; multipart-footprint: 29; repeated-location-province-name: 67; weak-source-parent-match: 19 |
| Namibia | NAM | 111 / 20 | Local constituency territory (108); Published geographic subdivision within a source rural district (3) | 1,911.2 | grid-high-distortion: 1; grid-unrepresented: 5; local-cluster-scale-outlier: 1; multipart-footprint: 3; repeated-location-province-name: 6; weak-source-parent-match: 7 |
| Nauru | NRU | 1 / 1 | Compact source country/territory (1) | 19.9 | repeated-location-province-name: 1 |
| Nepal | NPL | 75 / 7 | Districts (75) | 1,700.8 | multipart-footprint: 4 |
| Netherlands | NLD | 346 / 16 | Municipality (344); Named source island / overseas territory (2) | 81.9 | multipart-footprint: 1; repeated-location-province-name: 4; weak-source-parent-match: 52 |
| New Caledonia | Unmatched | 3 / 3 | ADM1 fallback (3) | 7,321.7 | multipart-footprint: 3; repeated-location-province-name: 3 |
| New Zealand | NZL | 94 / 25 | Territorial authority (88); Named source island / overseas territory (6) | 1,811.3 | local-cluster-scale-outlier: 2; multipart-footprint: 17; repeated-location-province-name: 7; weak-source-parent-match: 9 |
| Nicaragua | NIC | 153 / 19 | Named local administrative territory (153) | 405.2 | multipart-footprint: 7; weak-source-parent-match: 12 |
| Niger | NER | 271 / 69 | Published geographic subdivision within a source rural district (15); Communes (255); Source city territory: Capital District (1) | 858.1 | large-territory-screen: 5; multipart-footprint: 8; repeated-location-province-name: 49; weak-source-parent-match: 2 |
| Nigeria | NGA | 774 / 37 | Local Government Areas (774) | 719.0 | local-cluster-scale-outlier: 1; multipart-footprint: 35; repeated-location-province-name: 6; weak-source-parent-match: 16 |
| Niue | NIU | 1 / 1 | Compact source country/territory (1) | 261.5 | repeated-location-province-name: 1 |
| Norfolk Island | Unmatched | 1 / 1 | ADM1 fallback (1) | 41.4 | repeated-location-province-name: 1; weak-source-parent-match: 1 |
| North Macedonia | MKD | 84 / 8 | Municipality (84) | 231.5 | grid-high-distortion: 1; multipart-footprint: 2; weak-source-parent-match: 3 |
| Northern Cyprus | Unmatched | 1 / 1 | ADM1 fallback (1) | 3,309.8 | multipart-footprint: 1; repeated-location-province-name: 1 |
| Northern Mariana Islands | MNP | 4 / 4 | Municipality (4) | 119.8 | multipart-footprint: 2; repeated-location-province-name: 4; weak-source-parent-match: 4 |
| Norway | NOR | 428 / 13 | Municipality (422); Named source island / overseas territory (2); Disconnected components of the same named source district (4) | 472.4 | large-territory-screen: 1; multipart-footprint: 136; repeated-location-province-name: 2; weak-source-parent-match: 121 |
| Oman | OMN | 63 / 8 | Wilayaf (60); Published geographic subdivision within a source rural district (3) | 1,501.9 | local-cluster-scale-outlier: 1; multipart-footprint: 11; weak-source-parent-match: 2 |
| Pakistan | PAK | 126 / 7 | Districts (126) | 4,798.3 | multipart-footprint: 11; repeated-location-province-name: 2 |
| Palau | PLW | 16 / 16 | Named local administrative territory (16) | 32.3 | grid-unrepresented: 1; multipart-footprint: 3; repeated-location-province-name: 16; weak-source-parent-match: 13 |
| Panama | PAN | 76 / 13 | District (76) | 599.5 | multipart-footprint: 19; weak-source-parent-match: 9 |
| Papua New Guinea | PNG | 326 / 88 | Local Government Areas (326) | 702.7 | grid-high-distortion: 3; grid-unrepresented: 3; multipart-footprint: 41; repeated-location-province-name: 1; weak-source-parent-match: 43 |
| Paraguay | PRY | 243 / 19 | District (241); Source city territory: Capital District (1); Disconnected components of the same named source district (1) | 496.9 | grid-high-distortion: 1; large-territory-screen: 1; multipart-footprint: 3; repeated-location-province-name: 5; weak-source-parent-match: 4 |
| Peru | PER | 204 / 26 | Provinces (193); Published geographic subdivision within a source rural district (11) | 3,196.3 | multipart-footprint: 13; repeated-location-province-name: 11; weak-source-parent-match: 1 |
| Philippines | PHL | 1,575 / 86 | Municipalities (1568); Named metropolitan territory: National Capital Region (1); Source city territory: Highly Urbanized City (3); Source city territory: Independent Component City (3) | 116.4 | grid-high-distortion: 1; multipart-footprint: 126; repeated-location-province-name: 11; weak-source-parent-match: 325 |
| Pitcairn Islands | Unmatched | 1 / 1 | ADM1 fallback (1) | 38.6 | repeated-location-province-name: 1; weak-source-parent-match: 1 |
| Poland | POL | 380 / 16 | County (380) | 765.7 | multipart-footprint: 7; weak-source-parent-match: 4 |
| Portugal | PRT | 311 / 23 | Municipality (311) | 204.7 | multipart-footprint: 12; repeated-location-province-name: 16; weak-source-parent-match: 36 |
| Puerto Rico | PRI | 78 / 1 | Municipality (78) | 111.1 | multipart-footprint: 1; weak-source-parent-match: 5 |
| Qatar | QAT | 8 / 8 | Municipality (8) | 1,610.5 | multipart-footprint: 1; repeated-location-province-name: 8; weak-source-parent-match: 2 |
| Republic of Korea | KOR | 161 / 17 | Si, Kun (districts and city districts) (154); Named metropolitan city; verified district membership (7) | 591.1 | mixed-urban-role-needs-classification: 154; multipart-footprint: 18; repeated-location-province-name: 8; weak-source-parent-match: 21 |
| Republic of Moldova | MDA | 37 / 37 | Districts (37) | 850.2 | multipart-footprint: 6; repeated-location-province-name: 37 |
| Romania | ROU | 42 / 42 | Counties (42) | 5,574.5 | multipart-footprint: 4; repeated-location-province-name: 42 |
| Russian Federation | RUS | 2,397 / 86 | Raion (2288); Published geographic subdivision within a source rural district (106); Named inland-water portion within a source district (1); Named source city territory (2) | 1,910.4 | grid-high-distortion: 1; large-territory-screen: 64; local-cluster-scale-outlier: 11; multipart-footprint: 221; repeated-location-province-name: 1; weak-source-parent-match: 26 |
| Rwanda | RWA | 28 / 5 | District (27); Published city administrative territory; constituent districts combined (1) | 731.3 | multipart-footprint: 2; weak-source-parent-match: 1 |
| Saint Barthelemy | Unmatched | 1 / 1 | ADM1 fallback (1) | 22.7 | repeated-location-province-name: 1 |
| Saint Helena | Unmatched | 3 / 3 | ADM1 fallback (3) | 123.4 | multipart-footprint: 1; repeated-location-province-name: 3; weak-source-parent-match: 3 |
| Saint Kitts and Nevis | KNA | 1 / 1 | Compact source country/territory (1) | 258.6 | multipart-footprint: 1; repeated-location-province-name: 1 |
| Saint Lucia | LCA | 1 / 1 | Compact source country/territory (1) | 610.1 | repeated-location-province-name: 1 |
| Saint Martin | Unmatched | 1 / 1 | ADM1 fallback (1) | 68.4 | repeated-location-province-name: 1; weak-source-parent-match: 1 |
| Saint Pierre and Miquelon | Unmatched | 1 / 1 | Compact source country/territory (1) | 239.4 | multipart-footprint: 1; repeated-location-province-name: 1 |
| Saint Vincent and the Grenadines | VCT | 1 / 1 | Compact source country/territory (1) | 376.4 | multipart-footprint: 1; repeated-location-province-name: 1 |
| Samoa | WSM | 1 / 1 | Compact source country/territory (1) | 2,838.3 | multipart-footprint: 1; repeated-location-province-name: 1 |
| San Marino | SMR | 1 / 1 | Compact source country/territory (1) | 60.3 | repeated-location-province-name: 1 |
| Sao Tome and Principe | STP | 2 / 2 | Named local administrative territory (2) | 859.9 | repeated-location-province-name: 2; weak-source-parent-match: 1 |
| Saudi Arabia | SAU | 157 / 13 | Governorate (141); Published geographic subdivision within a source rural district (16) | 5,013.0 | large-territory-screen: 5; multipart-footprint: 32; weak-source-parent-match: 5 |
| Scarborough Reef | Unmatched | 1 / 1 | ADM0 fallback (1) | 0.1 | grid-unrepresented: 1; repeated-location-province-name: 1; weak-source-parent-match: 1 |
| Senegal | SEN | 45 / 14 | department (45) | 2,753.3 | multipart-footprint: 5; repeated-location-province-name: 14; weak-source-parent-match: 2 |
| Serbia | SRB | 145 / 25 | Municipality (145) | 454.4 | multipart-footprint: 3; repeated-location-province-name: 1; weak-source-parent-match: 1 |
| Serranilla Bank | Unmatched | 1 / 1 | ADM0 fallback (1) | 0.1 | grid-unrepresented: 1; repeated-location-province-name: 1; weak-source-parent-match: 1 |
| Seychelles | SYC | 8 / 8 | Regions (8) | 37.4 | multipart-footprint: 1; repeated-location-province-name: 4; weak-source-parent-match: 5 |
| Siachen Glacier | Unmatched | 1 / 1 | ADM1 fallback (1) | 2,086.7 | repeated-location-province-name: 1 |
| Sierra Leone | SLE | 14 / 4 | Districts (14) | 5,490.7 | multipart-footprint: 4; weak-source-parent-match: 1 |
| Singapore | SGP | 1 / 1 | Compact source country/territory (1) | 775.9 | multipart-footprint: 1; repeated-location-province-name: 1 |
| Sint Maarten | Unmatched | 1 / 1 | ADM1 fallback (1) | 23.1 | repeated-location-province-name: 1 |
| Slovakia | SVK | 79 / 8 | District (79) | 579.8 | multipart-footprint: 2; weak-source-parent-match: 2 |
| Slovenia | SVN | 212 / 7 | Municipality (212) | 67.5 | multipart-footprint: 1; repeated-location-province-name: 4; weak-source-parent-match: 7 |
| Solomon Islands | SLB | 10 / 10 | Province (10) | 3,110.0 | multipart-footprint: 8; repeated-location-province-name: 10; weak-source-parent-match: 7 |
| Somalia | SOM | 108 / 18 | Districts (108) | 2,934.7 | grid-high-distortion: 2; grid-unrepresented: 4; multipart-footprint: 8; weak-source-parent-match: 4 |
| Somaliland | SOM | 22 / 7 | Named district clipped to reference territorial envelope (21); Source district plus numerical remainder of the same partitioned source ID (1) | 7,246.3 | grid-high-distortion: 2; multipart-footprint: 7 |
| South Africa | ZAF | 213 / 53 | Local municipality (213) | 3,662.4 | multipart-footprint: 7; repeated-location-province-name: 8; weak-source-parent-match: 2 |
| South Georgia and the Islands | Unmatched | 1 / 1 | Named source island / overseas territory (1) | 3,935.0 | multipart-footprint: 1; repeated-location-province-name: 1 |
| South Sudan | SSD | 80 / 10 | counties (77); Published geographic subdivision within a source rural district (3) | 5,864.1 | large-territory-screen: 1; multipart-footprint: 3 |
| Southern Patagonian Ice Field | Unmatched | 1 / 1 | ADM0 fallback (1) | 1,401.1 | repeated-location-province-name: 1 |
| Spain | ESP | 384 / 62 | MUNICIPIOS (43); MAPA agricultural district; separately mapped major cities excluded (341) | 1,142.9 | multipart-footprint: 62; repeated-location-province-name: 21; weak-source-parent-match: 6 |
| Spratly Is. | Unmatched | 1 / 1 | ADM1 fallback (1) | 1.9 | grid-high-distortion: 1; repeated-location-province-name: 1; weak-source-parent-match: 1 |
| Sri Lanka | LKA | 25 / 9 | Named local administrative territory (25) | 2,069.0 | multipart-footprint: 3; weak-source-parent-match: 2 |
| State of Palestine | PSE | 16 / 2 | governorate (16) | 290.2 | multipart-footprint: 2; repeated-location-province-name: 1 |
| Sudan | SDN | 196 / 19 | District (185); Published geographic subdivision within a source rural district (11) | 4,178.5 | large-territory-screen: 7; multipart-footprint: 15; repeated-location-province-name: 2; weak-source-parent-match: 1 |
| Suriname | SUR | 59 / 11 | Ressorten (59) | 404.7 | multipart-footprint: 1; weak-source-parent-match: 13 |
| Sweden | SWE | 290 / 21 | Municipality (290) | 737.2 | multipart-footprint: 20; weak-source-parent-match: 24 |
| Switzerland | CHE | 169 / 30 | District (169) | 165.3 | multipart-footprint: 17; repeated-location-province-name: 16; weak-source-parent-match: 17 |
| Syrian Arab Republic | SYR | 61 / 14 | District (61) | 1,256.6 | local-cluster-scale-outlier: 1; multipart-footprint: 5; repeated-location-province-name: 13; weak-source-parent-match: 1 |
| Taiwan | TWN | 207 / 23 | Townships (198); Published city municipality; same-source ADM1 district membership (9) | 64.4 | grid-high-distortion: 1; multipart-footprint: 4; repeated-location-province-name: 10; weak-source-parent-match: 26 |
| Tajikistan | TJK | 58 / 4 | District (58) | 1,213.8 | multipart-footprint: 9; weak-source-parent-match: 1 |
| Thailand | THA | 879 / 79 | districts (878); Source city territory: Province (1) | 476.2 | multipart-footprint: 24; repeated-location-province-name: 2; weak-source-parent-match: 33 |
| Timor-Leste | TLS | 65 / 13 | Administrative Posts (65) | 205.7 | grid-high-distortion: 1; multipart-footprint: 2; repeated-location-province-name: 8; weak-source-parent-match: 8 |
| Togo | TGO | 37 / 6 | Prefectures (37) | 1,240.6 | multipart-footprint: 5; weak-source-parent-match: 3 |
| Tonga | TON | 5 / 5 | Named local administrative territory (5) | 92.9 | multipart-footprint: 3; repeated-location-province-name: 5; weak-source-parent-match: 4 |
| Trinidad and Tobago | TTO | 14 / 14 | Named local administrative territory (14) | 300.0 | repeated-location-province-name: 14; weak-source-parent-match: 4 |
| Tunisia | TUN | 264 / 24 | Delegation (264) | 294.2 | grid-high-distortion: 3; multipart-footprint: 3; weak-source-parent-match: 20 |
| Turkey | TUR | 942 / 83 | Districts (941); Source city territory: Province (1) | 673.0 | multipart-footprint: 14; repeated-location-province-name: 2; weak-source-parent-match: 39 |
| Turkmenistan | TKM | 63 / 5 | Named local administrative territory (47); Named district portion replacing unnamed source fragments (16) | 5,507.4 | large-territory-screen: 1; local-cluster-scale-outlier: 3; multipart-footprint: 7; repeated-location-province-name: 2; weak-source-parent-match: 3 |
| Turks and Caicos Islands | Unmatched | 1 / 1 | Compact source country/territory (1) | 431.5 | multipart-footprint: 1; repeated-location-province-name: 1 |
| Tuvalu | TUV | 8 / 8 | Named local administrative territory (8) | 1.2 | grid-high-distortion: 1; grid-unrepresented: 2; repeated-location-province-name: 8; weak-source-parent-match: 8 |
| Uganda | UGA | 137 / 132 | District (137) | 1,235.9 | multipart-footprint: 8; repeated-location-province-name: 52; weak-source-parent-match: 2 |
| Ukraine | UKR | 495 / 31 | Raions (495) | 1,121.9 | multipart-footprint: 14; repeated-location-province-name: 2; weak-source-parent-match: 7 |
| United Arab Emirates | ARE | 11 / 7 | Published geographic subdivision within a source rural district (5); Named local administrative territory (6) | 1,679.0 | local-cluster-scale-outlier: 1; multipart-footprint: 10; repeated-location-province-name: 6; weak-source-parent-match: 1 |
| United Kingdom | GBR | 184 / 75 | Counties and Unitary Authorities (183); Named metropolitan territory: Greater London (1) | 377.2 | multipart-footprint: 19; repeated-location-province-name: 37; weak-source-parent-match: 14 |
| United Republic of Tanzania | TZA | 170 / 30 | Districts (170) | 3,134.3 | multipart-footprint: 22; repeated-location-province-name: 11; weak-source-parent-match: 9 |
| United States Minor Outlying Islands | Unmatched | 8 / 8 | ADM1 fallback (8) | 1.4 | grid-high-distortion: 2; grid-unrepresented: 2; repeated-location-province-name: 8; weak-source-parent-match: 6 |
| United States of America | USA | 3,176 / 58 | Counties (3137); Published geographic subdivision within a source rural district (37); Five boroughs of New York City (1); Disconnected components of the same named source district (1) | 1,643.0 | grid-high-distortion: 2; grid-unrepresented: 1; large-territory-screen: 7; multipart-footprint: 124; repeated-location-province-name: 8; weak-source-parent-match: 73 |
| United States Virgin Islands | Unmatched | 1 / 1 | Compact source country/territory (1) | 355.9 | multipart-footprint: 1; repeated-location-province-name: 1 |
| Uruguay | URY | 19 / 19 | Named local administrative territory (19) | 9,795.4 | multipart-footprint: 3; repeated-location-province-name: 19 |
| US Naval Base Guantanamo Bay | Unmatched | 1 / 1 | ADM1 fallback (1) | 64.8 | multipart-footprint: 1; repeated-location-province-name: 1; weak-source-parent-match: 1 |
| Uzbekistan | UZB | 201 / 18 | District (198); Published geographic subdivision within a source rural district (3) | 481.9 | grid-high-distortion: 3; grid-unrepresented: 3; large-territory-screen: 1; local-cluster-scale-outlier: 1; multipart-footprint: 19; weak-source-parent-match: 9 |
| Vanuatu | VUT | 6 / 6 | Named local administrative territory (6) | 1,628.6 | multipart-footprint: 6; repeated-location-province-name: 6; weak-source-parent-match: 5 |
| Vatican | Unmatched | 1 / 1 | ADM1 fallback (1) | 0.0 | grid-unrepresented: 1; repeated-location-province-name: 1 |
| Venezuela (Bolivarian Republic of) | VEN | 339 / 27 | Municipios (334); Published geographic subdivision within a source rural district (4); Named source island / overseas territory (1) | 667.2 | multipart-footprint: 14; repeated-location-province-name: 6; weak-source-parent-match: 14 |
| Viet Nam | VNM | 647 / 73 | District (644); Source city territory: Province (1); Source city territory: City\|Municipality\|Thanh Pho (2) | 378.4 | grid-high-distortion: 2; multipart-footprint: 22; repeated-location-province-name: 10; weak-source-parent-match: 61 |
| Wallis and Futuna | Unmatched | 3 / 3 | ADM1 fallback (3) | 58.9 | multipart-footprint: 1; repeated-location-province-name: 3; weak-source-parent-match: 2 |
| Western Sahara | MAR | 5 / 3 | Named district clipped to reference territorial envelope (5) | 24,272.1 | multipart-footprint: 3 |
| Yemen | YEM | 335 / 22 | Districts (335) | 407.4 | grid-high-distortion: 1; local-cluster-scale-outlier: 1; multipart-footprint: 25; weak-source-parent-match: 13 |
| Zambia | ZMB | 116 / 10 | Districts (116) | 5,167.5 | multipart-footprint: 8; repeated-location-province-name: 1; weak-source-parent-match: 2 |
| Zimbabwe | ZWE | 88 / 10 | District (87); Source city territory: City (1) | 3,570.7 | grid-unrepresented: 1; multipart-footprint: 6; repeated-location-province-name: 3; weak-source-parent-match: 2 |

## All source-policy profiles

This second matrix explicitly accounts for every source-policy profile rather than assuming a one-to-one relationship with reference territories. Canonical roles, licenses and dates refer to the selected source layer; later city/physical/functional refinements can have separate provenance recorded in the territory matrix.

| Policy ISO | Reference territories | Policy role | Canonical source role / date | License |
|---|---|---|---|---|
| AFG | Afghanistan | wuleswali | wuleswali / 2014 | Public Domain |
| AGO | Angola | Municipality | Unknown / 2018 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| ALB | Albania | District | rrethe / 2021 | Creative Commons Attribution 2.5 Generic |
| AND | Andorra | Parish | Parish / 2007 | Public Domain |
| ARE | United Arab Emirates | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| ARG | Argentina | departments | departments / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| ARM | Armenia | Municipal community | Municipal Communities / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| ATG | Antigua and Barbuda | Parish and Dependency | Parish and Dependency / 2009 | Public Domain |
| AUS | Australia | Local Government Areas | Local Government Areas / 2022 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| AUT | Austria | District | Unknown / 2017 | Creative Commons Attribution-ShareAlike 2.0 |
| AZE | Azerbaijan | District | Unknown / 2020 | Creative Commons Attribution-ShareAlike 3.0 Unported |
| BDI | Burundi | Commune | Unknown / 2007 | Public Domain |
| BEL | Belgium | Arrondissements | Arrondissements / 2014 | CC0 1.0 Universal (CC0 1.0) Public Domain Dedication |
| BEN | Benin | Commune | Commune / 2007 | Public Domain |
| BFA | Burkina Faso | Named local administrative territory | Unknown / 2007 | Public Domain |
| BGD | Bangladesh | district | district / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| BGR | Bulgaria | Municipality | Municipality / 2019 | Public Domain |
| BHR | Bahrain | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| BHS | Bahamas | Districts | Districts / 09-09-2017 to 24-08-2020 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| BIH | Bosnia and Herzegovina | Municipality | gbOpen / 2013 | Public Domain |
| BLR | Belarus | Raion | Raion / 2005 | Creative Commons Attribution 3.0 License |
| BLZ | Belize | Districts | Districts / 2006 | Creative Commons Attribution 2.5 Generic |
| BOL | Bolivia (Plurinational State of) | Province | Unknown / 2015 | Public Domain |
| BRA | Brazil | municipality | municipality / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| BRB | Barbados | Parish | Parish / 2005 | Creative Commons Attribution 2.5 Generic |
| BRN | Brunei Darussalam | Districts | Districts / 2011 | Public Domain |
| BTN | Bhutan | Dzongdeys | Dzongdeys / 2010 | Creative Commons Attribution 3.0 License |
| BWA | Botswana | Subdistrict | Unknown / 2015 | Public Domain |
| CAF | Central African Republic | Commune | Municipalities / 2018 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| CAN | Canada | Named local administrative territory | Unknown / 2016 | Open Data Commons Open Database License 1.0 |
| CHE | Switzerland | District | District / 2022 | Federal Office of Topography swisstopo License |
| CHL | Chile | Communes | Communes / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| CHN | China | County Level | County Level / 2017 | Open Data Commons Public Domain Dedication and License (PDDL) v1.0 |
| CIV | Côte d'Ivoire | Departments | Departments / 2021 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| CMR | Cameroon | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| COD | Democratic Republic of the Congo | territory, city | territory, city / 2019 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| COG | Congo | Named local administrative territory | Unknown / 2007 | Public Domain |
| COL | Colombia | Municipality | Unknown / 2020 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| COM | Comoros | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| CPV | Cabo Verde | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| CRI | Costa Rica | Canton | Cantons / 2020 | CC0 1.0 Universal (CC0 1.0) Public Domain Dedication |
| CUB | Cuba | Municipality | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| CYP | Cyprus | District | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| CZE | Czechia | District | District / 2010 | Public Domain |
| DEU | Germany | Independent City or District | Independent City or District / 2021 | Data license Germany - Attribution - Version 2.0 |
| DJI | Djibouti | Districts | Districts / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| DMA | Dominica | Parish | Parish / 2005 | Creative Commons Attribution 2.5 Generic |
| DNK | Denmark | Municipality | kommune / 2018 | Public Domain |
| DOM | Dominican Republic | Municipalities | Municipalities / 2020 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| DZA | Algeria | Commune | Unknown / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| ECU | Ecuador | Cantons | Cantons / 2019 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| EGY | Egypt | marakiz and aqsam | marakiz and aqsam / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| ERI | Eritrea | districts | districts / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| ESP | Spain | MUNICIPIOS | MUNICIPIOS / 2018 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| EST | Estonia | Municipality | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| ETH | Ethiopia | Named local administrative territory | Unknown / 2016 | Open Data Commons Open Database License 1.0 |
| FIN | Finland | Subregion | Unknown / 2016 | Open Data Commons Open Database License 1.0 |
| FJI | Fiji | Provinces | Provinces / 2020 | Creative Commons Attribution 4.0 (CC BY 4.0) |
| FRA | France | Arrondissement | Arrondissement / 2022 | Etalab Open License 2.0 |
| FSM | Micronesia (Fed. States of) | State | State / 2019 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| GAB | Gabon | Department | Department / 2018 | Creative Commons Attribution 3.0 License |
| GBR | United Kingdom | Counties and Unitary Authorities | Counties and Unitary Authorities / 2019 | Open Government Licence v3.0 |
| GEO | Georgia | Municipality | Municipality / 2007 | Public Domain |
| GHA | Ghana | Districts | Districts / 2019 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| GIN | Guinea | prefecture | prefecture / 2017 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| GMB | Gambia | District | District / 2020 | Creative Commons Attribution 4.0 (CC BY 4.0) |
| GNB | Guinea-Bissau | Sector | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| GNQ | Equatorial Guinea | District | Unknown / 2013 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| GRC | Greece | Municipality | municipality / 2010 | CC0 1.0 Universal (CC0 1.0) Public Domain Dedication |
| GRD | Grenada | Parish | Parish / 2017 | Creative Commons Attribution-ShareAlike 2.0 |
| GRL | Greenland | Municipalities | Municipalities / 2020 | Creative Commons Attribution-ShareAlike 3.0 Unported |
| GTM | Guatemala | Municipality | Municipio / 2021 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| GUM | Guam | Village | Village / 2021 | Public Domain |
| GUY | Guyana | Neighbourhood Councils | Neighbourhood Councils / 2019 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| HND | Honduras | Municipality | Municipalities / 2019 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| HRV | Croatia | Municipality / town | Municipalities and Towns / 2021 | Creative Commons Attribution-ShareAlike 2.0 |
| HTI | Haiti | Arrondissement | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| HUN | Hungary | District | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| IDN | Indonesia | regency, city | regency, city / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| IND | India | District | District / 2021 | Open Data Commons Open Database License 1.0 |
| IRL | Ireland | County / county-level city | Separate source/fallback / Not established by selected-layer metadata | See actual territory-source provenance |
| IRN | Iran (Islamic Republic of) | Shahrestan | Shahrestan / 2017 | Open Data Commons Open Database License 1.0 |
| IRQ | Iraq | Districts | Districts / 2021 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| ISL | Iceland | Municipality | Municipalities / 2016 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| ISR | Israel | Subdistrict | Subdistrict / 2021 | CC0 1.0 Universal (CC0 1.0) Public Domain Dedication |
| ITA | Italy | Province / metropolitan city | Unknown / 2023 | Creative Commons Attribution 3.0 License |
| JAM | Jamaica | parish | parish / 2011 | Creative Commons Attribution-ShareAlike 2.0 |
| JOR | Jordan | Nahias | Nahias / 2006 | Public Domain |
| JPN | Japan | Municipality / city ward | Subprefectures / 2017 | Creative Commons Attribution-ShareAlike 2.0 |
| KAZ | Kazakhstan | District | District / 2017 | Open Data Commons Open Database License 1.0 |
| KEN | Kenya | Sub-Counties | Sub-Counties / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| KGZ | Kyrgyzstan | Raions | Raions / 2010 | Creative Commons Attribution-ShareAlike 3.0 Unported |
| KHM | Cambodia | District | Unknown / 2014 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| KIR | Kiribati | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| KNA | Saint Kitts and Nevis | parish | parish / 2021 | Creative Commons Attribution-ShareAlike 2.0 |
| KOR | Republic of Korea | Si, Kun (districts and city districts) | Si, Kun (districts and city districts) / 2020 | Creative Commons Attribution 3.0 License |
| KWT | Kuwait | Governorate | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| LAO | Lao People's Democratic Republic | Districts | Districts / 2019 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| LBN | Lebanon | Districts (Aqdya) | Districts (Aqdya) / 2021 | Public Domain |
| LBR | Liberia | District | Districts / 2021 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| LBY | Libya | District | Districts / 2021 | Public Domain |
| LCA | Saint Lucia | District | District / 2015 | CC0 1.0 Universal (CC0 1.0) Public Domain Dedication |
| LIE | Liechtenstein | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| LKA | Sri Lanka | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| LSO | Lesotho | District | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| LTU | Lithuania | Municipality | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| LUX | Luxembourg | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| LVA | Latvia | Administratīvās teritorijas | Administratīvās teritorijas / 2021 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| MAR | Morocco, Western Sahara | Province / prefecture | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| MCO | Monaco | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| MDA | Republic of Moldova | Districts | Districts / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| MDG | Madagascar | District | districts / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| MDV | Maldives | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| MEX | Mexico | municipios | municipios / 2012 | Creative Commons Attribution 4.0 (CC BY 4.0) |
| MHL | Marshall Islands | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| MKD | North Macedonia | Municipality | Opštini / 2016 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| MLI | Mali | Cercle | Cercle / 2017 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| MLT | Malta | Local Council | Local Council / 2022 | Public Domain |
| MMR | Myanmar | Township | Township / 2019 | Creative Commons Attribution 4.0 (CC BY 4.0) |
| MNE | Montenegro | Municipality | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| MNG | Mongolia | soum, düüregs | soum, düüregs / 2021 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| MNP | Northern Mariana Islands | Municipality | Municipality / 2021 | Public Domain |
| MOZ | Mozambique | districts | districts / 2019 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| MRT | Mauritania | Mauritania | Mauritania / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| MUS | Mauritius | Districts and Outer Islands of Mauritius | Districts and Outer Islands of Mauritius / 2017 | Open Data Commons Open Database License 1.0 |
| MWI | Malawi | district | district / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| MYS | Malaysia | Districts | Districts / 2020 | Creative Commons Attribution 3.0 License |
| NAM | Namibia | Local constituency territory | Unknown / 2007 | Public Domain |
| NER | Niger | Communes | Communes / 2012 | Creative Commons Attribution 3.0 License |
| NGA | Nigeria | Local Government Areas | Local Government Areas / 2022 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| NIC | Nicaragua | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| NIU | Niue | village | village / 2020 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| NLD | Netherlands | Municipality | Municipality / 2022 | CC0 1.0 Universal (CC0 1.0) Public Domain Dedication |
| NOR | Norway | Municipality | Unknown / 2013 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| NPL | Nepal | Districts | Districts / 2006 | Public Domain |
| NRU | Nauru | District | District / 2005 | Public Domain |
| NZL | New Zealand | Territorial authority | Territorial Authorities / 2021 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| OMN | Oman | Wilayaf | Wilayaf / 2020 | Other - Direct Permission |
| PAK | Pakistan | Districts | Districts / 2019 | Public Domain |
| PAN | Panama | District | Unknown / 2012 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| PER | Peru | Provinces | Provinces / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| PHL | Philippines | Municipalities | Municipalities / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| PLW | Palau | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| PNG | Papua New Guinea | Local Government Areas | Local Government Areas / 2019 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| POL | Poland | County | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| PRI | Puerto Rico | Municipality | Municipality / 2021 | Public Domain |
| PRK | Dem. People's Republic of Korea | county, city, special city | county, city, special city / 2019 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| PRT | Portugal | Municipality | gbOpen / 2020 | CC0 1.0 Universal (CC0 1.0) Public Domain Dedication |
| PRY | Paraguay | District | gbOpen / 2012 | Creative Commons Attribution 4.0 (CC BY 4.0) |
| PSE | State of Palestine | governorate | governorate / 2017 | Creative Commons Attribution 4.0 (CC BY 4.0) |
| QAT | Qatar | Municipality | Unknown / 2015 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| ROU | Romania | Counties | Counties / 2017 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| RUS | Russian Federation | Raion | Raion / 2017 | Open Data Commons Open Database License 1.0 |
| RWA | Rwanda | District | Unknown / 2012 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| SAU | Saudi Arabia | Governorate | Governorate / 2021 | Creative Commons Attribution-ShareAlike 2.0 |
| SDN | Sudan | District | District / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| SEN | Senegal | department | department / 2019 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| SGP | Singapore | Named local administrative territory | Unknown / 2016 | Open Data Commons Open Database License 1.0 |
| SLB | Solomon Islands | Province | Province / 2021 | Public Domain |
| SLE | Sierra Leone | Districts | Districts / 2017 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| SLV | El Salvador | Municipalities | Municipalities / 2007 | Public Domain |
| SMR | San Marino | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| SOM | Somalia, Somaliland | Districts | Districts / 2022 | Creative Commons Attribution 4.0 (CC BY 4.0) |
| SRB | Serbia | Municipality | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| SSD | South Sudan | counties | counties / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| STP | Sao Tome and Principe | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| SUR | Suriname | Ressorten | Ressorten / 2021 | Public Domain |
| SVK | Slovakia | District | Okres / 2017 | Open Data Commons Open Database License 1.0 |
| SVN | Slovenia | Municipality | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| SWE | Sweden | Municipality | Municipality / 2017 | CC0 1.0 Universal (CC0 1.0) Public Domain Dedication |
| SWZ | Eswatini | Inkhundla | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| SYC | Seychelles | Regions | Regions / 2020 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| SYR | Syrian Arab Republic | District | District / 2017 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| TCD | Chad | Departments | Departments / 2019 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| TGO | Togo | Prefectures | Prefectures / 2017 | Creative Commons Attribution-ShareAlike 2.0 |
| THA | Thailand | districts | districts / 2019 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| TJK | Tajikistan | District | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| TKM | Turkmenistan | Named local administrative territory | Unknown / 2009 | Creative Commons Attribution-ShareAlike 3.0 Unported |
| TLS | Timor-Leste | Administrative Posts | Administrative Posts / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| TON | Tonga | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| TTO | Trinidad and Tobago | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| TUN | Tunisia | Delegation | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| TUR | Turkey | Districts | Districts / 2021 | Open Data Commons Open Database License 1.0 |
| TUV | Tuvalu | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| TWN | Taiwan | Townships | Townships / 2017 | Creative Commons Attribution-ShareAlike 2.0 |
| TZA | United Republic of Tanzania | Districts | Districts / 2021 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| UGA | Uganda | District | District / 2020 | CC0 1.0 Universal (CC0 1.0) Public Domain Dedication |
| UKR | Ukraine | Raions | Raions / 2006 | Public Domain |
| URY | Uruguay | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| USA | United States of America | Counties | Counties / 2018 | Public Domain |
| UZB | Uzbekistan | District | Tuman / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| VCT | Saint Vincent and the Grenadines | Parishes | Parishes / 2017 | Open Data Commons Open Database License 1.0 |
| VEN | Venezuela (Bolivarian Republic of) | Municipios | Municipios / 2015 | Open Data Commons Open Database License 1.0 |
| VNM | Viet Nam | District | District / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| VUT | Vanuatu | Named local administrative territory | Unknown / 2017 | Open Data Commons Open Database License 1.0 |
| WSM | Samoa | Named local administrative territory | Unknown / 2018 | Creative Commons Attribution-ShareAlike 3.0 Unported |
| XKX | Kosovo | Municipalities | Municipalities / 2021 | Creative Commons Attribution-ShareAlike 2.0 |
| YEM | Yemen | Districts | Districts / 2021 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| ZAF | South Africa | Local municipality | Local municipality / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |
| ZMB | Zambia | Districts | Districts / 2020 | Creative Commons Attribution 4.0 (CC BY 4.0) |
| ZWE | Zimbabwe | District | District / 2020 | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) |

## Completion gate

This evidence does not close any country or territory simply because its chain is complete or its automated flags are empty. Complete the top-down macro review, then resolve every province/local-territory branch using source-based decisions, complete-city and island/coverage checks, explicit migration crosswalks and archived evidence. Independently research all 49 unmatched reference territories and the 28 generic source-policy roles. A reviewed flag must have a correction or a documented geographic exception; an unresolved source remains visibly open.

The inspected footprint snapshot is `1c8c1584520d7360375c8ac79f12fe840dd8a47efb10f3d05c8517689667dd58`. Input hashes in the JSON record the exact policy, source, hierarchy, semantic, coverage and pixel audit snapshots used. This source-granularity report is separate from [the macro-boundary review](GLOBAL_MACRO_REVIEW.md).

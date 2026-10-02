# Europe: exhaustive current-ID inspection and bounded corrections

The review covers every current European branch: **1 continent, 4 subcontinents, 11 regions, 129 areas, 1,009 provinces and 8,722 locations**. The current hierarchy SHA-256 is `ababc53ece8f080ff266af21a57276cab8e47a79be0763635f731dcc9df25fca`. [europe.json](../../data/geographic-decisions/europe.json) records every ID, current parent, decision, source, member inventory and unresolved reason. Antarctica is excluded.

This is a complete inspection inventory and a concrete correction proposal, **not completed semantic approval of Europe**. All 8,722 local territories still require independent assessment of settlement/function, fragmentation and neighboring scale. Retaining a sourced department/region relationship does not approve every descendant location. No location geometry, hierarchy, historical record or owner was changed by this review.

## Actual evidence and inspection

- All **8,722 current polygons** were inspected for validity, parts, geographic bounds and WGS84 ellipsoidal land area. All are valid.
- **7,723 direct-source locations** were matched by their original source shape IDs to actual pinned polygons and compared geometrically. **999** aggregations, physical adaptations or other references require independent member-source validation.
- **798 province groups** matched exact named polygons across **39 pinned parent source layers**. The JSON includes exact shape IDs, cache hashes, current member IDs and source containment diagnostics.
- **123 locations** retain less than 80% of the original source footprint, distributed across 17 reference owners. This is a review flag: source polygons may include marine areas, and a low retained share is not sufficient evidence to restore geometry.
- Actual French government JSON responses supply all **96 mainland department → 13 region** relationships and names. Every current French department member relationship matched the official codes; their assembled footprints were separately compared with pinned department polygons.
- TDWG’s README explicitly defines botanical-country units and warns that some ignore political considerations. It supports the diagnosis of source-border fragments; it does not automatically validate this atlas’s tiers.
- Eurostat explicitly favors administrative divisions, allows geographic exceptions and distinguishes statistical size thresholds. Those thresholds are not location quotas or equal-area requirements.
- SSB lists separately dated Norwegian county versions in 2022, 2024 and 2026. The 2022 parent / 2013 location combination remains a reference-vintage problem.
- The Belgian government request returned an anti-bot challenge with HTTP 200; that is **not** usable evidence. ONS and Malta official requests returned 403. Those requests are recorded as failures, not source approvals.

## Supported corrections

The proposed changes preserve all location land and stable IDs. Root integration must archive merged geographic identities and original chains rather than erase them. Geometry and political assignment are separate.

| Change | Scope | Why supported |
| --- | --- | --- |
| Merge duplicate province fragments | **29 source-fragment groups into 24 existing province identities** | Exact identical source layer and source shape ID; every incoming member lies at least 90% inside that named pinned parent polygon. |
| Reparent Basel-Stadt | Existing canton identity → existing Switzerland area | Three canton fragments were placed under France, Baden-Württemberg and Germany botanical remnants. Identical canton-source identity supports joining whole member geography. |
| Repair Portuguese encoding | Setúbal, Évora, Santarém, Bragança province display labels | Exact reversible UTF-8/Latin-1 decoding; same source shape identity and unchanged geometry. |
| Correct French reference names | Côtes-d’Armor; strip trailing space from Indre-et-Loire | Exact official government name/code rows. |
| Rename Malta-only area | Sicilia → Malta | Actual area membership contains solely the Malta archipelago; the pinned Natural Earth original has GEOUNIT=Malta. Macro placement and repeated tiers remain open. |

The fragment consolidations cover Bulgaria; Swiss cantons; German Lüneburg and Schleswig-Holstein; Spanish Ourense, Gipuzkoa, Navarra, Girona, Huelva, Huesca, Badajoz and Lleida; Estonian Tartu and Ida-Viru; Croatian Koprivnica-Križevci and Međimurje; Hungarian Vas; Dutch Noord-Brabant and Limburg; Portuguese Viana do Castelo; Russian Nizhny Novgorod; and Slovenian Vzhodna. This applies one source-identity rule across the continent rather than special-casing user examples.

The Greek South Aegean and Crimea duplicate sets remain open: incoming geometry does not satisfy strong pinned source correspondence. No geopolitical ownership decision is made by those geographic labels.

## Every regional branch

Counts and findings refer to the inspected pre-migration hierarchy. All eleven branches remain semantically open.

| Region | Areas / provinces / locations | Direct-source locations / low retention | Required remaining semantic work |
| --- | --- | --- | --- |
| Southeastern Europe | 12 / 213 / 1852 | 1849 / 45 | The macro-region is a geographic Balkan/Thracian grouping, but its current areas mix modern national envelopes, island groups, the outdated botanical Yugoslavia label and small cross-border remnants. Source provincial roles differ substantially: Albanian qarqet, Bulgarian oblasts, Croatian counties, Bosnian cantons/entities, Greek regional units and Serbian districts cannot be equated merely because source ADM numbers match. |
| Central Europe | 17 / 139 / 1385 | 1382 / 3 | Administrative hierarchy can support Länder/government-district/local-district clusters, cantons, Czech/Slovak regions and Polish voivodeships. The current mixture of country-sized WGSRPD areas and selected German Länder is not a consistent area role. Basel-Stadt occurs in three distinct province groups under France, Baden-Württemberg and Germany; these are declared geographic portions, not three modern cantons. |
| Low Countries | 6 / 26 / 388 | 387 / 3 | Belgian Flemish/Walloon/Brussels areas above provinces are supported tier roles, including Brussels’ coextensive statistical exception. Netherlands is one country-wide area above twelve provinces, while Belgium/Germany residual areas include cross-border source matches; Luxembourg’s compact whole-territory chain is a separate coextensive exception, not a regional-size target. |
| Eastern European Plain | 12 / 123 / 2010 | 2006 / 29 | A physical-plain macro-region is appropriate across several owners; its area labels presently combine Russian botanical subdivisions, Belarus, Ukraine containing Moldovan administrative districts, and Krym. Some Russian macro-area labels follow historical economic/geographic units; their purpose must be documented separately from selected-year sovereignty. |
| Nordic Europe | 7 / 69 / 961 | 958 / 24 | Country/island geographic areas above Nordic county/region units can be a meaningful scheme. The main issue is source vintage compatibility: Norway has 2022 eleven-county provinces but 2013 municipal location boundaries; the inspected official 2026 classification lists fifteen named counties plus an unspecified code. Finland/Iceland source canonical roles are missing, and Greenland is correctly evaluated separately under North America. |
| Iberia | 18 / 81 / 655 | 320 / 1 | Spanish autonomous communities above province/local territories are a supported administrative-geographic tier pattern, but current atlas groups contain geographic portions and a residual Spain area. Mainland Portugal uses a country-wide area above districts, a different intermediate role; Andorra/Gibraltar are legitimate compact exceptions if source scope is stated. |
| Baltic | 3 / 71 / 317 | 317 / 16 | The Baltic macro-region is geographically recognizable, but one Baltic States area mixes Estonian counties, Lithuanian counties and Latvian 2021 administrative territories at the province tier. Three residual areas labeled Northwest European Russia/Northwestern Russia contain Baltic source units. Comparable source-role decisions are required; names alone do not establish local administrative equivalence. |
| France | 15 / 99 / 323 | 321 / 1 | Thirteen mainland/Corsican French regions above departments and arrondissement locations are supported administrative roles at the supplied 2022 vintage. Monaco and the Channel Islands are independent geographic exceptions within this atlas macro-region; the region name must describe that broader scope rather than imply political possession. |
| Britain | 16 / 70 / 174 | 172 / 1 | ONS documents nine English statistical regions and county/unitary/metropolitan distinctions; regions and metropolitan counties are not simply a current government reporting chain. Scotland uses thirty-two unitary council areas. Current atlas areas such as London and South East England, Eastern/Highlands and Islands and Welsh subregions mix atlas aggregation with statistical reference zones; their provenance needs precise source codes/vintage. |
| Ireland | 2 / 10 / 45 | 11 / 0 | The island-of-Ireland macro-region is country-independent as required. Four historic Irish provinces are meaningful geographic groupings but not four current first-level administrations. Northern Ireland mixes an overall province and five source statistical subregions; official ONS evidence shows eleven current local-government districts since 2015, replacing twenty-six older districts. |
| Italy | 21 / 108 / 612 | 0 / 0 | Italian region areas are named administrative-geographic envelopes, while locations are functional local labour systems and atlas province footprints are assembled from whole labour systems assigned by greatest source-province overlap. This is a documented functional adaptation, not exact administrative province geometry. San Marino/Vatican use compact whole-territory exceptions. |

## Every represented reference-owner group

Owner labels here crosswalk input-source coverage only; they do not determine country-independent region geography or selected-year ownership. Each row is part of the same inspection rubric.

| Reference owner | European location records | Source roles | Vintages | Low source retention |
| --- | --- | --- | --- | --- |
| Aland | 1 | Compact source country/territory | Undated modern reference | 0 |
| Albania | 36 | District | 2021 | 0 |
| Andorra | 1 | Compact source country/territory | Undated modern reference | 0 |
| Austria | 94 | District | 2017 | 0 |
| Belarus | 118 | Raion | 2005 | 0 |
| Belgium | 43 | Arrondissements | 2014 | 0 |
| Bosnia and Herzegovina | 142 | Municipality | 2013 | 0 |
| Bulgaria | 265 | Municipality | 2019 | 0 |
| Croatia | 557 | Municipality / town; Source city territory: City | 2021; Undated modern reference | 25 |
| Czechia | 77 | District | 2010 | 0 |
| Denmark | 98 | Municipality | 2018 | 0 |
| Estonia | 214 | Municipality | 2017 | 15 |
| Faroe Islands | 1 | unknown | Undated modern reference | 0 |
| Finland | 70 | Subregion | 2016 | 4 |
| France | 320 | Arrondissement | 2022 | 0 |
| Germany | 409 | Independent City or District; Source city territory: State | 2021; Undated modern reference | 2 |
| Gibraltar | 1 | unknown | Undated modern reference | 0 |
| Greece | 306 | Municipality | 2010 | 15 |
| Guernsey | 1 | unknown | Undated modern reference | 0 |
| Hungary | 176 | District; Source city territory: Capital City | 2017; Undated modern reference | 0 |
| Iceland | 74 | Municipality | 2016 | 5 |
| Ireland | 34 | unknown | Undated modern reference | 0 |
| Isle of Man | 1 | unknown | Undated modern reference | 0 |
| Italy | 610 | Published named commuting territory; multiple contiguous municipalities. Atlas parent grouping follows whole systems, not exact administrative province borders. | 2011 geography, 2018 update | 0 |
| Jersey | 1 | unknown | Undated modern reference | 0 |
| Kosovo | 7 | Municipalities | 2021 | 0 |
| Latvia | 43 | Administratīvās teritorijas | 2021 | 1 |
| Liechtenstein | 1 | Compact source country/territory | Undated modern reference | 0 |
| Lithuania | 60 | Municipality | 2017 | 0 |
| Luxembourg | 1 | Compact source country/territory | Undated modern reference | 0 |
| Malta | 1 | Compact source country/territory | Undated modern reference | 0 |
| Monaco | 1 | Named local administrative territory | 2017 | 1 |
| Montenegro | 23 | Municipality | 2017 | 0 |
| Netherlands | 344 | Municipality | 2022 | 3 |
| North Macedonia | 84 | Municipality | 2016 | 2 |
| Norway | 427 | Municipality; Territory | 2013; Undated modern reference | 15 |
| Poland | 380 | County | 2017 | 1 |
| Portugal | 281 | Municipality | 2020 | 0 |
| Republic of Moldova | 37 | Districts | 2020 | 0 |
| Romania | 42 | Counties | 2017 | 0 |
| Russian Federation | 1360 | Federal City; Raion | 2017; Undated modern reference | 20 |
| San Marino | 1 | Compact source country/territory | Undated modern reference | 0 |
| Serbia | 145 | Municipality | 2017 | 0 |
| Slovakia | 79 | District | 2017 | 0 |
| Slovenia | 212 | Municipality | 2017 | 3 |
| Spain | 372 | MAPA agricultural district; separately mapped major cities excluded; MUNICIPIOS | 2018; Undated modern reference | 1 |
| Sweden | 290 | Municipality | 2017 | 0 |
| Switzerland | 169 | District | 2022 | 0 |
| Turkey | 32 | Districts; Source city territory: Province | 2021; Undated modern reference | 0 |
| Ukraine | 495 | Raions | 2006 | 9 |
| United Kingdom | 184 | Counties and Unitary Authorities; Named metropolitan territory: Greater London | 2019; Undated modern reference | 1 |
| Vatican | 1 | unknown | Undated modern reference | 0 |

## Single-location fallback investigations

Every European single-location fallback province was checked against actual adjacent-tier source polygons. All eleven stay open; weak coastline/vintage geometry is not resolved by nearest-centroid assignment.

| Location | Best pinned candidate | Current land inside candidate | Status |
| --- | --- | --- | --- |
| Sukarrieta | Bizkaia | 46.8% | Open: legal/administrative membership and coastline reconciliation required. |
| Elafonisos | Peloponnisoy | 46.9% | Open: legal/administrative membership and coastline reconciliation required. |
| Ydra | Attikis | 25.4% | Open: legal/administrative membership and coastline reconciliation required. |
| Poros | Attikis | 37.1% | Open: legal/administrative membership and coastline reconciliation required. |
| Ilhavo | AVEIRO | 16.1% | Open: legal/administrative membership and coastline reconciliation required. |
| Espinho | PORTO | 38.9% | Open: legal/administrative membership and coastline reconciliation required. |
| Piran / Pirano | Zahodna Slovenija | 15.4% | Open: legal/administrative membership and coastline reconciliation required. |
| Izola / Isola | Zahodna Slovenija | 37.7% | Open: legal/administrative membership and coastline reconciliation required. |
| Ankaran / Ancarano | Zahodna Slovenija | 40.7% | Open: legal/administrative membership and coastline reconciliation required. |
| Gagarin | Sevastopol | 14.3% | Open: legal/administrative membership and coastline reconciliation required. |
| Hodoj | Vzhodna | 49.0% | Open: legal/administrative membership and coastline reconciliation required. |

## Measurement and limits

Location original-source comparisons use WGS84 `pyproj.Geod` polygon area: absolute exterior area minus absolute interior-ring areas, summed over polygon components. Current/source intersection is calculated with Shapely valid polygon geometry, then measured geodesically. This is a geographic diagnostic, not the majority-ownership preparation algorithm. Europe’s compared local footprints are away from the antimeridian. Source retention = intersection area / original source area; containment = intersection area / current area. Original shapes can include water.

Province member diagnostics use the exact union of current member polygons and pinned source geometry. The stored parent containment shares are planar diagnostics and are labeled accordingly. They establish strong source correspondence for reviewed incoming fragments; publication still needs root’s geometry/membership validation and archived-identity migration.

No macro continent/subcontinent boundary was approved simply because it matches owner borders. The Europe/Asia physical convention, island exceptions and regional extent still require explicit geographic decisions. No group is created to approach an EU5 count.

All current unit IDs have a decision row. All current location IDs occur exactly once in the location review and inventory. Name corrections are modern reference fixes and must not become ancient labels; historical names still require their own dated source intervals.

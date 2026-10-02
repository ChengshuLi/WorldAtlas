# Africa: exhaustive sourced decisions and explicit remaining work

This batch inventories all **1,361 groups and 8,949 locations**, across **11 regions and 65 represented reference-owner territories**. It inspects actual pinned JSON geometry and metadata, not just administrative level numbers or example locations. No geography or database was mutated by this audit. Decisions are proposed migrations with stable-ID provenance. Antarctica remains excluded.

## What was inspected

- Every current African member polygon: all 8,949 geometries are valid.
- Original local polygons for 8,559 direct source features, with precise WGS84 current/original and intersection area measurements.
- Named original administrative-parent polygons for every verifiable member; 7,203 members have at least 98% area agreement, 1,680 fall below 98%, and 66 lack a measured named-parent polygon.
- Canonical source roles, represented vintages, licenses and exact source feature IDs for every country/territory.
- All repeated named source-parent families, including foreign botanical-country fragments and Somaliland/Somalia reference-mask duplicates.

A source polygon may contain water. A smaller display footprint therefore triggers inspection rather than an automatic missing-land claim. Exact problem IDs and measured values are in the JSON. Source matching does not approve modern administration, historical labels, urban coherence or descendant granularity.

## Concrete migrations

| Old unit | Action / retained unit | Source evidence |
| --- | --- | --- |
| Somalia (`atlas:parent-evidence:area:2e96c0ee3dd39ef9`) | merge: Somalia | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/SOM/ADM1/geoBoundaries-SOM-ADM1.geojson) |
| Algeria (`atlas:parent-evidence:area:383ae4dcc3546c06`) | merge: Algeria | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/DZA/ADM1/geoBoundaries-DZA-ADM1.geojson) |
| Mozambique (`atlas:parent-evidence:area:909a39dcf73cd0e8`) | merge: Mozambique | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/MOZ/ADM1/geoBoundaries-MOZ-ADM1.geojson) |
| Togdheer (`atlas:parent-evidence:province:07ca8e4c52c7be0d`) | merge: Togdheer | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/SOM/ADM1/geoBoundaries-SOM-ADM1.geojson) |
| El Tarf (`atlas:parent-evidence:province:295fba9a5be3d6ef`) | merge: El Tarf | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/DZA/ADM1/geoBoundaries-DZA-ADM1.geojson) |
| Niassa (`atlas:parent-evidence:province:50d8b9b9304c3f6a`) | merge: Niassa | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/MOZ/ADM1/geoBoundaries-MOZ-ADM1.geojson) |
| Bouvet I. (`framework:area:bouvet-i:6f8a0a0de684`) | rename: Bouvet Island | [inspected source](https://raw.githubusercontent.com/tdwg/wgsrpd/master/README.md) |
| Burkina (`framework:area:burkina:40e9db1629ea`) | rename: Burkina Faso | [inspected source](https://unstats.un.org/unsd/methodology/m49/overview/) |
| Canary Is. (`framework:area:canary-is:69a7b4cc4432`) | rename: Canary Islands | [inspected source](https://raw.githubusercontent.com/tdwg/wgsrpd/master/README.md) |
| Cape Verde (`framework:area:cape-verde:a7c5fdada5b4`) | rename: Cabo Verde | [inspected source](https://unstats.un.org/unsd/methodology/m49/overview/) |
| Gambia, The (`framework:area:gambia-the:4d8ac268bae1`) | rename: Gambia | [inspected source](https://unstats.un.org/unsd/methodology/m49/overview/) |
| Gulf of Guinea Is. (`framework:area:gulf-of-guinea-is:38986b297bde`) | rename: Gulf of Guinea Islands | [inspected source](https://raw.githubusercontent.com/tdwg/wgsrpd/master/README.md) |
| Ivory Coast (`framework:area:ivory-coast:86d2b1a53604`) | rename: Côte d’Ivoire | [inspected source](https://unstats.un.org/unsd/methodology/m49/overview/) |
| Mozambique Channel Is. (`framework:area:mozambique-channel-is:3a4f67a407f4`) | rename: Mozambique Channel Islands | [inspected source](https://raw.githubusercontent.com/tdwg/wgsrpd/master/README.md) |
| St.Helena (`framework:area:st-helena:db4eecec44e8`) | rename: Saint Helena | [inspected source](https://raw.githubusercontent.com/tdwg/wgsrpd/master/README.md) |
| Swaziland (`framework:area:swaziland:02c2e32eff24`) | rename: Eswatini | [inspected source](https://unstats.un.org/unsd/methodology/m49/overview/) |
| Zaïre (`framework:area:zaire:1b5e542ab32a`) | rename: Democratic Republic of the Congo | [inspected source](https://unstats.un.org/unsd/methodology/m49/overview/) |
| Awdal (`framework:province:awdal:68a1ed29ae51`) | merge: Awdal | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/SOM/ADM1/geoBoundaries-SOM-ADM1.geojson) |
| Bafing (`framework:province:bafing:6bd6c39d7894`) | merge: Bafing | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/CIV/ADM2/geoBoundaries-CIV-ADM2.geojson) |
| Bari (`framework:province:bari:eaca0bbaf68b`) | merge: Bari | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/SOM/ADM1/geoBoundaries-SOM-ADM1.geojson) |
| Birni-N'Konni (`framework:province:birni-n-konni:88142df38f54`) | merge: Birni-N'Konni | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/NER/ADM2/geoBoundaries-NER-ADM2.geojson) |
| Caprivi (`framework:province:caprivi:f7c2d35dd30e`) | merge: Caprivi | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/NAM/ADM1/geoBoundaries-NAM-ADM1.geojson) |
| El Tarf (`framework:province:el-tarf:e7f50a1625a4`) | merge: El Tarf | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/DZA/ADM1/geoBoundaries-DZA-ADM1.geojson) |
| Hhohho (`framework:province:hhohho:1e3d7f6cfbbc`) | merge: Hhohho | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/SWZ/ADM1/geoBoundaries-SWZ-ADM1.geojson) |
| Litoral Province (`framework:province:litoral-province:7fc24808332a`) | merge: Litoral Province | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/GNQ/ADM1/geoBoundaries-GNQ-ADM1.geojson) |
| Nugaal (`framework:province:nugaal:5a723287b34e`) | merge: Nugaal | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/SOM/ADM1/geoBoundaries-SOM-ADM1.geojson) |
| Ouango (`framework:province:ouango:bfe2950c116b`) | merge: Ouango | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/CAF/ADM2/geoBoundaries-CAF-ADM2.geojson) |
| Plateaux Region (`framework:province:plateaux-region:8b71f147e2fe`) | merge: Plateaux Region | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/TGO/ADM1/geoBoundaries-TGO-ADM1.geojson) |
| Red Sea Governorate (`framework:province:red-sea-governorate:b94760568fe1`) | merge: Red Sea Governorate | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/EGY/ADM1/geoBoundaries-EGY-ADM1.geojson) |
| RegiÃ£o AutÃ³noma da Madeira (`framework:province:regiao-auta3noma-da-madeira:7038cd7bbc12`) | rename: Região Autónoma da Madeira | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/PRT/ADM1/geoBoundaries-PRT-ADM1.geojson) |
| RegiÃ£o AutÃ³noma dos AÃ§ores (`framework:province:regiao-auta3noma-dos-aaores:5bda02b962fe`) | rename: Região Autónoma dos Açores | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/PRT/ADM1/geoBoundaries-PRT-ADM1.geojson) |
| Sanaag (`framework:province:sanaag:0b900fac3c37`) | merge: Sanaag | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/SOM/ADM1/geoBoundaries-SOM-ADM1.geojson) |
| Sisonke (`framework:province:sisonke:68fd575d9434`) | merge: Sisonke | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/ZAF/ADM2/geoBoundaries-ZAF-ADM2.geojson) |
| Sool (`framework:province:sool:54a234d32b4f`) | merge: Sool | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/SOM/ADM1/geoBoundaries-SOM-ADM1.geojson) |
| Soroti (`framework:province:soroti:8a155dcc42ea`) | merge: Soroti | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/UGA/ADM2/geoBoundaries-UGA-ADM2.geojson) |
| Tonkpi (`framework:province:tonkpi:21c5d681b3ca`) | merge: Tonkpi | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/CIV/ADM2/geoBoundaries-CIV-ADM2.geojson) |
| Upper East Region (`framework:province:upper-east-region:4997e1981640`) | merge: Upper East Region | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/GHA/ADM1/geoBoundaries-GHA-ADM1.geojson) |
| Woqooyi Galbeed (`framework:province:woqooyi-galbeed:24c406b607ec`) | merge: Woqooyi Galbeed | [inspected source](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/SOM/ADM1/geoBoundaries-SOM-ADM1.geojson) |

Merged source-parent identities do not merge locations or political owners. Old group identities must remain archived; their current children move to the same named source parent. The unused Northern Provinces botanical fragment becomes empty after its Hhohho child consolidates with the existing Eswatini Hhohho source group.

## Country and territory matrix

Every represented territory appears here, including cross-continent owners whose African island territories belong to this branch. “Open” is deliberate: direct source matching cannot alone settle city aggregation, rural local purpose or current administrative reform.

| Territory | Locations | Inspected local roles | Source vintages | Weak/unmeasured parent matches | Major source-area reductions |
| --- | ---: | --- | --- | ---: | ---: |
| Algeria | 1566 | Commune: 1566 | 2020 | 271 | 1 |
| Angola | 161 | Municipality: 161 | 2018 | 11 | 0 |
| Benin | 77 | Commune: 77 | 2007 | 52 | 0 |
| Bir Tawil | 1 | Unspecified: 1 | Undated modern reference | 1 | 0 |
| Botswana | 35 | Subdistrict: 35 | 2015 | 3 | 0 |
| British Indian Ocean Territory | 1 | Unspecified: 1 | Undated modern reference | 1 | 0 |
| Burkina Faso | 351 | Named local administrative territory: 351 | 2007 | 0 | 0 |
| Burundi | 119 | Commune: 119 | 2007 | 18 | 0 |
| Cabo Verde | 22 | Named local administrative territory: 22 | 2017 | 14 | 0 |
| Cameroon | 360 | Named local administrative territory: 360 | 2017 | 201 | 0 |
| Central African Republic | 175 | Commune: 175 | 2018 | 76 | 0 |
| Chad | 81 | Departments: 81 | 2019 | 12 | 0 |
| Comoros | 1 | Unspecified: 1 | Undated modern reference | 1 | 0 |
| Congo | 46 | Named local administrative territory: 46 | 2007 | 12 | 0 |
| Côte d'Ivoire | 510 | Departments: 510 | 2021 | 2 | 0 |
| Democratic Republic of the Congo | 189 | territory, city: 189 | 2019 | 67 | 0 |
| Djibouti | 11 | Districts: 11 | 2020 | 8 | 0 |
| Egypt | 282 | marakiz and aqsam: 280; Unspecified: 2 | 2020, Undated modern reference | 121 | 3 |
| Equatorial Guinea | 28 | District: 28 | 2013 | 21 | 0 |
| Eritrea | 58 | districts: 58 | 2020 | 22 | 0 |
| Eswatini | 53 | Inkhundla: 53 | 2017 | 0 | 0 |
| Ethiopia | 680 | Named local administrative territory: 680 | 2016 | 1 | 0 |
| France | 2 | Overseas department: 2 | Undated modern reference | 2 | 0 |
| French Southern and Antarctic Lands | 1 | Named territory: 1 | Undated modern reference | 1 | 0 |
| Gabon | 49 | Department: 49 | 2018 | 35 | 0 |
| Gambia | 40 | District: 39; Unspecified: 1 | 2020, Undated modern reference | 2 | 0 |
| Ghana | 260 | Districts: 260 | 2019 | 64 | 0 |
| Guinea | 34 | prefecture: 34 | 2017 | 1 | 0 |
| Guinea-Bissau | 39 | Sector: 39 | 2017 | 4 | 0 |
| Kenya | 274 | Sub-Counties: 273; Unspecified: 1 | 2020, Undated modern reference | 53 | 0 |
| Lesotho | 10 | District: 10 | 2017 | 0 | 0 |
| Liberia | 136 | District: 136 | 2021 | 3 | 0 |
| Libya | 39 | District: 39 | 2021 | 0 | 0 |
| Madagascar | 119 | District: 119 | 2020 | 75 | 0 |
| Malawi | 28 | district: 28 | 2020 | 2 | 0 |
| Mali | 56 | Cercle: 56 | 2017 | 0 | 0 |
| Mauritania | 69 | Mauritania: 69 | 2020 | 20 | 0 |
| Mauritius | 13 | Dependency: 1; Districts and Outer Islands of Mauritius: 12 | 2017, Undated modern reference | 6 | 1 |
| Morocco | 77 | Province / prefecture: 77 | 2017 | 0 | 0 |
| Mozambique | 159 | districts: 159 | 2019 | 19 | 1 |
| Namibia | 111 | Local constituency territory: 111 | 2007 | 26 | 1 |
| Niger | 271 | Communes: 270; Unspecified: 1 | 2012, Undated modern reference | 166 | 0 |
| Nigeria | 774 | Local Government Areas: 774 | 2022 | 0 | 0 |
| Norway | 1 | Named territory: 1 | Undated modern reference | 1 | 0 |
| Portugal | 30 | Municipality: 30 | 2020 | 21 | 0 |
| Rwanda | 28 | District: 28 | 2012 | 0 | 0 |
| Saint Helena | 3 | Unspecified: 3 | Undated modern reference | 3 | 0 |
| Sao Tome and Principe | 2 | Named local administrative territory: 2 | 2017 | 1 | 0 |
| Senegal | 45 | department: 45 | 2019 | 1 | 0 |
| Seychelles | 8 | Regions: 8 | 2020 | 7 | 0 |
| Sierra Leone | 14 | Districts: 14 | 2017 | 1 | 0 |
| Somalia | 108 | Districts: 108 | 2022 | 44 | 10 |
| Somaliland | 22 | Districts: 22 | Undated modern reference | 22 | 0 |
| South Africa | 213 | Local municipality: 213 | 2020 | 0 | 0 |
| South Sudan | 80 | counties: 80 | 2020 | 0 | 0 |
| Spain | 12 | MUNICIPIOS: 4; Unspecified: 8 | 2018, Undated modern reference | 3 | 0 |
| Sudan | 196 | District: 196 | 2020 | 0 | 0 |
| Togo | 37 | Prefectures: 37 | 2017 | 7 | 0 |
| Tunisia | 264 | Delegation: 264 | 2017 | 25 | 1 |
| Uganda | 137 | District: 137 | 2020 | 131 | 0 |
| United Republic of Tanzania | 170 | Districts: 170 | 2021 | 78 | 0 |
| Western Sahara | 5 | Province / prefecture: 5 | Undated modern reference | 5 | 0 |
| Yemen | 2 | Districts: 2 | 2021 | 2 | 0 |
| Zambia | 116 | Districts: 116 | 2020 | 0 | 0 |
| Zimbabwe | 88 | District: 87; Unspecified: 1 | 2020, Undated modern reference | 0 | 1 |

## Region-by-region unresolved work

| Region | Areas / provinces / locations | Specific next work |
| --- | --- | --- |
| East Tropical Africa | 3 / 209 / 581 | Compare all Kenya county/subcounty, Tanzania district and Uganda district/subcounty roles and source vintages against current official census/gazette sources. Retain full rural coverage while clustering functional/local provinces; blocked Kenya/Uganda primary pages leave confirmation open, not source-approved. |
| Macaronesia | 4 / 26 / 62 | Document a continent convention for Azores/Madeira/Canary/Cape Verde instead of treating botanical African grouping as a universally accepted physical continent boundary. Inspect island-specific province footprints and small coastal city wards independently; political Portugal/Spain ownership never decides region membership. |
| Middle Atlantic Ocean | 2 / 2 / 2 | Government evidence supports separate Ascension island administration within one Overseas Territory; retain separate land territory and geographic parent. Require documented exception for repeated St Helena/Ascension single-member tiers and dated settlement/habitation sources; source institutional homepage does not prove historical rank. |
| Northeast Tropical Africa | 8 / 164 / 1239 | Audit the original SOM district footprint versus earlier Natural Earth country/Somaliland clipping across the entire profile, not only Borama: original Borama 1575.075km² versus current 1.238km². Explain Sudan grouping/South Sudan membership and repeated Somalia area IDs; retain country-independent macro geography and distinguish state/district roles. |
| Northern Africa | 10 / 142 / 2235 | Reconcile duplicate-name Algeria and Morocco area branches with sourced geographic distinctions; unique IDs alone do not make duplicate-purpose groupings meaningful. Review El Magharia and Egypt urban qism/port district roles with complete sourced city memberships before grouping; finer pixels alone does not repair clipped source footprints. |
| South Atlantic Islands | 2 / 2 / 2 | Document Bouvet/Tristan da Cunha geographic convention and full member islands; Norwegian/UK affiliation is separate from continent. Whole-island repeated area/province/location footprints may be justified sparse-territory exceptions, but require explicit purpose and approved source geometry. |
| South Tropical Africa | 6 / 53 / 549 | Review every district/municipality/province role across Mozambique/Malawi/Zambia/Zimbabwe/Angola; Angola source revision has provenance but regional grouping remains open. Explain duplicate Mozambique area IDs with actual physical/admin-purpose distinctions; investigate Mvurwi tiny retained footprint against source municipal territory. |
| Southern Africa | 15 / 97 / 421 | Audit/replace NAM source profile at source-feature level before pixel fixes: five source-labelled constituency polygons are tiny/southerly, and current source ages 2007. Compare NSA NSDI/census and Stanford original geometry/attribute joins. Review Caprivi Strip, Northern Provinces and Swaziland legacy labels and actual member territories; modern UNM 49 uses Eswatini. Existing South Africa provincial areas need district/local-purpose checks. |
| West Tropical Africa | 15 / 300 / 2713 | Check every botanical-country area against municipal/district/regional source roles and vintage; national statistical pages offer censuses but do not by themselves validate geometry. Prioritize Nigeria/Ghana multi-province grouping purpose and coastal/island omissions, retaining administrative rural territory rather than only urban municipality coverage. |
| West-Central Tropical Africa | 10 / 215 / 1000 | Replace the undated area display label Zaïre with a documented contemporary geographic reference or explicitly label its legacy interval; retain its stable ID and dated evidence. UNM 49 names Democratic Republic of the Congo. Check whole-country botanical areas with many administrative provinces against sourced basin/highland/administrative clusters; do not certify density from ADM numbers. |
| Western Indian Ocean | 9 / 48 / 145 | Verify all Indian Ocean island land footprints and political claims separately; St Brandon source/current area differences require coastal/source mask review. Separate TAAF Eparses administrative affiliation from Mozambique Channel physical grouping; Chagos archipelago scope/country ownership requires dated evidence, not modern page backfill. |

## Source and geometry defects that remain open

- Somalia/Somaliland source-mask losses are global within that profile, not a Borama-only issue: BADHAN, BERBERA, BORAMA, ERIGAVO, LAS ANOD, ZEILA, BUHODLE and BURAO each retain less than 10% of their original pinned source polygon. Their exact IDs/ratios are recorded. Geography/source repairs require source-wide conflict resolution and archive crosswalks, independent of political recognition.
- Ten tiny Namibia source-labelled constituencies are suspicious. Some wrong labels sit within their wrongly assigned parent at 100% overlap: parent containment cannot certify a correct geometry/attribute join. The entire 2007 profile stays open, with the Stanford/NSA Public Domain source identified. No arbitrary pixel reassignment or invented constituency footprint is proposed.
- El Marsa, Algeria retains approximately 6.15% of its original 3.03 km² source polygon. Check coastal/water content and source masks before repair.
- Whole-island Réunion, Mayotte, Comoros, Seychelles regions, Lesotho/Libya ADM1 locals, physical RESOLVE adaptations and city aggregates require independent local-purpose/granularity review. They are not approved by a structural pass.
- Macaronesia, Socotra and remote Atlantic/Indian Ocean islands require explicit continent conventions; national ownership does not define their geography.
- Legacy botanical labels and lossless mojibake display corrections preserve IDs. Historical names and rename dates require separate temporal evidence.

## Completion boundary

The machine-readable file gives every group a concrete retain, merge, rename or open decision and every location an exact open review entry. Dated named administrative clusters can have supported reference footprints while descendants remain open. **The Africa branch is not declared globally semantically complete.** No claim of child completion is inherited from a parent, a source level or a valid polygon.

[Machine-readable decisions](../../data/geographic-decisions/africa.json)

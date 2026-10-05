# Texas geography research findings — issue #431

**Research date:** 2026-10-05 (America/Los_Angeles). **Mode:** source/semantic evidence only. **Issue scope:** exact 254 Texas member IDs in the preserved v5 workload snapshot. **Evaluated against:** fresh main commit `4877ef4e99528615daf657a376b7605d1657f817`, current release v6. The issue’s v5 release pins remain intact; this comparison does not repin or certify them.

## Findings and classification

All 254 exact IDs match one GeoBoundaries `USA/ADM2` source feature by original `shapeID`, with unique joins to the 2018 and 2025 U.S. Census county tables by 2018 county name and 2025 county GEOID. All are named Texas counties, have source role `Counties`, source vintage 2018, declared Public Domain license, ADM2 level, and the same current Texas parent. Census 2018 marks all 254 as functioning counties (`FUNCSTAT=A`). No subject is correction-needed from this evidence. Classifications are **230 justified** for source identity, tier, and parent, and **24 insufficient-evidence** for county geometry because the comparisons show unresolved differences. “Justified” does not mean legally surveyed, complete to every island/shoreline, or region-certified.

### Authoritative meaning and source suitability

- The [U.S. Census Texas government guide](https://www2.census.gov/geo/pdfs/reference/guidestloc/All_GSLCG.pdf) says Texas has 254 counties and distinguishes county governments from county subdivisions; the [Texas Government counties portal](https://www.texas.gov/local-government-resources/) also reports 254. The Texas Constitution, Article V §18, describes county commissioners courts and precincts, supporting the administrative meaning of county in Texas. Census 2018 and 2025 TIGER county layer metadata independently label the queried feature class “Counties (or statistically equivalent entities).” Together, this supports counties as an appropriate named ADM2 tier for these entities; source level code alone was not used as the justification.
- The pinned GeoBoundaries metadata identifies the 2018 source as U.S. Census Bureau MAF/TIGER, canonical type “Counties,” Public Domain, and links its licensing provenance to the Census [2018 Cartographic Boundary File page](https://www.census.gov/geographies/mapping-files/2018/geo/carto-boundary-file.html). That official page lists `cb_2018_us_county_500k.zip` as the nationwide county file at 1:500,000 scale (11 MB). This is the same-purpose generalized comparator; detailed TIGER/Line is a separate representation and vintage comparator.
- Census explains that TIGER county boundaries support statistical collection and tabulation and do not themselves determine jurisdictional authority. The [2018 TIGER/Line technical documentation](https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2018/TGRSHP2018_TechDoc.pdf) documents its Jan. 1, 2018 vintage. The [2025 TIGER/Line release page](https://www.census.gov/geographies/mapping-files/2025/geo/tiger-line-file.html) documents a Jan. 1, 2025 vintage and 2025 release. These Census products are authoritative statistical comparators, not legal boundary determinations.
- The U.S. Census Bureau defines the West South Central Division as Arkansas, Louisiana, Oklahoma, and Texas in its [regions and divisions reference map](https://www2.census.gov/geo/pdfs/maps-data/maps/reference/us_regdiv.pdf). On current main, the 470 member IDs of that division partition exactly into the 254 Texas members of #431 and the 216 Arkansas/Louisiana/Oklahoma members of sibling packet #432, with zero overlap. Current parent counts are Arkansas 75, Louisiana 64, Oklahoma 77, and Texas 254. All 470 current children are named `gb:USA:ADM2` units with source role Counties, vintage 2018, Public Domain license, ADM2 level and ADM1 source parent. This validates neighboring granularity only; combined division geometry/acceptance belongs to integration work.

## Geometry and completeness review

Reproduction transforms WGS84 longitude/latitude to EPSG:6933 with `always_xy=True`, then calculates equal-area IoU. The 0.98 screen is only a reproducible triage trigger. It neither proves an error nor establishes a legal boundary. Source-to-Atlas v6 IoU has a minimum 0.985990 and median 0.999008, so none trigger the screen. Against 2018/2025 Census TIGER, 23 counties trigger it; against the same-purpose 2018 1:500,000 Census Cartographic Boundary File, 20 trigger it. The 2018 and 2025 TIGER versions are near-identical for this roster (median IoU 0.999999998; no screen triggers). A separate component check found Brewster County has one Polygon in the pinned source but two Atlas components. Thus 23 numeric signals plus the Brewster topology mismatch produce 24 county assessments classified insufficient-evidence until the differences are documented or authoritative local evidence resolves them. No unsupported correction is proposed.

The named large comparison signals are coastal counties (including Aransas, Galveston, Cameron, Kenedy, Chambers, Kleberg, Willacy, Nueces, Brazoria, Jefferson, Matagorda and Calhoun) and interior counties (including Refugio, Bowie, Delta, Red River, San Patricio, Brazos, Waller, Camp, Newton, Jasper and Washington). For several coast counties, Atlas-to-detailed-TIGER IoU is low while Atlas-to-2018-CBF IoU is materially higher; this is consistent with a representation/generalization or water treatment difference but does not prove its cause. Census `ALAND`/`AWATER` attributes are retained for context, not treated as the legal land/water boundary.

GeoBoundaries source geometry has 246 Polygon and 8 MultiPolygon records in Texas; current Atlas has 245 Polygon and 9 MultiPolygon, while Census county API features and CBF rows each resolve to one polygon per county. Brewster is the ninth Atlas multipart: the pinned source is a Polygon and current Atlas is a MultiPolygon (2 components), although its IoU is above the numeric screen. The reason is not established. The other eight source/Atlas multipart counties are coastal counties with water/island comparison limits. Multipart features require careful shoreline/island handling. The current evidence does not establish that every offshore island, tidal feature, or jurisdictional water boundary is complete. No individual island omission is asserted. All 254 county names are present in the 2018 Census Texas query and 2025 Census Texas query; both have 254 unique county GEOIDs. The nationwide pinned GeoBoundaries ADM2 artifact contains 3,233 features, with the metadata reporting the same national administrative-unit count.

## County-by-county classification

| County | Atlas ID | 2018 GEOID | Class | Unresolved comparison signal |
|---|---|---:|---|---|
| Panola | `gb:USA:ADM2:52423323B10240344188589` | `48365` | justified | No IoU or source/Atlas component-count trigger |
| Fayette | `gb:USA:ADM2:52423323B10356189909314` | `48149` | justified | No IoU or source/Atlas component-count trigger |
| Collin | `gb:USA:ADM2:52423323B10774992912194` | `48085` | justified | No IoU or source/Atlas component-count trigger |
| Mason | `gb:USA:ADM2:52423323B11317235464600` | `48319` | justified | No IoU or source/Atlas component-count trigger |
| Collingsworth | `gb:USA:ADM2:52423323B11356717138354` | `48087` | justified | No IoU or source/Atlas component-count trigger |
| Lee | `gb:USA:ADM2:52423323B12429161322070` | `48287` | justified | No IoU or source/Atlas component-count trigger |
| Hopkins | `gb:USA:ADM2:52423323B1297205264682` | `48223` | justified | No IoU or source/Atlas component-count trigger |
| Culberson | `gb:USA:ADM2:52423323B13187380615958` | `48109` | justified | No IoU or source/Atlas component-count trigger |
| Cherokee | `gb:USA:ADM2:52423323B13396294206268` | `48073` | justified | No IoU or source/Atlas component-count trigger |
| Karnes | `gb:USA:ADM2:52423323B141370106049` | `48255` | justified | No IoU or source/Atlas component-count trigger |
| Kinney | `gb:USA:ADM2:52423323B1423896904617` | `48271` | justified | No IoU or source/Atlas component-count trigger |
| Wilson | `gb:USA:ADM2:52423323B14345052331851` | `48493` | justified | No IoU or source/Atlas component-count trigger |
| Milam | `gb:USA:ADM2:52423323B14814081114413` | `48331` | justified | No IoU or source/Atlas component-count trigger |
| Jasper | `gb:USA:ADM2:52423323B15193843372165` | `48241` | insufficient-evidence | atlas_v6_to_2018_cbf=0.979411; atlas_v6_to_2018_census=0.979138; atlas_v6_to_2025_census=0.979138 |
| Reeves | `gb:USA:ADM2:52423323B15445354954685` | `48389` | justified | No IoU or source/Atlas component-count trigger |
| Zavala | `gb:USA:ADM2:52423323B15496967187618` | `48507` | justified | No IoU or source/Atlas component-count trigger |
| Newton | `gb:USA:ADM2:52423323B15615503962810` | `48351` | insufficient-evidence | atlas_v6_to_2018_cbf=0.978441; atlas_v6_to_2018_census=0.977495; atlas_v6_to_2025_census=0.977495 |
| Washington | `gb:USA:ADM2:52423323B15750525116760` | `48477` | insufficient-evidence | atlas_v6_to_2018_cbf=0.979522; atlas_v6_to_2018_census=0.979351; atlas_v6_to_2025_census=0.979351 |
| Guadalupe | `gb:USA:ADM2:52423323B15867360599504` | `48187` | justified | No IoU or source/Atlas component-count trigger |
| Madison | `gb:USA:ADM2:52423323B16147855559492` | `48313` | justified | No IoU or source/Atlas component-count trigger |
| Marion | `gb:USA:ADM2:52423323B1637569116072` | `48315` | justified | No IoU or source/Atlas component-count trigger |
| Gonzales | `gb:USA:ADM2:52423323B16861027908547` | `48177` | justified | No IoU or source/Atlas component-count trigger |
| King | `gb:USA:ADM2:52423323B16867264390271` | `48269` | justified | No IoU or source/Atlas component-count trigger |
| Moore | `gb:USA:ADM2:52423323B17136176847480` | `48341` | justified | No IoU or source/Atlas component-count trigger |
| Franklin | `gb:USA:ADM2:52423323B17137134235452` | `48159` | justified | No IoU or source/Atlas component-count trigger |
| Blanco | `gb:USA:ADM2:52423323B17591428926756` | `48031` | justified | No IoU or source/Atlas component-count trigger |
| Schleicher | `gb:USA:ADM2:52423323B17811041209466` | `48413` | justified | No IoU or source/Atlas component-count trigger |
| Hidalgo | `gb:USA:ADM2:52423323B17892136313191` | `48215` | justified | No IoU or source/Atlas component-count trigger |
| McCulloch | `gb:USA:ADM2:52423323B18546494380839` | `48307` | justified | No IoU or source/Atlas component-count trigger |
| Refugio | `gb:USA:ADM2:52423323B18578133959698` | `48391` | insufficient-evidence | atlas_v6_to_2018_cbf=0.966219; atlas_v6_to_2018_census=0.965649; atlas_v6_to_2025_census=0.965649; source_to_2018_cbf=0.971389; source_to_2018_census=0.970346 |
| Somervell | `gb:USA:ADM2:52423323B18632711548456` | `48425` | justified | No IoU or source/Atlas component-count trigger |
| Brewster | `gb:USA:ADM2:52423323B18775242771825` | `48043` | insufficient-evidence | source→Atlas components 1→2 |
| Hunt | `gb:USA:ADM2:52423323B19009886233189` | `48231` | justified | No IoU or source/Atlas component-count trigger |
| Cameron | `gb:USA:ADM2:52423323B19813922549461` | `48061` | insufficient-evidence | atlas_v6_to_2018_cbf=0.967702; atlas_v6_to_2018_census=0.789692; atlas_v6_to_2025_census=0.787557; source_to_2018_cbf=0.966032; source_to_2018_census=0.788221 |
| Garza | `gb:USA:ADM2:52423323B20011668612695` | `48169` | justified | No IoU or source/Atlas component-count trigger |
| Sabine | `gb:USA:ADM2:52423323B20361031483491` | `48403` | justified | No IoU or source/Atlas component-count trigger |
| Coleman | `gb:USA:ADM2:52423323B20578192164801` | `48083` | justified | No IoU or source/Atlas component-count trigger |
| Johnson | `gb:USA:ADM2:52423323B21675904174262` | `48251` | justified | No IoU or source/Atlas component-count trigger |
| Waller | `gb:USA:ADM2:52423323B21823422169347` | `48473` | insufficient-evidence | atlas_v6_to_2018_cbf=0.977859; atlas_v6_to_2018_census=0.977588; atlas_v6_to_2025_census=0.977432 |
| Live Oak | `gb:USA:ADM2:52423323B21847190963699` | `48297` | justified | No IoU or source/Atlas component-count trigger |
| Hemphill | `gb:USA:ADM2:52423323B21915580186486` | `48211` | justified | No IoU or source/Atlas component-count trigger |
| San Patricio | `gb:USA:ADM2:52423323B23065911216534` | `48409` | insufficient-evidence | atlas_v6_to_2018_cbf=0.976403; atlas_v6_to_2018_census=0.974683; atlas_v6_to_2025_census=0.974810 |
| Young | `gb:USA:ADM2:52423323B23202152143639` | `48503` | justified | No IoU or source/Atlas component-count trigger |
| Mills | `gb:USA:ADM2:52423323B24678536385719` | `48333` | justified | No IoU or source/Atlas component-count trigger |
| Baylor | `gb:USA:ADM2:52423323B2493878028026` | `48023` | justified | No IoU or source/Atlas component-count trigger |
| Maverick | `gb:USA:ADM2:52423323B24944567676343` | `48323` | justified | No IoU or source/Atlas component-count trigger |
| Cottle | `gb:USA:ADM2:52423323B25180232244393` | `48101` | justified | No IoU or source/Atlas component-count trigger |
| Victoria | `gb:USA:ADM2:52423323B26003221317012` | `48469` | justified | No IoU or source/Atlas component-count trigger |
| Rockwall | `gb:USA:ADM2:52423323B26615713613896` | `48397` | justified | No IoU or source/Atlas component-count trigger |
| Rusk | `gb:USA:ADM2:52423323B2750647625909` | `48401` | justified | No IoU or source/Atlas component-count trigger |
| Bailey | `gb:USA:ADM2:52423323B27652723515833` | `48017` | justified | No IoU or source/Atlas component-count trigger |
| Wharton | `gb:USA:ADM2:52423323B28004932041096` | `48481` | justified | No IoU or source/Atlas component-count trigger |
| Clay | `gb:USA:ADM2:52423323B2844770292718` | `48077` | justified | No IoU or source/Atlas component-count trigger |
| Loving | `gb:USA:ADM2:52423323B28459712837049` | `48301` | justified | No IoU or source/Atlas component-count trigger |
| Lamar | `gb:USA:ADM2:52423323B29010460164460` | `48277` | justified | No IoU or source/Atlas component-count trigger |
| Jim Wells | `gb:USA:ADM2:52423323B29014105242179` | `48249` | justified | No IoU or source/Atlas component-count trigger |
| Oldham | `gb:USA:ADM2:52423323B29026545860806` | `48359` | justified | No IoU or source/Atlas component-count trigger |
| Denton | `gb:USA:ADM2:52423323B29429067330401` | `48121` | justified | No IoU or source/Atlas component-count trigger |
| Kenedy | `gb:USA:ADM2:52423323B29588841600752` | `48261` | insufficient-evidence | atlas_v6_to_2018_cbf=0.978920; atlas_v6_to_2018_census=0.801752; atlas_v6_to_2025_census=0.801752; source_to_2018_cbf=0.979683; source_to_2018_census=0.801716 |
| Orange | `gb:USA:ADM2:52423323B30055377123023` | `48361` | justified | No IoU or source/Atlas component-count trigger |
| Bexar | `gb:USA:ADM2:52423323B3019751705730` | `48029` | justified | No IoU or source/Atlas component-count trigger |
| Leon | `gb:USA:ADM2:52423323B32398895201359` | `48289` | justified | No IoU or source/Atlas component-count trigger |
| Kerr | `gb:USA:ADM2:52423323B33444382210707` | `48265` | justified | No IoU or source/Atlas component-count trigger |
| Terry | `gb:USA:ADM2:52423323B33800517044511` | `48445` | justified | No IoU or source/Atlas component-count trigger |
| Llano | `gb:USA:ADM2:52423323B33925670758301` | `48299` | justified | No IoU or source/Atlas component-count trigger |
| Midland | `gb:USA:ADM2:52423323B34026516853793` | `48329` | justified | No IoU or source/Atlas component-count trigger |
| Comal | `gb:USA:ADM2:52423323B34146067891906` | `48091` | justified | No IoU or source/Atlas component-count trigger |
| Starr | `gb:USA:ADM2:52423323B3441852728971` | `48427` | justified | No IoU or source/Atlas component-count trigger |
| Winkler | `gb:USA:ADM2:52423323B34965640211434` | `48495` | justified | No IoU or source/Atlas component-count trigger |
| Dallas | `gb:USA:ADM2:52423323B35177303918175` | `48113` | justified | No IoU or source/Atlas component-count trigger |
| Red River | `gb:USA:ADM2:52423323B35361747398086` | `48387` | insufficient-evidence | atlas_v6_to_2018_cbf=0.975871; atlas_v6_to_2018_census=0.975326; atlas_v6_to_2025_census=0.975326; source_to_2018_cbf=0.979966; source_to_2018_census=0.979424 |
| Bowie | `gb:USA:ADM2:52423323B35633344294937` | `48037` | insufficient-evidence | atlas_v6_to_2018_cbf=0.966624; atlas_v6_to_2018_census=0.966242; atlas_v6_to_2025_census=0.966196; source_to_2018_cbf=0.969836; source_to_2018_census=0.969228 |
| Cochran | `gb:USA:ADM2:52423323B36453728926515` | `48079` | justified | No IoU or source/Atlas component-count trigger |
| Nolan | `gb:USA:ADM2:52423323B36812497972126` | `48353` | justified | No IoU or source/Atlas component-count trigger |
| Shackelford | `gb:USA:ADM2:52423323B36829987013590` | `48417` | justified | No IoU or source/Atlas component-count trigger |
| Hutchinson | `gb:USA:ADM2:52423323B37064870430206` | `48233` | justified | No IoU or source/Atlas component-count trigger |
| Uvalde | `gb:USA:ADM2:52423323B37617394138403` | `48463` | justified | No IoU or source/Atlas component-count trigger |
| Bell | `gb:USA:ADM2:52423323B38294551325831` | `48027` | justified | No IoU or source/Atlas component-count trigger |
| Wise | `gb:USA:ADM2:52423323B38394143035791` | `48497` | justified | No IoU or source/Atlas component-count trigger |
| Jim Hogg | `gb:USA:ADM2:52423323B38410477009705` | `48247` | justified | No IoU or source/Atlas component-count trigger |
| Ochiltree | `gb:USA:ADM2:52423323B38476522601311` | `48357` | justified | No IoU or source/Atlas component-count trigger |
| Duval | `gb:USA:ADM2:52423323B38482742195031` | `48131` | justified | No IoU or source/Atlas component-count trigger |
| Deaf Smith | `gb:USA:ADM2:52423323B38670867283875` | `48117` | justified | No IoU or source/Atlas component-count trigger |
| Zapata | `gb:USA:ADM2:52423323B38699112518848` | `48505` | justified | No IoU or source/Atlas component-count trigger |
| Chambers | `gb:USA:ADM2:52423323B38827881811881` | `48071` | insufficient-evidence | atlas_v6_to_2018_cbf=0.971063; atlas_v6_to_2018_census=0.719751; atlas_v6_to_2025_census=0.719793; source_to_2018_cbf=0.977061; source_to_2018_census=0.723514 |
| Nacogdoches | `gb:USA:ADM2:52423323B39218063073671` | `48347` | justified | No IoU or source/Atlas component-count trigger |
| Travis | `gb:USA:ADM2:52423323B39349585413380` | `48453` | justified | No IoU or source/Atlas component-count trigger |
| Hudspeth | `gb:USA:ADM2:52423323B39607492205238` | `48229` | justified | No IoU or source/Atlas component-count trigger |
| Upton | `gb:USA:ADM2:52423323B39686210449423` | `48461` | justified | No IoU or source/Atlas component-count trigger |
| Hays | `gb:USA:ADM2:52423323B40062002431262` | `48209` | justified | No IoU or source/Atlas component-count trigger |
| Williamson | `gb:USA:ADM2:52423323B40503008253426` | `48491` | justified | No IoU or source/Atlas component-count trigger |
| Lipscomb | `gb:USA:ADM2:52423323B40527291934066` | `48295` | justified | No IoU or source/Atlas component-count trigger |
| Burnet | `gb:USA:ADM2:52423323B41129730997096` | `48053` | justified | No IoU or source/Atlas component-count trigger |
| Wheeler | `gb:USA:ADM2:52423323B41320659077500` | `48483` | justified | No IoU or source/Atlas component-count trigger |
| Fort Bend | `gb:USA:ADM2:52423323B41825478999592` | `48157` | justified | No IoU or source/Atlas component-count trigger |
| Val Verde | `gb:USA:ADM2:52423323B42666839171000` | `48465` | justified | No IoU or source/Atlas component-count trigger |
| Gaines | `gb:USA:ADM2:52423323B42726904643682` | `48165` | justified | No IoU or source/Atlas component-count trigger |
| Brazos | `gb:USA:ADM2:52423323B4274675521661` | `48041` | insufficient-evidence | atlas_v6_to_2018_cbf=0.977325; atlas_v6_to_2018_census=0.976816; atlas_v6_to_2025_census=0.976816 |
| Briscoe | `gb:USA:ADM2:52423323B43262131750605` | `48045` | justified | No IoU or source/Atlas component-count trigger |
| Lavaca | `gb:USA:ADM2:52423323B4330471688052` | `48285` | justified | No IoU or source/Atlas component-count trigger |
| San Saba | `gb:USA:ADM2:52423323B43547858448152` | `48411` | justified | No IoU or source/Atlas component-count trigger |
| Roberts | `gb:USA:ADM2:52423323B43933736406095` | `48393` | justified | No IoU or source/Atlas component-count trigger |
| Cass | `gb:USA:ADM2:52423323B4448800346359` | `48067` | justified | No IoU or source/Atlas component-count trigger |
| Howard | `gb:USA:ADM2:52423323B44641171264537` | `48227` | justified | No IoU or source/Atlas component-count trigger |
| Crane | `gb:USA:ADM2:52423323B45238818245083` | `48103` | justified | No IoU or source/Atlas component-count trigger |
| Hartley | `gb:USA:ADM2:52423323B45324234898268` | `48205` | justified | No IoU or source/Atlas component-count trigger |
| Hood | `gb:USA:ADM2:52423323B45355972710900` | `48221` | justified | No IoU or source/Atlas component-count trigger |
| Kendall | `gb:USA:ADM2:52423323B46155834246828` | `48259` | justified | No IoU or source/Atlas component-count trigger |
| Houston | `gb:USA:ADM2:52423323B46548202222593` | `48225` | justified | No IoU or source/Atlas component-count trigger |
| Martin | `gb:USA:ADM2:52423323B4659936825166` | `48317` | justified | No IoU or source/Atlas component-count trigger |
| Stonewall | `gb:USA:ADM2:52423323B46618187662485` | `48433` | justified | No IoU or source/Atlas component-count trigger |
| Jeff Davis | `gb:USA:ADM2:52423323B47004263581076` | `48243` | justified | No IoU or source/Atlas component-count trigger |
| Kleberg | `gb:USA:ADM2:52423323B47433581718173` | `48273` | insufficient-evidence | atlas_v6_to_2018_cbf=0.968670; atlas_v6_to_2018_census=0.849596; atlas_v6_to_2025_census=0.849596; source_to_2018_cbf=0.970347; source_to_2018_census=0.850426 |
| Shelby | `gb:USA:ADM2:52423323B47536211032207` | `48419` | justified | No IoU or source/Atlas component-count trigger |
| Hockley | `gb:USA:ADM2:52423323B48286910012363` | `48219` | justified | No IoU or source/Atlas component-count trigger |
| Crosby | `gb:USA:ADM2:52423323B48575431157789` | `48107` | justified | No IoU or source/Atlas component-count trigger |
| Limestone | `gb:USA:ADM2:52423323B48911079087514` | `48293` | justified | No IoU or source/Atlas component-count trigger |
| Freestone | `gb:USA:ADM2:52423323B49293454061444` | `48161` | justified | No IoU or source/Atlas component-count trigger |
| Bastrop | `gb:USA:ADM2:52423323B49733018646154` | `48021` | justified | No IoU or source/Atlas component-count trigger |
| Gillespie | `gb:USA:ADM2:52423323B49995715327400` | `48171` | justified | No IoU or source/Atlas component-count trigger |
| Hill | `gb:USA:ADM2:52423323B5018647072048` | `48217` | justified | No IoU or source/Atlas component-count trigger |
| Medina | `gb:USA:ADM2:52423323B50387422534954` | `48325` | justified | No IoU or source/Atlas component-count trigger |
| Ector | `gb:USA:ADM2:52423323B50517740835867` | `48135` | justified | No IoU or source/Atlas component-count trigger |
| Swisher | `gb:USA:ADM2:52423323B50579359224447` | `48437` | justified | No IoU or source/Atlas component-count trigger |
| Atascosa | `gb:USA:ADM2:52423323B50957806098426` | `48013` | justified | No IoU or source/Atlas component-count trigger |
| Fisher | `gb:USA:ADM2:52423323B51130731271508` | `48151` | justified | No IoU or source/Atlas component-count trigger |
| Bosque | `gb:USA:ADM2:52423323B51528806968962` | `48035` | justified | No IoU or source/Atlas component-count trigger |
| Sherman | `gb:USA:ADM2:52423323B51722927782830` | `48421` | justified | No IoU or source/Atlas component-count trigger |
| Cooke | `gb:USA:ADM2:52423323B51849349717412` | `48097` | justified | No IoU or source/Atlas component-count trigger |
| Rains | `gb:USA:ADM2:52423323B52067062833636` | `48379` | justified | No IoU or source/Atlas component-count trigger |
| Sutton | `gb:USA:ADM2:52423323B52490011896417` | `48435` | justified | No IoU or source/Atlas component-count trigger |
| Real | `gb:USA:ADM2:52423323B52683952870677` | `48385` | justified | No IoU or source/Atlas component-count trigger |
| Brazoria | `gb:USA:ADM2:52423323B52788200523187` | `48039` | insufficient-evidence | atlas_v6_to_2018_census=0.904285; atlas_v6_to_2025_census=0.904307; source_to_2018_census=0.905724 |
| Wichita | `gb:USA:ADM2:52423323B53531362245787` | `48485` | justified | No IoU or source/Atlas component-count trigger |
| El Paso | `gb:USA:ADM2:52423323B54521825371801` | `48141` | justified | No IoU or source/Atlas component-count trigger |
| Irion | `gb:USA:ADM2:52423323B54674882577965` | `48235` | justified | No IoU or source/Atlas component-count trigger |
| Coke | `gb:USA:ADM2:52423323B55584027344898` | `48081` | justified | No IoU or source/Atlas component-count trigger |
| Falls | `gb:USA:ADM2:52423323B55743875979164` | `48145` | justified | No IoU or source/Atlas component-count trigger |
| Willacy | `gb:USA:ADM2:52423323B56216373700802` | `48489` | insufficient-evidence | atlas_v6_to_2018_cbf=0.978829; atlas_v6_to_2018_census=0.812909; atlas_v6_to_2025_census=0.812527; source_to_2018_cbf=0.979301; source_to_2018_census=0.812775 |
| Hall | `gb:USA:ADM2:52423323B5625612438776` | `48191` | justified | No IoU or source/Atlas component-count trigger |
| McLennan | `gb:USA:ADM2:52423323B56606150013880` | `48309` | justified | No IoU or source/Atlas component-count trigger |
| Galveston | `gb:USA:ADM2:52423323B5668037178714` | `48167` | insufficient-evidence | atlas_v6_to_2018_cbf=0.925873; atlas_v6_to_2018_census=0.493609; atlas_v6_to_2025_census=0.493745; source_to_2018_cbf=0.931783; source_to_2018_census=0.493828 |
| Menard | `gb:USA:ADM2:52423323B56824601140740` | `48327` | justified | No IoU or source/Atlas component-count trigger |
| Kaufman | `gb:USA:ADM2:52423323B57409714288179` | `48257` | justified | No IoU or source/Atlas component-count trigger |
| Taylor | `gb:USA:ADM2:52423323B57845343787287` | `48441` | justified | No IoU or source/Atlas component-count trigger |
| Palo Pinto | `gb:USA:ADM2:52423323B58285060103577` | `48363` | justified | No IoU or source/Atlas component-count trigger |
| Hale | `gb:USA:ADM2:52423323B58430787795097` | `48189` | justified | No IoU or source/Atlas component-count trigger |
| Borden | `gb:USA:ADM2:52423323B58948144984010` | `48033` | justified | No IoU or source/Atlas component-count trigger |
| Sterling | `gb:USA:ADM2:52423323B58993545111067` | `48431` | justified | No IoU or source/Atlas component-count trigger |
| Erath | `gb:USA:ADM2:52423323B59070350705897` | `48143` | justified | No IoU or source/Atlas component-count trigger |
| Henderson | `gb:USA:ADM2:52423323B59303088288262` | `48213` | justified | No IoU or source/Atlas component-count trigger |
| Castro | `gb:USA:ADM2:52423323B59330108654898` | `48069` | justified | No IoU or source/Atlas component-count trigger |
| Nueces | `gb:USA:ADM2:52423323B60755765681698` | `48355` | insufficient-evidence | atlas_v6_to_2018_cbf=0.969685; atlas_v6_to_2018_census=0.745365; atlas_v6_to_2025_census=0.745283; source_to_2018_cbf=0.972399; source_to_2018_census=0.747019 |
| Knox | `gb:USA:ADM2:52423323B61031799743155` | `48275` | justified | No IoU or source/Atlas component-count trigger |
| McMullen | `gb:USA:ADM2:52423323B61214192740744` | `48311` | justified | No IoU or source/Atlas component-count trigger |
| Parker | `gb:USA:ADM2:52423323B6127736207828` | `48367` | justified | No IoU or source/Atlas component-count trigger |
| Jefferson | `gb:USA:ADM2:52423323B61382457071366` | `48245` | insufficient-evidence | atlas_v6_to_2018_census=0.879699; atlas_v6_to_2025_census=0.879662; source_to_2018_census=0.881185 |
| Hamilton | `gb:USA:ADM2:52423323B6154390219134` | `48193` | justified | No IoU or source/Atlas component-count trigger |
| Lamb | `gb:USA:ADM2:52423323B61761098121912` | `48279` | justified | No IoU or source/Atlas component-count trigger |
| Wood | `gb:USA:ADM2:52423323B61780035147901` | `48499` | justified | No IoU or source/Atlas component-count trigger |
| Fannin | `gb:USA:ADM2:52423323B62023249377371` | `48147` | justified | No IoU or source/Atlas component-count trigger |
| DeWitt | `gb:USA:ADM2:52423323B62485565379891` | `48123` | justified | No IoU or source/Atlas component-count trigger |
| Armstrong | `gb:USA:ADM2:52423323B62682340625208` | `48011` | justified | No IoU or source/Atlas component-count trigger |
| Kent | `gb:USA:ADM2:52423323B63007180209639` | `48263` | justified | No IoU or source/Atlas component-count trigger |
| Hardeman | `gb:USA:ADM2:52423323B6303249721628` | `48197` | justified | No IoU or source/Atlas component-count trigger |
| Montgomery | `gb:USA:ADM2:52423323B63190785401157` | `48339` | justified | No IoU or source/Atlas component-count trigger |
| Dallam | `gb:USA:ADM2:52423323B63824106950713` | `48111` | justified | No IoU or source/Atlas component-count trigger |
| Liberty | `gb:USA:ADM2:52423323B64688263814776` | `48291` | justified | No IoU or source/Atlas component-count trigger |
| Trinity | `gb:USA:ADM2:52423323B67589001499387` | `48455` | justified | No IoU or source/Atlas component-count trigger |
| La Salle | `gb:USA:ADM2:52423323B67793839713525` | `48283` | justified | No IoU or source/Atlas component-count trigger |
| Dawson | `gb:USA:ADM2:52423323B68149389571600` | `48115` | justified | No IoU or source/Atlas component-count trigger |
| Harris | `gb:USA:ADM2:52423323B68186618035588` | `48201` | justified | No IoU or source/Atlas component-count trigger |
| Titus | `gb:USA:ADM2:52423323B68756889637402` | `48449` | justified | No IoU or source/Atlas component-count trigger |
| Robertson | `gb:USA:ADM2:52423323B69162906436111` | `48395` | justified | No IoU or source/Atlas component-count trigger |
| Ward | `gb:USA:ADM2:52423323B69201645731080` | `48475` | justified | No IoU or source/Atlas component-count trigger |
| Glasscock | `gb:USA:ADM2:52423323B694996530293` | `48173` | justified | No IoU or source/Atlas component-count trigger |
| Throckmorton | `gb:USA:ADM2:52423323B71191132614173` | `48447` | justified | No IoU or source/Atlas component-count trigger |
| Polk | `gb:USA:ADM2:52423323B71522839301040` | `48373` | justified | No IoU or source/Atlas component-count trigger |
| Wilbarger | `gb:USA:ADM2:52423323B71723905303227` | `48487` | justified | No IoU or source/Atlas component-count trigger |
| Calhoun | `gb:USA:ADM2:52423323B71782729975754` | `48057` | insufficient-evidence | atlas_v6_to_2018_cbf=0.968671; atlas_v6_to_2018_census=0.730014; atlas_v6_to_2025_census=0.730014; source_to_2018_cbf=0.970655; source_to_2018_census=0.730284 |
| Jack | `gb:USA:ADM2:52423323B71935080527637` | `48237` | justified | No IoU or source/Atlas component-count trigger |
| Camp | `gb:USA:ADM2:52423323B72263497206932` | `48063` | insufficient-evidence | atlas_v6_to_2018_cbf=0.977998; atlas_v6_to_2018_census=0.977655; atlas_v6_to_2025_census=0.977655; source_to_2018_cbf=0.979621; source_to_2018_census=0.979266 |
| Callahan | `gb:USA:ADM2:52423323B72764612751760` | `48059` | justified | No IoU or source/Atlas component-count trigger |
| Dickens | `gb:USA:ADM2:52423323B72793142672199` | `48125` | justified | No IoU or source/Atlas component-count trigger |
| Yoakum | `gb:USA:ADM2:52423323B73359815084270` | `48501` | justified | No IoU or source/Atlas component-count trigger |
| Austin | `gb:USA:ADM2:52423323B73481023135249` | `48015` | justified | No IoU or source/Atlas component-count trigger |
| Harrison | `gb:USA:ADM2:52423323B74436267722648` | `48203` | justified | No IoU or source/Atlas component-count trigger |
| Mitchell | `gb:USA:ADM2:52423323B74678572937686` | `48335` | justified | No IoU or source/Atlas component-count trigger |
| Concho | `gb:USA:ADM2:52423323B74717321160891` | `48095` | justified | No IoU or source/Atlas component-count trigger |
| Reagan | `gb:USA:ADM2:52423323B76210058558743` | `48383` | justified | No IoU or source/Atlas component-count trigger |
| Tyler | `gb:USA:ADM2:52423323B76755657103328` | `48457` | justified | No IoU or source/Atlas component-count trigger |
| Eastland | `gb:USA:ADM2:52423323B76826810418880` | `48133` | justified | No IoU or source/Atlas component-count trigger |
| Caldwell | `gb:USA:ADM2:52423323B77410024444051` | `48055` | justified | No IoU or source/Atlas component-count trigger |
| Grimes | `gb:USA:ADM2:52423323B77575058684255` | `48185` | justified | No IoU or source/Atlas component-count trigger |
| Stephens | `gb:USA:ADM2:52423323B77635562535718` | `48429` | justified | No IoU or source/Atlas component-count trigger |
| Smith | `gb:USA:ADM2:52423323B77803099717971` | `48423` | justified | No IoU or source/Atlas component-count trigger |
| Matagorda | `gb:USA:ADM2:52423323B77931792505034` | `48321` | insufficient-evidence | atlas_v6_to_2018_census=0.854564; atlas_v6_to_2025_census=0.854564; source_to_2018_census=0.855952 |
| Tarrant | `gb:USA:ADM2:52423323B78708010643826` | `48439` | justified | No IoU or source/Atlas component-count trigger |
| Brown | `gb:USA:ADM2:52423323B78869774166833` | `48049` | justified | No IoU or source/Atlas component-count trigger |
| Potter | `gb:USA:ADM2:52423323B78910372712846` | `48375` | justified | No IoU or source/Atlas component-count trigger |
| Andrews | `gb:USA:ADM2:52423323B79543792390346` | `48003` | justified | No IoU or source/Atlas component-count trigger |
| Bandera | `gb:USA:ADM2:52423323B80467523610206` | `48019` | justified | No IoU or source/Atlas component-count trigger |
| Jones | `gb:USA:ADM2:52423323B81114604697536` | `48253` | justified | No IoU or source/Atlas component-count trigger |
| Navarro | `gb:USA:ADM2:52423323B81183293432055` | `48349` | justified | No IoU or source/Atlas component-count trigger |
| Grayson | `gb:USA:ADM2:52423323B81583627867323` | `48181` | justified | No IoU or source/Atlas component-count trigger |
| Upshur | `gb:USA:ADM2:52423323B81614927564615` | `48459` | justified | No IoU or source/Atlas component-count trigger |
| Foard | `gb:USA:ADM2:52423323B82900100133763` | `48155` | justified | No IoU or source/Atlas component-count trigger |
| Gregg | `gb:USA:ADM2:52423323B83112121815500` | `48183` | justified | No IoU or source/Atlas component-count trigger |
| Jackson | `gb:USA:ADM2:52423323B84486994162427` | `48239` | justified | No IoU or source/Atlas component-count trigger |
| Terrell | `gb:USA:ADM2:52423323B84594382337875` | `48443` | justified | No IoU or source/Atlas component-count trigger |
| Childress | `gb:USA:ADM2:52423323B84755136262127` | `48075` | justified | No IoU or source/Atlas component-count trigger |
| Kimble | `gb:USA:ADM2:52423323B85125570419162` | `48267` | justified | No IoU or source/Atlas component-count trigger |
| Goliad | `gb:USA:ADM2:52423323B85181165620653` | `48175` | justified | No IoU or source/Atlas component-count trigger |
| Parmer | `gb:USA:ADM2:52423323B8622019817897` | `48369` | justified | No IoU or source/Atlas component-count trigger |
| Motley | `gb:USA:ADM2:52423323B8649342389596` | `48345` | justified | No IoU or source/Atlas component-count trigger |
| Bee | `gb:USA:ADM2:52423323B86725714839987` | `48025` | justified | No IoU or source/Atlas component-count trigger |
| San Augustine | `gb:USA:ADM2:52423323B87261257392916` | `48405` | justified | No IoU or source/Atlas component-count trigger |
| Tom Green | `gb:USA:ADM2:52423323B87640997786605` | `48451` | justified | No IoU or source/Atlas component-count trigger |
| Pecos | `gb:USA:ADM2:52423323B87811641324082` | `48371` | justified | No IoU or source/Atlas component-count trigger |
| Haskell | `gb:USA:ADM2:52423323B88573225501787` | `48207` | justified | No IoU or source/Atlas component-count trigger |
| Lampasas | `gb:USA:ADM2:52423323B89118572661224` | `48281` | justified | No IoU or source/Atlas component-count trigger |
| Carson | `gb:USA:ADM2:52423323B89233879615837` | `48065` | justified | No IoU or source/Atlas component-count trigger |
| Angelina | `gb:USA:ADM2:52423323B89498799122377` | `48005` | justified | No IoU or source/Atlas component-count trigger |
| Archer | `gb:USA:ADM2:52423323B89953257646119` | `48009` | justified | No IoU or source/Atlas component-count trigger |
| Hansford | `gb:USA:ADM2:52423323B90257338049784` | `48195` | justified | No IoU or source/Atlas component-count trigger |
| Burleson | `gb:USA:ADM2:52423323B90377685931333` | `48051` | justified | No IoU or source/Atlas component-count trigger |
| Delta | `gb:USA:ADM2:52423323B91707505421918` | `48119` | insufficient-evidence | atlas_v6_to_2018_cbf=0.975649; atlas_v6_to_2018_census=0.975045; atlas_v6_to_2025_census=0.975045; source_to_2018_cbf=0.975694; source_to_2018_census=0.975084 |
| Presidio | `gb:USA:ADM2:52423323B92102614150660` | `48377` | justified | No IoU or source/Atlas component-count trigger |
| Runnels | `gb:USA:ADM2:52423323B92139575394667` | `48399` | justified | No IoU or source/Atlas component-count trigger |
| San Jacinto | `gb:USA:ADM2:52423323B92388679305568` | `48407` | justified | No IoU or source/Atlas component-count trigger |
| Anderson | `gb:USA:ADM2:52423323B92486842041177` | `48001` | justified | No IoU or source/Atlas component-count trigger |
| Lubbock | `gb:USA:ADM2:52423323B93291035550773` | `48303` | justified | No IoU or source/Atlas component-count trigger |
| Gray | `gb:USA:ADM2:52423323B94857587121418` | `48179` | justified | No IoU or source/Atlas component-count trigger |
| Aransas | `gb:USA:ADM2:52423323B95001910303654` | `48007` | insufficient-evidence | atlas_v6_to_2018_cbf=0.842206; atlas_v6_to_2018_census=0.602827; atlas_v6_to_2025_census=0.602824; source_to_2018_cbf=0.848493; source_to_2018_census=0.604961 |
| Walker | `gb:USA:ADM2:52423323B95540408919203` | `48471` | justified | No IoU or source/Atlas component-count trigger |
| Colorado | `gb:USA:ADM2:52423323B95841930276474` | `48089` | justified | No IoU or source/Atlas component-count trigger |
| Webb | `gb:USA:ADM2:52423323B96012126646205` | `48479` | justified | No IoU or source/Atlas component-count trigger |
| Lynn | `gb:USA:ADM2:52423323B96500488872097` | `48305` | justified | No IoU or source/Atlas component-count trigger |
| Comanche | `gb:USA:ADM2:52423323B96574112762437` | `48093` | justified | No IoU or source/Atlas component-count trigger |
| Edwards | `gb:USA:ADM2:52423323B96652215547422` | `48137` | justified | No IoU or source/Atlas component-count trigger |
| Hardin | `gb:USA:ADM2:52423323B96895412793722` | `48199` | justified | No IoU or source/Atlas component-count trigger |
| Van Zandt | `gb:USA:ADM2:52423323B97041282112733` | `48467` | justified | No IoU or source/Atlas component-count trigger |
| Brooks | `gb:USA:ADM2:52423323B9714616989875` | `48047` | justified | No IoU or source/Atlas component-count trigger |
| Scurry | `gb:USA:ADM2:52423323B97167662457996` | `48415` | justified | No IoU or source/Atlas component-count trigger |
| Randall | `gb:USA:ADM2:52423323B97563616401050` | `48381` | justified | No IoU or source/Atlas component-count trigger |
| Crockett | `gb:USA:ADM2:52423323B97949275752783` | `48105` | justified | No IoU or source/Atlas component-count trigger |
| Montague | `gb:USA:ADM2:52423323B98336857110967` | `48337` | justified | No IoU or source/Atlas component-count trigger |
| Morris | `gb:USA:ADM2:52423323B98583115824614` | `48343` | justified | No IoU or source/Atlas component-count trigger |
| Donley | `gb:USA:ADM2:52423323B98750800467499` | `48129` | justified | No IoU or source/Atlas component-count trigger |
| Ellis | `gb:USA:ADM2:52423323B98957090602000` | `48139` | justified | No IoU or source/Atlas component-count trigger |
| Floyd | `gb:USA:ADM2:52423323B99276961620993` | `48153` | justified | No IoU or source/Atlas component-count trigger |
| Frio | `gb:USA:ADM2:52423323B99594247353741` | `48163` | justified | No IoU or source/Atlas component-count trigger |
| Coryell | `gb:USA:ADM2:52423323B99652996528900` | `48099` | justified | No IoU or source/Atlas component-count trigger |
| Dimmit | `gb:USA:ADM2:52423323B99675237938488` | `48127` | justified | No IoU or source/Atlas component-count trigger |

## Texas parent and higher-area status

- The province assessment is recorded separately in `province-assessment.json`. Texas has 254 current county children and all 254 exactly match the issue roster; Texas county-government sources and the current hierarchy support the administrative meaning and membership. The province’s overall class is **insufficient-evidence** for its boundary because this county issue did not compare the outer Texas polygon to a dated state boundary source. Current hierarchy retains it as `gb:USA:ADM1`, grouped under West South Central, and marks its semantic and boundary review open.
- The hierarchy flags this as a 254-child group that needs review. The Texas Census guide distinguishes the 254 county governments from 862 statistical county subdivisions/CCD units that do not have county-government legal function. This supports retaining a county-level group without inventing another tier solely to reduce child count; it does not certify province geometry or sovereign parentage.
- West South Central is an official Census division, not a county-level administrative authority. This packet owns only Texas’s 254 IDs. Sibling #432 supplies the remaining 216 roster; the division’s complete parent geometry and region integration remain outside this packet.
- Current Atlas per-feature `semantic_review.status` remains `open` for the broader semantic review workflow. These findings provide issue-scoped evidence for Texas county identity/tier; they do not close that broader review or certify the Southeastern North America region.

## Provenance, reproduction, and unresolved engineering handoff

- Raw GeoBoundaries file restored from LFS at commit `9469f09592ced973a3448cf66b6100b741b64c0d`: 10,500,644 bytes, SHA-256 `81fdd384df8012e5007ed2994a8ab306352f3c48e32cd8ea99182195e8647f43`; metadata JSON SHA-256 `a4d2a82a1cd434960b6ed49531bff3330d0881674eea9dc8711e1ad6bf049b9f`. Original LFS pointers and a verifier/restoration script are retained beside them.
- Official 2018 Texas TIGERweb API response was retrieved 2026-10-05 06:14:19 PDT; 2025 response at 06:14:54 PDT. Exact query URLs, layer metadata, response sizes and hashes are recorded in `source/census-api-retrieval-manifest.json`. 2018 Texas TIGERweb API response SHA-256 `309151b2ea2bfcad71698f7c3b82a52fc92cb3a59c29ee040d22ec7263b34cc7`; layer metadata SHA-256 `2d3b72f3957787cae0f8ae5a77bafd0b9603f8d6a5b4db2a700898e179e855c6`. 2025 response SHA-256 `efc43054c4a7f555ba1a1cf26e6315e5562005635152a9a41795152fe0eec0d6`; metadata SHA-256 `0c64a04e01055622c957ef56f9b8fd35c99c4bcc78c2fa1bba11e716d6a72f31`.
- Official 2018 CBF ZIP retrieval dated 2026-10-05T13:26:58Z from `https://www2.census.gov/geo/tiger/GENZ2018/shp/cb_2018_us_county_500k.zip`; response 200, 11,530,479 bytes, SHA-256 `aaa866af327754e1b80aa87bfb97b04a7209f4f871075aef84affb8f0b3afe67`, Last-Modified `2019-05-02T14:21:36Z`. Census source is a U.S. government work; the original archive and retrieval record are retained.
- Reproduction: install exactly `source/reproduction-requirements.txt`; run the documented `reproduce.py` against the preserved inputs. The script pins baseline commit and verifies the GeoBoundaries LFS OID, current issue/sibling roster partition, source identity, unique census joins, geometry validity, projection axis order, and positive/negative overlap controls. Two clean final runs (`runs/twelve`, `runs/thirteen`) produced byte-identical output.
- Unresolved source-catalog lineage: current `data/administrative-sources.json` SHA-256 `16249e8d795aaded6a72910a8c72115a073814b25ee902d61ccc9a9490c6641a` differs from the exact restored upstream LFS raw-file hash above. Existing #954 scopes its investigation to sibling #432’s 216 IDs and does not resolve the Texas members. Engineering should establish what bytes/serialization the catalog hash identifies before any shared pin is changed. This packet itself preserves the Texas evidence and recommends no source catalog edit.
- Geometry follow-up #966 owns the exact 24 insufficient-evidence counties and the Texas province outline. It will retrieve dated authoritative state/county/court/survey records, resolve the Brewster component discrepancy, and document transformations, shoreline and island completeness before proposing any correction. Do not use current Census overlap alone to authorize an Atlas geometry change.
- Source-hash follow-up #967 owns the exact 254 Texas source members. It will identify the bytes represented by the repository catalog digest and give engineering a source-registry handoff. #954 remains a related sibling issue for its own 216 IDs; it does not close the Texas finding.

## Limits

This packet is a sourced research assessment for #431 only. It does not change geometry, source registry, hierarchy, claims, release pins, live records, or production. It does not approve any region interior, issue #714 publication, historical import, or release. No regional certificate or global geographic completeness claim follows.

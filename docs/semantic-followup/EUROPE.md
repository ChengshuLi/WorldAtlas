# Europe: exhaustive semantic follow-up

Reviewed 1 October 2026. This report accounts for every **current** Europe entity: **8,738 locations, 984 provinces, 121 areas, 11 regions, four subcontinents and one continent**, across **53 reference-owner territories**. It preserves exact entity and footprint/member hashes. Antarctica remains excluded.

The machine-readable record is [`europe.json.gz`](../../data/geographic-semantic-followup/europe.json.gz). It contains every current ID, complete chain, source role/vintage/license, prior review pointer, diagnostic outcome, country-specific assessment and ID-linked proposal. This is complete inventory and source-policy assessment, **not semantic completion**: no location or branch is declared approved solely because its source taxonomy or geometry screening passes.

## Inspected evidence and limits

Fresh inspection covered all **45 represented ADM source-policy metadata endpoints**, the corresponding 45 retained prepared geometry inventories, the GISCO 2024 named statistical-unit inventory, French official department/region registries, Belgian government region taxonomy, Swiss official register structure and SSB 2026 classifications. Compact territories and the non-ADM Irish reference are individually included. Public request URLs, byte hashes, returned metadata and selected inspected facts are retained inside the compressed record.

The fresh original Kosovo GeoJSON has **seven district polygons**, while its metadata claims **48 municipalities**. This is a source-description/count inconsistency, not proof that 41 current atlas locations disappeared. Prepared source inventories for Estonia, Slovenia, Russia and Turkey also differ from metadata counts; original source-land and intended scope must be checked before any change.

SSB 2026 has **357 named municipalities and 15 named counties**, excluding unspecified codes. Current Norway locations come predominantly from the 2013 municipality snapshot, while parent counties use another vintage. A reform crosswalk must retain old IDs and historical claims; replacing labels alone does not implement a correct new geography.

GISCO labels are statistical categories. NUTS integers are not atlas tiers, and name matches do not approve member footprints. Failed/blocked national pages and the interactive Andorra shell remain explicit unavailable evidence.

## Every regional branch

| Region | Areas | Provinces | Locations | Status |
| --- | ---: | ---: | ---: | --- |
| Baltic | 1 | 68 | 317 | Open; all child IDs recorded |
| Britain | 16 | 70 | 174 | Open; all child IDs recorded |
| Central Europe | 13 | 131 | 1385 | Open; all child IDs recorded |
| Eastern European Plain | 13 | 125 | 2007 | Open; all child IDs recorded |
| France | 15 | 99 | 323 | Open; all child IDs recorded |
| Iberia | 19 | 72 | 674 | Open; all child IDs recorded |
| Ireland | 2 | 10 | 45 | Open; all child IDs recorded |
| Italy | 21 | 108 | 612 | Open; all child IDs recorded |
| Low Countries | 5 | 24 | 388 | Open; all child IDs recorded |
| Nordic Europe | 7 | 69 | 961 | Open; all child IDs recorded |
| Southeastern Europe | 9 | 208 | 1852 | Open; all child IDs recorded |

## Every represented country/territory source policy

Counts cover only locations whose actual chain reaches Europe. Transcontinental owners and islands assigned to other continents remain covered in the corresponding global audit; owner totals are not geography totals.

| Profile | Europe locations | Installed source role and required decision |
| --- | ---: | --- |
| ALD — Aland | 1 | Whole Åland archipelago is an explicit territorial adaptation, not a municipality. ÅSUB publishes municipality and village/district statistics; audit every island and the compact archipelago exception before approving one location. |
| ALB — Albania | 36 | The selected layer names district territories (rrethe), not a generic modern municipality layer. Compare all source districts and their qark parents to the applicable legal vintage; the 2021 source label is not proof that the district role survives in 2026. |
| AND — Andorra | 1 | Seven source parishes have been consolidated into one whole-territory location. Treat this as a proposed compact mountain-territory exception, not an ADM1 parish location; the interactive government portal supplied no usable taxonomy content in this retrieval. |
| AUT — Austria | 94 | District locations under Länder can supply local administrative territories and local clusters. The source API canonical role is Unknown despite the policy saying District: independent district taxonomy and every city/district distinction remain required. |
| BLR — Belarus | 118 | Raion locations under oblast clusters are identifiable local administrative territories, but the 2005 vintage requires explicit retention and urban-scope review. A present-day or historical claim must not inherit that administrative membership silently. |
| BEL — Belgium | 43 | Arrondissement locations, province clusters and the three regional areas have distinct roles. The fresh Belgian government page explicitly identifies Flemish, Brussels-Capital and Walloon regions; it supports those area labels, not all arrondissement geometry or urban scope. |
| BIH — Bosnia and Herzegovina | 142 | The source canonical field says gbOpen, which is a collection label rather than an administrative role. Municipality/canton/entity roles must be verified individually; the country encompasses unlike intermediate administrations and cannot be approved from ADM3. |
| BGR — Bulgaria | 265 | Municipality locations under oblast clusters are a plausible country-specific local territory hierarchy. Confirm each city/municipal envelope and the represented 2019 geometry; NUTS classifications corroborate higher labels without replacing the municipal source. |
| HRV — Croatia | 557 | The source expressly mixes municipalities and towns; a city aggregation also exists. Audit each city envelope, county parent and the post-Yugoslav area interpretation. The source feature count and active count differ partly because of deliberate source adaptation. |
| CZE — Czechia | 77 | District locations and kraj clusters are different roles; Eurostat labels confirm regional names but not district footprints. The combined Czechoslovakia area is an undated legacy grouping, not a current administrative unit. |
| DNK — Denmark | 98 | Kommune locations under region clusters are plausible local territory/cluster roles. Check every island component and region correspondence independently; a same-name or single-child tier needs an explanation rather than implicit duplication. |
| EST — Estonia | 214 | The selected source represents 2017 and labels the canonical role Unknown. Its prepared inventory and live metadata disagree by one feature; establish the exact pre/post-reform municipality vintage and geometry before interpreting the locations as current municipalities. |
| FRO — Faroe Islands | 1 | A single Faroe archipelago territory is an explicit aggregation. Hagstova exposes named island/regional statistical branches, so one local-territory location must justify archipelago-wide function and preserve every island rather than rely on sovereign-owner membership. |
| FIN — Finland | 70 | The selected 70-source layer has canonical role Unknown; atlas policy calls it Subregion. Confirm each functional subregion and regional parent from official Finnish classifications, keeping Åland and disconnected island coverage explicit. |
| FRA — France | 320 | Arrondissements → departments → regions are distinct plausible roles at the pinned 2022 source vintage. The official department API supplies every code-to-region relation; the existing sourced fixes are retained, while urban identity and every footprint remain separate questions. |
| DEU — Germany | 409 | Locations mix independent cities and districts; provincial clusters mix Regierungsbezirke and Länder. The residual Germany area contains nine disconnected Länder rather than the whole country; use the actual Land identities and explicit coextensive city-state exceptions. |
| GIB — Gibraltar | 1 | A whole compact peninsula territory can be a local-territory exception. It must have a stated geographic area role within Iberia; the residual Spain area also contains unrelated Andorra and Sukarrieta and is not a sourced common local cluster. |
| GRC — Greece | 306 | Source municipalities plus city aggregations require per-city envelope review; regional units and regions are distinct higher roles. Mainland/island splits and the source 2010 vintage must be explicit, including Greek territories associated with Asia under the atlas convention. |
| GGY — Guernsey | 1 | The government parish page explicitly identifies parish responsibilities and contacts, showing a finer administrative layer exists. A whole Guernsey location remains a candidate compact territorial exception; coverage of the entire dependency and separate islands is not certified. |
| HUN — Hungary | 176 | District source role is a policy assertion while canonical metadata is Unknown; Budapest aggregation changes the count. Verify the precise rural district/urban district distinction and all parent memberships instead of assuming every named source record is a whole settlement. |
| ISL — Iceland | 74 | The 2016 municipality source and current Statistics Iceland municipality/urban-nuclei tables are separate vintages. Review all mergers, rural municipal extents and inhabited settlements; the statistical region labels alone do not justify local territories. |
| IRL — Ireland | 34 | County and county-level-city reference locations use a different source than the ADM profiles. Historic provinces are geographic groupings, not current first-level administrations; the island-wide region may cross ownership while every modern/historic role remains explicit. |
| IMN — Isle of Man | 1 | Whole Isle of Man is an explicit island-territory location, with its separately named area already installed. That corrects geographic context but does not certify finer settlement purpose, island completeness or independent coextensive provincial roles. |
| ITA — Italy | 610 | All 610 Italy locations are published ISTAT local labour systems (2011 geography, 2018 update), not the provinces claimed by the stale policy. Whole labour-system membership crosses administrative provinces; preserve the functional role and quantify every mismatch. |
| JEY — Jersey | 1 | Whole Jersey is a candidate compact island-territory exception. The attempted government parish URL returned 404; independent parish/island scope, neighbouring scale and complete footprint checks remain unapproved rather than inferred from the owner label. |
| KAZ — Kazakhstan | 10 | The ten Kazakhstan-owned Europe locations are district territories associated with the west-of-Ural geographic side. Region membership is country-independent. Keep the measured whole-location continental assignment, while district purpose and land/island completeness stay separate. |
| XKX — Kosovo | 7 | The pinned public GeoJSON has seven named District of ... polygons, while metadata claims Municipalities and 48 units. Official GISCO 2024 exposes seven Kosovo statistical-region labels. Correct the source-role description and review granularity; do not call these municipality locations. |
| LVA — Latvia | 43 | The 43 administrative-territory source features represent 2021. Validate the precise reform vintage and city/municipal roles rather than backdate them; Baltic macro membership does not establish municipal or province-tier equivalence. |
| LIE — Liechtenstein | 1 | Eleven source subdivisions have become one whole Liechtenstein location. The source canonical role is Unknown and the official portal was blocked; compactness is a candidate exception, not evidence that a whole-country location is equivalent to each municipality. |
| LTU — Lithuania | 60 | The 60-source layer has canonical role Unknown although policy says Municipality. Verify urban versus district municipalities and county/functional clusters individually; label correspondence with statistical regions does not approve local settlement footprints. |
| LUX — Luxembourg | 1 | Twelve source canton-labelled subdivisions are consolidated into a whole Luxembourg territory. Official GISCO identifies Luxembourg as its own territorial label; the current sole-member Belgium area is mislabelled. Whole-country granularity still needs a justified exception. |
| MLT — Malta | 1 | Sixty-eight local-council source territories are consolidated into one Maltese archipelago location. This is a compact archipelago exception, not a local-council location. The previously installed Malta area label repair is already accounted for and must not be proposed twice. |
| MCO — Monaco | 1 | The sole source territory and the Monaco statistics portal identify Monaco; its sole-member France area is misleading reference context. A compact whole-territory exception may be appropriate, but exact footprint and coextensive tier roles require evidence. |
| MNE — Montenegro | 23 | The 2017 canonical source role is Unknown, though source names include Municipality. Verify municipality boundaries and subsequent reorganizations before claiming current membership; the wider former-Yugoslav area requires a geographic-purpose decision. |
| NLD — Netherlands | 344 | The 2022 municipality source and twelve provincial envelopes supply recognizable roles. Municipal mergers and urban scope remain open. Eurostat province labels corroborate taxonomy without making the atlas member union an exact official province polygon. |
| MKD — North Macedonia | 84 | The 2016 source opštini layer needs municipality/urban-scope and reform review. Current groups live under the outdated Yugoslavia area; administrative geography must be separated from the former polity name without silently replacing historical identities. |
| NOR — Norway | 427 | The source municipality layer represents 2013 and provinces represent an older county framework. SSB 2026 explicitly lists 357 municipalities and 15 counties, excluding unspecified codes. Preserve old identities and build a sourced reform crosswalk before migration; Svalbard is separate. |
| POL — Poland | 380 | Powiat source names support county-level territories, but the canonical role is Unknown. Distinguish urban powiat cities from rural counties and official województwo clusters; NUTS subdivisions do not automatically become atlas provinces. |
| PRT — Portugal | 300 | Municipality territories and districts need distinct roles and source-vintage assessment. The canonical role gbOpen is not taxonomy. Europe includes mainland and Azores; Portuguese-owned Madeira lies in the Africa convention, so owner totals are not missing-island evidence. |
| MDA — Republic of Moldova | 37 | District locations are all grouped within the Ukraine area. That botanical residual does not accurately describe a Moldova-only administrative cluster. Use a distinct sourced area or an explicitly geographic combined label, preserving the original source and IDs. |
| ROU — Romania | 42 | All 42 source units are counties/Bucharest, corroborated by 42 NUTS-3 labels. A province-scale source used as a location needs explicit local-purpose review and a sourced finer/functional alternative; a count or area threshold alone cannot demand subdivisions. |
| RUS — Russian Federation | 1347 | European raion territories are a subset of a transcontinental source country, with federal-city exceptions. Whole-location west/east-Ural assignment is geographic, not ownership-based; verify every rayon/federal-city envelope and source district-parent role independently. |
| SMR — San Marino | 1 | Nine source subdivisions are consolidated into one compact San Marino territory. The canonical role is Unknown, so the source roles and coextensive geographic tiers require independent documentation; compact size does not silently certify complete islands/land coverage. |
| SRB — Serbia | 145 | The 145 source territories have canonical role Unknown; names include municipalities/cities. Verify actual city/municipal roles and district membership, preserve every variant, and review the former-Yugoslav area separately from political ownership. |
| SVK — Slovakia | 79 | The selected okres layer supports district-territory intent, with kraj province clusters. The source vintage and city districts still require local-purpose review; Czechoslovakia is a legacy geographic label rather than an administrative authority. |
| SVN — Slovenia | 212 | The prepared source contains 212 municipality polygons while live metadata says 213. Hodoj has a separate geographic portion parent; source and boundary anomalies must be resolved explicitly rather than changing neighboring ownership or dropping a municipality by count. |
| ESP — Spain | 372 | Active Europe locations are 333 MAPA agricultural-comarca adaptations plus 39 municipality territories. The municipality-only policy is stale. Agricultural districts are a functional rural geography, and excluded separately mapped cities must be audited as whole territories. |
| SWE — Sweden | 290 | Municipality territories under county clusters are identifiable source roles. Assess all archipelagos, northern rural extents and city/municipal envelopes; the 2017 observation is not a current legal or historical boundary assertion. |
| CHE — Switzerland | 169 | The FSO states that its official commune register is structured by cantons and districts or comparable entities. District locations/canton clusters are supported taxonomy, but exceptions where cantons lack comparable districts and the 2022 footprint vintage remain open. |
| TUR — Turkey | 32 | The Europe branch contains source districts and one city aggregation, associated with European Thrace under the geographic convention. Actual district inventory and metadata counts differ; city scope and both continental sides must be reviewed before declaring complete source coverage. |
| UKR — Ukraine | 495 | The source contains 495 raions from 2006. This is a dated reference, not a 2026 raion map; independent reform/legal sources were unavailable in this retrieval. Crimean and other source geographic portions require country-independent parent explanations and retained history. |
| GBR — United Kingdom | 184 | Counties/unitary authorities plus a separately aggregated London city form mixed local territory roles. Review all English/Welsh/Scottish/Northern-Irish variants; the Great Britain residual is specifically Reading and North Ayrshire, not an acceptable general parent explanation. |
| VAT — Vatican | 1 | The full licensed Vatican footprint was already installed and is retained. A compact whole-territory location and coextensive tiers can be an explicit exception, but neighboring geographic scope and source coverage remain distinct from that completed repair. |

## Concrete proposed changes

No proposals alter active geography or dated evidence in this report. Each is linked to actual IDs and exact current member inventories in the compressed ledger.

- Correct source-policy descriptions for all Italian labour-system locations, Spanish agricultural-comarca/municipality locations and the seven Kosovo district territories. These annotations do not themselves fix urban envelopes or granularity.
- Rename the sole-member France area to Monaco and the sole-member Belgium area to Luxembourg, retaining IDs and original evidence. The compact-territory exception remains separately reviewed.
- Replace the unexplained nine-Länder Germany remainder with source-supported Land-area groupings if every provincial role and coextensive exception is justified.
- Research explicit area roles for Moldova, Liechtenstein, former Yugoslav and Czech/Slovak territories; do not silently substitute EU Western Balkans terminology for a different member inventory.
- Resolve the actual Britain residual (Reading/North Ayrshire) and Iberia residual (Sukarrieta/Gibraltar/Andorra) through source membership and full geographic scope, not a nearest-centroid assignment.
- Crosswalk Norway/Estonia/Ukraine source vintages and review Romania county-sized location purpose before any source replacement.

## Every flagged case remains accounted for

There are **1,760 distinct attention locations**. Overlapping triggers comprise **910 multipart territories, 846 weak parent-correspondence cases, 256 neighboring-scale contrasts and two shared-source-identity cases**. Every one is retained by ID with the full attention evidence. Unequal areas, multipart islands and named rural territories are questions requiring sourced exceptions, not automatic reasons to split or merge.

All 1,121 parent groups retain their exact direct children and complete member location IDs. The prior Europe inspection is reconciled to current membership, distinguishing new continental association from retired/replaced identities. Previously installed Malta, encoding and source-union corrections are not submitted again.

## Reproduce and continue

```sh
python scripts/audit-europe-semantic-followup.py --check
python scripts/audit-europe-semantic-followup.py
```

The check uses the committed compressed report and current committed inputs. It requires no previous-thread cache. Public source receipts and parsed observations are embedded in the report; the prepared-cache geometry inventories explicitly identify their scope and original public URL. A new source retrieval must retain a new receipt rather than pretending an old hash is current.

Research every open branch and flagged ID to a source-supported correction or justified exception, then feed individually complete checks into the global closure process. Actual geometry/membership changes require the normal archived-identity migration, majority-ownership regeneration, source-land checks and fixed-grid validation. This follow-up does not close those gates.

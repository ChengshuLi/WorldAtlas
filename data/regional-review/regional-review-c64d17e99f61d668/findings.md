# Findings — issue #420

**Reviewed:** 2026-10-05 (America/Los_Angeles)
**Status:** source/semantic review only; no geography certification or edits to atlas records.
**Issue pins:** region `framework:region:southeastern-europe:e7fed0fa4e00`; current review release `geography:review:df86cbaeaf2e18f16ddf2906ef089768baac22f4428e28ed0a4724296cbb413e` v5; hierarchy SHA-256 `03d23534f87cdd0582bcb228780f00f65090bec2e8a760acbab528383f28549d`; footprint SHA-256 `2ac42eeb9fef8af923a0d4c4e55af49ca0a103de891ffbfb2c1181ad75950286`.

This is the exact 207-member issue scope: 80 Greece (`gb:GRC:ADM3`, source vintage 2010) and 127 Croatia (`gb:HRV:ADM2`, source vintage 2021). The two issue area scopes are partial. The province workloads are complete *within the exact reviewed source tier* as listed below; this does not mean an entire area or the region has been approved. Every individual classification and stable ID appears in `crosswalk.json`.

## Individual outcomes

| Scope | Scoped units | Identity/role result | Geographic/boundary classification |
|---|---:|---|---|
| Greece ADM3 / municipality | 80 | The geoBoundaries snapshot labels the source tier “Municipality”; the Kallikratis law/report support the municipal role and a 325-unit historical framework. The official geometry file cannot currently be restored from its catalog endpoint. | **Insufficient evidence** for every unit. The retained 2010 geometry source itself and name/role metadata are not a same-vintage official boundary crosswalk. |
| Croatia ADM2 / municipalities and towns | 127 | 126 exact name + county + type matches against both the DGU INSPIRE extract and the Ministry’s official roster spreadsheet; one source spelling differs from both official rosters. | **Insufficient evidence** for the 126 exact identity matches because the source-vintage polygons have not been compared to authoritative boundary geometry. **Correction-needed** for `gb:HRV:ADM2:41942358B16839252431518` (`Općina Magdenovac`), whose 2013 Ministry roster and DGU record give `Magadenovac` in Osijek-Baranja County. Verify the 2021 source label and boundaries before any record change. |

“Justified” identity in the Croatian column means supported unit identity/role, not a finding that its territorial boundary is correct. The one correction-needed classification is a sourced spelling/identity handoff, not a request to edit core geography in this packet.

## Exact province inventory

| Atlas province scope | Country source tier | Issue members |
|---|---|---:|
| Požega-Slavonia | Croatia ADM2 | 10 |
| Virovitica-Podravina | Croatia ADM2 | 16 |
| Brod-Posavina | Croatia ADM2 | 28 |
| Osijek-Baranja | Croatia ADM2 | 42 |
| Vukovar-Syrmia | Croatia ADM2 | 31 |
| Ionian Islands (`Ionion Nison`) | Greece ADM3 | 7 |
| Epirus (`Ipeiroy`) | Greece ADM3 | 18 |
| Western Macedonia (`Dytikis Makedonias`) | Greece ADM3 | 12 |
| Western Greece (`Dytikis Elladas`) | Greece ADM3 | 18 |
| Thessaly (`Thessalias`) | Greece ADM3 | 25 |

The exact counts sum to 127 + 80 = 207, and every ID was found once in the pinned raw geoBoundaries source and once in Atlas parts 9/10. The source hierarchy metadata points Greek members to `gb:GRC:ADM2` and Croatian members to `gb:HRV:ADM1`; it does not independently certify the current Atlas province assignments. Its source-overlap diagnostic is below 0.90 for 15/80 Greek members (minimum 0.59631) and 5/127 Croatian members (minimum 0.792991). These 20 rows are explicit parent/source-comparison follow-ups in `crosswalk.json`, not asserted parent errors. The admin parents range from regional tiers in Greece to counties in Croatia; “ADM3” and “ADM2” are source-specific labels, not universal granularity standards.

The 127 Croatian source members are current Croatian local-government territories grouped by the Atlas’s macro area named “Yugoslavia.” Their source owner and official county crosswalk remain Croatia. That macro-area label does not assert that present-day Croatian administration is Yugoslav or settle the combined parent meaning. Greece and Yugoslavia area scopes are partial; combined parent decisions remain with regional integration.

## Territorial role, boundaries and granularity

- The pinned GRC source metadata says 2010 ADM3, canonical `municipality`, 326 source features, CC0 in one field, and `geoBoundaries, Wikimedia Commons` in the source description. Its detailed license fields separately say Wikimedia source material includes CC BY 3.0. The Hellenic Data Service catalog identifies the Kallikratis municipality-boundary dataset as version 1.1 (a correction to the 2010 release), CC-BY-3.0, by the Hellenic Mapping and Cadastral Organization. Preserve the attribution conflict instead of choosing the more permissive declaration.
- The official 2012 Greek Ministry report describes the Law 3852/2010 municipal reorganization and 325 municipalities. This supports the historical municipality role/count, but cannot identify or validate the 80 exact polygons.
- The GRC source has 326 distinct source IDs but 325 unique normalized names: `Oraiokastro` occurs twice under distinct IDs `gb:GRC:ADM3:53547021B25127242481922` and `gb:GRC:ADM3:53547021B15452068412187`. This duplicate is outside the issue’s exact 80 Greek IDs. It is a source-lineage/completeness follow-up; the country-level count difference alone does not show which geometry is right.
- Greek source geometry is multipart for 10 scoped municipalities: Missolonghi, Skiathos, Corfu, Ithaca, Paxos, Lefkada, South Pelion, Skopelos, Zakynthos and Alonnisos (up to 11 polygon components). Multipart geometry may be legitimate for islands, but this packet lacks the official same-vintage municipal geometries needed to verify islands, islets, exclusion/remainder areas, and complete municipal territory.
- The Croatian geoBoundaries metadata describes 2021 ADM2 as “Municipalities and Towns,” derived from OpenStreetMap/geoBoundaries, with CC BY-SA 2.0 source license. The 2013 Ministry XLS distinguishes 428 `Općina` and 128 `Grad`; DGU’s scoped 3rdOrder names/county records plus these typed roster entries support the unit identity for 126 rows. DGU Open Data is reusable under its Open Licence with attribution, dataset URI, last-modified date, and a statement of modifications.
- Croatian source geometry is multipart for Bilje, Šodolovci and Đakovo; Kneževi Vinogradi includes one polygon hole. These are review signals, not errors by themselves. No scoped city territory was split into settlement/ward units, and no city boundary completeness or neighboring edge was validated.
- Atlas geometry records show topology reconciliation for 7 scoped Greek and 39 scoped Croatian locations. Their metadata says shared display coverage was reconciled against Natural Earth/reference borders and then finer source geometry, and warns original source boundaries may differ. Hashing the retained source Geometry objects against the corresponding current Atlas Geometry objects gives 0/80 Greek and 0/127 Croatian exact matches. These are exact serialized coordinate-object differences, not measured territorial discrepancies; no spatial distance, area, overlap, or edge-quality result is inferred from hashes. Preserve the original-source hashes, inspect the source-vintage boundaries and route resulting shared-boundary changes to engineering/region integration.
- `crosswalk.json` records every source role, year, license field, source ID, Atlas parent, original/current geometry hash, parts/holes/vertex count, overlap metadata and an individual classification. Geometry component counts and hierarchy overlap alone do not certify territorial meaning.

## Croatia count definitions and source version

The current Ministry list says 555 local-government units (428 municipalities + 127 cities), 20 counties, and separately says Zagreb has special city-and-county status. The Croatian Bureau of Statistics’ 2022 publication gives the territorial constitution as of 2021-12-31 as 21 counties, 128 towns and 428 municipalities. The official Ministry spreadsheet captured in this packet was last saved 2013-06-10 and also lists 428 `Općina` + 128 `Grad` rows. These counts use different treatments of Zagreb and dates; the 127/128 city difference is not evidence that an issue-scoped unit is missing. DGU’s downloaded GML contains 50,192 actual `wfs:member` records and 556 `3rdOrder` units, but its FeatureCollection header says `numberReturned=10000` while `numberMatched=50192`, despite the file containing 50,192 member elements and the header also advertising a next-page URL. The archive advertises all Croatia; preserve the internal count inconsistency, and do not rely on its count/header alone as a completeness certificate.

The retrieved DGU archive was 208,774,354 bytes (the ATOM feed advertised 219,327,549). Its `AdministrativeUnit.gml` member was 600,770,112 bytes, SHA-256 `add049ecfb0355f0d64f912b99ba79021ad0f0d5f1cb2434ec5b1187a7446d69`. Exact archive SHA-256: `4a6b9f23e438861f2462b0d6aa06bd4140112e82947a4cdee06ce7a3b40ae23f`. A scoped official extract is retained because the full archive exceeds the per-file evidence size guidance; the extraction script verifies the exact full-archive hash before producing it.

## Greece source access and vintage

The Hellenic Data Service catalog metadata was retrieved and retained. Its advertised official Kallikratis ZIP URL returned HTTP 404 when requested on 2026-10-05. The official YPES Kallikratis PDF and the Central Greece 325-municipality roster page returned HTTP 403 to direct retrieval; GEODATA.gov.gr’s CKAN request timed out. Search results and the official 2012 ministry report support broad legal/count context, but are not substituted for the missing exact geometry/roster evidence. No source vintage is invented to fill the gap. The source-attempt log and restoration URLs are in `source/access-attempts.json`.

## Engineering and research handoffs

1. **Bounded correction follow-up:** [#1003](https://github.com/ChengshuLi/WorldAtlas/issues/1003) reviews the exact 2021 source object and licensed authoritative boundary evidence for `gb:HRV:ADM2:41942358B16839252431518`; it will decide whether the display label/source entity ID is a typo for official `Magadenovac`, then recommend an ID-preserving correction only if supported. It is blocked on #420. No location edit is in this packet.
2. **Bounded Greece source-restoration follow-up:** [#1002](https://github.com/ChengshuLi/WorldAtlas/issues/1002) restores the exact 2010 Kallikratis boundaries (HDS v1.1) or an equivalent official same-vintage dataset; it requires retrieval/hash/license and an 80-member crosswalk. It is blocked on #420 and must resolve CC0 vs CC-BY-3.0 lineage before redistributing geometry.
3. **Regional integration handoff:** inspect the 20 low source-parent-overlap rows and every source/current geometry difference with full relevant neighbor and boundary inputs. Preserve exact region/release pins and obtain full-area context before any shared parent or boundary decision.
4. **Out-of-scope Greece source-count handoff:** investigate the two Oraiokastro source features and 326-vs-325 count outside this packet’s location IDs; do not fold them into #420 or infer a repair from their duplicate name alone.

No rows, IDs, province names, releases, or boundaries were changed. No deployment, production write, import, or historical approval was performed. Geographic completion is not certified; all unresolved issues remain visible for the child/source-restoration and region-integration work.

## Authoritative references

- [Hellenic Data Service: Kallikratis municipality boundaries](https://data.hellenicdataservice.gr/el/dataset/63786e9f-7be9-4d1e-99c9-48ff45d0962f) — official dataset metadata and advertised download/version/license.
- [Greek Ministry of Interior: Structure and Operation in Greece (2012)](https://www.ypes.gr/UserFiles/f0ff9297-f516-40ff-a70e-eca84e2ec9b9/Structure_and_operation_Greece_2012.pdf) — 325 municipality historical count and legal context.
- [Law 3852/2010, YPES-hosted PDF](https://www.ypes.gr/UserFiles/f0ff9297-f516-40ff-a70e-eca84e2ec9b9/N_KALLIKRATIS.pdf) — law source, direct retrieval returned 403 in this review.
- [Central Greece Region: 325 municipality list](https://www.pste.gov.gr/en/dimi/) — official regional government source, direct retrieval returned 403.
- [GEODATA.gov.gr Kallikratis municipality dataset](https://geodata.gov.gr/en/dataset/oria-demon-kallikrates) — Hellenic Mapping and Cadastral Organization source, CC-BY-3.0 catalog entry; service was not retrievable in this review.
- [DGU Open Data terms and INSPIRE ATOM entry](https://dgu.gov.hr/proizvodi-i-usluge/otvoreni-podaci/6596?big=0) — public unit download endpoint and Open Licence attribution/modification requirements.
- [DGU Spatial Unit Register](https://dgu.gov.hr/registar-prostornih-jedinica-172/172) — official register maintained by DGU.
- [NIPP register: INSPIRE administrative units](https://registri.nipp.hr/izvori/446) — official harmonized administrative-unit data record.
- [Croatian Ministry local-government list](https://mpudt.gov.hr/korisne-informacije/iz-djelokruga/lokalna-i-podrucna-regionalna-samouprava-24398/popis-zupanija-gradova-i-opcina-24402/24402?lang=sl) — current Ministry counts and Zagreb status.
- [Croatia in Figures 2022, Croatian Bureau of Statistics](https://podaci.dzs.hr/media/l2wkiv1a/croinfig_2022.pdf) — 2021 territorial counts and city/county convention.
- [Croatian open-data roster record](https://data.gov.hr/ckan/dataset/popis-zupanija-gradova-i-opcina) — retained package metadata and archived Ministry XLS source.

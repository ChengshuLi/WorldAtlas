# Findings and handoffs

Review date: 2026-10-05 (UTC). Issue: [#412](https://github.com/ChengshuLi/WorldAtlas/issues/412). Scope is the exact 223 frozen IDs in `scope.json`, not all of Mozambique, Zambia, or Southern Tropical Africa.

## Scope and reproducible join

The packet covers 121 Mozambique districts and 102 Zambia districts across 16 fully represented province groups in the batch scope. Each scoped ID joins to exactly one feature by the stable geoBoundaries source ID; every normalized Atlas/source name matches. See `location-assessments.csv` for the full row-level result and semantic classification. The row-level screening classifies 99 Zambia records as justified at administrative tier/parent level (not boundary level), two Zambia records as correction-needed parent candidates (Chama and Chirundu), and 122 records as insufficient evidence (all Mozambique rows and Itezhi-Tezhi). The Zambia parent recommendations preserve existing IDs and geometry pending current compatible linework; they are not implemented here. The pinned Mozambique and Zambia geoBoundaries files each contain 159 and 116 ADM2 features, respectively. These counts and joins are useful identity evidence only.

The script deliberately leaves every boundary status `insufficient-evidence`. It records polygon type, part, vertex, and closed-ring counts as structural information. It does not run an independent topology, adjacency, gap/overlap, or boundary-to-authority validation. The retained files alone do not establish whether each polygon represents the legally current territorial unit.

Granularity screen: the seven in-scope Mozambique ADM2 features whose names begin `Cidade` (Beira, Chimoio, Inhambane, Lichinga, Nampula, Pemba, Quelimane) are separate named district-tier records in this source, rather than city neighborhoods. Official INE territorial tables for Nampula and Cabo Delgado list Cidade de Nampula and Cidade de Pemba alongside their province's districts. They remain separate because merging them into parent rural districts would contradict the source's ADM2 role. Thirteen Mozambique Atlas geometries (19 in the pinned source) and six Zambia Atlas geometries (four in the pinned source) are multi-part polygons; they are listed in the CSV. These multipart shapes are screening leads for detached islands/territory checks, not a finding of error. This batch contains no ADM3+ records or anonymous remainder labels. No audited geometric argument here rules out weak, oversize or stale units; those boundary/purpose questions remain unverified.

## Mozambique (121 scoped rows)

The pinned geoBoundaries metadata labels the 2019 product as `districts`, says its source was Mozambique INE/OCHA ROSEA, reports 159 features and a 2023-01-19 source-data update, and asserts CC BY 3.0 IGO. However, INE's 2017 census metadata says the country had 161 districts and that Maputo City has seven municipal districts. INE's 2026 Censo 2027 cartography announcement again says the cartographic work covers 161 districts. This unresolved 161-versus-159 discrepancy means the packet cannot certify the full roster or completeness of the 159-feature source. The issue's 121 exact named records are assessed individually as insufficient evidence because their current legal parents and all scoped boundaries lack an authoritative redistributable row-level crosswalk.

The OCHA/INE-derived 2019 metadata records a lineage instruction that an Admin-2 “Pemba” polygon was merged into “Metuge” on instruction from IMO. The retained geoBoundaries feature collection includes both `Cidade De Pemba` and `Metuge`, so the lineage statement is not sufficiently clear to infer which feature, version, or administrative meaning it describes. Because all 17 Cabo Delgado province records are in scope, this uncertainty affects this packet directly. It is not resolved by the exact-name join.

The official INE ArcGIS 2017 district service describes its layer as still undergoing correction/harmonization and explicitly states the base belongs exclusively to INE. That geometry was not downloaded or redistributed here. The row-level Mozambique parent field therefore reflects the current Atlas hierarchy only; there is no lawful, independently retained row-level authoritative parent crosswalk in this packet. The 2019 source lineage, complete current district roster, license basis for the re-hosted geometry, and any Pemba/Metuge parent or boundary changes need authoritative resolution before engineering changes.

**Engineering handoff:** keep all 121 boundary assessments open. Obtain a redistributable current official ADM2 source or written redistribution permission; establish its date, unit definitions, province relations, exact completeness, license, and lineage. Resolve the 159/161 difference and Pemba/Metuge treatment before proposing IDs, parents, or geometry changes. Do not turn source-name matches into a correction.

## Zambia (102 scoped rows)

The official 2022 Census National Analytical Report states Zambia had ten provinces and 116 districts at the 2022 Census. The retained 2022 OSG/GRID3 administrative-boundary layer contains 116 district features. The layer's 116 distinct district names crosswalk one-to-one to the pinned 2020 geoBoundaries roster; all 102 scoped names are unique and present. The layer metadata describes a government-supported boundary compilation with OSG endorsement and CC BY 4.0. Current broad count and name crosswalk are well supported, but they do not validate every line or settle every parent assignment.

Three in-scope parent records require a focused authoritative reconciliation:

| District | Atlas parent | 2022 layer `PROVINCE` | 2022 `PROV_CODE` / leading `DIST_CODE` | Evidence and disposition |
| --- | --- | --- | --- | --- |
| Chama | Muchinga | Eastern | 103 / 106001 | ZamStats 2022 and 2023–2047 Eastern Province district lists, current Eastern Province Administration, and Chama District Council's 2025 plan say Chama is currently in Eastern, returned there in 2021. This conflicts with the Atlas parent and numeric codes. **Correction-needed parent candidate: Eastern. Preserve geometry and identity until code meanings and licensed, current ADM1 linework are reconciled.** |
| Chirundu | Lusaka | Southern | 109 / 105002 | Chirundu Town Council documents a 2021 transfer from Lusaka to Southern; current Southern official listings and the layer's PROVINCE field agree. Numeric codes conflict with that field. **Correction-needed parent candidate: Southern. Preserve geometry and identity until code meanings and licensed, current ADM1 linework are reconciled.** |
| Itezhi-Tezhi | Central | Southern | 109 / 101004 | Layer name conflicts with numeric codes and Atlas. Parliamentary and provincial sources differ across dates; historical sources report a move from Southern to Central in 2012 while current listings also place it in Southern. **Insufficient evidence; no change proposed pending dated authoritative resolution.** |

`PROV_CODE` is a numeric field and `DIST_CODE` has a leading province code. The discrepancy is directly observable in the source rows and should not be silently normalized. See the CSV for raw values. The other 99 scoped districts match both the 2022 `PROVINCE` field and the Atlas parent. Chama and Chirundu have sufficient dated official evidence for a current-parent correction recommendation, but the contradictory numeric source fields and lack of independently verified current linework still prevent any boundary decision. Itezhi-Tezhi remains unresolved.

**Engineering handoff:** preserve all current Atlas IDs and geometry. For Chama, Chirundu, and Itezhi-Tezhi, obtain a written/official administrative gazette or harmonized OSG/Ministry confirmation resolving both the dated legal parent and the `PROVINCE`/code discordance. Then create a separately scoped correction proposal if warranted. The 2022 census report confirms the aggregate 10/116 structure, not individual district boundaries.

## Cross-cutting conclusion

No boundary correction is proposed in this packet. All 223 boundary findings remain `insufficient-evidence`; the two Zambia parent correction recommendations and the Mozambique roster/license issues are explicit engineering/research follow-ups. This packet does not authorize a release import, production publication, regional approval, or whole-region completion.

## Bounded follow-up issues

- [#1042](https://github.com/ChengshuLi/WorldAtlas/issues/1042) covers all 159 current Mozambique location IDs, their province parents, and the area identity. It coordinates #411 and #412 and remains `status:blocked` until both evidence packets merge. Its acceptance is authoritative roster, 159/161 explanation, lawful source/license, and Pemba/Metuge lineage.
- [#1043](https://github.com/ChengshuLi/WorldAtlas/issues/1043) covers only Chama, Chirundu, Itezhi-Tezhi, their three current parents, and two candidate provinces. It coordinates #412 and #413 and remains `status:blocked` until both packets merge. It will reconcile dated legal assignment against the conflicting 2022 `PROVINCE`/code values.

Both children have unique owned paths and exact `evidence_quality.v1` subject/pin declarations. Creating them preserves these unresolved findings without expanding this packet's owned paths or transferring IDs.

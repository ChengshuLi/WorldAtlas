# West Africa interior batch 6: scoped evidence packet

Issue #472 owns this evidence directory. The packet assesses 229 native geoBoundaries ADM2 identities in four areas: Ghana 147/260 (partial), Guinea 34/34, Guinea-Bissau 39/39, and Liberia 9/136 (partial). It covers 27 named province scopes as pinned in `scope.json`. `reproduction/subject-assessments.csv` has one row per exact subject ID; `reproduction/findings.json` records counts, source metadata, overlays, Liberia comparisons and limits. The issue's area/province splits are retained verbatim in `scope.json`, not inferred from this packet's four country summaries.

This is evidence about a fixed research subset. It is not a regional or national boundary approval, a correction to atlas records, permission to import history, or publication authorization. No core geography or atlas records were changed.

## Method and identity preservation

`scope.json` is the exact scope snapshot from the issue, with the 229 IDs, source pins, frozen parent/area metadata and SHA-256 digests. The reproduction script checks the ID roster digest and uniquely retrieves each matching original row from the repository's compressed review-location sources. It joins each row to the shape ID in the pinned source, checks retained name/license/vintage and declared parent, and reports geometry type, polygon component count, vertex count, EPSG:6933 area, bounds, ADM1 overlay share, and the row-level evidence classification. It measures area-weighted child coverage of each separate ADM1 polygon; `0.98` is an explicit screening threshold, not a legal/geographic tolerance. Invalid geometry is repaired only in memory with Shapely `buffer(0)` for diagnostics; source bytes are unchanged. The country union measures are comparisons only.

Run from the repository root with the repository's pinned Python requirements:

```sh
python data/regional-review/regional-review-1deb892647c1aa26/reproduce.py
```

The script uses no network. It writes only the two output files under `reproduction/`. It reads Liberia ADM1/ADM2 geometry from the already merged #473 packet and verifies its compressed and decompressed hashes against that packet's register; `sources/shared-geoboundaries-lbr-2021.json` records the reuse paths and hashes. `acquire_geoboundaries.py` restores the pinned geoBoundaries release bytes and pointer receipts for the other layers. Retrieval receipts include exact URLs, dates, HTTP status, original byte lengths and SHA-256 values. Original source files have not been edited.

The row-level geometry columns also expose the fragmentation and granularity screens. In this scoped set, 17 source features are multipart: 7 Ghana, 5 Guinea, 4 Guinea-Bissau and 1 Liberia. Guinea-Bissau examples include island sectors Uno (7 components), Caravela (13), Bolama (3) and Bubaque (11); those parts are positive evidence of archipelagic representation in this source, but not an island-completeness proof. Other notable multipart rows include Ghana's Ho Municipal, Awutu Senya East and Kasena Nankana East, Guinea's Boke (10 components), and Liberia's Commonwealth (2). Metropolitan Accra contains several very small contiguous units (Ayawaso Central 1.56 km², Accra Metropolis 5.62 km², Ayawaso East 6.19 km²); these are retained as named municipalities/metropolitan units, not inferred rural tiles. Conversely, large source areas include Guinea's Kankan (17,648 km²) and Siguiri (17,649 km²), and Ghana's Karaga and Kwahu Afram Plains South (about 3,121 and 3,096 km²). Such size outliers may reflect the administrative level's purpose or data vintage; they need source/local-purpose evidence before any granularity change. Every component count, vertex count, and area remains available on its exact subject row.

## Source roles, vintage, license and coverage

The main reproducible source is the `gbOpen` release at geoBoundaries commit `9469f09592ced973a3448cf66b6100b741b64c0d` (commit dated 2023-12-13; release data built 2023-12-12). The release's own `metaData.txt` asks users to cite Runfola et al. (2020) or geoboundaries.org and recommends attribution to the input data providers. Original GeoJSON bytes, metadata and citation text or exact restoration receipts are under `sources/geoboundaries-9469f09/`; the release's license is recorded per layer. Relevant source records:

| Area | ADM2 count / declared role | Vintage and input provider | License | Context / finding |
|---|---:|---|---|---|
| Ghana (GHA) | 260 / Districts | 2019; USAID Ghana HPNO and Ghana Statistical Service | CC BY 4.0 | Official GSS 2021 PHC field manual describes 16 administrative regions and 260 MMDAs, distinct from 271 statistical districts. The pinned ADM1 comparison layer is 2021 OSM under CC BY-SA 2.0, so it is neither the same vintage nor same provider/license as the 2019 ADM2 source. |
| Guinea (GIN) | 34 / `prefecture` | 2017; World Food Programme and OCHA ROWCA | CC BY 3.0 IGO | Government of Guinea's presentation describes seven administrative regions plus a special Conakry zone and 33 prefectures. The 34th canonical prefecture entry, Conakry, needs a role/tier correction proposal. The government's page was HTTP 403 to direct capture; the fact was inspected via its public page rendering/search index. Page vintage is unstated and its text refers to the 2021–2025 health strategy. |
| Guinea-Bissau (GNB) | 39 / blank canonical role | 2017; OpenStreetMap and Wambacher | ODbL 1.0 | ADM1 has 9 features (`Regiões`) under ODbL 1.0. A 2024 UK P-CGN factfile citing DGGC through UN SALB reports 39 sectors; the 2025 government National Communication reports 36 sectors beneath eight regions plus the autonomous sector. Completeness and current tier interpretation remain unresolved. Respect ODbL attribution and database obligations if redistributing/deriving its database. |
| Liberia (LBR) | 136 / Districts | 2021; UNMIL and OCHA ROWCA | CC BY 3.0 IGO | Primary LISGIS 2022 census cartography contains 160 districts across 15 counties, under LISGIS CC BY 4.0. The nine issue-scoped old units lie in Bomi (4) and Grand Cape Mount (5); all have candidate same-county current matches except `Commonwealth`, for which `Commonwealth Rs` is only a possible alias. Crosswalk is not settled. |

All ADM0/ADM1 overlays and the licensed LISGIS GeoJSON inputs are retained as contextual evidence. They are not contemporaneous ground truth. The GeoBoundaries country union comparisons show (fraction intersecting ADM0 / dissolved ADM2 area outside ADM0 / overlap excess): GHA 0.9980154 / 0.00495744 / 0; GIN 0.99418207 / 0.00522698 / 0; GNB 1 / 0 / 0; LBR 1 / 0 / 0. These do not establish absence of missing islands, legal correctness, or completeness. The Ghana GSS field manual and two Guinea-Bissau public reports were downloaded for hashing/inspection but are not retained as full documents; see `official-context.json` for exact URLs, retrieval dates, response hashes, and rights-conscious retention limits. The direct GIN source retrieval failure is likewise recorded.

## Findings and bounded handoffs

### Ghana: 147 scoped districts

The rows match the pinned 2019 source ID, feature name, license and vintage; their declared regional names agree with the best parent-name overlay. 116 have at least 98% area overlay with the separate 2021 OSM ADM1 context. 31 fall below that screen. Examples include Asuogyaman (52.2%), Shai Osudoku (55.4%), and Achiase (70.0%). Because the comparison layer is a different-vintage/different-provider OSM product, those 31 are **insufficient evidence**, not demonstrated wrong parents. Handoff: obtain same-vintage GSS/official 2019 district-to-region geometry or crosswalk and recheck those exact 31 IDs, preserving both source vintages. The remaining 116 are classified justified only for this source/role/parent evidence; they are not legal boundary certifications.

### Guinea: 34 prefecture-canonical features

33 rows match source name, license, vintage and parent context. Conakry is the single correction-needed row: national context distinguishes it as a special zone, while the pinned 34-feature ADM2 metadata labels the whole layer `prefecture`. Handoff: a bounded source/role correction for the Conakry ID must identify the correct administrative role and authoritative geometry; do not silently relabel its boundary or infer a missing prefecture geometry.

### Guinea-Bissau: 39 sector candidates

All 39 retained identities agree with the pinned source and their parent overlay, but all are insufficient evidence for current completeness because the 2024 P-CGN/DGGC-referenced 39-sector source conflicts with the 2025 Government of Guinea-Bissau report of 36 sectors. These sources may describe differing conventions, effective dates or inclusion of the autonomous sector; this packet cannot reconcile them. Handoff: seek a dated DGGC/UN SALB roster and definition of the 36/39 count, including Bissau's autonomous status, then compare every native ID and neighboring coverage. No completeness claim follows from polygon count or overlay.

### Liberia: nine issue-scoped districts

The older pinned layer has 136 features and LISGIS's 2022 census layer has 160. The exact nine rows are `Tewor`, `Suehn Mecca`, `Klay`, `Garwula`, `Golakonneh`, `Dowein`, `Porkpa`, `Commonwealth`, and `Senjeh`. Eight names and county parents match exactly. `Commonwealth` is in Grand Cape Mount and `Commonwealth Rs` (LISGIS code 1208) is a plausible same-parent candidate, not a verified alias. Measured old-to-current symmetric difference divided by the old shape area is: Tewor 1.96%, Suehn Mecca 3.26%, Klay 34.27%, Garwula 0.46%, Golakonneh 1.19%, Dowein 15.17%, Porkpa 1.28%, Commonwealth/Commonwealth Rs 4.36%, and Senjeh 3.44%. These are source-vintage differences, not proof the 2022 data should replace any historical geography. LISGIS 2022 also has Bomi district `Tehr` (code 0310), which is outside these nine subjects. The neighboring #473 packet owns the other 127 old Liberia IDs and recorded a blocked source/crosswalk handoff #802; this packet does not duplicate those subjects or broaden #802's declared scope. Handoff: verify the nine-name mapping and changes against the original 2021 source documentation and LISGIS/DGGC or another authoritative dated crosswalk; link the work with #802 while preserving the distinct nine IDs and vintage.

## Per-row classifications and limits

`justified` means the scoped source identity, exact displayed name, recorded source license/vintage, declared parent name and (where applicable) screening overlay support the narrow statement in that row. It does not certify geometry lawfulness or national coverage. `correction-needed` records the specific Conakry role discrepancy. `insufficient-evidence` records unresolved cross-vintage parent coverage or the country completeness/crosswalk conflicts above. Counts: 149 justified (116 GHA + 33 GIN), 1 correction-needed, 79 insufficient-evidence (31 GHA + 39 GNB + 9 LBR). The row-level CSV preserves each assessment and its precise source/parent metrics. County/province scope records remain exact to the work item's frozen scope.

Source references and retrieval receipts:

- geoBoundaries pinned release: <https://github.com/wmgeolab/geoBoundaries/tree/9469f09592ced973a3448cf66b6100b741b64c0d> (original bytes/pointer receipts are in this packet; the LBR geometry bytes are reused from merged issue #473).
- Ghana Statistical Service, 2021 PHC Field Officers Manual, direct PDF URL and receipt in `official-context.json`.
- Government of Guinea, administrative overview: <https://gouvernement.gov.gn/presentation/> (retrieval blocked directly; content vintage not stated).
- Guinea-Bissau, National Communication 4 to UNFCCC (2025): <https://unfccc.int/sites/default/files/resource/GNB_NC4_English_FINAL_16112025_JLT.pdf>.
- UK Permanent Committee on Geographical Names, Guinea-Bissau Toponymic Factfile (2024): <https://assets.publishing.service.gov.uk/media/65f31c5efa1851001a011765/Guinea-Bissau_toponymic_factfile.pdf>.
- LISGIS, 2022 district and county data APIs: <https://lisgis.gov.lr/api/visualizations/datasets/geo-districts/2022>, <https://lisgis.gov.lr/api/visualizations/datasets/geo-counties/2022>; license page <https://lisgis.gov.lr/open-data-license> (captured bytes and source hashes in `sources/lisgis-2022/`).

Exact claims, scope hashes, source retrieval dates and SHA-256 receipts are in `scope.json`, `geoboundaries-restoration.json`, `official-context.json`, `sources/lisgis-2022/receipt.json`, and `sources/shared-geoboundaries-lbr-2021.json`. No source evidence was edited to match an expected answer.

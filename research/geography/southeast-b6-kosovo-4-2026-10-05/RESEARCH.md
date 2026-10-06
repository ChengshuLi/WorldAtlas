# Kosovo batch 6: four district identity and parent findings

Research date: 2026-10-06. Issue: [#1008](https://github.com/ChengshuLi/WorldAtlas/issues/1008). Reservation worker: `01a10947-b3d7-7812-8b2f-c5a47e88ccb2`. The branch was created from fresh `origin/main` `a801bc56cf8ea2b697a66b22ceebd7edf763badc`. The evidence manifest uses the older pinned scope baseline `96f2a6d201236ba62f471535db240b123de60c09`, which is the exact commit at which the issue's declared pins coexist. Its pinned release pointer is now historical (fresh main has since advanced from v6 to v7); no claims here rely on it as the currently published release. All twelve declared pins were verified at the manifest baseline.

## Decision summary

The four source labels each match a named Kosovo Agency of Statistics (KAS) proposed Level III statistical/economic region. The KAS report expressly calls these regions non-administrative territorial units and lists multiple legal municipalities in each. This is meaningful evidence that the labels and expected regional role are broader than a single municipality. It is not proof that the source polygons geometrically equal the KAS regions. No lawful, comparable, current KCA municipal-boundary vector was obtained, and the original source's 2021 OSM snapshot and relation identifiers are absent. Therefore **each source-polygon-to-current-municipality identity remains unresolved**.

The most material ambiguity is Mitrovica: KAS's Mitrovicë region includes both Mitrovicë and Mitrovica e Veriut (North Mitrovica), plus five other municipalities. The 2008 municipal-boundary law provides for separate North and South Mitrovica municipalities. If this source polygon represents the KAS region, it is not one municipality; without geometry comparison, that conditional cannot be upgraded to a finding about the polygon. Peja, Prizren, and Gjakova also match the names of one municipality within four-municipality KAS regions, so name alone cannot distinguish a municipality polygon from a regional grouping polygon.

The four existing province parents are same-name, single-child containers. Their pinned hierarchy notes say their member correspondence was derived from the same geoBoundaries source feature and leaves semantic review open. They do not independently establish a legal parent relationship. Keep parent purpose unresolved and coordinate any future change with the other three members of this same seven-feature source layer (#999) and the regional integrator.

No shared geography, geometry, IDs, parent nodes, release files, political-status fields, publication, import or regional approval was changed or requested.

## Per-ID outcomes

The complete reproducible per-ID record is in [findings.json](findings.json); pinned-input and source-role controls are in [reproduction.json](reproduction.json).

| Atlas ID / label | KAS 2022 proposed group | Members in that group | Municipality identity | Existing parent |
|---|---|---|---:|---|
| `gb:XKX:ADM1:2360587B11570115914955` — District of Mitrovica | Mitrovicë | 7, including Mitrovicë and Mitrovica e Veriut | Unresolved; same-name region spans seven municipalities | `framework:province:district-of-mitrovica:f4149a641a12`, single-child provisional container |
| `gb:XKX:ADM1:2360587B15813948402025` — District of Peja | Pejë | 4, including Pejë | Unresolved; name also identifies one member municipality | `framework:province:district-of-peja:68d54986d0ba`, single-child provisional container |
| `gb:XKX:ADM1:2360587B89959345704230` — District of Prizren | Prizren | 4, including Prizren | Unresolved; name also identifies one member municipality | `framework:province:district-of-prizren:5ea331ce3ec0`, single-child provisional container |
| `gb:XKX:ADM1:2360587B9056373484571` — District of Gjakova | Gjakovë | 4, including Gjakovë | Unresolved; name also identifies one member municipality | `framework:province:district-of-gjakova:86f71e89a8e2`, single-child provisional container |

For all four records, the source metadata says `boundaryType=ADM1`, `boundaryCanonical=Municipalities`, and `admUnitCount=48`; the retained collection has seven features, and the official KAS publication describes 38 municipalities grouped into seven non-administrative regions. The unexplained 48-versus-7 discrepancy is preserved as an upstream metadata conflict. It is not evidence that the polygons represent 48 current municipalities.

## Sources and territorial meaning

1. The immutable geoBoundaries source is the seven-feature XKX ADM1 collection at commit `9469f09592ced973a3448cf66b6100b741b64c0d`. Its metadata distinguishes boundary representation year 2021, source-data update 2023-01-19, and build date 2023-12-12. The original GeoJSON and metadata remain in the already merged #422 source packet at their pinned baseline paths and hashes; this packet does not make another geometry archive. All seven `shapeID`s match Atlas IDs and all seven source names match the corresponding KAS region names by the crosswalk retained from #999. Name correspondence is not boundary equivalence.
2. KAS, *Classification of Statistical Regions in Kosovo: Proposal Based on Regulation (EC) No 1059/2003* (April 2022), pages 4–7, describes the 38 municipalities as administrative units and proposes seven Level III regions as non-administrative territorial units. The region-to-municipality lists are retained as a small extraction from #999, with the original PDF's exact SHA-256 and restoration URL. The proposal is not a legal administrative-region act and contains no reusable machine-readable polygon dataset.
3. The Official Gazette's 2025-07-08 consolidated record for Law 03/L-041 is the current consolidated legal record inspected for this work. The statute defines municipalities as basic self-government units and boundary composition through cadastral zones. The original law, published 2008-06-02, expressly distinguishes North and South Mitrovica. These official legal texts establish legal-unit context, not contemporary digital polygon equivalence for the 2021 source.
4. KAS's 2024 census final-results publication credits municipality boundaries to the Kosovo Cadastral Agency (KCA), 2024. The official KCA Geoportal and its manual list an “Administrative Units” layer for municipal/local boundaries. A boundary authority/layer is identifiable, but this review did not verify an accessible downloadable vector, its vintage, completeness, or reuse terms. The census map is not vector data.
5. Neighboring-tier context from #999 shows different national level conventions and vintages: North Macedonia ADM2 (84 features, 2016, Opštini, reported CC BY 4.0); Serbia ADM2 (145 features, 2017, canonical unit unresolved, OSM/Wambacher ODbL); Montenegro ADM1 (23 features, 2017, canonical unit unresolved, OSM/Wambacher ODbL). These counts and licenses are not directly comparable indicators of Kosovo's legal tier. They are context, not validation.

Detailed exact URLs, source hashes, retrieval dates, rights uncertainty and restoration steps are recorded in [SOURCE_RESTORATION.md](SOURCE_RESTORATION.md). Official publications were not copied into this packet. Exact response hashes are verification receipts only; the lawful source files already retained in #422 remain the sole retained geometry evidence.

## Bounded handoffs

- **Source role (seven features together):** Propose a coordinated source-role adjudication for all seven source features. KAS's same-name, multi-municipality grouping evidence supports evaluating “non-administrative economic/statistical regional grouping”; it does not establish that this exact polygon dataset has that geometry. Keep the original `ADM1`, `Municipalities`, `48` metadata as immutable historic source assertions with their conflict recorded. Do not silently rewrite original evidence.
- **Identity and boundaries:** Obtain KCA's official current municipal vector and explicit terms for reuse/restoration; identify its vintage, feature roster and completeness. Confirm whether it is the appropriate representation vintage for these source boundaries. Group municipality polygons using the exact KAS 2022 table; document CRS, edge/precision treatment, multipart handling, boundary-date differences, and per-feature discrepancies. Do not infer identity from a name, level code, country code, or overlap score.
- **Parents and integration:** Keep existing province IDs/links as provisional references. #999 and #1008 must be considered together with the regional integrator before changing source-role resolution, parent purpose, boundary geometry, area/reference assignments, or release pins. Any proposal must preserve IDs and old evidence and separately account for macro-boundary evidence. This packet does not approve or alter those shared objects.
- **Reuse:** geoBoundaries says products are CC BY 4.0 but requires users to honor individual source metadata; this metadata says CC BY-SA 2.0 and cites OpenStreetMap, whose data license is ODbL 1.0. The metadata has malformed URLs and no OSM snapshot/relation IDs or exact OSM-Boundaries service provenance. Exact file reuse compatibility remains unresolved. Do not create or redistribute another polygon copy until the source chain and terms are clarified.

## Reproduction and verification limits

From the repository root, run:

```sh
python3 research/geography/southeast-b6-kosovo-4-2026-10-05/reproduce.py --root .
node scripts/evidence-quality.mjs research/geography/southeast-b6-kosovo-4-2026-10-05/evidence-quality.json
node scripts/check-handoff-scope.mjs --help
```

The Python reproducer loads the declared historic baseline blobs, checks all 12 issue pins, exact four feature IDs, parent IDs and single-child status, the seven source names and count conflict, the four KAS member lists, the complete 38-name count, and the inherited #999 source crosswalk/extract hashes. It emits deterministic findings, a source-role result and positive/negative controls. It does not compare geometries or establish boundary equivalence, law, or license compatibility. The issue's release manifest pin is intentionally reported as historical: fresh main advanced the release pointer after the declared evidence baseline; that later release does not affect the boundary facts examined here.

This is a source research packet with unresolved geographic conclusions, not regional approval, a legal opinion, a correction implementation, or authorization to import historical claims.

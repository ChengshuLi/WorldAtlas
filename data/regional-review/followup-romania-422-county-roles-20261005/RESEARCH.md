# Romania counties and repeated framework tier: scoped findings

Research date: 2026-10-05. Scope: exactly the 42 IDs and 42 listed province parents in issue #997. The reproducible row-level join is `source-crosswalk.json`; names from the source are preserved verbatim. `reproduce.py` rejects changed pins, missing/extra IDs, missing source features, duplicated source IDs, role/name mismatches, absent parents, and non-singleton or mismatched province parents.

## Legal and statistical roles

Romania’s consolidated [Law 2/1968](https://legislatie.just.ro/Public/DetaliiDocument/215837), Article 2 and Annex, identifies the Municipality of Bucharest separately from the counties and lists 41 counties. [Eurostat’s Romania regional accounts metadata](https://ec.europa.eu/eurostat/cache/metadata/EN/reg_eco10_esms_ro.htm) identifies NUTS 3 as the 41 counties plus Bucharest. The official county-layer listing on [data.gov.ro](https://data.gov.ro/dataset/unitati-administrativ-teritoriale-07-03-2024) likewise describes first-order administrative units as counties and Bucharest Municipality. Exact subject/name joins find 41 county names plus `BUCURESTI`, matching the one Bucharest role, across the 42 pinned IDs. This supports classification and roster completeness by name/count; it does not prove legal boundary accuracy or that every current boundary equals the 2017 geometry.

The official roster’s diacritics and the source’s uppercase ASCII transliterations are matched after Unicode decomposition, case-folding, and punctuation/diacritic removal; both original names remain in the row data. Each source `shapeID` maps one-to-one to one issue Atlas ID; the Atlas name agrees with the source label under the same conservative normalization. See per-subject join fields and hashes in `source-crosswalk.json`.

## Source meaning, vintage, completeness, and license

The retained geoBoundaries source is a 2017 World Bank ADM1 product, with source-data metadata dated 2023-01-19 and build date 2023-12-12. It has 42 source features and maps one-to-one to the exact 42 scoped Atlas units. Its metadata calls all 42 “Counties”; the legal distinction shows that label is imprecise for Bucharest. Cross-reference the 2024 ANCPI first-order source for current completeness, but it could not be downloaded and compared. The source license label is CC BY 4.0 and the attribution/use text is retained. However, World Bank catalog item `40320b20a03e469596202d77d5f5d374` differs from source metadata ArcGIS item `361134ff4ff44e78a9aeec01af9a5175`; exact object lineage remains unresolved. Do not claim license lineage has been conclusively matched at item level.

Neighboring pinned catalog entries demonstrate differing source vintages, classifications and granularities: Hungary ADM1 county (20, 2011); Bulgaria ADM1 province (28, 2019); Moldova ADM1 Districts (37, 2020); Serbia ADM1 districts (25, 2017) and ADM2 units (145, 2017); Ukraine ADM1 “Unknown” (27, 2017). This is catalog context only, not proof of neighboring legal equivalence. There is no common tier name/count/vintage suitable for asserting equivalent administrative meaning.

## Parent role and geometry limits

For each scoped child, the pinned hierarchy has one same-name `framework:province` parent with one child. Its recorded basis is “Named source administrative unit grouped within this geographic area”; framework status is `retained-reference`; semantic review and boundary status remain open. The evidence explains an internal grouping/reference role, but Romanian law and NUTS distinguish counties and Bucharest, not a separate province level. No authoritative evidence reviewed here establishes 42 legally meaningful same-boundary provinces. Recommend an ID-preserving hierarchy engineering review: decide whether these nodes are useful reference wrappers or should be represented by a non-administrative framework grouping, preserve child IDs and source identities, and make no mutation until the hierarchy owner reviews dependent queries/releases.

The crosswalk computes canonical JSON geometry hashes and vertex counts for source and Atlas representations. The Atlas uses transformed/simplified geometry; exact JSON matches are a representation diagnostic only. The source cache is from 2017, and no same-vintage official county vector was obtained. The current official ANCPI archive timed out on repeated fetches. Therefore polygon correctness, current boundary correspondence, geometric completeness, topology, and legal boundary accuracy remain unresolved. No count, checksum, topology check, or source label is treated as proof of those claims.

## Engineering handoffs and disposition

1. **Hierarchy owner:** review the 42 singleton same-name `province` parents and their `retained-reference` semantics. Preserve all existing IDs and consumers; propose any role change separately with migration/release checks.
2. **Source maintainer:** resolve the two World Bank/ArcGIS item IDs and preserve the current attribution/license evidence before any pin change.
3. **Geometry researcher:** restore the listed 2024 ANCPI ZIP, record its archive and extracted-file hashes/CRS/vintage/license notice, then perform a subject-by-subject boundary comparison. Keep the 2017 polygons as historical source until a reviewed replacement exists.

This packet reports research findings only. Implementation is proposed, geographic approval remains unapproved, and it authorizes no boundary mutation, publication, production write, regional approval, or historical import.

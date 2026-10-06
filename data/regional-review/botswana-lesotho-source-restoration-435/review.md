# Botswana and Lesotho source/tier research — issue #1136

Research date: 2026-10-06 (UTC). Scope: exactly 45 IDs from the immutable #435 roster: 35 Botswana (22 retained BWA ADM2 source features and 13 RESOLVE ecological clips) plus 10 Lesotho district IDs. This packet supplements #435; it does not alter, replace, or certify its evidence.

## Findings

### Botswana

Statistics Botswana’s 2022 PHC administrative/technical report (Table 4, §14.6, report p. 36) enumerates 28 census districts and a separate “Sub-District / Admin Authority” field. Its labels distinguish several functions and levels: Gaborone is a city/census district; Ngwaketse is a district with Kanye and Moshupa authorities; South East has north/south subdistricts; Central Serowe-Palapye has Serowe administration and a Palapye subdistrict; Central Boteti has Letlhakane; Central Tutume has Tutume and Tonota; Kgalagadi South/North use Tsabong/Hukuntsi authorities. These are official census-operation labels, not proof of statutory status or boundary geometry.

Exact-name comparison against that roster yields partial correspondences for Gaborone, Chobe, South East, Kgatleng, Barolong, Tshabong/Tsabong, Hukunsti/Hukuntsi, Palapye, Serowe, Mahalapye, Bobonong/Bobirwa, Lethlakane/Letlhakane and Tutume. This is a crosswalk hypothesis only; name similarity and census enumeration cannot validate a 2015 polygon. The other 2015 direct labels (including Ngwaketse Central/North/South, Machaneng, Gemsbok, Masungu, Kweneng North/South and Tuli) have no exact Table 4 match. Their absence does not prove abolition or error: the census layer is one purpose and older names may refer to a different/delimited function. The one source feature Gaborone is a city while its Atlas parent is South-East District, further warning that hierarchy role needs legal/administrative clarification.

All 13 physical IDs are ecological fragments whose IDs preserve a composite name and whose original source IDs resolve to three retained 2015 administrative polygons (Ghanzi, Ngamiland East, Ngamiland West). The ecological `resolve:*` ID is not an administrative authority. The old source supports lineage only; it does not make a clip an administrative entity. Prior #435 intersection diagnostics are retained there and are not repeated as a new territorial correctness assertion.

For current boundaries, Statistics Botswana maps are not law; the 2015 RCMRD source is dated; the Government of Botswana Department of Surveys and Mapping indicates layer access by request/fee; the 2025 Esri/MBR product expressly prohibits offline export. No licensed, reproducible, authoritative current full boundary dataset was lawfully available for this packet. Request official dated boundaries, legal basis, completeness, neighboring coverage and written reuse/adaptation rights before engineering proposes any polygon change.

### Lesotho

The Government of Lesotho’s 2022 Third National Communication identifies ten administrative districts and reports 80 constituencies and 124 community councils; it credits its district map to Lesotho Meteorological Services. Legal Notice No. 37 of 2022 establishes 80 electoral constituencies and says the individual deposited constituency maps/schedule control over district aggregation maps prepared for election convenience. The IEC’s 2025 page provides election maps, not district or community-council geometry. An older official decentralization source reports 128 councils; these counts differ by source date/function and are not reconciled here.

All ten Atlas subjects have a retained 2017 geoBoundaries/OSM ADM1 polygon and each subject is named exactly the same as its immediate Atlas parent. The official material corroborates the names as the ten districts, but does not establish a legitimate district-under-identically-named-district tier, nor certify the current polygons. UN SALB metadata describes nationally validated district polygons current through 2024-06-24, but its terms are noncommercial, require attribution and prohibit geometry changes without contributor consent. The source geometry was not copied. Request the versioned polygon and consent from the Lesotho national geospatial authority and SALB before use. The DRWS ArcGIS service endpoint returned HTTP 200/application error 499 “Token Required”; the exact 80-byte response is retained and must not be mistaken for source metadata.

The duplicated parent tier is therefore an engineering investigation, not a geography edit: trace why two IDs represent the same district name, determine intended feature roles and parent semantics from hierarchy provenance/official authority, then propose an ID-preserving correction only through a separate authorized engineering/geography issue. Do not delete either ID based on duplicate names.

## Source and reproduction limits

See `findings/source-register.json` for exact URLs, vintages, terms, retrieval dates, byte hashes and restoration steps. The 2015 Botswana and 2017 Lesotho inputs were copied byte-for-byte from the prior committed packet and rehashed. The Botswana 2022 PDF was restored by its exact official URL and has SHA-256 `eca23da4cb3dfa1dcc1df8b53d6abe5a0790db3dc3c95a329e7f80bd9caf0034` (1,753,665 bytes); we retain its URL/hash, not the copyrighted PDF. The full Lesotho 2022 report did not transfer completely; no partial file is retained and no hash is claimed. Follow its restoration instructions.

`subject-assessments.jsonl` joins every exact ID to its original source identifier, Atlas parent, evidence class, bounded finding, disposition, and uncertainty. `scripts/reproduce.py` checks all 45 IDs, per-country/group counts, exact retained input/source and baseline pins. These identity and byte checks only establish scope/reproducibility; they do not prove legal correctness.

## Engineering handoff / acceptance boundary

1. Preserve the 45 IDs and all original geometries/history/pins.
2. Do not infer statutory equivalence from names, a census roster, feature counts, area similarity or IoU.
3. Obtain Botswana DSM’s official dated polygon data and redistribution/adaptation rights; reconcile all 35 subjects and neighboring Botswana/Namibia granularity against its legal role.
4. Obtain Lesotho’s official versioned district and community-council source, plus contributor permission; compare all ten district polygons and resolve the duplicated same-name parent tier using hierarchy lineage.
5. Create separately scoped work for any shared hierarchy or boundary changes; researchers here only provide sourced proposals. No publication, approval or import follows from this packet.

This work item is fully assessed per declared ID, but its key geometry/legal questions remain blocked by source rights/access. It is not a regional certification.

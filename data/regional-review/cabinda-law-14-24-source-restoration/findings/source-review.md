# Cabinda 2024 municipal boundary source review

Research date: 2026-10-05. Scope is issue #896 and its four exact legacy location IDs. This packet is source research and engineering handoff only. It neither alters records nor certifies current geography.

## Territorial meaning and current roster

Angola Law 14/24 of 5 September 2024 establishes ten municipalities in Cabinda Province (Article 5; municipal boundary descriptions in Articles 6–19; provincial tables/maps are integral annexes under Article 3). The current roster is Cabinda, Cacongo, Buco Zau, Belize, Miconje, Massabi, Necuto, Tando Zinze, Liambo and Ngoio. The official Institute of Modernization of Public Administration (IMA) Cabinda page independently lists the same ten municipalities under Cabinda and provides a commune table. Its commune details are not treated as boundary evidence. The IMA page's listed site terms permit non-profit reproduction of site content with attribution and integrity, but do not clearly license derivative geometry from the Gazette maps.

The provincial context is Cabinda, an Angolan exclave bounded by the Republic of the Congo to the north/east, the Democratic Republic of the Congo to the south, and the Atlantic to the west (Law 14/24, provincial description). The statute and official roster establish administrative meaning and parentage, not machine-readable coordinates.

## Legacy identities and vintage

The four exact issue IDs resolve in baseline `data/geography/part-29.json` to Belize, Cabinda, Cacongo (Landana), and Buco Zau. Each feature is a single Polygon, ADM2 / Municipality, parent `framework:province:cabinda:fb67d098df5d`, source geoBoundaries gbHumanitarian, reference year 2018, and declares CC BY 3.0 IGO. The original 2018 geoBoundaries collection and metadata are retained with their exact hashes in `evidence-quality.json`. Its metadata describes 161 Angola ADM2 features and a 2018 boundary vintage; it is not a current 2024 source. The metadata credits “GADM and INE - see methodology, HDX” but provides a malformed HDX URL, so lineage to original national geometry remains a limitation despite the declared collection license.

The four names overlap four names in the statutory 2024 roster; Cacongo's label differs. This does not prove legal identity continuity or footprint persistence. The six other statutory names (Miconje, Massabi, Necuto, Tando Zinze, Liambo, Ngoio) do not occur as separate names among the four issue-scoped IDs. This does not establish absence from other Atlas records or from the land covered by those old polygons. The exact crosswalk is in `cabinda-municipality-crosswalk.json`.

## Search, completeness, license and neighboring granularity

The official IMA page supports the 10-name list but provides no municipality boundary files. The official Gazette's legal text/maps were not redistributed: the linked official PDF used in predecessor #460 is pinned by SHA-256 `dfaab2fa7059d8447aee3cab492deb94793971883b6a4998dc5353bf3d6e6e6a`; no open reuse license for the Gazette maps or a georeferenced derivative was established. Restore from the exact official URL recorded in the predecessor issue packet and verify that digest before inspection. Do not digitize/redistribute map-derived geometry absent rights and georeferencing instructions.

A current ArcGIS service titled “Nova Divisao Administrativa de Angola” was screened, but its item has no stated authority, source lineage or license; it is not used or retained as boundary evidence. UN SALB identifies Angola's national geospatial authority as IGCA but no public current Cabinda municipality dataset was found in the accessed catalog. IGCA is therefore the appropriate engineering follow-up for an authoritative data package and written reuse terms. No neighbouring Congo or DRC boundary data at a comparable municipality tier was verified. Law 14/24 gives Angola's national tier counts (21 provinces and 326 municipalities); this does not resolve cross-border edge topology or local completeness.

The retained geoBoundaries data is licensed under its metadata's CC BY 3.0 IGO declaration. The metadata itself warns that underlying source lineage is GADM/INE/HDX and its HDX URL is malformed. It is retained only as a historical comparator; it cannot establish current coverage. Official IMA page capture and site terms capture are described with exact hashes in `evidence-quality.json`; government site terms are not extended here to linked Gazette maps or derivative data.

## Engineering handoff and uncertainty

Obtain from IGCA or another competent Angolan authority: (1) the authoritative 2024/2025 municipality polygons, with source vintage, CRS, identifiers/codes and neighboring commune/province/country edge coverage; (2) explicit redistribution and derivative-work permission; (3) a legal identity crosswalk from the four 2018 shapes to the ten current units; and (4) change history and topology expectations. Then engineering can prepare a separate, reviewed proposal preserving old IDs and history, recording splits/retirements and parent updates, without importing until applicable release gates are met.

Unresolved: current ten-unit boundary geometry; legal identity and footprint continuity for every legacy ID; underlying 2018 geometry lineage; Gazette-map derivative rights; comparable neighboring-tier coverage; and coastal/cross-border topology. Structural counts or hashes cannot resolve these geographic questions. Stage remains research partial, implementation not proposed, geography unapproved.

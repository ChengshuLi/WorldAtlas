# Findings: Comoros settlement and locality sources

Research date: 2026-10-08 UTC. Scope: `atlas:territory:COM` and the three retained source-island members `Anjouan/Ndzuwani`, `Grande Comore/Ngazidja`, and `Mohéli/Mwali`. Parent evidence is issue #482 at the immutable commit recorded in `source-inventory.json`.

## Decision

No source inspected in this item qualifies as a currently reusable, authoritative, complete settlement gazetteer with coordinates or geometry, named administrative codes, explicit reuse permission, and documented settlement completeness. The best official leads are INSEED's 2020 EHCVM community-coordinate file and the 2023–2024 RGA-2 community data. Both are restricted or lack an open reuse grant; the 2020 survey is demonstrably sampled and incomplete. The RGA-2 metadata's coordinate and aggregation statements need clarification from INSEED and do not expose the actual village rows, coordinate granularity or a completeness crosswalk. Do not import, redistribute or treat their metadata as a usable coordinate layer.

This is a negative source-fitness result, not proof no source exists. An official, public locality point layer may be unpublished, separately held by INSEED or another ministry, or available under permission that was not found here.

## Authoritative source search

### RGPH 2017

INSEED's National Microdata Archive describes the 2017 population and housing census, national coverage, fieldwork from 2017-12-16 through 2018-01-26, and the ZD as the lowest geographic level of the cataloged data. It requires attribution but its catalog does not grant an open reuse license. Census population tables and the ZD-level statement do not establish that a named locality roster has coordinates or that ZD polygons/IDs can be reused as settlement locations.

The official catalog lists the 2020 report “RGPH04 - Rapport d'analyse - thème 8 : Migration et urbanisme.” Its NADA download endpoint is reproducible and was successfully retrieved; the previous WordPress upload URL now returned 404. No copy is retained because no redistribution license was identified. The report PDF has not been text-extracted in this packet, so no unverified report counts or detailed political wording are used here.

### EHCVM 2020

The INSEED catalog and variable dictionary explicitly define village names and island/prefecture/commune parent fields alongside village coordinates, accuracy and timestamps. The latitude metadata reports 320 valid and 55 missing cases; the paired longitude variable reports the same. The survey sampled 380 of the 2017 census ZD and interviewed 5,624 households. This is useful for independent candidate screening, but it is neither an exhaustive settlement roster nor a complete coordinate layer. The catalog footer says “Tous droits réservés” and no open license was found. No row-level survey data or coordinates were accessed or retained.

### RGA-2 2025 (campaign 2023–2024)

The current INSEED catalog describes island, prefecture, commune and village/locality variables, all three islands in its administrative study scope, a 964-ZD frame and community-level GPS collection. This makes it the strongest current official lead. However, the catalog also describes a mixed census/sample design, says geographic identifiers are aggregated for anonymity, requires an access request and research affiliation, forbids onward sharing without INSEED permission, and marks the material “Tous droits réservés.” The public metadata does not expose village rows, their coordinates, source codes, positional meaning, row-level completeness or a terms grant authorizing Atlas redistribution. Its island coverage explicitly describes the three islands under national administration; that administrative study frame must not be transformed into a physical-land or sovereignty conclusion. This source is a request-for-clarification lead, not an importable gazetteer.

### OCHA COD-AB 2019

The retained OCHA/HDX package is valid on 2019-12-05 and contains 3 ADM1, 17 ADM2 and 55 ADM3 administrative polygons with names, p-codes and parent assignments. HDX metadata identifies CC BY-IGO. The reproducible table in `administrative-crosswalk.csv` lists every island, prefecture and commune, and explicitly labels each record as an administrative unit, not a settlement. The COD-AB specification says a row is an administrative polygon; it allows village/locality as an ADM5 concept only where a country source provides that level. Comoros' retained package ends at ADM3. These polygons provide context for a future locality-to-admin match but not a settlement gazetteer.

### Volunteer candidate screen

The parent packet retains 565 HOTOSM/OSM features; 295 are unnamed, with a mix of 332 residential-area polygons and 233 named/unnamed point classes. It is ODbL and explicitly volunteer-sourced. This is a candidate-omission screen only and does not establish official settlement names, completeness, administrative remainder coverage or inhabited status.

## Island and neighboring granularity

- COD-AB has exactly three named ADM1 members: `KM1` Anjouan (Ndzouani), `KM2` Grande Comore (Ngazidja), and `KM3` Mohéli (Mwali). The crosswalk reproduces all 17 ADM2 and 55 ADM3 parent paths against those three members.
- Inspecting the retained OCHA ADM1 GeoJSON shows Anjouan and Grande Comore each encoded as a Polygon and Mohéli as an 8-part MultiPolygon. Those are source components, not an independent island inventory. No absent-island inference follows from the geometry encoding or the source's 2019 date.
- The prior evidence packet's three geoBoundaries 2017 island shapes reconstruct the current `atlas:territory:COM`; its reported symmetric difference is 2.635106764360453% and relative area change -0.08411396676023487%. This remains a cross-source comparison, not a coast accuracy test, legal boundary confirmation or exhaustive offshore-island proof.
- Prior evidence identifies Mayotte separately and warns not to infer political ownership from physical geography. INSEED's census and agricultural-study wording concerns the source's administrative/statistical population. It is not evidence that this Atlas composite should absorb another island or that any competing political claim is resolved.
- Island-level source names vary (`Moheli`, `Mwali`, `Mohéli`; `Ndzouani`, `Ndzuwani`; `Ngazidja`, `Grande Comore`). These are recorded as source names and aliases, not normalized as a political adjudication.

## Reproduction and interpretation boundaries

Run `python3 data/regional-review/comoros-settlement-source-20261003/reproduce.py --write` once to generate the administrative reference CSV; later run without `--write` to verify it. The script checks the predecessor archive's exact SHA-256, requires the 3/17/55 feature counts, validates parent chains and refuses to overwrite an existing CSV. It does not create settlement points, infer localities, repair geometry, test administrative legality or certify completeness.

The retained source archive is in predecessor issue #482; it is not duplicated here. Page response hashes in `source-inventory.json` identify the exact fetched public metadata response at the recorded retrieval time. They are not claims that a mutable webpage is an immutable official release. Direct restoration URLs and explicit access/reuse limits are recorded for each lead. No source with unverified license terms was copied into this packet.

## Unresolved findings and handoff

1. Ask INSEED for a public or explicitly redistributable village/locality gazetteer, with edition/validity date, stable village/admin codes, coordinate meaning and accuracy, all ADM2/ADM3 crosswalks, settlement completeness criteria, outer-island treatment and exact license/redistribution permission. The RGA-2 metadata page is the contact/access starting point; this packet makes no request on anyone's behalf.
2. Confirm whether the RGA-2 community-coordinate output is separate from protected household/agricultural records, what “aggregated” spatial precision means, whether all localities are included, and whether a non-sensitive generalized public derivative exists. Do not reuse microdata coordinates without written permission and a privacy review.
3. If an authorized national roster cannot be supplied, ask OCHA/HDX or INSEED for source lineage of the 2019 55 ADM3 units and for a named ADM5/locality layer, if maintained. Don't interpret an absent COD-AB ADM5 as proof localities are absent.
4. A future owner must match official localities to each 17 ADM2 and 55 ADM3 unit, account for unassigned/remainder names and duplicates, reconcile source name/code history, and test named offshore/islet coverage against an authoritative physical-island inventory. HOTOSM remains a screening source only.

## Disposition

Source research and the 75-row administrative crosswalk are complete as evidence-only partial work. The acceptance requirement for an authoritative reusable settlement gazetteer and a settlement-to-ADM2/ADM3 coverage reconciliation remains **unverified**. This packet does not satisfy regional certification or authorize changes to hierarchy, footprint, live data, publication or historical imports. The issue should remain open for the explicit source-owner and completeness handoff; use exactly `Refs #634` on a partial PR.

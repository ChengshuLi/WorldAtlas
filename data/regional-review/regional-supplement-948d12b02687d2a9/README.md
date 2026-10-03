# South-Central Pacific new named-land review — #526

## Work partition

This is the first of at most two focused evidence PRs for #526. This checkpoint covers the complete Phoenix Islands area and all 8 of its 8 assigned locations. PR 2 will cover the remaining 12 locations in the partial Northern Cook Islands, Cook Islands, Line Islands, and Pitcairn Islands scopes. The staged split follows the issue’s shared area scopes; it does not change any geographic boundary or member list.

PR 1 is partial work and therefore references, rather than closes, #526. The outstanding 12 assigned locations, four area reviews and source-policy gaps remain open for PR 2.

## Phoenix Islands findings

**The named island-group role is justified; source-family completeness is not certified.** The Kiribati-authored Phoenix Islands Protected Area (PIPA) Management Plan names Kanton/Abariringa/Canton, Birnie, Enderbury, Manra/Sydney, McKean, Nikumaroro/Gardner, Orona/Hull and Rawaki/Phoenix. It calls the Phoenix Islands one of Kiribati’s three island groups, distinct from the Line Islands and Gilbert Islands. The issue’s eight location names correspond to that official list.

The same plan separates the eight atoll/reef islands from the much larger PIPA protected property: 408,250 km² of ocean and terrestrial habitats, two submerged reefs, and seamounts. PIPA’s marine conservation perimeter is not a land location footprint. The plan says the Phoenix Islands have no permanent settlement and records a small caretaker population on Kanton in its 2009–2014 management era. That is dated management evidence, not a contemporary population count.

The OSM responses for all eight locations are already lawfully retained under ODbL in the repository’s macro-coverage source archive. The matching source-profile and decompressed raw hashes, original API URLs, retrieval date (2026-10-02), compressed byte counts/hashes, and full per-way metadata are recorded in phoenix-assessment.json. The full OSM extract families reconstruct **29/29 closed land components**, with no open chains or missing nodes; all 29 components are absent from existing location footprints. The independently retained GSHHG 2.3.7 comparison inventories **33 polygons** totaling a different amount of land per island group. Source vintage, shoreline generalization, exposed-rock interpretation and possible unmapped land remain unresolved.

| Assigned subject | OSM rings | OSM km² | GSHHG polygons | GSHHG km² |
| --- | ---: | ---: | ---: | ---: |
| Birnie | 1 | 0.515 | 1 | 0.596 |
| Enderbury | 1 | 6.149 | 1 | 7.179 |
| Canton/Kanton/Abariringa | 5 | 10.868 | 1 | 16.201 |
| McKean | 1 | 0.540 | 1 | 0.874 |
| Manra/Sydney | 1 | 9.099 | 1 | 11.767 |
| Orona/Hull | 18 | 7.534 | 16 | 11.000 |
| Nikumaroro/Gardner | 1 | 4.204 | 11 | 6.538 |
| Rawaki/Phoenix | 1 | 0.676 | 1 | 0.778 |
| **Total components** | **29** | — | **33** | — |

These counts are source-component inventories, not island quotas. Orona’s 18 OSM rings and 16 GSHHG polygons, and Nikumaroro’s 1-to-11 comparison, must not trigger automatic location splitting. Ring/polygon IDs, bounds, source versions, timestamps and measured areas appear in phoenix-assessment.json so each detached surface remains reviewable. No separate unnamed rock or submerged feature is silently added. No administrative remainder is identified.

## Parent findings and neighboring consistency

Every row in phoenix-assessment.json records the complete location → Phoenix Islands province → Phoenix Islands area → South-Central Pacific region → Polynesia → Oceania parent chain. The declared province and area each contain the same eight locations and use the same name. The area is supported as a broad physical island-group grouping. The issue’s source hints and Kiribati PIPA plan do not establish a separate civil “Phoenix Islands province.” Treat that repeated, coextensive tier as insufficiently justified pending a coordinated region-wide semantic decision. This packet does not edit the shared hierarchy.

Kiribati’s PIPA plan places the Phoenix Islands east of the Gilbert Islands and west of the Line Islands. That physical distinction is consistent with the three separate Kiribati island groups and with the published South-Central Pacific parent. No inter-region boundary inconsistency was found. The Line Islands are only partly reviewed in this issue and are deferred to PR 2.

## Sources, dates, licenses and restoration

- Republic of Kiribati, *Phoenix Islands Protected Area Management Plan 2009–2014*, linked as [UNESCO dossier document 105314](https://whc.unesco.org/document/105314), retrieved 2026-10-03. Its document index is [here](https://whc.unesco.org/en/list/1325/documents/). The dossier is state-party authored; no open reuse license is stated, so the PDF is not redistributed. Byte count and SHA-256 are in phoenix-assessment.json. Restore from the canonical document URL and record a new hash before reuse.
- UNESCO World Heritage Centre, [Phoenix Islands Protected Area](https://whc.unesco.org/en/list/1325/), retrieved 2026-10-03. Page hash is recorded in phoenix-assessment.json. No HTML or media bytes are redistributed; restore from the canonical URL and record its new hash/date.
- Kiribati, *National Biodiversity Strategy and Action Plan v2*, [CBD country document](https://www.cbd.int/doc/world/ki/ki-nbsap-v2-en.pdf), retrieved 2026-10-03. Hash and byte count are recorded; no PDF bytes are redistributed because no open reuse license was stated.
- OpenStreetMap, eight individual API map extracts enumerated in phoenix-assessment.json, each retrieved 2026-10-02. Retained compressed extracts preserve their historical bytes; each row gives exact compressed and decompressed hashes, URL, and profile hash. Licensed ODbL 1.0 with attribution © OpenStreetMap contributors. Restoration instructions: fetch that exact URL, preserve the response as a new immutable vintage, and require its decompressed SHA-256 to match the row before treating it as the same source. Do not overwrite a changed response.
- GSHHG full resolution 2.3.7 (released 2017-06-15), [project source](https://www.soest.hawaii.edu/pwessel/gshhg/), LGPLv3 or later. The per-location comparison inventory is included in phoenix-assessment.json; retained native-source records and their compressed/native/upstream archive hashes are identified there and in data/macro-improvements/macro-coverage-oceania/gshhg-extraction.json. Follow the extraction manifest to reproduce; a later GSHHG release is a new comparison.

All geographic evidence is kept separate from political ownership, historical affiliation, and date-valid attribute evidence. EU5 counts are not quotas, and the source vintages do not describe ancient or historical boundaries.

## Reproduction check

From repository root run:

    python3 data/regional-review/regional-supplement-948d12b02687d2a9/verify.py

The verifier checks all 8 retained OSM source archives, hashes and sizes, every coastline way and node reference, exact source-way and land-component inventories, all 33 GSHHG polygons, and the retained GSHHG record hashes. It verifies evidence integrity; it does not certify that a source is a complete modern shoreline or approve regional publication.

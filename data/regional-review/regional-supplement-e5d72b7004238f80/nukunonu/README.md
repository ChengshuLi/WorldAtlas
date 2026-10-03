# Nukunonu atoll evidence review — #520

Reviewed 2026-10-03. This packet is evidence and a proposed correction only. It does not change published parent membership, geometry, source policy, grid, or live records; it does not approve the region for imports.

## Result

**Nukunonu: correction-needed (proposed), with shoreline completeness unresolved.** The subject is the named Tokelau atoll, not a village, a political ownership claim, or 97 independent location units. The Government of Tokelau describes Nukunonu as the central of three coral atolls and reports 4.7 km². Its Villages page identifies the two main settlements as Fale and Motuhaga, linked by a concrete bridge; Motuhaga is a recent settlement. The page’s census figures are explicitly from 2001/2006 and are not current demographic evidence.

The archived OSM extract named by the source profile was found at `data/macro-improvements/macro-coverage-oceania/osm-2af0d96ae4f6.xml.gz`. Its decompressed SHA-256 exactly matches the profile’s `0b150bc8…e0dbad4`. All **97/97** `natural=coastline` ways in the extract form closed rings with no missing nodes or open chains, covering 5.482223456 km² in the repository’s recorded reconstruction. All 97 individual rings, their IDs, names where mapped, per-way OSM versions/timestamps, areas, and bounds are enumerated in `assessment.json`. The repository’s source comparison classified each ring as current source land absent from existing location footprints.

The independent GSHHG comparison identifies **21** full level-1 land polygons (4.833268655 km²); each partially matches current OSM land, while their partition/area differs from OSM. This supports a material shoreline/generalization discrepancy and does not certify either source as a modern complete reference. Reef/lagoon treatment, tidal exposure, unmapped dry land, and coastline vintage remain unresolved. Do not turn the retrieval bbox into a boundary or infer political ownership.

## Scope and parent findings

The frozen published parent chain recorded for this member is location → Tokelau province → Tokelau Archipelago area → Western Polynesian Islands region → Polynesia → Oceania. The province has two current locations and the area has three; this issue owns only Nukunonu (one member in each parent). Tokelau province is an administrative/territorial grouping; the area is a physical archipelago grouping. Whether “Tokelau Archipelago” and Tokelau’s three atolls are fully coherent as a physical area needs the coordinated parent-scope review. This packet leaves all shared parents and siblings unchanged. No inter-region boundary inconsistency is asserted.

No additional unnamed motu, detached territory, administrative remainder, or neighboring atoll is silently added. The whole extract envelope and every returned coastline ring were audited. The envelope is only a source-fetch extent. Official source descriptions establish two settlements but do not inventory every motu. The full extent and settlement/atoll distinction are therefore recorded without fabricating a complete official islet gazetteer.

## Sources and lawful reproduction

- Government of Tokelau, [About Tokelau / Geography](https://www.tokelau.org.nz/About+Us.html), retrieved 2026-10-03. Copyright Government of Tokelau; no open reuse license stated. Only findings and citation are retained here; no page bytes are redistributed. Revisit the canonical URL and record its retrieval date and content hash before later reuse. Its quoted 4.7 km² and physical description are contextual, not a survey-quality boundary.
- Government of Tokelau, [Villages](https://www.tokelau.org.nz/About+Us/Villages.html), retrieved 2026-10-03. Copyright Government of Tokelau; no open reuse license stated. Only findings and citation are retained; restore later by fetching the canonical URL, logging date/hash, and rechecking its dates and wording. The population details are 2001/2006 census vintage.
- OpenStreetMap, [API map extract](https://api.openstreetmap.org/api/0.6/map?bbox=-171.9144444,-9.2436111,-171.6544444,-8.9836111), retrieved 2026-10-02. Retained archive path and compressed/decompressed byte counts and hashes are in `assessment.json`. Licensed ODbL 1.0; attribution © OpenStreetMap contributors. For restoration, fetch the exact API URL, decompress the XML if gzip encoded, and require uncompressed SHA-256 `0b150bc8b2675fceeca0fca17661d5c373cc1381c4c7667b92b0e8cb4e0dbad4`; a live response can differ and must not replace the preserved historical bytes.
- OpenStreetMap, [copyright and license](https://www.openstreetmap.org/copyright), retrieved 2026-10-03. ODbL 1.0; see the page for attribution/share-alike terms.
- GSHHG level-1 shoreline comparison is an existing repository analysis; its dated source-input identity and per-polygon findings are inventoried in `assessment.json`. Reuse/restoration must follow the source manifest and license in the repository’s macro-coverage inputs. The independent comparison is not treated as legal or authoritative boundary evidence.

The underlying source-profile/archive record is from the WorldAtlas macro-coverage Oceania research. Source identity is `osm:named-land:tokelau-nukunonu`; source ID is `osm-api-2026-10-02`; profile correction follow-up is #501. Its source role is a current dry-land reference family, not an approved atlas tier or historical effective interval. EU5 counts were not used as a quota.

## Proposed next work

1. Keep the atoll as a single named-land subject, pending source-policy and regional semantic approval; do not split Fale/Motuhaga or the many motu into province-tier location subjects merely because OSM maps them separately.
2. Have engineering compare a policy-approved independent modern shoreline family against the 97 OSM rings, explicitly deciding reef-flat, lagoon, tidal and omitted-land treatment before integrating any footprint.
3. Coordinate the shared Tokelau province / Tokelau Archipelago parent review across all of each parent’s members; do not resolve it from this one member’s packet.
4. Keep political status, sovereign ownership and historical attributes separate from geographic containment. No historical imports are eligible until the full region is integrated, validated and published.

## Validation

Run `python3 data/regional-review/regional-supplement-e5d72b7004238f80/nukunonu/verify.py` from repository root. It checks retained archive hashes and size, complete OSM node references, all coastline ways closed and matching the 97-row assessment inventory, and the GSHHG inventory count. It does not certify the scientific correctness or policy suitability of either shoreline dataset.

The **Tokelau province** parent remains unresolved as a tier/boundary: the published hierarchy records one child, while this supplemental issue’s frozen parent scope declares two total locations with only one owned here. This discrepancy requires reconciling the underlying release/member snapshot before a complete parent claim can be made. This packet cannot certify a complete province polygon or the out-of-scope member. The **Tokelau Archipelago** area is broadly consistent with a physical grouping of three separated atolls, but its exact footprint and tier remain open; all three member reviews must be combined. Neither parent is changed here.

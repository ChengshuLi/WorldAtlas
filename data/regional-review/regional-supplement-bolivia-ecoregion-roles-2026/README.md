# Bolivia physical ecoregion role follow-up (#594)

This packet accounts for all nine exact assigned `atlas:physical` IDs, both complete predecessor province polygons (Cordillera and Velasco), and all seven RESOLVE ECO_ID features. It proposes metadata corrections only. It does not alter IDs, geometry, parent chains, the published partition, source archives, or live data.

## Sourced disposition

Every current row says `source_role=Province` and carries the country-specific administrative-tier selection rationale (“Named local administrative territories…”). Yet the `source_id` is `resolve:<ECO_ID>`, its name combines the predecessor province and ecoregion, and its footprint is a clipped intersection of a 2015 Bolivia ADM2 source polygon and a RESOLVE natural ecoregion. The 2017 RESOLVE item description calls the dataset terrestrial ecoregions and states its boundaries represent natural/ecological systems, rather than political units. Its service feature properties expose `ECO_ID`, `ECO_NAME`, `BIOME_NAME`, `REALM` and `LICENSE`; all seven retained mapped features declare CC BY 4.0. These sources support a named ecological portion identity, not a province or other administrative unit.

The 2015 Bolivia ADM2 source contains 110 features: 108 correspond directly to current province locations; Cordillera and Velasco are represented by these nine physical portions (five and four). Thus the retained source roster is fully accounted for with no unrepresented ADM2 polygon. That accounting does not make the nine portions administrative children. The 2015 source metadata declares Public Domain/free access and was built in 2023, but its canonical-role field is blank. The official GeoBolivia catalog record endpoint returned HTTP 403 in parent research; no current official row-level administrative crosswalk is asserted.

## Correction proposal

For every listed ID, remove the unsupported administrative “Province” role and administrative-tier selection rationale. Record the actual derivation in `location_basis` and `selection_reason`: the named RESOLVE ECO_ID feature intersected with the named 2015 ADM2 predecessor polygon, selected as physical/ecological geography rather than an administrative unit. Retain the stable physical ID, `source_id`, current footprints and Santa Cruz parent pending engineering review. Keep `administrative_level=Named physical region portion` as a descriptive tier pending an explicit model decision. Use a canonical non-administrative source-role value only if engineering confirms the vocabulary; if the role field is administrative-only, leave it unset rather than assigning a false tier. Replace the selection rationale with the ecological/physical basis and state clearly that it is not an administrative selection.

Whether these ecological portions belong in the published location collection at this tier remains unresolved. The source supports a real ecological identity but does not establish that the model's tier, parent, or membership is complete and suitable. No hierarchy, parent or tier mutation is proposed here.

## Whole-scope checks

`assessment.json` accounts for each exact assigned ID once and gives its source mapping, current metadata, complete parent chain, geometry component/ring counts, source/current overlay, current contacts, land-screen limits, settlement status and remainder/island/water uncertainty. Across the nine subjects, the seven ecoregions map as ECO_ID 476 (1 portion), 504 (1), 523 (1), 529 (2), 567 (1), 569 (1), and 584 (2). Five portions derive from Cordillera and four from Velasco.

The pinned EPSG:6933 overlay reports that the seven selected ecological features, clipped to the two complete predecessor polygons, cover each predecessor polygon to numerical precision. The current union differs from the source Cordillera polygon by 393.563 km² (0.47%) and from Velasco by 200.774 km² (0.29%). Per-fragment expected-area coverage ranges from 93.300% to 99.830%; the detailed results and all 36 candidate fragment pairs are in `derived-portion-audit.json`. These are scale/vintage diagnostics, not evidence to relocate shared boundaries. Temporary `ST_MakeValid` repairs are used for overlay only; original input bytes are untouched.

The nine current geometries have between 1 and 18 polygon components and up to four interior rings. The 2017 GSHHG screen reports zero level-1 centroid hits per fragment while each representative point falls on its screen's level-1 land polygon. This does not prove complete named land, islands, inland hydrography or settlement coverage. All nine have an explicit unresolved settlement finding; no complete, dated and lawfully reusable settlement inventory was crosswalked. Official unnamed administrative remainder and current province/physical-role data also remain unresolved.

Current exact within-Bolivia fragment neighbor pairs match the nine source-derived pairs in the overlay. Current map contacts include neighboring Brazil and Paraguay features for some assigned portions. Parent evidence did not perform source-to-source external border validation; these contacts alone do not establish inconsistency. Any future boundary proposal must coordinate with regional integration #489 and affected neighbor owners. No cross-region inconsistency is asserted or changed in this packet.

The full location parent chain is preserved and verified for each row: Santa Cruz province → Bolivia area → Western South America region → Western South America subcontinent → South America continent. Political reference-owner and history attributes are not used as evidence of ecology or physical coverage.

## Sources, rights and reproduction

`scope.json` pins the exact nine IDs, current-main baseline and source/input file sizes and hashes. `sources.json` records canonical source references, dates, licenses, retained-byte paths/hashes and restoration steps. Licensed source files remain in the merged #490 packet; they are not copied or edited here. The GeoBolivia source record's access failure and the resulting uncertainty are retained explicitly.

From repository root:

```sh
python3 data/regional-review/regional-review-2d6fa291e9384c2f/verify.py
python3 data/regional-review/regional-supplement-bolivia-ecoregion-roles-2026/reproduce-overlay.py
python3 data/regional-review/regional-supplement-bolivia-ecoregion-roles-2026/verify.py
```

The overlay reproducer reads the parent packet's original source bytes, scans all current geography parts for the exact assigned IDs and writes only this packet's `derived-portion-audit.json`. The verifier refuses changed pinned baseline/input bytes, mismatched IDs/roles/source mappings/parent chains or incomplete source accounting. Do not run parent generators for this packet; their original outputs remain untouched.

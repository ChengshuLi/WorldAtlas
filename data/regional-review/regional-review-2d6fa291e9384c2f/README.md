# Issue #490 — Western South America interior batch 1

## Scope and disposition

This packet accounts for all 211 exact member IDs: all 117 current Bolivia locations and 94 Colombia municipalities. Bolivia is a complete country scope; Colombia is partial (94/1,122 municipalities) but contains two complete department cohorts, Nariño (64) and Chocó (30). The packet also records all 11 issue-pinned parent cohorts and the complete ancestry chain of every location.

The source inventory reveals a mixed Bolivia location tier. The pinned 2015 Bolivia ADM2 source contains 110 official-source province polygons. 108 locations match 108 unique ADM2 IDs and exact names. The two other source polygons are Cordillera and Velasco; the current hierarchy substitutes nine ecoregion portions over those two predecessor provinces. The seven distinct RESOLVE Eco_IDs in these names are ecological features, not political/administrative units. The current Atlas metadata nevertheless marks all nine as `source_role=Province` and gives an administrative-unit selection rationale. Those nine exact rows are classified `correction_needed` for source-role/selection rationale. The other 202 direct Bolivia/Colombia source rows are `insufficient_evidence` for full geography approval. No rows are marked approved, and no Atlas data have been changed.

## Administrative sources and complete membership accounting

- **Bolivia ADM2:** The full pinned 110-feature geoBoundaries layer is retained compressed with raw/compressed hashes in `sources.json`, under the source metadata's Public Domain terms and attribution. Metadata identifies GeoBolivia as the underlying source, labels the boundary ADM2/Province, gives boundary vintage 2015, source update 2023-01-19, build 2023-12-12, and declares 110 units. The published canonical-role field is blank. The 108 assigned direct rows match unique source IDs and exact names. The other two IDs, Cordillera and Velasco, are each linked as predecessors to their five and four current portions respectively. This exhausts the full 110-unit source roster: no additional source province remainder is left unaccounted for.
- **Bolivia ADM3 context:** The full 339-feature 2015 GeoBolivia-derived ADM3 layer is retained with hashes. It is only a nested granularity/administrative-context reference; the source has no row-level parent field and does not replace a current official crosswalk or settlement catalogue.
- **Colombia ADM2:** All 94 assigned rows match distinct DANE-declared 2020 geoBoundaries shape IDs and exact names. The 1,122-unit source is reused from the merged #492 evidence packet rather than duplicating its 74.8 MB compressed copy. It is CC BY 4.0 with DANE attribution. The DANE DIVIPOLA MGN 2024 service metadata exists, but its feature rows and reuse terms were inaccessible in the earlier service investigation. No current official row-level reconciliation is claimed.
- **Parents:** The complete location-to-parent chain is stored per row. The Bolivia source supplies provinces (ADM2); the Atlas parent cohorts are department groupings. Colombia rows are municipal units under the two complete department cohorts. Current official DANE department/municipality rows and present department role checks remain open.

## Bolivia physical portions: source, fit and correction proposal

The nine labels contain a province name (Cordillera or Velasco) and an ecoregion name. Their `resolve:<number>` source suffixes are **RESOLVE `ECO_ID` values**, not GitHub issue numbers. The retained REST response contains the seven exact ecozone polygons mapped by those IDs. The live ArcGIS item's license and each returned feature's `LICENSE` field both state CC BY 4.0. Its item description says ecoregion boundaries are natural/ecological rather than political boundaries.

The reproducible overlay intersects the full 2015 GeoBolivia-derived Cordillera and Velasco province shapes with their matched RESOLVE ecozone polygons in EPSG:6933 equal-area coordinates. Seven original ecoregion features (five intersecting Cordillera, four Velasco) cover each repaired source predecessor area to numerical precision. This supports the *derivation* of the nine portions; it does not make the ecozones administrative provinces. The nine current portions reproduce the same 9-pair source-derived internal adjacency graph.

Because some raw ecoregion and current fragment polygons contain invalid topology (nested shells or self-intersections), `ST_MakeValid` is used only inside a temporary local overlay. Original input bytes and current baseline geometry are preserved. The per-fragment expected/current area overlap ranges from 93.30% to 99.83%. The current nine-fragment union differs from the source predecessor provinces by 393.56 km² (0.47%) for Cordillera and 200.77 km² (0.29%) for Velasco in this equal-area screen. These discrepancies need scale/precision review; they do not support a boundary relocation without authoritative, topology-valid source evidence.

Concrete proposal for engineering integration: correct the nine source-role and selection-reason records to describe a **physical ecoregion portion** with both its predecessor province source ID and RESOLVE ECO_ID, and evaluate whether that identity/tier belongs in the published location collection. Preserve the stable IDs, source claims, original footprints and full administrative predecessor source data during review. A separate bounded correction follow-up is linked below.

## Settlements, land, islands and remainders

Every location has a row-level unresolved settlement finding. There is no complete current, lawfully reusable official settlement inventory reconciled to these 211 exact IDs. DANE's 2013I settlement service is an older lead; its feature rows and license were not obtained. Bolivia's retained province source is not a point-settlement catalogue, and the GeoBolivia source catalog returned HTTP 403. A named-town screen cannot be inferred from polygon identity or feature counts.

GSHHG 2.3.7 (2017, LGPLv3+) was independently screened across all 211 assigned representatives. 210 fall within a level-1 physical-land polygon; 12 assigned current polygons contain one or more full-resolution level-1 polygon centroids. The one representative-point no-hit is Bahía Solano (Mutis), Colombia, at `[-77.338639, 6.403750]`; the point is inside its current Atlas polygon. This is a screen lead only, not evidence that the location is water or that any footprint is wrong. The 72 complete relevant GSHHG records are retained with hashes. GSHHG cannot certify every island, inland lake/island, hydrography, named component, detached territory, settlement or administrative remainder. Per-location component and ring counts are recorded but are not treated as a completeness proof.

## Neighbors and coordination

For Bolivia, exact consecutive-coordinate source/current edge graphs have 293 province-level neighbor pairs each, with no coarse graph difference after mapping Cordillera and Velasco to their nine portions. The current location graph has 312 exact internal pairs, including physical-fragment boundaries. For the 94 Colombia locations, both the full-source and current exact-segment graphs have 227 internal assigned pairs and no pair-set difference.

The current graph also records exact contacts to neighboring country locations: Bolivia has 56 current cross-country contact pairs to Brazil, Paraguay, Peru, Argentina and Chile; the Colombia subset has 15 to Ecuador and Panama. These are candidate contacts in the current geometry graph. This packet did not perform exact adjacent-country source-to-source border comparisons, so it makes no claim of an inter-region discrepancy or a cross-border boundary correction. The exact contacts and open comparison requirement are recorded for regional integration in #489. No shared boundary was edited.

## Sources, uncertainty and reproduction

`sources.json` records canonical URLs, publishers, source/vintage dates, stated licenses, byte sizes/hashes, access failures and restoration instructions. The exact RESOLVE REST request and response hash are in `resolve-query-receipt.json`. The 2015 Bolivia ADM2/ADM3 inputs are lawfully retained under source-declared Public Domain terms; ecoregion features under CC BY 4.0; the GSHHG extract under LGPLv3+; the Colombia DANE-declared raw source is reused from an already merged packet under CC BY 4.0. The GeoBolivia catalog's HTTP 403 and inaccessible DANE feature rows are not filled by assumption.

From a fresh current-main checkout containing the previously merged Colombia source and GSHHG archive/member restored to the exact hashes in `sources.json`:

```sh
python3 data/regional-review/regional-review-2d6fa291e9384c2f/audit_bolivia_derived_portions.py
python3 data/regional-review/regional-review-2d6fa291e9384c2f/audit_bolivia_neighbors.py
python3 data/regional-review/regional-review-2d6fa291e9384c2f/audit_colombia_neighbors.py
python3 data/regional-review/regional-review-2d6fa291e9384c2f/screen_gshhg.py /path/to/gshhs_f.b
python3 data/regional-review/regional-review-2d6fa291e9384c2f/build_assessment.py
python3 data/regional-review/regional-review-2d6fa291e9384c2f/verify.py
```

Reproductions only write into this packet or private temporary files and never mutate baseline geography. Exact-segment and point-in-land screens are evidence leads, not geographic approval or certification.

## Bounded follow-ups

- **Physical-role correction:** blocked child issue [#594](https://github.com/ChengshuLi/WorldAtlas/issues/594) identifies all nine fragments, their two predecessor provinces, source `ECO_ID`s, exact role mismatch and the temporary-overlay caveat. Engineering decides any published metadata/tier change after integration review.
- **Authoritative data restoration:** blocked child issue [#595](https://github.com/ChengshuLi/WorldAtlas/issues/595) binds the exact 211 IDs and seeks current Bolivian administrative/settlement data, DANE MGN 2024 and licensed dated settlement evidence, plus authoritative land/remainder records where available. It links to #587 without expanding that issue's separate 194-ID scope.

This packet does not approve Western South America or enable historical imports. Engineering must integrate supported findings and validate/publish the full regional branch before location-attribute research imports are eligible.

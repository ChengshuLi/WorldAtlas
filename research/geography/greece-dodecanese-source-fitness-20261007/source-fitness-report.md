# Greece Dodecanese/Aegean source fitness assessment

**Issue:** [#1367](https://github.com/ChengshuLi/WorldAtlas/issues/1367)
**Assessment date:** 2026-10-07 (UTC)
**Scope:** `gap-source-batch:6dcdd6a83a01e92e4d85ed5c` — all 46 complete components, all 11 source contacts, all 25 numeric rows, 7 demonstrated local-construction contradictions, and 18 retained numeric unknowns.
**Outcome:** limited to reproducible historical source-relative context; insufficient alone to establish authoritative 2010 municipal boundaries, approve any regional geometry, or classify current dry land.

## Findings

The original consumed input is geoBoundaries `gb:GRC:ADM3`, recorded as a simplified Greece ADM3 municipality product. The committed compressed source payload was restored from its immutable Git blob and decoded without reserialization: **376,781 encoded bytes**, SHA-256 `55dcb304944675e95c3530f02b71da019a6f647d38300cf1b7a337659fa87b5b`; **1,263,212 decoded bytes**, SHA-256 `72179d50a8a85aa9fecf996761f905db9e8a59f4eb882f8481f88651692b7e18`; **326 features**. All 11 scoped contact identifiers were found by exact `shapeID` in the original payload. Their names are retained in `inputs/source-access-and-claims.json` and full features in the pinned complete handoff.

The pinned administrative metadata says 2010 represented year, source-data update 2023-02-10, build 2023-12-12, and attributes the source to “geoBoundaries, Wikimedia Commons.” It reports `boundaryLicense` as CC0 but also carries a `licenseDetail` stating sources 2 and 3 are CC BY 3.0. This record does not expose enough local source lineage to identify which official Greek boundary record supports each feature; license application to this simplified product and derivatives is unresolved. The metadata's full-geometry URL and the actually consumed simplified-geometry URL are different assets and must not be conflated.

The strongest same-purpose historical comparator found is the Greek GEODATA/OKXE catalogue entry **“Όρια Δήμων (Καλλικράτης)”**. Its catalogue description calls it Kallikratis municipality boundaries and says v1.1 is a corrected version of v1.0 posted 2010-06-28. Search/index content was accessible on 2026-10-07, but direct catalogue opening failed in this review; no official geometry was downloaded or inspected. The earlier dated [#1006 comment](https://github.com/ChengshuLi/WorldAtlas/issues/1006#issuecomment-6000438992) reports HTTP 404 for the linked ZIP. Thus, this is a strong official source lead, not evidence of a completed geometry comparison. [GEODATA/OKXE catalogue entry](https://www.geodata.gov.gr/el/dataset?groups=boundaries&organization=okxe&res_format=shapefile&res_format=wms&tags=%CE%B4%CE%B9%CE%BF%CE%B9%CE%BA%CE%B7%CF%84%CE%B9%CE%BA%CE%B1-%CF%8C%CF%81%CE%B9%CE%B1&tags=%CE%BA%CE%B1%CE%BB%CE%BB%CE%B9%CE%BA%CF%81%CE%AC%CF%84%CE%B7%CF%82)

The Ministry of Interior's 2024 structure publication says Greece's Kallikratis administrative division took effect on 2011-01-01 and comprises 332 municipalities. That provides nationwide historical context. The contrast between this count and geoBoundaries' metadata count of 326 does **not** by itself identify omitted municipalities or boundary errors: the sources describe different published products and their counts alone do not yield an exact feature crosswalk. [Ministry of Interior publication](https://www.ypes.gr/wp-content/uploads/2024/06/STRUCTURE-OPERATION-LRD-ENGLISH-VERSION-2024.pdf)

ELSTAT's 2011 Census page publishes statistical tables and links an interactive census map. It is useful statistical context; this review found no boundary-purpose statement there that would make those census polygons legal municipality evidence. They should not substitute for the OKXE/official boundary geometry or local legal records. [ELSTAT 2011 Census](https://www.statistics.gr/en/2011-census-pop-hous)

The GSHHG 2.3.7 physical comparison is a generalized, heterogeneous-vintage coastline reference. Its retained per-query records help explain the physical comparison, but do not establish modern dry land, ownership, municipal law, or a repair. The 11 source contacts and positive-neighbor relations are identity/context signals only. A missing mapped-water intersection is not evidence of dry land.

## Complete-family preservation

The complete-family accounting impact is **216,181,559.43068022 m²** as recorded. It is a bookkeeping total for the complete family, not approved dry land. The scope file retains all 46 component IDs, 11 contact IDs, seven construction contradiction IDs, 18 unknown numeric IDs, the positive-neighbor list, and original family/routing stream hashes. The pinned handoff retains every original routing row, physical query row and support, numeric source row and binding, candidate pointset, original source contact feature, and current contact feature. The closure inventory records 99 preflight inputs (105,046,993 bytes aggregate; largest file 11,246,700 bytes) within configured preflight descriptor and size limits. No global calculation or subset diagnosis was rerun.

Related open work was freshly captured in `related-work/`: #819's full island census crosswalk roster, #1081's Anatolia provenance scope, #1006's broader Greek roster, #1002's boundary restoration, and #1007's special/weak-parent records. The exact 11 contact IDs overlap #819 and #1081, whose owned paths differ from this packet; their pins, unknowns, comments and rosters are preserved. #1006 covers a different roster reconciliation. This report does not revise or complete those scopes.

## Bounded source-fit conclusion and next evidence

The consumed geometry is fit for reproducing the existing historical contact/identity context and for source-relative comparison with explicit limits. It is **not fit as the sole authority for resolving the numeric contradictions, certifying the 2010 legal municipality boundary, approving regional geography, or establishing current dry land**. No component-specific error or omission is proven here.

A future authoritative comparison would require an obtainable, versioned official Kallikratis geometry or the underlying approved local administrative-boundary records, followed by an exact feature/identifier crosswalk and boundary-purpose review for all 11 contacts. Separately, preserve and resolve every numerical and physical prerequisite in the 46-component handoff. Any repair proposal needs its own bounded engineering review and inter-region/authority checks. The 18 numerical unknowns remain open.

## Reproduction and source inventory

- The lossless source and full family closure are in `inputs/greek-complete-source-ready-handoff.json`; the extraction/verification lineage is in `inputs/input-lineage.json`.
- Original source metadata, source blob, route report, numerical report, physical report, and current contact feature container are pinned by commit/path/whole-file SHA-256 in `evidence-quality.json`.
- The source output records official-source access and unavailable-resource limits in `inputs/source-access-and-claims.json`.
- Run `python3 research/geography/greece-dodecanese-source-fitness-20261007/tools/verify-source-identity.py` from the repository root to restore source bytes and verify all 11 IDs against the 326-feature source and pinned current contact file.
- Run `node scripts/evidence-quality.mjs research/geography/greece-dodecanese-source-fitness-20261007/evidence-quality.json .` from the repository root to verify evidence byte bindings.

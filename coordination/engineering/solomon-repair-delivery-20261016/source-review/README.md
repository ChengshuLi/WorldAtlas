# Solomon ADM1 source and retained-exclusion review

Completed 2026-10-16 for issue #2215, package `gb-SLB-ADM1--repair-evaluation` at accepted commit `a5f0214a899db981c5e5c0a6974aa8d3a76e1b41`. Read-only investigation; no repository changes or ownership claim.

## Result

All 3,925 selected literal native centers in 1,698 intervals have exactly one covering feature in the complete original ten-feature Solomon ADM1 product, and that feature is their recorded target. No uncovered centers, cross-owner covers, multiple covers, or Honiara covers occurred. All ten original and current features are valid and have zero holes. The original ten-feature family has only one nonempty pairwise intersection: Honiara/Guadalcanal share a MultiLineString boundary with zero positive area.

Counts by target: Temotu 390; Guadalcanal 150; Central 532; Malaita 266; Isabel 572; Makira 366; Choiseul 286; Rennell and Bellona 225; Western 1,138. Honiara has zero selected cells and remains an explicitly reviewed competitor: owner 39705, source index 55525, source ID `gb:SLB:ADM1:17018030B49873759306190`.

Current Honiara also covers zero selected centers. Each current sibling covers zero centers allocated to another selected target. All nine exact current parent IDs match selection. Every original/current geometry pair differs, so none should be described as an unchanged polygon or exact source restoration without stating the operation.

## Source custody and method

The complete original gzip is 33,558 bytes, SHA-256 `bb5015f3111992aaed331dd9eecad792c611d5c6bd6513a7d1f3fd04f82d15c8`. Its decoded original is 93,632 bytes, SHA-256 `418f5f1aeaab5f63d240219d1a78efda66e6ceb35ee1f35345d6e4e55fa0798c`. Its declared CRS is `urn:ogc:def:crs:OGC:1.3:CRS84`.

Custody path: `coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-SLB-ADM1-000.bin.gz`. The catalogue identifies the consumed simplified product, not the full-resolution URL appearing in current feature metadata: https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/SLB/ADM1/geoBoundaries-SLB-ADM1_simplified.geojson . Recorded year 2021 is a represented-year claim, not an independently verified effective date. Natural Earth credit/Public Domain metadata and the separately retained geoBoundaries derivative CC BY 4.0 attribution terms must both remain visible.

Native centers use longitude `(x + 0.5) / 262166 * 360 - 180` and the retained literal row-latitude bytes, decoded SHA-256 `66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23`. Independent computation used Python 3.12.14, NumPy 2.3.5, Shapely 2.1.2, GEOS 3.13.1. No make-valid, buffering, snapping, union normalization, or geometry replacement was used.

## Retained restrictions and interpretation

- No current SLB feature has `topology_reconciled`, `residual_overlap_repair`, or `display_geometry_repaired`. No SLB-matching entries occur in Oceania `location_changes`, `location_metadata_changes`, or `pixel_geometry_findings`.
- `data/geographic-decisions/oceania.json` location-review entries 35 and 36 remain open with empty flags. Their open semantic status is preserved; this check supplies no tier/granularity certificate or import/publication authority.
- Temotu remains the exact existing administrative target and parent. The separate unresolved Santa Cruz Islands area convention is preserved; neither a historical provincial name nor this source test proves coextensiveness or authorizes reparenting.
- Makira issue #1604 corrects a provider product-checksum algorithm and preserves the specific fifteen previously unqualified physical pointsets. It is not blanket approval, a new ban on every Makira native cell, or evidence that these 366 selected centers intersect those fifteen pointsets.
- #1607 is a Temotu verification-vintage/custody correction. #1327 concerns separate verifier output/control behavior. Neither changes source meaning or grants geographic approval.
- Original Honiara is required as a complete-family competitor. Current Honiara is also retained exclusion context. Neither produces a selected-center exclusion in this independent probe.

## Primary territorial context

The Ministry of Provincial Government's posted Provincial Government Act 1997, section 3(1) and Schedule 1, distinguishes the provinces from Honiara and explicitly excludes Honiara from Guadalcanal. Schedule 1 provides the nine provincial envelopes and section 3 distinguishes their offshore extent. This contextual evidence supports keeping Honiara separate; it is not a license to extend this land-only package into water.

https://www.mpgis.gov.sb/legislation/6-provincial-government-act-1997/file.html
https://mpgis.gov.sb/provincial-governments.html
https://mpgis.gov.sb/guadalcanal.html

The Honiara City Act 1999 refers to the city boundary plan deposited with the Surveyor-General. Consequently, generalized geoBoundaries coordinates are not asserted to be cadastral or legally exact. No new current-law certification requirement is imposed on the bounded source-relative claim.

https://parliament.gov.sb/sites/default/files/legislation/Acts/1999/THE%20HONIARA%20CITY%20ACT%201999.pdf

## Precise remaining limits

This review proves source-relative membership and the retained ten-family exclusion checks only. It does not execute native owner-zero conservation, accepted-patch composition, full global source competition, or physical-source qualification. Those are the author's separate execution checks. It does not establish present physical shoreline truth, legal ownership, current statutory polygon accuracy, historical intervals, or publication eligibility. No selected-cell exclusion is recommended solely from this source review.

## Artifacts

`source-geometry-review.json`: original-family, per-owner and native-center checks.
`current-exclusions-review.json`: current feature identities, parents, flags and retained semantic reviews.
`check_source.py` and `check_current.py`: exact independent scratch probe code.

The probe scripts use scratch paths and write exclusively to fresh report paths; they are review artifacts rather than a new production entry point.

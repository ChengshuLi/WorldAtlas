# Scoped source and territorial assessment

Assessment date: 2026-10-06 (America/Los_Angeles). This is an additive reproducibility/source-context follow-up for the exact eight #1160 USA ADM2 subjects. It does not reopen their historical analysis or propose boundary edits.

## Identity, tier and parent crosswalk

The exact source-key crosswalk is Census GEOID `13` + three-digit county code. The retained Census records name the state code `13`, match the eight Atlas names and IDs, and carry `LSADC=06`; the Census TIGERweb layer is explicitly “Counties (or statistically equivalent entities).” Atlas source metadata identifies USA ADM2, 2018 reference vintage, and the shared Georgia parent `framework:province:georgia:99c5fb82481b`. The eight values and their source properties are reproduced in each `runs/<run-id>/eight-county-comparison.json`.

| Census GEOID | County | Atlas ID suffix | Role in this bounded comparison |
| --- | --- | --- | --- |
| 13039 | Camden | `52423323B71362647483761` | Georgia coast screen |
| 13051 | Chatham | `52423323B68249799438553` | Georgia coast screen |
| 13127 | Glynn | `52423323B35006791438696` | Georgia coast screen |
| 13179 | Liberty | `52423323B31615661575159` | Georgia coast screen |
| 13191 | McIntosh | `52423323B58673559392327` | Georgia coast screen |
| 13231 | Pike | `52423323B93853380479562` | Interior control |
| 13249 | Schley | `52423323B40186233786127` | Interior control |
| 13273 | Terrell | `52423323B62158301450735` | Interior control |

These are county-tier administrative subjects under the same state parent, not eight subdivisions of a coastal macro-region. The roster is complete for the issue's declared eight IDs only. The 2026 query requested exactly these eight GEOIDs and returned eight records; it does not prove Georgia's complete county roster, adjacency coverage, municipal granularity or broader regional coverage. The 2018/2025 comparison files cover their retained Georgia/Kentucky collection, but this packet does not certify a complete state inventory from them.

## Source vintages and retained evidence

The following source objects remain unchanged in the prior packets. Their exact source hashes and byte counts are in this packet's `input-pins.json` and the prior evidence receipts. No source was downloaded again for this erratum.

| Role | Source vintage and retrieval | Retained location and limitation |
| --- | --- | --- |
| Atlas's inherited geometry/source identity | geoBoundaries USA ADM2 release states boundary year 2018; metadata records source-data update 2023-01-19 and build 2023-12-12. Retrieved 2026-10-05 in prior evidence. | Full and simplified variants, metadata, notice and crosswalk are preserved under the linked #981/#1154 evidence. The #1160 comparison does not read either variant, so it cannot say which one the Atlas footprint represents. |
| Census 2018 comparator | January 1, 2018 TIGERweb county layer; retrieval 2026-10-05T14:21:09.552Z. | `data/regional-review/regional-review-528e53393a4376b4/source/census-2018/georgia-kentucky-counties.geojson`; used for dated identity and area screening. |
| Census 2025 comparator | January 1, 2025 TIGERweb state/county layer; retrieval 2026-10-05T14:21:50.061Z. | `data/regional-review/regional-review-528e53393a4376b4/source/census-2025/georgia-kentucky-counties.geojson`; Census's 2025 page dates its boundaries and names to January 1, 2025 and states release on September 23, 2025 ([official release page](https://www.census.gov/geographies/mapping-files/2025/geo/tiger-line-file.html)). |
| Census 2026 comparator | TIGERweb current MapServer layer 82 describes “Counties (or statistically equivalent entities); January 1, 2026 vintage.” Exact eight-feature response and metadata were retrieved 2026-10-05T15:32:01.777Z. | `data/regional-review/coastal-reference-check-428/source/census-2026/`; query receipt pins response SHA-256 `c09e62479268b4ee8b986a66768d5dea821b4e667d9d446a78d5304076c2e717` (873,257 bytes). The retained metadata file is a one-final-LF-normalized derivative, not proven raw metadata-response bytes; its receipt and both hashes remain preserved. |
| Census county code/use authority | Retained 2025 TIGER/Line technical documentation and LSAD code reference, retrieved 2026-10-05. | `data/regional-review/coastal-reference-check-428/source/authorities/`. The official [2025 technical-documentation index](https://www.census.gov/programs-surveys/geography/technical-documentation/complete-technical-documentation/tiger-geo-line/2025.html) links the retained technical document. Census states that 2025 boundaries and names reflect January 1, 2025; the technical documentation limits TIGER/Line's purpose to statistical collection/tabulation, disclaims positional/attribute accuracy, and says it is not a jurisdiction determination or legal land description. |

The original #1152 issue pins are preserved exactly: 57 distinct whole-file source/data inputs with their declared hashes; the prior runner and input inventory are pinned too. The new runner reads those historical bytes from immutable commit `a37ad37b94168f9b458617489a702bbb72afbd3d`, not changed files from newer `main`, and records the separate fresh-main claim base `bd3b4ab860f11320717c354b10378c9972726373`. The shared geometry helper, world index and every member named by that index are among the exact source pins. The checks' success confirms those specific bytes and calculations; it does not transform the source into legal boundary authority.

## Geographic findings and uncertainty

The retained 2018/2025/2026 records agree on all eight county names, GEOIDs, Georgia state code and county tier. Atlas metadata keeps all eight under the Georgia parent. The 2026 endpoint identifies Census as source and returns a complete eight-of-eight query response for this issue scope. Source-vintage comparison reproduces the earlier results; the five coastal Atlas-versus-2026 IoUs are approximately 0.7703 (Chatham), 0.8642 (Camden), 0.7876 (Glynn), 0.8833 (Liberty) and 0.8343 (McIntosh), while the three interior comparisons range approximately 0.9819–0.9889. Census 2025/2026 pairs are unchanged or extremely close in the retained outputs. These are EPSG:6933 equal-area statistical screens with invalid comparator repair in memory only; no repaired geometry is written.

The lower coastal overlap is consistent with differences in water/coastal extent, source generalization or other representation choices, but the evidence does not identify which cause applies. The source materials do not adjudicate tidal water, marsh, submerged areas, offshore islands or each county's legal shoreline. Census TIGER/Line is explicitly statistical and carries no positional-accuracy warranty. The 2026 source does not declare the AREAWATER unit in the retained layer metadata, so any quotient using it remains conditional and must not be described as a confirmed area share.

geoBoundaries metadata labels the 2018 source “Public Domain,” while its separate product notice assigns CC BY 4.0 to project code and derivative works and requires attribution. The applicable terms for the underlying/derived boundary bytes remain unresolved in the retained #981 findings. The source variants are not copied here; restore and inspect the existing versioned source files and notice through the source references in `input-pins.json` before any reuse. Census bytes are retained with source attribution and the official statistical-use/no-warranty notice; this packet does not provide a new legal reuse determination.

No candidate correction follows from the IoU pattern. If future work proposes a boundary change, it needs authoritative Georgia/county survey or legal instruments that specify water/island treatment and an appropriate geometry comparator. Neighboring-county continuity and full Georgia/state completeness remain unadjudicated here. No regional approval, deployment, production write, historical import or publication request is implied.

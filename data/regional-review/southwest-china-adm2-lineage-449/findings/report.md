# Southwest China ADM2 identity and boundary-lineage follow-up

**Issue:** [#917](https://github.com/ChengshuLi/WorldAtlas/issues/917)
**Research date:** 2026-10-09 (UTC)
**Worker:** `01a10947-7d6e-7ba2-98a1-a9f91dedabfc`
**Base:** `696d1eadd9afdff8267ef3166c4c6b8b849011f5`
**Exact scope:** 228 native IDs; scope digest is in `reproduction-summary.json`; all output and this report stay in #917's owned directory.

## Result

This pass reproduced the historical source-to-Atlas lineage for each scoped feature and made a new attempt to retrieve suitable current administrative rosters and approved boundary-map evidence. The direct provincial and national originals could not be obtained as bytes in this runtime. Search-index excerpts identify source leads, but they do not substitute for source files and were not used as row-level evidence. The outcome is therefore **partial, with current legal identity, parent and boundary completeness unresolved for all 228 subjects**. This is not a validation or approval of Southwest China geography and does not support a geometry correction.

The missing originals, dates, canonical URLs, access results, terms limits and restoration instructions are itemized in [`retrieval-log.json`](retrieval-log.json). The per-feature ledger [`feature-lineage.csv`](feature-lineage.csv) retains the exact 228 identities, parents, 2017 source feature IDs, geometry types, rings and vertex counts, along with explicit unresolved status for each row. Do not interpret missing evidence as evidence of no change, no islands or correct geometry.

## Reproduced source lineage

The issue scope is 33 Chongqing, 82 Guizhou and 113 of Sichuan's 158 features. The exact ID set is taken from the live issue's `worldatlas-work:v1` contract preserved in `source/issue-contract-917.json`. The pinned `data/geography/part-3.json` and `part-4.json` contain all 228 subjects once. Every Atlas feature resolves uniquely to a `shapeID` in the unchanged #449 retained source, geoBoundaries gbOpen `CHN-ADM2-17275852`, repository commit `9469f09592ced973a3448cf66b6100b741b64c0d`, declared vintage 2017, type ADM2 / canonical role “County Level”. All 228 source Pinyin names match the Atlas name exactly.

The parent source files remain owned by #449 and were not copied or edited. Their original GeoJSON is 7,618,692 bytes, SHA-256 `2b68d8a808742fc6d7acd769584db960d8fc2c25b9f1d20e3e98c72e9f1c4d34`; the 1,101-byte metadata JSON has SHA-256 `7f609da61c856d022a9bf83b35fb271d78ebb5855ad2c1cdff337e51acdec58a`. The retained inventory gives the immutable source path and restoration URLs. Metadata declares PDDL v1.0, but the upstream attribution points to a separate source whose rights were not established. This inherited license uncertainty remains open; the source declaration is not treated as proof of upstream rights.

The 2017 feature schema has no Chinese administrative code or parent ID. Atlas parent assignments separately cite geoBoundaries gbHumanitarian / HDX China ADM2 (2020) and greatest-overlap matching. This is a different source and vintage. The 2017 boundary source cannot reproduce those parent links. The current parent of each of the 228 features remains unresolved pending current roster rows and suitable boundary evidence.

## Geometry transformation reproduction

The new read-only reproducer verifies one-to-one scope/source/Atlas identity and emits per-feature source/output vertex counts and ring counts. The source has 14,634 vertices across these rows; the Atlas has 12,905, 1,729 fewer across 225 rows. Only three Atlas geometries equal the pinned source geometry after rounding source coordinates to four decimal places; zero rows match when rounded to 0–3 or 5–8 decimal places. All 228 are Polygon in both files. Two source and Atlas rows contain an interior ring. These are lineage and representation observations only: planar Polygon structure cannot show that the territory lacks detached islands or omitted pieces.

The transformation's originating tool, version, commit, coordinate precision, clipping or simplification parameters, source/output hashes at transformation time and original per-feature change receipt were not present in the available repository history or #449 evidence. Each affected row is individually marked `unresolved` in the feature ledger; the 225 vertex reductions are not attributed to a guessed simplifier. No area, geodesic, coastline, legal boundary, neighboring-edge or completeness comparison is claimed.

Reproduce the current ledger and scope controls from repository root with:

```sh
python3 data/regional-review/southwest-china-adm2-lineage-449/reproduce-lineage.py
python3 data/regional-review/southwest-china-adm2-lineage-449/reproduce-lineage.py --self-test
```

The command reads only the issue contract snapshot, two unchanged baseline feature parts and #449's immutable source originals. It writes only the two generated findings within this owned directory. It does not access a remote service or change source data.

Two clean runs produced byte-identical feature and summary ledgers; the command, script hash, and per-output hashes are retained in [`reproduction-runs.json`](reproduction-runs.json). The adverse scope controls reject duplicate expected/actual identities, missing subjects and foreign subjects; their receipts are `scope-control-positive.json` and `scope-control-negative.json`. These controls establish safe scope binding, not geographic truth.

## Current administrative and map evidence

### Current roster

The needed primary sources are identified by exact official title and URL in the retrieval log. The Chongqing Civil Affairs indexed notice exposes the linked 2025-12 spreadsheet title. Its separate 2025 code-change notice exposes a new code for Liangjiang New Area and discontinued former Jiangbei/Yubei codes. This is a material current identity/parent investigation lead, not a finding that any one of the 33 Atlas polygons changed, transferred or has an incorrect boundary. The workbook and notice originals were not retained, and none of the scoped rows has been crosswalked to a current code.

Guizhou's exact 2025-12-31 statistical-table title and the Sichuan province's 2025-12-31 code-table title were discovered. Direct official endpoints did not return the source bytes. Secondary syndication snippets and aggregate counts were excluded from the row-level comparison. A directly retrieved Guangyuan Municipal Civil Affairs listing (HTTP 200; exact body hash in the retrieval log) now links the Sichuan title to its notice page; that page returns HTTP 302 with the literal `Location` `http://mzt.sc.gov.cn/scmzt/quhuaxinxi/2026/1/28/fccc0ed4b8fe4655a3b946c6d8e9e1ed.shtml`. Following that HTTP redirect timed out; a separate HTTPS retry of the same path also timed out. The listing and redirect are locator evidence only, not roster bytes or a county crosswalk. The Ministry of Civil Affairs National Geographical Names Information Database, the expected national year-end code source under Order 79, also remains inaccessible from the recorded research runtime. Wayback CDX queries for the three provincial roster notices also timed out, leaving snapshot availability unknown; no archive copy was used. No present-day name, code, administrative class, status, current parent or roster completeness is certified for any of the 228 rows.

### Boundary reference

The State Council's Map Management Regulations require county-level-and-higher boundaries shown on maps to follow approved standard boundary depictions. The National Geomatics Center catalog describes a public-edition 1:250,000 product with county polygons and administrative boundaries, but its stated currency is 2012. That product is too old to establish present boundary identity/completeness and predates the 2025 Chongqing change signal.

Sichuan’s Civil Affairs Department’s 2025 trial standard for place-name plans says boundary depictions should follow the latest approved standard map, be checked against the latest approved boundary-adjustment records and demarcation results, and have administrative-division information reviewed by Civil Affairs. This is a source-request specification for the 113 Sichuan subjects, not a geometry source: only the official search-index text was available, the PDF and its reuse terms were not retained, and no row-level comparison follows from it.

The Chongqing Planning and Natural Resources Bureau's standard-map service was directly retrieved. Its citywide administrative-division image and the Liangjiang New Area administrative map carry approval `渝S(2025)130号`, are printed `2026年一月`, were served with a 2026-01-26 Last-Modified timestamp (Liangjiang image: 2026-06-18), and show county/area names and internal lines. The six citywide sheet originals, service catalog hash, and Liangjiang map hash are logged with exact restoration URLs. The official 2026 update notice directs users to this module; the map footer credits the planning bureau and civil-affairs bureau. The catalog's `data/qh.js` instead labels its entries `2024年06月`, a material stale-metadata conflict. A directly retrieved 大足区行政区划 sheet also prints January 2026 but retains approval `渝S(2024)029号`. Treat each map's own vintage and approval as specific to that sheet, not inferred from the catalog timestamp or another sheet.

These raster products materially improve the current display-map evidence for Chongqing, including the newly mapped Liangjiang unit. However, their printed warning says `图内界线不作为划界依据` (the lines shown are not a basis for boundary demarcation); the municipal overview scale bar spans 75 km and images are generalized cartography, not polygon files. The retrieved public pages say maps may be downloaded/used but disclose no open license for repository redistribution or digitization. Original JPEGs therefore are not committed; exact URLs, byte lengths, hashes, retrieval/Last-Modified dates, observed approval/vintage and a reproducible restoration procedure are retained. Do not treat their depiction as legal-boundary geometry, nor infer which of the 33 historical Atlas subjects is affected by the 2025 Liangjiang code change.

No suitable, currently authoritative county polygon file was obtained. Consequently every subject remains untested for legal boundary match, disconnected components, island/coastline completeness, neighboring coverage and boundary role. No overlap score or national general-purpose product has been substituted for that missing evidence.

The Civil Affairs Bureau reports that approved county boundary results are shared with the Planning and Natural Resources Bureau; this remains the engineering handoff route for legal geometry. Guizhou's accessible official 2024 standard-map announcement describes ten thematic sheets at 1:3,000,000 A4, too generalized to test county geometry completeness. Exact locators, retrieved image hashes, access results, limitations and restoration steps are in [`retrieval-log.json`](retrieval-log.json).



## Handoff and disposition

1. Restore the official national and provincial year-end rosters using the exact URLs in `retrieval-log.json`; record each actual file's SHA-256, retrieval timestamp, source vintage and reuse terms before extracting rows. Crosswalk every one of the 228 existing IDs to official identity/code/class/status and current parent; explicitly investigate the Chongqing 2025 code notice without inferring polygons from code changes.
2. Obtain an approved, suitably current and lawfully usable polygon/map source for the three provinces, together with its original bytes or precise restoration details, approval/version/vintage and scale/generalization limits. Independently examine all 228 features and their neighbors for outer boundaries, shared edges, islands, detached parts and omissions. Record unsupported or unavailable comparisons per ID.
3. Engineering should trace the original geography ingestion/build commit and toolchain that created these 228 Atlas geometries; recover original transformation settings/receipts or preserve the 225 per-feature origin gaps. Any later change must preserve stable IDs and historical claims, use sourced bounded corrections only, and be submitted as a separate reviewed engineering proposal. This packet makes no geometry change.

The exact scope, release pins, source originals, parent packet, neighboring files and shared geography remain unchanged. This PR should use **`Refs #917`**, because the current official row-level and boundary questions remain unresolved. Do not close #917 or describe this work as validating the Southwest China branch on the strength of source identity matches, vertex counts, indexed search snippets or structural checks.

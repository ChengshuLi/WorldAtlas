# Data strategy

## Selected decisions

Flat 2D display; fixed, time-agnostic hierarchy: location → province → area → region → subcontinent → continent. Use recent reliable administrative footprints; prefer current, allow 2025/2024 or older, and record varying source dates. No common reference date or mandatory 2026 coverage. Freeze footprints across history; only political control changes.

Complete geography before researching 20+ historical attributes per location. Start with six continents excluding Antarctica; user approves each level before parallel workers subdivide it (17 subcontinents is illustrative). Before approval, verify proposed partitions preserve intended whole lower-level administrative units; revise proposals if not. Every in-scope cell is water or exactly one location. Antarctica is cropped from the map; the starting full-world grid is 16,384 × 8,192 = 134,217,728 cells. Its exact latitude cutoff and resulting height remain open. Investigate source gaps/overlaps; state clear approximation rules/consequences.

Use source polygons/coordinates; a city's point is not its area. Map cells to the location with the largest area share; locations to the entity with the largest controlled area at the date. Cells inherit location affiliation even where another entity controls a smaller portion. Effective control assigns one entity per location/date; no claims records. Joint administration uses a documented lead or, where comparable evidence distinguishes, greater responsibility/resources. Resolve remaining ties by stable location/entity ID order; record rationale as arbitrary, not historical fact or a substitute for missing evidence. Never invent an unsupported controller.

Population includes all fixed-footprint inhabitants at each date, including rural areas and villages. Encourage estimates/inference when records are sparse; label and record basis/assumptions, leaving values unknown only without a defensible estimate. Never present estimates as observed counts or double-count overlapping sources. Store estimate status/source/basis; show details on demand to keep UI clean.

## Storage and delivery

R2 stores original evidence of any size; Neon tracks references, dates, and checksums, without duplicate copies. Neon also holds editable research with PostGIS polygons and separate generated tables for hierarchy, affiliation, population, and attributes. Code generates the cell-to-location grid in R2; never patch generated data. GitHub holds code, schemas, and docs; issues track task completion. One worker owns research through validation, fixes, and delivery. Research may later parallelize across 10–20+ Luna agents. No research-only PR; user merges code/schema/doc PRs.

A shared apply command validates and transactionally commits research/derived writes with per-location locks and revision checks; unrelated locations proceed in parallel. Serialize grid corrections: rebuild affected data from latest inputs, upload the R2 grid, recheck revisions, then commit geometry/results and pointer in Neon. The app reads matching revisions. R2 and Neon are not one atomic transaction. No publisher, queue, or handoff.

## Open design questions

- Map projection/layout, geographic coverage, exact latitude cutoff/final grid height, and land/water/coast/lake/river treatment.
- Location granularity and boundary dataset choices, resolved during hierarchy work.
- Attribute definitions, time/date conventions, schemas, grid format/partitioning, and matching-revision app loading.
- Apply-command interface and validation.

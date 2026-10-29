# Data strategy

## Geography and political model

WorldAtlas uses a flat 2D display and time-agnostic hierarchy: location → province → area → region → subcontinent → continent. Use recent, reliable administrative boundaries as fixed footprints; prefer current data but accept 2025, 2024, or older, recording source dates that may differ. No common reference date or required 2026 coverage. Freeze footprints through history; only political control changes. Dataset and location granularity remain open.

Complete geography before historical research of 20+ attributes per location. Start with six continents, excluding Antarctica; user approves each level before parallel workers subdivide it at the next. Repeat top-down through subcontinents, regions, areas, provinces, and locations; 17 subcontinents is illustrative. Before approval, ensure lower-level administrative units intended to stay whole fit within the partition; revise proposals first. Every in-scope map cell must resolve to water or exactly one location, without cell gaps/overlaps; transparently address finer polygon imperfections. Do not count Antarctica's land as water; its display, land/water mask, coasts, lakes, and rivers remain open.

Retain source polygons/coordinates; cities need boundary polygons for area assignments, not representative points. Map each cell to the location covering most of its area; map each location to the entity controlling most of its area on the date. Cells inherit location affiliation even where another entity controls a smaller portion. Assign one effective-control entity per location/date; no claims records. Joint administration uses a documented lead or, with comparable evidence, greater responsibility/resources. Remaining eligible area/administration ties use stable location/entity ID order; record this arbitrary model tie-break as not historical fact or missing evidence. Never invent a controller. Approximation needs clear rules/consequences; investigate polygon gaps/overlaps.

## Population

Population covers everyone in fixed footprints at each date, including rural areas and villages. Encourage estimates/inference when records are sparse; label and record basis/assumptions, leaving values unknown only when no defensible estimate exists. Never present estimates as observed counts or double-count overlapping sources. Store estimate status/source/basis; show details on demand to keep UI clean. Estimates do not justify guessing political control.

## Storage and delivery

Keep original evidence of any size in R2; track references, dates, and checksums in Neon without duplicate copies. Editable research lives in Neon/PostGIS. Generated hierarchy, affiliation, population, and attributes use separate Neon tables; code generates the R2 cell-to-location grid. Never manually patch generated data. GitHub holds code, schemas, docs, and issues. Issues track task/completion; one worker owns research, validation, fixes, and delivery, with no research-only PR. Future research may parallelize across 10–20+ Luna agents. Code/schema/doc changes go through PRs for the user to merge.

A shared apply command validates and transactionally commits research/derived writes with per-location locks and revision checks; unrelated locations can proceed in parallel. Serialize grid corrections: rebuild affected cells/attributes from latest inputs, upload the new R2 grid, recheck source revisions, then transactionally save geometry/results and matching pointer in Neon. The app reads matching revisions. R2 and Neon are not one atomic transaction; no publisher, ready queue, or handoff. Grid resolution, area method, schema/formats, and exact map layout remain open.

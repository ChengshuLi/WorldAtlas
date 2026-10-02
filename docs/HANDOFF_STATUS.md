# Handoff and continuation log

Primary repository: `https://github.com/ChengshuLi/WorldAtlas`, branch **work**. This file records work that can be continued from Git. A `.cache` path below identifies a local stage only; the accompanying tracked evidence and restoration instructions are the durable handoff. Do not claim a local stage is deployed or silently apply a blocked candidate.

## Current scope

Finish the code, contracts, geographic foundation, migrations, grid, coverage reporting and publication checks. Broad historical expansion is paused at the user's request. Preserve completed historical work and prepare GPT 6 Luna to add sourced content through the stable API. Antarctica is excluded; EU5 counts are granularity references.

## Current installed checkpoint — 2026-10-02 UTC

The reviewed geography is installed locally, not yet deployed: **49,589 locations → 5,133 provinces → 471 areas → 66 regions → 29 subcontinents → six continents**. The fixed resolution-10 grid represents all 49,589 locations. Footprint SHA256: `5d7236fe7e9d2f83c07c0b5cc1d5e703bf685f860fd49c850edd18eea27c61a8`; hierarchy SHA256: `bb083958f4ccee3ca1aa4b9d0392433a79c4ebbf023c873168c0900ca4a36d58`. Active ownership has 6,833,837 intervals and environmental references have 346,167 tuples; removed-footprint records remain in immutable archives.

The final audit inventories all 49,589 locations, 5,705 parent groups, 250 current reference-owner groups and 201 source-policy profiles, with zero unmatched policies. The earlier 252 source-territory groups include ASM and MNP, now separately crosswalked under the USA owner group; these are not omitted territories. Structural checks pass. All local-purpose/island-completeness approvals and all 5,705 full branch approvals remain open; 486 independently supported group boundaries do not approve descendants. Closure SHA256: `3189ad65022098dbe8a27d794a7a5fe0d4e4bc6ddcf8ce2ae5e947782c34cbda`.

Migrations 0005 and 0006 harden provenance and unresolved-value constraints. Populated native D1 preservation checks are recorded in `docs/STRUCTURAL_VALIDATION.md`; built browser checks across six continents and all 14 modes passed, as did exact-final content-only imports/withdrawals with unchanged website assets. The full publication suite initially passed 135/136; its only failure was a stale grid-resolution assertion, now corrected and verified by all five grid tests. Missing local parent indexes were subsequently fixed with populated-database preservation and query-plan tests; the matching full suite passed **138/138 with zero skips**. Forced legacy migration improved from 281 seconds to 43 seconds. Native deployment remains pending. Previous production remains the earlier milestone until a deployment receipt below says otherwise.

## Completed content retained in Git

| Product | Retained result | Continuation |
| --- | --- | --- |
| Historical political ownership | Original 6,834,664 intervals; source repair reuses 6,832,396, archives 2,268 and derives 1,441 replacement intervals | `docs/INCREMENTAL_OWNERSHIP.md`, `docs/SOURCE_TERRITORY_REPAIR_MIGRATION.md`; all original intervals remain accounted for |
| Environmental references | Original 346,293 tuples; source repair reuses 345,984, archives 309 and derives 183 replacement tuples | `docs/INCREMENTAL_REFERENCES.md`, `data/reference-migrations/source-territory-repair-v1` |
| Dated name attestations | 3,588 original name records, supported only in 2020 or 2021 | `data/dated-reference-names`, original producer proofs and separate exhaustive revalidation receipt |
| Census religion | 396 observation-year 2021 records: 193 known and 203 explicit unknown | `data/demographic-evidence`, original sources/proofs and exhaustive revalidation receipt |
| Settlement populations | 9,301 estimates on 582 independent settlement identities | Keep separate from location totals and rank |
| Paused GHSL preparation | Source manifest, producer and unvalidated intermediate bytes | `data/interrupted-preparation/ghsl-2020`, `docs/GHSL_POPULATION_IMPORT.md`; never import incomplete output |
| Earlier geography | 19,050 predecessor location identities, geometry, chains, nine original state rows and six original historical rows | `data/geographic-migration-archive.json.gz`; immutable hosted catalog must remain unchanged |

## Structural work and its evidence

The shared resolver produces a whole-location scalar value or unknown at each supported date. Names, membership and attributes use stable identities and half-open intervals without year zero. Sparse imports, immutable corrections, graph entities/relationships and separate media storage support content updates without rebuilding map assets. Atomic attribute/name/retirement reads preserve complete snapshots and prevent withdrawn cached claims from reappearing after partial API failures. The main location panel uses the approved historical title, always-visible present-day reference, selected year, six-tier hierarchy and eight attributes; detailed limitations stay in collapsed Evidence.

The original source-repair stage covers all 49,614 locations. Twenty-five source-identity unions and two seam corrections plus the licensed full Vatican territory yield 49,589 active locations, with 27 changed footprints and 25 retired IDs. Every previous affected geometry and claim context is archived; historical claims are not transferred. The macro stage retains every repaired geometry and corrects continental-side membership using conservative whole-footprint physical-source shares. Its complete hierarchy is 49,589 locations → 5,133 provinces → 471 areas → 66 regions → 29 subcontinents → six continents.

Durable receipts and source bytes are in `data/geographic-repair-evidence`, `data/macro-boundary-migration.json.gz`, `data/macro-boundary-decisions.json` and `data/macro-boundary-source-rivers.geojson.gz`. Read their migration documents before replaying. The active `data/world-index.json` and `data/publication-geography-receipt.json`, when present, establish what has actually been installed; a proposal file alone does not.

The exhaustive candidate-grid assessment tests every approved location at fixed resolutions 7–10. Resolution 10 represents all 49,589 territories with no measured WGS84 relative-area error above 25%; resolutions 7–9 lose 50, nine and one locations respectively. Compact ownership arrays and byte-shuffled transport preserve exact values. Actual WebGL and a simulated 4096 texture limit pass; navigation performs zero ownership uploads. `data/final-grid-resolution-review.json.gz`, `data/final-grid-rendering-review.json` and `docs/FINAL_GRID_ASSESSMENT.md` retain methods, timings, memory and limitations.

## Open items: evidence, blocker and next action

| ID | Status / blocker | Durable evidence and exact next action |
| --- | --- | --- |
| GEO-NAM | Entire Namibia 2007 source profile requires replacement; candidate still conflicts with neighbors and leaves uncovered land | Read `docs/NAMIBIA_REPAIR_MIGRATION.md`, `data/retained-geographic-sources/namibia` and `data/namibia-source-quality-annotations.json`. All 111 existing IDs and all 107 candidate codes are inventoried. Resolve all 25 neighboring-source conflicts (331.61 km²) and remaining 339.46 km² of uncovered old land before replacement. Do not silently clip neighbors, assign nearest territory, infer urban rank or transfer historical claims. |
| GEO-SEMANTICS | Exhaustive inventory/diagnostics are complete; semantic approval remains open | `data/global-semantic-closure.json.gz`, `data/world-review.json`, `docs/GLOBAL_SEMANTIC_CLOSURE.md` and all six `data/geographic-decisions` files inventory every branch. Process continent → subcontinent → region → area → province → location; source-backed decisions must address every flagged member, with unsupported cases explicitly open. Structural success cannot approve descendants. |
| GEO-MACRO | Fifteen own-boundary conventions need stronger exact physical/island evidence | `data/macro-boundary-decisions.json` and `docs/MACRO_BOUNDARY_CONVENTION.md`. Resolve the named physical segments/island associations; preserve the distinction between a supported geographic convention and completed descendant semantics. |
| GEO-COVERAGE | Some source omissions, marine territory/coastline-vintage differences and dry-land gaps remain | Use the exhaustive source/split and coverage ledgers, including Marshall island source comparisons. A represented polygon does not prove complete global dry-land coverage. |
| GRID-MOBILE | Physical mobile memory/frame-time validation is unavailable | The permanent compact CPU ownership array is about 232 MB plus a comparable GPU copy. Mobile viewport/texture-limit simulation is not physical-device evidence. Benchmark actual target devices; retain the same canonical geography and avoid arbitrary cell donations or navigation recompilation. |
| CONTENT-HISTORY | Broad historical expansion intentionally paused | Read `docs/LUNA_DATA_HANDOFF.md`. Expand sourced sparse names/attributes/relationships only within supported intervals. Unsupported years remain unknown; do not create 200 million snapshots or infer demographics from country priors. Existing completed evidence must remain preserved. |
| STORAGE-SCALE | Initial service is bounded, not an unlimited 200-million-row database | Read `docs/HOSTED_STORAGE_ARCHITECTURE.md`. Measure row/index sizes and query load; introduce geographic/attribute/time backend partitioning behind the stable API when necessary. Media objects currently have a 20 MiB upload limit; larger files need multipart support. |
| RELEASE-FINAL | Matching final build, publication gates and native private deployment remain required until receipts confirm them | Run `docs/STRUCTURAL_VALIDATION.md` phases against matching prepared assets. Commit/push the exact source, publish the existing owner-private Site, verify migrations and bootstrap receipts, then record URLs/SHAs and checks here. Do not describe a staged build as production. |

## Checkpoint discipline

Every new claim, correction, source archive and review decision must be pushed to the primary GitHub branch with its supported interval, identity, source hash and status. For large publicly reproducible downloads, commit immutable URLs/hashes and restoration commands; completed compact products and unique intermediate output must be retained. SQLite backups and private credentials are not source handoff assets. Record unresolved blockers before ending a thread. Keep this log and the publication scope current when a stage is installed or published.

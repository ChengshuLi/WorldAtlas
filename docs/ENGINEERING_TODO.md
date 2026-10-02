# Engineering TODO — detailed acceptance guidance

The authoritative dated TODO/work record is [ENGINEERING_HANDOFF.md](ENGINEERING_HANDOFF.md#engineering-todo-and-retained-work-record). Update statuses/dates there and retain completed entries. This guide supplies detailed acceptance criteria.

This is the open engineering queue for future maintainer threads. Historical-content campaigns have a separate queue in [HISTORICAL_RESEARCH_TODO.md](HISTORICAL_RESEARCH_TODO.md). Clone branch **main**, read `AGENTS.md` and [HANDOFF_STATUS.md](HANDOFF_STATUS.md), and inspect the current live release before changing anything. The verified Site 18 platform is writable; no new baseline migration or rehearsal is required to start research.

Use the authoritative tracker for current status. A source checkpoint, candidate, structural pass or inventory does not establish deployment or semantic completion. Completion requires retained evidence, validation and actual publication receipts when applicable.

## ENG-01 — dated footprint rendering and caches

- Connect reviewed immutable footprint versions and dated selection to the Worker/browser snapshot, resolver eligibility, grid loading, picking, fills, borders and cache keys. Current browser capability is `datedFootprints:0`; the SQL/catalog scaffold alone is not rendering support.
- Reuse the loaded canonical ownership assets during zoom, pan and resize. Change cached grid versions only when a sourced footprint/inventory change requires it. Prevent stale evidence or withdrawn records from returning across version changes.
- Verify dated transitions, missing/unavailable versions, withdrawal authority, whole-location values, and preservation of reference/predecessor geometry before publishing the capability.

**Why:** dated names or membership cannot establish a historical land shape; a changed footprint must not silently inherit evidence for a different territory.

**References:** [FOOTPRINT_VERSION_CONTRACT.md](FOOTPRINT_VERSION_CONTRACT.md), [HOSTED_TEMPORAL_GEOGRAPHY.md](HOSTED_TEMPORAL_GEOGRAPHY.md), `hosted/footprint-versions.js`, `src/data-client.js`, `data/validation/neon-final-publication.json`.

## ENG-02 — install three validated hierarchy candidates

- Install the prepared Monaco/Luxembourg grouping corrections and West Virginia duplicate-province correction through a coherent reviewed geographic release.
- Update every dependent hierarchy/catalog/grid-parent lookup and manifest; preserve all original IDs, predecessor relationships, geometry and historical evidence. Revalidate dependent prepared evidence explicitly rather than silently repinning it.
- Publish and verify matching map, inspector, parent boundaries, complete chains, migration accounting and before/after hashes.

**Why:** the candidates are validated proposals, but the live atlas still uses the previous parent assignments. Partial installation would make its datasets disagree.

**References:** [REFERENCE_HIERARCHY_CORRECTIONS.md](REFERENCE_HIERARCHY_CORRECTIONS.md), `data/reference-hierarchy-corrections/migration-receipt.json.gz`, `scripts/prepare-reference-hierarchy-corrections.py`.

## ENG-03 — geographic repairs and worldwide review closure

- Work continent → subcontinent → region → area → province → location, accounting for every branch and source profile. Retain the exhaustive current inventories; do not approve children merely because a parent's boundary is supported.
- Obtain source-backed decisions for flagged granularity, city fragments, administrative remainders, islands/land gaps, repeated tiers and physical boundary conventions. Historical researchers may supply evidence; maintainers own correction implementation and geographic release acceptance.
- Resolve the blocked Namibia replacement's neighboring-source conflicts and unexplained land before installing it. Keep unresolved cases visibly open; no arbitrary clipping, nearest-territory assignment or count quotas.
- For each accepted repair, preserve identities/history, crosswalk every changed unit, rebuild affected derived products, validate coverage/overlap and publish matching receipts. Close semantic reviews only with a sourced decision or justified exception.

**Why:** complete database chains and exhaustive screening do not prove globally sensible granularity or source completeness. Current full branch approvals remain open.

**References:** [GLOBAL_SEMANTIC_CLOSURE.md](GLOBAL_SEMANTIC_CLOSURE.md), [REGION_SEMANTIC_REVIEW.md](REGION_SEMANTIC_REVIEW.md), [NAMIBIA_REPAIR_MIGRATION.md](NAMIBIA_REPAIR_MIGRATION.md), `data/geographic-semantic-followup`, `data/global-semantic-closure.json.gz`.

## ENG-04 — physical mobile performance

- Measure initial load, decoded/GPU memory, frame times, pan/zoom, resize and fallback rendering on actual phones. Preserve device/browser specifications and measurements; viewport emulation is not physical-device evidence.
- Address measured bottlenecks while preserving fixed ownership, readable thin-local/bold-parent borders, selection correctness and zero navigation ownership recompilations/uploads.

**Why:** the ownership array is approximately 232 MB on the CPU, with a comparable GPU copy. Existing desktop/software-renderer tests cannot establish phone memory capacity or responsiveness.

**References:** [FINAL_GRID_ASSESSMENT.md](FINAL_GRID_ASSESSMENT.md), `data/final-grid-rendering-review.json`, `data/validation/neon-final-live-browser.json`.

## ENG-05 — operational limits and measured growth

- Confirm the actual Neon project plan, storage/compute allowances and backup/restore retention, and separately document object-storage limits. The configured 512 MiB guard is not the provider quota.
- Verify useful capacity warnings and recovery instructions. Measure representative import/query latency, row/index growth and backup performance before sustained expansion.
- Introduce partitioning, caching or larger-media multipart transport only when measured requirements warrant it, behind the existing stable IDs and content API. Keep all 23 factual tables, owner-only migration state and object bytes covered by appropriate backups.

**Why:** research can exhaust finite storage or compute even though the provider scales. Content threads must not need infrastructure changes or UI rewrites to continue ordinary imports.

**References:** [NEON_SETUP.md](NEON_SETUP.md), [LONG_TERM_STORAGE_PLAN.md](LONG_TERM_STORAGE_PLAN.md), [RESEARCH_CAPACITY.md](RESEARCH_CAPACITY.md), [STORAGE_EXPORT_V2.md](STORAGE_EXPORT_V2.md).

## End-of-thread record

Update the engineering handover tracker, dated milestones and owned job progress with completed scope, receipts, blockers and next action. Push an `engineering/<job-id>` branch and PR to **main**; integrate validated PRs serially and update central operational summaries. Preserve the original evidence and fixed migrations. Keep credentials out of Git. Leave research tasks in the research queue; do not transfer these engineering items to Luna.

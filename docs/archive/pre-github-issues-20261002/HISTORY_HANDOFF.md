# Historical-content handover for Luna

Give a Luna thread this document and [its prompt](prompts/LUNA_HISTORY.txt). This entry point describes the research lane without requiring the prior chat or workspace.

**Repository:** `https://github.com/ChengshuLi/WorldAtlas`, integration branch **main**. **Site:** https://worldatlas-explorer.chengshu-li-2013.chatgpt.site/, owner-private. Read `AGENTS.md`, [HISTORICAL_RESEARCH_TODO.md](HISTORICAL_RESEARCH_TODO.md), [LUNA_DATA_HANDOFF.md](LUNA_DATA_HANDOFF.md), [RESEARCH_IMPORT_WORKFLOW.md](RESEARCH_IMPORT_WORKFLOW.md) and [ATTRIBUTE_CONTRACT.md](ATTRIBUTE_CONTRACT.md). Inspect existing campaign branches/PRs before selecting new scope.

## Current starting point

The Site uses production Neon PostgreSQL and R2. Content imports are enabled, with bounded validation, immutable claims and idempotent receipts. Existing ownership/environmental products, 3,588 dated names, 396 religion records, 9,301 separate-settlement estimates and original archives are retained. Do not discard or repeat completed research. Interrupted GHSL preparation is not validated import content.

Names, attributes, source provenance and stable entity identities are independent of application code. Store supported sparse half-open intervals, not annual location snapshots. Missing evidence remains unknown. Preserve fixed classifications, source dates and uncertainty. Modern physical reference context is already labeled by the UI; it is not historical evidence. Research historical environmental intervals, including recent gaps, without automatically widening modern observations.

## Historical research TODO and retained work record

This document is the authoritative research tracker. Keep done items and evidence; never delete or renumber historical entries. Global objectives stay open until their explicitly stated coverage is achieved. Completing one bounded campaign does not close a worldwide attribute. Detailed scope guidance is in [HISTORICAL_RESEARCH_TODO.md](HISTORICAL_RESEARCH_TODO.md).

Dates use **America/Los_Angeles**. Preserve the actual first-raised date when known; use `unknown` for earlier requests without a reliable date. `Recorded` is the first durable tracker entry. Completion is the verified scoped milestone, with original UTC receipts retained. Existing source research below predates this tracker; its original completion date is not invented.

| ID | Global objective / retained milestone | Status | Raised | Recorded | Completed | Evidence / next action |
| --- | --- | --- | --- | --- | --- | --- |
| RES-00 | Preserve and verify the completed historical checkpoint for handover | done | unknown | 2026-10-02 | 2026-10-02 | `data/validation/neon-final-import-replay.json`; retained names/religion claims, ownership/environment products, estimates and archives; this is verification, not their original research completion date |
| RES-01 | Source inventory and systematic campaign coverage | open | unknown | 2026-10-02 | — | Assess geography, time, attributes, licensing and uncertainty; choose disjoint campaigns across all six continents |
| RES-02 | Historical names and aliases at every tier | open | unknown | 2026-10-02 | — | Extend retained 3,588 observation-year names with supported intervals and stable IDs |
| RES-03 | Historical ownership evidence | open | unknown | 2026-10-02 | — | Extend/improve retained reconstruction; direct evidence and explicit uncertainty; hand spatial preparation needs to maintainer |
| RES-04 | Population, habitation and rank | open | unknown | 2026-10-02 | — | Separate settlements from location totals; retained GHSL preparation remains unvalidated |
| RES-05 | Primary culture | open | unknown | 2026-10-02 | — | Supported population distributions/attestations, warranted primary interpretation and uncertainty |
| RES-06 | Primary religion | open | unknown | 2026-10-02 | — | Extend retained 396 observation-year records with warranted dated evidence |
| RES-07 | Historical topography, vegetation and climate intervals | open | unknown | 2026-10-02 | — | Fixed classifications; investigate recent/ancient gaps without silently widening modern reference dates |
| RES-08 | Sourced dated parent membership and existence | open | unknown | 2026-10-02 | — | Use published contract/atomic phases; refer changed footprints or geographic identity migrations to maintainer |
| RES-09 | Interconnected historical subjects, relationships and licensed media | open | unknown | 2026-10-02 | — | Later scoped campaigns through supported generic content APIs; new domain UI is engineering |

## Campaign work record — owned by Luna threads

Each research branch may add/update **only its own rows** in this section. Use IDs `CAM:<campaign-id>:<number>`, state the bounded scope and related RES objective, and record status, raised/recorded/completed dates and evidence. Keep all existing rows, including completed ones. Completion requires source/import/read-back evidence. Do not use raw `|` characters inside a cell. The CI guard checks ownership, retained rows and completion fields. Global objective updates above belong to maintainer integration.

<!-- RESEARCH-CAMPAIGNS:START -->
| ID | Scope | Status | Raised | Recorded | Completed | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
<!-- RESEARCH-CAMPAIGNS:END -->

The campaign directory also contains dated notes and an owned progress JSON, so a single table row can link to detailed sources, intermediate work and multiple milestones. Empty campaign rows mean no new post-handover campaign is claimed here; inspect unmerged research branches/PRs before starting.

## One bounded research issue per PR

For each scoped campaign TODO, create/reuse one GitHub issue and one new `research/<campaign-id>` branch from current `origin/main`. Use one owned campaign item (for example `CAM:<campaign-id>:1`); the broad RES goals remain umbrellas. Put that item in `TODO: <stable-id>` and link one `Closes #<issue-number>` line in the PR body targeting `main`. Keep input/import/read-back evidence bounded to that issue. After its PR merges, create a fresh branch for the next issue. Do not gather several campaigns into one later omnibus PR. Retain done items with completion dates and issue/PR evidence.

## Work in the research lane

1. Use a separate checkout/worktree. Fetch `origin/main`, choose a unique lower-case campaign ID such as `japan-names-1900-20261002`, and create **`research/<campaign-id>`** from that integration branch. Never switch another active thread's checkout or push routine work directly to `main`.
2. You own **`research/campaigns/<campaign-id>/` and this document's `CAM:<campaign-id>:…` rows**. Copy `coordination/templates/research-progress.json` to `research/campaigns/<campaign-id>/progress.json`; fill in scope, dates, branch, base commit, source paths, release pins, receipts and open questions. Save research input, lawful source bytes or restoration manifests, notes and bundles within that directory. Mark completed scoped tracker items `done` with dates and evidence; preserve them as the ongoing record. Do not edit global objectives, handover instructions or another campaign's rows.
3. Choose a bounded campaign from the research TODO, check existing sources/entities/categories, and reuse stable IDs. Before importing, obtain the current `/api/geography/release`, capacities and capabilities through documented private access; save the exact release JSON with the campaign. Private credentials come from the authorized Site mechanism, never Git/chat/arguments; GitHub's Neon management key is not an import token.
4. Prepare factual JSON and compile/validate it using existing tools. Import accepted batches, retain receipts after every commit, verify new claims and selected-year results, and log uncovered scope. Preserve incomplete progress if interrupted.
5. Push your branch frequently. Open a PR targeting **main** that describes campaign coverage, sources, imports, read-back and unresolved questions. Run `node scripts/check-handoff-scope.mjs --branch research/<campaign-id> --base origin/main --head HEAD`. Technical maintainers integrate PRs serially; do not merge or rewrite application releases yourself. Follow applicable Codex PR attachment instructions.

Example commands after saving the factual input and current release:

```sh
node scripts/prepare-research-bundle.mjs research/campaigns/CAMPAIGN/input.json research/campaigns/CAMPAIGN/geographic-release.json research/campaigns/CAMPAIGN/bundle
node scripts/import-research-bundle.mjs https://worldatlas-explorer.chengshu-li-2013.chatgpt.site/ research/campaigns/CAMPAIGN/bundle --dry-run
node --use-env-proxy scripts/import-research-bundle.mjs https://worldatlas-explorer.chengshu-li-2013.chatgpt.site/ research/campaigns/CAMPAIGN/bundle
```

Replace `CAMPAIGN` with your actual unique ID. Normal facts go through the existing content contract. Sourced dated membership/existence uses its documented contract and atomic phases. New geography/footprints, category registry changes, code, schema, UI, migrations, infrastructure and deployment are outside this lane. Existing generic subjects/relationships and linked licensed media are allowed through supported imports; new domain interfaces belong to engineering.

## Concurrent engineering and other research

Read [PARALLEL_WORK_PROTOCOL.md](PARALLEL_WORK_PROTOCOL.md). Different campaign directories prevent Git overwrites; source/geography/time/attribute scope prevents duplicate effort. Inspect other campaign progress files, including unmerged PRs, and pick a disjoint campaign. If extending somebody else's campaign, resume that same branch serially rather than create two writers for the same ID.

Production imports and geographic publication are transactionally serialized. Every new batch is release-pinned; changing geography stops an obsolete campaign. Preserve the old input, bundle and receipts, and report the precise mismatch for maintainer revalidation; do not silently change pins or recreate IDs. During server maintenance or capacity errors, stop import attempts after bounded retries and continue source research/preparation. Live import success and Git merge are different events: an already imported fact may be live before its PR merges, so retain receipts and inspect the API before retrying.

## End-of-thread handover

Push notes, original hashes/licensing, input, bundles, partial/final receipts, read-back, owned tracker rows and progress file. Record which supported coverage was achieved and what remains unresolved. The technical maintainer updates global objective summaries after integration. A fresh Luna thread resumes from the campaign branch and directory; it never needs your workspace. Do not count a successfully imported batch as worldwide historical completion.

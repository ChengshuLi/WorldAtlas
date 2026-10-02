# Engineering handover

Give a future engineering thread this document and [its prompt](prompts/ENGINEERING.txt). The document is an entry point to the durable repository; no prior chat, workspace, cache or private credential is required for understanding the work.

**Repository:** `https://github.com/ChengshuLi/WorldAtlas`, integration branch **main**. **Site:** https://worldatlas-explorer.chengshu-li-2013.chatgpt.site/, owner-private. Read `AGENTS.md`, [ENGINEERING_TODO.md](ENGINEERING_TODO.md), [HANDOFF_STATUS.md](HANDOFF_STATUS.md) and `data/validation/neon-final-publication.json`. Recheck the live state rather than assuming an old receipt is current.

## Current starting point

Site 18 uses production Neon PostgreSQL and retained R2 with imports enabled. The original production transfer and forward schema are verified; 23 factual tables are supported. Existing claims, predecessor history and original archives are preserved. Published capabilities include dated membership/existence and v2 storage export; dated-footprint browser integration remains zero. No baseline restoration or new rehearsal is needed for ordinary follow-up work.

The open engineering queue has five items: dated footprints/caches; installation of three hierarchy corrections; source-based global geographic corrections/review closure; physical mobile validation; actual capacity allowances and measured scaling. Source research may support geography, but technical maintainers own migration implementation and release validation. Historical content expansion runs separately in Luna threads.

## Engineering TODO and retained work record

This table is the authoritative engineering tracker. Keep every item after completion; append new stable IDs rather than renumbering or deleting history. Status is `open`, `active`, `blocked` or `done`. A done item needs a completion date and evidence. Detailed acceptance guidance is in [ENGINEERING_TODO.md](ENGINEERING_TODO.md).

Dates use **America/Los_Angeles**. `Raised` records the actual first request when known; `unknown` means the earlier chat did not establish its date. `Recorded` is the first durable tracker entry and must not be substituted for an unknown raised date. Underlying receipts retain their exact UTC timestamps. Preserve first-raised/recorded dates when updating status. If an item needs reopening, retain its completed milestone and add a linked follow-up item.

| ID | Item | Status | Raised | Recorded | Completed | Evidence / next action |
| --- | --- | --- | --- | --- | --- | --- |
| ENG-00 | Writable Neon research/import platform and preserved baseline | done | unknown | 2026-10-02 | 2026-10-02 | `data/validation/neon-final-publication.json`; 23-table/seven-date API checks, all 22 retained batches replayed, six-continent browser verification |
| ENG-01 | Dated footprint browser rendering and version caches | open | unknown | 2026-10-02 | — | `docs/FOOTPRINT_VERSION_CONTRACT.md`; connect the implemented scaffold to snapshots/rendering; browser capability remains zero |
| ENG-02 | Install three validated hierarchy corrections | open | unknown | 2026-10-02 | — | `docs/REFERENCE_HIERARCHY_CORRECTIONS.md`; prepare coherent release and explicit evidence revalidation |
| ENG-03 | Source-based geographic repairs and worldwide semantic closure | open | unknown | 2026-10-02 | — | `docs/GLOBAL_SEMANTIC_CLOSURE.md`; retain exhaustive inventories; resolve sourced decisions, blocked Namibia and migrations |
| ENG-04 | Physical mobile performance validation | open | unknown | 2026-10-02 | — | `docs/FINAL_GRID_ASSESSMENT.md`; actual phone memory/frame-time measurements remain open |
| ENG-05 | Actual provider allowances, growth controls and measured scaling | open | unknown | 2026-10-02 | — | `docs/LONG_TERM_STORAGE_PLAN.md`; verify configured storage/compute/backup limits before sustained growth |
| ENG-06 | Concurrent two-lane handovers, running trackers and path guard | done | 2026-10-02 | 2026-10-02 | 2026-10-02 | `data/validation/parallel-handoff-setup.json`; 11 guard tests passed, dated trackers/prompts and trusted-base PR workflow configured |
| ENG-07 | Establish main baseline and one-issue-per-PR development | done | 2026-10-02 | 2026-10-02 | 2026-10-02 | [Issue #1](https://github.com/ChengshuLi/WorldAtlas/issues/1), [initial PR #2](https://github.com/ChengshuLi/WorldAtlas/pull/2), `data/validation/main-pr-policy.json`; one-issue metadata checks, 27 affected tests and manual-only management workflows |

## Engineering milestones

- **2026-10-02:** verified the writable production research platform and retained facts/archives; recorded exact deployment and validation receipts in `data/validation/neon-final-publication.json`. The five wider engineering items above remain open.
- **2026-10-02:** established separate engineering/research branches, handover prompts, owned progress templates and continuing work records. Verified with 11 passing scope tests; ENG-06 retains its completion date and evidence. GitHub workflow execution and required branch protection are not claimed.

## One TODO issue per PR

Use current `origin/main` for every new issue branch, and target `main` in every PR. Create/reuse one GitHub issue for one stable TODO ID. Split large umbrella goals into bounded child items before starting. Put `TODO: ENG-…` and `Closes #<issue-number>` in the PR body. Complete and merge that issue incrementally, preserve its dates/evidence/PR link, then start the next issue on a fresh branch. The initial work-to-main foundation PR is the sole approved large bootstrap exception.

- **2026-10-02:** ENG-07 adopts `main` for both lanes, with one bounded TODO/GitHub issue per fresh branch and PR. Initial foundation publication is tracked by [PR #2](https://github.com/ChengshuLi/WorldAtlas/pull/2); its GitHub merge state is authoritative. Normal merges do not invoke provider workflows.

## Work in the engineering lane

1. Use a separate checkout/worktree. Fetch `origin/main`, choose a unique lower-case job ID such as `dated-footprints-20261002`, and create **`engineering/<job-id>`** from that integration branch. Never switch another active thread's checkout or push routine work directly to `main`.
2. Copy `coordination/templates/engineering-progress.json` to **`coordination/engineering/<job-id>.json`**. Set the job ID, branch, scope, base commit and evidence paths. Update this owned file periodically and at milestones; do not replace another thread's progress file.
3. Keep source changes, tests, maintainer documentation and receipts on your branch. Update this tracker and append dated engineering milestones as items progress. Do not edit `research/campaigns/`, campaign-owned rows in the historical tracker, or another engineering job's progress. If research inputs need correction or revalidation, produce a separate maintainer receipt and request a new immutable content campaign; preserve original bundles.
4. Push your branch frequently. Open a PR targeting **main**, including status, checks, deployed state and open items. Run `node scripts/check-handoff-scope.mjs --branch engineering/<job-id> --base origin/main --head HEAD` before submission. Follow applicable Codex PR attachment instructions.
5. Technical maintainers integrate reviewed branches serially. Rebase or merge the latest `origin/main`, preserve both lanes' files, rerun affected checks, and merge only verified changes. Update central TODOs and `HANDOFF_STATUS.md` as part of integration. A pushed PR is durable progress, not proof of a live deployment.

Read [PARALLEL_WORK_PROTOCOL.md](PARALLEL_WORK_PROTOCOL.md) for exact file ownership, PR checks and live-database coordination. Do not mix two implementation jobs that touch the same subsystem without an explicit dependency and one integration owner.

## While Luna imports concurrently

- Routine UI/code work uses isolated development data. Keep research imports compatible with the published API. Check additive schema changes before deployment; preserve current live content rather than overwriting it with a historical seed/checkpoint.
- Research imports pin release ID and hierarchy/footprint hashes. Production import and release publication already share a database transaction lock; a new campaign on obsolete geography must stop rather than silently repin. Supply an explicit before/after release and revalidation receipt when a geographic release changes.
- For owner DDL/storage maintenance, record a notice in your progress file, enable and deploy server read-only maintenance, drain in-flight imports using the same transaction lock, perform the bounded change, validate preservation against the fresh live revision, then re-enable and verify imports. Luna can continue source research and preparation while imports are paused.
- Do not disable constraints, alter immutable evidence or change private audience/credentials to make a test pass. Keep source archives/media bytes separately preserved; test appropriate to the actual change.

## End-of-thread handover

Push the branch, progress record, source, reproducible inputs and validation/publication receipts. Record exact commits, PR, deployed release and next concrete action. Leave unknowns and incomplete tests explicit. Use the engineering TODO as your queue; Luna is responsible for content research/imports, not engineering. Another thread can resume by reading this document, current `origin/main` and any open engineering PR/branch and its owned progress file.

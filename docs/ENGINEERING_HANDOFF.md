# Engineering handover


The global macro partition is approved and published under #33/#36. Use [MACRO_FOUNDATION_APPROVAL.md](MACRO_FOUNDATION_APPROVAL.md) and `data/macro-foundation/regional-handoffs.json.gz` for all 81 fixed regional scopes. Regional interior audits can proceed in bounded parallel work items; no regional location-content imports are approved yet.
Give a future engineering thread this document and [its prompt](prompts/ENGINEERING.txt). They provide architecture, workflow and validation instructions. **GitHub Issues is the single source of truth for TODOs, status and work history**: [open engineering issues](https://github.com/ChengshuLi/WorldAtlas/issues?q=is%3Aissue+is%3Aopen+label%3Atype%3Aengineering). This document contains no live task checklist.

M engineering and N history workers must read [WORKER_COORDINATION.md](WORKER_COORDINATION.md), claim one ready 1–3-PR work item before implementation, and use the merge queue. Umbrellas are split into bounded children and never reserved by one worker.

Repository: https://github.com/ChengshuLi/WorldAtlas, integration branch **main**. Site: https://worldatlas-explorer.chengshu-li-2013.chatgpt.site/, owner-private. Read `AGENTS.md`, [acceptance guidance](ENGINEERING_TODO.md), [HANDOFF_STATUS.md](HANDOFF_STATUS.md), [PARALLEL_WORK_PROTOCOL.md](PARALLEL_WORK_PROTOCOL.md) and `data/validation/neon-final-publication.json`. Recheck live capabilities rather than assuming old receipts are current.

## Architecture and preserved starting point

Site 18 uses production Neon PostgreSQL and retained R2 with imports enabled. The production transfer and forward schema are verified; 23 factual tables are supported. Existing claims, predecessor history and original archives remain preserved. Published capabilities include dated membership/existence and v2 storage export; the checkpoint's dated-footprint browser capability is zero. No baseline restoration or migration rehearsal is needed for ordinary follow-up work.

Application code and factual content are independent. Keep stable IDs, sparse supported intervals, immutable evidence and original geometry/history. Source research may support geographic decisions, but technical maintainers own schema, code, infrastructure and geographic releases. Luna owns source research and supported factual imports.

## Start, implement and integrate

1. Inspect labeled GitHub Issues, open PRs and lane branches. Choose an unclaimed engineering issue, post scope and planned validation in its comments, and assign yourself when possible. Link dependencies explicitly. Large issues may use several focused PRs or linked child issues; completing one part must not close the larger objective.
2. Use an isolated checkout/worktree. Fetch current `origin/main` and create a unique **`engineering/<job-id>`** branch, with a lower-case ID matching `[a-z0-9][a-z0-9-]{0,63}`. One focused PR addresses one issue or one part of it. After each merge, create a fresh branch from updated main for the next PR.
3. Copy `coordination/templates/engineering-progress.json` to **`coordination/engineering/<job-id>.json`**. Link the issue and keep implementation receipts, dependencies, checks and maintenance context there. This file is a resumable execution artifact, not another task-status tracker. Do not modify research campaign files or another job's progress.
4. Preserve compatibility and existing live facts. Test the actual change and retain evidence. Update the GitHub issue at milestones with date, completed scope, blockers, evidence, PR and next action. Do not rewrite archived tracker snapshots or completed receipts.
5. Push frequently and open a PR to **main**. Use exactly one `Refs #N` line for partial work or one `Closes #N` line only when all issue acceptance criteria are met. No document TODO ID is required. Include concrete behavior, validation and live deployment state. Run `node scripts/check-handoff-scope.mjs --branch engineering/<job-id> --base origin/main --head HEAD --pr-body-file /path/to/body.md` and follow applicable Codex PR attachment instructions.
6. Integrate reviewed PRs serially after affected checks pass. **Submit to the serialized worker merge queue** (`node scripts/queue-pr-merge.mjs --pr N --head SHA`), which verifies current ownership and uses the PR title as squash commit title. A merge does not automatically deploy the Site or run a migration. Close an issue only after required implementation/publication verification; keep closed issues and evidence as the work record.

## While Luna imports concurrently

Routine UI work and research imports can proceed together. Read [the parallel protocol](PARALLEL_WORK_PROTOCOL.md) before owner DDL/storage or geography changes. Imports pin release/hierarchy/footprint hashes; publication and import already share a transaction lock. A changed release requires explicit revalidation, never silent repinning or evidence transfer.

For owner maintenance, post intent on the issue and record operational context, enable/deploy server read-only maintenance, drain in-flight imports through the shared lock, perform the bounded operation, verify fresh before/after preservation, then re-enable/deploy and prove imports resume. Never hold a transaction while waiting for a person or network response. Keep credentials in authorized secret mechanisms.

## Durable handover and dates

GitHub issue comments hold dated progress, completion evidence and next actions. Preserve original raised/recorded/completed dates; unknown earlier dates remain unknown. Human work dates use America/Los_Angeles; original machine receipts keep UTC. GitHub creation dates for migrated issues describe the migration, not the original work.

End with the issue, exact branch/commit/PR, completed scope, deployment state, receipt paths, blockers and next action. Push all necessary inputs and receipts; another thread has no access to your cache/workspace. See [the immutable pre-Issues archive](archive/pre-github-issues-20261002/README.md) for original work records, not current status.

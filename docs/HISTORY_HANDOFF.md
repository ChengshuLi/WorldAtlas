# Historical-content handover for Luna

This lane researches dated attributes for approved territories. Boundary/hierarchy/source suitability research uses [GEOGRAPHY_HANDOFF.md](GEOGRAPHY_HANDOFF.md) and `type:geography`; it can also run on Luna if the user chooses. Engineering owns executable geographic migrations and publication. Neither research lane bypasses complete published regional approval for location-attribute imports.

Give a Luna thread this document and [its prompt](prompts/LUNA_HISTORY.txt). They explain research contracts, import commands and safe concurrency. **GitHub Issues is the single source of truth for TODOs, status and work history**: [open historical-research issues](https://github.com/ChengshuLi/WorldAtlas/issues?q=is%3Aissue+is%3Aopen+label%3Atype%3Ahistory-research). This document contains no live task checklist.

M engineering and N history workers must read [WORKER_COORDINATION.md](WORKER_COORDINATION.md), claim one ready 1–3-PR work item before implementation, and use the merge queue. Umbrellas are split into bounded children and never reserved by one worker.

Repository: https://github.com/ChengshuLi/WorldAtlas, integration branch **main**. Site: https://worldatlas-explorer.chengshu-li-2013.chatgpt.site/, owner-private. Read `AGENTS.md`, [scope guidance](HISTORICAL_RESEARCH_TODO.md), [LUNA_DATA_HANDOFF.md](LUNA_DATA_HANDOFF.md), [RESEARCH_IMPORT_WORKFLOW.md](RESEARCH_IMPORT_WORKFLOW.md), [ATTRIBUTE_CONTRACT.md](ATTRIBUTE_CONTRACT.md) and [PARALLEL_WORK_PROTOCOL.md](PARALLEL_WORK_PROTOCOL.md).

## Current gate: source-only work

The global macro partition is approved and published. Engineering now audits and publishes completely reviewed regional branches inside the fixed scopes in `data/macro-foundation/regional-handoffs.json.gz`. The v2 `data/research-geography-gate.json` opens only approved subjects in those branches; no branches are currently approved. Source research, lawful archives, staging and dry runs may proceed. Content claims require explicit region IDs and closed macro/regional approval dependencies. Do not design geography or bypass the gate. Read [GEOGRAPHY_RESEARCH_READINESS.md](GEOGRAPHY_RESEARCH_READINESS.md).

## Preserved starting point and content contract

The Site uses production Neon PostgreSQL and R2, with bounded validation, immutable claims and idempotent imports. The checkpoint retains ownership/environmental products, 3,588 dated names, 396 religion records, 9,301 separate-settlement estimates and original archives. Preserve completed research. Interrupted GHSL preparation is not validated import content. Recheck current live state before continuing.

Store supported sparse half-open intervals, not annual snapshots. Keep stable entity IDs, original source bytes/hashes, licenses, methods, uncertainty and fixed classifications. Missing evidence remains unknown. Present-day physical reference context is separately labeled; it is not historical evidence and cannot justify widening observation intervals. Research gaps such as 2025 using actual sources.

## Select a campaign and preserve evidence

1. Inspect labeled GitHub Issues, comments, active PRs and campaign directories before choosing disjoint geography/time/attribute/source scope. Post your bounded scope and sources on the issue and claim it when possible. Worldwide objectives remain open until their complete coverage is evidenced; use linked child issues when useful.
2. Create a unique **`research/<campaign-id>`** branch from fresh `origin/main` in an isolated checkout/worktree. You own **only `research/campaigns/<campaign-id>/`**. Do not edit shared handovers, code, schema, infrastructure, category registries, grid assets or geographic releases. Research factual JSON and notes using existing tools; refer engineering blockers to a linked engineering issue.
3. Copy `coordination/templates/research-progress.json` into your campaign directory and link the GitHub issue. Keep original inputs, lawful source bytes/restoration manifests, bundles, release pins, partial/final receipts and read-back there. This is an execution/resume artifact; task status and dated progress belong to GitHub Issues.
4. Obtain the current `/api/geography/release`, capabilities and capacity through documented private access. Save the exact release and pin every bundle. Credentials must never enter chat/Git/arguments; the GitHub Neon management key is not an import token.
5. Compile and validate supported factual JSON and retain staged inputs. After the global gate opens, import bounded idempotent batches and retain receipts after every commit. Verify claim/source/interval read-back and selected-year results. Preserve partial progress and report uncovered scope honestly.

Example commands after saving factual input and current release:

```sh
node scripts/prepare-research-bundle.mjs research/campaigns/CAMPAIGN/input.json research/campaigns/CAMPAIGN/geographic-release.json research/campaigns/CAMPAIGN/bundle
node scripts/import-research-bundle.mjs https://worldatlas-explorer.chengshu-li-2013.chatgpt.site/ research/campaigns/CAMPAIGN/bundle --dry-run
node --use-env-proxy scripts/import-research-bundle.mjs https://worldatlas-explorer.chengshu-li-2013.chatgpt.site/ research/campaigns/CAMPAIGN/bundle
```

Replace `CAMPAIGN` with your unique ID. Use documented atomic phases for sourced dated membership/existence. Generic subjects/relationships and licensed media may use supported imports; new domain UI and geographic identity/footprint migrations belong to engineering.

## Incremental PRs and concurrent imports

Push evidence frequently and open a focused PR to **main** addressing one issue or part of it. Large issues may have multiple PRs. Use exactly one `Refs #N` line for partial work, or one `Closes #N` only when all acceptance criteria are verified. Include source/import/read-back evidence and unresolved questions. Run `node scripts/check-handoff-scope.mjs --branch research/<campaign-id> --base origin/main --head HEAD --pr-body-file /path/to/body.md`; follow applicable Codex PR attachment instructions. Maintainers integrate validated PRs serially with **squash merges using the PR title as commit title**. After each merge, branch afresh from current main; preserve earlier campaign directories and link them rather than modifying another campaign's files.

Import success and Git merge are separate events: a fact may already be live before its PR merges. Check existing receipts/API before retrying. Publication and imports are transactionally serialized. On changed release, maintenance or capacity errors, retain pins/receipts, stop after bounded retries and continue independent research; never silently repin or weaken constraints. Resume the same active campaign serially if another thread already owns it.

## Work history and handover

Update the issue at milestones with dates, actual coverage, evidence, blockers and next action. Retain closed issues and original raised/recorded/completed dates. Human work dates use America/Los_Angeles; receipts retain exact UTC timestamps. Unknown earlier dates remain unknown; completing one batch does not close a worldwide objective.

Before ending, push every source note, input, bundle and receipt needed by a fresh thread. Report issue, branch/commit/PR, imports/read-back and remaining questions. Keep this document as instructions, not a parallel TODO tracker. Original records are preserved in [the pre-Issues archive](archive/pre-github-issues-20261002/README.md).

<div hidden aria-hidden="true">

<!-- Empty legacy markers retained for the trusted pre-migration PR guard only. No tasks are tracked here. -->
<!-- RESEARCH-CAMPAIGNS:START -->
| ID | Scope | Status | Raised | Recorded | Completed | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
<!-- RESEARCH-CAMPAIGNS:END -->

</div>

## Issue lifecycle accuracy

Read [ISSUE_LIFECYCLE.md](ISSUE_LIFECYCLE.md). Authors reconcile original acceptance and next actions before moving on; reviewers check closure/continuation independently of merging. Dependency owners maintain direct dependents. Between jobs review up to three neglected unclaimed same-lane readiness problems. Use shared read-only readiness checks before readying and claiming; preserve scientific/publication gates and canonical ownership. Existing chats refresh before their next job; Main handles exceptional decisions.

Read docs/AUDIT_FAILURE_PREVENTION.md on current main before the next job or review. Identify the consequential acceptance claims and independently test applicable consumed-input/code, identity/join, source/method, safe-reproduction, nonvacuous-control and operating-limit invariants. Use shared evidence helpers or an explicitly reviewed equivalent; reviewers derive expectations from original acceptance and independent records before relying on author tests. Exercise real entry points and adjacent paths for corrective PRs; record unexecuted proof as a limit. Keep exact-head review, original evidence, scientific/publication gates and focused research CI. Adoption requires actual subsequent handoffs, not just this prompt edit.

## Prepare for the first review

Follow [AUTHOR_PREFLIGHT.md](AUTHOR_PREFLIGHT.md) before the next job and before
requesting its first review. Select the checks implicated by the original acceptance
and changed behavior from the start; preserve source-only focused CI. Resolve quick
ownership/evidence errors before review, while long regressions and substantive
independent review may proceed in parallel. The guide supplies practical helper and
command details, meaningful adverse cases and existing-chat refresh text; author
preflight does not replace independently derived reviewer expectations.

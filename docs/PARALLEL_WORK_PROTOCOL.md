# Concurrent engineering, geography and content research

M geography, N engineering and P history workers follow [WORKER_COORDINATION.md](WORKER_COORDINATION.md). Choose a bounded work item; record worker ID, branch and scope in its ordinary issue comments. Do not reserve umbrellas. Use the merge queue and one designated Site publisher. [Worldwide geographic approval](GEOGRAPHY_RESEARCH_READINESS.md) now gates all new location-attribute imports; research workers stage sources only until engineering closes that gate.

[THREE_THREAD_START.md](THREE_THREAD_START.md) links the issue-creation, engineering, geography and history-research handovers/prompts. Issue creation changes GitHub Issues only; it does not compete for worker-owned files or production imports.

GitHub Issues is the single source of truth for TODOs, current status and work history. Handover documents and prompts remain entry instructions. Execution files preserve reproducible inputs and receipts, not competing task-status lists. Existing live facts are authoritative independently of a PR's merge state.

| Concern | Engineering | Historical research / Luna |
| --- | --- | --- |
| Entry document | `docs/ENGINEERING_HANDOFF.md` | `docs/HISTORY_HANDOFF.md` |
| Prompt | `docs/prompts/ENGINEERING.txt` | `docs/prompts/LUNA_HISTORY.txt` |
| GitHub type label | `type:engineering` | `type:history-research` |
| Branch from current main | `engineering/<job-id>` | `research/<campaign-id>` |
| Owned execution artifact | `coordination/engineering/<job-id>.json` | `research/campaigns/<campaign-id>/progress.json` |
| Git scope | Code/tests, maintainer documentation, geography releases; preserve research and other jobs | Own campaign directory only; no shared document edits |
| Live actions | Reviewed deployment/geography/owner maintenance | Supported factual imports and licensed media via existing API |

Geography researchers use `docs/GEOGRAPHY_HANDOFF.md` and `docs/prompts/GEOGRAPHY.txt`, label `type:geography`, branch `geography/<job-id>`, and the issue's exact evidence ownership prefixes. They do not execute migrations, update shared geography, perform live imports or publish. The existing table's engineering geographic releases and historical content responsibilities remain distinct.

Read [LOCAL_WORKSPACES.md](LOCAL_WORKSPACES.md). Allocate isolated checkouts through `scripts/local-workspace.mjs`; keep bounded work/review slots, include exact required sparse inputs, and release finished slots after preserving unique work. Do not retain a full checkout per task or review revision. Existing chats must refresh their saved instructions.

## Issue workflow and incremental PRs

Use existing issues/PR discussions to record scope, dependencies, evidence and
remaining work. Labels and issue forms are optional. Coherent changes can address
multiple related issues, or proceed without a new issue. There is no required body
syntax. Use GitHub closure keywords only for acceptance actually completed.

Create a fresh unique Git branch from current `origin/main`, using an isolated
managed checkout. Lane prefixes are conventions. Preserve other workers' files and
branches; coordinate overlap before editing. Submit the reviewed exact head through
the serialized queue, which validates the current-main candidate and actual tests,
then squash-merges using the PR title. It grants no live-operation authority.

## Git ownership and durable evidence

Research only edits its campaign directory. Shared handover updates are engineering work; task progress never requires a shared Markdown edit. Geography edits only issue-declared `data/regional-review/<packet-id>/` or `research/geography/<campaign-id>/` directories; local reproductions cannot mutate the baseline or call live APIs. Engineering cannot change these evidence directories, history campaign directories or another job's progress. It consumes source/proposal evidence and writes supported migrations elsewhere. Ownership is coordinated by distinct workers and the parent. Ordinary queue
admission does not fetch issue contracts or police labels/branch prefixes. Exact
candidate files and real scientific/consumer checks determine integration safety.

Keep lawful original sources/restoration manifests, factual inputs, bundles, release pins and import/read-back receipts in the campaign directory. Templates under `coordination/templates/` are execution artifacts. A follow-up PR uses a new directory and links preserved prior campaign evidence; it does not overwrite another campaign. Push early/often, attach PRs as instructed and leave exact branch/commit/issue/PR and next action. Fresh threads cannot access your caches or private credentials. The pre-Issues tracker archive and migration receipt remain immutable snapshots.

## Live data safety

Imports are immutable, bounded, transactional and idempotent by ingestion identity. Duplicate IDs cannot conceal conflicts. Compiler/importer pins release, hierarchy and footprint hashes. PostgreSQL imports and geographic publication share advisory transaction lock `(807245315,1)` and fresh reads after waiting; obsolete new batches stop. Previously committed byte-identical retries retain original evidence and context. Changes require explicit migration/revalidation receipts, never silent repinning or evidence transfer.

Concurrent writes trigger bounded read retries/atomic caches. Use current live revision/counts rather than permanently expecting checkpoint 1321. Different research campaigns must have disjoint scope or an explicit dependency; file ownership alone cannot prevent duplicate imports. Scope notices belong to issue comments and execution artifacts. These mechanisms preserve integrity, not source accuracy or unlimited capacity.

## Maintenance and geography releases

Routine UI development and factual imports proceed concurrently. For owner DDL/storage changes, record intent on the engineering issue, enable/deploy `ATLAS_READ_ONLY=1`, drain in-flight mutations through the shared lock, execute a bounded serialized change, verify fresh before/after preservation/API compatibility, then re-enable/deploy and prove imports resume. Never hold a database transaction while waiting for a person or network response.

Provider-management workflows are **manual-dispatch only**. Merging a PR does not invoke storage transfer or forward DDL. Original successful production receipts remain immutable; do not rerun the baseline transfer merely because it is on main.

Maintenance returns retryable HTTP 503 before mutations. Importers retry boundedly and retain partial receipts; Luna then continues independent source research/preparation. Geographic publication preserves stable/predecessor identities, original evidence and versioned crosswalks. Maintainers supply supported revalidation and new inputs; Luna retains obsolete bundles/pins and waits rather than silently changing them.

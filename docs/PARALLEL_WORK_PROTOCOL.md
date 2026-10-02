# Concurrent engineering and content research

Engineering and Luna use separate handovers, prompts, branches and owned progress files. `work` is the integration branch, not a shared working checkout. Existing live facts are authoritative independently of a research PR's merge state.

| Concern | Engineering lane | Luna research lane |
| --- | --- | --- |
| Entry document | `docs/ENGINEERING_HANDOFF.md` | `docs/HISTORY_HANDOFF.md` |
| Copy-ready prompt | `docs/prompts/ENGINEERING.txt` | `docs/prompts/LUNA_HISTORY.txt` |
| Queue | `docs/ENGINEERING_TODO.md` | `docs/HISTORICAL_RESEARCH_TODO.md` |
| Branch | `engineering/<job-id>` | `research/<campaign-id>` |
| Owned progress | `coordination/engineering/<job-id>.json` | `research/campaigns/<campaign-id>/progress.json` |
| Changes | Source/tests, maintainer documents, reviewed geographic products and release receipts; no researcher-owned campaign files/rows | Files inside that campaign's directory and its own `CAM:<campaign-id>:…` historical-tracker rows only |
| Production action | Validated deployment/geographic publication/maintenance | Supported content imports and media through existing APIs |
| Shared integration | Technical maintainer merges reviewed PRs into `work` serially and updates central summaries | Push campaign PR; maintainer integrates it |

## Start and resume

Each thread uses its own checkout/worktree from current `origin/work`. Pick a unique ID matching `[a-z0-9][a-z0-9-]{0,63}`. Inspect remote lane branches and PRs, not only merged files, for active work. Publish the scope/progress file early. Another thread resumes an existing campaign/job branch serially; two threads must not write the same campaign/job concurrently. Multiple Luna threads must use different campaign IDs and avoid overlapping geographic/time/attribute research unless explicitly coordinated.

Research directories contain original input, source notes/bytes or restoration manifests, bundles, receipts and a progress file. Technical-maintainer progress contains implementation state, checks, deployment/maintenance and dependencies. Templates are under `coordination/templates/`. Progress-file status values are `active`, `blocked`, `review`, `complete`; tracker items use `open`, `active`, `blocked`, `done`. Completion requires stated evidence and does not automatically mean deployed or globally researched. Fill actual values; template nulls do not establish coverage. Preserve raised/recorded/completed dates in America/Los_Angeles and retain exact UTC receipts.

Push lane branches frequently and create PRs against `work`. The guard checks every changed old/new path, including rename sources. Research may change its directory and its own historical-tracker rows only: instructions, global objectives, other campaigns, original dates and completed milestone rows are preserved. Engineering preserves researcher-owned directories/rows and other jobs' progress. CI runs trusted base code against the candidate checkout with read-only permissions and no secrets. This checks Git/document ownership, not historical accuracy or database permissions. GitHub branch protection has not been configured by this setup; maintainers must honor the integration rule and should require the scope check if repository settings permit.

The maintainer integrates one PR at a time against fresh `origin/work`, preserving source, receipts and unrelated files. Resolve genuine code/content dependencies explicitly; never force-push `work`, copy over another thread's checkout or overwrite research files with an old snapshot. If revalidation is required, retain original bundles and create a separate maintainer migration/revalidation receipt. Engineering owns its authoritative tracker and shared operational summaries; Luna owns its campaign files and dated tracker rows. Global research objectives are maintained during integration. If simultaneous research PRs add rows at the same insertion point, merge all distinct rows; never choose one side wholesale. Git conflicts can require a serial integration, but neither lane may discard the other's work.

## Live data safety already implemented

- All normal source/content imports are immutable, bounded, transactional and idempotent by ingestion identity. Duplicate stable IDs must not be changed to conceal a conflict. New evidence/corrections use the documented source and retirement contracts.
- Compiler/importer pins release ID, hierarchy hash and footprint hash. A production batch checks those pins inside its transaction. PostgreSQL imports and geographic publication share advisory transaction lock `(807245315,1)` and fresh reads after waiting. A publication cannot race a new unvalidated old-release import into the same transaction.
- An import that committed before publication remains preserved with its original context; a byte-identical committed retry is recognized. That does not authorize a different batch or automatic evidence transfer to a changed footprint. The importer stops on changed release and retains partial receipts.
- Live revision changes during reads trigger bounded retries/atomic cache behavior. Future validation must use the actual live revision/counts, not permanently expect the original 1321 checkpoint after new research.

These mechanisms protect integrity; they do not adjudicate contradictory historical sources or guarantee unlimited capacity. Research still requires sourced methods and documented uncertainty.

## Maintenance and geographic changes

Routine UI development and factual imports can proceed together. For owner DDL/storage changes, the maintainer records intent/current scope in its progress file, enables and deploys `ATLAS_READ_ONLY=1`, and waits for in-flight transactions through the shared database lock before the bounded operation. Keep owner migration operations serialized. Verify fresh before/after preservation and API compatibility; remove maintenance, deploy and prove imports resume. Never hold a database transaction open while waiting for an agent/network response.

During maintenance the server rejects mutations with retryable HTTP 503 before database/bucket work. The existing importer retries a bounded number of times and preserves partial receipts; Luna then stops imports and continues source research or network-free preparation. This remains safe even if a Git notice arrives late.

For a geographic release, preserve stable/predecessor identities and original evidence. Publish a versioned crosswalk and explicit supported revalidation result. Luna retains the old bundle/pins and waits for a compatible campaign input; it never silently edits release hashes. Engineering can continue preparing migrations while Luna imports into the currently published release; publication provides the transaction boundary.

## Durable handovers

Users give each new thread one lane document and its prompt. Those documents link contracts/queues; campaign/job-specific progress lives in unique paths and is accessible from GitHub even before merge. End each thread with branch, exact commit, PR, completed scope, live import/deployment state, evidence paths, blockers and next action. Credentials remain in authorized server/session mechanisms and are excluded from every handover.

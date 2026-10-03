# Many engineering, geography and history workers

M geography, N engineering and P history-research chats may work in isolated checkouts. GitHub Issues remains the work record; a serialized bot-managed reservation prevents two cooperative workers from taking the same issue. Threads using the same GitHub account need distinct **worker IDs**, not just an assignee.

## Small, reviewed work items

Each worker holds at most one active work item; do not mass-reserve the queue. Actionable issues have exactly one type label, `kind:work-item`, `status:ready`, an explicit scope and a **1–3 PR budget**. Larger objectives are `kind:umbrella`, cannot be claimed and are decomposed into bounded child issues. An umbrella can have many children, while each child normally completes in one PR and at most three. Open dependencies or `status:blocked` prevent claims. Completing a child does not close its parent.

The issue-creation thread reviews scope, dependencies and overlap before marking ready. Include one machine-readable block in the issue body (GitHub is its sole authority):

```text
<!-- worldatlas-work:v1
{"max_prs":2,"depends_on":[],"scope":"Concrete acceptance scope","mode":"engineering"}
-->
```

Modes are `engineering`, `geography`, `source-only` and `content`. `type:geography` uses `geography/<job-id>` branches and must declare 1–8 disjoint safe `owned_paths` prefixes, each exactly `data/regional-review/<packet-id>/` or `research/geography/<campaign-id>/`. Existing review packets retain their declared directories. Its work is source evidence, proposals and local reproductions only. Engineering preserves this evidence and implements executable migrations/integration/publication. Models are selected by the user; geography research can run on Luna. See [GEOGRAPHY_HANDOFF.md](GEOGRAPHY_HANDOFF.md). Source-only research defines disjoint subjects/source collections/time/attributes and stages evidence without imports. Content additionally needs `geographic_release`, `scope_manifest` and `territory_match_review`, plus `region_ids` and an explicit permitted subject scope in its manifest. Claim automation requires completed global macro approval and a completed published full-branch regional certificate with matching release pins. No branches are approved yet. See [GEOGRAPHY_RESEARCH_READINESS.md](GEOGRAPHY_RESEARCH_READINESS.md).

A geography work item declares ownership in the same machine block, for example:

```text
<!-- worldatlas-work:v1
{"max_prs":2,"depends_on":[33,36],"scope":"Pinned regional source/semantic review packet; evidence and bounded proposals only","mode":"geography","owned_paths":["data/regional-review/regional-review-packet-a/"]}
-->
```

Inspect other ready issues' declared prefixes before accepting ownership. The canonical geography claim retains the exact prefix array; scope changes require coordinated release/reclaim. No geography live-operation reservations are allowed. Engineering reads but preserves both geography namespaces; integration outputs go elsewhere. Trusted CI and the serialized merge queue verify actual GitHub-owned paths, including rename sources; evidence must use ordinary files rather than symlinks/submodules.

A ready label is a reviewed decision, not an automatic conclusion from complete database chains. Two separate issues can still overlap; triage must record subsystem/resource or geography/source/time/attribute scope and dependencies. A worker discovering overlap stops the conflicting part and coordinates on the issues. Git claims are cooperative reservations, not security isolation or an unlimited production-capacity guarantee.

Geography proposals → bounded engineering corrections/integration → complete validated published regional branch → permitted historical imports. Independent UI/performance/infrastructure engineering and source-only historical collection may run in parallel throughout. Inter-region inconsistencies require a coordinated issue covering all affected neighbors; no unilateral boundary or certificate edits. After a published boundary change, engineering revalidates affected release pins, complete-branch certificates and content scopes while retaining earlier records/evidence.

## PR review size

Keep PRs focused on one issue or a coherent part. Aim for fewer than 1,000 changed non-test lines as a soft review target, not a hard cutoff. Larger focused PRs are allowed when splitting would make implementation, migration or validation harder to review safely; explain the reason in the PR description. Report generated-data changes separately. Do not compress code or documentation merely to meet a line budget. The soft target does not change issue PR budgets, lane ownership, required checks or serialized squash merges. Split oversized issue scopes into bounded children when needed, rather than fragmenting one coherent change just to meet a line count.

## Claim before implementation

Read fresh main, inspect the issue and its active PRs, choose a globally unique worker ID (for example the chat ID or a UUID) and a planned fresh lane branch. From the repo:

```sh
node scripts/issue-lease.mjs claim --issue 22 --worker YOUR-UNIQUE-WORKER --branch engineering/YOUR-JOB --out /tmp/claim.json
node scripts/issue-lease.mjs inspect --issue 22
```

Replace placeholders. Begin only after the command exits successfully and its result says `accepted: true`. Retain the receipt, claim ID and workflow link in your owned execution artifacts. A `status:claimed` label is visible convenience; the canonical bot-authored comment is authority. Public ownership nonces prevent accidental collisions, not impersonation by someone with repository write access.

Per-issue GitHub Actions concurrency serializes claim/renew/release/recover on **main**. Different issues may reserve concurrently. GitHub allows one running and one pending run per group; later requests may cancel pending requests. The client retries canceled runs boundedly with jitter and never treats cancellation, timeout or missing confirmation as success. Lack of Actions dispatch/read permissions is a blocker; do not fall back to an uncoordinated comment-only claim.

## Keep, rotate and release a reservation

The lease lasts 24 hours. Renew at work milestones and before each live operation/merge; heartbeat periodically during sustained work. Use your actual claim ID:

```sh
node scripts/issue-lease.mjs renew --issue 22 --worker YOUR-UNIQUE-WORKER --branch engineering/YOUR-JOB --claim-id CLAIM-ID --out /tmp/renew.json
node scripts/issue-lease.mjs release --issue 22 --worker YOUR-UNIQUE-WORKER --branch engineering/YOUR-JOB --claim-id CLAIM-ID --out /tmp/release.json
```

Only the holder can renew/release. Renewal can rotate to a fresh branch after a previous PR merges/closes and live work is verified. An open PR or `live_work:true` prevents branch rotation/release. Set `--live-work true` before a live operation, then renew with `--live-work false` only after its outcome/receipts are settled. Source-only workers do not perform live imports. Do not leave work pending without recording its branch, sources, receipts and next action.

Expiry does not authorize destroying or silently taking another worker's work. A stale reservation requires operator inspection and explicit recovery: label `coordination:recovery-approved`, an expired lease, no active PR/live operation, and a reason supplied with `recover`. Preserve the old branch/artifacts and coordinate unresolved evidence before approval. Live/PR handovers require their existing owner/integrator first; automatic recovery is refused.

## PRs and the merge queue

Each focused PR targets main and has exactly one `Refs #N` for partial work or `Closes #N` for full acceptance. CI checks the current claim and exact branch as well as issue type/scope. All working lanes submit merges through:

```sh
node scripts/queue-pr-merge.mjs --pr PR-NUMBER --head VERIFIED-HEAD-SHA
```

Inspect the exact returned run name/request ID, wait for its completion and read the bot-authored **Merge result** comment on the PR with that request ID. Claims similarly return bot-authored **Reservation result** comments on their issues. Artifact copies remain available for audit, but the clients do not depend on artifact downloads. Queued or successful workflow execution alone is not proof of an accepted merge. The queue serializes integration, rereads the claim, checks the exact head and successful current checks, requires latest main included, and squash-merges with the PR title as commit title. If another merge advanced main, update your branch, rerun affected checks and resubmit. Canceled pending merge requests may be retried; queues are not FIFO.

After each merge, release a completed issue or renew its claim onto a fresh branch for its remaining bounded part. When three PRs are insufficient, stop extending it and split the remaining scope into reviewed children/follow-ups. Existing closed Issues, source evidence and dates are retained.

One explicitly designated engineering publisher coordinates Site deployments, geographic releases and owner maintenance. Workers do not publish competing versions independently. The GitHub merge queue does not serialize manual Site operations or a different repository; use the existing deployment/maintenance protocol. Branch protection is not configured, so workers must honor the queue and checks; direct merge permissions are not revoked by this setup.

## Current research policy

The user's top-down policy requires **global continent/subcontinent/region boundary approval, then complete published regional branches before their location-attribute imports**. Other regional interiors may remain unfinished. See [TOP_DOWN_GEOGRAPHY_WORKFLOW.md](TOP_DOWN_GEOGRAPHY_WORKFLOW.md). `data/research-geography-gate.json` records the macro approval and regional certificates; the macro partition is approved and published, but no complete regional branches are approved, so content imports remain closed. Every fixed regional scope is in `data/macro-foundation/regional-handoffs.json.gz`; use bounded children for parallel interior audits.

Only engineering may approve and publish the partition/branches with retained sourced evidence, exact subject IDs and matching release/hierarchy/footprint pins. The worldwide umbrella #7 stays open until all branches finish; it no longer directly blocks a certified branch. History workers do not design geography. Geography researchers may propose sourced boundary/hierarchy changes in their owned evidence; only engineering integrates and certifies them. Source-only collection/staging and dry runs may continue, but source populations/primary culture/religion still need the intended territory and supported interval before imports. The private API and retained facts remain intact; the cooperative claim/CLI gate is not new server authorization. Region completion creates a research handover/ready queue, not an automatic new chat or private credential grant.

## Evidence and independent review

Follow `docs/PREMERGE_EVIDENCE_REVIEW.md` and the authoritative `.github/evidence-policy.json`. New work after activation declares exact subjects/pins and its owned manifest in the issue contract; legacy scopes remain preserved. Prepare versioned whole-file evidence, immutable scientific helper results and honest source/publication limits. Request a distinct worker's substantive review tied to the exact PR head; never self-review under a second worker ID. The queue rechecks evidence and review; green CI alone does not approve geography or authorize imports.

# Many engineering, geography and history workers

M geography, N engineering and P history-research chats may work in isolated checkouts. GitHub Issues remains the work record; a serialized bot-managed reservation prevents two cooperative workers from taking the same issue. Threads using the same GitHub account need distinct **worker IDs**, not just an assignee.

Read [LOCAL_WORKSPACES.md](LOCAL_WORKSPACES.md). Allocate isolated checkouts through `scripts/local-workspace.mjs`; keep bounded work/review slots, include exact required sparse inputs, check storage before generation/installations, and release finished slots after preserving unique work. Do not retain a full checkout per task or review revision. Existing chats must refresh their saved instructions.

## Chat identity

Worker identity belongs to the chat, not the issue, branch, goal, checkout or GitHub account. In Codex, use the exact current CODEX_THREAD_ID as the author worker ID and keep it across successive jobs. Never copy an ID from another chat, a reservation, a checkout registry, a handoff or inherited/forked context. A fork/new chat has its own identity. Before claiming or allocating, compare the chosen ID with this chat’s actual ID; if another chat owns the claim/slot, leave it untouched and do not treat it as your work or blocker. New author claim/recover and work-allocation commands reject mismatches when CODEX_THREAD_ID is available. Outside Codex, establish one unique persistent ID for that chat; the tools cannot verify chat identity when the environment does not supply it. Do not unset or override CODEX_THREAD_ID to bypass the check.

Active legacy work keeps its recorded worker ID only for finishing, renewing and releasing that exact claim/checkout. Do not rename an active claim, take over another chat’s slot or start new work under the legacy ID. After verified merge/handoff and safe release, use this chat’s ID for the next claim and allocation. Independent reviewer agents keep their own stable distinct reviewer IDs (actual agent identity when available); an inherited parent CODEX_THREAD_ID does not identify a sub-agent. Never invent a second ID for self-review. Review allocation is exempt from the author-ID check because review sub-agents may inherit their parent’s environment; review identity remains cooperative and must be checked by the reviewer.

## Small, reviewed work items

Each worker holds at most one active work item; do not mass-reserve the queue. Actionable issues have exactly one type label, `kind:work-item`, `status:ready`, an explicit scope and a **1–3 PR budget**. Larger objectives are `kind:umbrella`, cannot be claimed and are decomposed into bounded child issues. An umbrella can have many children, while each child normally completes in one PR and at most three. Open dependencies or `status:blocked` prevent claims. Completing a child does not close its parent.

At each new claim, choose eligible `urgent` issues in your own lane first, then other `follow-up` issues, then other ready work. Eligible means an open, unclaimed, unblocked `kind:work-item` labeled `status:ready`, with satisfied dependencies and authorized scope. Preserve the existing regional approval and import gates. Finish or safely hand over your current claim; do not abandon it to preempt another worker. Urgency never bypasses readiness, ownership, review or publication/import rules. If urgent candidates are all blocked, already claimed or outside your lane, continue another eligible item and record why they were unavailable in your issue checkpoint.

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

Read fresh main, inspect the issue and its active PRs, use this chat’s stable author ID as defined above and a planned fresh lane branch. From the repo:

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

Only the holder can renew/release. Renewal can rotate to a fresh branch after a previous PR merges/closes and live work is verified. An open PR or `live_work:true` prevents branch rotation/release. For an operation directly executed under the holder’s reservation, set `--live-work true` before it, then renew with `--live-work false` only after its outcome/receipts are settled. Delegated Site publication uses the publisher-owned operation record described below; the implementation holder does not toggle its flag for the publisher. Code-enforced owner maintenance uses the same implementation handoff; `CURRENT_POSTGRES_RECOVERY.md` supports a bounded publisher-owned production-only child after safe original-claim release, while preserving its legacy path for already-agreed operations. A work item with `production_operation` is reserved for its declared publisher, not ordinary implementation workers. Source-only workers do not perform live imports. Do not leave work pending without recording its branch, sources, receipts and next action.

Expiry does not authorize destroying or silently taking another worker's work. A stale reservation requires operator inspection and explicit recovery: label `coordination:recovery-approved`, an expired lease, no active PR/live operation, and a reason supplied with `recover`. Preserve the old branch/artifacts and coordinate unresolved evidence before approval. Live/PR handovers require their existing owner/integrator first; automatic recovery is refused.

## PRs and the merge queue

Each focused PR targets main and has exactly one `Refs #N` for partial work or `Closes #N` for full acceptance. CI checks the current claim and exact branch as well as issue type/scope. All working lanes submit merges through:

```sh
node scripts/queue-pr-merge.mjs --pr PR-NUMBER --head VERIFIED-HEAD-SHA
```

Inspect the exact returned run name/request ID, wait for its completion and read the bot-authored **Merge result** comment on the PR with that request ID. Claims similarly return bot-authored **Reservation result** comments on their issues. Artifact copies remain available for audit, but the clients do not depend on artifact downloads. Queued or successful workflow execution alone is not proof of an accepted merge. Candidate preflight and isolated integration tests run in parallel across workers. Only the final authority recheck and squash merge share the short serialized integration slot; tests never hold that slot. The merge uses the PR title. It tests GitHub’s exact current-main plus reviewed-head merge tree without updating the worker branch, and rechecks ownership, evidence/review, check-runs and commit statuses. Reviewed changed-file blobs and modes must remain identical in the combined tree, including removed/renamed paths. Conflicts or changed reviewed bytes require author intervention and fresh substantive review; no automatic conflict resolution is allowed. The client waits for a final bot receipt and verifies the actual merged PR; it retries cancellations or stale merge objects/base advances at most three times with the same authored head. It discovers runs through bounded paginated search, then polls the latched run ID. Queues are not FIFO.

Preparation refreshes GitHub's asynchronous candidate immediately after eligibility
checks and verifies its parents before fetching complete trees. A stale or unavailable
candidate is polled at most six times, with two-second waits and a 30-second polling
deadline (in-flight API calls retain their existing timeout). A successful wait repeats
authority validation. Changes to the reviewed head, PR scope, issue contract or
ownership fail; actual main/PR-base advances require renewed preflight and evidence
vintage validation. Rejections retain expected/actual commit IDs, observation time
and attempt count. Worker commands and branch ownership do not change; no automatic
rebases or conflict resolutions occur. This reduces stale-preview retries, not the
need to validate a genuinely changed integration base. Testing remains parallel,
and only final merging is serialized. If the automatic preview stays stale, trusted
preparation creates an owned disposable `worldatlas-integration/pr-N-REQUEST-RUN`
branch at the exact main SHA and asks GitHub to merge the exact reviewed SHA there.
It validates the resulting parents and reviewed tree before tests. This never edits
main or worker branches and executes no candidate code with write credentials.
The final job deletes only that exact owned ref at its expected SHA, including on
test/merge rejection. Failed cleanup is recorded for operator inspection. Failed preparation notification
also attempts exact-owned cleanup; an unconfirmed ref creation records its possible
resource without deleting a collision. Canceled
jobs may leave an owned ref and require cleanup, never blind deletion or proof of
merge. Candidate tests still check out immutable SHAs with read-only permissions.

Base-dependent evidence still needs refresh: a metric labeled current must match the actual PR-base vintage, and original-file receipts must match actual base bytes. Disjoint main changes with unchanged scoped inputs can reuse review; fresh global measurements or changes to the reviewed inputs cannot. Preserve the earlier evidence, refresh in a new vintage, and obtain exact-head review when needed. Trusted preflight selects checks by every changed and renamed path. Code, workflow, schema and core-data changes run the complete unit suite across three parallel shards, plus one hosted package build. Isolated geography/history campaign evidence and engineering-owned receipts or Markdown/text docs run the focused ownership/evidence/review/invariant suite, without rebuilding the unchanged application. Both profiles run in isolated read-only jobs without secrets or persistent checkout credentials. They retain the same exact candidate, reviewed-byte, claim and evidence gates; a renamed runtime file cannot evade full regression. Prepare/final jobs execute only fresh trusted main code. Tests are bounded to35minutes, trusted jobs to10minutes each; unfinished heads fail preflight rather than holding the slot for worker action.

The full runner keeps packaged-asset checks on the build job and the expensive local model/migration file on a separate job. Measured database-neighbor suites use the otherwise lighter job; the remaining discovered files retain deterministic assignment. Every file still runs exactly once. Named placement is a scheduling choice, not a runtime guarantee; compare actual complete workflow times rather than summed TAP durations.

Package inputs are declared in `.github/package-inputs.json` and physically copied into an isolated build source image by the standard package builders; see [PACKAGE_INPUTS.md](PACKAGE_INPUTS.md). CI uses the same declaration from trusted base. Implementation edits do not invalidate later research through code fingerprints. Research becomes a package input only through an explicit reviewed declaration change. A packaged research PR runs its research evidence checks plus package checks; package applicability alone does not select full application regression.

For unpublished research, retain the canonical claim/scope/evidence gates, focused ownership/evidence/invariant checks, independent exact-head review and exact current-main integration checks. Package CI records applicability without a candidate checkout, npm/pip installs, budget unit tests or compilation: none of their inputs changed. Changes to the classifier, budget tools or their tests retain the full package profile. Its receipt states that no fresh package-size measurement was made. The focused suite is short; the avoidable expensive work was rebuilding unchanged package inputs. Full application tests remain required when the affected behavior is uncertain.

Package applicability selectors, their scope tests and the package-check workflow are coordination controls: their PRs run focused ownership/evidence/integration controls plus package-scope tests, rather than unrelated application regression. Full-profile discovery runs the package-scope test file once; the evidence profile includes it through the integration proof tests. Actual build/archive tools, test runners, application code and schema remain full. The package workflow still independently decides whether an archive rebuild is applicable.

Changes to the test runner require the full profile so the actual complete test inventory and scheduling are verified; they are excluded from the coordination-only allowlist.

All integrations must use this queue. GitHub’s merge endpoint guards the PR head, not the base; the final main-read/PUT interval cannot atomically exclude an out-of-band direct merge. Do not integrate directly during a queued run. If a designated exceptional repair is needed, drain/coordinate the queue first. The normal protocol serializes every writer; it does not claim a server-enforced base CAS. GitHub native merge queues are unavailable for this personally owned private repository under the current platform eligibility rules.

After a confirmed merge, the trusted queue also attempts remote head cleanup, independently of merge acceptance. It confirms the merged PR and exact reviewed head, same-repository worker lane, non-default/unprotected branch, complete open-PR head/base identities with no other use, and unchanged branch/ref SHA immediately before deletion. An already absent branch is clean; advanced, protected, shared, fork or uncertain heads remain with a durable `head_cleanup` reason. A bounded API/time budget stops oversized or slow cleanup before starting further calls. API/deletion errors are pending cleanup and never invalidate the successful merge. GitHub's automatic-delete checkbox remains enabled but is not the queue's sole cleanup mechanism. The GitHub delete-ref endpoint has no SHA guard; the final read/delete interval cannot atomically exclude an out-of-band push or new PR. Workers must use fresh branches after merging and never push to or reuse merged heads. This cleanup does not remove local branches/worktrees, original evidence, or archived PRs.

After each merge, release a completed issue or renew its claim onto a fresh branch for its remaining bounded part. When three PRs are insufficient, stop extending it and split the remaining scope into reviewed children/follow-ups. Existing closed Issues, source evidence and dates are retained.

One explicitly designated engineering publisher coordinates Site deployments, geographic releases and owner maintenance. Workers do not publish competing versions independently. The GitHub merge queue does not serialize manual Site operations or a different repository; use the existing deployment/maintenance protocol. Branch protection is not configured, so workers must honor the queue and checks; direct merge permissions are not revoked by this setup.

Implementation acceptance and production publication are separate. Workers verify ordinary changes in isolated local/preview environments and record what that proves; authorized bounded production read-only access is permitted without a deployment appointment, while writes/imports/migrations use independent test data/database and heavy load tests require coordination; they do not wait for a production deployment to merge. A complete durable publication handoff allows the implementation holder to release its claim once all PRs are merged/closed and no holder-run live operation is active. The publisher does not require that source claim to remain active or have `live_work=true` solely for delegated publication. Do not close an issue whose existing acceptance includes unverified live delivery: record its publication-only remainder on the original issue with `publisher-needed`, prevent duplicate implementation claims, and continue other ready work. Do not silently relax existing acceptance or geographic approval/import gates.

The designated publisher pins latest primary main at run start and discovers merged changes since its verified primary delivery commit, plus original issues labeled `publisher-needed` and unresolved production checks. No duplicate publication request on #714 is required. Original issues retain criteria/blockers/evidence; closed linked issues are still considered for delivery. GitHub deployment metadata indexes one bounded publisher-owned operation and its exact result, separately from per-issue acceptance. Expiry does not prove cleanup; all active/unsettled records block overlap. This remains cooperative serialization. Existing #714 operations settle under their original rules and remain preserved until backlog reconciliation/archival. See [PUBLICATION_HANDOFF.md](PUBLICATION_HANDOFF.md) for discovery, records, safe release and SQL exceptions. Existing chats must refresh saved instructions; repository edits do not modify them automatically. Auditor #726 owns separate post-merge quality review/follow-up creation.

## Current research policy

The user's top-down policy requires **global continent/subcontinent/region boundary approval, then complete published regional branches before their location-attribute imports**. Other regional interiors may remain unfinished. See [TOP_DOWN_GEOGRAPHY_WORKFLOW.md](TOP_DOWN_GEOGRAPHY_WORKFLOW.md). `data/research-geography-gate.json` records the macro approval and regional certificates; the macro partition is approved and published, but no complete regional branches are approved, so content imports remain closed. Every fixed regional scope is in `data/macro-foundation/regional-handoffs.json.gz`; use bounded children for parallel interior audits.

Only engineering may approve and publish the partition/branches with retained sourced evidence, exact subject IDs and matching release/hierarchy/footprint pins. The worldwide umbrella #7 stays open until all branches finish; it no longer directly blocks a certified branch. History workers do not design geography. Geography researchers may propose sourced boundary/hierarchy changes in their owned evidence; only engineering integrates and certifies them. Source-only collection/staging and dry runs may continue, but source populations/primary culture/religion still need the intended territory and supported interval before imports. The private API and retained facts remain intact; the cooperative claim/CLI gate is not new server authorization. Region completion creates a research handover/ready queue, not an automatic new chat or private credential grant.

## Evidence and independent review

Follow `docs/PREMERGE_EVIDENCE_REVIEW.md` and the authoritative `.github/evidence-policy.json`. New work after activation declares exact subjects/pins and its owned manifest in the issue contract; legacy scopes remain preserved. Prepare versioned whole-file evidence, immutable scientific helper results and honest source/publication limits. Request a distinct worker's substantive review tied to the exact PR head; never self-review under a second worker ID. The queue rechecks evidence and review; green CI alone does not approve geography or authorize imports.

## Applicable regression and exact-tree reuse

The integration profile defaults to `full`. Documentation text and the exact coordination paths in
`scripts/integration-profile.mjs` and the current worker's owned receipts use the
focused `evidence` profile. It includes reservation, ownership, regional import
barriers, evidence/review validation, workflow checkout and integration controls.
Source-only owned research retains its focused controls. Every changed path and
rename origin participates; unknown non-text documentation/scripts, application code, storage,
atlas data, geometry, schema, imports, builds and deployment require full regression.
The PR profile selector runs trusted base code against GitHub's complete file list and verifies the current head. Geography focused selection also reads the linked issue and paginated canonical reservation, requiring an active unexpired exact-branch geography claim with identical safe owned prefixes; missing/stale ownership fails rather than allowing reduced tests. Out-of-scope files or rename origins retain full regression;
a base without the selector runs full regression. Full shards cover every test file
exactly once, build actual packaged assets and reject skipped tests.

The queue can avoid repeating those tests only when GitHub's successful current
`merge-integration-checks.yml` run proves the entire candidate Git tree equals the
reviewed head's tested tree. That approved workflow explicitly checks out the head;
GitHub's `head_sha` alone cannot establish what a default PR merge-ref checkout tested.
The workflow and runner/profile blobs must match trusted current main. All expected
shards and their required completed steps must succeed; skipped jobs establish no
coverage. Preparation pins the run ID and attempt. The final serialized merge re-reads that run,
the same successful attempt/jobs and the usual exact-head review, evidence, ownership,
checks, candidate parents and base guards. An unavailable/untrusted proof causes
normal isolated tests; a proof revoked after preparation refuses the merge and
requires resubmission. A rerun after preparation invalidates the proof even if it succeeds. An altered
workflow/runner first passes ordinary integration.

This is cooperative GitHub Actions evidence, not independent authenticated worker
identity or a native GitHub merge queue. The existing final base check and guarded
head merge remain; outside writers must honor the same serialized queue. A green
run does not certify geographic facts, authorize imports or publish the Site.

The focused `evidence` controls use Node and repository files without installed
npm packages. Both PR regression and isolated queue regression install npm
packages only for the `full` profile. Full proof still requires successful Node
and Python installation, applicable browser setup and the actual hosted build;
focused proof requires every focused control to execute successfully with zero
skipped tests. A skipped dependency-install step is not application coverage.

# Many engineering, geography and history workers

M geography, N engineering and P history-research chats may work in isolated checkouts. GitHub Issues remains the work record. Before implementation, comment with the worker ID, branch, bounded scope and planned checks. The parent coordinates overlapping work. Threads sharing a GitHub account still use distinct worker IDs; a comment is coordination, not security isolation.

Read [LOCAL_WORKSPACES.md](LOCAL_WORKSPACES.md). Allocate isolated checkouts through `scripts/local-workspace.mjs`; keep bounded work/review slots, include exact required sparse inputs, check storage before generation/installations, and release finished slots after preserving unique work. Do not retain a full checkout per task or review revision. Existing chats must refresh their saved instructions.

## Chat identity

Worker identity belongs to the chat, not the issue, branch, goal, checkout or GitHub account. In Codex, use the exact current CODEX_THREAD_ID as the author worker ID and keep it across successive jobs. Never copy an ID from another chat, a reservation, a checkout registry, a handoff or inherited/forked context. A fork/new chat has its own identity. Before starting work or allocating, compare the chosen ID with this chat’s actual ID; if another chat owns the work/slot, leave it untouched and do not treat it as your work or blocker. New author work-allocation commands reject mismatches when CODEX_THREAD_ID is available. Outside Codex, establish one unique persistent ID for that chat; the tools cannot verify chat identity when the environment does not supply it. Do not unset or override CODEX_THREAD_ID to bypass the check.

Active legacy work keeps its recorded worker ID only for finishing, renewing and releasing that exact claim/checkout. Do not rename an active claim, take over another chat’s slot or start new work under the legacy ID. After verified merge/handoff and safe release, use this chat’s ID for the next job and allocation. Independent reviewer agents keep their own stable distinct reviewer IDs (actual agent identity when available); an inherited parent CODEX_THREAD_ID does not identify a sub-agent. Never invent a second ID for self-review. Review allocation is exempt from the author-ID check because review sub-agents may inherit their parent’s environment; review identity remains cooperative and must be checked by the reviewer.

## Coordinated work

Work on one coherent delivery goal at a time. Before implementation, identify the
worker, branch, scope, overlap and planned checks in the existing issue or PR
conversation. The parent coordinates distinct workers and handoffs. Reuse existing
issues for history and remaining acceptance; related fixes may share a PR and no
issue is required solely to satisfy the merge machinery. Labels and branch prefixes
are optional navigation aids. Ordinary work needs no machine work block, planning
count, readiness label, parsed claim, body syntax or owned-path grant.

Keep other workers' branches and evidence intact. Geography researchers stage
source evidence/proposals in their agreed regional-review or research directories;
engineering implements executable integration/publication; history research keeps
its campaign scope. Coordinate scope expansion or conflicting writers before edits.
These are human ownership responsibilities, not security boundaries based on names.
Actual import/publication authorization and source validity never come from labels.

Resolve real dependencies. Preserve original sources, identities, scientific scope,
unknowns and dated results. A completed child does not close a broader objective.
Geography proposals still require bounded engineering integration and a validated,
published complete regional branch before permitted historical imports. Cross-region
changes require joint scope and certificate/content revalidation.

## Deliver results with proportionate verification

For a delivery campaign, work backwards from the next integrated useful batch.
Use the existing issue for the batch's expected result, actual outcome and next
step. No new status form, tracker, audit sweep or performance report is required.
Count repaired gaps separately from native cells, researched candidates and valid
exclusions. Supporting code, evidence and merged PRs are means, not delivered repairs.
Production-deferred work reports verified selected/offline integration separately.

- Batch independent cases that share an admitted rule and delivery path. Deliver
  supported cases without waiting for unresolved cases that cannot affect them.
  Batch size follows actual source, integration and resource boundaries, not an
  arbitrary tiny count. Keep partial remainders and uncertain cases explicit.
- Reuse the current inventory, source findings, admitted producer and consumer.
  Ordinary subsequent batches should change inputs, assignments and release selection,
  not invent another helper, certificate or audit. A different rule/source may need
  new science; it must not hold already-supported cases hostage.
- A supporting change must remove a demonstrated obstruction to that batch. Repair
  the existing path where possible, then return to delivery. If the same phase fails
  again after a repair, or two consecutive work steps add support without advancing
  acceptance, stop expanding the approach: identify the actual bottleneck and change
  the design. Escalate only the decision that exceeds your authority, with a concrete
  alternative. This is a course correction, not a quota, automatic pause or new issue.
- Keep retained scientific results when their consumed inputs, code, parameters and
  relevant runtime assumptions are unchanged and the previous result was not invalidated.
  Inspect that applicability and reference the existing evidence; do not copy it into
  another packet or call it a new execution. Recompute only affected results. Changes
  to selection still require current-baseline conservation and actual selected-output
  verification. Unrelated main commits do not alone require repeating source research.
- Test changed logic with meaningful positive/adverse cases and run required focused CI.
  Ordinary coordination changes may include modified tests from the existing focused
  runner inventory; their ordinary authored blobs and complete runtime fixtures must
  be available. Unknown, new, removed, renamed or nonordinary test files retain full
  regression, as do application/package/native changes.
  New exact heads require renewed relevant review, not automatic full reruns by author,
  reviewer and Auditor. Repeat expensive executions only for a changed repeatability
  claim, a relevant input/method/runtime change, a suspect earlier result or an explicit
  acceptance requirement. Equal runs are not independent correctness evidence.
- Git and the exact-head review own changed-code identity and the complete diff.
  The evidence manifest binds scientific inputs/results; do not duplicate code/docs
  hashes or Git's change list in it. Existing optional receipts remain checked when
  supplied. Do not generate custom JSON saying tests passed merely to satisfy a form.
  Cite actual test output and substantive checks in the existing PR/review.
- Keep real resource admission and safe cleanup. Use the documented operation-specific
  bounds; a large GIS experiment's memory gate does not prohibit editing, reading small
  files or running focused tests. Do not invent global free-memory thresholds, repeatedly
  poll unchanged resource conditions, or duplicate whole datasets for reviews.

No current acceptance, scientific authority or explicit human constraint is weakened
by this policy. A demonstrated wrong result or unsafe operation still blocks the
corresponding delivery. An optional improvement is not a new acceptance criterion.

## Coherent PR scope

Keep PRs focused on a coherent outcome, without numerical size targets or extra justification based on line count. Keep code and documentation readable. Report generated-data changes separately. Retain lane ownership, required checks and serialized squash merges. Split issue scopes only when their acceptance or independent work requires it; keep coherent changes together.

## Ordinary ownership and live-operation reservations

Read fresh main and the relevant issue/PR discussion. Record this chat's worker ID,
fresh branch, bounded scope and planned checks in that existing conversation. The
parent coordinates overlap and handoffs. No parsed ownership receipt, timed lease,
renewal heartbeat, readiness audit or claim workflow is required for code or
source authoring. Preserve other workers' open branches, evidence and checkpoints.

The existing `issue-claims.yml` workflow remains only for explicitly coordinated
engineering live operations and settling historical reservations. Cloudflare
republish, current PostgreSQL recovery and compact production retain their active
live reservation, independently expiring operation window, exact provider/tool/
source pins, operation registry and actual database locks. Read the applicable
operation guide before dispatch; a reservation never authorizes an operation by
itself. Existing native maintenance workflow groups differ; they do not provide
global serialization across every historical writer.

For an authorized live reservation, use native `gh workflow run issue-claims.yml`
with the documented issue, worker, branch, action, claim ID, request ID and live-work
inputs. Observe the exact run using `gh run view` / `gh run watch`, then read back
its canonical bot comment and operation state. Preserve the original IDs when
reconciling an uncertain dispatch; never infer acceptance from a queued run or
blindly redispatch a mutation. Only the holder can renew/release. An open PR or
live operation blocks release/rotation; expiry never permits takeover or proves
cleanup. Recovery still requires explicit approval and preservation of earlier
work. Historical comments and receipts remain immutable records.

## PRs and the merge queue

Each coherent PR targets main. Issue links and GitHub closure keywords are optional,
with no custom syntax or one-issue limit. Close only completed acceptance. The
submitting operator verifies substantive distinct-worker review of the exact head.
Workers sharing one GitHub account still obtain review from a genuinely distinct
worker. Submit that worker's substantive exact-head review as `COMMENT`, not a
self-`APPROVE` attempt. The existing operator-reviewed comment route is sufficient;
no extra account, approval layer or machine review receipt is needed. For example:

```sh
gh api --method POST repos/ChengshuLi/WorldAtlas/pulls/PR-NUMBER/reviews \
  -f commit_id=EXACT_REVIEWED_HEAD -f event=COMMENT \
  -f body='Distinct worker ID; exact head; inspected scope; actual checks and limits; findings.'
```

Read back the returned review's commit and the current PR head. A different head or
unresolved substantive objection requires renewed relevant review, not another
identity or a blind retry. A comment does not create scientific approval or make an
author their own independent reviewer.

Submit, find, observe and recover native merge executions through the single
[merge queue client procedure](MERGE_QUEUE_CLIENT.md). Research, PR checks and
independent review can continue while Actions holds pending runs.

The queue validates the exact reviewed head, current checks and current main,
then creates one owned disposable candidate branch and asks GitHub to merge the
reviewed SHA into that exact base. It verifies ordered parents and complete trees.
The isolated read-only jobs test that combined candidate. Finalization rederives
applicability from the authenticated base/candidate pair, validates actual scientific
reports, and rereads current head/main/checks before a SHA-guarded squash merge using
the current PR title. It never edits an author branch, resolves conflicts, or runs
candidate code with write credentials.

Ordinary preparation/finalization do not fetch an issue, parse its labels/body,
police branch namespaces or replay the generic remote evidence-manifest traversal.
Actual scientific consumers still authenticate complete source inputs, identities,
geometry, rule/results and original-scope conservation. Package/emitted consumers
check their actual output. The author and independent reviewer inspect retained
source evidence and consequential claims, using the existing evidence validators
when applicable. A matching hash or generic manifest walk alone never established
those scientific facts. Specialized physical-water exception authorization retains
its explicit source dossier/issue contract, distinct-worker decision and fresh
byte/review checks. Live operations retain their separate authorization and locks.

A merge does not complete unproven acceptance, publish or authorize an import.
Verify fresh PR API state has `merged: true`, the exact reviewed head and actual
merge commit. See [MERGE_QUEUE_CLIENT.md](MERGE_QUEUE_CLIENT.md) for dispatch,
observation, safe retries and local release. Historical reservation records remain.

The final job deletes only that exact owned ref at its expected SHA, including on
test/merge rejection. Failed cleanup is recorded for operator inspection. Failed preparation notification
also attempts exact-owned cleanup; an unconfirmed ref creation records its possible
resource without deleting a collision. Canceled
jobs may leave an owned ref and require cleanup, never blind deletion or proof of
merge. Candidate tests still check out immutable SHAs with read-only permissions.

Base-dependent evidence still needs refresh: a metric labeled current must match the actual PR-base vintage, and original-file receipts must match actual base bytes. Disjoint main changes with unchanged scoped inputs can reuse review; fresh global measurements or changes to the reviewed inputs cannot. Preserve the earlier evidence, refresh in a new vintage, and obtain exact-head review when needed. The final queue selects checks by every changed and renamed path. Code, workflow, schema and core-data changes run the complete unit suite across three parallel shards, plus one hosted package build. Isolated geography/history campaign evidence and engineering-owned receipts or Markdown/text docs run the final focused ownership/evidence/review/invariant suite, without rebuilding the unchanged application. Both profiles run in isolated read-only jobs without secrets or persistent checkout credentials. They retain exact candidate and actual scientific-consumer checks; a renamed runtime file cannot evade full regression. Prepare/final jobs execute only fresh trusted main code. Tests are bounded to35minutes, trusted jobs to10minutes each; unfinished heads fail preflight rather than holding the slot for worker action.

The full runner keeps packaged-asset checks on the build job and the expensive local model/migration file on a separate job. Measured database-neighbor suites use the otherwise lighter job; the remaining discovered files retain deterministic assignment. Every file still runs exactly once. Named placement is a scheduling choice, not a runtime guarantee; compare actual complete workflow times rather than summed TAP durations.

Package inputs are declared in `.github/package-inputs.json` and physically copied into an isolated build source image by the standard package builders; see [PACKAGE_INPUTS.md](PACKAGE_INPUTS.md). CI uses the same declaration from trusted base. Implementation edits do not invalidate later research through code fingerprints. Research becomes a package input only through an explicit reviewed declaration change. A packaged research PR runs its research evidence checks plus package checks; package applicability alone does not select full application regression.

Ordinary authors run applicable checks and receive substantive exact-head review.
There is no preliminary issue/scope/evidence job; the queue executes actual
candidate checks once. Reuse unchanged authenticated scientific evidence.

Package applicability selectors, scope tests and package workflows retain their
focused final coordination controls. Actual build/archive tools, test runners,
application code and schema remain full. Full discovery includes every test once;
the focused final inventory includes the relevant package-scope controls.

Changes to the test runner require the full profile so the actual complete test inventory and scheduling are verified; they are excluded from the coordination-only allowlist.

All integrations must use this queue. GitHub’s merge endpoint guards the PR head, not the base; the final main-read/PUT interval cannot atomically exclude an out-of-band direct merge. Do not integrate directly during a queued run. If a designated exceptional repair is needed, drain/coordinate the queue first. The normal protocol serializes every writer; it does not claim a server-enforced base CAS. GitHub native merge queues are unavailable for this personally owned private repository under the current platform eligibility rules.

After a confirmed merge, the trusted queue also attempts remote head cleanup, independently of merge acceptance. It confirms the merged PR and exact reviewed head, same repository, non-default/unprotected branch, complete open-PR head/base identities with no other use, and unchanged branch/ref SHA immediately before deletion. An already absent branch is clean; advanced, protected, shared, fork or uncertain heads remain with a durable `head_cleanup` reason. A bounded API/time budget stops oversized or slow cleanup before starting further calls. API/deletion errors are pending cleanup and never invalidate the successful merge. GitHub's automatic-delete checkbox remains enabled but is not the queue's sole cleanup mechanism. The GitHub delete-ref endpoint has no SHA guard; the final read/delete interval cannot atomically exclude an out-of-band push or new PR. Workers must use fresh branches after merging and never push to or reuse merged heads. This cleanup does not remove local branches/worktrees, original evidence, or archived PRs.

After each merge, reconcile acceptance and remaining work on the issue, then use a fresh branch. Split work only for a distinct deliverable or real ownership boundary. Existing closed Issues, source evidence and dates are retained.

One explicitly designated engineering publisher coordinates Cloudflare deployments, geographic releases and owner maintenance. Workers do not publish competing versions independently. The GitHub merge queue does not serialize manual provider operations or a different repository; use the existing deployment/maintenance protocol and complete cross-provider registry. The old owner-private read-only Site is a retained recovery copy, retired from ordinary serving/publishing instructions; explicit recovery operations still require serialization. See `CLOUDFLARE_RECOVERY_HANDOFF.md`. Branch protection is not configured, so workers must honor the queue and checks; direct merge permissions are not revoked by this setup.

Implementation acceptance and production publication are separate. Workers verify ordinary changes in isolated local/preview environments and record what that proves; authorized bounded production read-only access is permitted without a deployment appointment, while writes/imports/migrations use independent test data/database and heavy load tests require coordination; they do not wait for a production deployment to merge. A complete durable publication handoff allows the implementation holder to release its claim once all PRs are merged/closed and no holder-run live operation is active. The publisher does not require that source claim to remain active or have `live_work=true` solely for delegated publication. Do not close an issue whose existing acceptance includes unverified live delivery: record its publication-only remainder on the original issue with `publisher-needed`, prevent duplicate implementation claims, and continue other ready work. Do not silently relax existing acceptance or geographic approval/import gates.

The designated publisher pins latest primary main at run start and discovers merged changes since its verified primary delivery commit, plus original issues labeled `publisher-needed` and unresolved production checks. No duplicate publication request on #714 is required. Original issues retain criteria/blockers/evidence; closed linked issues are still considered for delivery. GitHub deployment metadata indexes one bounded publisher-owned operation and its exact result, separately from per-issue acceptance. Expiry does not prove cleanup; all active/unsettled records block overlap. This remains cooperative serialization. Existing #714 operations settle under their original rules and remain preserved until backlog reconciliation/archival. See [PUBLICATION_HANDOFF.md](PUBLICATION_HANDOFF.md) for discovery, records, safe release and SQL exceptions. Existing chats must refresh saved instructions; repository edits do not modify them automatically. Auditor #726 owns separate post-merge quality review/follow-up creation.

## Current research policy

The user's top-down policy requires **global continent/subcontinent/region boundary approval, then complete published regional branches before their location-attribute imports**. Other regional interiors may remain unfinished. See [TOP_DOWN_GEOGRAPHY_WORKFLOW.md](TOP_DOWN_GEOGRAPHY_WORKFLOW.md). `data/research-geography-gate.json` records the macro approval and regional certificates; the macro partition is approved and published, but no complete regional branches are approved, so content imports remain closed. Every fixed regional scope is in `data/macro-foundation/regional-handoffs.json.gz`; use bounded children for parallel interior audits.

Only engineering may approve and publish the partition/branches with retained sourced evidence, exact subject IDs and matching release/hierarchy/footprint pins. The worldwide umbrella #7 stays open until all branches finish; it no longer directly blocks a certified branch. History workers do not design geography. Geography researchers may propose sourced boundary/hierarchy changes in their owned evidence; only engineering integrates and certifies them. Source-only collection/staging and dry runs may continue, but source populations/primary culture/religion still need the intended territory and supported interval before imports. The private API and retained facts remain intact; the cooperative claim/CLI gate is not new server authorization. Region completion creates a research handover/ready queue, not an automatic new chat or private credential grant.

## Evidence and independent review

Follow `docs/PREMERGE_EVIDENCE_REVIEW.md`. Ordinary engineering uses the actual Git diff, applicable tests and a distinct worker's substantive exact-head review comment; no synthetic evidence manifest, duplicate inventory, body hashes or frozen review packet is required. Scientific claims retain their actual subjects/pins, immutable input/result evidence and honest source/publication limits under `.github/evidence-policy.json`; explicitly declared manifests remain checked. Never self-review under a second worker ID. The submitting operator verifies current review before integration; green CI alone does not approve geography or authorize imports.

## Applicable regression and exact-tree reuse

The integration profile defaults to `full`. Documentation text and the exact coordination paths in
`scripts/integration-profile.mjs` and the current worker's owned receipts use the
focused `evidence` profile. It includes reservation, ownership, regional import
barriers, evidence/review validation, workflow checkout and integration controls.
Source-only owned research retains its focused controls. Every changed path and
rename origin participates; unknown non-text documentation/scripts, application code, storage,
atlas data, geometry, schema, imports, builds and deployment require full regression.
The queue uses GitHub's complete PR file inventory for authored scope and evidence review. Execution routing instead compares authenticated accepted-base and combined-candidate leaf identities, kinds and modes at both preparation and final admission. Already accepted changes in a stale PR inventory do not select unrelated execution; actual additions, removals and both sides of moves still participate. Ordinary focused-test checks use the executed candidate tree. Focused selection uses actual source-packet/control paths and package applicability, independent of branch names and issue labels. Unknown runtime files or move origins retain full regression;
Unknown applicability runs complete final regression. Full shards cover every test file
exactly once, build actual packaged assets and reject skipped tests.

The automatic author geography/regression/package phase and its proof-transfer,
predecessor-program catalogue and current-control reuse chain are removed. Current
scope and required evidence must succeed before admission. Every existing current
head check must finish successfully; the queue creates no exemption for failed
checks. Author metadata no longer classifies unused build/test work. Independent
review still selects concrete local controls for the changed invariants.

The final queue requires successful actual geography and integration jobs. A prior
author run, supplied legacy proof pin or skipped final job cannot replace them.
Final authority, scientific evidence, reviewed bytes, ordered candidate parents,
current main/head, checks and geographic adjudication are revalidated before the
SHA-guarded merge. There is no new scheduler, cache or proof packet.

Keep a qualified scientific delta and its manifest unchanged while its actual
subjects, source/native inputs, results, metrics, vintages and limits are unchanged.
Current delivery selector/package/sidecar wrappers and duplicate composition metrics
need no additional scientific bookkeeping solely to restate final queue custody.
Preserve historical declarations honestly; changed science requires new evidence
and relevant review. Actual delivery files/receipts and final-head review remain.

Historical author geography/package artifact readers remain available only where
original provenance and accepted-checkpoint acquisition consume them. Original
records preserve their actual head, workflow, candidate, attempt and checksum;
they are never relabeled as current execution. New ordinary package originals
come from the final queue.

Full-profile changes to checker/producer code or its dependencies run the exact
combined candidate checker, with
checker-code identity separate from baseline and candidate data identities. The
bounded applicability collector compares the actual selected world/grid/release,
source-bank, native asset and additive output bindings under that one executing
checkout. Identical immutable data and direct present/absent aliases make the
differential check not applicable, including for software changes. This is only a
data-applicability decision: it does not certify new code, inherit historical
legality or establish fresh source authority. Applicable software regressions and
independent review validate changed code behavior. Changed data, missing or
mismatched pins and unsupported selector/asset layouts retain the genuine full
native-conservation route in the actual final queue candidate.
Historical authority, producer-schema, rebind-execution and checkpoint-legality
graphs are retained original evidence, not replayed to compare unchanged outputs.
The collector reads only direct routing metadata and authenticates selected
outputs by their immutable Git descriptors; scientific leaf bodies stay opaque.
It retains at most 64 MiB of raw routing bodies with eviction. The 32 MiB member,
4096-descriptor and per-operation bounds remain unchanged. The geography job
uses the hosting provider's default execution limit.
Owned process-group cleanup remains. Cumulative I/O, unique planned bytes and
live-cache peaks are reported separately; this is not a process-RSS guarantee.
One exact baseline-to-candidate tree delta lets unchanged candidate paths reuse
already authenticated baseline descriptors; changed paths retain separate reads.
There is no finite software hash exception, baseline self-comparison substitute,
checkpoint reuse or new checkpoint authority for this route. Selected-data and
source-only work, data-only full changes and unrelated application changes retain
the baseline checker and their existing applicability/adjudication. The existing
changed-file classifier conservatively selects scripts, scientific runtime modules,
engineering code/policy files and dependency metadata, including rename origins.
The final trusted merge consumer independently derives the route from the profile
and selected-data classification; a candidate-code report cannot serve as baseline
or checkpoint evidence. Full regression/build and exact-head independent review
remain required.

Candidate checker execution has no GitHub token or persistent checkout credentials.
Public immutable Git acquisition uses the existing read-only transport anonymously;
access failure blocks rather than falling back to a token. The exact executing
checkout and its code inventory are checked and recorded. Existing child scientific
receipts are retained verbatim, including their legacy `candidate_code_executed:
false` marker. That marker does not establish absence of candidate checker code in
a software run: the enclosing report explicitly records `candidate_code_executed:
true`, the actual code commit and inventory, and distinct data commits. Historical
receipt bytes and historical scientific admission are unchanged. Stable workflow
step names remain for original-job receipt compatibility; the report's explicit
execution identity determines what ran. Software-run raw findings block; only
the baseline route may request the existing authenticated source adjudication.
A mixed checker upgrade and raw-data correction needing adjudication must deliver
the checker first, then the data change through that existing trusted route.

The author authority job resolves its event candidate's authenticated accepted
parent before checking out trusted code. Older PR opening metadata cannot keep an
obsolete scope checker running. Ownership/evidence retain their actual original
authored/event vintages, recorded separately from the executing trusted parent.
The queue independently pins actual current main plus reviewed head. Disjoint
main movement alone does not require rewriting an unchanged reviewed branch.

Historical PR geography reports compared the event merge against its exact
accepted parent. Their original readers still verify ordered parents, complete
candidate tree and distinct reviewed/workflow/candidate identities. Legacy raw-head
receipts keep their original meaning; no historical report is relabeled current.

This is cooperative GitHub Actions evidence and native workflow concurrency, not
independent authenticated worker identity or GitHub's separate branch-protection
merge-queue product. The final base read and SHA-guarded head merge remain separate
API operations: an out-of-band writer can advance main between them. Native queue
serialization is not an atomic base guard; every main writer must honor the same
serialized workflow. A green run does not certify geographic facts, authorize
imports or publish the Site.

The focused `evidence` controls use Node and repository files without installed
npm packages. Final full validation requires pinned Node/Python dependencies,
applicable browser setup, the actual hosted build and complete zero-skips tests.
Every final focused control must execute successfully. A skipped install/test
step does not establish application coverage.

## Native queued integration

Issue #1174 identified an actual starvation path: a long engineering request tested
main `72029…` while unrelated source merges advanced it to `1f971…` and `9a824…`.
The final base guard correctly rejected that candidate. Independent testing plus
final-only serialization allowed this to repeat indefinitely. The observed HTTP
403 failures have no established cause and are separate from that scheduling bug.
The retired scheduler addressed this with durable registrations. Native Actions
now owns queueing, while the existing top-level concurrency group still holds the
complete candidate/test/final lifecycle to prevent cooperating merges from
invalidating one another's tested base.

Use [MERGE_QUEUE_CLIENT.md](MERGE_QUEUE_CLIENT.md) for submission, run discovery,
observation and recovery. Provider ordering, queue limits and runner availability
remain external controls, not an application-level availability guarantee.

### Migrate existing requests safely

The coordinating integrator enumerates old scheduler and worker executions and
lets live work settle before new direct submissions. Include queued, requested,
waiting, pending and in-progress runs: a workflow already running keeps its old
definition after this change merges. Preserve old request IDs, exact heads,
workflow links and receipts on the original issues. Do not cancel #1810's
in-flight work as part of the transition. Research and PR checks remain enabled.

Any reversible admission hold is owned by the coordinating integrator, with its
prior state recorded and restored. Disabling a workflow is not cancellation and
does not settle existing runs; enumerate racing admissions as well. Reconcile
ambiguous old submissions and terminal registrations before deciding whether a
remaining unchanged-head PR needs a new native dispatch. Do not bulk-replay old
registrations or dispatch both paths. Workers do not independently toggle shared
workflow availability. No direct merge, provider operation or publication is part
of this procedure.

### Immutable blob reuse during repeated authority checks

The root #1150/head `405f75ce2280dc44172ba596b9ee08513abe437c` workload
contains 400 descriptors and 92 original changed-file loads. Its remote reader
makes 493 blob requests per evidence pass, and an isolated fallback can perform
three full authority/evidence passes (1,479 blob requests). Read-only Git object
inventory finds 474 distinct OIDs totaling 235,417,555 raw bytes, with a largest
blob of 14,322,993 bytes. These are request-workload measurements, not geographic
approval. GitHub documents a default GITHUB_TOKEN limit of
[1,000 requests per hour per repository](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api).
That limit is compatible with the observed fanout and denials; it does not prove
the cause of the earlier HTTP403 results without their actual message/headers.

Each prepare/final execution now memoizes only successful immutable Git blob
GETs keyed by repository and requested OID. Before admission the helper requires
base64 encoding, complete canonical encoding, exact response/full-byte size, and
the Git blob SHA1 computed from its header and full content to match the requested
OID. Unsupported, incomplete, mismatched and failed responses never enter the
cache. The cache holds at most 512 entries and 272 MiB of raw payload accounting;
base64 storage is at most four-thirds of that bound plus response metadata.
Overflow stays uncached without evicting the useful first scan. Existing evidence
file/total/descriptor budgets remain mandatory and unchanged. This size retains
the known 474-blob workload across repeated checks without cache thrashing.

Every commit/tree/path/vintage binding and every PR, issue, reservation, review,
check, status and ancestry comparison is freshly read. Changed OIDs fetch new
bytes; cached blob bytes do not cache a validation result or extend authority.
Separate jobs/requests do not share this in-memory cache. Controls model the actual
workload count/aggregate/largest payload size and prove 1,479 requested reads use
474 verified fetches while changed OIDs/tree modes/head/claim/check/review still
reject. The cache neither skips a byte check nor accepts an untested candidate.

Actual API denials remain failures. Merge receipts retain only HTTP status,
sanitized API message and allowlisted numeric rate remaining/reset/retry-after
and GitHub request ID when available; original denial and notification denial are
separate. Tokens, authentication headers, cookies and complete bodies/header maps
are never retained. Inspect this evidence before attributing any future denial
or choosing a retry; observation expiry alone still cannot restart live work.


For bootstrap observability, the existing PR authority profile job has a static
failure-only diagnostic. It makes one read-only current-repository PR GET with
the same job token and a 20-second request timeout, emits only the sanitized
message/status and allowlisted rate/request fields, and leaves the original job
failure intact. It explicitly redacts the known token as well as token prefixes
and Bearer values. This later same-token probe describes its own response, not an
inferred original response. The trusted-base selector still owns the actual
profile/coverage decision; a successful probe cannot substitute for validation.

### Bounded PR startup metadata observations

PR evidence/profile admission may observe the same exact run/attempt job inventory
up to three times, with at most 250 ms and 750 ms between successful responses.
The existing 41-second startup allowance includes immutable workflow lookup,
every read and wait; it is never restarted or extended. A full 20-second HTTP
attempt must fit before either sleep or another read. HTTP errors, quota refusal,
permission failures and uncertain transport are not retried by this path.

Missing/null metadata and known pending states may settle to a fully valid row.
The first unique job ID and valid nonempty start are pinned. Wrong run/attempt,
duplicate jobs, ID/start drift, terminal state or malformed nonempty start refuse.
No evidence transport or inspection starts before all original identity and timing
checks pass. Allowlisted binding fields and read/wait counts explain both failed
and recovered observations; they do not assert a provider cause or saved time.
A simulated recovery proves the control path, not that a particular hosted
failure was eventual consistency.

### Actual HTTP quota and job deadlines

Final merge runs its actual evidence, review, source, candidate-parent/tree
and mutable-authority validation once. There is no separate evidence preinventory,
request estimator, speculative artifact/proof walk, capacity poll or replanning
pass. The full scientific byte validator retains its ancestry, descriptor and
byte limits. The final current issue/check/source/base guards and SHA-guarded
merge remain required.

The shared HTTP client uses actual response status and numeric retry/reset
information for bounded GET-only retries after recognized quota rejections.
Successful responses do not require capacity headers. There is no predictive
request floor, cleanup allocation, startup barrier or capacity probe. Ordinary
permission failure, ambiguous transport outcomes and writes are never
automatically retried merely because quota might recover.

Each HTTP attempt has a 20-second abort signal. A caller-supplied deadline also
must fit the complete next attempt and any retry wait; Actions owns the worker
job timeout. No separate startup job-clock or finalization-reserve protocol is
used. Exact-owned candidate cleanup and result notification retain their
restricted, single-attempt dispatcher. Actual provider rejection can leave
cleanup or notification pending for reconciliation; local forecasts cannot
reserve capacity against other jobs.

Inspect the same Actions execution rather than canceling or duplicating a long
job. Reconcile terminal failure and actual PR state before retrying; retained
successful preparation/tests of the exact candidate can support a failed-job
rerun, but rerunning only the final job cannot bypass missing or failed checks. Local
mocked HTTP controls establish rejection and cleanup behavior, not hosted quota
recovery or a system-wide capacity guarantee.

## Issue lifecycle accuracy

Read [ISSUE_LIFECYCLE.md](ISSUE_LIFECYCLE.md). Authors reconcile original acceptance and next actions before moving on; reviewers check closure/continuation independently of merging. Dependency owners maintain direct dependents. Coordinate encountered overlap and remaining work on the original issue; preserve scientific/publication gates. No readiness script or routine queue-triage pass is required. Existing chats refresh before their next job; Main handles exceptional decisions.

Read docs/AUDIT_FAILURE_PREVENTION.md on current main before the next job or review. Identify the consequential acceptance claims and independently test applicable consumed-input/code, identity/join, source/method, safe-reproduction, nonvacuous-control and operating-limit invariants. Use shared evidence helpers or an explicitly reviewed equivalent; reviewers derive expectations from original acceptance and independent records before relying on author tests. Exercise real entry points and adjacent paths for corrective PRs; record unexecuted proof as a limit. Keep exact-head review, original evidence, scientific/publication gates and focused research CI. Adoption requires actual subsequent handoffs, not just this prompt edit.

## Prepare for the first review

Follow [AUTHOR_PREFLIGHT.md](AUTHOR_PREFLIGHT.md) before the next job and before
requesting its first review. Select the checks implicated by the original acceptance
and changed behavior from the start; preserve source-only focused CI. Resolve quick
ownership/evidence errors before review, while substantive
independent review proceeds independently of the later final queue computation. The guide supplies practical helper and
command details, meaningful adverse cases and existing-chat refresh text; author
preflight does not replace independently derived reviewer expectations.

### Shared Actions quota: reduce work and recover from actual evidence

The Actions installation token and a worker's local GitHub credential can have
separate quotas. A healthy local `/rate_limit` is not evidence that an Actions job
has recovered. The premerge evidence entry point uses the same bounded,
exact-tree-bound Git blob transport as the merge queue, rather than one REST
request per evidence file. It still verifies complete bytes and every declared
binding; mutable issue, claim, PR, tree, ancestry and review authority stay fresh.
The final queue is the single automatic PR validation path. It rechecks current
authority and exact candidate evidence; main package push observations remain
separate from merge workflows, claim mutations and publication.

Premerge evidence, linked-issue checks, profile selection, deployment classification,
claims and the existing
merge workflows emit actual categorized HTTP attempt counts. Their existing
responses supply allowlisted numeric repository-core observations when available;
no extra quota poll is added. These observations describe that credential and
window, are not reserved capacity, and cannot attribute other concurrent jobs'
consumption. Missing headers remain unknown. A lower request count in one path
cannot guarantee that the whole installation never exhausts its finite quota.

On a proven quota refusal, retain the original status, numeric reset/retry-after,
request ID and retry time. Do not immediately dispatch another workflow for the
same failure or rerun a long regression simply to retry a refused API operation.
Wait until the recorded condition can change, then inspect the current canonical
claim/request/head and retry only the required bounded operation. Permission
errors and unknown transport outcomes are different; do not guess a reset or
blindly replay writes. GitHub Actions job timeouts and bounded actual HTTP
attempts remain mandatory; no check or authority is waived by waiting. There is no
separate current-job metadata admission or authenticated job-clock protocol.

Claim jobs retain `claim-result.json` even when a notification cannot be posted.
A known quota refusal defers that doomed notification. `mutation_attempted` and
`reconcile_required` distinguish pre-write refusal from a possible partial/lost
write. A worker must inspect the canonical reservation and exact request before
resuming or redispatching; an artifact alone never confers ownership. Preserve
active work and checkpoints while waiting. Refresh this guidance before the next
job; no new chat monitor or provider credential is introduced.

A proven quota refusal during deployment classification retains its blocked
decision and retry evidence; the required package job fails before checkout or
dependency/build work. It never reports package success or a source-only skip.
Unknown non-quota inventories retain the conservative full-build fallback.
Concurrent read batches finish their existing bounded requests before receipts
are finalized, so a fast rejection cannot hide other already-started attempts.


### One final delivery validation

Ordinary delivery performs actual conservation, build/assembly and applicable
regression on the single final composed candidate. Authenticated retained-output
assembly still authenticates its actual original successful producer and all
unchanged output bytes; it does not transfer an author's regression claim.

For unchanged-method selected deliveries, the setup profile remains `full` while
`test_selection=selected-data` declares the narrower inventory. This option is
ineligible until the generic selected-delivery smoke exists unchanged on trusted
main. Only the additive selection changes; all existing method/base authority and
registry entries remain intact. New files must be ordinary inert data/evidence in
a coordinated delivery directory. The package definition may only append exact
new data file entries reachable through the fixed selected-reader roles, preserving
all existing entries, order and other policy fields. Supporting evidence cannot
create package/import authority. New retained Python/JavaScript helper copies,
JSONL stdout, original XML responses (including retained `.json` names), LFS pointer text and compressed GeoJSON/latitude evidence may
accompany DATA only after the fixed selected/base-reader walk excludes every such
file from current consumed roles and package inputs/verification paths. Authenticate
whole ordinary Git bodies without executing helpers, resolving XML entities or
following LFS pointers; decode complete gzip members and check structured syntax.
Loader/configuration files, changed current code, executable modes and unavailable
role proof retain full regression. Retained science is still independently checked;
this route grants no new source authority. Unknown boundaries retain all three
full regression shards.

Existing coordination packet `evidence-quality.json` files may be updated only as
inert metadata on the selected-data route. Both tree entries must be ordinary and
the complete fixed selected/base-role walk must exclude each receipt from current
consumed roles and actual package inputs/verification paths. No issue declaration
or filename can exempt a consumed input. Other existing packet edits, missing role
proof and changed current code retain complete regression. Source interpretation,
input/result validity and substantive exact-head review remain independently required.

Each such delivery adds exactly one `selected-delivery-expectations.json` under its
owned delivery directory. Use the existing smoke's version 1 schema, authored from
reviewed original authority/ledger inputs. Eligibility binds its ledger hash,
complete active selected component roster (including zero-cell rows), targets,
dispositions, geometries and cumulative native cells. Existing awaiting-evidence
and rejected ledger rows remain unchanged; they are retained source records, not
rendered selections. Reclassifying those old rows takes the full route. Do not derive expectations from emitted
assets. Missing or ambiguous expectations retain full regression. Batch labels
remain reviewed source-side statements, not a new independent source approval.

The automatic author workflow is removed. The serialized queue checks current
ownership, complete changed paths and evidence directly, then composes
current main with the reviewed head, then runs one fresh geography conservation pass
and one actual package assembly or full Cloudflare build on that candidate. The
generic emitted-asset smoke checks the complete selected roster, every additive
patch cell with the actual picker/sampler and retained stable-owner controls.
New full builds capture the complete output inventory immediately after the
genuine build. Authenticated assembly retains that original inventory and
verifies unchanged output bytes.
Ordinary selected data does not rerun unchanged-base unit/browser tests or restore
canonical/model-reader/SQLite context solely for those tests. Software, content,
unknown or base-changing work keeps full regression.

There are no automatic author jobs or prequeue check-name prerequisites. Existing
failed/pending external checks and commit statuses still block admission. There is
no automatic author computation or regression proof to transfer. The final gate
requires successful current queue integration and applicable geography, the exact candidate
parents/tree, current authority and independent review. Missing, skipped, failed
or stale required final checks prevent merge. Only existing engineering coordination
scripts and validated focused-test edits outside scientific/current-method and
package input/verification roles omit the entire unrelated geography job. Final
acceptance recomputes that scope and records the actual skipped job as not applicable;
docs, workflow definitions, packets and ambiguous inputs retain geography.
Software, dependency and unknown changes
keep their complete CI route. The runner reports setup profile and actual test
selection separately and rejects skipped tests. Hosted adoption and elapsed
savings must be recorded when observed, not inferred from local controls or added
parallel job durations.

Ordinary software, executable-source additions, changed inputs, mixed and unknown
scope run one complete final queue pass. Stable app-only author proofs previously
could transfer before admission; the simpler default now places that single pass
in the serialized lane. Measure actual lane occupancy and completed delivery time,
including removed duplicate/reworked prequeue work, rather than adding job durations.

The Cloudflare step does not measure the historical Site archive reserve. An
explicit `npm run build:hosted` recovery build retains its actual file/archive
budget check. Normal main pushes do not schedule a separate legacy Site build.

### Run the reviewed consumers

The existing merge dispatch accepts an optional `reviewed_tests` JSON object with
`base`, `head` and `files`. The first two fields are exact 40-character accepted-main
and reviewed-head commits. `files` is the nonempty list of actual `test/*.test.mjs`
consumers identified during review. There is no author-maintained transitive input
list: preparation includes the complete `test/fixtures/` boundary, the existing
executing-authority input contract, and genuine package declarations when packaged
consumers apply. Ordinary code namespaces remain available.

Unit and contract tests own self-contained fixtures. Captured scientific bodies
retain their original pins and adverse authority checks. Policy tests use explicit authenticated metadata/body fixtures: a descriptor does
not claim its unread body is present. Consumed bodies retain exact Git identities,
and the reader has no repository or network fallback. Real Git transport is
covered separately by small synthetic repositories and absent/corrupt-object controls. Real selected-data/package checks continue to use their
existing authoritative readers and declarations rather than these contract fixtures.
Do not repair a missing contract operand by adding a live-history path to dispatch.

For rollout through older accepted preparation, `inputs` may contain the exact
mechanically derived vector returned by `reviewedTestPlan`; the new planner also
accepts an omitted or empty field. Arbitrary manual vectors are rejected. This is
an execution argument, not source authority or proof that a test roster is complete.

Preparation and final admission validate the same immutable pair and ordinary
candidate paths. Stale base/head, missing executing-policy inputs, missing fixture roots, escaping paths and
symlinks fail clearly. Re-review the actual new pair before updating a stale
request. With no argument, existing automatic routing and its conservative
complete-regression fallback remain available.

A reviewed list uses one isolated regression worker and acquires only its code
and fixture inputs. It does not change geography applicability, trusted checker
selection, native/source validation or the selected-data emitted smoke. Selected
data keeps its existing mandatory route rather than accepting this override.
Any actual change to a declared package input, including a move away, adds both
existing packaged-asset consumers and retains the genuine package build and its
inputs. Explicitly selecting either packaged consumer also requires that build.
Otherwise the snapshot/build/output-retention stages are omitted. Browser setup
continues to follow the actual selected consumers; migration preparation occurs
only for its consuming test. Existing historical integration reproducers retain their
authoritative original-input acquisition; normal routing remains available for those
unconverted legacy consumers. The reviewed contract boundary cannot be expanded by
a hand-written dispatch list.

Record the exact selected files, complete fixture closure, stage count and actual
elapsed results in the ordinary review/handoff. Distinguish a cold fixture probe,
local tests and hosted execution; do not count skipped work as scientific or
publication acceptance. No additional issue, certificate or approval step is
introduced.

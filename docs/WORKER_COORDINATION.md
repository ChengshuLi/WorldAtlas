# Many engineering, geography and history workers

M geography, N engineering and P history-research chats may work in isolated checkouts. GitHub Issues remains the work record. Before implementation, comment with the worker ID, branch, bounded scope and planned checks. The parent coordinates overlapping work. Threads sharing a GitHub account still use distinct worker IDs; a comment is coordination, not security isolation.

Read [LOCAL_WORKSPACES.md](LOCAL_WORKSPACES.md). Allocate isolated checkouts through `scripts/local-workspace.mjs`; keep bounded work/review slots, include exact required sparse inputs, check storage before generation/installations, and release finished slots after preserving unique work. Do not retain a full checkout per task or review revision. Existing chats must refresh their saved instructions.

## Chat identity

Worker identity belongs to the chat, not the issue, branch, goal, checkout or GitHub account. In Codex, use the exact current CODEX_THREAD_ID as the author worker ID and keep it across successive jobs. Never copy an ID from another chat, a reservation, a checkout registry, a handoff or inherited/forked context. A fork/new chat has its own identity. Before starting work or allocating, compare the chosen ID with this chat’s actual ID; if another chat owns the work/slot, leave it untouched and do not treat it as your work or blocker. New author work-allocation commands reject mismatches when CODEX_THREAD_ID is available. Outside Codex, establish one unique persistent ID for that chat; the tools cannot verify chat identity when the environment does not supply it. Do not unset or override CODEX_THREAD_ID to bypass the check.

Active legacy work keeps its recorded worker ID only for finishing, renewing and releasing that exact claim/checkout. Do not rename an active claim, take over another chat’s slot or start new work under the legacy ID. After verified merge/handoff and safe release, use this chat’s ID for the next job and allocation. Independent reviewer agents keep their own stable distinct reviewer IDs (actual agent identity when available); an inherited parent CODEX_THREAD_ID does not identify a sub-agent. Never invent a second ID for self-review. Review allocation is exempt from the author-ID check because review sub-agents may inherit their parent’s environment; review identity remains cooperative and must be checked by the reviewer.

## Small, reviewed work items

Each worker holds at most one active work item; do not mass-reserve the queue. Actionable issues have exactly one type label, an explicit bounded scope and a positive PR planning estimate (`max_prs`, retained for v1 compatibility). Labels summarize human coordination; they do not start an automated readiness protocol. Larger objectives are `kind:umbrella`, cannot be claimed and are decomposed by independently deliverable scope or ownership. The estimate does not block readiness, claims, branch rotation or merging; exceeding it does not require another issue or a contract edit. Review why work is growing and finish the existing promise instead of mechanically creating a successor. Resolve real dependencies before dependent work; independent work can proceed. Completing a child does not close its parent.

Within a human-assigned delivery goal, choose the next eligible work that most directly finishes that outcome: integrate a supported batch or fix its demonstrated blocker before unrelated housekeeping or speculative hardening. A newly found incident threatening data, service availability or correctness of that delivery takes priority according to its demonstrated impact. For general unassigned queue work, choose eligible urgent items, then follow-ups, then other ready work. A label alone does not establish impact. Finish or safely hand over the current work; preserve lane, declared scope and scientific/publication rules.

The issue-creation thread reviews scope, dependencies and overlap before marking ready. Include one machine-readable block in the issue body (GitHub is its sole authority):

```text
<!-- worldatlas-work:v1
{"max_prs":2,"depends_on":[],"scope":"Concrete acceptance scope","mode":"engineering"}
-->
```

Modes are `engineering`, `geography`, `source-only` and `content`. `type:geography` uses `geography/<job-id>` branches and must declare 1–8 disjoint safe `owned_paths` prefixes, each exactly `data/regional-review/<packet-id>/` or `research/geography/<campaign-id>/`. Existing review packets retain their declared directories. Its work is source evidence, proposals and local reproductions only. Engineering preserves this evidence and implements executable migrations/integration/publication. Models are selected by the user; geography research can run on Luna. See [GEOGRAPHY_HANDOFF.md](GEOGRAPHY_HANDOFF.md). Source-only research defines disjoint subjects/source collections/time/attributes and stages evidence without imports. Content additionally needs `geographic_release`, `scope_manifest` and `territory_match_review`, plus `region_ids` and an explicit permitted subject scope in its manifest. Actual content imports require completed global macro approval and a completed published full-branch regional certificate with matching release pins. No branches are approved yet. See [GEOGRAPHY_RESEARCH_READINESS.md](GEOGRAPHY_RESEARCH_READINESS.md).

A geography work item declares ownership in the same machine block, for example:

```text
<!-- worldatlas-work:v1
{"max_prs":2,"depends_on":[33,36],"scope":"Pinned regional source/semantic review packet; evidence and bounded proposals only","mode":"geography","owned_paths":["data/regional-review/regional-review-packet-a/"]}
-->
```

Inspect other ready issues' declared prefixes before accepting ownership. The issue retains the exact prefix array; scope changes require coordination with affected workers. No geography live-operation reservations are allowed. Engineering reads but preserves both geography namespaces; integration outputs go elsewhere. Trusted CI and the serialized merge queue verify actual GitHub-owned paths, including rename sources; evidence must use ordinary files rather than symlinks/submodules.

A ready label is a reviewed decision, not an automatic conclusion from complete database chains. Two separate issues can still overlap; triage must record subsystem/resource or geography/source/time/attribute scope and dependencies. A worker discovering overlap stops the conflicting part and coordinates on the issues. Ordinary author coordination is not security isolation or a production-capacity guarantee.

Geography proposals → bounded engineering corrections/integration → complete validated published regional branch → permitted historical imports. Independent UI/performance/infrastructure engineering and source-only historical collection may run in parallel throughout. Inter-region inconsistencies require a coordinated issue covering all affected neighbors; no unilateral boundary or certificate edits. After a published boundary change, engineering revalidates affected release pins, complete-branch certificates and content scopes while retaining earlier records/evidence.

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

## PR review size

Keep PRs focused on one issue or a coherent part. Aim for fewer than 1,000 changed non-test lines as a soft review target, not a hard cutoff. Larger focused PRs are allowed when splitting would make implementation, migration or validation harder to review safely; explain the reason in the PR description. Report generated-data changes separately. Do not compress code or documentation merely to meet a line budget. The soft target does not change lane ownership, required checks or serialized squash merges. Split oversized issue scopes into bounded children when needed, rather than fragmenting one coherent change just to meet a line count.

## Ordinary ownership and live-operation reservations

Read fresh main, the issue and its active PRs. Post an ordinary issue comment naming
this chat's worker ID, fresh lane branch, bounded scope and planned checks. The
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

Each focused PR targets main and has exactly one `Refs #N` for partial work or `Closes #N` for full acceptance. CI checks actual issue linkage, lane, declared paths and the complete Git diff/head/base. All working lanes submit merges through:

```sh
gh workflow run worker-merge.yml --repo ChengshuLi/WorldAtlas --ref main \
  -f pr_number=PR-NUMBER -f expected_head=VERIFIED-HEAD-SHA \
  -f request_id=UNIQUE-REQUEST-ID
```

Use a fresh 16–100 character request ID containing only ASCII letters, digits and
hyphens. Record it before dispatch, identify the exact matching Actions run with
`gh run list`, then inspect or watch that numeric run ID. The native Actions queue
holds the entire preparation, isolated candidate tests and final merge lifecycle
in the top-level `worldatlas-main-integrate` concurrency group. The workflow uses
`queue: max` and does not cancel an in-progress merge when another arrives.
Research, PR checks and independent review remain parallel.

The merge uses the PR title as its squash commit title. It tests GitHub's exact
current-main plus reviewed-head merge tree without updating the worker branch,
and rechecks issue scope, evidence/review, check-runs and commit statuses. Reviewed
changed-file blobs and modes must remain identical in the combined tree, including
removed/renamed paths. Conflicts or changed reviewed bytes require author
intervention and fresh substantive review; no automatic conflict resolution is
allowed. Workflow completion or a bot result comment alone is not merge proof.
Fresh PR API state must show `merged: true`, the exact reviewed `.head.sha` and
its actual nonempty `.merge_commit_sha`. Retained live reservations still return bot-authored
**Reservation result** comments on their issues; ordinary authoring needs no lease.
See [MERGE_QUEUE_CLIENT.md](MERGE_QUEUE_CLIENT.md) for direct dispatch, ordinary
GitHub CLI observation, uncertain submissions, safe retries and explicit local
workspace release. There is no custom merge-registration or observation client.

After eligibility checks, trusted preparation creates an owned disposable
`worldatlas-integration/pr-N-REQUEST-RUN` branch at the exact main SHA and asks
GitHub to merge the exact reviewed SHA there. It verifies the returned commit
identity, ordered parents and tree, then revalidates scope, checks, review, issue
contract, head and both main/PR evidence bases before exposing the candidate.
Head, scope or authority changes fail; base advances require renewed preflight
and evidence vintage validation. It then compares complete authored/candidate
trees for reviewed bytes before tests. This never edits main or worker branches,
resolves conflicts automatically or executes candidate code with write credentials.
Independent PR checks remain parallel; each admitted merge run holds the native
concurrency slot through its candidate tests and final merge.
The final job deletes only that exact owned ref at its expected SHA, including on
test/merge rejection. Failed cleanup is recorded for operator inspection. Failed preparation notification
also attempts exact-owned cleanup; an unconfirmed ref creation records its possible
resource without deleting a collision. Canceled
jobs may leave an owned ref and require cleanup, never blind deletion or proof of
merge. Candidate tests still check out immutable SHAs with read-only permissions.

Base-dependent evidence still needs refresh: a metric labeled current must match the actual PR-base vintage, and original-file receipts must match actual base bytes. Disjoint main changes with unchanged scoped inputs can reuse review; fresh global measurements or changes to the reviewed inputs cannot. Preserve the earlier evidence, refresh in a new vintage, and obtain exact-head review when needed. The final queue selects checks by every changed and renamed path. Code, workflow, schema and core-data changes run the complete unit suite across three parallel shards, plus one hosted package build. Isolated geography/history campaign evidence and engineering-owned receipts or Markdown/text docs run the final focused ownership/evidence/review/invariant suite, without rebuilding the unchanged application. Both profiles run in isolated read-only jobs without secrets or persistent checkout credentials. They retain the same exact candidate, reviewed-byte, scope and evidence gates; a renamed runtime file cannot evade full regression. Prepare/final jobs execute only fresh trusted main code. Tests are bounded to35minutes, trusted jobs to10minutes each; unfinished heads fail preflight rather than holding the slot for worker action.

The full runner keeps packaged-asset checks on the build job and the expensive local model/migration file on a separate job. Measured database-neighbor suites use the otherwise lighter job; the remaining discovered files retain deterministic assignment. Every file still runs exactly once. Named placement is a scheduling choice, not a runtime guarantee; compare actual complete workflow times rather than summed TAP durations.

Package inputs are declared in `.github/package-inputs.json` and physically copied into an isolated build source image by the standard package builders; see [PACKAGE_INPUTS.md](PACKAGE_INPUTS.md). CI uses the same declaration from trusted base. Implementation edits do not invalidate later research through code fingerprints. Research becomes a package input only through an explicit reviewed declaration change. A packaged research PR runs its research evidence checks plus package checks; package applicability alone does not select full application regression.

All ordinary author heads run trusted current head/issue/evidence/scope checks,
applicable bounded author/reviewer controls and substantive independent exact-head
review. They do not automatically run geography, application regression or a
package build. The serialized queue owns one actual current-main-plus-reviewed-head
pass, with full software/unknown validation and the existing source-only focused
route. A source packet becomes a package input only through its explicit reviewed
declaration. Main-push package applicability and the distinct Sites reserve
measurement remain separate from this premerge pipeline.

Package applicability selectors, scope tests and package workflows retain their
focused final coordination controls. Actual build/archive tools, test runners,
application code and schema remain full. Full discovery includes every test once;
the focused final inventory includes the relevant package-scope controls.

Changes to the test runner require the full profile so the actual complete test inventory and scheduling are verified; they are excluded from the coordination-only allowlist.

All integrations must use this queue. GitHub’s merge endpoint guards the PR head, not the base; the final main-read/PUT interval cannot atomically exclude an out-of-band direct merge. Do not integrate directly during a queued run. If a designated exceptional repair is needed, drain/coordinate the queue first. The normal protocol serializes every writer; it does not claim a server-enforced base CAS. GitHub native merge queues are unavailable for this personally owned private repository under the current platform eligibility rules.

After a confirmed merge, the trusted queue also attempts remote head cleanup, independently of merge acceptance. It confirms the merged PR and exact reviewed head, same-repository worker lane, non-default/unprotected branch, complete open-PR head/base identities with no other use, and unchanged branch/ref SHA immediately before deletion. An already absent branch is clean; advanced, protected, shared, fork or uncertain heads remain with a durable `head_cleanup` reason. A bounded API/time budget stops oversized or slow cleanup before starting further calls. API/deletion errors are pending cleanup and never invalidate the successful merge. GitHub's automatic-delete checkbox remains enabled but is not the queue's sole cleanup mechanism. The GitHub delete-ref endpoint has no SHA guard; the final read/delete interval cannot atomically exclude an out-of-band push or new PR. Workers must use fresh branches after merging and never push to or reuse merged heads. This cleanup does not remove local branches/worktrees, original evidence, or archived PRs.

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
The queue classifier runs trusted current-main code against GitHub's complete file list and verifies the reviewed head. Geography focused selection reads the linked issue and requires matching lane/mode and safe declared owned prefixes; missing or invalid scope fails rather than allowing reduced tests. Out-of-scope files or rename origins retain full regression;
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
checker-code identity separate from baseline and candidate data identities. It
runs the genuine cold native-conservation and continuous-geometry comparisons;
the actual final queue candidate executes this check once. Historical artifacts
cannot replace that current final job.
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

Submit `worker-merge.yml` directly on main with the exact reviewed head and a fresh
request ID. `queue: max` retains up to 100 pending executions; excess executions
can be cancelled. There is no separate scheduler, registration comment, FIFO
ticket, dispatch-attempt ledger, completion wake or automatic recovery daemon.
Provider ordering, queue limits and runner availability remain external controls,
not an application-level availability guarantee. No queue-capacity engine is
introduced; existing per-run API quota and deadline guards remain mandatory.

Record the matching run ID/URL and use `gh run list`, `gh run view` and
`gh run watch` to inspect it. Preserve failure diagnostics and result receipts,
then independently verify actual PR merged state, exact head and squash commit.
An interrupted local wait does not end a workflow. An uncertain dispatch, missing
run on a bounded history page, pending state or missing receipt never authorizes a
blind duplicate. After a settled failed/cancelled execution, reconcile the PR and
all earlier unresolved executions. With successful preparation and unchanged
reviewed head/tested main, address the cause and rerun failed jobs of that same
execution; successful original jobs need no repetition. Failed preparation or a
changed base requires a fresh request. Changed reviewed bytes require new
substantive review. See [MERGE_QUEUE_CLIENT.md](MERGE_QUEUE_CLIENT.md).

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

The existing HTTP client admits every actual request using response-header core
quota, including concurrent charges and conditional 304 refunds. It retains a
16-request recovery floor, bounded GET-only retries after recognized quota
rejections and a fresh repository probe after a reset. No ordinary permission
failure, ambiguous transport outcome or write is automatically retried.

The worker entrypoint binds its deadline to the authenticated current prepare or
merge job's start and the executing workflow's immutable literal timeout (10 or
75 minutes). Setup time is charged. Workflow/job metadata share a finite startup
budget; requests and waits must fit a complete 20-second HTTP attempt before the
existing 30-second finalization reserve. Local entrypoint runs also have finite
deadlines. Failed startup authority or deadline admission closes all further
HTTP, including optional cleanup/notification. Once a deadline is admitted, only
the client's already-restricted exact-owned candidate cleanup
and result-notification routes can use that final reserve; they keep the same
quota state and bounded recovery allocation. This is best-effort cleanup, not a
guarantee against concurrent quota depletion or a slow provider.

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
the worker's own delivery directory. The package definition may only append exact
new data file entries reachable through the fixed selected-reader roles, preserving
all existing entries, order and other policy fields. Supporting JSON/log evidence
cannot create package/import authority. Unknown boundaries retain all three full
regression shards.

The linked issue's explicitly declared scientific evidence manifest may also be
updated as metadata. Its exact path comes from the current validated issue contract,
not a candidate filename or broad JSON allowance. Both tree entries must be ordinary;
the receipt must stay outside fixed selected/base roles and actual package inputs
or verification paths. The base check authenticates the unchanged native manifest,
transport index, source bank, selected comparison registry and consumption/code
metadata, then excludes their declared reader roles without reading scientific leaves. Bounded syntax checks do not replace its independent
scientific/evidence validation or exact-head review. Arbitrary existing packet JSON
edits, consumed manifests and unavailable qualification retain complete regression.

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

The Cloudflare step does not measure the historical Sites archive reserve; the
separate main-push Deployment package budget workflow retains its actual Sites
build and file/archive accounting. Parallel build removal reduces runner work;
no wall-time improvement is established merely by adding those job durations.

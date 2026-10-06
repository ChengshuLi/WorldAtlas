# Issue lifecycle accuracy

GitHub issues own acceptance, dependencies, remaining work and dated evidence. PRs
own implementation/review evidence. Merging is separate from completing an issue.
Use the existing labels and ordinary comments; no additional ledger or mandatory
handoff form is required. Readiness is reviewed eligibility, not scientific approval.

## Before readying or claiming

Run `node scripts/review-issue-readiness.mjs ChengshuLi/WorldAtlas NUMBER OUTPUT [BRANCH]`
with the read-only GitHub token in GH_TOKEN. This shares mechanical contract, lane,
evidence-declaration, dependency, budget and geography-owned-path checks with claims.
Its output explains rejection reasons and incomplete reads. It never changes labels,
claims, approvals or production. A ready label remains required for an actual claim.
The command examines unready issues so it can be used before adding ready.

Inspect original acceptance, newer comments, source/production waits and canonical
ownership too. Eligibility cannot decide whether a research conclusion is supported.
Resolve rejection reasons before marking ready. A failed claim is a safety net: repair
routine stale metadata or explain the next action on the issue, rather than leaving
an unexplained rejection. Evidence support deficiencies belong in bounded engineering
work; never fabricate subjects or discard a scientific gate to make a claim pass.

Use fresh complete issue, comment, dependency and linked-PR reads. Immediately before
an issue mutation, reread these inputs and preserve concurrent owner changes. GitHub
issue updates have no atomic compare-and-swap: stop/reassess changed snapshots, make
narrow edits rather than replacing whole label sets, and read back every mutation.
Do not mutate on partial pagination/API failure. An uncertain mutation outcome requires
readback before retry. Canonical bot claims, not convenience labels/assignees, own work.

## Author and premerge reviewer

After a meaningful result, and before moving to another job, reconcile the original
acceptance: finished work with evidence, remaining work and its next action. Each PR
explains which criteria it advances and what happens next. The independent reviewer
checks these statements against actual changes and evidence alongside exact-head review.
A partial implementation may merge without completing the whole issue.

Use `Closes #N` only when every original criterion is proven, including required
production acceptance. Otherwise use `Refs #N`. Initial research may finish with
explicit unknowns where its original promise permits that; correction or approval
work cannot close merely because the uncertainty was documented. No closure grants
geography approval, publication or import permission.

Before the last allowed partial PR, review all remaining obligations. Continue on the
original issue while implementation allowance remains. After exhaustion, reuse an
existing bounded follow-up or create one for a genuinely distinct unfinished task;
an explicit external/production wait can stay on the original issue. Do not force
duplicates, silently increase the budget or close just because the allowance ended.
An issue requiring no additional implementation can be reconciled without another PR.
Follow-ups belong to their lane/role, not permanently to the creating chat.

Substantive issue-contract, acceptance or PR-disposition changes require renewed
review. New PRs use the existing review receipt's issue_contract_sha256 and
pr_body_sha256 bindings; comments alone do not invalidate those bindings. Existing
PRs retain the activation compatibility described in PREMERGE_EVIDENCE_REVIEW.md.

After merging, verify the actual merge and reconcile the issue again. If interrupted,
the next responsible worker uses the merged PR, review and durable checkpoint; a
missing final comment is neither proof of completion nor reason to repeat the work.
Preserve original evidence, dates, source bytes, closed repairs and human deferrals.

## Dependencies, waits and recovery

The worker changing dependencies updates readiness at the same time. When completing
an issue, inspect its direct dependents, including other lanes. Check all remaining
dependencies, evidence, ownership, scope and budget before marking ready. Reopened
dependencies or invalidated evidence require readiness reconsideration. Routine
unclaimed metadata repairs are local; cross-lane scientific/ownership decisions go
to the responsible role. Do not grant another lane's scientific approval.

A wait identifies its missing input, responsible role, observable resume condition
and prior evidence/attempt. Revisit when that condition changes. Leave unchanged,
well-documented blockers alone; do not rerun the same unavailable source indefinitely.
Publisher discovers production acceptance on original publisher-needed issues and
existing deployment/change records. Auditor owns its quality follow-ups and #726;
neither role acquires unrelated housekeeping duties.

An available same-lane worker may reconcile an unclaimed issue. An active claim or
open PR stays with its owner. For expired claims inspect checkpoints, live PRs and
operations, then follow explicit approved recovery; expiry never authorizes takeover.
Disputed scope, conflicting ownership, unresolved cross-lane authority and decisions
requiring human/provider approval are escalated to Main/human with a concrete question.
Reopen prematurely closed work only with original-acceptance evidence; do not reopen
a completed historical repair just because its old blocker appears in a report.

## Between jobs and instruction adoption

Before selecting the next implementation, inspect up to three neglected unclaimed
same-lane issues with apparently finished dependencies or previously discovered
readiness problems. Include blocked/missing-ready work, not only the ready queue.
Prefer older last relevant issue review/checkpoints and avoid repeatedly examining
unchanged documented blockers. Handle routine repairs on original issues; do not
create another queue/table. If all relevant workers are inactive, maintenance waits.
The manual queue audit can support an explicit investigation; there is no hourly
unread report, event-driven audit workflow or background chat monitor.

Repository prompts do not rewrite saved chat goals. Existing workers refresh before
their next job, preserving active identity, claim, exact-head review and checkpoints.
Actual subsequent handoffs and dependent reviews prove adoption; edited files alone
do not. Main needs no periodic full-queue housekeeping obligation.

Copy-ready refresh:

> Before your next job, reread AGENTS.md, docs/WORKER_COORDINATION.md,
> docs/ISSUE_LIFECYCLE.md and your role prompt on current main. Preserve active
> ownership and checkpoints. Reconcile your issue's original acceptance and next
> action after results/before moving on; review direct dependents on completion or
> dependency changes. Between jobs review up to three neglected unclaimed same-lane
> readiness problems. Use shared read-only readiness checks before readying/claiming;
> no scientific approval from machine eligibility. Keep merging separate from closure,
> preserve waits/publisher-needed, reuse genuine bounded follow-ups, and never take over
> an expired claim automatically. Report adoption with actual issue handoff/dependency
> evidence. Do not restart paused work or perform unapproved production operations.

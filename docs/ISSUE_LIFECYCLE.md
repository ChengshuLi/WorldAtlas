# Issue lifecycle accuracy

GitHub issues own acceptance, dependencies, remaining work and dated evidence. PRs
own implementation/review evidence. Merging is separate from completing an issue.
Use the existing labels and ordinary comments; no additional ledger or mandatory
handoff form is required. Readiness is reviewed eligibility, not scientific approval.

## Before starting work

Read original acceptance, current comments, active PRs and actual source/production
waits. Comment with the worker ID, branch, bounded scope and planned checks; the
parent coordinates overlap. Labels summarize that decision. No machine readiness
review, canonical lease or routine triage sweep is required for ordinary work.
Scientific approval and actual production authorization remain separate.

Before changing an issue, read its current body and discussion and preserve other
workers' changes. Make narrow edits and read them back; an uncertain write needs
readback before retry. Preserve historical claims and checkpoints.

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

Continue unfinished in-scope work on the original issue, regardless of merged PR
count. The legacy `max_prs` field is a positive planning estimate, not an allowance.
No budget bump or successor issue is needed. Review remaining obligations after
meaningful results; split only for a distinct deliverable, ownership or genuine wait.
Reuse an existing follow-up before creating another. Do not silently expand acceptance
or close merely because an estimate was exceeded. Explicit human limits still apply.
Follow-ups belong to their lane/role, not permanently to the creating chat.

Substantive issue-contract, acceptance or PR-disposition changes require renewed
review. New versioned-evidence PRs use the existing review receipt's issue_contract_sha256 and
pr_body_sha256 bindings; comments alone do not invalidate those bindings. Existing
PRs retain the activation compatibility described in PREMERGE_EVIDENCE_REVIEW.md.

After merging, verify the actual merge and reconcile the issue again. If interrupted,
the next responsible worker uses the merged PR, review and durable checkpoint; a
missing final comment is neither proof of completion nor reason to repeat the work.
Preserve original evidence, dates, source bytes, closed repairs and human deferrals.

## Dependencies, waits and recovery

The worker changing dependencies updates readiness at the same time. When completing
an issue, inspect its direct dependents, including other lanes. Check all remaining
dependencies, evidence, ownership and scope before marking ready. Reopened
dependencies or invalidated evidence require readiness reconsideration. Routine
unclaimed metadata repairs are local; cross-lane scientific/ownership decisions go
to the responsible role. Do not grant another lane's scientific approval.

A wait identifies its missing input, responsible role, observable resume condition
and prior evidence/attempt. Revisit when that condition changes. Leave unchanged,
well-documented blockers alone; do not rerun the same unavailable source indefinitely.
Publisher discovers production acceptance on original publisher-needed issues and
existing deployment/change records. Auditor owns its quality follow-ups and #726;
neither role acquires unrelated housekeeping duties.

An available same-lane worker may reconcile an unclaimed issue. An active branch or
open PR stays with its owner. Preserve historical claims and checkpoints; coordinate
a handoff instead of assuming that an expired record authorizes takeover.
Disputed scope, conflicting ownership, unresolved cross-lane authority and decisions
requiring human/provider approval are escalated to Main/human with a concrete question.
Reopen prematurely closed work only with original-acceptance evidence; do not reopen
a completed historical repair just because its old blocker appears in a report.

## Instruction adoption

Existing workers reread AGENTS.md, WORKER_COORDINATION.md and their role prompt
before the next job. Reconcile the original issue after meaningful results and
when moving on. Address encountered blockers and direct dependencies when needed;
there is no mandatory between-jobs readiness audit or replacement queue ledger.
Preserve active work, real waits, evidence, source bytes and production gates.

Geography ownership may name a safe subdirectory inside an owned packet or
campaign. Preserve that narrower scope: an edit must not silently grant the whole
enclosing packet. Enclosing and nested scopes overlap; siblings can remain disjoint.

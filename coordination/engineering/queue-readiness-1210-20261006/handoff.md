# Issue lifecycle accuracy — #1210

This implementation replaces the unmerged draft's ledger/attention-label/event
workflow and mandatory disposition form with the human-approved lifecycle design.
Original GitHub issues retain acceptance, dependencies, ownership and next actions.
Authors/reviewers reconcile completion separately from merging; dependency owners
review direct dependents; available same-lane workers review neglected unclaimed
readiness problems between jobs. Auditor and Publisher retain their existing roles.
The hourly report trigger is removed; explicit investigations remain read-only.
The merge scheduler and merge-integration machinery are unchanged.

Read-only readiness and claims now share contract/lane/evidence/dependency/budget,
explicit-blocker and geography-owned-path validation. The targeted command preserves
incomplete-read/changed-snapshot failures and canonical ownership. Claim mutations
reread issue and canonical ownership before writing. These are cooperative gates,
not atomic GitHub issue transactions or scientific approval.

The existing review receipt binds normalized original acceptance/work scope and PR
body for new PRs; substantive contract/closure changes require renewed review.
Ordinary comments and JSON formatting do not invalidate the binding. Pre-existing
PRs retain activation compatibility; all voluntarily supplied bindings are checked.
No public application API or separate handoff schema is introduced.

Current local controls cover shared eligibility disagreement, ownership conflicts,
partial/stale reads, expired claims, explicit resolved/unresolved blockers and
review contract/disposition drift, plus existing evidence/claim/handoff/integration
regressions. controls.txt records the current run. compatibility-controls.txt is
an archived earlier-draft regression run, not evidence for unexecuted current code.
Local controls do not prove hosted workflow behavior or actual worker adoption.

Remaining #1210 work includes retrospective original-acceptance reconciliation,
independent final exact-head review, hosted merge and actual main/workflow readback,
and adoption through subsequent real handoffs/dependency reviews. Use Refs #1210;
this PR alone must not close the whole task. #1208 separately owns typed hierarchy
subjects; preserve its technical gate and other workers' claims. No scientific,
provider, production or import operation is authorized by this change.

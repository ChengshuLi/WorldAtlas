# Worker queue readiness and remaining-work handoffs

Run `GH_TOKEN=... node scripts/queue-readiness-audit.mjs OWNER/REPO report.json previous-complete-report.json` using a server/local secret, never credentials pasted into chat. Token permissions: repository metadata, issues and pull requests read. This command performs GET requests only; no claim, label, issue, closure, merge or deployment mutation exists.

Before marking a work item ready, issue triage runs `GH_TOKEN=... node scripts/review-issue-readiness.mjs OWNER/REPO ISSUE_NUMBER review.json` using this same validator and reviews its findings on the actual current issue. `assessIssue` accepts current dependency, comment, lease and PR evidence. A missing-ready finding is a candidate for review, never authorization to change a label. Refetch these inputs immediately before a manually reviewed change; if they changed, repeat review. There is no automatic readiness, closure or recovery command. Active leases, live operations and open PRs require coordination with their existing holders.

The hourly main-only workflow exhausts paginated issues, open PRs, comments and timelines, and fetches all declared dependencies and linked PRs. Four issues are inspected concurrently to bound API pressure. Invalid/unknown future types, scopes, evidence declarations and budgets are findings, not skipped work. Symbolic pin names remain valid when their SHA values and manifest bindings meet the evidence policy. It checks canonical bot claims rather than treating a GitHub assignee as worker identity. Closed research does not certify a region; content issues always require separate published-certificate and release-pin review by the existing gate.

Reports contain stable issue/code/detail fingerprints, new and resolved findings, failures and the last successful coverage time. The scheduler restores its previous complete report from the Actions cache and publishes a bounded artifact/summary. Incomplete reads fail the job and retain the successful checkpoint; they cannot declare prior findings resolved. Cache eviction means the next complete report becomes a fresh baseline and may repeat artifact findings. No automatic duplicate issue/comment notifications are created. Artifacts retain 30 days; caches are convenience, not an archival work record.

Source/access/decision blockers can be made unambiguous in an issue comment:

```text
<!-- worldatlas-blocker:v1
{"id":"original-source-access","active":true,"reason":"Original source currently returns HTTP 403"}
-->
```

Only a reviewed subsequent comment with the same ID and `active:false` clears that explicit marker. Possible legacy blocker prose is reported with a comment ID for human inspection; wording alone does not establish whether the blocker remains active. The audit does not change this history or automatically remove `status:blocked`. Geographical truth, source availability and production permissions remain independently reviewed constraints.


## Act on findings on the original issues

The main-only workflow uses a separate trusted step to add/remove only
`coordination:triage-needed` on original issues. It creates no ledger, duplicate
issue or recurring comment. The scanner itself remains GET-only; the workflow
requires issues-write for this dedicated flag. Actionable findings include
invalid contracts, dependency/status contradictions, missing readiness review,
expired/ambiguous claims, overlapping ownership and exhausted PR budgets.
An ordinary active claim, open PR or legacy blocker wording alone is not a flag.
The flag is attention, never permission to implement, recover, close or publish.
Before mutating it, the step rereads the issue and checks the observed timestamp,
body and other labels. Changed inputs are deferred to the next audit. Incomplete
coverage can add flags but cannot remove previous flags. Complete coverage may
remove a flag whose mechanical finding disappeared; this does not establish
acceptance. Only this label is mutated, preserving all worker/status labels.

Main / issue creation owns reviewing flagged issues before its next queue refresh
or issue-creation pass. Review actual acceptance, merged PRs, source limits,
canonical claims, dependencies and existing open/closed children. Record the
reason and concrete next action on the original issue. Repair malformed
contracts; mark reviewed actionable work ready; retain genuine gates with the
blocking issue, required input or operator decision. Respect active holders and
expired checkpoints. Auditor continues quality review and follow-ups under #726;
its table is not a second readiness queue.

A closed dependency triggers review, not automatic readiness. Missing source
bytes may be the research question the issue asks a worker to investigate.
Where acceptance permits an honest unavailable-source result, complete that
bounded review and link restoration/correction work; do not leave the initial
review permanently blocked merely because geography remains unapproved.
Actual corrections, source verification, certificate approval, imports and
publication retain their own acceptance and gates.

## Last partial PR and exhausted budgets

Before spending the last allowed PR, map **every original acceptance criterion**
to satisfied evidence or a real bounded remaining-work issue. Search existing
open and closed issues first; reuse them and preserve completed children. Do not
raise the budget, repeat the same failed source search, or declare approval.
Release a finished implementation claim safely even while separately tracked
production/source acceptance remains; this rule does not prevent lease release.

The trusted merge queue checks new issues created on/after the activation in
`.github/queue-handoff-policy.json`; legacy work can opt in with
`queue_handoff_required:true` in its work scope. A last partial `Refs #N` PR
must carry the following marker in its PR body. The queue rereads it and actual
follow-up issues both before integration and immediately before merging.
The normal independent exact-head review checks that the criterion mapping is
substantive and complete; schema validation cannot judge scientific acceptance.
A complete PR uses `Closes #N` only when all original acceptance is fulfilled.

```text
<!-- worldatlas-queue-disposition:v1
{"version":1,"issue":123,"scope_sha256":"SHA256_OF_JSON_STRINGIFY_PARSED_WORK_SCOPE","merged_prs":[124,125],"criteria":[{"criterion":"Original acceptance item","status":"satisfied","evidence":["https://github.com/OWNER/REPO/pull/124"],"follow_up_issues":[]},{"criterion":"Remaining acceptance item","status":"remaining","evidence":["https://github.com/OWNER/REPO/pull/125"],"follow_up_issues":[126]}]}
-->
```

`merged_prs` is the sorted complete merged list **including the candidate PR**
when submitting the last partial PR. After verified merge, copy the reviewed
mapping into a dated comment on the original issue with the actual merge SHA and
claim-release/handoff facts. This gives the retrospective audit durable evidence.
The scope digest uses the exported `scopeDigest` helper in
`scripts/queue-disposition.mjs`; scope or merged-PR changes invalidate a stale
mapping. Existing exhausted issues without a mapping are triage findings, not
permanent external blockers. Triage decides whether original bounded acceptance
is complete, what still needs children, and how the original issue should remain
tracked. No machine marker authorizes closure.


## Event checks first, hourly catch-up second

The trusted `queue-readiness-events.yml` workflow checks the changed original
issue and open work items depending on it after issue/status/comment changes or
a confirmed PR merge. It uses current main code only, treats event text as data,
and never checks out or executes a PR head. Attention-label changes and PR
comments are ignored. Targeted reports declare their exact coverage and cannot
consume a global checkpoint or resolve unrelated findings.

The normal worker merge and accepted claim-release workflows invoke the same
focused checker directly after their durable result. This handles bot-driven
work without relying on another event being emitted. Queue-refresh failure is
reported separately and never changes an accepted merge or safe release into a
rejection. The hourly full audit catches missed/interrupted events and manual
changes. These checks flag review; Main / issue creation must perform it. They
cannot establish scientific acceptance or substitute for the worker's handoff.

The read-only preflight checks the target and current dependencies/PR/claim evidence, and compares owned paths with every open geography declaration even in targeted mode. Review its findings, inspect scientific/source/publication gates, and refetch mutable inputs before labeling ready. It does not set readiness itself.

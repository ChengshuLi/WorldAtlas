# Read-only worker queue audit

Run `GH_TOKEN=... node scripts/queue-readiness-audit.mjs OWNER/REPO report.json previous-complete-report.json` using a server/local secret, never credentials pasted into chat. Token permissions: repository metadata, issues and pull requests read. This command performs GET requests only; no claim, label, issue, closure, merge or deployment mutation exists.

Before marking a work item ready, issue triage runs this same validator and reviews its findings on the actual current issue. `assessIssue` accepts current dependency, comment, lease and PR evidence. A missing-ready finding is a candidate for review, never authorization to change a label. Refetch these inputs immediately before a manually reviewed change; if they changed, repeat review. There is deliberately no apply command. Active leases, live operations and open PRs require coordination with their existing holders.

The hourly main-only workflow exhausts paginated issues, open PRs, comments and timelines, and fetches all declared dependencies and linked PRs. Four issues are inspected concurrently to bound API pressure. Invalid/unknown future types, scopes and budgets are findings, not skipped work. It checks canonical bot claims rather than treating a GitHub assignee as worker identity. Closed research does not certify a region; content issues always require separate published-certificate and release-pin review by the existing gate.

Reports contain stable issue/code/detail fingerprints, new and resolved findings, failures and the last successful coverage time. The scheduler restores its previous complete report from the Actions cache and publishes a bounded artifact/summary. Incomplete reads fail the job and retain the successful checkpoint; they cannot declare prior findings resolved. Cache eviction means the next complete report becomes a fresh baseline and may repeat artifact findings. No automatic duplicate issue/comment notifications are created. Artifacts retain 30 days; caches are convenience, not an archival work record.

Source/access/decision blockers can be made unambiguous in an issue comment:

```text
<!-- worldatlas-blocker:v1
{"id":"original-source-access","active":true,"reason":"Original source currently returns HTTP 403"}
-->
```

Only a reviewed subsequent comment with the same ID and `active:false` clears that explicit marker. Possible legacy blocker prose is reported with a comment ID for human inspection; wording alone does not establish whether the blocker remains active. The audit does not change this history or automatically remove `status:blocked`. Geographical truth, source availability and production permissions remain independently reviewed constraints.

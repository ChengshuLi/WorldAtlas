# Read-only queue investigations

Issue maintenance is part of normal worker jobs: see [ISSUE_LIFECYCLE.md](ISSUE_LIFECYCLE.md).
The former hourly schedule is disabled because its report had no reliable consumer.
The five-minute merge scheduler remains unchanged. No replacement event workflow,
attention-label queue, ledger or chat monitor is introduced.

For explicit investigations, `queue-readiness-audit.yml` remains workflow_dispatch-only
and read-only. `node scripts/queue-readiness-audit.mjs REPO OUTPUT [PREVIOUS_REPORT]`
examines paginated open issues, comments, dependencies and linked PR timelines. It
reports malformed contracts, shared eligibility rejection, ownership overlaps,
claim/label drift, budget exhaustion and readiness candidates. Incomplete reads cannot
report resolved findings or replace the last complete checkpoint. Evidence-schema
eligibility is not source approval; prose warnings can refer to already repaired
historical blockers and require reading newer evidence.

For one issue before marking ready or claiming use
`node scripts/review-issue-readiness.mjs REPO NUMBER OUTPUT [BRANCH]`. Both commands
are read-only. The targeted command explains rejection reasons, preserves active
ownership and fails incomplete reads. GH_TOKEN supplies authentication; never commit
credentials or local cache paths. Investigation outputs are scratch, not another
public status table. The investigating worker consumes findings on original issues.

A closed dependency is an invitation to review, not automatic readiness. An exhausted
budget requires acceptance reconciliation, not forced child creation. Preserve genuine
external/production waits, human decisions and canonical claims. Read fresh snapshots,
make narrow changes and read back outcomes as described in ISSUE_LIFECYCLE.md.

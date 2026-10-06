# Independent implementation and publication

Ordinary engineering workers validate implementation without depending on the production publisher. Local or deployed previews identify their exact code, dataset and runtime. Read-only features may use an authorized production read-only API/connection; ordinary bounded reads need no deployment appointment. Writes, imports, migrations or destructive tests use isolated data/database, and heavy load tests require coordination. Never give a preview production write credentials or silently run its startup migrations against production. Functional checks must exercise the real changed behavior rather than only mock its implementation. A preview proves its stated scope; it does not prove current production credentials, bindings, real database recovery, deployed geography certification or production performance. Remote preview access/hosting must be authorized; this protocol provisions no services or credentials.

## Performance acceptance

A worker may verify a loading-time target in its own preview using a full authorized snapshot of the real atlas in isolated storage, or authorized production read-only access. Record exact code/data pins, dataset size, hosting/database configuration and region, browser/device/network, measured start/end event and cold/warm cache/connection conditions. Exercise the real API/rendering path and repeat enough runs to expose variation; report the stated statistic and failures rather than the fastest run. A tiny fixture, localhost-only speed or a different backend cannot establish an equivalent hosted target. If a preview calls the existing production API, it exercises that deployed backend version; changes to API/server code must also execute the changed code under test rather than silently benchmark the old handler. Shared production cache/traffic effects must be recorded. These measurements can satisfy implementation acceptance when the issue agrees on those conditions; identify any production-only residual separately. The publisher later verifies actual delivery/deployment regressions without holding the implementation worker idle.

## Merged work and original issues

A reviewed PR already carries its issue relationship: exactly one `Refs #N` (partial) or `Closes #N` (all acceptance verified) line. Record implementation evidence and any production-only remainder on that original issue. Do not duplicate ordinary changes in #714. If actual production acceptance is required, keep the issue open, add `publisher-needed`, describe exact checks/pins/dependencies/rollback, and prevent duplicate implementation claims. Source-only evidence and documentation generally need no Site release. A complete original-issue handoff permits safe claim release once all PRs are merged/closed and no holder-run live work remains. The publisher does not require an implementation claim or live flag solely for delegated publication.

The label catches work that a commit comparison cannot: #51's special backup/restore operation, or a failed/deferred check after its code was already delivered. It is discovery, never authorization or readiness. Workers need not label ordinary delivery-only changes. Closed linked issues still appear in release discovery; inspect their delivery impact without assuming they need reopening. Close an issue only when all its actual criteria are proven. New implementation required after handoff uses a reviewed bounded issue, never a silently resumed released branch.

## Every publisher run

Use Node 24 and authenticated GitHub CLI; the planner makes GET requests only:

```sh
node scripts/publication-plan.mjs > publication-plan.json
```

The tool pins current primary `main` once, reads the complete GitHub deployment registry, compares the last verified primary delivery commit with that pinned target, enumerates associated merged PRs and their explicit original-issue references (including closed issues), and reads open `publisher-needed` issues. Unlinked commits/PRs remain visible for manual classification. GitHub pagination/ancestry failures stop planning. No last-24-hour search, mirror-SHA comparison or moving-branch build is allowed. The CLI defaults to immutable `coordination/publication/bootstrap.json`, reconstructed from retained Site24 build/mirror/native/served evidence at primary c5fce098; it is historical evidence, not a fresh production probe. Registry delivery supersedes it. A supplied `--bootstrap VERIFIED-DELIVERY.json` is an explicit initial-boundary override requiring equally reviewed evidence; never advance a bootstrap to skip undelivered work. Retain original evidence and reconcile any mismatch with actual served state before live work. Missing or incoherent history blocks delivery planning rather than assuming current main has shipped.

The target is latest main **at run start**. Compatible changes may ship together; later merges wait for the next run. Inspect each change's impact and original criteria, including data/release/lookup/assets compatibility. Evidence-only changes can be classified as requiring no delivery. A code commit is independent of geographic release numbering: a UI-only deployment need not create a new dataset release. Never deploy an incompatible latest tree merely because it merged. Record the blocker and repair through normal issue/PR coordination.

The planner separates delivery from issue acceptance. Successful delivery advances the primary boundary even if an issue-specific test fails or is deferred; that result remains discoverable from the registry and `publisher-needed`. Failed deployment never advances the boundary. The planner reports every issue as unreviewed: the publisher must freshly establish substantive eligibility, review/CI/pins, permissions/dependencies, preserved records, rollback and all unsettled operations before live work. Urgent eligible work comes first; unrelated blocked acceptance need not prevent a compatible safe release. An unsettled live operation does prevent another live operation.

## Durable operation and delivery records

Use GitHub's native Deployments API in the **primary repository** as a durable operation index, not a new issue queue. It records metadata; it does not itself publish the Site. Exactly one designated publisher creates records with `environment: "worldatlas-production"`, `task: "worldatlas-publication"`, `ref: EXACT_PRIMARY_SHA`, `auto_merge: false`, and `required_contexts: []` (the publisher separately verifies applicable review/CI). Before external work, register `payload.worldatlas_publication`:

```json
{
  "version": 1,
  "operation_id": "UNIQUE_ID",
  "publisher_worker_id": "ACTUAL_PUBLISHER_ID",
  "kind": "site",
  "primary_commit": "EXACT_40_CHARACTER_PRIMARY_SHA",
  "issues": [6, 638, 712],
  "started_at": "UTC_TIMESTAMP",
  "expires_at": "BOUNDED_UTC_TIMEOUT",
  "rollback_url": "https://github.com/ChengshuLi/WorldAtlas/issues/6#issuecomment-ACTUAL_ID"
}
```

Use `kind: "recovery"` for a tracked special operation that does not advance Site delivery. Also retain the complete operation-specific approved release/data/assets/lookup pins, scope, access/read-only/drain/recipient, rollback and expiry evidence on its original issue; these general fields cannot replace SQL window/reservation gates. Post an `in_progress` deployment status before external work. Re-read **all** registry records immediately before registration/start, together with legacy #714 and original-issue operations during transition. No status or an active/unknown status blocks overlap, even after expiry. This is cooperative serialization, not an atomic/server-enforced lock. A newer success cannot hide an older unsettled operation. Do not delete records or use automatic inactivation to imply cleanup.

Immediately after the operation and served checks, append exactly one `worldatlas-publication-result:v1` JSON marker to an originating issue, authored by an authorized repository owner/member/collaborator. Preserve earlier receipts. Fields:

- `version: 1`, numeric GitHub `deployment_id`, identical `operation_id`, `publisher_worker_id`, and `primary_commit` from registration.
- `state`: `verified`, `failed-settled`, or `unsettled`; `cleanup_confirmed` is true only for the first two. Include actual rollback/cleanup evidence and limits in the comment.
- `delivery`: null for failed/recovery operations. For verified Site delivery, an object with `version: 1`, exact `primary_commit` and separate mirror `source_commit`, `site: {project_id, version, deployment_id}`, `release_id`, `hierarchy_sha256`, `footprint_sha256`, `assets_sha256`, and nonempty `evidence_urls`. Retain exact lookup/runtime/backend identity in those linked receipts. Never substitute the source mirror commit for the primary commit.
- `issue_checks`: exactly one row per registered issue: `{issue, outcome, evidence_urls}`. Outcomes are `verified`, `failed`, `deferred`, `not-applicable`; evidence is nonempty. Deployment success does not imply every issue passed. Retain the actual criteria/method/conditions/limits on each originating issue, link them here, and add/retain `publisher-needed` before settlement for incomplete acceptance. Remove the label only when the remaining publisher scope is completed or explicitly superseded with a discoverable linked issue.

Then create a deployment status with `state: "success"` for verified/cleaned operation, `"failure"` for failed-settled, or `"error"` for unsettled; `log_url` is the result comment URL and **`auto_inactive: false`**. Unsettled explicitly remains blocking. A missing/mismatched receipt fails closed. The latest outcome for each issue persists independently of delivery; failed/deferred results are rediscovered even if a label was accidentally removed. All settled Site delivery commits must form a monotone ancestor chain. Rollback that changes delivered code needs explicit operator reconciliation; do not silently move the boundary backwards.

Keep result comments and deployment records immutable after settlement. A correction is a new explicit reconciled record, with evidence explaining the old result. These cooperative records validate structural coherence, not the truth of production tests. No deployment status certifies geographic approval or grants production access.

## Production-specific exceptions and transition

Current database recovery requires actual-source evidence, not a synthetic restore. Follow CURRENT_POSTGRES_RECOVERY.md: use a bounded publisher-owned child after explicit release of the original implementation claim, toggle only its own live flag, and preserve exact scope/tool/main/recipient/read-only/drain/cleanup gates. New child/window tracking uses the originating issue (`queue: 51` for #51); legacy `queue: 714` remains readable and valid for already-agreed operations. Never amend an active legacy operation merely to switch tracking location or clear another worker's flag.

Migrate outstanding #714 requests to their original issues with exact legacy links, honest blockers and `publisher-needed`. Preserve all #714 comments and operation receipts. Archive/close #714 only after discovery/boundary verification and explicit reconciliation of every old request/operation; closure is retirement of the queue, not proof that originating issues are complete. Until that checkpoint, read legacy unsettled records on every run and post new work to original issues/registry. A schedule changes only through an authorized recorded amendment.

The post-merge Auditor separately owns quality review and follow-up issue creation under #726; publisher discovery is for delivery and production acceptance, not a duplicate audit program. Existing publisher/worker chats must refresh saved goals/automation instructions once; repository edits do not rewrite running chat instructions. Reread this document and the role prompt on every run. This coordination change does not deploy, write production data, provision services or loosen research/import gates.

Issue completion follows [ISSUE_LIFECYCLE.md](ISSUE_LIFECYCLE.md). Publisher owns production acceptance on original publisher-needed issues; delivery alone does not prove every criterion. Record production evidence, remaining waits and direct-dependent disposition when completing production work. No unrelated queue-housekeeping duty is added.

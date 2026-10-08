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

The tool pins current primary `main` once, reads the complete GitHub deployment registry, compares the last verified primary delivery commit with that pinned target, enumerates associated merged PRs and their explicit original-issue references (including closed issues), and reads open `publisher-needed` issues. Cloudflare is the ongoing serving/publishing destination. Site, native recovery, Cloudflare public/private staging and recovery histories are read together: an unsettled operation in any reserved environment blocks another live operation. Unknown tasks/environments, incomplete pagination or incoherent receipts fail closed. Unlinked commits/PRs remain visible for manual classification. No last-24-hour search, mirror-SHA comparison or moving-branch build is allowed.

The CLI retains immutable `coordination/publication/bootstrap.json`, reconstructed from Site24 evidence at primary c5fce098, as historical evidence. Actual verified Cloudflare registry deliveries supersede that initial boundary without fabricating a Site version or changing the bootstrap. `coordination/publication/cloudflare-history.json` pins only the seven existing pre-transition payload/result records, including their singular-issue and staging encodings. The reader consumes hash-checked captured bytes; new records cannot opt into these exceptions. Historical normalization exposes only the primary/Worker/package identity actually present, with explicit absent-pin limits. It is sufficient for read-only change discovery, not a new deployment certificate or bootstrap override. Before live work, independently verify the full served/package/release/lookup/backend pins. New Cloudflare receipts below require them explicitly. Preserve supplemental historical acceptance rows even when they were not part of a singular original registration.

A supplied `--bootstrap VERIFIED-DELIVERY.json` is an explicit initial-boundary override requiring equally reviewed evidence; never advance a bootstrap to skip undelivered work. Retain original evidence and reconcile any mismatch with actual served state before live work. Missing or incoherent history blocks planning rather than assuming current main has shipped.

The target is latest main **at run start**. Compatible changes may ship together; later merges wait for the next run. Inspect each change's impact and original criteria, including data/release/lookup/assets compatibility. Evidence-only changes can be classified as requiring no delivery. A code commit is independent of geographic release numbering: a UI-only deployment need not create a new dataset release. Never deploy an incompatible latest tree merely because it merged. Record the blocker and repair through normal issue/PR coordination.

The planner separates delivery from issue acceptance. Successful delivery advances the primary boundary even if an issue-specific test fails or is deferred; that result remains discoverable from the registry and `publisher-needed`. Failed deployment never advances the boundary. The planner reports every issue as unreviewed: the publisher must freshly establish substantive eligibility, review/CI/pins, permissions/dependencies, preserved records, rollback and all unsettled operations before live work. Urgent eligible work comes first; unrelated blocked acceptance need not prevent a compatible safe release. An unsettled live operation does prevent another live operation.

## Durable operation and delivery records

### Ongoing Cloudflare publication

Build compatible new code from the immutable classified primary target using Node24 and the standard `ATLAS_PUBLIC_READ_ONLY=1 npm run build:cloudflare` entry point. Verify the actual package inventory, Worker/config, every referenced geography/lookup asset and the live published release/compact backend. Keep the existing runtime-role Neon secret and private `worldatlas-archives` binding; no database migration, source regeneration, secret rotation or write enablement is part of publication. Use the reviewed generated Wrangler configuration for upload/deployment, with credentials only in authorized environment/stdin. Register before any provider upload or deployment. A merge or prepared package alone never establishes delivery. A human-deferred or incompatible change in the pinned tree prevents wholesale delivery; leave it discoverable with its exact scope and reason.

New Cloudflare operations use native primary-repository Deployments metadata with environment/task `worldatlas-cloudflare-public` (or the explicit `worldatlas-cloudflare-staging` / `worldatlas-cloudflare-recovery` pair), `ref` equal to the **actually delivered application primary commit**, `auto_merge:false`, `required_contexts:[]`, and `payload.worldatlas_cloudflare`. Use `validateCloudflareOperation` from `scripts/publication-cloudflare.mjs` before registration. Its fields are:

- `version:1`, `protocol_version:2`, unique UUID `operation_id`, actual `worker_id`, `kind` (`cloudflare`, `staging` or `recovery`), exact `primary_commit`, nonempty unique `issues`.
- `started_at`, `expires_at` (positive bounded window no longer than two hours), repository `rollback_url`, actual prior `rollback_worker_version` UUID.
- Separate exact `discovery_commit` (main pinned at run start), `tool_commit` (reviewed operation implementation) and `authored_head`; repository `review_url`, `runtime_review_url` and `merge_receipt_url`. Tool provenance must not pretend that newer application code shipped.
- Fixed `origin`, `backend:"postgres"`, `read_only:true`, `database_writes:false`; `public_reads:true` only for public delivery. Private staging/recovery cannot advance the public boundary.
- Exact `release_id`, and SHA256 identities `package_inventory_sha256`, `worker_sha256`, `config_sha256`, `assets_sha256`, `lookup_sha256`, `hierarchy_sha256`, `footprint_sha256`, `catalog_sha256`, `source_fingerprint`. Package, Worker, config and lookup pins identify whole-file bytes; define the exact complete inventory encoding for an aggregate assets pin and retain its member byte descriptors. Hierarchy, footprint, catalog and fingerprint pins retain the matching release/backend definitions. Explain each pin's actual input and vintage on the original issue; a refreshed summary hash does not replace its original bytes.

Post `in_progress` before external work. Freshly read the global registry, authorized result/cleanup receipts, canonical ownership, original acceptance and human holds immediately before registration and mutation. This remains cooperative serialization. An unknown or expired operation is not cleaned merely because its status is terminal. Preserve all original records.

Immediately after provider and served checks, append exactly one `worldatlas-cloudflare-result:v1` JSON marker on an originating issue, with `version:1`, exact `deployment_id` (GitHub registry ID), `operation_id`, `worker_id`, `primary_commit`, settlement state and actual `cleanup_confirmed`, plus the same per-issue outcome/evidence rules below. Retain `worker_version`, `acceptance_url`, `public_reads`, `database_writes_enabled:false`, `database_information_deleted:false`, `original_site_and_storage_preserved:true`. New verified public results include an explicit `delivery` validated by `validateCloudflareDelivery`:

- `version:1`, `provider:"cloudflare"`, the actual application `primary_commit` and `cloudflare:{origin,worker_version, deployment_id, registry_deployment_id}`. Here `deployment_id` is the actual **Cloudflare provider UUID** and `registry_deployment_id` is GitHub's numeric operation ID. No Site/mirror identity is invented.
- The same exact release/backend/read-only and package/Worker/config/asset/lookup/hierarchy/footprint/catalog/fingerprint pins as registration, plus nonempty repository `evidence_urls`.

Failed, unsettled, staging and recovery results require `delivery:null`. Settle the GitHub status using the authorized result URL and `auto_inactive:false`; successful public delivery advances the primary boundary independently of remaining issue acceptance. Failed/deferred checks remain discoverable, including on closed original issues. Native SQL/recovery operations retain the existing `worldatlas-production` contract below; its history is unchanged.

### Bounded unchanged-version proof

When current-main application changes are explicitly deferred, a real deployment of the currently served immutable Cloudflare version can verify the publisher transition. This does **not** ship current main or advance beyond its actual application commit. Keep `discovery_commit` and reviewed `tool_commit` separate, pin `expected_worker_version` equal to `rollback_worker_version`, and set `publish_method:"republish-current-version"`. This narrow operation needs its own live canonical acceptance reservation: `reservation_issue`, `claim_id`, `claim_branch`, `reservation_scope_sha256` (SHA256 of `JSON.stringify(workSpec(issue.body))`). Only the holder toggles its own live flag.

After registration/start, run `node scripts/cloudflare-republish.mjs` with one hidden stdin JSON object containing numeric `deployment_id`, `account_id`, `api_token`, and an absolute fresh owned `output` directory. Never put credentials in arguments or save that input. The actual entry point validates ownership, all histories, current primary/package/Worker, native provider version, complete compact marker, matching release and four blocked mutation methods. It refreshes registry/ownership/dependencies immediately before its single provider POST, then confirms the actual newly created deployment UUID references the same version at 100%. It never uploads code, changes bindings/secrets, deletes objects or writes SQL. Redirects fail, response bodies/time are bounded, and fresh-output admission preserves existing files/symlinks. Uncertain mutation results are not retried or treated as settled; inspect actual provider history first.

The resulting `provider-deployment.json` deliberately says `delivery_settled:false`. Verify exact served frontend/assets, actual map/temporal hydration and API/release/read-only behavior, preserve whole-file receipts, then append/settle the authorized result. Remove only operation-owned temporary resources and release the live flag after confirmed cleanup. This unchanged-version path is an acceptance probe; ordinary compatible new code still follows the reviewed build/upload procedure above.

### Retained Site and native recovery records

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

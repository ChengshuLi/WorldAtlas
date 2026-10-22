# Reviewed PostgreSQL forward deployment

For schema-forward modes, the frozen fourteen-table copy and its original evidence must be verified first. `scripts/neon-forward-migrations.mjs` then applies reviewed PostgreSQL forward migrations without rotating credentials, changing Site audience or moving media. Only an explicitly pinned historical settlement bundle may be added through the existing private ingestion services after forward verification.

The workflow is `.github/workflows/neon-forward-migrations.yml`, with explicit manual dispatch for production, verify-only or rehearsal. Ordinary pushes and merges never select a forward operation. The selector uses Bash builtins, and the script checks the repository and branch. The workflow shares the owner-maintenance concurrency group with current PostgreSQL recovery. The completed original copy executor and workflow are retired; its original workflow/repository identities and exact committed receipt remain available to authenticate the preserved production proof. The forward executor does not depend on an expiring Actions ZIP.

Root owns the concrete operation and its publication. Do not substitute a successful rehearsal receipt for the production baseline. The original production run must be completed and successful; the whole committed `data/validation/neon-production-storage-migration.json` body must match the reviewed receipt hash, and its repository/workflow/head/run/attempt must match that original run. The original source identity, full-byte copy, runtime checks and readback remain mandatory. Historical artifact ID/hash fields are retained as provenance, not fetched as a second copy of the receipt. No forward operation is automatically created by this tool.

## Reviewed operation template

```json
{
  "version": 1,
  "project_id": "weathered-lab-37571695",
  "production_branch_id": "br-summer-butterfly-ar8qikk5",
  "core_schema_sha256": "1a43333772e6059d4fa97ce60baad7a27239616693c86708d08eadbc73b97618",
  "checkpoint_directory": "data/storage-checkpoints/d1-revision-1321",
  "checkpoint_sha256": "ACTUAL_CHECKPOINT_SHA256",
  "source_manifest_sha256": "ACTUAL_SOURCE_MANIFEST_SHA256",
  "source_snapshot_fingerprint": "ACTUAL_SOURCE_SNAPSHOT_FINGERPRINT",
  "source_revision": 1321,
  "site_origin": "https://worldatlas-explorer.chengshu-li-2013.chatgpt.site",
  "site_backend": "d1",
  "maintenance": {
    "receipt_file": "data/validation/forward-site-maintenance.json",
    "receipt_sha256": "ACTUAL_MAINTENANCE_RECEIPT_SHA256"
  },
  "migrations": [
    {
      "id": "0001_temporal_geography",
      "file": "postgres/migrations/0001_temporal_geography.sql",
      "sha256": "ACTUAL_REVIEWED_MIGRATION_SHA256"
    },
    {
      "id": "0002_footprint_versions",
      "file": "postgres/migrations/0002_footprint_versions.sql",
      "sha256": "ACTUAL_REVIEWED_MIGRATION_SHA256"
    }
  ],
  "baseline": {
    "run_id": "ACTUAL_PRODUCTION_RUN_ID",
    "run_attempt": "1",
    "head_sha": "ACTUAL_PRODUCTION_RUN_HEAD_SHA",
    "artifact_id": "ACTUAL_PRODUCTION_ARTIFACT_ID",
    "artifact_sha256": "ACTUAL_ARTIFACT_SHA256",
    "receipt_sha256": "ACTUAL_BASELINE_RECEIPT_SHA256",
    "run_url": "https://github.com/ChengshuLi/WorldAtlas/actions/runs/ACTUAL_PRODUCTION_RUN_ID"
  },
  "production_acknowledgement": "apply-reviewed-forward-migrations-after-verified-baseline"
}
```

All placeholder values fail validation. Migration IDs, file paths, order and byte hashes are pinned. The initial-baseline template supports the first migration alone, the first two, or all three known migrations in order (the third is `postgres/migrations/0003_typed_observations.sql`). For that initial route, source checkpoint parts are unpacked and independently verified before SQL. Do not run the historical revision-1321 example against a grown database.

Root privately verifies the Site's maintenance state and commits a fresh hash-pinned attestation:

```json
{
  "version": 1,
  "verification_method": "root-private-site-authenticated-read",
  "site_origin": "https://worldatlas-explorer.chengshu-li-2013.chatgpt.site",
  "backend": "d1",
  "source_revision": 1321,
  "source_snapshot_fingerprint": "ACTUAL_SOURCE_SNAPSHOT_FINGERPRINT",
  "read_only": true,
  "verified_at_utc": "ACTUAL_VERIFICATION_TIMESTAMP",
  "deployment_id": "ACTUAL_DEPLOYMENT_ID",
  "environment_revision": "ACTUAL_ENVIRONMENT_REVISION"
}
```

The attestation must match the operation and be at most one hour old, with at most 30 seconds of future clock skew. CI checks its bytes and freshness before and after the transaction. This is an explicit reviewed root attestation: **the runner does not independently access the private Site**. No private Site access credential is copied into Actions. Keep maintenance enabled until root verifies the compatible website, runtime and resulting forward/storage contract.

## Execution and receipts

```sh
node scripts/neon-forward-migrations.mjs production .github/operations/neon-forward-production.json
node scripts/neon-forward-migrations.mjs verify-only .github/operations/neon-forward-production.json
```

These commands require the authorized GitHub Actions context and the existing project-scoped `NEON_API_KEY`, `NEON_PROJECT_ID` and Actions `GITHUB_TOKEN`. Owner URLs are obtained only in memory and never printed or written. The workflow does not retrieve, rotate or export the existing application password. Effective role permissions are verified by the owner; restricted-login authentication remains part of the original copy/runtime checks.

`data/validation/neon-forward-migrations/receipt.json` is a sanitized 0600 atomic file uploaded as `neon-forward-MODE-RUN_ID-RUN_ATTEMPT`. It reports the baseline authentication, root maintenance attestation, original per-table byte hashes/counts, migration hashes, role permissions, sequence preservation, cleanup and any safe failure/commit status. It is evidence only after the actual run finishes successfully. Never describe local tests as a live migration receipt.

The SQL transaction acquires advisory lock `807245315,1`, rechecks every original row and ingestion sequence position, installs new DDL, adds only reviewed grants, and checks the original source bytes, guards and core function definitions again. All DDL and grants roll back together on failure. Unknown commit outcomes require explicit read-only verification rather than guessing or dropping existing tables.

## Owner migration registry and permissions

`public.worldatlas_schema_migrations` is administrative metadata outside the atlas fact tables. Its exact columns are:

```text
migration_id, file_sha256, core_schema_sha256,
source_snapshot_fingerprint, base_guards_sha256,
installed_contract_sha256, applied_at
```

The registry is owner-only and rejects update, delete and truncate. The installed contract digest covers new table columns, constraints/deferred foreign keys, enabled user guards and their SQL functions. An existing identical deployment is a verified no-op. Changed file hashes, unregistered table collisions, weakened guards or changed installed contracts are rejected; the tool does not silently repair them.

The runtime receives SELECT/INSERT on the four dated membership/existence tables. For footprints it receives SELECT only on `atlas_footprint_versions` and `atlas_footprint_version_objects`, and SELECT/INSERT on the three selection/withdrawal tables. Publication fields remain owner-only. No new sequence, explicit ingestion rowid, mutation of original facts, registry access, guard bypass, schema creation or role membership is granted. The original narrow geographic-release publication permissions remain as reviewed in the frozen foundation.

Storage v1 still describes the original fourteen tables. Storage v2 describes the eighteen/23 atlas fact tables and their source/target migration and catalog proofs; the administrative registry must be preserved separately in owner-maintenance receipts/backups, without granting public/runtime access. After content growth, use the explicit current-source preservation pin below rather than replacing the immutable historical baseline or copying its old facts back.

## Current compact-source continuation

The same operation may include this additional pin, with **all three** existing migrations in their original order:

```json
"current_source": {
  "inventory_file": "data/validation/current-recovery/source-inventory.json",
  "inventory_sha256": "ACTUAL_CURRENT_INVENTORY_SHA256",
  "receipt_file": "data/validation/current-recovery/receipt.json",
  "receipt_sha256": "ACTUAL_SUCCESSFUL_NATIVE_RECOVERY_RECEIPT_SHA256"
}
```

Use the existing current PostgreSQL recovery operation's successful native backup/isolated-restore receipt and complete owner inventory. Its read-only source marker must be exact compact-only V4 over frozen base2 or base3. The receipt pins the same collections, owner registry, compact physical rows and dictionary sequences; its encrypted-backup and isolated-restore readback must have succeeded. These are reviewed operation inputs, not self-generated assertions of live readiness. No operation file or fresh maintenance receipt is supplied by this implementation.

For a current capture followed immediately by the reviewed forward operation, the same operation may instead set `"current_source": "capture-current-native"`. Supply `window_comment_id` to the existing forward workflow. It invokes the existing native recovery function in that same owner job, under its genuine forward-workflow identity and the shared maintenance concurrency group. The fresh publisher window must additionally pin `forward_operation_sha256` to the complete committed operation-file bytes. An old read-only-only window cannot authorize this caller. All existing actor, exact main/tool/source, reservation, hosting/drain, recipient and expiry checks remain, and the exact window is reread before and after forward SQL.

The successful native capture must belong to the same head, run, attempt and window. The executor reads its actual private inventory and sanitized receipt from local runner files, computes their whole-byte pins in memory, and passes them through the unchanged current-source validator. It does not publish an inventory to Git or transfer it through an artifact. Only encrypted backup bytes, the recipient envelope and sanitized recovery receipts from `data/validation/current-postgres-recovery/public-receipts/` are uploaded alongside the sanitized forward receipt. Plaintext dump and inventories remain private. Explicit pre-existing `current_source` pins remain supported unchanged.

This integration does not produce its own maintenance approval. The existing fresh hash-pinned root maintenance attestation still must match the captured current marker and pass before and after SQL. Capture/restore or authorization failure stops before the owner installer; a post-commit check failure must be reconciled, never treated as permission to repeat unknown writes. Repository acceptance is not permission for the live backup, grants or migration.

Keep the original top-level checkpoint/source fields and authenticated baseline receipt unchanged as historical provenance. The old registry rows retain their original fingerprint, guards and application timestamps. The fresh maintenance attestation instead binds the current recovery marker's revision/fingerprint. A current-source continuation does not unpack or compare live facts to the old revision-1321 snapshot, restore any old row, or reopen the retired baseline copy executor.

Inside the existing owner lock and atomic transaction, the installer reads the actual current compact inventory and compares it with the reviewed pin. It applies only the missing canonical V3 DDL and necessary typed-table grants. The only accepted delta is three empty typed tables, their known catalog/functions/permissions, and one new immutable migration row. Every inherited logical collection, original registry row, compact physical row, dictionary key/sequence, ingestion sequence, database/default ACL and inherited function/table/sequence permission remains exact. Unknown profiles, data drift, modified registry rows, extra access and unreviewed DDL refuse and roll back. Repeating the same operation after a successful commit verifies a no-op; a new base3 recovery pin can independently verify the resulting state.

Issue #2696's historical settlement import requires the explicitly scoped owner operation below. Accepting this repository support neither authorizes nor performs a production migration, import, publisher contact or deployment. The standing #907 publication hold remains. Before requesting an owner window, prepare the exact reviewed current recovery/maintenance pins, unchanged historical proof, migration hashes, narrow grant delta, rehearsal/readback results and the separately scoped import/parity package. A stale or missing current pin is a real blocker, not permission to reset production or invent a new baseline.

## Local validation

Focused tests use actual PostgreSQL/PGlite SQL to exercise all three forward migrations, complete original-byte and sequence preservation, idempotent retries, atomic rollback, restricted runtime permissions, immutable registry, catalog tampering rejection and no-network skipped operations. They also exercise private maintenance attestation boundaries and the actual Bash operation selector. No production or disposable Neon call is made by those tests.

The grown-state tests execute the real installer and recovery inventory against an isolated compact PostgreSQL database with additional source/entity/release rows. They cover exact preservation, idempotence, base3 inventory, transactional rollback and adverse fingerprints/private ACLs/physical evidence/sequences/registry rows. They do not claim a native `pg_dump` rehearsal, provider branch execution, HTTP deployment or production import.

The same-job test uses an in-process native-capture/provider fixture but executes the actual forward service and PostgreSQL SQL twice, including a fresh base3 verification. It checks preserved rows/registry/ACLs, no archive request, genuine workflow identity, exact operation/window binding, changed-window refusal and private upload boundaries. It is not a native Docker dump/restore or production execution receipt.


## Exact historical settlement service import

A reviewed current-native operation may additionally declare `settlement_import`
with exactly `input_sha256` and `manifest_sha256`. The first must bind the unchanged
`data/settlement-estimates.json` source; the second pins the deterministic bundle
from the accepted compiler. For the final lossless metadata contract this bundle
is `da0a886f662ff9c80343ee92c347c50ce16718fd216add3f3d9669e6a62a1c80`.
The earlier pre-final bundle omitted `language`/`name_role` metadata and must not
be substituted. The whole-operation publisher window covers this declaration.
All three migrations and a fresh current native capture are required. An ordinary
forward operation without the declaration imports nothing, and verify-only never
invokes a database import even when the declaration is present.

After V3 verification, the same owner job invokes `importResearchBundle` through
`createPostgresDatabase` and the unchanged `importBatch`/`importTypedBatch` services.
The 48 exact ingestion IDs, source/subject/registry/date checks, immutable guards,
receipt validation and ingestion advisory lock remain authoritative. Transactions
honor the service's ReadCommitted boundary; no private HTTP endpoint, fake bearer
token, application credential, role impersonation or membership is introduced.
The public Cloudflare Worker remains read-only. This is owner maintenance, not
proof of a public API write or a website deployment.

The runner verifies all 582 retained settlement identities before importing and
runs the existing two-way 9,301-row field/source/contract parity query afterward.
It retains only sanitized batch receipts under the existing forward artifact.
Derived payloads are prepared from the immutable Git source in temporary private
files, not uploaded alongside receipts. Every resume checks the original IDs
against actual server receipts, including those already present in a local ledger.
A lost response after commit therefore resolves to the same fingerprint and does
not authorize a new ID. The schema transaction and each import batch commit
separately: a later error does not roll back earlier successful batches. Reconcile
actual receipts and obtain the applicable fresh owner operation/window before
continuing; do not replay a stale migration or clear existing data.

Local proof executes the actual services and PostgreSQL transactions on grown
compact state, including a committed-but-lost-response interruption, complete
idempotent replay, unchanged non-campaign inventories/ACLs, exact parity, and
verify-only with zero import calls. Provider/native Docker behavior remains the
separately disclosed fixture, not a production rehearsal. The future production
backup, narrow V3 grants and exact import still need their applicable action-time
authorization; this code does not lift the #907 hold.


## Ordered geographic publication, without schema or settlement work

Issue #2701 uses the same private owner workflow with `geography-verify` and
`geography-production`, selecting `.github/operations/neon-geographic-production.json`.
The closed operation pins the existing production project/branch, v10 compressed
manifest and original index, plus the exact retained v8 membership image. Four
ordered v7–v10 plans reuse the existing complete admission, stage and finalize
services. Each phase stays within the unchanged 512-descriptor bound. There is no
archive-upload tail, public write endpoint, DDL, grant, role membership, backup
or settlement operation. The cancelled settlement import remains cancelled.

`geography-verify` validates every complete input, including restored v8 bytes,
before returning with no database calls. Production requires a fresh existing
`worldatlas-production` / `worldatlas-publication` GitHub deployment record with
`kind: geography`, the exact accepted `primary_commit`, issue #2701, the complete
operation-file SHA-256, the existing origin, and `read_only: true`. Its creator
must match the workflow actor; its operation window is at most two hours. Pass
that existing record's ID as `publication_deployment_id`. Complete publication
registry reconciliation must show it as the sole unsettled operation. The same
window is reauthenticated between releases, and expiry checked before each write.
This uses the existing owner-maintenance concurrency and server-side Neon binding,
not the historical fourteen-table copy baseline or the cancelled import window.

The `geography-production` job has a 120-minute execution budget, covering
checkout, all four ordered releases, verification, the public build and receipt
retention. The former 30-minute whole-job limit interrupted healthy publication
before all releases finished. Other modes retain their 30-minute limit. This
budget matches the maximum publication-window duration; it does not renew that
window or permit writes after its actual expiry. A timed-out or expired operation
still requires durable-state reconciliation and a fresh exact-head window before
resuming the original immutable ingestion IDs. Stuck jobs remain bounded.

The exact published v6 predecessor and all later existing release pins must match.
The same immutable ingestion IDs and service transactions preserve prior entities,
prior release memberships, unrelated content and access. Cát Hải's new parent is
release-scoped membership, not an overwrite of `atlas_entities`. A failed or lost
response requires reconciliation of those original IDs and release states before
continuation; previous committed batches are not undone or replaced. Only the
sanitized receipt is uploaded. Settle the same publication record with separate
per-issue results and `delivery: null`; geographic publication cannot claim a
website deployment. Publish the separately tested read-only website only after
its exact requested content release is verified published.

Issue discovery is reporting, not artifact or database compatibility. References
to earlier PRs stay PR provenance, not invented original issues or a deployment
blocker. Exact head/release pins and genuine unsettled-operation serialization
remain authoritative.


### Coordinated public map publication

The publication operation selects one accepted source and its exact M content
release. The public Worker compatibility deployment must precede any release
finalization: the two legacy map snapshot routes keep omitted `release_id` at
the retained published v6, while explicit new clients keep their own M and
separate generic release endpoints keep their existing semantics. Empty or
unknown explicit IDs do not fall back. This protects cached/open old pages and
asset rollback after later releases are published.

Compile only that same Worker entry with `node scripts/build-cloudflare.mjs
--legacy-worker`. Its existing Wrangler metadata uses `keep_assets` and retained
binding types; it does not copy credentials, upload a replacement asset set, or
change the public write policy. Before the normal serialized Worker deployment,
verify the actual provider's non-secret binding inventory against the retained
configuration. Stop on an unexpected binding rather than discard it. The explicit
geography publication window binds the old asset inventory and new Worker
separately and settles with `delivery:null`; it is not a staging/recovery action
or a new full website delivery. After synchronization, the existing Cloudflare
publication record binds and publishes the complete new package.

Once this compatibility deployment is verified, `geography-production` performs
the exact bounded append through the existing private services and immutable
batch receipts. It then uses the existing public builder's `--publication`
boundary: authenticate the source-bound successful operation, derive M from the
accepted selected products, and verify the published exact M and old-client
compatibility before the expensive build. A mismatch stops, never selects
latest or starts an unrelated synchronization. No future write authorization is
inferred from the current v7–v10 operation/window.

The owner workflow retains the completed public package with its exact source,
operation, M, configuration, original build receipt, and complete output hashes.
A retry looks for that same workflow/source/operation artifact and verifies all
bytes before reuse, without claiming another build. A damaged or incompatible
retained package refuses rather than silently rebuilding. Only the public
package and sanitized receipts are uploaded, never SQLite or private database
inventories. The existing publisher deploys that exact package under the normal
serialized publication operation and verifies served assets plus explicit M;
the prior live pair remains usable throughout. A failed deploy resumes from the
retained package instead of rebuilding or issuing new ingestion IDs.

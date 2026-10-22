# Reviewed PostgreSQL forward deployment

The frozen fourteen-table copy and its original evidence must be verified first. `scripts/neon-forward-migrations.mjs` then applies reviewed PostgreSQL forward migrations without importing historical facts, rotating credentials, changing Site audience or moving media.

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

Issue #2696's historical settlement import is a **separate later owner operation**. Accepting this repository support neither authorizes nor performs a production migration, import, publisher contact or deployment. The standing #907 publication hold remains. Before requesting an owner window, prepare the exact reviewed current recovery/maintenance pins, unchanged historical proof, migration hashes, narrow grant delta, rehearsal/readback results and the separately scoped import/parity package. A stale or missing current pin is a real blocker, not permission to reset production or invent a new baseline.

## Local validation

Focused tests use actual PostgreSQL/PGlite SQL to exercise all three forward migrations, complete original-byte and sequence preservation, idempotent retries, atomic rollback, restricted runtime permissions, immutable registry, catalog tampering rejection and no-network skipped operations. They also exercise private maintenance attestation boundaries and the actual Bash operation selector. No production or disposable Neon call is made by those tests.

The grown-state tests execute the real installer and recovery inventory against an isolated compact PostgreSQL database with additional source/entity/release rows. They cover exact preservation, idempotence, base3 inventory, transactional rollback and adverse fingerprints/private ACLs/physical evidence/sequences/registry rows. They do not claim a native `pg_dump` rehearsal, provider branch execution, HTTP deployment or production import.

The same-job test uses an in-process native-capture/provider fixture but executes the actual forward service and PostgreSQL SQL twice, including a fresh base3 verification. It checks preserved rows/registry/ACLs, no archive request, genuine workflow identity, exact operation/window binding, changed-window refusal and private upload boundaries. It is not a native Docker dump/restore or production execution receipt.

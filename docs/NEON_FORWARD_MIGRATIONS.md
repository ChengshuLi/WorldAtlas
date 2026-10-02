# Reviewed PostgreSQL forward deployment

The frozen fourteen-table copy and its original evidence must be verified first. `scripts/neon-forward-migrations.mjs` then applies reviewed PostgreSQL forward migrations without importing historical facts, rotating credentials, changing Site audience or moving media.

The workflow is `.github/workflows/neon-forward-migrations.yml`. A root-maintainer commit changing `.github/operations/neon-forward-production.json` explicitly activates production on `work`; other pushes only use the separate optional rehearsal operation and skip when it is absent. Manual dispatch also supports production, verify-only and rehearsal. The selector uses Bash builtins, not ripgrep. The repository and branch are checked in the script. The workflow shares the owner-maintenance concurrency group with the original copy workflow.

Root owns the concrete operation and its publication. Do not substitute a successful rehearsal receipt for the production baseline. The original production run must be completed and successful; its authenticated artifact and receipt bytes must match the reviewed hashes, source identity, original full-byte copy and readback. No forward operation is automatically created by this tool.

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

All placeholder values fail validation. Migration IDs, file paths, order and byte hashes are pinned. The template supports the first migration alone, or both in order. Source checkpoint parts are unpacked and independently verified before SQL.

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

The attestation must match the operation and be at most one hour old, with at most 30 seconds of future clock skew. CI checks its bytes and freshness before and after the transaction. This is an explicit reviewed root attestation: **the runner does not independently access the private Site**. No private Site access credential is copied into Actions. Keep maintenance enabled until root verifies the compatible website, runtime, forward schema and storage v2.

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

Storage v1 still describes the original fourteen tables. Storage v2 describes the eighteen/23 atlas fact tables and their source/target migration and catalog proofs; the administrative registry must be preserved separately in owner-maintenance receipts/backups, without granting public/runtime access. This tool targets the initial frozen baseline; later migrations after content growth need a newly reviewed current snapshot and technical-maintainer operation.

## Local validation

Focused tests use actual PostgreSQL 18.3/PGlite to exercise both forward migrations, complete original-byte and sequence preservation, idempotent retries, atomic rollback, restricted runtime permissions, immutable registry, catalog tampering rejection and no-network skipped operations. They also exercise private maintenance attestation boundaries and the actual Bash operation selector. No production or disposable Neon call is made by those tests.

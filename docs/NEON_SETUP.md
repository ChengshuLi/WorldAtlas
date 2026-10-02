# Neon production storage and pending forward release

The user created PostgreSQL project `weathered-lab-37571695`, production branch shown as `br-summer-butterfly-ar8qikk5`, with requested database name `worldatlas` and PostgreSQL 18. Read-only GitHub Actions run 36964473361 authenticated successfully and verified PostgreSQL 18, production/default branch `br-summer-butterfly-ar8qikk5`, database **`neondb`**, and role `neondb_owner`. The user retained the default database name; it is valid and need not be renamed. This management check does not establish SQL schema state or free-plan storage limits. Receipt: `data/validation/neon-project-verification.json`.

## Workspace setup completed

- Global Neon CLI 7.0.6 installed from the official `neon` package.
- `neon skills -y --agent codex` installed the official agent guidance under `.agents/skills`, with `skills-lock.json`.
- Project-level OAuth MCP setup in `.codex/config.toml` pins `https://mcp.neon.tech/mcp?projectId=weathered-lab-37571695`. It contains no credential; the client needs its own OAuth authorization. Installation does not prove callable/authenticated MCP access in the current session.
- `neon config init --services none` installed `@neon/config` and `@neon/env`. The generated policy was replaced with the user's requested bare `defineConfig({})` in `neon.ts`, with no Auth, Functions, buckets or branch-expiry policy.
- Local `.env` files are Git-ignored before any credential pull.

The CLI's attempted browser login timed out. Its redirect targets localhost on this remote workspace, so it cannot be treated as a completed login on the user's desktop. Current cloud readiness reports no secret bindings/outbound identity. The user connected this project to `ChengshuLi/WorldAtlas`; GitHub Actions secret `NEON_API_KEY` and repository variable `NEON_PROJECT_ID` are verified by the read-only workflow. This provides authentication inside Actions, not in the workspace or the Site. No additional key is needed for those workflows. Workspace CLI access, if needed, still requires a secure cloud secret or authenticated MCP/CLI session. Never paste connection strings or keys into chat, tracked files, command arguments or receipts.

## Optional maintainer CLI access

Inspect actual current credential readiness; do not print secret values. Verify the project/production branch and database metadata, then link:

```sh
neon link --project-id weathered-lab-37571695 --branch production -y
neon config plan
neon deploy
```

Review the concrete policy diff before applying it. The empty policy must not unexpectedly remove existing services. `neon deploy` applies Neon service policy; it does not migrate the WorldAtlas SQLite schema or move its frontend. Preserve Sites authentication/frontend hosting and existing R2 archives. Check the database name/version/plan and retain nonsecret setup receipts.

Link/apply may pull connection variables into ignored `.env`/`.env.local`; inspect existing configuration before pulling and preserve unrelated values. Use the direct connection for migrations/dumps and pooled connection for normal application queries where appropriate. Server secrets must stay outside browser assets and Git. `.neon` local context is not a portable credential; this document and stable project ID are the restoration instructions.

## Verified production storage and pending forward release

The PostgreSQL schema/backend adapter, explicit backend selection, original fourteen-table raw export and byte-preserving owner restoration are implemented and tested. Actual Neon checks verify the restricted application role and independent publication/import locking. A full original-storage restore rehearsal also passed on a disposable branch; its receipt is `data/validation/neon-full-storage-rehearsal.json`. These are executed provider checks rather than a design-only plan.

The original D1 revision-1321 checkpoint preserves 3,984 completed names/religion claims, 381 sources and 28 media manifests. Corrected production Actions run [36973747147](https://github.com/ChengshuLi/WorldAtlas/actions/runs/36973747147), baseline `17747fe`, verified all fourteen original collections on the production target, including restricted application-role read-back. The actual database measured 318,275,584 bytes. Receipt: [neon-production-storage-migration.json](../data/validation/neon-production-storage-migration.json). The earlier selector-affected run 36973245038 was a rehearsal, rather than the production proof.

Site 17 was redeployed with `ATLAS_CONTENT_BACKEND=postgres`, a server-only `DATABASE_URL`, a reviewed 512 MiB operational budget and `ATLAS_READ_ONLY=1`. Deployment `appgdep_6abf516837648191aa6fe214ff06b563` succeeded at 2026-10-02 06:38:42.762 UTC. Live private-API checks retained all 3,984 claims, 28 R2 archives and 16,199,861 archive bytes at revision 1321; [neon-production-site-preservation.json](../data/validation/neon-production-site-preservation.json) records the result. The operational budget is not the provider quota.

Writes remain paused while forward DDL run [36974831053](https://github.com/ChengshuLi/WorldAtlas/actions/runs/36974831053), source `d0cc015`, applies migrations 0001/0002 and the matching Site 18/version-two publication is validated. Engineering source `937fa8e` passed all 394 final tests with zero skips and three real browser checks; those results are not production publication receipts. Technical maintainers own the remaining forward DDL/grants, new-release live verification, write enablement, browser footprint/version-cache integration and installation of three validated hierarchy candidates. The footprint scaffold is implemented; the validated browser capability remains zero. `neon.ts` alone performs none of these steps. Read `docs/HANDOFF_ENGINEERING_CHECKPOINT.md` and `docs/LONG_TERM_STORAGE_PLAN.md`.

Luna prepares supported datasets and uses the unchanged research workflow once published writes are available. No coding, secret binding, provider setup, migrations, publication or grid/cache work is assigned to Luna. Final handoff readiness remains unverified until the new release is validated and writes are enabled; the original production-storage and private-API receipts are already verified.

## Runtime cutover controls

`ATLAS_CONTENT_BACKEND` defaults to `d1`. Explicit `postgres` selection requires the server-only `DATABASE_URL`; invalid/missing configuration fails rather than falling back to the old database. D1 remains bound for preservation/rollback, and R2 object identities remain unchanged. Credentials must not be put in browser assets, Git, chat or verification receipts.

`ATLAS_READ_ONLY=1` rejects every API mutation before accessing the database or bucket. It is required across an authoritative `/api/storage/export-marker` plus all fourteen `/api/storage/export/{collection}` reads. The export CLI checks a stable revision, counters, release hashes, raw JSON bytes and durable part hashes; independent collections can run concurrently, while each cursor remains sequential. The export platform shipped in Site 16, and Site 17 repaired the managed D1 compound-SELECT marker limit. The complete authoritative original snapshot is now retained in Git at `data/storage-checkpoints/d1-revision-1321`; do not rewrite that frozen fourteen-table checkpoint when adding forward tables.

The owner-only PostgreSQL restore accepts an empty target and an explicitly verified snapshot. It retains original row IDs, disables/re-enables only USER guards inside a SERIALIZABLE transaction, preserves base CHECK/FK constraints, compares every raw table, and transactionally restarts the revision sequence. The application credential must not own the schema or be able to disable guards. Keep the original database/archive backups and prove read-back/restore before any cutover.

## Actual Neon SQL and restricted-role verification — 2026-10-02 UTC

Actions run [36967823740](https://github.com/ChengshuLi/WorldAtlas/actions/runs/36967823740) verified the committed PostgreSQL schema and hosted service against a newly created Neon branch. It authenticated as `worldatlas_app`, checked all fourteen tables and effective grants, exercised immutable original/replacement evidence and identical import retries, and denied thirteen prohibited schema/evidence/sequence/role operations. Both owner and application connections closed; the disposable branch was deleted. Production received no SQL writes. The sanitized receipt is `data/validation/neon-runtime-role-verification.json`; it records the exact schema/runtime-role hashes and source commit.

The restricted application role is provisioned by `scripts/provision-postgres-runtime-role.mjs`, separately from `postgres/schema.sql`. The application has table reads and bounded approved inserts; ingestion IDs are generated rather than explicitly supplied, and publication updates are limited to permitted columns. It has no table ownership, role memberships, schema creation, guard bypass or revision-sequence reset privilege. An existing unreviewed privileged role is rejected. Password provisioning/explicit rotation uses secret environment input and does not print credentials.

The matching prepared/static release suite passed **257/257, zero skips**. This earlier milestone established tested implementation and a small provider rehearsal. The subsequent full disposable-branch rehearsal, actual production copy, restricted private Site binding and original-data preservation are verified. Forward migrations and the new-release/write-availability checks remain pending as described above. Original D1/R2 evidence remains retained.

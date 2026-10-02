# Engineering checkpoint before Luna research

Future engineering threads receive [ENGINEERING_HANDOFF.md](ENGINEERING_HANDOFF.md) and its [prompt](prompts/ENGINEERING.txt). Content-only Luna threads receive [HISTORY_HANDOFF.md](HISTORY_HANDOFF.md) and its [prompt](prompts/LUNA_HISTORY.txt). These are authoritative dated trackers; the `_TODO.md` guides supply details.

**Recorded 2026-10-02 UTC. Research/import platform ready; wider atlas work remains open.** The repository is `https://github.com/ChengshuLi/WorldAtlas`, branch `work`. Deployed engineering source is `cf8769a039267407fdaab1d3bf0d8ad6ef8cef42`; subsequent handoff-only commits contain documentation and verification receipts. The functional suite passed 394/394 with zero skips; five packaging checks and three focused browser checks passed. Owner-private **Site 18 is deployed with Neon PostgreSQL, retained R2 archives and imports enabled** (environment revision 3; deployment `appgdep_6abf573be0948191a5517d0b2cbe7948`, succeeded 2026-10-02 07:03:34.504 UTC). Production migration run 36973747147 and forward migration run 36974831053 are verified. Live checks cover all 23 factual tables and seven dates from 3000 BC to 2026 AD; capabilities are `mapSnapshots:1`, `datedGeography:1`, `datedFootprints:0`, `storageExport:2`. Original read-back preserved all 3,984 historical claims and 28 archives (16,199,861 bytes), at ingestion revision 1321. See `data/validation/neon-final-publication.json` and `neon-final-api-writable.json` for the exact release and checks. The existing content-research/import platform is ready for Luna. This does **not** complete every atlas goal: dated-footprint browser/cache integration, installation of three validated hierarchy candidates, blocked geographic repairs, worldwide semantic approval and physical mobile validation remain technical-maintainer work. Luna researches sources, prepares supported sparse evidence, imports it and logs results; Luna does not change code, geography, infrastructure or deployments.

Luna's scope is **source research, factual evidence files, supported sparse imports, verification and durable research notes**. Coding, schema changes, provider configuration, deployments, geographic installation, grid/performance work and UI changes remain technical-maintainer responsibilities. Do not use this document to authorize a schema migration or production restore from a research thread.

## Preserved foundation and production state

- Owner-private **Site 18 uses production Neon PostgreSQL**, with restricted server-only credentials and retained R2 archives. Deployment `appgdep_6abf573be0948191a5517d0b2cbe7948` succeeded at 2026-10-02 07:03:34.504 UTC. Imports are enabled. Replaying all 22 existing prepared batches preserved revision 1321 and the complete snapshot fingerprint; no new claims were added.
- The durable original-storage checkpoint is [data/storage-checkpoints/d1-revision-1321/checkpoint.json](../data/storage-checkpoints/d1-revision-1321/checkpoint.json), with its 25 tracked compressed parts. Its [verification receipt](../data/validation/storage-checkpoint-revision-1321.json) records **revision 1321**, 381 sources, 3,588 names, 396 attribute records and 28 media objects. Revision 1321 is the original ingestion revision, not a source count. The **3,984 completed historical claims** and original source/claim metadata remain preserved. Media bytes remain in R2 plus licensed tracked archives; the raw database checkpoint contains media metadata rather than blob bytes.
- That checkpoint contains fourteen original collections, 206,548,113 raw bytes and 9,245,712 compressed bytes. Its source manifest SHA-256 is `b59946f515e385d8c7c8de84a529e851fc802262f07e39cb080f5f493f3572e2`; its source snapshot fingerprint is `c315f806f9b7a60cbb7196ce5f8be38cd16c385b00f883f5275ec8f5bc9202ef`. Do not regenerate it using the new schema.
- Corrected production run [36973747147](https://github.com/ChengshuLi/WorldAtlas/actions/runs/36973747147), source `17747fe`, verified all fourteen raw collections on the actual production target and restricted-role read-back (318,275,584 database bytes): [production migration receipt](../data/validation/neon-production-storage-migration.json). [Live private-API preservation](../data/validation/neon-production-site-preservation.json) verified all 3,984 claims and 28 archives (16,199,861 bytes) at revision 1321. Earlier run 36973245038 was a rehearsal, and is not used as the production proof.
- Forward DDL run [36974831053](https://github.com/ChengshuLi/WorldAtlas/actions/runs/36974831053), source `d0cc015`, verified both migrations, original byte preservation and restricted-role grants. Site 18 exposes all 23 factual tables through version-two exports and live dated-geography readers; seven timeline dates passed API checks. See `neon-production-forward-migrations.json`, `neon-final-api-writable.json` and `neon-final-import-replay.json` in `data/validation`.
- Existing prepared ownership, environmental observations, 9,301 settlement estimates, predecessor geometry/history and paused GHSL work remain retained under the paths in [IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md) and [REPRODUCIBLE_CHECKPOINT.md](REPRODUCIBLE_CHECKPOINT.md). Do not import the incomplete GHSL output or transfer estimates into location population totals.

## Verified platform and remaining maintainer work

| Component | Evidence at this checkpoint | Maintainer completion still required |
| --- | --- | --- |
| Per-transaction geographic pins | Actual two-session Neon proof confirms locking, fresh reads, stale-pin rollback and original pinned replay. Matching code is published in Site 18; all 22 retained batches replayed without snapshot changes. | Retain exact geographic pins and bounded import receipts for future campaigns. |
| Dated parent membership and identity existence | Actual SQL, compiler/bridge, shared resolver and bounded loader tests passed. Production DDL, grants and Site 18 routes/client are published; seven-date live API checks passed. | Luna can import supported evidence under [the contract](HOSTED_TEMPORAL_GEOGRAPHY.md) and [safe campaign phases](TEMPORAL_GEOGRAPHY_CAMPAIGNS.md). Research must not directly edit reference parents. |
| Forward export/restore | Version-two export/restore is tested independently of the frozen original contract. All 23 production factual-table export routes and catalog pins passed live checks. | Future backups use v2 for all factual tables, plus separate owner-only migration-registry and object-storage backups. Preserve the frozen original checkpoint. |
| Dated footprints and client caches | Versioned footprint scaffold is implemented. Current validated temporal bridge advertises `datedFootprints: 0`. | Finish browser version selection/cache and renderer integration against reviewed immutable manifests. No content import may pretend unsupported footprint selection is active. |
| Hierarchy corrections | Three sourced candidates are validated but not installed. | Complete maintainer-owned atomic release installation and matching publication with original/new ID accounting and evidence preserved. Staged proposals do not establish active geography. |
| Backend/provider binding | Actual production restore/read-back, restricted server-secret binding, forward migrations, live API preservation and enabled imports are verified. | Monitor measured storage/compute/query capacity and backups. No silent D1 fallback or uncontrolled dual writes. |

Worldwide local semantic approval, missing-source land/island questions and physical mobile performance remain separate open work; structural completeness or a database transfer cannot close them. Historical content expansion remains intentionally paused in the engineering thread.

## Fresh-thread startup and research commands

Start from Git, read the latest receipts, and use the current approved release rather than a remembered label or URL response:

```sh
git clone --branch work https://github.com/ChengshuLi/WorldAtlas.git
cd WorldAtlas
git rev-parse HEAD
npm ci
```

Read `AGENTS.md`, this checkpoint, `docs/HANDOFF_STATUS.md`, `docs/LUNA_DATA_HANDOFF.md` and `docs/RESEARCH_IMPORT_WORKFLOW.md`. Obtain `/api/geography/release` through documented private Site access and save the exact response as `geographic-release.json`. Imports are enabled; recheck the live release, revision, capabilities and capacity before a campaign. Capacity or maintenance conflicts require retaining receipts and reporting the blocker.

```sh
node scripts/prepare-research-bundle.mjs research.json geographic-release.json research-bundles/campaign-001
node scripts/import-research-bundle.mjs https://worldatlas-explorer.chengshu-li-2013.chatgpt.site/ research-bundles/campaign-001 --dry-run
```

Once the latest production receipt confirms writes are available, the existing importer uses a hidden credential prompt:

```sh
node --use-env-proxy scripts/import-research-bundle.mjs https://worldatlas-explorer.chengshu-li-2013.chatgpt.site/ research-bundles/campaign-001
```

Keep sparse half-open intervals, stable IDs, fixed environmental classifications and traceable provenance. Unknown years need no fabricated rows. Commit and push original inputs, bundles, lawful source bytes/restoration manifests, receipts, read-back and open findings on the appropriate isolated lane branch; PRs integrate into **work** serially. Never commit credentials, `.cache`, local databases or provider connection URLs. Dated-geography campaigns must check the live capability and follow safe transaction phases in the campaign guide; dated footprints remain unsupported by the browser.

For an optional **local-only**, credential-free inspection of the retained original storage checkpoint:

```sh
node scripts/storage-checkpoint.mjs unpack data/storage-checkpoints/d1-revision-1321 /tmp/worldatlas-d1-revision-1321
node scripts/restore-postgres-storage.mjs /tmp/worldatlas-d1-revision-1321 --dry-run
```

These commands verify/unpack durable Git bytes; they do not provision a database, migrate production or move R2 blobs. No prior workspace or cache is required.

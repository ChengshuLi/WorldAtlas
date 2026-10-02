# Engineering checkpoint before Luna research

**Recorded 2026-10-02 UTC. Production PostgreSQL storage and private Site binding are verified; the forward release and write enablement remain pending.** The primary repository is `https://github.com/ChengshuLi/WorldAtlas`, branch `work`; the current engineering source checkpoint is `937fa8e`, with 394/394 final tests (zero skips) and three real browser checks passed. The footprint scaffold is implemented, while browser/version-cache integration and installation of three validated hierarchy candidates remain maintainer work. A pushed source checkpoint is not a matching production deployment. The technical maintainer must update [HANDOFF_STATUS.md](HANDOFF_STATUS.md) with the final pushed SHA, actual migration/deployment receipts and remaining blockers before declaring readiness.

Luna's scope is **source research, factual evidence files, supported sparse imports, verification and durable research notes**. Coding, schema changes, provider configuration, deployments, geographic installation, grid/performance work and UI changes remain technical-maintainer responsibilities. Do not use this document to authorize a schema migration or production restore from a research thread.

## Preserved foundation and production state

- Owner-private **Site 17 now uses production Neon PostgreSQL** through explicit backend selection and its restricted server-only secret, with R2 archives retained. Deployment `appgdep_6abf516837648191aa6fe214ff06b563` succeeded at 2026-10-02 06:38:42.762 UTC. Writes remain read-only while the forward release is validated.
- The durable original-storage checkpoint is [data/storage-checkpoints/d1-revision-1321/checkpoint.json](../data/storage-checkpoints/d1-revision-1321/checkpoint.json), with its 25 tracked compressed parts. Its [verification receipt](../data/validation/storage-checkpoint-revision-1321.json) records **revision 1321**, 381 sources, 3,588 names, 396 attribute records and 28 media objects. Revision 1321 is the original ingestion revision, not a source count. The **3,984 completed historical claims** and original source/claim metadata remain preserved. Media bytes remain in R2 plus licensed tracked archives; the raw database checkpoint contains media metadata rather than blob bytes.
- That checkpoint contains fourteen original collections, 206,548,113 raw bytes and 9,245,712 compressed bytes. Its source manifest SHA-256 is `b59946f515e385d8c7c8de84a529e851fc802262f07e39cb080f5f493f3572e2`; its source snapshot fingerprint is `c315f806f9b7a60cbb7196ce5f8be38cd16c385b00f883f5275ec8f5bc9202ef`. Do not regenerate it using the new schema.
- Corrected production run [36973747147](https://github.com/ChengshuLi/WorldAtlas/actions/runs/36973747147), source `17747fe`, verified all fourteen raw collections on the actual production target and restricted-role read-back (318,275,584 database bytes): [production migration receipt](../data/validation/neon-production-storage-migration.json). [Live private-API preservation](../data/validation/neon-production-site-preservation.json) verified all 3,984 claims and 28 archives (16,199,861 bytes) at revision 1321. Earlier run 36973245038 was a rehearsal, and is not used as the production proof.
- Forward DDL run [36974831053](https://github.com/ChengshuLi/WorldAtlas/actions/runs/36974831053), source `d0cc015`, and matching Site 18/version-two checks are pending. The final handoff is not ready until the new release is verified and writes are enabled.
- Existing prepared ownership, environmental observations, 9,301 settlement estimates, predecessor geometry/history and paused GHSL work remain retained under the paths in [IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md) and [REPRODUCIBLE_CHECKPOINT.md](REPRODUCIBLE_CHECKPOINT.md). Do not import the incomplete GHSL output or transfer estimates into location population totals.

## Tested engineering versus remaining publication work

| Component | Evidence at this checkpoint | Maintainer completion still required |
| --- | --- | --- |
| Per-transaction geographic pins | 72 affected/integration checks passed; [real two-session Neon proof](../data/validation/neon-geography-pin-verification.json) confirms publication locking, fresh reads, stale-pin rollback and original pinned replay. | Publish matching Worker/adapter/importer code and record the production receipt. Site 17 did not contain this follow-up. |
| Dated parent membership and identity existence | New SQL/service contracts and bounded winning/withdrawal pages pass actual SQLite/PostgreSQL tests. Compiler, browser bridge and shared resolver pass 33 focused checks; the integrated temporal/API suites pass 31 checks and the bounded loader 12 checks. Source intervals, immutable corrections, explicit unknowns and complete reference fallback remain distinct. | Apply forward DDL and restricted-role grants after the original fourteen-table transfer; publish the matching tested routes/client integration and verify the live private API. See [HOSTED_TEMPORAL_GEOGRAPHY.md](HOSTED_TEMPORAL_GEOGRAPHY.md) and [campaign sequencing](TEMPORAL_GEOGRAPHY_CAMPAIGNS.md). |
| Forward export/restore | Version-two export/restore is implemented and locally tested independently of the frozen original contract. | Complete forward DDL and matching version-two live publication checks. Preserve the original checkpoint and frozen restore path. |
| Dated footprints and client caches | Versioned footprint scaffold is implemented. Current validated temporal bridge advertises `datedFootprints: 0`. | Finish browser version selection/cache and renderer integration against reviewed immutable manifests. No content import may pretend unsupported footprint selection is active. |
| Hierarchy corrections | Three sourced candidates are validated but not installed. | Complete maintainer-owned atomic release installation and matching publication with original/new ID accounting and evidence preserved. Staged proposals do not establish active geography. |
| Backend/provider binding | Actual production restore/read-back, restricted server-secret binding and private API preservation are verified. | Keep writes paused until forward DDL and the matching new release pass live version-two/preservation checks, then record write enablement. No silent D1 fallback or uncontrolled dual writes. |

Worldwide local semantic approval, missing-source land/island questions and physical mobile performance remain separate open work; structural completeness or a database transfer cannot close them. Historical content expansion remains intentionally paused in the engineering thread.

## Fresh-thread startup and research commands

Start from Git, read the latest receipts, and use the current approved release rather than a remembered label or URL response:

```sh
git clone --branch work https://github.com/ChengshuLi/WorldAtlas.git
cd WorldAtlas
git rev-parse HEAD
npm ci
```

Read `AGENTS.md`, this checkpoint, `docs/HANDOFF_STATUS.md`, `docs/LUNA_DATA_HANDOFF.md` and `docs/RESEARCH_IMPORT_WORKFLOW.md`. Obtain `/api/geography/release` through the documented private Site access and save the exact response as `geographic-release.json`. Read-only research and evidence preparation can proceed while production writes are paused; capacity/maintenance conflicts require retaining receipts and reporting the blocker.

```sh
node scripts/prepare-research-bundle.mjs research.json geographic-release.json research-bundles/campaign-001
node scripts/import-research-bundle.mjs https://worldatlas-explorer.chengshu-li-2013.chatgpt.site/ research-bundles/campaign-001 --dry-run
```

Once the latest production receipt confirms writes are available, the existing importer uses a hidden credential prompt:

```sh
node --use-env-proxy scripts/import-research-bundle.mjs https://worldatlas-explorer.chengshu-li-2013.chatgpt.site/ research-bundles/campaign-001
```

Keep sparse half-open intervals, stable IDs, fixed environmental classifications and traceable provenance. Unknown years need no fabricated rows. Commit and push original research input, immutable generated bundles, lawful source bytes or restoration manifests, partial import receipts, read-back results and open findings. Never commit credentials, `.cache`, local databases or provider connection URLs. New dated-geography campaigns must wait for the matching published capability and follow the safe transaction phases in the campaign guide.

For an optional **local-only**, credential-free inspection of the retained original storage checkpoint:

```sh
node scripts/storage-checkpoint.mjs unpack data/storage-checkpoints/d1-revision-1321 /tmp/worldatlas-d1-revision-1321
node scripts/restore-postgres-storage.mjs /tmp/worldatlas-d1-revision-1321 --dry-run
```

These commands verify/unpack durable Git bytes; they do not provision a database, migrate production or move R2 blobs. No prior workspace or cache is required.

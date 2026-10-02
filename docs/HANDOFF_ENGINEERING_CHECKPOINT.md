# Engineering checkpoint before Luna research

**Recorded 2026-10-02 UTC. Engineering completion and production cutover are pending.** The primary repository is `https://github.com/ChengshuLi/WorldAtlas`, branch `work`; the inspected committed base is `f20adf08dc9ac05606ade20a669757889efd56bb`. Additional dated-geography, footprint, export and client changes are being integrated after that base. Their existence in a workspace is not a pushed or published checkpoint. The technical maintainer must update [HANDOFF_STATUS.md](HANDOFF_STATUS.md) with the final pushed SHA, actual migration/deployment receipts and remaining blockers before declaring readiness.

Luna's scope is **source research, factual evidence files, supported sparse imports, verification and durable research notes**. Coding, schema changes, provider configuration, deployments, geographic installation, grid/performance work and UI changes remain technical-maintainer responsibilities. Do not use this document to authorize a schema migration or production restore from a research thread.

## Preserved foundation and production state

- The last documented Site deployment is owner-private **version 17**, using D1/R2 with writes temporarily read-only for transfer. A newer commit or local passing test does not establish a deployed backend.
- The durable original-storage checkpoint is [data/storage-checkpoints/d1-revision-1321/checkpoint.json](../data/storage-checkpoints/d1-revision-1321/checkpoint.json), with its 25 tracked compressed parts. Its [verification receipt](../data/validation/storage-checkpoint-revision-1321.json) records **revision 1321**, 381 sources, 3,588 names, 396 attribute records and 28 media objects. Revision 1321 is the original ingestion revision, not a source count. The **3,984 completed historical claims** and original source/claim metadata remain preserved. Media bytes remain in R2 plus licensed tracked archives; the raw database checkpoint contains media metadata rather than blob bytes.
- That checkpoint contains fourteen original collections, 206,548,113 raw bytes and 9,245,712 compressed bytes. Its source manifest SHA-256 is `b59946f515e385d8c7c8de84a529e851fc802262f07e39cb080f5f493f3572e2`; its source snapshot fingerprint is `c315f806f9b7a60cbb7196ce5f8be38cd16c385b00f883f5275ec8f5bc9202ef`. Do not regenerate it using the new schema.
- [The full Neon rehearsal receipt](../data/validation/neon-full-storage-rehearsal.json) verifies the original checkpoint on a disposable branch, with restricted application-role read-back and branch cleanup. It is **not** a production cutover receipt. Production migration work dispatched from `f20adf0` is pending at this checkpoint; the maintainer must record its actual outcome before changing this status.
- Existing prepared ownership, environmental observations, 9,301 settlement estimates, predecessor geometry/history and paused GHSL work remain retained under the paths in [IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md) and [REPRODUCIBLE_CHECKPOINT.md](REPRODUCIBLE_CHECKPOINT.md). Do not import the incomplete GHSL output or transfer estimates into location population totals.

## Tested engineering versus remaining publication work

| Component | Evidence at this checkpoint | Maintainer completion still required |
| --- | --- | --- |
| Per-transaction geographic pins | 72 affected/integration checks passed; [real two-session Neon proof](../data/validation/neon-geography-pin-verification.json) confirms publication locking, fresh reads, stale-pin rollback and original pinned replay. | Publish matching Worker/adapter/importer code and record the production receipt. Site 17 did not contain this follow-up. |
| Dated parent membership and identity existence | New SQL/service contracts and bounded winning/withdrawal pages pass actual SQLite/PostgreSQL tests. Compiler, browser bridge and shared resolver pass 33 focused checks; Worker routing adds four actual SQLite/PostgreSQL checks. Source intervals, immutable corrections, explicit unknowns and complete reference fallback remain distinct. | Apply forward DDL and restricted-role grants after the original fourteen-table transfer; deploy matching routes and finish tested client integration. See [HOSTED_TEMPORAL_GEOGRAPHY.md](HOSTED_TEMPORAL_GEOGRAPHY.md) and [campaign sequencing](TEMPORAL_GEOGRAPHY_CAMPAIGNS.md). |
| Forward export/restore | New version-two export/restore files are being integrated independently of the frozen original contract. | Prove complete inclusion of every new table/column, exact source-byte preservation, revision/sequence recovery and restricted-role read-back. Preserve the original checkpoint and frozen restore path. |
| Dated footprints and client caches | New versioned footprint assets/contracts are in development. Current validated temporal bridge advertises `datedFootprints: 0`. | Finish reviewed immutable geometry/grid manifests, sourced selection, release/hash validation, cache invalidation and renderer integration. No content import may pretend unsupported footprint selection is active. |
| Hierarchy corrections | Sourced reference-hierarchy proposals and installer changes are being validated separately. | Complete original/new ID accounting, preserved historical evidence, unchanged-footprint proof where applicable, atomic release installation and matching publication. Staged proposals do not establish active geography. |
| Backend/provider binding | Neon authentication, restricted-role tests and disposable full restore rehearsal are verified. | Complete actual production restore/read-back, bind restricted application credentials as server secrets, publish explicit backend selection, verify private access and re-enable writes only after a recorded cutover. No silent D1 fallback or uncontrolled dual writes. |

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

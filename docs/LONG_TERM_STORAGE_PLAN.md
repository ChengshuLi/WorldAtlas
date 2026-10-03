# Long-term historical storage recommendation

Current provider/capacity inspection and operator response (3 October 2026) are in [PROVIDER_CAPACITY.md](PROVIDER_CAPACITY.md). Keep its measured usage, configured guards, provider settings and public pricing separate; the older dated cutover measurements below remain preserved.

The accepted architecture keeps the owner-private Sites website/API, managed PostgreSQL for indexed historical facts, and object storage for licensed source archives/media. Owner-private **Site 18 is deployed with Neon PostgreSQL, retained R2 archives and imports enabled** (environment revision 3; deployment `appgdep_6abf573be0948191a5517d0b2cbe7948`, succeeded 2026-10-02 07:03:34.504 UTC). Production migration run 36973747147 and forward migration run 36974831053 are verified. Live checks cover all 23 factual tables and seven dates from 3000 BC to 2026 AD; capabilities are `mapSnapshots:1`, `datedGeography:1`, `datedFootprints:0`, `storageExport:2`. Original read-back preserved all 3,984 historical claims and 28 archives (16,199,861 bytes), at ingestion revision 1321. See `data/validation/neon-final-publication.json` and `neon-final-api-writable.json` for the exact release and checks. The existing content-research/import platform is ready for Luna. This does **not** complete every atlas goal: dated-footprint browser/cache integration, installation of three validated hierarchy candidates, blocked geographic repairs, worldwide semantic approval and physical mobile validation remain technical-maintainer work. Luna researches sources, prepares supported sparse evidence, imports it and logs results; Luna does not change code, geography, infrastructure or deployments. Read [the engineering checkpoint](HANDOFF_ENGINEERING_CHECKPOINT.md) and [continuation log](HANDOFF_STATUS.md).

## What belongs where

| Store | Content | Retrieval |
| --- | --- | --- |
| Managed PostgreSQL | Stable identities, sources, sparse dated scalar claims/names, graph relationships, media manifests, withdrawals and import receipts | Indexed API reads and transactional imports |
| Object storage | Images/audio/video, lawful source archives, large route geometry, immutable bulk exports and cached map products | Content-addressed keys, hashes, licenses and byte-range retrieval |
| Sites deployment | Website code, fixed cartographic assets and bootstrapping manifests | Private website and API |

Research imports must not become website deployment assets. New facts, sources and relationships should not require a UI build or map pixelation. The current generic research bundles and stable content API preserve those boundaries.

The location × year × attribute product is a conceptual coverage matrix. A fact supported for 500 years is one interval claim, not 500 yearly rows. Unknown periods need no invented rows. Observation snapshots must keep their actual supported dates. Derived map summaries may be cached, but remain reproducible views of sourced immutable evidence.

## Implemented PostgreSQL foundation and measured growth

The implemented foundation has ordinary tables and indexes supporting location/attribute/date, entity/date, stable identity, source and correction queries. Preserve half-open dates, no year zero, exact source bounds, fixed classifications, immutable claims, sourced withdrawals, atomic corrections and deterministic resolver precedence. Use relational foreign keys and tested transactional imports; object storage cannot replace these query/consistency guarantees.

Measure representative row/index size, import throughput, selected-year map latency, query execution plans, backup/restore time and storage growth. PostgreSQL can grow beyond one D1 database, but a small serverless plan still has finite storage, compute and connection limits. Do not promise billions of rows without an actual capacity/budget envelope. Add partitioning only when these measurements justify it; the partition key and cross-partition identity/correction constraints need an explicit design rather than a premature schema guess.

Keep normal map delivery compact and entity-paged. Retrieve detailed source histories, relationships and media separately. Cache selected-year summaries with source/content revisions and preserve withdrawal authority. A cache is never authority to restore withdrawn evidence after a failed read.

## Provider selection and provisioning

The user selected Neon project `weathered-lab-37571695`, with PostgreSQL 18 and database `neondb`. Provider authentication and restricted-role contracts are verified. Supabase or RDS remain alternatives if future operational requirements change. Measure storage/compute, budget, backup retention, restore guarantees and Site connectivity; public marketing limits do not prove the configured account's actual quota.

Provisioning requires the selected provider/account, project/region and budget. Store connection credentials as server secrets; never browser assets, research bundles, command arguments, receipts or Git. Preserve the current private audience and server-side write authorization. Luna should not set up providers or rewrite code.

## Migration work remains engineering

1. Retain the implemented PostgreSQL adapter/schema and matching API contracts; publish the exact tested source.
2. Preserve tested constraints, source-bound imports, correction history and idempotent resume; verify new forward migrations and restricted-role grants on the actual target.
3. Retain the verified production copy of all original identities, claims, corrections and ingestion receipts, plus frozen D1 migrations and the restorable original export. Verify every new forward table through version-two export/restore.
4. Check exhaustive counts/hashes and representative indexed queries, publication authorization, backups and a tested restore before switching production reads/writes.
5. Retain the verified private API PostgreSQL binding. Complete the forward schema and matching new release, then verify write availability with an explicit checkpoint; avoid uncontrolled dual writes.
6. Recheck media manifests/object bytes separately. Blob storage can remain in R2 if its actual quota, access and cost are suitable.

Hosted dated membership/existence, its bounded client loader and version-two 23-table factual backup routes are now published with matching production DDL. Browser footprint/version-cache integration and installation of three validated hierarchy candidates remain maintainer work. The footprint scaffold advertises capability zero. PostgreSQL and structural checks do not establish global geographic semantic completion.

The research workflow prepares and validates bounded campaigns independently of infrastructure. Production imports are enabled; research must recheck current capabilities, release pins, revision and capacity. Large sustained expansion still requires measured storage/compute/query budgets. Technical maintainers own scaling and code; Luna owns source research, content, citations, imports and notes.

## Accepted direction and initial free tier — checked 1 October 2026 Pacific

The user accepted the PostgreSQL/object-storage recommendation and asked to start without paying if possible. Neon's official pricing page currently offers 1 GB of PostgreSQL storage per project, 100 CU-hours per month per project, scale-to-zero compute, and no time limit or required credit card. The free allowance is an initial research envelope, not capacity for hundreds of millions of facts. Sustained imports can exhaust compute before disk. The pricing page also lists 5 GB of separate object storage per project; using it would need a verified upload/access integration. Existing R2 can remain in place; its Site-managed quota/cost has not been verified.

Supabase was considered but not provisioned; Neon is the selected live provider. Published marketing allowances are not proof of the configured project quota. Paid costs include compute, storage and backup/history. Recheck current provider terms and project plan before sustained expansion.

Official sources inspected: https://neon.com/pricing and https://supabase.com/pricing. This note records the checked allowances, not a guarantee that a future plan is unchanged. Provider credentials must be supplied through secure server configuration, never chat or tracked files.

Production Neon migration is verified: run [36973747147](https://github.com/ChengshuLi/WorldAtlas/actions/runs/36973747147), source `17747fe`, restored all fourteen original collections to the production branch and verified restricted-role read-back. The database measured 318,275,584 bytes. Site 17 was redeployed with explicit PostgreSQL backend selection and a server-only runtime secret; the live private API retained all 3,984 claims and 28 archives (16,199,861 bytes) at revision 1321. See [the production migration receipt](../data/validation/neon-production-storage-migration.json) and [the live preservation receipt](../data/validation/neon-production-site-preservation.json).

Owner-private **Site 18 is deployed with Neon PostgreSQL, retained R2 archives and imports enabled** (environment revision 3; deployment `appgdep_6abf573be0948191a5517d0b2cbe7948`, succeeded 2026-10-02 07:03:34.504 UTC). Production migration run 36973747147 and forward migration run 36974831053 are verified. Live checks cover all 23 factual tables and seven dates from 3000 BC to 2026 AD; capabilities are `mapSnapshots:1`, `datedGeography:1`, `datedFootprints:0`, `storageExport:2`. Original read-back preserved all 3,984 historical claims and 28 archives (16,199,861 bytes), at ingestion revision 1321. See `data/validation/neon-final-publication.json` and `neon-final-api-writable.json` for the exact release and checks. The existing content-research/import platform is ready for Luna. This does **not** complete every atlas goal: dated-footprint browser/cache integration, installation of three validated hierarchy candidates, blocked geographic repairs, worldwide semantic approval and physical mobile validation remain technical-maintainer work. Luna researches sources, prepares supported sparse evidence, imports it and logs results; Luna does not change code, geography, infrastructure or deployments. Run 36973245038 was a rehearsal, not the production proof.

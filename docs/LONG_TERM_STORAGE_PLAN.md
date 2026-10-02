# Long-term historical storage recommendation

The accepted architecture keeps the owner-private Sites website and its API, uses managed PostgreSQL for the growing indexed historical knowledge base, and uses object storage for licensed source archives and media. Neon is provisioned. The PostgreSQL schema, adapter, restricted runtime role, original fourteen-table export/restore and explicit backend selection are implemented and tested, including a disposable full restore rehearsal. Production Site 17 now uses Neon PostgreSQL with retained R2 archives. Actual production migration, restricted server-secret binding and live private-API preservation are verified. Writes stay temporarily read-only while forward DDL and Site 18/version-two publication checks remain pending. See [the engineering checkpoint](HANDOFF_ENGINEERING_CHECKPOINT.md) and [the continuation log](HANDOFF_STATUS.md).

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

Hosted dated membership/existence and its bounded client loader are now implemented and tested, with matching production DDL/publication still pending. Matching version-two export/restore publication, browser footprint version/cache integration and installation of the three validated hierarchy candidates remain engineering work. The footprint scaffold is implemented with browser capability zero. Choosing PostgreSQL or passing structural checks does not establish global geographic semantic completion.

The research workflow prepares and dry-runs supported bounded campaigns independently of infrastructure. Actual imports must wait for the current production receipt confirming writes are available, with measured capacity diagnostics. Large sustained expansion should wait for a verified storage plan and backend migration. Technical maintainers own this work; Luna owns source research, factual content, citations, imports and research notes.

## Accepted direction and initial free tier — checked 1 October 2026 Pacific

The user accepted the PostgreSQL/object-storage recommendation and asked to start without paying if possible. Neon's official pricing page currently offers 1 GB of PostgreSQL storage per project, 100 CU-hours per month per project, scale-to-zero compute, and no time limit or required credit card. The free allowance is an initial research envelope, not capacity for hundreds of millions of facts. Sustained imports can exhaust compute before disk. The pricing page also lists 5 GB of separate object storage per project; using it would need a verified upload/access integration. Existing R2 can remain in place; its Site-managed quota/cost has not been verified.

Supabase's current free plan offers 500 MB database storage, 1 GB file storage and pauses projects after one week of inactivity. Neon is the selected, provisioned provider, with production restore and secure Site runtime binding verified; forward migrations and new-release write availability remain pending. Supabase has not been provisioned for this project. Paid costs include compute, storage and backup/history, not only disk. Recheck current provider terms at provisioning time.

Official sources inspected: https://neon.com/pricing and https://supabase.com/pricing. This note records the checked allowances, not a guarantee that a future plan is unchanged. Provider credentials must be supplied through secure server configuration, never chat or tracked files.

Production Neon migration is verified: run [36973747147](https://github.com/ChengshuLi/WorldAtlas/actions/runs/36973747147), source `17747fe`, restored all fourteen original collections to the production branch and verified restricted-role read-back. The database measured 318,275,584 bytes. Site 17 was redeployed with explicit PostgreSQL backend selection and a server-only runtime secret; the live private API retained all 3,984 claims and 28 archives (16,199,861 bytes) at revision 1321. See [the production migration receipt](../data/validation/neon-production-storage-migration.json) and [the live preservation receipt](../data/validation/neon-production-site-preservation.json).

Writes remain paused (`ATLAS_READ_ONLY=1`) while forward DDL run [36974831053](https://github.com/ChengshuLi/WorldAtlas/actions/runs/36974831053), source `d0cc015`, and the matching Site 18/version-two live checks are pending. The final research handoff is not yet ready. Current engineering source `937fa8e` passed all 394 final tests with zero skips and three real browser checks; those checks do not establish publication. Luna does not perform these engineering steps.

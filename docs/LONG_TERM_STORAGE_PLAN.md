# Long-term historical storage recommendation

The recommended long-term architecture keeps the owner-private Sites website and its API, uses managed PostgreSQL for the growing indexed historical knowledge base, and uses object storage for licensed source archives and media. No separate PostgreSQL service is provisioned yet. The current implementation is one D1 database plus R2; API compatibility is a design boundary, not an already implemented PostgreSQL adapter.

## What belongs where

| Store | Content | Retrieval |
| --- | --- | --- |
| Managed PostgreSQL | Stable identities, sources, sparse dated scalar claims/names, graph relationships, media manifests, withdrawals and import receipts | Indexed API reads and transactional imports |
| Object storage | Images/audio/video, lawful source archives, large route geometry, immutable bulk exports and cached map products | Content-addressed keys, hashes, licenses and byte-range retrieval |
| Sites deployment | Website code, fixed cartographic assets and bootstrapping manifests | Private website and API |

Research imports must not become website deployment assets. New facts, sources and relationships should not require a UI build or map pixelation. The current generic research bundles and stable content API preserve those boundaries.

The location × year × attribute product is a conceptual coverage matrix. A fact supported for 500 years is one interval claim, not 500 yearly rows. Unknown periods need no invented rows. Observation snapshots must keep their actual supported dates. Derived map summaries may be cached, but remain reproducible views of sourced immutable evidence.

## Initial PostgreSQL design and measured growth

Start with ordinary tables and indexes supporting location/attribute/date, entity/date, stable identity, source and correction queries. Preserve half-open dates, no year zero, exact source bounds, fixed classifications, immutable claims, sourced withdrawals, atomic corrections and deterministic resolver precedence. Use relational foreign keys and tested transactional imports; object storage cannot replace these query/consistency guarantees.

Measure representative row/index size, import throughput, selected-year map latency, query execution plans, backup/restore time and storage growth. PostgreSQL can grow beyond one D1 database, but a small serverless plan still has finite storage, compute and connection limits. Do not promise billions of rows without an actual capacity/budget envelope. Add partitioning only when these measurements justify it; the partition key and cross-partition identity/correction constraints need an explicit design rather than a premature schema guess.

Keep normal map delivery compact and entity-paged. Retrieve detailed source histories, relationships and media separately. Cache selected-year summaries with source/content revisions and preserve withdrawal authority. A cache is never authority to restore withdrawn evidence after a failed read.

## Provider selection and provisioning

Neon or Supabase are reasonable managed PostgreSQL candidates; RDS is another option if the project later needs more operational control. Choose based on measured storage/compute, budget, backup retention and restore guarantees, region, authentication and connectivity from the private Site. Verify the actual plan rather than importing a provider's marketing limits into the application.

Provisioning requires the selected provider/account, project/region and budget. Store connection credentials as server secrets; never browser assets, research bundles, command arguments, receipts or Git. Preserve the current private audience and server-side write authorization. Luna should not set up providers or rewrite code.

## Migration work remains engineering

1. Implement a PostgreSQL backend adapter and migration schema behind the current content API, with the same request/response and import contracts.
2. Verify constraints, source-bound imports, correction history, idempotent resume and shared resolver/static parity against both backends.
3. Copy all current identities, claims, corrections and ingestion receipts; preserve every stable ID and original evidence byte. Retain frozen D1 migrations and a restorable export.
4. Check exhaustive counts/hashes and representative indexed queries, publication authorization, backups and a tested restore before switching production reads/writes.
5. Switch the private API to the verified backend without changing research bundle format or rebuilding geography. Keep an explicit read/write cutover checkpoint; avoid uncontrolled dual writes.
6. Recheck media manifests/object bytes separately. Blob storage can remain in R2 if its actual quota, access and cost are suitable.

Dedicated hosted dated geographic memberships/footprint revisions and future domain-specific UI remain separate engineering tasks. They are not closed by choosing PostgreSQL. Global geographic semantic research is also not a structural database pass.

The immediate research workflow can import supported bounded campaigns into the current service, with measured capacity diagnostics. Large sustained expansion should wait for a verified storage plan and backend migration. Technical maintainers own this work; Luna owns source research, factual content, citations, imports and research notes.

## Accepted direction and initial free tier — checked 1 October 2026 Pacific

The user accepted the PostgreSQL/object-storage recommendation and asked to start without paying if possible. Neon's official pricing page currently offers 1 GB of PostgreSQL storage per project, 100 CU-hours per month per project, scale-to-zero compute, and no time limit or required credit card. The free allowance is an initial research envelope, not capacity for hundreds of millions of facts. Sustained imports can exhaust compute before disk. The pricing page also lists 5 GB of separate object storage per project; using it would need a verified upload/access integration. Existing R2 can remain in place; its Site-managed quota/cost has not been verified.

Supabase's current free plan offers 500 MB database storage, 1 GB file storage and pauses projects after one week of inactivity. Neon is the initial recommendation, subject to an actual account/project, secure credentials, region and measured query/storage checks. None has been provisioned in this checkpoint. Paid costs include compute, storage and backup/history, not only disk. Recheck current provider terms at provisioning time.

Official sources inspected: https://neon.com/pricing and https://supabase.com/pricing. This note records the checked allowances, not a guarantee that a future plan is unchanged. Provider credentials must be supplied through secure server configuration, never chat or tracked files.

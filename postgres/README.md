# PostgreSQL content foundation

`schema.sql` is the PostgreSQL counterpart of the frozen D1 migrations `0000` through `0007`. It creates the same fourteen content tables, explicit source/category/identity references, lookup indexes and enforced evidence contracts. Apply it once to an empty database; subsequent schema changes require a new reviewed migration. The original SQLite migration files remain unchanged.

This directory does not establish that a live Neon database has been provisioned or migrated. The target project is `weathered-lab-37571695`; deployment credentials and the runtime binding are separate, private configuration. Never put connection strings in Git, public assets, import receipts or logs. Local PGlite checks execute actual PostgreSQL, but do not certify the target server version, network access, production concurrency or capacity.

## Original evidence and identity

`value`, `metadata`, `counts`, `expected_counts` and geographic `evidence` remain **TEXT containing JSON**. Their whitespace, object-key order, numeric spelling and encoded source text are retained. JSON casts are used only for validation and querying; storing the columns as JSONB would change this contract. Ordinary retries compare complete stored field values, including those original text strings, and reject a changed claim under an existing ID. Identical retries do not replace earlier timestamps, evidence, identities or references.

Text columns use PostgreSQL's `C` collation to keep binary UTF-8 ordering independent of the provider's default locale. Calendar bounds use integral NUMERIC domains, so a raw SQL fractional year is rejected instead of being rounded during assignment to INTEGER. These domains enforce the supported range, no year zero and the exclusive 2027 endpoint. The adapter converts known calendar columns to safe JavaScript integers. Media sizes, timestamps and ingestion revisions use BIGINT; API validation and the adapter must reject unsafe JavaScript integer conversions.

The six geographic entity tiers and separate settlement identities retain their adjacent-tier parent rules. Political ownership is a dated attribute, never an implied geographic parent. Generic entities, names, relationships, licensed media links and retirement provenance use the existing content API; changing backend storage does not create historical evidence or new map footprints.

## Enforced writes

PL/pgSQL triggers retain append-only identities, sources, categories, claims, media, corrections, memberships and crosswalks. UPDATE, DELETE and TRUNCATE are rejected. The sole mutable content operation is a validated staged-to-published geographic-release transition, preserving its original definition. Normal writes use bounded transactional imports and stable ingestion fingerprints.

The schema enforces sourced intervals and lifetimes, example isolation, matching category/graph identities, typed scalar values, nullable unresolved evidence, retirement-aware overlap rules, habitation/rank contradictions and literal-zero population qualifications. New topography, vegetation and climate values must exactly match the fixed registry and its supported aliases. Registry values are copied from `src/environment-classifications.js`; changing that vocabulary needs a reviewed forward migration, not editing deployed SQL.

A correction inserts its retirement before the replacement claim in one transaction. This withdraws the old claim from overlap checks while retaining its original bytes. The ingestion receipt checks replacement completeness, and a deferred constraint additionally prevents committing a retirement whose promised replacement does not exist. Supersession cycles and unsourced or example-only withdrawal of factual claims are rejected.

## Transactions and revisions

Use SERIALIZABLE transactions for imported batches and retry SQLSTATE `40001` or `40P01` as a complete transaction, with a bounded retry policy. Identity, location-evidence, entity-name and geographic publication advisory locks protect conflicting writes; hash collisions only serialize unrelated work. A reader must still bracket page reads with the ingestion revision and reject changing multi-page snapshots.

`atlas_ingestions.rowid` is an explicit BIGINT, preserving the SQLite ingestion revision during migration. Its default function `atlas_next_ingestion_rowid()` acquires `pg_advisory_xact_lock(807245315,1)` **before** calling its sequence. Thus another ingestion cannot publish a higher revision and later reveal a lower one. The adapter also acquires that lock before writing an ingestion-tracked batch, keeping claims and their receipt in one transaction. Failed transactions and identical retries may consume sequence numbers; gaps do not imply missing claims.

Only the verified maintenance restore may specify original row IDs. Pause normal writes, preserve every source revision, reset the sequence to the restored maximum and verify the value before reopening imports. Untracked direct SQL writes are not part of the content API and cannot provide its snapshot-revision guarantee. Media registration and geographic preparation retain their separate publication contracts; they do not silently alter the fixed map's attribute snapshot.

## Geographic publication

Releases begin staged and require a reference source, pinned hashes, all six expected tier counts and six continents excluding Antarctica. Publication checks counts, full same-release parent chains, populated higher groups, advancing versions and agreement between active memberships and sourced crosswalks. Memberships and changes cannot be appended to a published release.

The service must independently verify membership, active-location and change hashes before publication, and compare hierarchy/footprint hashes with the actual prepared assets. PostgreSQL cannot certify external geometry merely because a supplied hash has the right format. These remain **undated reference releases**. Dedicated historical membership or footprint records are a separate application contract, not something this backend migration invents.

## Verified source migration

Export all fourteen D1 tables with original text fields and explicit ingestion `rowid`, preserving an ordered source manifest and hashes. Include the original entity registry, sources, both geographic releases, active and retired identities, claims, media metadata and object links. Keep R2 object bytes in place; changing relational storage does not require re-uploading media.

Restoration differs from adding new evidence: frozen D1 migrations intentionally grandfather some earlier environmental or unresolved labels. Applying new-import guards to those old rows would discard evidence. Use an owner-only, logged maintenance transaction with normal writes paused:

1. Apply `schema.sql` to an empty target and verify the table inventory.
2. Disable **USER** triggers on the fourteen target tables inside the restore transaction. Do not add a runtime configuration switch that lets ordinary imports bypass guards. Foreign keys and base CHECK constraints remain active.
3. Copy byte-preserved rows in dependency order: sources and entity types; topologically ordered entities; categories; attributes and ingestion receipts; media; names, relationships and media links; retirements; geographic releases, memberships and changes. Supply original ingestion row IDs. Published releases are copied as original rows, not falsely republished historical records.
4. Re-enable all USER triggers before committing, and restart the ingestion sequence at the restored maximum plus one (or one for an empty ledger) with `ALTER SEQUENCE atlas_ingestions_rowid_seq RESTART WITH …` inside the same transaction. Unlike `setval`, this restart rolls back with a failed restore. The currently preserved revision 1321 requires next value 1322; measure the actual restored maximum rather than hard-code it.
5. Verify per-table counts, ordered row hashes, original text bytes, constraints, trigger status, current geographic hash pins and maximum revision. Read back media metadata and representative linked object hashes. Retain the receipts in Git.
6. Validate the new API against the retained D1 read-only source, then switch the private runtime binding. Keep the source database and archives until the migration's read-back proof is accepted.

Only the schema owner can disable triggers; the application role should have the minimum SELECT/INSERT and validated publication permissions it needs, without ALTER, DROP, TRUNCATE or schema ownership. An owner connection remains able to perform deliberate administrative changes, so its secret must not be exposed as a general user credential.

## Compatibility and practical limits

The helper functions `json_each(TEXT,path)`, `json_type(TEXT,path)`, `json_extract(TEXT,path)` and `instr(TEXT,TEXT)` support the existing reviewed queries. `json_extract` returns **TEXT**, rather than SQLite's dynamically typed scalar. PostgreSQL map queries therefore use explicit numeric casts and PostgreSQL metadata construction; the adapter must not blindly translate arbitrary SQLite expressions. Supported helper paths are `$` or dot-separated object keys used by the current service.

PostgreSQL JSON parsing, Unicode handling and explicit SQL type casts are not interchangeable with every SQLite extension. Preserve raw source text and use the validated API for new evidence; do not claim arbitrary SQLite SQL is portable. Original JSON text with duplicate keys remains stored unchanged, but historical imports should use the documented normalized evidence contract rather than rely on ambiguous duplicate-key extraction semantics.

This foundation provides a persistent indexed backend and independent object storage. It does not claim unlimited rows or proven billion-record throughput. Continue sparse supported intervals, compact selected-year map transport and lazy original evidence retrieval; measure query plans, ingestion cost, storage and hosted latency before adding partitions or materialized caches. Unknown years require no fabricated annual rows.

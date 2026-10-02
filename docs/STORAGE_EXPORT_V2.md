# Forward raw-storage export v2

The frozen v1 snapshot, its fourteen-table source schema, resume ledger and PostgreSQL restoration tool remain unchanged. The current Site 17 transfer uses v1. Do not convert that snapshot or resume it using a v2 tool.

V2 is the separate complete contract for D1 migrations **0000–0009** and PostgreSQL `schema.sql` plus forward migrations **0001–0002**. It covers every one of the 23 `atlas_*` factual tables, including archived identities, example records, withdrawals, original ingestion rowids, staged footprint catalog entries and sealed validation receipts. It does not resolve, reclassify or reinterpret imported evidence.

| Additional collection | Purpose |
| --- | --- |
| `temporal_geography_validations` | Sealed membership/existence ingestion receipts |
| `geographic_membership_records` | Sparse dated parent evidence |
| `geographic_existence_records` | Sparse dated existence evidence |
| `temporal_geography_retirements` | Retained corrections and withdrawals |
| `footprint_versions` | Source/product/publication metadata and object pins |
| `footprint_version_objects` | Every source, mask, geometry and grid object reference |
| `footprint_selection_validations` | Sealed footprint-selection ingestion receipts |
| `geographic_footprint_records` | Sparse dated product selections and explicit unknowns |
| `footprint_retirements` | Retained footprint corrections and withdrawals |

## Capture and proof

The private read-only service exposes `/api/storage/v2/export-marker` and `/api/storage/v2/export/{collection}`. These routes must enforce the same private authentication and source-maintenance flag as v1; the new module does not authorize a caller by itself. Ordinary profile and map responses are not raw backups.

The reviewed contract is in `hosted/storage-export-v2-contract.js`. It pins every source/target SQL file by its original byte hash and pins the effective D1 and PostgreSQL catalogs. D1 catalog proof covers table, index and trigger definitions. PostgreSQL proof covers column order/types/domains/defaults/collations, user triggers, constraints, domain definitions, enabled deferred foreign-key triggers, and the atlas/JSON compatibility function definitions. An unexpected factual table, missing guard, changed definition or disabled guard prevents capture or restoration. The supported PostgreSQL schema is `public`; a PostgreSQL-version change that alters catalog serialization requires an explicit contract review.

The snapshot marker contains all table counts, the original ingestion revision, migration/catalog pins and hashes of all geographic release and footprint-version rows. The latter hashes detect permitted staged-to-published transitions even when the ingestion revision and row counts do not change. Before/after page markers and the final marker must match. Maintenance remains required throughout the entire capture.

Each bounded page receives its own SHA-256/byte-count/cursor receipt. A complete manifest additionally stores an ordered raw-row SHA-256 for **every** collection, including empty tables. JSON stored in SQL TEXT remains a string with its original whitespace, key order and duplicate keys; it is never parsed and re-encoded as database JSON. The exporter computes full row hashes from preserved pages, rather than rescanning all historical rows for every HTTP request. It streams those pages, so memory does not grow with the number of historical claims.

```sh
node scripts/export-hosted-storage-v2.mjs https://confirmed-site-origin/ /durable/private/snapshot-v2 --concurrency 2
```

The private credential is entered through hidden terminal stdin and is not written to the ledger or manifest. Fetch and response-body transfers have a shared 60-second deadline, four bounded attempts and cancellation-aware retry backoff. HTTP conflicts, malformed JSON and mismatched proof are not retried as successful content. HTTP 413 pages shrink without changing the collection cursor. A failed capture keeps its verified pages and `resume.json`; run the same command with a fresh credential to resume. V1 and v2 markers, cursors and ledgers are deliberately incompatible.

## Owner restoration

First install the reviewed base PostgreSQL schema and both forward migrations in an **empty** target. Forward schema deployment has its own owner-maintenance workflow; these restoration tools never install migrations or silently change a running service.

```sh
node scripts/restore-postgres-storage-v2.mjs /durable/private/snapshot-v2 --dry-run
node scripts/restore-postgres-storage-v2.mjs /durable/private/snapshot-v2 --empty-target-owner-restore
node scripts/restore-postgres-storage-v2.mjs /durable/private/snapshot-v2 --verify-only
```

Only the schema owner can restore. The secret `DATABASE_URL` stays in the authorized environment. Restoration verifies local migration bytes, the complete installed catalog and every source page/hash before starting. Historical tables stream in batches of at most 200; the entity identity graph is retained for parent-before-child ordering. Each source page is re-hashed when consumed during restoration, so edits after preflight cannot bypass verification.

One serializable transaction locks all 23 tables, verifies they are empty, temporarily disables USER triggers, inserts original rows in dependency order, flushes the deferred foreign-key graph, and restores every USER trigger. CHECK/domain constraints and foreign-key triggers remain enabled. Flushing deferred constraints before re-enabling triggers avoids PostgreSQL's pending-trigger-event restriction. The transaction then streams every restored table back to compare its count and ordered raw-row hash, confirms unchanged guard definitions/states, and transactionally restarts the ingestion sequence at the original maximum rowid plus one.

Any dependency, read-back, trigger or sequence failure rolls back every table and guard change. A lost commit acknowledgement produces an `unknown` commit-status receipt: use `--verify-only` before retrying. A nonempty target is rejected rather than overwritten. The v1 tool continues to restore v1 snapshots into its reviewed fourteen-table baseline; v2 snapshots require the v2 tool and complete forward target.

Media and footprint **metadata** are preserved; binary object bytes are not copied by this SQL transfer. Receipts explicitly say `media_bytes_moved: false`. Original object stores, verified object hashes, producer receipts and access configuration need a separate retained-object transfer/verification. Owner deployment metadata such as `public.worldatlas_schema_migrations` is outside the factual tables and must be retained with the administrative deployment receipt; application backups do not grant the runtime role access to that registry.

## Validation

```sh
node --test --test-concurrency=2 test/storage-export.test.mjs test/postgres-restore.test.mjs test/storage-export-v2.test.mjs
```

The forward tests include all 23 nonempty tables, multi-page identities, exact legacy TEXT, temporal and footprint receipts/withdrawals, immutable guard enforcement, sequence continuity, PostgreSQL export, source/target tampering, partial capture/resume, staged publication detection, deferred-FK rollback and byte-compatible v1 export/restore. Fixtures are synthetic and isolated; these checks do not claim production migration or media-byte transfer.

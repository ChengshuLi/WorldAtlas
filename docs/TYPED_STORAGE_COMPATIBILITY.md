# Typed storage version 3: compatibility and maintenance

This is the second bounded part of #529, following the pure contract/registry seam in PR #659. It adds empty forward storage and a complete versioned raw backup path. Typed import/read APIs, optional capabilities, actual new adapter/static/prepared/snapshot parity and the final domain module handover remain the third part. No domain algorithms, factual records, geographic approvals or production maintenance happen as a side effect of merging this code.

## Additive storage

`drizzle/0010_typed_observations.sql` and `postgres/migrations/0003_typed_observations.sql` add three append-only tables. The migration journal appends one entry for0010; every pre-existing entry and snapshot stays unchanged, and the previous whole journal bytes are retained in the owned evidence directory. Existing SQL migrations and the legacy source catalog, entities, relationships, records, retirements and geographic release/footprint records remain byte-for-byte unchanged.

- `atlas_typed_observations` stores polity/location/feature subjects with a registered field ID, contract version and registry hash, JSON TEXT value, supported interval, method/status/example label, existing source ID and original metadata.
- `atlas_typed_feature_links` stores dated links between existing identities with a registered relationship ID and the same evidence context. New feature identities reuse the existing extensible entity/type catalogs; this migration creates none.
- `atlas_typed_retirements` withdraws a typed observation or link while retaining its target, source, reason, optional replacement and original metadata. Existing retirement collections are not reinterpreted.

The database checks stable identity collisions, source support/class, endpoint kind/lifetime/example constraints, half-open dates without year zero, method/status, unresolved null values and raw JSON validity. Exact replays retain original bytes; changing or removing retained evidence fails. PostgreSQL also rejects truncation, and new trigger functions do not grant PUBLIC execution.

Active observations at the same subject/field/method/example level cannot overlap. A correction may append its retirement before its replacement in one atomic ingestion; the adapter must append its ingestion journal in that same atomic batch; that journal guard requires every referenced typed replacement to exist before the supported service batch commits. A standalone owner SQL retirement without its journal can persist an incomplete replacement; this guard is not universal deferred integrity enforcement. Such writes are outside the supported ingestion protocol, and the final adapter must never omit the journal. Example sources cannot withdraw factual typed evidence. Typed links retain separate identity/evidence semantics and do not compute geometry or disease aggregation.

Field/metric/module semantics, complete measurement metadata, derivation inputs, current registry hash, source archive references, regional gates and exact release/subject pins must additionally be checked by the controlled import adapter. A well-formed registry hash in SQL is not permission to import an arbitrary field. This storage layer does not implement GDP/mortality algorithms, approve feature geometry or authenticate a certificate.

## Raw export and restoration

The version 3 contract in `hosted/storage-export-v3-contract.js` covers all 26 factual tables, including all three typed tables, and pins the existing migrations plus these forward additions. Catalog hashes cover the actual installed SQLite/PostgreSQL definitions and enabled guards. Unexpected tables, changed definitions or missing/disabled guards fail closed; no filtered unknown inventory is accepted as a complete backup.

The private GET routes are:

- `/api/storage/v3/export-marker`
- `/api/storage/v3/catalog`
- `/api/storage/v3/export/<collection>`

A complete export requires the documented owner maintenance read-only window. Use `scripts/export-hosted-storage-v3.mjs` with the confirmed HTTPS Site origin and a fresh durable directory. Its existing hidden-stdin credential mechanism uses the private header in memory; never put a secret in a URL, argument, environment log, repository or chat. The output journal preserves every completed page and checks its bytes/hash before resuming. Bound transport retries do not authorize replacing a different snapshot.

Values and metadata stay original JSON TEXT, including whitespace, original numeric spellings and archived/withdrawn evidence. Numeric measurements stored as JSON TEXT do not pass through a SQL numeric conversion. Identity keys and ingestion row IDs retain their original order; counts, revision, geographic releases, footprint versions, catalog and contract pins bind the snapshot. Zero, false, unresolved null and retired corrections have separate source rows.

`scripts/restore-postgres-storage-v3.mjs` restores only a verified complete source snapshot into an explicitly acknowledged empty owner target. It checks schema ownership, migration pins, all table/column inventories and original enabled guards, uses one transaction, restores every original row with constraints verified, restores guards, reads every table back by ordered hash and transactionally resets the sequence. A constraint failure rolls back rows, guards and sequence. Ambiguous commits require read-only verification before retry; a workflow success is not a restoration receipt. Media registration bytes are preserved, but this SQL export does not move or verify object-store payloads.

The version 1 fourteen-table baseline and version 2 twenty-three-table backup contracts/readers/restorers remain intact. Existing archived backups retain their exact contracts and restore verification. Version 1 remains a deliberately limited baseline projection. Version 2 remains strict: it must not silently claim completeness for a database that has added typed tables. Use version 3 for a complete typed-schema backup. Final API integration must provide an explicitly labeled compatible legacy read/export projection, validate the complete known extension before any projection and prevent maintenance clients from treating a projection as a complete backup. This requirement is unfinished in this second part.

## Deployment boundary and remaining work

The version 3 marker validates the complete catalog before reading new tables; an uninstalled or inconsistent schema fails closed. These routes do not advertise a typed write capability. A normal merge does not install owner PostgreSQL DDL, change application role privileges, rerun the baseline transfer, import research or publish the Site. The owner forward-migration workflow currently supports its already reviewed migrations; extending that verified workflow and its role/catalog proofs is still part of the final integration work. Never bypass its closed migration list with ad-hoc provider SQL.

Current production remains on the verified version 2 forward schema. The designated publisher coordinates owner maintenance, future reviewed forward application and publication on issue #39, retains exact rollback/source/package/native receipts, and settles live-work ownership only after verification. Domain children remain blocked until all #529 acceptance criteria and the coordinator's explicit readiness are met.

Local reproduction: after `npm ci`, run `node --test test/storage-export-v3.test.mjs test/storage-export-v2.test.mjs test/storage-export.test.mjs`. To reproduce installed catalog byte hashes without changing any provider or existing source file, run `node data/engineering/observation-storage-20261003-7e91/catalog-reproduction.mjs /tmp/fresh-catalog-receipt.json`. The destination must not already exist. Source fixtures are explicitly synthetic; no geography/device certificate or production operation is inferred.

# Persistent historical atlas

The map is a view of a shared historical knowledge model. Stable identities are independent of display names, political ownership and current reference geometry. Geography uses its complete single-parent adjacent-tier chain; people, events, armies, routes, artifacts and other entities connect through sourced relationships instead of borrowing geographic parent fields.

## Storage responsibilities

- D1 stores indexed entities, supported source intervals, categories, dated attributes/names, relationship evidence, media metadata and import receipts.
- R2 stores media bytes and source files independently of a website deployment. Database links retain content identity, attribution, licensing and source context.
- Fixed map geometry and grid assets are compiled independently of dated record imports. They are cached cartographic assets, not the authoritative store for future historical additions.
- The retained SQLite database and immutable geographic archive preserve earlier imported records. Existing records are not silently moved onto successor footprints.

New imports use bounded, transactional batches and idempotency keys. Validated source intervals and stable entity references prevent unsupported ancient backfill. Date intervals remain half-open, exclude year zero, and preserve original source precision. Optional calendar and date precision metadata may describe finer event timing without pretending the current annual map has day-level evidence.

Every historical claim carries its own evidence. Relationship types can describe participation, command, travel, manufacture, association with a place, or another documented relation. Extensible entity types avoid adding a new flat table for every future subject. Dated labels and aliases remain separate from identity. Rich domain-specific properties belong in typed future facets rather than unrelated map columns.

The browser combines immutable prepared source caches with current database evidence through the existing shared location resolver. A current year's owner, primary culture/religion and other map values remain single whole-location results even when the knowledge graph contains many related claims or participants.

## Current scope and limits

The foundation does not invent event, character, army, route or artifact content. Source licensing, uncertainty, identity matching and geographic semantic review remain necessary before imports. Database and object storage capacity is separate from the static deployment package limit. The initial media upload endpoint accepts files up to 20 MiB; larger-file multipart transport can be added without changing entity/media identities or database relationships.

The Site stays owner-private. Server-side writes rely on the existing platform access boundary, reject cross-origin browser writes and accept bounded structured imports. A future change of audience must revisit write authorization; database persistence never relies on browser storage.

## Geographic publication and growth

The current geographic parent registry is a reference snapshot; it is not evidence that those memberships existed in ancient years. Changing a sourced footprint or parent membership requires an explicit geographic migration, retained predecessors, a new footprint/source hash, and regenerated derived ownership and grid assets. Existing dated claims stay on their original IDs. The initial hosted API deliberately accepts historical records and graph relationships, not raw footprint replacement.

Immutable geographic reference releases, adjacent-tier reference memberships, original/successor crosswalks and footprint/hierarchy/grid hash pins are implemented and deployed. Both baseline and reviewed releases remain queryable; published releases are immutable and bootstrap is resumable. These memberships are undated reference snapshots. Dedicated dated geographic membership/footprint publication and year-selected grid revisions remain future work; current reference membership must not be presented as verified ancient administration. Generic dated graph relationships can express sourced historical associations without mutating the reference hierarchy.

As content grows, keep indexed queries and cursor paging; add typed facets for domain-specific event dates, army composition, route geometry and artifact descriptions. Large route/source geometry belongs in versioned object storage with a recorded digest, not an unbounded JSON metadata field. Preserve date precision and calendar explicitly when adding subannual dates; unknown days do not become January 1. Search indexing and database partitioning can be added without replacing stable public entity IDs. Managed database capacity has its own service limits; it is separate from the deployment asset limit.

Schema migrations remain immutable after application. Backfills run as independently resumable, idempotent imports with receipts. Source hash checks, transactional writes and retained original evidence support reproducible publication and later correction. The reference catalog bootstrap is separate from the website archive, so adding records does not require a new website deployment.

## Correcting evidence

Sourced retirements withdraw or supersede claim records, dated names, relationships and media links. They retain the original immutable claim, correction source and reason; a replacement may be imported in the same transaction. Failed replacement validation rolls back the entire batch. Retired claims stop participating in every active reader and overlap/habitation check. Corrections do not delete entities or media objects.

`GET /api/evidence/{collection}/{claim_id}` returns the original claim and source plus withdrawal/replacement history. Example claims remain opt-in. A retirement is irreversible; restoring evidence creates a new claim ID. The correction's publication/source dates are distinct from the ancient interval described by the original claim.

Media retrieval supports byte-range requests for audio/video seeking. The current bounded upload endpoint still has a 20 MiB per-file limit.

Map requests restrict dated-name queries to geographic and settlement entities; future person/event names remain available through their entity profiles and general API queries. Each attribute/name/retirement page brackets its read with the ingestion revision, and the client requires complete pages from one revision across all three streams. A changing revision retries the entire read at most twice. On an outage the streams fail atomically: the last complete same-year/example snapshot may be shown explicitly as stale, retaining its complete withdrawals. Without such a cache, dated prepared/imported values are unavailable because withdrawal knowledge is missing. Geography remains browsable. Retry the year to recover current content; an empty failed retirement response never authorizes restoring prepared claims.

Deployment archives must contain root `drizzle/*.sql` and `drizzle/meta/**` alongside the Worker and client assets. The first provisioning attempt created bindings without tables when migrations were included only under the server output; importing data is gated on the live table inventory. Frozen primary SQL stays unchanged. The reproducible compiler creates a tested hosting transport for 21 guards in migration 0002; stage that derivative in the separate Site mirror as described in `docs/HOSTED_MIGRATION_TRANSPORT.md`. Native version 13 applied all migrations, and production release/content/archive read-back receipts are retained under `data/validation`.

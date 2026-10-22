# Persistent historical atlas

The map is a view of a shared historical knowledge model. Stable identities are independent of display names, political ownership and current reference geometry. Geography uses its complete single-parent adjacent-tier chain; people, events, armies, routes, artifacts and other entities connect through sourced relationships instead of borrowing geographic parent fields.

## Storage responsibilities

- Neon PostgreSQL is the maintained store for admitted hosted application records: entities, categories, dated names and dated attributes, relationships, withdrawals, media metadata and import receipts. A source file, local SQLite row or prepared bundle does not establish that a record was imported into Neon.
- R2 stores media bytes and source files independently of a website deployment. Database links retain content identity, attribution, licensing and source context.
- Git retains reviewed source evidence, geographic reference inputs, accepted repair provenance and the corrected prepared map bank. The website authenticates and copies that finished bank; it does not replay repairs in the browser. These versioned map products are independent of ordinary dated-record imports.
- Prepared catalogs, reference-derived rows and website assets are views of their pinned sources, not separately editable accepted facts. Retained settlement estimates remain Git-backed potential source evidence for future location/year work, not verified population totals for these location boundaries. Their direct import is cancelled.
- The generated `.cache/package-atlas.sqlite` is a disposable build/test artifact, not a synchronized content store. Its actual post-build consumers finish before the existing receipt-bound worktree release removes the unchanged generated output. A persistent `data/atlas.sqlite` or historical snapshot can contain local-only records; preserve it until its logical data and necessary provenance are recoverable. Existing records are not silently moved onto successor footprints.

New imports use bounded, transactional batches and idempotency keys. Validated source intervals and stable entity references prevent unsupported ancient backfill. Date intervals remain half-open, exclude year zero, and preserve original source precision. Optional calendar and date precision metadata may describe finer event timing without pretending the current annual map has day-level evidence.

Every historical claim carries its own evidence. Relationship types can describe participation, command, travel, manufacture, association with a place, or another documented relation. Extensible entity types avoid adding a new flat table for every future subject. Dated labels and aliases remain separate from identity. Rich domain-specific properties belong in typed future facets rather than unrelated map columns.

The browser combines immutable prepared source caches with current database evidence through the existing shared location resolver. A current year's owner, primary culture/religion and other map values remain single whole-location results even when the knowledge graph contains many related claims or participants.

## One current owner label per identity

Owner assignment and display text are separate. An admitted owner category ID resolves through one shared ID lookup, not independently maintained feature strings or palette entries. For owner/polity identities, the exact owner's preferred dated `atlas_names` record wins; otherwise the current canonical `atlas_categories` name supplies the identity label. A location's own name is never its owner's name. Explicit unknown/disputed/no-majority assignments remain unresolved before this lookup. A known assignment with no admitted display text remains a known ID with an unavailable label.

`data/current-owner-labels.json` is a generated read-only replica of non-example owner categories, not another editable master. It records the consistent ingestion revision and an actually published geographic release as capture provenance. That reference is not a perpetual compatibility requirement: an unrelated later geographic release does not change these owner identities. The initial complete capture contains 1,446 category rows at revision 3,051. The existing `ownerLabelSnapshot` catalog function exhausts all revision-checked pages, refuses drift or an unpublished capture release, and returns only ID, kind, name and source ID. Refresh the complete replica from the maintained store and commit/review it before ordinary source-image authentication; never modify accepted build inputs after authentication or silently read live Neon during a build.

The generated `atlas-geography.json` carries this replica to static and local-server consumers. The shared resolver serves map labels, search and owner profiles; geography/location/unit profiles still use their release-scoped membership names and dated preferred names, not raw entity identity metadata. Raw source spellings, original registry rows and immutable catalog history remain evidence and are not alternative display authorities. The reference category fallback does not assert an otherwise unsupported dated geographic or owner-profile name.

## Current scope and limits

The foundation does not invent event, character, army, route or artifact content. Source licensing, uncertainty, identity matching and geographic semantic review remain necessary before imports. Database and object storage capacity is separate from the static deployment package limit. The initial media upload endpoint accepts files up to 20 MiB; larger-file multipart transport can be added without changing entity/media identities or database relationships.

The historical Site deployment was owner-private. The [Cloudflare publication route](CLOUDFLARE_HOSTING.md) supports a public read-only website; a build does not deploy it, import records or enable writes. Protected server-side writes retain their existing authorization and cross-origin checks. Audience and deployment decisions remain explicit; database persistence never relies on browser storage.

## Geographic publication and growth

The current geographic parent registry is a reference snapshot; it is not evidence that those memberships existed in ancient years. Changing a sourced footprint or parent membership requires an explicit geographic migration, retained predecessors, a new footprint/source hash, and regenerated derived ownership and grid assets. Existing dated claims stay on their original IDs. A [same-winner reference-alias correction](NATIVE_REFERENCE_METADATA.md) instead preserves the original scientific bank and current content release when complete source/receipt validation proves that only an already-stale label changes. The hosted API accepts historical records and graph relationships, not raw footprint replacement.

Immutable geographic reference releases, adjacent-tier reference memberships, original/successor crosswalks and footprint/hierarchy/grid hash pins are implemented. Only actually published database releases are queryable; a committed reviewed release is not proof of live publication. Published releases are immutable and bootstrap is resumable. These memberships are undated reference snapshots. Dedicated dated geographic membership/footprint publication and year-selected grid revisions remain future work; current reference membership must not be presented as verified ancient administration. Generic dated graph relationships can express sourced historical associations without mutating the reference hierarchy.

As content grows, keep indexed queries and cursor paging; add typed facets for domain-specific event dates, army composition, route geometry and artifact descriptions. Large route/source geometry belongs in versioned object storage with a recorded digest, not an unbounded JSON metadata field. Preserve date precision and calendar explicitly when adding subannual dates; unknown days do not become January 1. Search indexing and database partitioning can be added without replacing stable public entity IDs. Managed database capacity has its own service limits; it is separate from the deployment asset limit.

Schema migrations remain immutable after application. Backfills run as independently resumable, idempotent imports with receipts. Source hash checks, transactional writes and retained original evidence support reproducible publication and later correction. The reference catalog bootstrap is separate from the website archive, so adding records does not require a new website deployment.

## Correcting evidence

Sourced retirements withdraw or supersede claim records, dated names, relationships and media links. They retain the original immutable claim, correction source and reason; a replacement may be imported in the same transaction. Failed replacement validation rolls back the entire batch. Retired claims stop participating in every active reader and overlap/habitation check. Corrections do not delete entities or media objects.

`GET /api/evidence/{collection}/{claim_id}` returns the original claim and source plus withdrawal/replacement history. Example claims remain opt-in. A retirement is irreversible; restoring evidence creates a new claim ID. The correction's publication/source dates are distinct from the ancient interval described by the original claim.

Media retrieval supports byte-range requests for audio/video seeking. The current bounded upload endpoint still has a 20 MiB per-file limit.

Map requests restrict dated-name queries to geographic, settlement and owner-category identities; future person/event names remain available through their entity profiles and general API queries. Each attribute/name/retirement page brackets its read with the ingestion revision, and the client requires complete pages from one revision across all three streams. A changing revision retries the entire read at most twice. On an outage the streams fail atomically: the last complete same-year/example snapshot may be shown explicitly as stale, retaining its complete withdrawals. Without such a cache, dated prepared/imported values are unavailable because withdrawal knowledge is missing. Geography remains browsable. Retry the year to recover current content; an empty failed retirement response never authorizes restoring prepared claims.

## Retained Site migration history

The following is historical Site/D1 transport evidence, not the current Neon or Cloudflare deployment recipe. Current PostgreSQL operations use [NEON_FORWARD_MIGRATIONS.md](NEON_FORWARD_MIGRATIONS.md) and [CURRENT_POSTGRES_RECOVERY.md](CURRENT_POSTGRES_RECOVERY.md), with their explicit authorization and recovery requirements.

The historical Site deployment archives required root `drizzle/*.sql` and `drizzle/meta/**` alongside the Worker and client assets. The first provisioning attempt created bindings without tables when migrations were included only under the server output; importing data is gated on the live table inventory. Frozen primary SQL stays unchanged. The reproducible compiler creates a tested hosting transport for 21 guards in migration 0002; stage that derivative in the separate Site mirror as described in `docs/HOSTED_MIGRATION_TRANSPORT.md`. Native version 13 applied all migrations, and production release/content/archive read-back receipts are retained under `data/validation`.

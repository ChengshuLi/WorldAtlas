# Versioned reference geography

Stable entity identities and sourced historical evidence are append-only. A corrected geographic hierarchy therefore publishes a separate **reference release**, rather than updating `atlas_entities.parent_id` or pretending the correction happened at a historical year.

Migration `0002_geographic_reference_releases.sql` adds three tables. Applied migrations `0000` and `0001`, their snapshots, the original registry and historical attribute/name/relationship rows remain unchanged.

- `atlas_geographic_releases` pins a source, integer version, publication/reference calendar label, prepared hierarchy/footprint hashes, membership/active-location/crosswalk hashes and all six expected active tier counts.
- `atlas_geographic_memberships` gives a stable geographic entity one reference parent and optional reference display name per release, with separate active/retired status and sourced evidence. Its composite primary key enforces one result per entity/release.
- `atlas_geographic_changes` preserves explicit sourced same-tier merge, split, replacement, retirement, creation, rename, reparent and retention crosswalks. Old and new IDs remain registered.

The six fixed tiers are location, province, area, region, subcontinent and continent. All active members must have an active adjacent-tier parent **in the same release**, except continents. Every active higher unit needs at least one active member. Exactly six continents are required; Antarctica is excluded. Strictly increasing parent tiers rule out cycles without an expensive recursive traversal.

## Stage, validate, then publish

Register any genuinely new stable entities first with the existing bounded `importBatch`. The original reference parent is retained permanently. A new geographic release supplies its current reference parent independently. Geography sources must have `status: 'reference'`; example entities, historical claims and nongeographic entity types cannot masquerade as reference geography.

Import functions in [geographic-releases.js](../hosted/geographic-releases.js):

```js
const memberships = [
  {
    entity_id: 'stable-location-id', kind: 'location',
    parent_id: 'stable-province-id', reference_name: 'Reference display name',
    active: 1, source_id: 'pinned-review-source',
    evidence: {method: 'whole-source-parent', source_version: 'pinned-sha'},
  },
  // Every active parent and every other approved location is required.
];
const changes = [
  {
    id: 'release-v2:reparent:stable-location-id',
    old_entity_id: 'stable-location-id', new_entity_id: 'stable-location-id',
    change_type: 'reparent', source_id: 'pinned-review-source',
    evidence: {reason: 'Verified complete named source-parent membership'},
  },
];
const release = {
  id: 'reference-geography-v2', source_id: 'pinned-review-source', version: 2,
  reference_date: '2026-10-01',
  hierarchy_sha256: preparedHierarchyAssetHash,
  footprints_sha256: preparedFootprintAssetHash,
  membership_sha256: await geographicMembershipHash(memberships),
  location_ids_sha256: await geographicLocationIdsHash(memberships),
  changes_sha256: await geographicChangesHash(changes),
  expected_counts: {location, province, area, region, subcontinent, continent: 6},
  metadata: {reference_only: true, source_manifest: pinnedManifest},
};
await stageGeographicRelease(db, {release});
// Send independent chunks of at most 250 total input rows each.
await stageGeographicRelease(db, {
  release_id: release.id, memberships: memberships.slice(0, 200),
  ingestion_id: 'release-v2:members:000',
});
// Stage every remaining membership/crosswalk chunk, then:
await finalizeGeographicRelease(db, release.id);
```

An import accepts `release`, or the exact existing `release_id`, plus `memberships`, `changes` and an optional ingestion ID. A definition counts as one input row. Each request is bounded to 250 rows and 1 MiB. Membership `kind` is read from the immutable identity registry; it is supplied to the hash helper for manifest preparation, not trusted as a new type.

Rows, release definitions and crosswalks are immutable even while staging. A changed stable ID rejects the entire D1 batch and ingestion receipt together. Identical retries are idempotent. A correction to a staged definition requires a new release ID/version, preserving the rejected/incomplete staging record as audit context. Crosswalk IDs should include the release ID to remain globally unique.

No staged or partially imported release appears in normal queries. Finalization validates the six-tier counts, full same-release chains, populated higher groups, active crosswalk endpoints and three actual content hashes. A same-tier merge/split/replacement/retirement must leave its old ID inactive or absent in the new release, and every replacement/new endpoint must be active there.

Only then does a single atomic status update publish the release. The database repeats structural checks inside that statement. Total immutable membership/crosswalk count predicates close the read/staging race; a concurrent append makes the update fail and requires verification again. Published integer versions must advance, so an older delayed staging operation cannot unexpectedly replace a newer current release.

## Hash and memory contract

Hashes use SHA-256 of canonical JSON: object keys sorted, UTF-8 encoded, deterministic binary UTF-8 row ordering. Memberships sort by `entity_id` and hash only `{entity_id, kind, parent_id, reference_name, active, source_id, evidence}`. Crosswalks sort by `id` and hash only `{id, old_entity_id, new_entity_id, change_type, source_id, evidence}`. Active location IDs form a separately sorted array. Missing reference names become `null`; missing evidence becomes `{}`. Manifest preparation must fill the resolved source ID before hashing.

Publication verification reads 500-row keyset pages. Cloudflare Workers use `crypto.DigestStream` to hash those pages without collecting the entire atlas or evidence in memory. Node's test/preparation fallback uses Web Crypto over buffered bytes; the digest is identical. Parent/active-child lookups use indexes on release/active/parent/entity, and normal pages cap at 250 rows. Finalization cost grows with the reference registry, not the number of historical attribute claims or media files.

`hierarchy_sha256` and `footprints_sha256` identify **externally pinned preparation artifacts**. The database independently proves the imported membership, active-location ID set and crosswalk hashes; it cannot reconstruct a geometry hash from geometry stored in a separate asset/object. Preparation/publication gates must compare those two asset hashes against the actual approved prepared files and the served static release manifest. Supplying a hash without validating its source is not a geometry audit.

## Query and profile contract

- `geographicRelease(db)` returns the latest published version. Passing an exact published ID makes an older release inspectable. `includeStaged: true` is for administrative audit only.
- `geographicMembershipPage(db, {releaseId, cursor, limit, active, parentId})` returns published reference rows; `active: null` includes retained inactive memberships.
- `referenceMembership(db, entityId, {releaseId})` returns the selected published release, the current reference membership and original registry name/parent/active status. A registered historical/retired identity absent from a published release returns `membership: null`, not an invented new parent.
- `geographicChangePage(db, {releaseId, cursor, limit})` returns the immutable source-backed crosswalk.

Each result says `reference_only: true`. HTTP routes and `entityProfile` integration belong to the Site owner. A profile should show the new reference name/parent as reference context, preserve original registry context, and keep dated preferred names and historical evidence resolved independently for the selected year. A geographic reference release is not a dated political, cultural or historical membership assertion. Future genuinely historical geographic membership needs a separately sourced temporal contract; this feature never silently backfills one.

The prepared/static atlas must expose the same selected release ID and hashes as the hosted reference API. Reject an asset/release mismatch rather than overlaying memberships onto incompatible footprints. Until a new release is published, readers keep the previous complete release; the original registry remains accessible throughout.

## Verification

`node --test test/geographic-releases.test.mjs` applies all generated migrations to actual SQLite with the D1 service interface. It covers staged invisibility, complete six-continent trees, pinned hashes/counts, wrong-tier/cyclic/missing/example/nongeographic identities, atomic rollback/idempotency, immutable publication, archived memberships/releases, sourced same-tier crosswalks, indexed parent queries, UTF-8 IDs and page-boundary hashing. Historical population and dated names remain byte-for-byte unchanged after the reference rename/reparent/merge.

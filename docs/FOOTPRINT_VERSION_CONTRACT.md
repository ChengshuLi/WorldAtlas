# Complete footprint products and dated selection

This forward contract adds D1 migration `0009_footprint_versions` and PostgreSQL
migration `0002_footprint_versions`; it does not change the frozen original
fourteen-table storage format or base PostgreSQL schema. Applying migrations,
restoring their new rows, publishing assets, worker endpoints and browser
integration are separate deployment operations. The service implementation is
`hosted/footprint-versions.js`.

No historical footprint set is supplied by this change. The current reference
map has documented land-mask/source caveats and must not be called certified
historical or complete worldwide land coverage. Current rasterization's lowest
ID wins rule is not a geometry-overlap validation.

## Maintainer producer boundary

`stageFootprintVersion(db, bucket, payload, {maintainer:true})` stages immutable
headers and object references. `publishFootprintVersion(db, bucket, id,
{maintainer:true, trustedProducers})` performs the publication checks. These
functions are owner/maintainer operations, not ordinary research endpoints.
`maintainer:true` is an internal capability; a route must never copy it from a
request body. PostgreSQL `worldatlas_app` can SELECT the two catalog tables but
cannot INSERT, UPDATE or publish them. D1 has no comparable database roles;
its owner/maintainer entry point must remain outside ordinary Site imports.

A trusted producer entry is `{code_sha256, public_key_jwk}` keyed by producer key
ID. Keys are Ed25519 public JWKs; private keys stay outside Git and the browser.
A trusted key pins the reviewed producer implementation hash. A signature is a
producer trust boundary, not a substitute for source research or an invented
human approval. Never configure a key for an unreviewed script that simply
sets all checks to true.

The server verifies every R2 object's original SHA256 and registered byte
count while reading it in chunks. Each object is bounded to 20 MiB; each grid
part decodes to at most16 MiB. There are at most512 objects/version. The server
holds one decoded part at a time, plus row offsets, the ID inventory and cell
counts; it never constructs all ownership runs or a world geometry in memory.
Node24 uses incremental `node:crypto` hashing; Workers use `DigestStream` when
available (the fallback requires Node compatibility).

## Manifest and signed receipt

The manifest is a registered content-addressed `atlas_media` R2 JSON object,
format `worldatlas-footprint-v1`, with:

- `id`, `release_id`, `source_id`, half-open `supported_from`, `supported_to`.
- Ordered `locations`: every active approved location in that published release,
  exactly once, UTF8/code-point order, pixel indices1..N, per-location
  `footprint_sha256`, original/reconciled `source_media_ids`, `status:represented`,
  positive `cells`, `land_area_m2`, and `represented_area_m2`.
- `objects`: distinct media IDs with role `source_archive`,
  `reconciled_geometry`, `coverage_mask`, `rows` or `runs`; SHA256 and byte count.
  Grid parts additionally pin offset/words, encoding `gzip-u32le`, decoded SHA256
  and decoded byte count. All five roles must be present.
- `grid`: format `packed-ownership-v2-u32le`, projection `EPSG:3857`,
  latitude_limit85.05112878, antimeridian `split-at-180`, zoom0..12,
  size256×2^zoom, coordinate_bits and run_words. Province membership is
  deliberately separate from location ownership.
- `location_ids_sha256` matching the release inventory, `dictionary_sha256`,
  `footprints_sha256`, `grid_sha256`, and explicit `footprint_hash_algorithm`.

For now every approved location must have positive represented cells. Partial
inventories, absent/unexplained IDs or non-applicable placeholders are rejected;
source-based identity replacement/exclusion requires a separately reviewed
geographic release/preparation operation. Habitation is not geometric absence.

`footprintCanonicalJson` sorts object keys and preserves array order. The
algorithm `sha256-canonical-json-location-geometry-sha256-v1` hashes the ordered
array `[[locationID, perLocationGeometrySHA256], ...]`. The geometry SHA is the
producer's canonical geometry-byte digest, pinned by the signed receipt.
This differs from older locale-sorted GeoJSON and archived WKB hashing; these
hashes are never interchangeable. Dictionary SHA hashes the ordered ID array.
Grid SHA hashes `{grid,dictionary_sha256,parts}` where parts are the rows/runs
object entries in manifest order. Original media SHA always hashes exact bytes,
including JSON whitespace; no SQL JSONB normalization is introduced.

The separate receipt JSON object has format `worldatlas-footprint-proof-v1`,
manifest_sha256, release_id, footprints_sha256, producer `{code_sha256,algorithm}`,
checks `{valid_geometries, antimeridian, no_inter_location_overlaps,
coverage_explained, all_locations_represented, exclusive_grid}` and coverage
`{landmask_media_id, uncovered_statuses, approved_exception_source_ids}`.
Uncovered statuses are explicit `water`, `source-gap`, `outside-projection`;
source gaps are not relabeled water. Every exception source must exist, and the
land mask must be an archived coverage-mask object. The signature is
`{key_id,algorithm:Ed25519,value:base64}` over canonical JSON of the entire receipt
with only its signature field removed.

The producer must actually execute geometry validity, source/license/vintage,
antimeridian, overlap, land-mask gap, distortion and hierarchy reconciliation
checks before signing. The server verifies the trusted signed assertion, exact
source bytes and mechanically validates the complete grid: contiguous part
coverage, row/run counts, nonoverlapping runs, valid exclusive location IDs,
and exact positive per-location representation counts. It does not rerun GIS
or independently certify the factual historical reconstruction. No producer
or geometry assets are created by these tests; all fixtures are synthetic.

## Research claims and snapshots

`importFootprintSelections(db, payload)` accepts `expected_geography` with
release_id/hierarchy_sha256/reference footprints_sha256, `footprints[]`, and
`retirements[]`; at most200 rows/1 MiB. Selection rows contain stable id,
version_id or null, source_id, valid_from/to, direct/derived/reference method,
status, example flag and exact TEXT metadata. They can select only published
complete products within both source and product support intervals. Unknown
and disputed null claims retain ordinary deterministic precedence.

The SQL-sealed receipt validates current geographic pins, immutable identities,
source/example bounds, no-year-zero integral dates, retirement-aware equal
precedence overlaps and replacement completeness. Corrections retire first,
insert replacements, seal the receipt, then add their ingestion. PostgreSQL
uses shared advisory transaction lock807245315,1; all API changes contribute to
the existing ingestion revision. Retrying identical bytes retains the original
receipt, while changed bytes under an existing ID fail atomically.

`footprintSelectionAt(db, year, {releaseId,examples,expectedRevision})` returns
one compact descriptor with version/header/media IDs, source pointer, claim,
release pins and revision. Its status is dated, unknown, or reference; unknown
retains explicitly labeled reference context. It refuses unpublished versions
and a changing revision. Large legacy source metadata is explicitly truncated
in this compact reader and remains available in original evidence storage.
`footprintVersionPage`, `footprintWithdrawalsPage` and `footprintEvidence` provide
bounded catalog/withdrawal/history reads; withdrawn selections never render.

## Attribute and browser integration contract

`footprintAttributeEligibility(record, context)` is a pre-resolution predicate:
remove stale known claims before shared attribute precedence; retain their
original evidence. Null claims stay eligible and keep their precedence. Known
claims require matching territorial_scope.location_sha256 and/or
territorial_scope.footprints_sha256 (every supplied pin must match).
A direct claim can cross versions only with explicit sourced continuity whose
version/source/evidence hash/location also occurs in the caller's verified
`continuityProofs`; metadata alone cannot grant continuity. An unscoped legacy
claim is allowed only under an explicitly matching legacyReferenceSha256 and
reference geography. Never silently reuse old majority/environment assignments
on changed footprints.

The worker/client must attach the selected descriptor at the same revision as
all attributes/membership/existence/withdrawals; all readers must receive the
same expected revision. Grid bytes are fetched through authenticated media
routes, checked against compressed/decoded hashes, and cached by version/grid
hash/dictionary hash. An actual footprint switch loads/uploads one fixed grid;
subsequent navigation reuses it. Membership-only changes update ancestor/border
mapping and do not rebuild or upload ownership. These browser invariants are an
integration requirement, not something the service-only tests claim to prove.

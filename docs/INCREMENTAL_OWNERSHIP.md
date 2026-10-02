# Incremental historical ownership preparation

`scripts/prepare-ownership-incremental.py` stages a new compact ownership-v2 corpus after an explicitly receipted location footprint migration. It does not change published data, the atlas database, source geometry, or the original overlap cache. Geographic names/parents alone do not change ownership footprints and require no spatial derivation.

The reuse rule is strict: the stable location ID, raw geometry fingerprint, canonical archived-algorithm WKB fingerprint and every supported non-example dated footprint must match. Every Cliopatria input hash and the exact executed WGS84 algorithm receipts must also match. Changed political sources require full preparation; a new global hash is never stamped onto old intersections. A removed ID is archived, not renamed into a successor or assigned its attributes.

## Explicit inputs

Before and after snapshots can be FeatureCollections, feature arrays, or world-index manifests whose relative parts still exist. Capture the before snapshot before modifying source geometry. These snapshots must retain the exact stable IDs and original coordinates. Names and geographic parents are irrelevant to the footprint comparison. The supplied reference and dated geometries must be independently approved applicable **land** footprints. Raw administrative polygons can include marine territory; this wrapper does not establish coastlines or silently treat all such water as land. Record land/coastline provenance in the migration evidence before derivation.

Dated footprint files contain either non-example rows `[location_id, valid_from, valid_to, geometry]`, with geometry as GeoJSON or a JSON string, or objects with `location_id`, `valid_from`, `valid_to`, `geometry` and an explicit Boolean `is_example`. Example objects are excluded. Supported intervals are half-open, never use year zero, and must not overlap for the same location. The before fingerprint must match the original prepared index.

A migration receipt records the exact before/after published footprint hashes, `changed_ids` (existing IDs with changed geometry or dated footprints), `removed_ids`, `added_ids`, inspected `source_evidence`, and explicit lineage `relationships` with `before_ids`/`after_ids`. Relationships describe identity lineage only. They do not transfer historical ownership, populations or other attributes. Independently approve source geometry and semantic purpose before preparing this receipt; the preparation script cannot establish historical/geographic truth merely from a hash.

```json
{
  "before_footprints_sha256": "exact-old-published-footprint-hash",
  "after_footprints_sha256": "exact-new-published-footprint-hash",
  "changed_ids": [],
  "removed_ids": ["old-location-id"],
  "added_ids": ["replacement-location-id"],
  "relationships": [{
    "before_ids": ["old-location-id"],
    "after_ids": ["replacement-location-id"],
    "kind": "source-backed-merge"
  }],
  "source_evidence": [{
    "url": "inspected-source-url",
    "source_sha256": "pinned-source-geometry-hash"
  }]
}
```

The published hash uses the existing Node `JSON.stringify`/`localeCompare` contract. Python serialization must not be substituted, because number formatting and sort order can differ. Per-location fingerprints are independently recorded in the staged identity map.

```bash
python scripts/prepare-ownership-incremental.py \
  --before /absolute/path/to/before/world-index.json \
  --after /absolute/path/to/after/world-index.json \
  --before-boundaries /absolute/path/to/before-boundaries.json \
  --after-boundaries /absolute/path/to/after-boundaries.json \
  --receipt /absolute/path/to/migration-receipt.json \
  --ownership /absolute/path/to/original/ownership-history \
  --source /absolute/path/to/pinned/cliopatria \
  --output /absolute/path/to/new/staged-ownership
```

The output must be a fresh directory outside the original ownership tree. Do not point it at `data/ownership-history`.

## Derivation and bounded storage

The wrapper imports the **hash-verified archived** `majority.py` and `ellipsoidal_area.py` helpers from the original execution receipt. It retains the original execution/initial execution proofs and archives its own wrapper separately. It streams political source chunks, keeps overlap/source geometry in an ephemeral SQLite lookup, and derives only changed/new IDs. It tests every source geometry against the union of each applicable reference and dated footprint. Reference candidates and additional dated-footprint candidates retain the original preparation's deterministic record order.

Derivation uses the same WGS84 latitude-strip surface integral and antimeridian normalization as full preparation. All same-polity source polygons are unioned. A winner must cover more than 50% of the entire applicable location land area, with the same published numerical tolerance. Contradictory overlap resolves to disputed, incomplete coverage remains in the denominator, and no-majority cases have a null owner. Dated footprint overrides change the denominator and candidate coverage only during their supported intervals. Uncovered years are never carried forward. Direct location ownership evidence remains the resolver's separate higher-precedence input; this script does not migrate or overwrite it.

Original owner, label, source-record and evidence dictionaries retain their existing numeric indices. New labels/evidence append after them. Compact interval tuples for unchanged IDs remain identical. Entire unaffected gzip parts are copied byte-for-byte; parts containing changed/removed IDs are filtered without changing the retained tuples. Additional evidence files may have variable lengths: the existing readers/runtime compiler flatten parts in order, without assuming every part has 20,000 rows.

An explicit `location-identity-map.json.gz` records every original/current ID, old sorted index, new sorted index, classification and both geometry/date fingerprints. Computation never treats an old positional index as a new location identity.

## Staging, archives and publication

The wrapper verifies source and asset hashes, exact before/after location coverage, unique IDs, compact interval validity and evidence indices, and **exhaustively compares every reused location's serialized interval tuples** against the original. Only after these checks does it copy the temporary result to the requested staging directory.

`archive-index.json` preserves the original index and original interval tuples for removed and changed IDs. Its evidence still uses the unchanged original dictionary prefix. Old identities and source/history archives remain immutable. A changed-ID archive does not mean its original intervals should be carried into the new footprint.

The staged index adds `incremental_preparation` receipts: original index hash, wrapper hash, migration receipt hash, before/after footprint/date hashes, identity map hash, reused/derived interval counts, exact source scan count and archive path. These receipts do not replace the original exact algorithm proofs.

The result is **not automatically published or installed**. Before replacing live assets, regenerate the century transport with `scripts/prepare-ownership-runtime.py` against this staged ownership directory; rebuild reference summaries and the fixed grid if geography changed; validate hierarchy/geometry/coverage and static/server consistency; preserve the original corpus; then perform the reviewed publication migration. Browser navigation must continue to reuse prepared grid ownership textures.

## Verification

Run `python test/ownership-incremental.py`. Synthetic cases exercise strict majority, same-polity unions, competing claims, partial coverage, source gaps, latitude-dependent area, antimeridian geometry, dated overrides, example exclusion, source/algorithm/receipt invalidation, removed-ID archives, exact dictionary/row preservation, old/new sorted-index mapping and actual century-runtime decoding.

The no-change full-corpus check was executed in a separate scratch staging directory: **49,614 location IDs, all 6,834,664 interval tuples and all 1,434,173 evidence tuples were preserved**, with byte-identical original gzip ownership/evidence parts, zero political geometry scans/spatial derivations, and the original index unchanged. The result demonstrates exhaustive reuse/preservation; it does not certify a future geometry migration or replace its staging/publication gates.

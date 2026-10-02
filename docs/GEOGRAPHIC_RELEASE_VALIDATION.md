# Geographic reference release validation

Geographic releases preserve the original entity registry and existing historical records. A release supplies current reference names, adjacent-tier memberships, active status, and an explicit crosswalk. A reviewed geometry change requires a separate, independently validated, hash-pinned migration receipt; it cannot become a names-only migration by retaining stable IDs. Structural publication remains separate from semantic geographic approval. Open boundary and descendant reviews remain open.

## Preparation API

```js
await prepareGeographicRelease({
  data: 'data',                       // Immutable catalog, decisions and evidence
  geographyData: 'data',              // Independently selected geography snapshot
  output: 'data/geographic-releases',
  referenceDate: '2026-10-01',
  reviewedVersion: 2,
  geometryManifests: null,            // Ordered before-to-after proof manifests
  metadataMigrations: null,          // Additional name/membership-only receipts
  registryManifests: [],              // Earlier release indexes for registered IDs
});
```

The CLI accepts `--data`, `--geography-data`, `--output`, `--reference-date`, and `--reviewed-version`. Repeat `--geometry-manifest`, `--metadata-migration`, or `--registry-manifest` for multiple inputs. With the current data, preparation discovers the source-repair evidence manifest and the macro-boundary metadata receipt. Explicit arrays override discovery. Geometry manifests must follow migration order, starting at the original baseline. An independently staged `--geography-data` directory needs `hierarchy.json`, `world-index.json`, and the world parts named by that index. Preparation reads those inputs and writes only the selected release output directory.

When source-backed land creation follows earlier metadata migrations, pass an explicit `--identity-proof-sequence FILE`. The file contains `{"version":1,"steps":[{"type":"geometry","sha256":"manifest digest"},{"type":"metadata","sha256":"receipt digest"},...]}`. Each digest is the exact SHA-256 of its supplied geometry manifest or metadata receipt bytes. The programmatic option is `identityProofSequence`. All provided proofs must appear exactly once, with geometry and metadata inputs each preserving their own declared order. Missing, duplicate, changed or reordered pins reject preparation.

For the retained version-3 chain followed by new land, the identity sequence is: original geometry repair, macro-boundary metadata, macro repairs, macro area splits, macro region splits, then the new creation manifest. Later additions can have further metadata steps between them. Independent reverse footprint reconstruction still validates the complete geometry chain separately; the identity sequence does not waive geometry, source, archive, catalog or historical-preservation checks.

At a pure creation step, the hierarchy snapshot must retain the exact existing chronological records. The sole generated-field update permitted is `metadata.child_count`, and only when its original and new values equal independently counted immediate members before and after the addition. Names, parent IDs, tiers, source/evidence metadata and retired identities cannot be rewritten by a creation snapshot. Complete adjacent-tier chains and nonempty groups are checked after each geometry step.

The canonical sequence hash participates in the release identity and is retained with the sequence in source metadata. Existing preparations without mixed creation/metadata history retain their prior release-key behavior. This change only prepares immutable products; it does not run schema/provider migrations or publish a Site.


For subsequent releases, supply previously registered release indexes using `--registry-manifest`, increase `--reviewed-version`, and choose the actual reference date. Previously introduced entity definitions retain their original source and immutable registry fields. They are not reimported with a new source. The original version-1 baseline retains its identity, reference date, entity inventory, membership hash, and original footprint hash across later releases.

## Geometry and identity proof contract

Each geometry manifest pins every included archive by SHA-256, including the migration receipt and original features. Archive paths must stay inside the evidence directory. Optional uncompressed hashes are checked as well. Source evidence requires inspected source URLs and reproducible source hashes; the release retains the complete manifest and receipt hashes. Source licensing, suitability, and independent geometry validation remain upstream review responsibilities, not inferred from a declared hash.

The receipt must declare independent geometry validation and zero historical transfer. Its `before_footprints_sha256` and `after_footprints_sha256` must agree with the manifest. Four unique, disjoint ID sets exhaust the applicable inventories: `changed_ids`, `removed_ids`, `added_ids`, and `reused_ids`. Every changed or retired identity needs its exact original feature in `archives`; every new location needs a precise sourced name and parent in `new_entities` or `added_features`.

Every changed identity must occur in an explicit relationship. Each relationship names exhaustive `before_ids` and `after_ids` and declares `history_transfer: false`. Equal before/after inventories mean retained identities. A single endpoint supports an unambiguous merge or split. A many-to-many replacement must additionally provide exhaustive, unique `identity_pairs` with `before_id` and `after_id`; aggregate counts never justify guessing a Cartesian crosswalk. The synthetic 111-retired/107-new replacement test exercises this contract, not an approved North American migration.

Validation reconstructs the complete original geography by reversing the ordered receipts. It checks the full after inventory and full geometry hash at each step, restores exact archived originals, and checks the full before inventory and full geometry hash. The final reconstructed inventory must equal the immutable original active-location catalog, and its geometry must equal the original footprint pin. This validates unchanged shapes too: an unreceipted mutation to any reused location fails. Added, retired, renamed, or reparented units also must match the reviewed identity receipts exactly. Every active unit must have exactly one active parent at the adjacent tier.

Retired entities remain registered and become inactive only in the new reference release. Their historical claims stay on their original IDs. Merges, splits, replacements, and retained-ID footprint changes appear explicitly in the crosswalk with receipt/source proof hashes. Preparation does not copy historical records onto a surviving or newly created identity.

## Exhaustive local service gate

```sh
node --test test/geographic-release-preparation.mjs
```

The default test uses the current `data` geography. `ATLAS_REVIEWED_GEOGRAPHY` can select an explicit staged snapshot. It regenerates the complete release set in a temporary directory and compares matching release outputs against the prepared assets. Every import batch has a pinned byte hash, at most 200 rows, and at most 1 MiB; the service limit is 250 rows. Original catalog batches and the original archive must retain their hashes.

The integration test uses SQLite with foreign keys enabled and every real `drizzle/*.sql` migration. Its D1 adapter invokes the actual record import, release staging, release finalization, paging, and profile services. It imports the complete original catalog and stages every generated batch. Staged memberships remain invisible until publication. Every original entity and source column is compared with its original catalog record. A test-only dated name and population attached to a retired location survive both releases on that original ID; the merge target does not receive the population automatically.

For both releases, independent canonical SHA-256 reconstruction checks every membership, every active adjacent-tier parent, every tier count, every location ID, and every crosswalk row. Both complete release inventories are read back across public pagination. The actual service validates all stored rows before publication. Older releases remain explicitly selectable, profiles expose current reference overlays alongside original registry fields, dated names retain precedence, and published membership mutation or release deletion fails.

Separate tests reject a same-ID real-world footprint mutation, tampered original archives, omitted identity dispositions, unvalidated geometry, historical transfers, and aggregate-only many-to-many replacements. A later-release test verifies prior registered identities are reused and the baseline manifest remains exactly unchanged.

This gate does not perform a hosted deployment, remote D1 upload, browser navigation benchmark, or independent semantic approval of source boundaries. Those are separate release gates.

## Recorded current dataset

The baseline retains 84,733 geographic registry identities, including archived units, and 49,614 active locations. Its counts are 5,220 provinces, 489 areas, 66 regions, 29 subcontinents, and six continents. Its original footprint hash is `1c8c1584520d7360375c8ac79f12fe840dd8a47efb10f3d05c8517689667dd58`.

The reviewed release has 49,589 active locations, 5,133 provinces, 471 areas, 66 regions, 29 subcontinents, and six continents. It introduces 25 geographic group identities, retains 84,758 membership records, and records 573 crosswalk changes across 856 bounded preparation batches. The source repair accounts for 27 retained-ID footprint changes and 25 retired locations; no historical records are transferred. The reviewed footprint hash is `5d7236fe7e9d2f83c07c0b5cc1d5e703bf685f860fd49c850edd18eea27c61a8`. These counts describe the prepared structural release and do not declare all semantic reviews complete.

Verified on 2 October 2026 against the installed current geography: all 14 tests passed in 78 seconds, including full real-D1 publication and preservation checks. The prepared reviewed release ID is `geography:review:44acd708dd8aae06e3643b252faf91c04c49b54bb93b705a8c4662ec8568755a`. The release index SHA-256 is `163f3329262f2a5db99e07c65b53e31b9a97cdbdaf57ea62ea79e874ea7e9baa`; its source-repair evidence manifest pin is `ae64e938771d28e6cbd9d79e97f83b1893bb43c99c0e22e50145043293cbb4c1`. No remote publication or browser validation is asserted by this local gate.

## Resumable private bootstrap

`scripts/bootstrap-geographic-release.mjs` defaults to six concurrent bounded batches. Set `ATLAS_IMPORT_CONCURRENCY` to an integer from 1 through 8 to change the bound. Source and entity tiers remain sequential so references exist before dependent imports. A failed batch stops new dispatch and waits for in-flight requests to finish before failing the run. Credentials still arrive on hidden terminal stdin and are never printed.

An absent or staged release is replayed using the same pinned ingestion IDs and all bounded stage batches, then finalized. Existing release identity, source, version, date, counts, and five content/geography hashes are checked before any geographic staging. Published releases are verified and skip staging. Readers may intentionally hide staged releases; retry works in that case too because service-side ingestion IDs are idempotent. Historical claims and the original identity registry remain unchanged.

`node --test test/geographic-bootstrap.test.mjs` checks an actual-D1 interrupted partial stage, successful retry with both visible and hidden staged state, concurrency bounds, published retry, existing staged/published hash mismatches, and preservation of historical/source/identity rows. This helper change needs no application redeployment.

Migration archive retention deduplicates uploads by content SHA-256. The first sorted source path supplies the immutable media name and MIME type on every retry. Every original source path remains an explicit receipt row with its own `path` and the shared `canonical_path`, media ID, digest, and byte count. Thus byte-identical before/after evidence can share one persistent media object while retaining both aliases. The bootstrap regression verifies one upload per unique digest, complete aliases, deterministic metadata on reversed-order retry, and rejection of an incorrect media digest/size. All four bootstrap regressions pass; no media metadata or historical claim is rewritten to repair an alias collision.

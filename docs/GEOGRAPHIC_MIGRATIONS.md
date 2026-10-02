# Geographic reference revisions

A new administrative source can replace one atlas territory with several finer territories. That is a revision to the atlas reference, not evidence that the historical territory split on the publication date. The old and new location IDs remain distinct. Renaming a retained territory keeps its ID; changing its parent chain does not create a new historical owner or identity.

`scripts/audit-geographic-migrations.py` compares the retained pre-plan geography with every current location. It records every new, retired, and changed retained ID. It also checks every archived location already stored in SQLite, including identities superseded before this plan. The script opens SQLite read-only and writes only the migration review and immutable gzip archive.

Run the audit from the repository root:

```sh
python scripts/audit-geographic-migrations.py
```

The audit needs `.cache/plan-baseline/{world-index.json,hierarchy.json,geography.tar.gz}` and `.cache/plan-original-records.json`. These are preserved revision inputs, not publicly reconstructed historical evidence. The report pins their hashes and those of the current geography. The archive provides the original archived location geometries, IDs, metadata, parent units, and original historical records, with source licenses retained on each location. Missing license metadata and incomplete archived chains remain explicit report findings.

Relationships use WGS84 ellipsoidal area. Rings are normalized across the antimeridian and edges densified to at most 0.1 degree before measuring. Each relationship records the share of the predecessor and the share of the successor represented by their intersection. Tiny numerical slivers below `max(0.01 m², 1e-9 × predecessor area)` are excluded. Current footprints undergo their own exhaustive interior-overlap check. Uncovered predecessor land is recorded; the script does not assign it to the nearest location.

`data/geographic-migration-review.json` separates baseline identity accounting, changed parent/name/geometry records, new-location predecessor relationships, and all archived-location successor relationships. `data/geographic-migration-archive.json.gz` retains original geometries and reference metadata. Neither artifact assigns a historical effective year. A footprint relationship is source evidence for cartographic continuity; it does not establish administrative, political, demographic, or cultural succession.

Original states and entity-history records are checked by their primary keys and complete row contents against the pre-work snapshot. Additional sourced records are permitted. Original records must remain on their original IDs, even when those IDs are archived. Ownership, population, culture, religion, rank, habitation, and dated names must not be copied to a new ID merely because geometries overlap. A transfer needs separate evidence and provenance.

## Recommended database representation

Keep cartographic reference relationships separate from dated `entity_links`. A `geographic_reference_replacements` table should contain predecessor and successor location IDs, source revision hash, assignment method, source citation, overlap shares, and uncertainty. It should allow many predecessors and successors, require references to retained location identities, and have no inferred effective-year column. Record actual researched historical splits or mergers in dated `entity_links` only when their dates and identities are supported by a source.

The current report and immutable archive provide the crosswalk and original evidence without automatically modifying historical records. Their existence does not close semantic review: an old or new territory can be fully accounted for while its granularity or parent grouping still needs research.

## Validated revision snapshot

The current audit accounts for all **45,983** baseline locations and **49,614** current locations. It retains **45,616** IDs, retires **367**, and introduces **3,998**. After the sourced macro-reference corrections, 743 retained IDs have name, parent-chain, or ancestor-name changes. The macro-correction ledger documents 713 affected locations and 83 geographic groups; the earlier revision accounted for another 30 changes. All 367 retired baseline footprints are fully represented by current member footprints at the documented numerical tolerance.

The separate archive contains **19,050** older inactive identities with complete retained parent chains and recorded licenses. Its gzip size is **10,765,139 bytes**. The crosswalk exposes **2,522** older-footprint differences: 1,999 have less than or equal to 1% uncovered land and 523 have larger differences. Several extreme relative differences concern tiny residual geometries left by earlier topology reconciliation, such as a 0.70 km² Sanaga-Maritime fragment; this is not evidence that the entire modern district vanished. These historical atlas-reference discrepancies remain open evidence to investigate.

All nine original state rows and six original entity-history rows passed exact primary-key/content comparison. The 9,301 additional settlement population estimates do not replace those rows. There were zero automatic record transfers.

To avoid repeating the same citation thousands of times, the report uses `source_index` references into its `sources` array. Relationship tuple columns are declared in `relationship_columns`; successor tuples contain `[id, predecessor_share, successor_share, overlap_km2]` and predecessor tuples contain `[id, successor_share, predecessor_share]`. Several archived reference revisions can cover the same successor; their individual shares must not be summed as though they were mutually exclusive contemporary territories.

## Fresh database restoration

`restoreReferenceArchive(db)` in `reference-archive.mjs` restores missing archived units and inactive locations before restoring the original state and temporal record IDs. It reads the gzip archive, keeps all existing active location names/geometry/membership, inserts missing adjacent-tier units in parent-first order, and creates missing settlement identities from their exact retained records. Original reference-owner labels are retained separately from political ownership.

A fresh seed must first import current geography without illustrative states, then restore the archive, then run the usual reference migrations and add any missing illustrative fixtures. Existing databases can call restoration idempotently. Conflicting original record IDs raise an explicit error; the savepoint rolls back the restoration instead of overwriting user evidence. No historical links or effective dates are manufactured.

Validation: `node --test test/reference-archive.test.mjs` passes four tests covering a fresh restored archive, exact original rows, idempotence, preservation of existing active territory geometry/name/owner context, explicit ID collisions, and atomic rollback.

To refresh only name and parent-chain changes after a correction that leaves location footprints unchanged, run `python scripts/audit-geographic-migrations.py --reuse-spatial`. This verifies the macro-correction footprint hash against prepared reference coverage, updates every retained-ID chain/name comparison and every new-ID chain, and reuses all 19,050 stored spatial relationships. The report separately pins macro-correction, hierarchy, and location-part hashes; it does not imply changed geometry or dated historical membership.

The audit now reuses the immutable licensed geometry archive whenever archived footprint identities and original historical records remain unchanged. Later renames of shared unit IDs never replace the original archive's group names or parent chains. Changed archived footprints require an explicit additional archive revision rather than overwriting the original snapshot.

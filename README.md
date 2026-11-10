# WorldAtlas

The settled project contract is in [the data strategy](docs/data-strategy.md).

## Published V8 map

The [map viewer](web/viewer/README.md) renders the V8.0 map from two
checksum-verified row-run streams. The Cloudflare Worker serves the viewer and
streams from the `worldatlas` R2 bucket.

## Pipeline code

- [Prepare structured geography](scripts/raw-to-structured/) from raw sources. These tools reconstruct and verify boundary geometry and other inputs for review and registration in Neon.
- [Build the map](scripts/map-build/pipeline/README.md) from selected Neon records and the raw R2 inputs the build reads directly. This includes the physical land and water grid, land and water assignment, and final composition.

Neon records the sources and reasoning for individual geographic decisions. The code guides explain how to produce and use those records.

## Rebuild V8

Run the [V8 pipeline](scripts/map-build/pipeline/README.md) from the repository root.

```bash
python3 scripts/map-build/pipeline/run_pipeline.py scripts/map-build/pipeline/config.json \
  --work-dir /absolute/path/to/worldatlas-work
```

The configuration selects versioned geographic decisions and source records in
Neon. The pipeline downloads the raw bytes from R2 and builds the physical grid,
then assigns land and water categories. The final grid has 131,072 columns and
54,614 rows. The pipeline guide covers credentials, the GDAL and PROJ versions
for exact reproduction, and stage timings.

## Preview and publish

The [release workflow](scripts/map-build/pipeline/README.md#stage-review-and-publish-a-release)
puts each candidate at its own address while the homepage serves the published
map. Approval records the exact candidate. Publishing serves its existing viewer
and map files at the homepage.

Deploy the Cloudflare Worker with `wrangler deploy`. The Worker uses the
`ATLAS` binding to the `worldatlas` R2 bucket.

`atlas.map_release_objects` tracks the two R2 objects for each versioned
row-run map. The `rows` stream stores row offsets and the `runs` stream stores
run endpoints and category codes. Register both in one transaction after
verifying the stored byte lengths and both sets of hashes. The table tracks
outputs separately from the source catalog. See
the [initial database schema](database/migrations/001_initial_schema.sql).
The `worldatlas-v8-viewer-inventory` document in
`atlas.structured_documents` records the deployed viewer's seven R2 objects,
their repository paths, byte lengths and SHA-256 hashes. The source catalog
tracks raw data objects, including the parts of source archives.

## Entity registry

The [initial schema](database/migrations/001_initial_schema.sql) defines stable entity
IDs, revisioned names and parent relationships, and the bindings from map
category codes to entities. Use the registry revision selected by the
decision snapshot.

Apply the [initial schema](database/migrations/001_initial_schema.sql) to an
empty database. Load the source catalog, editable decisions, and release
records separately.
Run the [database tests](database/tests/) with `bash database/tests/run.sh`.
Have PostgreSQL's `initdb`, `pg_ctl`, and `psql` on your path. The runner starts
a temporary local database, installs the schema, and runs the database checks.

Export a registry revision from Neon with `scripts/map-build/export_entity_registry.sql`.

    psql -X -A -t -v revision=REVISION -f scripts/map-build/export_entity_registry.sql > registry.json

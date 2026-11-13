# WorldAtlas

The settled project contract is in [the data strategy](docs/data-strategy.md).

## Map viewer

The [map viewer](web/viewer/README.md) renders a published release from two
checksum-verified row-run streams. The Cloudflare Worker serves the viewer and
streams from the `worldatlas` R2 bucket.

## Pipeline code

The root [`environment.yml`](environment.yml) defines the shared Python
environment. It covers source imports, map building and their tests. Website dependencies
are managed separately in [`package.json`](package.json).

- [Import source geography](scripts/source-imports/) from raw sources. These tools reconstruct and verify boundary geometry and other inputs for review and registration in Neon.
- [Build the map](scripts/map-build/README.md) from selected Neon records and the raw R2 inputs the build reads directly. This includes the physical land and water grid, land and water assignment, and final composition.

Neon records the sources and reasoning for individual geographic decisions. The code guides explain how to produce and use those records.

## Build a map

Run the [pipeline](scripts/map-build/README.md) from the repository root.

```bash
PYTHONPATH=scripts/source-imports:scripts/map-build python3 -m map_build scripts/map-build/config.json \
  --work-dir /absolute/path/to/worldatlas-work
```

The configuration selects versioned geographic decisions and source records in
Neon. The pipeline downloads the raw bytes from R2 and builds the physical grid,
then assigns land and water categories. The final grid has 131,072 columns and
54,614 rows. The pipeline guide covers credentials, the GDAL and PROJ versions
for exact reproduction, and stage timings.

## Preview and publish

The [release workflow](scripts/map-releases/README.md)
puts each candidate at its own address while the homepage serves the published
map. Approval records the exact candidate. Publishing serves its existing viewer
and map files at the homepage.

Use the release command to publish the reviewed viewer and map files.
When changing the Worker's server code or configuration, deploy it with
`npx wrangler deploy`. Its `ATLAS` binding connects it to the `worldatlas` R2 bucket.

`atlas.map_release_objects` tracks the two R2 objects for each versioned
row-run map. The `rows` stream stores row offsets and the `runs` stream stores
run endpoints and category codes. Register both in one transaction after
verifying the stored byte lengths and both sets of hashes. The table tracks
outputs separately from the source catalog. See
the [initial database schema](database/migrations/001_initial_schema.sql).
`atlas.map_release_candidates` records each candidate's complete file manifest,
including its grid, viewer, generated config, and legend file. The legend
contains entity names, colors, and cell counts for that release. The source
catalog tracks raw data objects, including the parts of source archives.

## Entity registry

The [initial schema](database/migrations/001_initial_schema.sql) defines stable entity
IDs and colors, revisioned names and parent relationships, and the bindings from map
category codes to entities. Use the registry revision selected by the
decision snapshot.

Apply the [database migrations](database/migrations/) in order to an empty
database. Load the source catalog, editable decisions, entity colors, and
release records separately.
Run the [database tests](database/tests/) with `bash database/tests/run.sh`.
Have PostgreSQL's `initdb`, `pg_ctl`, and `psql` on your path. The runner starts
a temporary local database, installs the schema, and runs the database checks.

## Viewer tools and tests

Use Node 22 or newer. From the repository root, install the locked dependencies
and run the Node tests.

```bash
npm ci
npm test
```

The [viewer guide](web/viewer/README.md) covers the browser tests and renderer.

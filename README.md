# WorldAtlas

The settled project contract is in [the data strategy](docs/data-strategy.md).

## Map viewer

The [map viewer](web/viewer/README.md) renders a published release from two
checksum-verified row-run streams. The Cloudflare Worker serves the viewer and
streams from the `worldatlas` R2 bucket.

## Pipeline code

The root [`environment.yml`](environment.yml) defines the shared Python
environment. It covers source imports, map building and their tests.
The root [`pyproject.toml`](pyproject.toml) installs the `worldatlas` package and
its three commands. Website dependencies are managed separately in [`package.json`](package.json).

Install [Micromamba](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html),
then create the environment and enter a shell using it:

```bash
micromamba create -y -n worldatlas -f environment.yml
micromamba run -n worldatlas python -m pip install --no-deps -e .
micromamba run -n worldatlas bash
```

Run the commands below from the repository root in that shell. For exact
physical-grid reproduction, complete the [GDAL setup](src/worldatlas/map_build/README.md#exact-physical-rasterization).

Geographic and numerical libraries use tested exact versions because upgrades
can change map coordinates or cells. Python accepts patch updates within 3.13;
the database tests support PostgreSQL 17 and 18. Storage/database clients and
review-image tools accept compatible updates. Boto3 selects its own matching
Botocore dependency. Each build records the actual runtime versions. CMake is
needed only when compiling GDAL and stays outside the runtime environment.

Set `NEON_DATABASE_URL` to the direct connection URL for the existing working
`worldatlas` database. The [database guide](database/README.md) explains how to
identify the working branch and inspect its construction records.
For R2, reuse the `worldatlas-r2` profile in `~/.aws/credentials`, or set
`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. With the profile:

```bash
export AWS_PROFILE=worldatlas-r2
export PROJ_NETWORK=OFF
```

Set the database URL in your shell or secret manager. Credentials stay outside
GitHub and Neon construction records. Connector logins are separate from the
credentials used by these Python commands.

- [Import source geography](src/worldatlas/source_imports) from raw sources. These tools reconstruct and verify boundary geometry and other inputs for review and registration in Neon.
- [Build the map](src/worldatlas/map_build/README.md) from selected Neon records and the raw R2 inputs the build reads directly. This includes the physical land and water grid, land and water assignment, and final composition.

Neon records the sources and reasoning for individual geographic decisions. The code guides explain how to produce and use those records.

## Build a map

Run the [pipeline](src/worldatlas/map_build/README.md) from the repository root.

```bash
worldatlas-build src/worldatlas/map_build/config.json \
  --work-dir /absolute/path/to/worldatlas-work
```

The configuration selects versioned geographic decisions and source records in
Neon. The pipeline downloads the raw bytes from R2 and builds the physical grid,
then assigns land and water categories. The final grid has 131,072 columns and
54,614 rows. The pipeline guide covers credentials, the GDAL and PROJ versions
for exact reproduction, and stage timings.

## Preview and publish

The [release workflow](src/worldatlas/map_releases/README.md)
puts each candidate at its own address while the homepage serves the published
map. Approval records the exact candidate. Publishing serves its existing viewer
and map files at the homepage.

Use the release command to publish the reviewed viewer and map files.
When changing the Worker's server code or configuration, deploy it with
`npx wrangler deploy`. Its `ATLAS` binding connects it to the `worldatlas` R2 bucket.

`atlas.map_releases` stores each release's immutable R2 asset manifest: map
streams, viewer, configuration, legends and frozen inputs. `atlas.map_publications`
connects official versions to those releases and identifies the homepage.
The legend contains entity names, colors and counts for that release. The source
catalog tracks raw files, including archive parts.

The grid's `rows` stream stores row offsets; `runs` stores run endpoints and
category codes. Both are registered together in the manifest after their stored
and decoded checksums are verified. See the
[database guide](database/README.md).

## Entity registry

The [initial schema](database/migrations/001_initial_schema.sql) defines stable entity
IDs and colors, revisioned names and parent relationships, and the bindings from map
category codes to entities. Use the registry revision selected by the
decision snapshot.

Apply the [initial schema](database/migrations) only to an empty database.
The working database is already initialized. The [database guide](database/README.md)
covers existing-database upgrades and loading data separately from the schema.
Run the [database tests](database/tests) with `bash database/tests/run.sh`.
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

## Continuous integration

[Checks](.github/workflows/ci.yml) runs every fast automated suite on each PR
update and on manual runs:

- Python source-import, map-building, release and SQL database suites concurrently on macOS and Linux.
- Node and Chromium browser tests on Linux.

CI tests a regular installation, including its SQL and configuration resources.
Each database-using suite has its own disposable database on one temporary server
per OS job. The website job runs alongside the Python jobs. CI caches installed
environments, uses local fixtures, and needs no cloud credentials. The website job uses
Chrome already installed on GitHub's runner. Its Node and browser suites also
run concurrently. New pushes cancel superseded runs.
Documentation-only updates also run the checks. Full-size map builds and
geographic review remain separate.

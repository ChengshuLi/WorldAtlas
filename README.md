# WorldAtlas

WorldAtlas builds and publishes versioned maps from raw source data and editable geographic records in Neon.

[Open the live map](https://worldatlas.chengshu-li-web.workers.dev/) · [Read the data strategy](docs/data-strategy.md)

## Use

### Pipeline code

The root [`environment.yml`](environment.yml) defines the shared Python environment. It covers source imports, map building and their tests. The root [`pyproject.toml`](pyproject.toml) installs the `worldatlas` package and its three commands. Website dependencies are managed separately in [`package.json`](package.json).

Install [Micromamba](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html), then create the environment and enter a shell using it:

```bash
micromamba create -y -n worldatlas -f environment.yml
micromamba run -n worldatlas python -m pip install --no-deps -e .
micromamba run -n worldatlas bash
```

Run the commands below from the repository root in that shell. For exact release replays, use the environment documented in the [restored release archive](src/worldatlas/map_releases/README.md#restore-inputs).

Geographic and numerical libraries use tested exact versions because upgrades can change map coordinates or cells. Python accepts patch updates within 3.13. Pydantic uses a fixed version so it generates the same JSON Schema in each environment. Storage and database clients accept compatible updates. Boto3 selects its own matching Botocore dependency. Each build records the actual runtime versions. CMake is needed only when compiling GDAL and stays outside the runtime environment.

Set `NEON_DATABASE_URL` to the direct connection URL for the working `worldatlas` database. Use the working branch's connection details from your Neon project. See the [database guide](database/README.md) for its schema. For R2, reuse the `worldatlas-r2` profile in `~/.aws/credentials`, or set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. With the profile:

```bash
export AWS_PROFILE=worldatlas-r2
export PROJ_NETWORK=OFF
```

Set the database URL in your shell or secret manager. Credentials stay outside GitHub and Neon construction records. Connector logins are separate from the credentials used by these Python commands. On the configured Mac, the existing direct URL is stored privately in `~/.config/worldatlas/neon-connection`. Load it without printing it:

```bash
export NEON_DATABASE_URL="$(cat "$HOME/.config/worldatlas/neon-connection")"
```

- [Import source geography](src/worldatlas/source_imports) from raw sources. These tools reconstruct and verify boundary geometry and other inputs for review and registration in Neon.
- [Build the map](src/worldatlas/map_build/README.md) from selected Neon records and the raw R2 inputs the build reads directly. This includes the physical land and water grid, land and water assignment, and final composition.

Neon records the sources and reasoning for individual geographic decisions. The code guides explain how to produce and use those records.

### Build a map

Run the [pipeline](src/worldatlas/map_build/README.md) from the repository root.

```bash
worldatlas-build src/worldatlas/map_build/config.json \
  --work-dir /absolute/path/to/worldatlas-work
```

The pipeline freezes working geographic decisions and exact source records from Neon. The pipeline downloads the raw bytes from R2 and builds the physical grid, then assigns land and water categories. The final grid has 131,072 columns and 54,613 rows. The pipeline guide covers credentials, the GDAL and PROJ versions for exact reproduction, and stage timings.

### Preview and publish

Stage a completed build as a numbered candidate.

```bash
worldatlas-release stage v9.0-rc.1 \
  /absolute/path/to/worldatlas-work/run --viewer web/viewer
```

Review the preview at `/releases/v9.0-rc.1/index.html`, then publish the approved candidate.

```bash
worldatlas-release publish v9.0-rc.1
```

Publishing serves that bundle at the homepage and retires superseded candidates for the same version. The [release guide](src/worldatlas/map_releases/README.md) covers bundle contents and reproduction. Deploy changes to the Worker code or configuration with `npx wrangler deploy`.

## How it works

### Map viewer

The [map viewer](web/viewer/README.md) renders a published release from two checksum-verified row-run streams. The Cloudflare Worker serves the viewer and streams from the `worldatlas` R2 bucket.

### Entity registry

The [initial schema](database/schema.sql) defines stable entity IDs and colors, editable names and parent relationships, and the bindings from map category codes to entities. Each build freezes the working records before computation.

Apply the [initial schema](database/schema.sql) only to an empty PostgreSQL database with `pg_jsonschema` available. The working database is already initialized. The [database guide](database/README.md) covers existing-database upgrades and native test setup. Run the [database tests](database/tests) with `python .github/scripts/run_tests.py --suite database`.

## Code and tests

### Viewer tools and tests

Use the Node version in [`.node-version`](.node-version), which CI also reads. From the repository root, install the locked dependencies and run the Node tests.

```bash
npm ci
npm test
```

The [viewer guide](web/viewer/README.md) covers the browser tests and renderer.

### Python checks

From the project Python environment, run the same formatting, type and coverage checks as Linux CI. Set up local PostgreSQL first. [Database test setup](database/README.md#tests)

```bash
python -m pip install -e '.[checks]'
python -m ruff check src/worldatlas .github/scripts
python -m ruff format --check src/worldatlas .github/scripts
npx --yes pyright@1.1.414 --pythonpath "$(command -v python)"
python -m coverage erase
NUMBA_DISABLE_JIT=1 PROJ_NETWORK=OFF python -m coverage run .github/scripts/run_tests.py
python -m coverage combine
python -m coverage report
```

Coverage includes production Python lines and branches across the test subprocesses. Disabling Numba compilation for coverage lets the tool see which terrain paths ran. The macOS CI job runs those same tests with compilation enabled.

### Continuous integration

[Checks](.github/workflows/ci.yml) runs every fast automated suite on each PR update and on manual runs:

- Python source-import, map-building, release and SQL database suites concurrently on macOS and Linux.
- Production Python formatting, docstrings, annotations, and type checks alongside the Linux test suites, which enforce 100% line and branch coverage.
- Node and Chromium browser tests on Linux.

CI tests a regular installation, including its SQL and configuration resources. macOS and Linux both run the Python and database suites against native PostgreSQL. Each database-using suite has its own disposable database on one temporary server per OS job. CI caches installed environments and the native macOS extension, uses local fixtures, and needs no cloud credentials. The website job uses Chrome already installed on GitHub's runner and runs alongside the Python jobs. Its Node and browser suites also run concurrently. New pushes cancel superseded runs. Documentation-only updates also run the checks. Full-size map builds and geographic review remain separate.

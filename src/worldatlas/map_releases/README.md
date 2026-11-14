# Preview, publish and restore a map

Map building calculates cells. This command packages a completed build, stages a
numbered candidate and publishes that same candidate after review. Use the project
environment, `NEON_DATABASE_URL` and the R2 credentials used by map building.

```bash
worldatlas-release stage v9.0-rc1 \
  /absolute/path/to/worldatlas-work/runs/preview --viewer web/viewer
```

The preview is at `/releases/v9.0-rc1/index.html`. The homepage continues to show
the published release. Changed contents require a new candidate number.

## Release files and input archive

Each release has one R2 folder, `releases/RELEASE_ID/`, containing its viewer,
compressed map streams, generated configuration, legend and `inputs.json.gz`.
The archive holds the actual saved configuration, geographic selection,
construction settings, source catalog references, run identity and build report.
Run identity includes runtime versions and available source revision/setup
information. Resumed builds retain the recorded identities of their attempts.
Packaging reads the saved run, never today's editable geography in Neon.

Raw files remain under `sources/`, shared across releases. Their cataloged versions,
size and SHA-256 identify the bytes needed by each build. Keep any raw source
needed by working geography or a retained release.

Neon's `map_releases` row lists the release files and their R2 keys, sizes,
checksums and media types. Large input data belongs in the archive, not that row.
`map_publications` selects the final RC for each official version. Its homepage
pointer identifies which version is served at `/` through R2's `index.html`.

## Publish and retire previews

After the user reviews and approves the candidate:

```bash
worldatlas-release approve v9.0-rc1 --reviewer NAME
worldatlas-release publish v9.0-rc1
```

Publication verifies the files, points the homepage to that exact bundle and
removes superseded candidate folders/rows for the same version. Only the selected
RC is retained permanently. Candidates of a version still under development stay
available. Input files in active candidates are temporary review/build records.

Publishing does not rebuild or recolor the map. Interrupted publication or
candidate cleanup can be retried with the same command. Published versions remain
available and cannot be redirected to a different candidate. The Worker serves
only `/`, `/index.html` and `/releases/RELEASE_ID/...`; retired `/review/` URLs
and version shortcuts return 404.
Deploying the Worker itself is separate: `npx wrangler deploy`.

## Archived code

New build attempts capture the installed WorldAtlas source files and the project
`environment.yml`, `pyproject.toml` and README before computation. Staging includes
those captured bytes in `inputs.json.gz`; it does not copy code from the checkout
at staging time. Git history is not needed to recover them.

Each attempt's producer record identifies its source archive. Identical snapshots
are stored once per release; resumed attempts using different code retain each
snapshot. Keep code unchanged while an attempt runs; edits between attempts are
captured on resume. This does not add a restriction on resuming with changed code.

The snapshot includes source and setup definitions, not raw datasets, Git history,
Python or native-library binaries. Raw data remains in R2; the run records runtime
versions and hashes. Reproduction uses that recorded environment and the native
GDAL setup described in the archived map-building guide. The current source
snapshot adds approximately 0.5 MB compressed per distinct code version.

## Restore inputs

```bash
worldatlas-release restore-inputs v9.0-rc1 /absolute/path/to/restored-inputs
worldatlas-build /absolute/path/to/restored-inputs/configuration.json \
  --work-dir /absolute/path/to/worldatlas-work/replay \
  --selection /absolute/path/to/restored-inputs/selection.json
```

Restoration verifies the R2 archive and writes a new directory. Code snapshots
are extracted under `restored-inputs/code/CODE_ID/`, alongside configuration,
selection and run records. `run.json` connects attempts to their code IDs through
the source-archive checksums. To use a restored code snapshot:

```bash
cd /absolute/path/to/restored-inputs/code/CODE_ID
micromamba create -f environment.yml
micromamba activate worldatlas
python -m pip install --no-deps .
```

Follow its archived map-building README for the recorded native GDAL setup,
then run the build command above using the restored configuration and selection.
Compare its output with the archived release's recorded checksums. Use the
recorded code and environment when reproducing an older result. Source location changes
recorded by an archive are applied to the extracted configuration/selection;
original captured records and reports are preserved.

Historical backfills use the same archive format. They can contain supporting
records from older pipelines and notes describing unavailable configuration,
code or reports. They do not invent missing inputs from today's Neon records.
An archive without a modern `selection` requires its historical implementation;
the restore command still extracts all available records and notes.

Run tests with `python .github/scripts/run_tests.py --suite map_releases`.

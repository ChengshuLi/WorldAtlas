# Preview, publish and restore a map

Map building calculates cells. The release command packages a completed build, stages a numbered candidate and publishes that candidate after review. Use the [project environment and credentials](../../../README.md#pipeline-code). Staging and publishing require the direct `NEON_DATABASE_URL` so uploads and publication cannot overlap. Release commands use the project's R2 account and stage website bundles in `worldatlas`, the bucket served by the Worker.

```bash
worldatlas-release stage v9.0-rc.1 \
  /absolute/path/to/worldatlas-work/runs/preview --viewer web/viewer
```

The preview is at `/releases/v9.0-rc.1/index.html`. The homepage continues to show the published release. Changed contents require a new candidate number while a version is in review. Once a version is official, stage further changes under a new map version.

## Release files and input archive

Each release has one R2 folder, `releases/RELEASE_ID/`, containing its viewer, compressed map streams, generated configuration, legend and `inputs.json.gz`. The `rows` stream stores row offsets, and `runs` stores run endpoints and category codes. The manifest records checksums for both the stored files and the decoded streams.

The archive holds the actual saved configuration, geographic selection, construction settings, source catalog references, run identity and build report. Run identity includes runtime versions and available source revision/setup information. Resumed builds retain the recorded identities of their attempts. Packaging reads the saved run, never today's editable geography in Neon.

Raw files remain under `sources/`, shared across releases. Their cataloged identities, size and SHA-256 identify the bytes needed by each build. Staging requires the physical inputs to be embedded in the saved configuration or pinned in R2 so a rebuild can run on another machine. Keep any raw source needed by working geography or a retained release. After retiring previews, check the working inputs and all surviving archives again before removing a raw object and its Neon catalog row.

Neon's `map_releases` row contains the bundle ID, R2 bucket, manifest checksum and publication-state flags. The release command derives the folder path from the bundle ID. The folder's `manifest.json` lists file locations, sizes, checksums and media types. Neon pins the manifest, and the manifest pins the files.

`is_official` records the permanent selection of a release for a version. Neon prevents demoting or deleting an official release. `is_current` identifies the official release served at `/` through R2's fixed `index.html`. Staging sets both flags to false.

## Publish and retire previews

After the user reviews and approves the candidate:

```bash
worldatlas-release publish v9.0-rc.1
```

Publication verifies the files, points the homepage to that exact bundle and removes superseded candidate folders/rows for the same version. Only the selected RC is retained permanently. Candidates of a version still under development stay available. Preview retirement removes the release bundles and catalog pointers. Shared raw sources under `sources/` require a separate dependency check.

Publishing serves the existing grid and legend. Retry an interrupted publication or candidate cleanup with the same command. If a newer version is already live, retrying an older official release only cleans up that older version's remaining previews. Published versions remain available at their original candidate URLs. The Worker serves `/`, `/index.html` and `/releases/RELEASE_ID/...`. Use `npx wrangler deploy` to deploy changes to the Worker itself.

## Archived code

New build attempts capture the installed WorldAtlas source files and the project `environment.yml`, `pyproject.toml`, schema and README before computation. Staging includes those captured bytes in `inputs.json.gz`; it does not copy code from the checkout at staging time. Git history is not needed to recover them.

Each attempt's producer record identifies its source archive. Identical snapshots are stored once per release; resumed attempts using different code retain each snapshot. Keep code unchanged while an attempt runs; edits between attempts are captured on resume. This does not add a restriction on resuming with changed code.

The snapshot includes source and setup definitions. Reproduction uses the recorded Python and native library versions, the native GDAL setup described in the archived map-building guide, and the recorded raw files in R2. The current source snapshot adds approximately 0.5 MB compressed per distinct code version.

## Restore inputs

**1. Extract the archived inputs.** `restore-inputs` verifies `inputs.json.gz` in R2 and saves the release's settings, geographic selection and captured code in a new local directory. The command finishes once those files are on disk.

```bash
worldatlas-release restore-inputs v9.0-rc.1 /absolute/path/to/restored-inputs
```

**2. Install the captured code and its environment.** `run.json` lists the code ID for each attempt as that attempt's `source_archive.sha256`. Use the snapshot for the attempt you want to replay. Follow its archived map-building README for the recorded native GDAL setup.

```bash
cd /absolute/path/to/restored-inputs/code/CODE_ID
micromamba create -f environment.yml
micromamba activate worldatlas
python -m pip install --no-deps .
```

**3. Run map building to recalculate the cells.** The builder uses the saved selection, including the geographic records and coordinates captured from Neon. It fetches the pinned raw coastline and inland-water inputs from R2 as needed. Compare the new map streams with the released manifest's `decoded_sha256` values, or pass `--compare-release v9.0-rc.1` to compare cell assignments.

```bash
worldatlas-build /absolute/path/to/restored-inputs/configuration.json \
  --work-dir /absolute/path/to/worldatlas-work/replay \
  --selection /absolute/path/to/restored-inputs/selection.json
```

The extracted configuration and selection apply any source relocations recorded by the archive. Optional comparison paths from the original machine are omitted from the extracted configuration. The archive preserves the original records and reports.

Historical backfills use the same archive format. They can contain supporting records from older pipelines and notes describing unavailable configuration, code or reports. They do not invent missing inputs from today's Neon records. An archive without a modern `selection` requires its historical implementation; the restore command still extracts all available records and notes.

Run tests with `python .github/scripts/run_tests.py --suite map_releases`.

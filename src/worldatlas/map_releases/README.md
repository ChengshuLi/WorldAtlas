# Preview, publish and restore a map

Map building calculates cells. The release command packages a completed build, stages a numbered candidate and publishes that candidate after review. Use the [project environment and credentials](../../../README.md#pipeline-code). Staging and publishing require the direct `NEON_DATABASE_URL` so uploads and publication cannot overlap. Release commands use the project's R2 account and stage website bundles in `worldatlas`, the bucket served by the Worker.

## Use

### Stage a preview

```bash
worldatlas-release stage v9.0-rc.1 \
  /absolute/path/to/worldatlas-work/runs/preview --viewer web/viewer
```

The preview is at `/releases/v9.0-rc.1/index.html`. The homepage continues to show the published release. Changed contents require a new candidate number while a version is in review. Once a version is official, stage further changes under a new map version.

### Publish and retire previews

After the user reviews and approves the candidate:

```bash
worldatlas-release publish v9.0-rc.1
```

Publication verifies the files, commits the approved release in Neon and updates the homepage. The command prints `Published` as soon as the homepage update succeeds. It then removes the other candidate folders and rows for that version, including partial uploads that stopped before registration, and reports when cleanup finishes. Candidates of a version still under development stay available. Shared raw sources under `sources/` require a separate dependency check.

Publishing serves the existing grid and legend. Retry an interrupted publication or candidate cleanup with the same command. If Neon has since selected a different release for the homepage, retrying the older official release only cleans up its remaining previews. Published versions remain available at their original candidate URLs. The Worker serves `/`, `/index.html` and `/releases/RELEASE_ID/...`. Use `npx wrangler deploy` to deploy changes to the Worker itself.

### Restore inputs

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

**3. Run map building to recalculate the cells.** The builder uses the saved selection, including the geographic records and coordinates captured from Neon. It fetches the pinned raw coastline and inland-water inputs from R2 as needed. After the build finishes, check the map streams against the release manifest's `decoded_sha256` values or run [`worldatlas-compare`](../map_build/README.md#compare-a-finished-build) to see which assignments changed.

```bash
worldatlas-build /absolute/path/to/restored-inputs/configuration.json \
  /absolute/path/to/worldatlas-work/replay/run \
  --work-dir /absolute/path/to/worldatlas-work/replay \
  --selection /absolute/path/to/restored-inputs/selection.json
```

Check the `divide` field in the restored `run.json`. If it lists parent IDs, add one `--divide` argument for each ID when you rebuild. For example, `[0, 12]` means add `--divide 0 --divide 12`. If the field is null or absent, use the command as shown.

The extracted configuration and selection apply any source relocations recorded by the archive. Optional comparison paths from the original machine are omitted from the extracted configuration. The archive preserves the original records and reports.

Historical backfills use the same archive format. They can contain supporting records from older pipelines and notes describing unavailable configuration, code or reports. They do not invent missing inputs from today's Neon records. An archive without a modern `selection` requires its historical implementation; the restore command still extracts all available records and notes.

## How it works

### Release files and input archive

Each release has one R2 folder, `releases/RELEASE_ID/`, containing its viewer, compressed map streams, generated configuration, legend and `inputs.json.gz`. The `rows` stream stores row offsets, and `runs` stores run endpoints and category codes. The manifest records checksums for both the stored files and the decoded streams.

The archive holds the saved configuration, geographic selection, construction settings, source catalog references, run identity and build report. The run identity records the inputs and options needed to resume. Each attempt records its own runtime versions, source revision and setup files in `producer.json`. Packaging reads the saved run, never today's editable geography in Neon.

Raw files remain under `sources/`, shared across releases. Their cataloged identities, size and SHA-256 identify the bytes needed by each build. Staging requires the physical inputs to be embedded in the saved configuration or pinned in R2 so a rebuild can run on another machine. Water manifests embedded in the build request can use source IDs from the saved catalog. A water manifest fetched as a separate R2 file must carry each shard's R2 bucket, key, byte size, and SHA-256. Keep any raw source needed by working geography or a retained release. After retiring previews, check the working inputs and all surviving archives again before removing a raw object and its Neon catalog row.

Neon's `map_releases` row contains the bundle ID, R2 bucket, manifest checksum and publication-state flags. The release command derives the folder path from the bundle ID. The folder's `manifest.json` lists file locations, sizes, checksums and media types. Neon pins the manifest, and the manifest pins the files.

`is_official` records the permanent selection of a release for a version. Neon prevents demoting or deleting an official release. `is_current` identifies the official release selected for the homepage. Publication commits this choice in Neon, then updates R2's `index.html`. The homepage can still show the previous release if the R2 update fails. Staging sets both flags to false.

### Archived code

New build attempts capture the installed WorldAtlas source files and the project `environment.yml`, `pyproject.toml`, schema and README before computation. Staging requires a captured snapshot for every recorded build attempt and includes those bytes in `inputs.json.gz`. The archive contains the code captured by the build, which can be restored independently of Git history.

Each attempt's producer record identifies its source archive. Identical snapshots are stored once per release; resumed attempts using different code retain each snapshot. Keep code unchanged while an attempt runs; edits between attempts are captured on resume. This does not add a restriction on resuming with changed code.

The snapshot includes source and setup definitions. Reproduction uses the recorded Python and native library versions, the native GDAL setup described in the archived map-building guide, and the recorded raw files in R2. The current source snapshot adds approximately 0.5 MB compressed per distinct code version.

## Code and tests

[`manage_release.py`](manage_release.py) drives staging and publication. [`catalog.py`](catalog.py) resolves bundle identities and verifies manifests. [`inputs.py`](inputs.py) creates and restores the input archive. Tests cover packaging, restoration and interruption cases.

Run tests with `python .github/scripts/run_tests.py --suite map_releases`.

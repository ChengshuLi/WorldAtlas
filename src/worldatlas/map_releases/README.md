# Preview and publish a map

Map building writes cell assignments. This command packages a completed build
with the viewer, stages a numbered candidate and publishes that same candidate
after review. It does not calculate cells.

Use the project Python environment, `NEON_DATABASE_URL` and the R2 credentials
used for map building. Run commands from the repository root.

```bash
worldatlas-release stage v9.0-rc1 \
  /absolute/path/to/worldatlas-work/runs/preview --viewer web/viewer
```

The preview appears at `/review/releases/v9.0-rc1/index.html`. The homepage continues to
serve the published release. Use a new candidate number for changed contents.

The bundle contains the viewer, compressed map streams, generated configuration
and legend, plus a compressed copy of the frozen input selection. Neon stores
the file manifest and checksums instead of duplicating that large snapshot in
one database row. Names, colors, bindings and all geographic inputs come from the
build's saved selection. Counts come from its final grid. Staging verifies the
build's checksums and registers the exact bundle in Neon.

After the user reviews and approves that candidate:

```bash
worldatlas-release approve v9.0-rc1 --reviewer NAME
worldatlas-release publish v9.0-rc1
```

`atlas.map_releases` stores each immutable manifest, including exact R2 object
keys. `atlas.map_publications` maps an official version to one release. Stream
lookups use that manifest rather than a second copy of its hashes and sizes.
The homepage alias is recorded on the current publication.

Publishing verifies the stored files and changes the homepage to serve them.
If publication is interrupted, retry the same command; it reconciles the
homepage pointer without changing the approved bundle. It keeps the numbered candidate URL. It does not rebuild or recolor the map.
Deploying changes to the Cloudflare Worker itself is separate: `npx wrangler deploy`.

Run the release tests with:

```bash
python .github/scripts/run_tests.py --suite map_releases
```

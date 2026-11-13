# Preview and publish a map

Map building writes cell assignments. This command packages a completed build
with the viewer, stages a numbered candidate and publishes that same candidate
after review. It does not calculate cells.

Use the project Python environment, `NEON_DATABASE_URL` and the R2 credentials
used for map building. Run commands from the repository root.

```bash
python3 scripts/map-releases/manage_release.py stage v9.0-rc1 \
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
python3 scripts/map-releases/manage_release.py approve v9.0-rc1 --reviewer NAME
python3 scripts/map-releases/manage_release.py publish v9.0-rc1
```

Publishing verifies the stored files and changes the homepage to serve them.
It keeps the numbered candidate URL. It does not rebuild or recolor the map.
Deploying changes to the Cloudflare Worker itself is separate: `npx wrangler deploy`.

Run the release tests with:

```bash
PYTHONPATH=scripts/map-build python3 -m unittest discover -s scripts/map-releases
```

# WorldAtlas

The settled project contract is in [the data strategy](docs/data-strategy.md).

## Published V8 map

The [current viewer](web/current/README.md) renders the V8.0 map from two
checksum-verified row-run streams. The Cloudflare Worker serves the viewer and
streams from the `worldatlas` R2 bucket.

## Rebuild V8

Run the [V8 pipeline](scripts/v7-pipeline/README.md) from the repository root.

```bash
python3 scripts/v7-pipeline/run_pipeline.py scripts/v7-pipeline/config.json \
  --work-dir /absolute/path/to/worldatlas-work
```

The configuration selects versioned geographic decisions and source records in
Neon. The pipeline downloads the raw bytes from R2 and builds the physical grid,
then assigns land and water categories. The final grid has 131,072 columns and
54,614 rows. The pipeline guide covers credentials, the GDAL and PROJ versions
for exact reproduction, and stage timings.

## Deployment

Use the new Cloudflare account specified in `wrangler.jsonc`. Authenticate with
Wrangler; never commit credentials. Deploy with `wrangler deploy`. The Worker
requires an R2 binding named `ATLAS` to the `worldatlas` bucket.

Publish `web/current/index.html` as `review/index.html` and
`web/current/sources.html` as `review/v8.0/sources.html`. The viewer loads its
JavaScript, CSS and configuration from the versioned asset prefix in the HTML.
Serve the grid streams as `application/gzip` with no `Content-Encoding` header
so the viewer can decompress them.

`atlas.map_release_objects` tracks the two R2 objects for each versioned
row-run map. The `rows` stream stores row offsets and the `runs` stream stores
run endpoints and category codes. Register both in one transaction after
verifying the stored byte lengths and both sets of hashes. The table tracks
outputs separately from the source catalog. See
[`033_map_release_objects.sql`](migrations/033_map_release_objects.sql).

## Entity registry and staged stable-ID grid

`migrations/002_entity_registry.sql` defines stable entity identities and revisioned
names, levels, parents, V7 review-code bindings, and R2 artifact references.
Geographic entities and review-code bindings are supplied by a versioned Neon
registry snapshot. The schema migration does not publish or approve geography. Colors and the historic V7 land/water codes remain presentation data,
not entity IDs. The revisioned schema permits the remaining hierarchy to be added
without changing the legend code.

Export a registry revision from Neon using `scripts/export_entity_registry.sql`,
for example with `psql -X -A -t -v revision=REVISION -f scripts/export_entity_registry.sql > registry.json`. Use the same registry revision
as the decision snapshot and review-code bindings.

For a staged continent-ID grid, first prepare proposal metadata with
`node scripts/prepare_entity_metadata.mjs proposal.json prepared.json --registry
registry.json`, then run `python scripts/build_entity_grid.py prepared.json
rows.u32le runs.u32le NEW_OUTPUT_DIR` on the matching uncompressed V7 row offsets
and run pairs. It writes a new lossless u32 row-run grid and a checksummed manifest;
adjacent land and water runs for the same entity may merge. The source physical
mask and review-code grid must be retained independently for rendering and review.
The manifest pins the registry and bindings as well as the input and output streams.
This conversion stages files only: uploading them to R2 and atomically activating a
matching accepted Neon revision require the separate reviewed publication process.
The final canonical grid will use location IDs after the lower hierarchy is approved.

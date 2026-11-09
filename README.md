# WorldAtlas

The settled project contract is in [the data strategy](docs/data-strategy.md).

## Published V8 map

The [current viewer](web/current/README.md) renders the V8.0 map from two
checksum-verified row-run streams. The Cloudflare Worker serves the viewer and
streams from the `worldatlas` R2 bucket.

## Rebuild V8

Run the [V8 pipeline](scripts/pipeline/README.md) from the repository root.

```bash
python3 scripts/pipeline/run_pipeline.py scripts/pipeline/config.json \
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
V8.0 is the first WorldAtlas release. Its row and run streams are
`review/v8.0/rows.u32le.gz` and `review/v8.0/runs.u32le.gz`. Serve them as
`application/gzip` with no `Content-Encoding` header so the viewer can
decompress them.

`atlas.map_release_objects` tracks the two R2 objects for each versioned
row-run map. The `rows` stream stores row offsets and the `runs` stream stores
run endpoints and category codes. Register both in one transaction after
verifying the stored byte lengths and both sets of hashes. The table tracks
outputs separately from the source catalog. See
[`033_map_release_objects.sql`](migrations/033_map_release_objects.sql).
The `worldatlas-v8-viewer-inventory` document at version `v8.0` in
`atlas.structured_documents` records the deployed viewer's seven R2 objects,
their repository paths, byte lengths and SHA-256 hashes. The source catalog
tracks raw data objects, including the parts of source archives.

## Entity registry

`migrations/002_entity_registry.sql` defines stable entity IDs, revisioned names
and parent relationships, and the bindings from map category codes to entities.
Use the registry revision selected by the decision snapshot.

For a fresh database, apply the SQL migrations in filename order.
`036_v8_editable_schema.sql` supplies the mainland and regional decision
tables already present on `continent-review-v1`. The migrations define the
schema. The Neon branch holds the source catalog, drafts and release records.

Export a registry revision from Neon with `scripts/export_entity_registry.sql`.

    psql -X -A -t -v revision=REVISION -f scripts/export_entity_registry.sql > registry.json

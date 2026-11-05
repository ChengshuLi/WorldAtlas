# WorldAtlas

The settled project contract is in [the data strategy](docs/data-strategy.md).

## Continent review prototype

`web/worker.js` serves deliberately published `review/` assets from the `worldatlas`
R2 bucket. Evidence objects are not publicly routed. The root page is a draft review
surface, not an accepted geography release.

The viewer loads and verifies the entire native grid up front as lossless row runs.
The low four bits contain the proposed continent ID; bit 4 distinguishes source land.
WebGL renders directly from the compact run representation at every zoom, and local
picking uses the same data. There are no overview substitutions or detail downloads
during navigation. Controls remain disabled until the complete map is ready.
`scripts/build_local_grid.py DRAFT_DIR` builds and hashes the local-rendering assets
from the generation chunks; chunking is an offline generation detail only.

## Current direct research pipeline

The direct research pipeline builds the physical grid from pinned raw OSM land
and Overture inland-water sources. Its geographic decisions and source catalog
are versioned in Neon. See [the physical stage](scripts/v7-raw-mask/DIRECT.md),
[the direct composition workflow](scripts/v7-replay/DIRECT.md), and
[the rebuild status](scripts/v7-replay/REBUILD.md).

The target grid uses 131,072 columns and center sampling. Use
`scripts/native_grid.py` to read lossless row runs. Source archives and generated
grids belong in R2; geographic records and source references belong in Neon.
The direct build remains research-only and is not a complete or publishable map.
Publishing a review page does not accept its geography.

`migrations/001_geography_review.sql` provides the initial proposal record and an
accepted-only view. Test migrations on a Neon development branch before applying
them to the main database.

## Deployment

Use the new Cloudflare account specified in `wrangler.jsonc`. Authenticate with
Wrangler; never commit credentials. Deploy with `wrangler deploy`. The Worker
requires an R2 binding named `ATLAS` to the `worldatlas` bucket.

The source contains `__ASSET_BASE__` in `web/index.html`; replace it with the exact
versioned `/review/.../` prefix when generating a published index. The display grid
is gzip data and must be served as `application/gzip`, without a `Content-Encoding`
header, because the browser explicitly decompresses it.

## Entity registry and staged stable-ID grid

`migrations/002_entity_registry.sql` defines stable entity identities and revisioned
names, levels, parents, V7 review-code bindings, and R2 artifact references.
Geographic entities and review-code bindings are supplied by a versioned Neon
registry snapshot. The schema migration does not publish or approve geography. Colors and the historic V7 land/water codes remain presentation data,
not entity IDs. The revisioned schema permits the remaining hierarchy to be added
without changing the legend code.

To prepare a local V7 review bundle with a registry exported from Neon, export one
revision using `scripts/export_entity_registry.sql`, for example with `psql -X -A
-t -v revision=REVISION -f scripts/export_entity_registry.sql > registry.json`,
then set `WORLDATLAS_ENTITY_REGISTRY_EXPORT` to that file when running
`scripts/build_full_v7_ui_bundle.py`. This is a historical-only builder: it
requires `WORLDATLAS_HISTORICAL_V7_REPLAY=1` because it still uses superseded
Gulf attribution. It cannot produce the selected SeaVoX Gulf bundle yet. See
[the rebuild notes](scripts/v7-replay/REBUILD.md) for the remaining gaps. The
builder validates the snapshot and bindings. With no export, it derives an explicitly draft, deterministic bootstrap
from the existing V7 categories. This fallback is for local review, not evidence
of database acceptance or publication. The V7 viewer retains its original review
codes, colors, and separate land/water styling while displaying registry names.

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

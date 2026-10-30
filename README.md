# WorldAtlas

The settled project contract is in [the data strategy](docs/data-strategy.md).

## Continent review prototype

`web/worker.js` serves deliberately published `review/` assets from the `worldatlas`
R2 bucket. Evidence objects are not publicly routed. The root page is a draft review
surface, not an accepted geography release.

The viewer loads one compressed native-resolution display grid. Its low four bits
contain the proposed continent ID; bit 4 distinguishes reference-source land for
display. Selection uses the exact cell ID locally. The smaller overview image is
only a display aid. Rendered detail tiles are generated in the browser.

`scripts/build_continent_proposal.py` builds the initial research draft from pinned
Natural Earth archives. It includes explicit, reviewable atlas conventions; it is
not an authoritative definition of continent or maritime boundaries. It checks
polygon intersection areas at land-boundary cells, resolves date-line assignments,
preserves inland lakes, and records source limitations in its output.

Run with Python, NumPy, SciPy, Shapely, Rasterio, pyshp, and Pillow:

```
python scripts/build_continent_proposal.py SOURCES_DIR OUTPUT_DIR
python scripts/audit_small_islands.py SOURCES_DIR OUTPUT_DIR
```

Source archives, generated grids, research notes, and review metadata belong in
R2/Neon rather than Git. Use an immutable review prefix for each candidate and
publish the root index only after its referenced assets exist. The draft remains
unaccepted until the user's exact cell-map review is complete.

`migrations/001_geography_review.sql` provides the initial proposal record and an
accepted-only view. Test migrations on a Neon development branch before applying
them to the main database. Do not infer approval from publishing a review page.

## Deployment

Use the new Cloudflare account specified in `wrangler.jsonc`. Authenticate with
Wrangler; never commit credentials. Deploy with `wrangler deploy`. The Worker
requires an R2 binding named `ATLAS` to the `worldatlas` bucket.

The source contains `__ASSET_BASE__` in `web/index.html`; replace it with the exact
versioned `/review/.../` prefix when generating a published index. The display grid
is gzip data and must be served as `application/gzip`, without a `Content-Encoding`
header, because the browser explicitly decompresses it.

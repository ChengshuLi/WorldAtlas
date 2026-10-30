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

`scripts/build_continent_proposal.py` builds the initial research draft from pinned
Natural Earth archives. It includes explicit, reviewable atlas conventions; it is
not an authoritative definition of continent or maritime boundaries. It checks
polygon intersection areas at land-boundary cells, resolves date-line assignments,
preserves inland lakes, and records source limitations in its output.

Run with Python, NumPy, SciPy, Shapely, Rasterio, pyshp, Matplotlib, and Pillow:

```
python scripts/build_continent_proposal.py SOURCES_DIR OUTPUT_DIR
python scripts/audit_small_islands.py SOURCES_DIR OUTPUT_DIR
```

`scripts/build_review_tiles.py SOURCES_DIR PRIOR_DRAFT_DIR OUTPUT_DIR` creates the
65,536-column center-sampled review version. It re-rasterizes source land at native
resolution while retaining the prior draft's marine grouping footprints, which remain
explicitly provisional. Enclosed ocean-code artifacts are audited and assigned to
the surrounding continent, retaining open-ocean boundaries and intentional island
groups. Heard–McDonald is grouped with Kerguelen in Africa. Pass `--maldives`
with the pinned OneMap island GeoJSON to replace the generalized Maldives coast;
retain its license and attribution. Generation is banded and does not allocate the whole grid.

`scripts/refine_review_regions.py PRIOR_NATIVE_DIR SOURCES_DIR OUTPUT_DIR` applies
reviewed island affiliations and regional sea corrections directly to native row runs.
It preserves the land mask, records changed-cell counts, and uses the mapped main
Suez Canal alignment in `data/geography/suez-canal.geojson`. The canal alignment
is credited to OpenStreetMap contributors; its Gulf extension is an editorial
separator through water. Shared Philippine, Banda, and Arafura waters use the
nearest corrected coastline, with nearby-water priority within 100 km.

`scripts/audit_mediterranean.py PRIOR_NATIVE_DIR OUTPUT_DIR` audits all connected
Mediterranean water cells at native resolution against the nearest coastal land
cell on a sphere, including islands. Its padded coast search is checked for every
cell so omitted coastlines cannot be nearer. Separate continent-specific searches
independently verify the result. Basin entrance gates exclude the Atlantic,
Marmara and Suez Canal; land assignments and water outside the basin are preserved.

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

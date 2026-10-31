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

`scripts/rebuild_northern_indian.py PRIOR_NATIVE_DIR OUTPUT_DIR` applies one rule
across the Arabian Sea, Bay of Bengal and adjoining waters: retain bounded Aden,
Persian/Oman and Andaman waters; elsewhere assign the nearest coastal continent
within 100 km, including islands, and Indian Ocean beyond. Aden is shared by
mainland coast proximity with local coastal-buffer priority. Native connected
water masks exclude inland lakes and unrelated seas. Independent per-continent
queries verify every revised sea cell. The Andaman western island-arc boundary
uses the source marine outline; its southern entrance follows named capes.

The final worldwide coastal pass is `scripts/rebuild_coastal_buffers.py
PRIOR_NATIVE_DIR OUTPUT_DIR OPEN_WATER_RUNS.npy`. Generate its topology input with
`scripts/classify_water_connectivity.py PRIOR_NATIVE_DIR OPEN_WATER_RUNS.npy`.
This final pass supersedes historical 100-km regional buffers: ordinary open
coasts receive exactly 12 nautical miles (22.224 km), from represented native
coastal land cells on a sphere. Inland waters and documented bounded/shared seas
are retained. Islands missing from the grid create no buffer. North Sea limits
follow the named Orkney/Shetland capes and 61°N; open Biscay, Atlantic approaches,
and Arctic coasts use the uniform buffer. The distance does not depict legal
territorial waters. Earlier regional scripts are retained as research provenance.

The final basin-coverage sequence also applies:

1. `refine_english_channel.py` clips the western mouth to the corrected IHO
   Île Vierge–Land’s End line.
2. `refine_arctic_atlantic.py` applies the continuous named-cape Nordic divider.
3. `repair_sea_family_coverage.py PRIOR OUTPUT SHELIKOF_GEOJSON` includes the
   constituent bays, sounds, and passages listed in `sea_families.py`.
4. `repair_arctic_basins.py PRIOR OUTPUT IHO_ARCTIC_GEOJSON_GZ` assigns complete
   northern parent-ocean areas. Davis Strait is Arctic north of 60°N; Norwegian
   Sea remains Atlantic, with Greenland and Barents seas Arctic.
5. `audit_ocean_connectivity.py PRIOR MASK.npy --ocean-code CODE` separately
   checks each ocean label. Resolve inconsistent labels against their containing
   parent basin; legitimate separated marginal basins require an explicit reason.
   `repair_ocean_parent_components.py` requires every changed center to be covered
   by the independently supplied parent-basin reference and pins the topology mask.
6. `close_enclosed_ocean_components.py PRIOR OUTPUT` checks four-edge ocean
   connectivity with longitude wrapping. Enclosed components surrounded by one
   continent inherit that continent; ambiguous components are reported.

Project boundary conventions take priority over generic source areas: the
Bering gateway follows Cape Dezhnev–Cape Prince of Wales, and the Nordic divider
ends at North Cape rather than extending an artificial Atlantic line eastward.
The Arctic Baffin/Davis basin can be disconnected from the main Arctic label by
continental classifications of the Canadian passages; this alone is not an error.

All passes preserve every land cell. Shared new sea cells use the nearest
represented coast. Open named embayments are explicitly distinguished from
bounded waters; names alone do not imply continental assignment. The reference
sources are [IHO Sea Areas v3](https://doi.org/10.14284/323),
[Natural Earth marine labels](https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-physical-labels/),
and the [NOAA Shelikof Strait coastal zone](https://api.weather.gov/zones/forecast/PKZ738).
The latter supplies a geographic passage footprint, not a legal maritime limit.

The viewer wraps horizontally across the dateline. Rendering and picking use
modulo world columns, including repeated wraps, while vertical panning stays
clamped. All native cells remain loaded throughout navigation.

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

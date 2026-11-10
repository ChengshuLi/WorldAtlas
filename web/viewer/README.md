# Map viewer

This folder contains the streamlined WorldAtlas interface deployed at the Cloudflare root. It renders the V8.0 native grid. `config.json` pins the row-offset and run streams, which remain in R2. The V8.0 reproduction matched the published grid byte for byte.

The displayed combined SHA-256 is calculated over the decompressed little-endian u32 row-offset bytes followed immediately by the decompressed little-endian u32 run bytes. It identifies these two streams, not source data, metadata, code or the interface. The client separately verifies the row and run hashes before use. The checked-in category counts were independently computed from the complete grid.

OpenStreetMap and SeaVoX attributions are available through Data sources. OpenStreetMap Foundation guidance recommends presenting its attribution on startup or beside a browsable map; this interface follows the requested source-page-only presentation. The linked source page lists the main current inputs. The deployment uses an immutable `review/worldatlas-current-20261107-clean-v1/` asset prefix, while the Worker serves the root HTML from `review/index.html`. The Worker maps `/v8.0/sources` and `/v8.0/sources.html` to the existing public `/review/v8.0/sources.html` object.

Use the [release workflow](../../scripts/map-build/pipeline/README.md#stage-review-and-publish-a-release)
to package the browser modules with a completed build. The candidate bundle
contains the viewer’s release-specific configuration and base URL.
Staging generates the category list and land colors in `config.json`. The
source config defines the shared water color. Selecting legend entries keeps
their fills at full brightness and outlines their combined area in white.

From the repository root, run `npm test` for grid, viewer, and Worker checks
that need only Node. For browser tests, install the development dependencies and
Chromium, then run the separate suite.

```bash
npm install
PLAYWRIGHT_SKIP_BROWSER_GC=1 npx playwright install chromium --only-shell
npm run test:browser
```

The browser suite runs the real Worker and viewer locally against a tiny map
stored in memory. It checks desktop WebGL, mobile touch and the Canvas fallback,
separate homepage and preview files, and missing or corrupted map data. Before
publishing, open `/` and the deployed preview to check both maps with the real
release files.

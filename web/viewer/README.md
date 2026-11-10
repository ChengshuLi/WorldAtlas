# Map viewer

This folder contains the WorldAtlas interface. Release packaging generates `config.json` with the grid dimensions, checksums, category bindings, and a link to the release's legend file. The source config defines the shared water color.

The displayed combined SHA-256 is calculated over the decompressed little-endian u32 row-offset bytes followed immediately by the decompressed little-endian u32 run bytes. The client verifies the row and run hashes before use.

OpenStreetMap and SeaVoX attributions are available through Data sources. OpenStreetMap Foundation guidance recommends presenting its attribution on startup or beside a browsable map; this interface follows the requested source-page-only presentation. The linked source page lists the main current inputs. The deployment uses an immutable `review/worldatlas-current-20261107-clean-v1/` asset prefix, while the Worker serves the root HTML from `review/index.html`. The Worker maps `/v8.0/sources` and `/v8.0/sources.html` to the existing public `/review/v8.0/sources.html` object.

Use the [release workflow](../../scripts/map-build/pipeline/README.md#stage-review-and-publish-a-release)
to package the browser modules with a completed build. The candidate bundle
contains the viewer’s release-specific configuration and base URL.
Staging generates `legend/continents.json` with one entry per entity containing
its ID, name, color, and cell count. Names come from the build's selected Neon
snapshot and land colors come from the stable entity records in Neon. Counts
come from the completed grid report, adding land and water for each continent.
The viewer loads this release file to display the legend. Selecting entries keeps
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

# Map viewer

This folder contains the WorldAtlas interface. The checked-in `config.json` holds `water_rgb`, the shared water color. Release packaging generates the deployed config with the map version, grid dimensions, file paths, checksums, category bindings, and a link to the release's legend file.

The displayed combined SHA-256 is calculated over the decompressed little-endian u32 row-offset bytes followed immediately by the decompressed little-endian u32 run bytes. The client verifies the row and run hashes before use.

The Cloudflare Worker serves viewer files and map data from R2. Each candidate
has a directory at `releases/CANDIDATE/`. Publishing copies
that candidate's homepage to `index.html`, which the Worker serves at
`/`. The homepage's base URL selects its release files. Data sources opens
the release's `sources.html`, including OpenStreetMap and IHO attributions.

Use the [release workflow](../../src/worldatlas/map_releases/README.md)
to package the browser modules with a completed build. The candidate bundle
contains the viewer’s release-specific configuration and base URL.
Staging generates `legend/continents.json` with one entry per entity containing
its ID, name, color, and cell count. Names come from the build's selected Neon
snapshot and land colors come from the stable entity records in Neon. Counts
come from the completed grid report, adding land and water for each continent.
The deployed config and legend file are generated release data stored in R2.
GitHub tracks their generator and the viewer source.

Selecting entries keeps their fills at full brightness and dims the other
colors. A white outline surrounds the combined selected land and water, with
no line between adjacent selected entities. Hovering another legend entry
temporarily brightens it while preserving the selection outline.

From the repository root, run `npm test` for grid, viewer, and Worker checks
that need only Node. For browser tests, install the development dependencies and
Chromium, then run the separate suite.

```bash
npm ci
PLAYWRIGHT_SKIP_BROWSER_GC=1 npx playwright install chromium --only-shell
npm run test:browser
```

CI runs the same suite with `PLAYWRIGHT_CHANNEL=chrome`, using the browser
already installed on GitHub's Linux runner. Local runs use Playwright's bundled
Chromium unless that variable selects an installed browser.

The browser suite runs the real Worker and viewer locally against a tiny map
stored in memory. It checks desktop WebGL, mobile touch and the Canvas fallback,
separate homepage and preview files, and legend totals. It also checks errors
for missing legend or map data and corrupted grid checksums. Before publishing,
open `/` and the deployed preview to check both maps with the real release files.

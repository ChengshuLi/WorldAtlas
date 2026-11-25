# Map viewer

The WorldAtlas viewer draws an official map or numbered preview and shows the selected entities and their cell counts.

## Use

Open the [published map](https://worldatlas.chengshu-li-web.workers.dev/) or a numbered preview. Follow the [release workflow](../../src/worldatlas/map_releases/README.md#stage-a-preview) to package the viewer with a completed build.

Selecting entries keeps their fills at full brightness and dims the other colors. A white outline surrounds the combined selected land and water, with no line between adjacent selected entities. Hovering another legend entry temporarily brightens it while preserving the selection outline.

On a touchscreen, tap to inspect a cell, drag with one finger to pan, and pinch with two fingers to zoom around their midpoint.

## How it works

The checked-in `config.json` holds `water_rgb`, the shared water color. Release packaging generates the deployed config with the map version, grid dimensions, file paths, checksums, category bindings, and the available geographic modes.

The displayed combined SHA-256 is calculated over the decompressed little-endian u32 row-offset bytes followed immediately by the decompressed little-endian u32 run bytes. The client verifies the row and run hashes before use.

The viewer sizes WebGL textures to fit the device and uploads the grid in batches to reduce temporary memory. When the grid exceeds those limits, graphics setup fails, or the browser loses WebGL after loading, Canvas draws from the same verified grid already in memory.

The Cloudflare Worker serves viewer files and map data from R2. Each candidate has a directory at `releases/CANDIDATE/`. Publishing copies that candidate's homepage to `index.html`, which the Worker serves at `/`. The homepage's base URL selects its release files. The Data sources dialog shows OpenStreetMap, Overture Maps, and IHO attributions over the map.

The release config lists the available geographic modes in hierarchy order. Each mode file, such as `modes/continent.json`, maps the shared grid’s codes to owners at that level and supplies the legend names, colors, and cell counts. Switching modes loads that file and updates the legend and colors together. The grid and viewport stay in place.

The legend counts land and water once per entity. Land without an assignment at the selected level uses a neutral fill and contributes to the unbuilt count. Water stays blue and can still be selected and outlined by its owner. The switcher appears only when the release has more than one geographic level with assignments.

The same legend panel can later show themes such as religion. Geographic modes count map cells. Counting locations will depend on the completed location boundaries.

## Code and tests

[`app.js`](app.js) connects the interface to the grid and legend. [`grid-data.js`](grid-data.js) loads and verifies streams. [`grid-renderer.js`](grid-renderer.js) draws the map. [`legend-model.js`](legend-model.js) reads and checks the legend.

From the repository root, run `npm test` for grid, viewer, and Worker checks that need only Node. For browser tests, install the development dependencies and Chromium, then run the separate suite.

```bash
npm ci
PLAYWRIGHT_SKIP_BROWSER_GC=1 npx playwright install chromium --only-shell
npm run test:browser
```

CI runs the same suite with `PLAYWRIGHT_CHANNEL=chrome`, using the browser already installed on GitHub's Linux runner. Local runs use Playwright's bundled Chromium unless that variable selects an installed browser.

The browser suite runs the real Worker and viewer locally against a tiny map stored in memory. It checks desktop WebGL, mobile touch and the Canvas fallback, separate homepage and preview files, the sources dialog, keyboard navigation, legend totals, and changing modes without reloading the map. It also checks errors for missing legend or map data and corrupted grid checksums. Before publishing, open `/` and the deployed preview to check both maps with the real release files.

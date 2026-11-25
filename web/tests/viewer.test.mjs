import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { cellValue, validateGrid } from "../viewer/grid-data.js";
import { renderPixels } from "../viewer/grid-renderer.js";
const read = (f) =>
  fs.readFileSync(new URL("../viewer/" + f, import.meta.url), "utf8");
test("structure, checksum and small native-grid renderer", () => {
  const html = read("index.html");
  assert.doesNotMatch(
    html,
    /<aside|id="v2"|id="jump"|Map legend ·|Select any continents/,
  );
  assert.match(html, /aria-label="Collapse legend"/);
  assert.doesNotMatch(html, /id="startup-credit"/);
  assert.match(
    html,
    /aria-label="World assignment map\. Click to select a cell\."/,
  );
  assert.doesNotMatch(
    html.match(/<header>[\s\S]*?<\/header>/)[0],
    /OpenStreetMap/,
  );
  assert.match(html, /<dialog id="sources-dialog"/);
  assert.match(html, /OpenStreetMap contributors/);
  assert.doesNotMatch(html, /© OpenStreetMap/);
  assert.match(html, /id="map-release"/);
  assert.doesNotMatch(html, /<details/);
  assert.doesNotMatch(read("app.js"), /document\.addEventListener\('keydown'/);
  const small = {
      width: 4,
      height: 2,
      local_grid: { run_count: 4 },
      categories: [1, 2, 3, 4].map((id) => ({ id })),
      palette: new Map(Array.from({ length: 32 }, (_, i) => [i, [i, i, i]])),
    },
    data = {
      rows: new Uint32Array([0, 2, 4]),
      runs: new Uint32Array([2, 1, 4, 2, 1, 3, 4, 4]),
    };
  validateGrid(small, data.rows, data.runs);
  assert.equal(cellValue(data.rows, data.runs, 3, 0), 2);
  assert.equal(renderPixels(small, data, 4, 2, 1, 0, 0).length, 8);
});
test("viewer uses assets relative to its release bundle", () => {
  const html = read("index.html");
  assert.doesNotMatch(html, /location\.replace/);
  assert.match(html, /type="module" src="app\.js"/);
});

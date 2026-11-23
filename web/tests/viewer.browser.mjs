import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { createServer } from "node:http";
import { once } from "node:events";
import { after, before, test } from "node:test";
import { gzipSync } from "node:zlib";
import { chromium } from "playwright";
import worker from "../worker.js";

const viewer = new URL("../viewer/", import.meta.url);
const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");
const mapWidth = 120;
const mapHeight = 60;
const published = "releases/v8.0-rc.1";
const candidate = "releases/v9.0-rc.1";
const objects = new Map();

function store(key, bytes, type) {
  const body = Buffer.from(bytes);
  objects.set(key, {
    body,
    httpEtag: `"${sha256(body)}"`,
    writeHttpMetadata(headers) {
      headers.set("Content-Type", type);
    },
  });
}

function words(values) {
  const bytes = Buffer.alloc(values.length * 4);
  values.forEach((value, i) => bytes.writeUInt32LE(value, i * 4));
  return bytes;
}

function bundle(prefix, version, east) {
  const rows = words(Array.from({ length: mapHeight + 1 }, (_, y) => y * 5));
  const runs = words(
    Array.from({ length: mapHeight }, () => [
      30,
      1,
      60,
      17,
      80,
      2,
      105,
      east,
      120,
      7,
    ]).flat(),
  );
  const config = JSON.parse(readFileSync(new URL("config.json", viewer)));
  Object.assign(config, {
    width: mapWidth,
    height: mapHeight,
    step: 360 / mapWidth,
    map_version: version,
    inland_water_release: version === "v8.0" ? "2026-08-19.0" : "2026-10-21.0",
    legend: "legend/entities.json",
    categories: [
      { id: 1, entity_id: 1, physical_class: "water" },
      { id: 2, entity_id: 2, physical_class: "water" },
      { id: 7, entity_id: 7, physical_class: "water" },
      { id: 17, entity_id: 1, physical_class: "land" },
      { id: 18, entity_id: 2, physical_class: "land" },
    ],
    local_grid: {
      run_count: mapHeight * 5,
      rows: "rows.u32le.gz",
      runs: "runs.u32le.gz",
      rows_sha256: sha256(rows),
      runs_sha256: sha256(runs),
    },
    combined_sha256: sha256(Buffer.concat([rows, runs])),
  });
  store(
    `${prefix}/legend/entities.json`,
    JSON.stringify([
      {
        id: 1,
        name: "Africa",
        color: [233, 180, 76],
        count: (60 + (east === 17 ? 25 : 0)) * mapHeight,
      },
      {
        id: 2,
        name: "Asia",
        color: [222, 118, 110],
        count: (20 + (east === 18 ? 25 : 0)) * mapHeight,
      },
      {
        id: 7,
        name: "Atlantic Ocean",
        color: config.water_rgb,
        count: 15 * mapHeight,
      },
    ]),
    "application/json",
  );
  store(`${prefix}/config.json`, JSON.stringify(config), "application/json");
  store(`${prefix}/rows.u32le.gz`, gzipSync(rows), "application/gzip");
  store(`${prefix}/runs.u32le.gz`, gzipSync(runs), "application/gzip");
  for (const name of [
    "app.js",
    "grid-data.js",
    "grid-renderer.js",
    "legend-model.js",
  ]) {
    store(
      `${prefix}/${name}`,
      readFileSync(new URL(name, viewer)),
      "text/javascript",
    );
  }
  store(
    `${prefix}/style.css`,
    readFileSync(new URL("style.css", viewer)),
    "text/css",
  );
  const index = readFileSync(new URL("index.html", viewer), "utf8").replace(
    "<head>",
    `<head><base href="/${prefix}/">`,
  );
  store(`${prefix}/index.html`, index, "text/html");
  return index;
}

let browser;
let server;
let origin;
before(async () => {
  store("index.html", bundle(published, "v8.0", 17), "text/html");
  store(`${candidate}/index.html`, bundle(candidate, "v9.0", 18), "text/html");
  const corrupt = "releases/v9.1-rc.1";
  store(`${corrupt}/index.html`, bundle(corrupt, "v9.1", 18), "text/html");
  // Valid gzip with different decoded bytes exercises the viewer's checksum.
  store(
    `${corrupt}/runs.u32le.gz`,
    gzipSync(words([1, 17])),
    "application/gzip",
  );
  const missing = "releases/v9.2-rc.1";
  store(`${missing}/index.html`, bundle(missing, "v9.2", 18), "text/html");
  objects.delete(`${missing}/rows.u32le.gz`);
  const missingLegend = "releases/v9.3-rc.1";
  store(
    `${missingLegend}/index.html`,
    bundle(missingLegend, "v9.3", 18),
    "text/html",
  );
  objects.delete(`${missingLegend}/legend/entities.json`);

  const sparse = "releases/v9.4-rc.1";
  bundle(sparse, "v9.4", 18);
  const remap = new Map([
    [1, 301],
    [17, 0xffffffff],
    [2, 999],
    [18, 70001],
    [7, 4321],
  ]);
  const runs = words(
    Array.from({ length: mapHeight }, () => [
      30, 301, 60, 0xffffffff, 80, 999, 105, 70001, 120, 4321,
    ]).flat(),
  );
  const config = JSON.parse(objects.get(`${sparse}/config.json`).body);
  const legend = JSON.parse(
    objects.get(`${sparse}/legend/entities.json`).body,
  );
  for (const category of config.categories)
    category.id = remap.get(category.id);
  for (let i = 0; i < 80; i++) {
    config.categories.push({
      id: 100000 + i,
      entity_id: 1000 + i,
      physical_class: "land",
    });
    legend.push({
      id: 1000 + i,
      name: `Synthetic area ${i}`,
      color: [20, 80, 120],
      count: 0,
    });
  }
  const rows = words(Array.from({ length: mapHeight + 1 }, (_, y) => y * 5));
  config.local_grid.runs_sha256 = sha256(runs);
  config.combined_sha256 = sha256(Buffer.concat([rows, runs]));
  store(`${sparse}/config.json`, JSON.stringify(config), "application/json");
  store(
    `${sparse}/legend/entities.json`,
    JSON.stringify(legend),
    "application/json",
  );
  store(`${sparse}/runs.u32le.gz`, gzipSync(runs), "application/gzip");

  server = createServer(async (request, reply) => {
    try {
      const read = async (key) => objects.get(key);
      const response = await worker.fetch(
        new Request(new URL(request.url, origin), {
          method: request.method,
          headers: request.headers,
        }),
        { ATLAS: { get: read, head: read } },
      );
      reply.writeHead(response.status, Object.fromEntries(response.headers));
      reply.end(Buffer.from(await response.arrayBuffer()));
    } catch (error) {
      reply.writeHead(500).end(String(error));
    }
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  origin = `http://127.0.0.1:${server.address().port}`;
  browser = await chromium.launch({
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
    args: ["--enable-unsafe-swiftshader"],
  });
});

after(async () => {
  try {
    await browser?.close();
  } finally {
    if (server?.listening)
      await new Promise((resolve) => server.close(resolve));
  }
});

async function loaded(page, path, version) {
  const response = await page.goto(origin + path);
  assert.equal(response.status(), 200);
  await page.waitForFunction(
    () => document.querySelector("#status").textContent !== "Loading map…",
  );
  assert.equal(await page.locator("#status").textContent(), "");
  assert.ok(
    (await page.locator("#map-release").textContent()).startsWith(
      `${version.toUpperCase()} · SHA-256 `,
    ),
  );
}

async function pickPoint(page, x, y) {
  const { width, height } = await page.locator("#canvas").boundingBox();
  const scale = Math.min(width / mapWidth, height / mapHeight);
  return {
    x: Math.round(width / 2 + (x + 0.5 - mapWidth / 2) * scale),
    y: Math.round(height / 2 + (y + 0.5 - mapHeight / 2) * scale),
  };
}

async function visiblePixel(page, position) {
  const canvas = await page.locator("#canvas").boundingBox();
  const png = await page.screenshot({
    clip: {
      x: Math.round(canvas.x) + position.x,
      y: Math.round(canvas.y) + position.y,
      width: 1,
      height: 1,
    },
  });
  return page.evaluate(async (base64) => {
    const bytes = Uint8Array.from(atob(base64), (char) => char.charCodeAt(0));
    const image = await createImageBitmap(
      new Blob([bytes], { type: "image/png" }),
    );
    const canvas = new OffscreenCanvas(1, 1);
    const context = canvas.getContext("2d");
    context.drawImage(image, 0, 0);
    return [...context.getImageData(0, 0, 1, 1).data];
  }, png.toString("base64"));
}

for (const { name, options, fallback, sparse, uploadFailure } of [
  {
    name: "desktop WebGL",
    options: { viewport: { width: 1024, height: 720 } },
    fallback: false,
  },
  {
    name: "mobile touch and Canvas fallback",
    options: {
      viewport: { width: 390, height: 700 },
      isMobile: true,
      hasTouch: true,
    },
    fallback: true,
  },
  {
    name: "sparse uint32 codes with 83 legend entities in WebGL",
    options: { viewport: { width: 1024, height: 720 } },
    fallback: false,
    sparse: true,
  },
  {
    name: "sparse uint32 codes with 83 legend entities in Canvas",
    options: { viewport: { width: 1024, height: 720 } },
    fallback: true,
    sparse: true,
  },
  {
    name: "Canvas after WebGL upload failure",
    options: { viewport: { width: 1024, height: 720 } },
    fallback: true,
    uploadFailure: true,
  },
]) {
  test(
    `${name} renders, selects cells, and filters the legend`,
    { timeout: 30_000 },
    async () => {
      const page = await browser.newPage(options);
      try {
        const gridRequests = [];
        if (uploadFailure) {
          page.on("request", (request) => {
            const path = new URL(request.url()).pathname;
            if (path.endsWith(".u32le.gz")) gridRequests.push(path);
          });
          await page.addInitScript(() => {
            const { texSubImage2D, getError } = WebGL2RenderingContext.prototype;
            const failed = new WeakSet();
            WebGL2RenderingContext.prototype.texSubImage2D = function (...args) {
              failed.add(this);
              texSubImage2D.apply(this, args);
            };
            WebGL2RenderingContext.prototype.getError = function () {
              return failed.delete(this) ? this.OUT_OF_MEMORY : getError.call(this);
            };
          });
        } else if (fallback)
          await page.addInitScript(() => {
            for (const type of [HTMLCanvasElement, OffscreenCanvas]) {
              const getContext = type.prototype.getContext;
              type.prototype.getContext = function (kind, ...args) {
                return kind === "webgl2"
                  ? null
                  : getContext.call(this, kind, ...args);
              };
            }
          });
        const errors = [];
        page.on("pageerror", (error) => errors.push(error.message));
        await loaded(
          page,
          sparse
            ? "/releases/v9.4-rc.1/index.html"
            : "/releases/v9.0-rc.1/index.html",
          sparse ? "v9.4" : "v9.0",
        );
        const canvas = page.locator("#canvas");
        if (uploadFailure) {
          assert.deepEqual(gridRequests.sort(), [
            `/${candidate}/rows.u32le.gz`,
            `/${candidate}/runs.u32le.gz`,
          ]);
        }
        assert.equal(
          await canvas.evaluate(
            (element, type) => Boolean(element.getContext(type)),
            fallback ? "2d" : "webgl2",
          ),
          true,
        );
        assert.equal(
          await page.evaluate(
            () => document.documentElement.scrollWidth === innerWidth,
          ),
          true,
        );
        assert.equal(
          await page.evaluate(() => {
            const labels = [
              ".brand p", "#tool-sources", "#map-release", ".legend-count",
              "#selection", "#status",
            ];
            const sizes = labels.map(
              (selector) => getComputedStyle(document.querySelector(selector)).fontSize,
            );
            return new Set(sizes).size;
          }),
          1,
        );
        const legend = page.getByRole("region", { name: "Map legend" });
        await legend.getByRole("button", { name: "Collapse legend" }).click();
        assert.equal(await legend.isVisible(), false);
        const east = await pickPoint(page, 90, 20);
        const eastFill = await pickPoint(page, 94, 20);
        const west = await pickPoint(page, 20, 20);
        const africaLand = await pickPoint(page, 40, 20);
        const asiaWater = await pickPoint(page, 70, 20);
        const { width } = await canvas.boundingBox();
        const insideBorder = (column) => ({
          x: Math.ceil((width * column) / mapWidth - 0.5) - 1,
          y: west.y,
        });
        const waterColor = [84, 141, 183, 255];
        assert.deepEqual(await visiblePixel(page, east), [222, 118, 110, 255]);
        assert.deepEqual(await visiblePixel(page, west), waterColor);
        assert.deepEqual(await visiblePixel(page, asiaWater), waterColor);

        const pick = () =>
          options.hasTouch
            ? canvas.tap({ position: east })
            : canvas.click({ position: east });
        const selection = page.locator("#selection");
        await pick();
        assert.equal(
          await selection.textContent(),
          "Cell 90, 20 · 28.50000°, 91.50000° · Asia (land)",
        );
        await page.getByRole("button", { name: "Zoom in" }).click();
        await pick();
        assert.match(await selection.textContent(), /^Cell 75, 25 ·/);
        await page.getByRole("button", { name: "World", exact: true }).click();
        await pick();
        assert.match(await selection.textContent(), /^Cell 90, 20 ·/);

        const search = page.getByRole("searchbox", {
          name: "Search continents",
        });
        const openLegend = page.getByRole("button", { name: "Legend", exact: true });
        if (options.hasTouch) await openLegend.tap();
        else await openLegend.click();
        assert.equal(await legend.evaluate((element) => element === document.activeElement), true);
        await page.keyboard.press("Tab");
        assert.equal(
          await search.evaluate(
            (element) => element === document.activeElement,
          ),
          true,
        );
        await search.fill("africa");
        assert.equal(await legend.locator(".legend-item").count(), 1);
        const africa = legend.getByRole("button", { name: /Africa/ });
        await africa.click();
        assert.equal(await africa.getAttribute("aria-pressed"), "true");
        await legend.getByRole("button", { name: "Collapse legend" }).click();
        assert.deepEqual(await visiblePixel(page, west), waterColor);
        assert.deepEqual(
          await visiblePixel(page, africaLand),
          [233, 180, 76, 255],
        );
        // WebGL and Canvas may round a dimmed channel differently by one byte.
        const assertDimmed = async (point, rgb) => {
          const pixel = await visiblePixel(page, point);
          assert.ok(
            rgb.every(
              (channel, i) =>
                Math.abs(pixel[i] - Math.round(channel * 0.55)) <= 1,
            ),
            `Expected a dimmed ${rgb.join(",")} fill, got ${pixel.join(",")}`,
          );
        };
        await assertDimmed(eastFill, [222, 118, 110]);
        await assertDimmed(asiaWater, waterColor.slice(0, 3));
        assert.deepEqual(
          await visiblePixel(page, insideBorder(30)),
          waterColor,
        );
        assert.deepEqual(
          await visiblePixel(page, insideBorder(60)),
          [255, 255, 255, 255],
        );

        await page.getByRole("button", { name: "Legend", exact: true }).click();
        await search.fill("asia");
        await legend.getByRole("button", { name: /Asia/ }).click();
        await legend.getByRole("button", { name: "Collapse legend" }).click();
        assert.deepEqual(
          await visiblePixel(page, insideBorder(60)),
          [233, 180, 76, 255],
        );
        assert.deepEqual(
          await visiblePixel(page, insideBorder(105)),
          [255, 255, 255, 255],
        );

        await page.getByRole("button", { name: "Legend", exact: true }).click();
        const clear = legend.getByRole("button", { name: "Clear selection" });
        if (options.hasTouch) await clear.tap();
        else await clear.click();
        assert.equal(await search.inputValue(), "asia");
        assert.equal(await page.evaluate(() => document.activeElement.id), "legend-panel");
        await search.fill("africa");
        assert.equal(await africa.getAttribute("aria-pressed"), "false");
        assert.deepEqual(errors, []);
      } finally {
        await page.close();
      }
    },
  );
}

test("selection matches the displayed pixel at a land-water boundary", async () => {
  for (const deviceScaleFactor of [1, 2]) {
    const page = await browser.newPage({
      viewport: { width: 320, height: 568 },
      deviceScaleFactor,
    });
    try {
      if (deviceScaleFactor === 2) {
        await page.addInitScript(() => {
          const getContext = HTMLCanvasElement.prototype.getContext;
          HTMLCanvasElement.prototype.getContext = function (type, ...args) {
            return type === "webgl2" ? null : getContext.call(this, type, ...args);
          };
        });
      }
      await loaded(page, `/${candidate}/index.html`, "v9.0");
      await page.getByRole("button", { name: "Collapse legend" }).click();
      const canvas = page.locator("#canvas");
      const boundary = { x: 213, y: (await pickPoint(page, 80, 20)).y };
      // The coast crosses this CSS pixel at x = 213⅓. Its first backing pixel
      // samples land at 1× (x = 213.5) and water at 2× (x = 213.25).
      const land = deviceScaleFactor === 1;
      assert.deepEqual(
        await visiblePixel(page, boundary),
        land ? [222, 118, 110, 255] : [84, 141, 183, 255],
      );
      await canvas.click({ position: { ...boundary, x: land ? 213 : 213.4 } });
      assert.match(
        await page.locator("#selection").textContent(),
        land ? /Asia \(land\)$/ : /Asia \(water\)$/,
      );
    } finally {
      await page.close();
    }
  }
});

test("the legend and map controls fit in narrow and short windows", async () => {
  const page = await browser.newPage({
    viewport: { width: 320, height: 568 },
    isMobile: true,
    hasTouch: true,
  });
  try {
    await loaded(page, `/${candidate}/index.html`, "v9.0");
    const selection = page.locator("#selection");
    const short = await selection.boundingBox();
    await selection.evaluate((element) => {
      element.textContent = "Cell 28672, 14608 · 49.87656°, -101.24863° · North America (land)";
    });
    const wrapped = await selection.boundingBox();
    assert.ok(wrapped.height > short.height);
    assert.ok(wrapped.x >= 0 && wrapped.x + wrapped.width <= 320);

    const map = page.locator("#map");
    const toolbar = page.locator(".tools");
    const panel = page.getByRole("region", { name: "Map legend" });
    const collapse = page.getByRole("button", { name: "Collapse legend" });
    const toggle = page.getByRole("button", { name: "Legend", exact: true });
    const list = panel.getByRole("group");
    const assertFits = async (legend) => {
      const area = await map.boundingBox();
      const tools = await toolbar.boundingBox();
      const box = await legend.boundingBox();
      const readout = await selection.boundingBox();
      assert.ok(box.y >= area.y);
      assert.ok(box.y + box.height < readout.y);
      if (box.x + box.width > tools.x) assert.ok(box.y >= tools.y + tools.height);
    };
    await assertFits(panel);
    for (const viewport of [{ width: 667, height: 240 }, { width: 320, height: 320 }]) {
      await page.setViewportSize(viewport);
      await assertFits(panel);
      assert.equal(await list.evaluate((element) => {
        element.scrollTop = element.scrollHeight;
        return element.scrollTop > 0;
      }), true);
      await collapse.tap();
      await assertFits(toggle);
      await toggle.tap();
      await assertFits(panel);
    }
  } finally {
    await page.close();
  }
});

test("rotation refits the world and preserves a zoomed location", async () => {
  const portrait = { width: 390, height: 750 };
  const landscape = { width: 750, height: 340 };
  const page = await browser.newPage({ viewport: portrait, isMobile: true, hasTouch: true });
  try {
    await loaded(page, `/${candidate}/index.html`, "v9.0");
    await page.getByRole("button", { name: "Collapse legend" }).tap();
    const canvas = page.locator("#canvas");

    async function inspect(offsetX = 0) {
      const box = await canvas.boundingBox();
      await page.touchscreen.tap(box.x + box.width / 2 + offsetX, box.y + box.height / 2);
      const details = await page.locator("#selection").textContent();
      return details.match(/^Cell \d+, \d+/)?.[0];
    }
    async function resize(viewport) {
      await page.setViewportSize(viewport);
      await page.waitForFunction(() => {
        const canvas = document.querySelector("#canvas");
        return canvas.width === canvas.clientWidth && canvas.height === canvas.clientHeight;
      });
    }

    const worldCenter = await inspect();
    const portraitCell = await inspect(90);
    assert.equal(worldCenter, "Cell 60, 30");
    assert.equal(portraitCell, "Cell 87, 30");
    await resize(landscape);
    assert.equal(await inspect(), worldCenter);
    assert.equal(await inspect(90), "Cell 80, 30");
    await resize(portrait);
    assert.equal(await inspect(90), portraitCell);

    const touch = await page.context().newCDPSession(page);
    const box = await canvas.boundingBox();
    const x = box.x + box.width / 2;
    const y = box.y + box.height / 2;
    const fingers = (radius) => [{ x: x - radius, y, id: 0 }, { x: x + radius, y, id: 1 }];
    await touch.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: fingers(50) });
    await touch.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: fingers(60) });
    await touch.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
    const pinchedCell = await inspect(90);
    assert.equal(pinchedCell, "Cell 83, 30");
    await resize(landscape);
    assert.equal(await inspect(90), "Cell 80, 30");
    await resize(portrait);
    assert.equal(await inspect(90), pinchedCell);
    await page.getByRole("button", { name: "World", exact: true }).tap();
    assert.equal(await inspect(90), portraitCell);

    const zoomIn = page.getByRole("button", { name: "Zoom in" });
    await zoomIn.tap();
    await zoomIn.tap();
    await canvas.focus();
    await page.keyboard.press("d");
    await page.keyboard.press("s");
    const zoomedCenter = await inspect();
    const zoomedCell = await inspect(90);
    assert.match(zoomedCenter, /^Cell /);
    assert.notEqual(zoomedCenter, worldCenter);
    await resize(landscape);
    assert.equal(await inspect(), zoomedCenter);
    assert.equal(await inspect(90), zoomedCell);
    await resize(portrait);
    assert.equal(await inspect(), zoomedCenter);
  } finally {
    await page.close();
  }
});

test("two fingers zoom the map around their moving midpoint", async () => {
  const page = await browser.newPage({
    viewport: { width: 390, height: 700 },
    isMobile: true,
    hasTouch: true,
  });
  try {
    await loaded(page, `/${candidate}/index.html`, "v9.0");
    await page.getByRole("button", { name: "Collapse legend" }).tap();
    const canvas = await page.locator("#canvas").boundingBox();
    const middle = Math.round(canvas.x + canvas.width * 0.6);
    const y = Math.round(canvas.y + canvas.height / 2);
    const selection = page.locator("#selection");
    const touch = await page.context().newCDPSession(page);

    async function inspect(x) {
      await page.touchscreen.tap(x, y);
      return selection.textContent();
    }
    function fingers(x, radius) {
      return [{ x: x - radius, y, id: 0 }, { x: x + radius, y, id: 1 }];
    }
    async function pinch(from, to) {
      await touch.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: from });
      await touch.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: to });
      await touch.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
    }

    const anchor = await inspect(middle);
    const beforeZoom = await inspect(middle + 80);
    assert.match(anchor, /^Cell /);
    assert.notEqual(beforeZoom, anchor);

    await pinch(fingers(middle, 30), fingers(middle + 8, 60));
    assert.equal(await selection.textContent(), beforeZoom);
    assert.equal(await page.evaluate(() => visualViewport.scale), 1);
    assert.equal(await inspect(middle + 8), anchor);
    assert.notEqual(await inspect(middle + 80), beforeZoom);

    await pinch(fingers(middle + 8, 60), fingers(middle, 30));
    assert.equal(await inspect(middle + 80), beforeZoom);
  } finally {
    await page.close();
  }
});

test(
  "homepage and preview keep their own map when opening data sources",
  { timeout: 30_000 },
  async () => {
    const page = await browser.newPage();
    try {
      for (const [path, version, name] of [
        ["/", "v8.0", "Africa"],
        [`/${candidate}/index.html`, "v9.0", "Asia"],
        ["/", "v8.0", "Africa"],
      ]) {
        await loaded(page, path, version);
        const africaCount =
          version === "v8.0" ? 85 * mapHeight : 60 * mapHeight;
        assert.equal(
          await page
            .getByRole("button", { name: /Africa/ })
            .locator(".legend-count")
            .textContent(),
          africaCount.toLocaleString() + " cells",
        );
        await page
          .locator("#canvas")
          .click({ position: await pickPoint(page, 90, 20) });
        const selection = await page.locator("#selection").textContent();
        assert.match(selection, new RegExp(`${name} \\(land\\)$`));
        const sources = page.getByRole("button", { name: "Data sources" });
        await sources.click();
        const dialog = page.getByRole("dialog", { name: "Data sources" });
        assert.equal(await dialog.getByRole("link", { name: "OpenStreetMap contributors" }).isVisible(), true);
        assert.equal(await dialog.locator("#inland-water-release").textContent(),
          version === "v8.0" ? ", release 2026-08-19.0" : ", release 2026-10-21.0");
        assert.equal(new URL(page.url()).pathname, path);
        await page.keyboard.press("Escape");
        assert.equal(await dialog.isVisible(), false);
        assert.equal(await sources.evaluate((element) => element === document.activeElement), true);
        assert.equal(await page.locator("#selection").textContent(), selection);
      }
    } finally {
      await page.close();
    }
  },
);

test("small pointer motion still picks a cell while dragging preserves the pick", async () => {
  const page = await browser.newPage({ viewport: { width: 1024, height: 720 } });
  try {
    await loaded(page, `/${candidate}/index.html`, "v9.0");
    await page.getByRole("button", { name: "Collapse legend" }).click();
    const canvas = page.locator("#canvas");
    const box = await canvas.boundingBox();
    const point = await pickPoint(page, 82, 20);
    const color = await visiblePixel(page, point);
    const x = box.x + point.x, y = box.y + point.y;
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x + 3, y);
    await page.mouse.up();
    assert.equal(await canvas.evaluate((element) => element === document.activeElement), true);
    const selection = page.locator("#selection");
    const pick = await selection.textContent();
    assert.match(pick, /^Cell 82, 20 · .* · Asia \(land\)$/);
    assert.deepEqual(await visiblePixel(page, point), color);

    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x + 50, y);
    assert.notDeepEqual(await visiblePixel(page, point), color);
    await page.mouse.move(x + 2, y);
    await page.mouse.up();
    assert.equal(await selection.textContent(), pick);
  } finally {
    await page.close();
  }
});

test("hovering one legend entry brightens it and keeps the other entry outlined", async () => {
  const page = await browser.newPage({ viewport: { width: 1024, height: 720 } });
  try {
    await loaded(page, `/${candidate}/index.html`, "v9.0");
    const africa = page.getByRole("button", { name: /Africa/ });
    const asia = page.getByRole("button", { name: /Asia/ });
    const map = page.locator("#canvas");
    const {x, y, width} = await map.boundingBox();
    const water = await pickPoint(page, 70, 20);
    const border = { x: Math.ceil(width * 60 / mapWidth - 0.5) - 1, y: water.y };
    await africa.click();
    const dimmed = await visiblePixel(page, water);
    assert.deepEqual(await visiblePixel(page, border), [255, 255, 255, 255]);
    await asia.hover();
    assert.deepEqual(await visiblePixel(page, water), [84, 141, 183, 255]);
    assert.deepEqual(await visiblePixel(page, border), [255, 255, 255, 255]);
    assert.equal(await asia.getAttribute("aria-pressed"), "false");
    await page.mouse.move(x + 40, y + water.y);
    assert.deepEqual(await visiblePixel(page, water), dimmed);
  } finally {
    await page.close();
  }
});

test("keyboard focus and map drawing survive legend edits and page caching", async () => {
  const page = await browser.newPage({ viewport: { width: 1024, height: 768 } });
  try {
    await loaded(page, `/${candidate}/index.html`, "v9.0");
    await page.locator("#canvas").focus();
    await page.keyboard.press("Tab");
    assert.equal(await page.evaluate(() => document.activeElement.id), "tool-in");
    await page.keyboard.press("Shift+Tab");
    assert.equal(await page.evaluate(() => document.activeElement.id), "canvas");

    const position = await pickPoint(page, 94, 20);
    assert.deepEqual(await visiblePixel(page, position), [222, 118, 110, 255]);
    await page.evaluate(() => {
      window.dispatchEvent(new PageTransitionEvent("pagehide", { persisted: true }));
      window.dispatchEvent(new PageTransitionEvent("pageshow", { persisted: true }));
    });
    const africa = page.getByRole("button", { name: /Africa/ });
    await africa.focus();
    await page.keyboard.press("Space");
    assert.equal(await africa.getAttribute("aria-pressed"), "true");
    assert.equal(await africa.evaluate((element) => element === document.activeElement), true);
    const dimmed = await visiblePixel(page, position);
    assert.ok(dimmed[0] >= 121 && dimmed[0] <= 123);

    const search = page.getByRole("searchbox", { name: "Search continents" });
    await search.fill("unmatched");
    const clear = page.getByRole("button", { name: "Clear selection" });
    await clear.focus();
    await page.keyboard.press("Space");
    assert.equal(await clear.isVisible(), false);
    assert.equal(await page.evaluate(() => document.activeElement.id), "legend-panel");
    await page.keyboard.press("Tab");
    assert.equal(await search.evaluate((element) => element === document.activeElement), true);
  } finally {
    await page.close();
  }
});

test("legend search clears hover from a removed entry", async () => {
  const page = await browser.newPage({ viewport: { width: 1024, height: 768 } });
  try {
    await loaded(page, `/${candidate}/index.html`, "v9.0");
    const point = await pickPoint(page, 74, 20);
    const color = await visiblePixel(page, point);
    await page.getByRole("button", { name: /Africa/ }).hover();
    assert.notDeepEqual(await visiblePixel(page, point), color);
    await page.getByRole("searchbox").fill("unmatched");
    assert.deepEqual(await visiblePixel(page, point), color);
  } finally {
    await page.close();
  }
});

test("running map recovers in Canvas after losing WebGL", async () => {
  const page = await browser.newPage({ viewport: { width: 1024, height: 768 } });
  try {
    let gridRequests = 0;
    page.on("request", (request) => {
      if (new URL(request.url()).pathname.endsWith(".u32le.gz")) gridRequests++;
    });
    await loaded(page, `/${candidate}/index.html`, "v9.0");
    const point = await pickPoint(page, 90, 20);
    const canvas = page.locator("#canvas");
    const asia = page.getByRole("button", { name: /Asia/ });
    await asia.click();
    await page.getByRole("button", { name: "Zoom in" }).click();
    await canvas.click({ position: point });
    const selected = await page.locator("#selection").textContent();
    assert.match(selected, /^Cell 75, 25 ·/);

    await canvas.evaluate((surface) => {
      surface.getContext("webgl2").getExtension("WEBGL_lose_context").loseContext();
    });
    await page.waitForFunction(() => Boolean(document.querySelector("#canvas").getContext("2d")));
    assert.equal(await page.locator("#status").textContent(), "");
    assert.equal(await asia.getAttribute("aria-pressed"), "true");
    assert.equal(await page.locator("#selection").textContent(), selected);
    await canvas.click({ position: { x: point.x - 36, y: point.y } });
    assert.notEqual(await page.locator("#selection").textContent(), selected);
    await canvas.click({ position: point });
    assert.equal(await page.locator("#selection").textContent(), selected);
    assert.equal(gridRequests, 2);
  } finally {
    await page.close();
  }
});

test("WebGL agrees with Canvas at distant subpixel boundaries", async () => {
  const page = await browser.newPage();
  try {
    await page.goto(`${origin}/health`);
    const { gpu, cpu } = await page.evaluate(async (prefix) => {
      const { createRenderer, renderPixels } = await import(`/${prefix}/grid-renderer.js`);
      const canvas = document.createElement("canvas");
      canvas.width = 32;
      canvas.height = 1;
      const meta = {
        width: 131072,
        height: 1,
        palette: new Map([[1, [244, 10, 14]], [2, [10, 24, 234]]]),
      };
      const data = {
        rows: Uint32Array.of(0, 2),
        runs: Uint32Array.of(100000, 1, 131072, 2),
      };
      const renderer = createRenderer(canvas, meta, data);
      const gl = canvas.getContext("webgl2");
      const scale = 7.37;
      const ox = 16.55 - scale * 100000;
      renderer.draw({ scale, ox, oy: 0, dpr: 1 });
      const actual = new Uint8Array(32 * 4);
      gl.readPixels(0, 0, 32, 1, gl.RGBA, gl.UNSIGNED_BYTE, actual);
      renderer.destroy();
      return {
        gpu: Array.from(actual),
        cpu: Array.from(new Uint8Array(renderPixels(meta, data, 32, 1, scale, ox, 0).buffer)),
      };
    }, candidate);
    assert.deepEqual(gpu, cpu);
  } finally {
    await page.close();
  }
});

test("grid downloads start while the legend response is pending", async () => {
  const page = await browser.newPage();
  try {
    const legend = Promise.withResolvers();
    await page.route("**/legend/entities.json", (route) => legend.resolve(route));
    const [route] = await Promise.all([
      legend.promise,
      page.waitForRequest("**/rows.u32le.gz", { timeout: 5000 }),
      page.waitForRequest("**/runs.u32le.gz", { timeout: 5000 }),
      page.goto(`${origin}/${candidate}/index.html`, { waitUntil: "commit" }),
    ]);
    assert.equal(await page.locator("#status").textContent(), "Loading map…");
    await route.continue();
    await page.waitForFunction(
      () => document.querySelector("#status").textContent !== "Loading map…",
    );
    assert.equal(await page.locator("#status").textContent(), "");
  } finally {
    await page.close();
  }
});

test(
  "missing or corrupted map data leaves a clear error and no selectable map",
  { timeout: 30_000 },
  async () => {
    const page = await browser.newPage();
    try {
      for (const [path, message] of [
        [
          "/releases/v9.1-rc.1/index.html",
          "Native map checksum mismatch",
        ],
        ["/releases/v9.2-rc.1/index.html", "Native map could not load"],
        ["/releases/v9.3-rc.1/index.html", "Map legend could not load"],
      ]) {
        await page.goto(origin + path);
        await page.locator("#status.error").waitFor();
        assert.equal(await page.locator("#status").textContent(), message);
        assert.equal(await page.locator(".legend-item").count(), 0);
        await page
          .locator("#canvas")
          .click({ position: await pickPoint(page, 90, 20) });
        assert.equal(
          await page.locator("#selection").textContent(),
          "Click a cell to select it.",
        );
      }
    } finally {
      await page.close();
    }
  },
);

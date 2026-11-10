import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { once } from 'node:events';
import { after, before, test } from 'node:test';
import { gzipSync } from 'node:zlib';
import { chromium } from 'playwright';
import worker from '../worker.js';

const viewer = new URL('../viewer/', import.meta.url);
const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex');
const mapWidth = 120;
const mapHeight = 60;
const published = 'review/releases/v8.0-rc.1';
const candidate = 'review/releases/v9.0-rc.1';
const objects = new Map();

function store(key, bytes, type) {
  const body = Buffer.from(bytes);
  objects.set(key, {
    body,
    httpEtag: `"${sha256(body)}"`,
    writeHttpMetadata(headers) { headers.set('Content-Type', type); },
  });
}

function words(values) {
  const bytes = Buffer.alloc(values.length * 4);
  values.forEach((value, i) => bytes.writeUInt32LE(value, i * 4));
  return bytes;
}

function bundle(prefix, version, east) {
  const rows = words(Array.from({ length: mapHeight + 1 }, (_, y) => y * 5));
  const runs = words(Array.from({ length: mapHeight }, () => [30, 1, 60, 17, 80, 2, 105, east, 120, 7]).flat());
  const config = JSON.parse(readFileSync(new URL('config.json', viewer)));
  Object.assign(config, {
    width: mapWidth, height: mapHeight, step: 360 / mapWidth, map_version: version,
    legend: 'legend/continents.json',
    categories: [
      { id: 1, entity_id: 1, physical_class: 'water' },
      { id: 2, entity_id: 2, physical_class: 'water' },
      { id: 7, entity_id: 7, physical_class: 'water' },
      { id: 17, entity_id: 1, physical_class: 'land' },
      { id: 18, entity_id: 2, physical_class: 'land' },
    ],
    local_grid: {
      run_count: mapHeight * 5, rows: 'rows.u32le.gz', runs: 'runs.u32le.gz',
      rows_sha256: sha256(rows), runs_sha256: sha256(runs),
    },
    combined_sha256: sha256(Buffer.concat([rows, runs])),
  });
  store(`${prefix}/legend/continents.json`, JSON.stringify([
    { id: 1, name: 'Africa', color: [233, 180, 76], count: (60 + (east === 17 ? 25 : 0)) * mapHeight },
    { id: 2, name: 'Asia', color: [222, 118, 110], count: (20 + (east === 18 ? 25 : 0)) * mapHeight },
    { id: 7, name: 'Atlantic Ocean', color: config.water_rgb, count: 15 * mapHeight },
  ]), 'application/json');
  store(`${prefix}/config.json`, JSON.stringify(config), 'application/json');
  store(`${prefix}/rows.u32le.gz`, gzipSync(rows), 'application/gzip');
  store(`${prefix}/runs.u32le.gz`, gzipSync(runs), 'application/gzip');
  for (const name of ['app.js', 'grid-data.js', 'grid-renderer.js', 'legend-model.js']) {
    store(`${prefix}/${name}`, readFileSync(new URL(name, viewer)), 'text/javascript');
  }
  store(`${prefix}/style.css`, readFileSync(new URL('style.css', viewer)), 'text/css');
  store(`${prefix}/sources.html`, readFileSync(new URL('sources.html', viewer)), 'text/html');
  const index = readFileSync(new URL('index.html', viewer), 'utf8')
    .replace('<head>', `<head><base href="/${prefix}/">`);
  store(`${prefix}/index.html`, index, 'text/html');
  return index;
}

let browser;
let server;
let origin;
before(async () => {
  store('review/index.html', bundle(published, 'v8.0', 17), 'text/html');
  store('review/previews/v9.0/index.html', bundle(candidate, 'v9.0', 18), 'text/html');
  const corrupt = 'review/releases/v9.1-rc.1';
  store('review/previews/v9.1/index.html', bundle(corrupt, 'v9.1', 18), 'text/html');
  // Valid gzip with different decoded bytes exercises the viewer's checksum.
  store(`${corrupt}/runs.u32le.gz`, gzipSync(words([1, 17])), 'application/gzip');
  const missing = 'review/releases/v9.2-rc.1';
  store('review/previews/v9.2/index.html', bundle(missing, 'v9.2', 18), 'text/html');
  objects.delete(`${missing}/rows.u32le.gz`);
  const missingLegend = 'review/releases/v9.3-rc.1';
  store('review/previews/v9.3/index.html', bundle(missingLegend, 'v9.3', 18), 'text/html');
  objects.delete(`${missingLegend}/legend/continents.json`);

  server = createServer(async (request, reply) => {
    try {
      const response = await worker.fetch(new Request(new URL(request.url, origin), {
        method: request.method, headers: request.headers,
      }), { ATLAS: { get: async (key) => objects.get(key) } });
      reply.writeHead(response.status, Object.fromEntries(response.headers));
      reply.end(Buffer.from(await response.arrayBuffer()));
    } catch (error) {
      reply.writeHead(500).end(String(error));
    }
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  origin = `http://127.0.0.1:${server.address().port}`;
  browser = await chromium.launch({ args: ['--enable-unsafe-swiftshader'] });
});

after(async () => {
  try { await browser?.close(); }
  finally { if (server?.listening) await new Promise((resolve) => server.close(resolve)); }
});

async function loaded(page, path, version) {
  const response = await page.goto(origin + path);
  assert.equal(response.status(), 200);
  await page.waitForFunction(() => document.querySelector('#status').textContent !== 'Loading map…');
  assert.equal(await page.locator('#status').textContent(), '');
  assert.ok((await page.locator('#map-release').textContent()).startsWith(`${version.toUpperCase()} · SHA-256 `));
}

async function pickPoint(page, x, y) {
  const { width, height } = await page.locator('#canvas').boundingBox();
  const scale = Math.min(width / mapWidth, height / mapHeight);
  return {
    x: Math.round(width / 2 + (x + 0.5 - mapWidth / 2) * scale),
    y: Math.round(height / 2 + (y + 0.5 - mapHeight / 2) * scale),
  };
}

async function visiblePixel(page, position) {
  const canvas = await page.locator('#canvas').boundingBox();
  const png = await page.screenshot({ clip: {
    x: Math.round(canvas.x) + position.x, y: Math.round(canvas.y) + position.y, width: 1, height: 1,
  } });
  return page.evaluate(async (base64) => {
    const bytes = Uint8Array.from(atob(base64), (char) => char.charCodeAt(0));
    const image = await createImageBitmap(new Blob([bytes], { type: 'image/png' }));
    const canvas = new OffscreenCanvas(1, 1);
    const context = canvas.getContext('2d');
    context.drawImage(image, 0, 0);
    return [...context.getImageData(0, 0, 1, 1).data];
  }, png.toString('base64'));
}

for (const { name, options, fallback } of [
  { name: 'desktop WebGL', options: { viewport: { width: 1024, height: 720 } }, fallback: false },
  { name: 'mobile touch and Canvas fallback',
    options: { viewport: { width: 390, height: 700 }, isMobile: true, hasTouch: true }, fallback: true },
]) {
  test(`${name} renders, selects cells, and filters the legend`, { timeout: 30_000 }, async () => {
    const page = await browser.newPage(options);
    try {
      if (fallback) await page.addInitScript(() => {
        for (const type of [HTMLCanvasElement, OffscreenCanvas]) {
          const getContext = type.prototype.getContext;
          type.prototype.getContext = function (kind, ...args) {
            return kind === 'webgl2' ? null : getContext.call(this, kind, ...args);
          };
        }
      });
      const errors = [];
      page.on('pageerror', (error) => errors.push(error.message));
      await loaded(page, '/v9.0-rc', 'v9.0');
      const canvas = page.locator('#canvas');
      assert.equal(await canvas.evaluate((element, type) => Boolean(element.getContext(type)), fallback ? '2d' : 'webgl2'), true);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth === innerWidth), true);
      const legend = page.getByRole('region', { name: 'Map legend' });
      await legend.getByRole('button', { name: 'Collapse legend' }).click();
      assert.equal(await legend.isVisible(), false);
      const east = await pickPoint(page, 90, 20);
      const eastFill = await pickPoint(page, 94, 20);
      const west = await pickPoint(page, 20, 20);
      const africaLand = await pickPoint(page, 40, 20);
      const asiaWater = await pickPoint(page, 70, 20);
      const { width } = await canvas.boundingBox();
      const insideBorder = column => ({ x: Math.ceil(width * column / mapWidth - 0.5) - 1, y: west.y });
      const waterColor = [84, 141, 183, 255];
      assert.deepEqual(await visiblePixel(page, east), [222, 118, 110, 255]);
      assert.deepEqual(await visiblePixel(page, west), waterColor);
      assert.deepEqual(await visiblePixel(page, asiaWater), waterColor);

      const pick = () => fallback ? canvas.tap({ position: east }) : canvas.click({ position: east });
      const selection = page.locator('#selection');
      await pick();
      assert.equal(await selection.textContent(), 'Cell 90, 20 · 28.50000°, 91.50000° · Asia (land)');
      await page.getByRole('button', { name: 'Zoom in' }).click();
      await pick();
      assert.match(await selection.textContent(), /^Cell 75, 25 ·/);
      await page.getByRole('button', { name: 'World', exact: true }).click();
      await pick();
      assert.match(await selection.textContent(), /^Cell 90, 20 ·/);

      const search = page.getByRole('searchbox', { name: 'Search continents' });
      await page.getByRole('button', { name: 'Legend', exact: true }).click();
      assert.equal(await search.evaluate((element) => element === document.activeElement), true);
      await search.fill('africa');
      assert.equal(await legend.locator('.legend-item').count(), 1);
      const africa = legend.getByRole('button', { name: /Africa/ });
      await africa.click();
      assert.equal(await africa.getAttribute('aria-pressed'), 'true');
      await legend.getByRole('button', { name: 'Collapse legend' }).click();
      assert.deepEqual(await visiblePixel(page, west), waterColor);
      assert.deepEqual(await visiblePixel(page, africaLand), [233, 180, 76, 255]);
      // WebGL and Canvas may round a dimmed channel differently by one byte.
      const assertDimmed = async (point, rgb) => {
        const pixel = await visiblePixel(page, point);
        assert.ok(rgb.every((channel, i) => Math.abs(pixel[i] - Math.round(channel * 0.55)) <= 1),
          `Expected a dimmed ${rgb.join(',')} fill, got ${pixel.join(',')}`);
      };
      await assertDimmed(eastFill, [222, 118, 110]);
      await assertDimmed(asiaWater, waterColor.slice(0, 3));
      assert.deepEqual(await visiblePixel(page, insideBorder(30)), waterColor);
      assert.deepEqual(await visiblePixel(page, insideBorder(60)), [255, 255, 255, 255]);

      await page.getByRole('button', { name: 'Legend', exact: true }).click();
      await search.fill('asia');
      await legend.getByRole('button', { name: /Asia/ }).click();
      await legend.getByRole('button', { name: 'Collapse legend' }).click();
      assert.deepEqual(await visiblePixel(page, insideBorder(60)), [233, 180, 76, 255]);
      assert.deepEqual(await visiblePixel(page, insideBorder(105)), [255, 255, 255, 255]);

      await page.getByRole('button', { name: 'Legend', exact: true }).click();
      await legend.getByRole('button', { name: 'Clear filter' }).click();
      await search.fill('africa');
      assert.equal(await africa.getAttribute('aria-pressed'), 'false');
      assert.deepEqual(errors, []);
    } finally { await page.close(); }
  });
}

test('homepage and preview load their own map and source files', { timeout: 30_000 }, async () => {
  const page = await browser.newPage();
  try {
    for (const [path, version, prefix, name] of [
      ['/', 'v8.0', published, 'Africa'], ['/v9.0-rc', 'v9.0', candidate, 'Asia'],
      [`/${candidate}/index.html`, 'v9.0', candidate, 'Asia'], ['/', 'v8.0', published, 'Africa'],
    ]) {
      await loaded(page, path, version);
      const africaCount = version === 'v8.0' ? 85 * mapHeight : 60 * mapHeight;
      assert.equal(await page.getByRole('button', { name: /Africa/ }).locator('.legend-count').textContent(),
        africaCount.toLocaleString() + ' cells');
      await page.locator('#canvas').click({ position: await pickPoint(page, 90, 20) });
      assert.match(await page.locator('#selection').textContent(), new RegExp(`${name} \\(land\\)$`));
      await page.getByRole('link', { name: 'Data sources' }).click();
      assert.equal(new URL(page.url()).pathname, `/${prefix}/sources.html`);
      assert.match(await page.title(), /Data sources/);
    }
  } finally { await page.close(); }
});

test('missing or corrupted map data leaves a clear error and no selectable map', { timeout: 30_000 }, async () => {
  const page = await browser.newPage();
  try {
    for (const [path, message] of [
      ['/v9.1-rc', 'Native map checksum mismatch'], ['/v9.2-rc', 'Native map could not load'],
      ['/v9.3-rc', 'Map legend could not load'],
    ]) {
      await page.goto(origin + path);
      await page.locator('#status.error').waitFor();
      assert.equal(await page.locator('#status').textContent(), message);
      assert.equal(await page.locator('.legend-item').count(), 0);
      await page.locator('#canvas').click({ position: await pickPoint(page, 90, 20) });
      assert.equal(await page.locator('#selection').textContent(), 'Click a cell to select it.');
    }
  } finally { await page.close(); }
});

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {chromium} from '@playwright/test';
import {runtimeOwnershipData} from '../src/runtime-ownership.js';
import {decodeDerived} from '../src/derived-records.js';

const [site, output, phase = 'before'] = process.argv.slice(2), origin = new URL(site ?? '');
if (origin.origin !== 'https://worldatlas-explorer.chengshu-li-2013.chatgpt.site' || origin.pathname !== '/' || origin.search || origin.hash || !output || !process.stdin.isTTY) throw Error('Use the production origin and receipt path with hidden credential stdin');
process.stdin.setRawMode(true);
console.log('Ready for private palette verification credential on hidden stdin.');
const token = await new Promise((resolve, reject) => {
  let input = '';
  process.stdin.on('data', chunk => {
    input += chunk.toString(); if (!/[\r\n]/.test(input)) return;
    process.stdin.pause(); process.stdin.setRawMode(false);
    try { const value = JSON.parse(input.trim()).token; input = ''; if (typeof value !== 'string' || !value || /[\r\n]/.test(value)) throw Error(); resolve(value); }
    catch { reject(Error('Invalid hidden credential input')); }
  });
});
let browser, server, runtime;
const buckets = new Map(), receipt = {version: 1, phase, started_at_utc: new Date().toISOString(), site: origin.origin, read_only: true,
  conditions: 'Actual production client/assets/API through fixed-origin GET-only localhost proxy; private header remains server-side. Headless Linux Chromium, 1440x1080, no throttling. Not a physical-device or color-vision certificate.',
  requests: [], selected_profiles: [], page_errors: [], years: []};
const save = () => { fs.mkdirSync(path.dirname(output), {recursive: true}); fs.writeFileSync(output, JSON.stringify(receipt, null, 2) + '\n'); };
try {
  server = http.createServer(async (req, res) => {
    const url = new URL(req.url, origin);
    if (req.method !== 'GET' || req.url.startsWith('//') || url.origin !== origin.origin) { res.writeHead(405); return res.end(); }
    const log = {path: url.pathname, year: url.searchParams.get('year')}; receipt.requests.push(log);
    try {
      const remote = await fetch(url, {headers: {'OAI-Sites-Authorization': 'Bearer ' + token}, redirect: 'error', signal: AbortSignal.timeout(120000)});
      const bytes = Buffer.from(await remote.arrayBuffer()); Object.assign(log, {status: remote.status, bytes: bytes.length});
      if (remote.ok && url.pathname.startsWith('/ownership-runtime/')) {
        const data = JSON.parse(bytes[0] === 31 && bytes[1] === 139 ? gunzipSync(bytes) : bytes);
        log.sha256 = createHash('sha256').update(bytes).digest('hex');
        if (url.pathname.endsWith('/index.json')) runtime = data; else buckets.set(url.pathname.split('/').at(-1), data);
      }
      const headers = {}; for (const key of ['content-type', 'cache-control', 'etag', 'last-modified']) if (remote.headers.has(key)) headers[key] = remote.headers.get(key);
      res.writeHead(remote.status, headers); res.end(bytes);
    } catch { log.failed = true; if (!res.headersSent) res.writeHead(502); res.end('Verification transport unavailable'); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  browser = await chromium.launch(); const page = await browser.newPage({viewport: {width: 1440, height: 1080}});
  receipt.browser_version = browser.version(); page.on('pageerror', error => receipt.page_errors.push(error.message));
  await page.goto('http://127.0.0.1:' + server.address().port, {waitUntil: 'domcontentloaded', timeout: 120000});
  await page.locator('#loading').waitFor({state: 'hidden', timeout: 180000});
  const canvas = () => page.locator('.atlas-pixel-canvas').evaluate(node => ({...node.dataset}));
  await page.waitForFunction(() => document.querySelector('.atlas-pixel-canvas')?.dataset.rendered === 'true', null, {timeout: 180000});
  const before = await canvas();
  for (const year of [1950, 1951, 2020, 1950]) {
    const old = await canvas();
    await page.locator('#year-input').fill(String(year)); await page.evaluate(() => document.querySelector('#year-form').requestSubmit());
    await page.waitForFunction(({year, uploads}) => document.querySelector('#map-year')?.textContent === year.toLocaleString('en-US') + ' AD' && document.querySelector('#loading')?.hidden && Number(document.querySelector('.atlas-pixel-canvas')?.dataset.uploads) > uploads,
      {year, uploads: Number(old.uploads)}, {timeout: 180000});
    assert.equal(await page.locator('#year-error').textContent(), '');
    receipt.years.push({year, legend: await page.locator('#legend-items .legend-item').evaluateAll(items => items.map(row => ({label: row.textContent.trim(), color: row.querySelector('i') ? getComputedStyle(row.querySelector('i')).backgroundColor : null}))), canvas: await canvas()}); save();
  }
  const selected = runtime.buckets.find(row => row.valid_from <= 1950 && 1950 < row.valid_to);
  assert.ok(buckets.has(selected.path));
  const data = runtimeOwnershipData(runtime, buckets.get(selected.path), 1950), records = new Map(decodeDerived(data.parts, data.index, 1950).map(row => [row.location_id, row]));
  receipt.ownership_source_index_sha256 = runtime.source_index_sha256;
  for (const query of ['Beijing', 'Taipei']) {
    await page.locator('#search').fill(query); await page.waitForTimeout(100);
    const results = await page.locator('[data-result]').evaluateAll(nodes => nodes.map(n => ({id: n.dataset.result, label: n.textContent.trim()})));
    assert.ok(results.length > 0, 'Search result required for ' + query); const result = results[0];
    await page.locator('[data-result]').first().click(); await page.waitForTimeout(500);
    const values = await page.locator('.profile-attributes dd').allTextContents(), derived = records.get(result.id);
    receipt.selected_profiles.push({query, search_results: results, selected_id: result.id, year: 1950, displayed_values: values,
      derived_source_record: derived ? {id: derived.id, category_id: derived.category_id, value: derived.value, status: derived.status, valid_from: derived.valid_from, valid_to: derived.valid_to, method: derived.method, source: derived.source} : null});
    await page.screenshot({path: output.replace(/\.json$/, '') + '-' + query.toLowerCase() + '.png'});
    await page.locator('#close-details').click(); save();
  }
  const after = await canvas(); assert.equal(after.compilations, before.compilations); assert.equal(after.ownershipUploads, before.ownershipUploads); assert.deepEqual(receipt.page_errors, []);
  receipt.completed = true; receipt.completed_at_utc = new Date().toISOString(); save();
  console.log(JSON.stringify({completed: true, years: receipt.years.length, profiles: receipt.selected_profiles.length, navigation_ownership_delta: 0, output}));
} catch (error) {
  receipt.completed = false; receipt.failure = error.name === 'TimeoutError' ? 'browser-timeout' : 'verification-assertion-or-transport-failed'; save();
  console.error(JSON.stringify({completed: false, reason: receipt.failure, output})); process.exitCode = 1;
} finally { await browser?.close(); if (server) await new Promise(resolve => server.close(resolve)); }

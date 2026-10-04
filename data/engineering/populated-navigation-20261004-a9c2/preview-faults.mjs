import path from 'node:path';
import http from 'node:http';
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
import {formatYear} from '../../../src/model.js';

const previewDirectory=process.argv[4];
const [site, output] = process.argv.slice(2), origin = new URL(site ?? '');
if (origin.origin !== 'https://worldatlas-explorer.chengshu-li-2013.chatgpt.site' || origin.pathname !== '/' || origin.search || origin.hash || !output || !process.stdin.isTTY) throw Error('Use the WorldAtlas origin and receipt path with hidden credential stdin');
process.stdin.setRawMode(true);
console.log('Ready for private verification credential on hidden stdin.');
const token = await new Promise((resolve, reject) => {
  let input = '';
  process.stdin.on('data', chunk => {
    input += chunk.toString(); if (!/[\r\n]/.test(input)) return;
    process.stdin.pause(); process.stdin.setRawMode(false);
    try { const value = JSON.parse(input.trim()).token; input = ''; if (typeof value !== 'string' || !value || /[\r\n]/.test(value)) throw Error(); resolve(value); }
    catch { reject(Error('Invalid hidden verification input')); }
  });
});
let fault = 'none', browser, server;
const receipt = {version: 1, started_at_utc: new Date().toISOString(), site: origin.origin, read_only: true, candidate_preview: Boolean(previewDirectory),
  conditions: 'Candidate frontend with actual production GET-only data/assets. Faults are injected in this verification transport; no production database revision, outage, content or configuration is changed.',
  physical_mobile: false, requests: [], scenarios: [], page_errors: []};
const save = () => fs.writeFileSync(output, JSON.stringify(receipt, null, 2) + '\n');
try {
  server = http.createServer(async (req, res) => {
    const url = new URL(req.url, origin);
    if (req.method !== 'GET' || req.url.startsWith('//') || url.origin !== origin.origin) { res.writeHead(405); return res.end(); }
    const entry = {path: url.pathname, year: url.searchParams.get('year'), injected: null}; receipt.requests.push(entry);
    if (url.pathname === '/api/map/snapshot' && ['outage', 'conflict-once'].includes(fault)) {
      const status = fault === 'outage' ? 503 : 409; entry.injected = fault; entry.status = status;
      if (fault === 'conflict-once') fault = 'none';
      res.writeHead(status, {'content-type': 'application/json'}); return res.end(JSON.stringify({error: 'Verification transport fault', retryable: status === 409}));
    }
    try {
      const local=previewDirectory&&(url.pathname==='/'?'index.html':/^\/assets\/[a-zA-Z0-9._-]+$/.test(url.pathname)?url.pathname.slice(1):null);
      if(local&&fs.existsSync(path.join(previewDirectory,local))){const bytes=fs.readFileSync(path.join(previewDirectory,local));res.writeHead(200,{'Content-Type':local.endsWith('.js')?'text/javascript':local.endsWith('.css')?'text/css':'text/html'});return res.end(bytes);}
const remote = await fetch(url, {headers: {'OAI-Sites-Authorization': 'Bearer ' + token}, redirect: 'error', signal: AbortSignal.timeout(120000)});
      let bytes = Buffer.from(await remote.arrayBuffer()); entry.status = remote.status;
      if (fault === 'revision-once' && ['/api/geography/temporal/snapshot', '/api/map/snapshot'].includes(url.pathname) && remote.ok) {
        const page = JSON.parse(bytes), target = url.pathname === '/api/map/snapshot' ? page.temporal_geography?.records : page;
        if (target) { assert.ok(Number.isSafeInteger(target.revision));
          entry.injected = fault; entry.original_revision = target.revision; target.revision++; bytes = Buffer.from(JSON.stringify(page)); fault = 'none';
        }
      }
      const headers = {}; for (const key of ['content-type', 'cache-control', 'etag', 'last-modified']) if (remote.headers.has(key)) headers[key] = remote.headers.get(key);
      res.writeHead(remote.status, headers); res.end(bytes);
    } catch { entry.failed = true; if (!res.headersSent) res.writeHead(502); res.end('Verification transport unavailable'); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  browser = await chromium.launch(); const page = await browser.newPage({viewport: {width: 1440, height: 1080}});
  page.on('pageerror', error => receipt.page_errors.push(error.message));
  await page.goto('http://127.0.0.1:' + server.address().port, {waitUntil: 'domcontentloaded'});
  await page.locator('#loading').waitFor({state: 'hidden', timeout: 180000});
  await page.waitForFunction(() => document.querySelector('.atlas-pixel-canvas')?.dataset.rendered === 'true', null, {timeout: 180000});
  const canvas = () => page.locator('.atlas-pixel-canvas').evaluate(node => ({...node.dataset}));
  async function select(year, label, injectedFault = 'none') {
    fault = injectedFault; const before = await canvas(), from = receipt.requests.length;
    await page.locator('#year-input').fill(String(year)); await page.evaluate(() => document.querySelector('#year-form').requestSubmit());
    await page.waitForFunction(({year, uploads}) => document.querySelector('#map-year')?.textContent === year && document.querySelector('#loading')?.hidden && Number(document.querySelector('.atlas-pixel-canvas')?.dataset.uploads) > uploads,
      {year: formatYear(year), uploads: Number(before.uploads)}, {timeout: 180000});
    const after = await canvas(), error = await page.locator('#year-error').textContent();
    assert.equal(after.compilations, before.compilations); assert.equal(after.ownershipUploads, before.ownershipUploads);
    const result = {label, year, injected_fault: injectedFault, error, request_range: [from, receipt.requests.length], ownership_compilation_delta: 0, ownership_upload_delta: 0};
    receipt.scenarios.push(result); save(); return result;
  }
  assert.equal((await select(2020, 'complete-supported-snapshot')).error, '');
  assert.equal((await select(2020, 'retry-conflict', 'conflict-once')).error, '');
  assert.equal((await select(2020, 'restart-scalar-and-geography-revision', 'revision-once')).error, '');
  assert.ok(receipt.requests.some(row => row.injected === 'revision-once'));
  assert.match((await select(2020, 'same-year-complete-cache-on-outage', 'outage')).error, /last complete snapshot for this year/);
  assert.match((await select(2021, 'other-year-does-not-reuse-evidence', 'outage')).error, /Dated attribute values are unavailable/);
  for (const year of [0, -3001, 2027]) {
    const from = receipt.requests.length, previous = await page.locator('#map-year').textContent();
    await page.locator('#year-input').fill(String(year)); await page.evaluate(() => document.querySelector('#year-form').requestSubmit());
    assert.equal(await page.locator('#map-year').textContent(), previous); assert.equal(receipt.requests.length, from);
    assert.match(await page.locator('#year-error').textContent(), /There is no year zero/);
    receipt.scenarios.push({label: 'unsupported-year', year, visible_year: previous, new_requests: 0});
  }
  assert.equal((await select(2021, 'recovery-refresh')).error, ''); assert.deepEqual(receipt.page_errors, []);
  receipt.completed = true; receipt.completed_at_utc = new Date().toISOString(); save(); console.log(JSON.stringify({completed: true, scenarios: receipt.scenarios.length, output}));
} catch (error) {
  receipt.completed = false; receipt.failure = error.name === 'TimeoutError' ? 'browser-timeout' : 'verification-assertion-or-transport-failed'; save();
  console.error(JSON.stringify({completed: false, reason: receipt.failure, output})); process.exitCode = 1;
} finally { await browser?.close(); if (server) await new Promise(resolve => server.close(resolve)); }

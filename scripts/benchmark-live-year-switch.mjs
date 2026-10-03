import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import {gzipSync} from 'node:zlib';
import {performance} from 'node:perf_hooks';
import {chromium} from '@playwright/test';
import {formatYear} from '../src/model.js';

const [site, output, phase = 'before', suite = 'historical'] = process.argv.slice(2), origin = new URL(site ?? '');
if (!['historical', 'supported'].includes(suite)) throw Error('Use historical or supported measurement suite');
if (origin.origin !== 'https://worldatlas-explorer.chengshu-li-2013.chatgpt.site' || origin.pathname !== '/' || origin.search || origin.hash || !output || !process.stdin.isTTY) throw Error('Use the WorldAtlas origin and receipt path with hidden credential stdin');
process.stdin.setRawMode(true);
console.log('Ready for private verification credential on hidden stdin.');
const token = await new Promise((resolve, reject) => {
  let value = '';
  process.stdin.on('data', chunk => {
    value += chunk.toString();
    if (!/[\r\n]/.test(value)) return;
    process.stdin.pause(); process.stdin.setRawMode(false);
    try { const payload = JSON.parse(value.trim()); if (typeof payload.token !== 'string' || !payload.token || /[\r\n]/.test(payload.token)) throw Error(); resolve(payload.token); }
    catch { reject(Error('Invalid hidden verification input')); }
  });
});
const requests = [], errors = [], navigation = [], trace = [];
let browser, server;
const receipt = {version: 1, phase, site: origin.origin, started_at_utc: new Date().toISOString(), read_only: true,
  conditions: {suite, transport: 'GET-only localhost proxy of actual private production responses; service credential remains server-side',
    browser: 'headless Chromium on Linux, 1440x1080, no CPU/network throttling', physical_mobile: false,
    cold_definition: 'Fresh browser context/asset cache; first in this verification session. Provider idle/wake state is unknown.'},
  requests, navigation, page_errors: errors};
const save = () => { fs.mkdirSync(path.dirname(output), {recursive: true}); fs.writeFileSync(output, JSON.stringify(receipt, null, 2) + '\n'); };
try {
  server = http.createServer(async (req, res) => {
    const started = performance.now(), url = new URL(req.url, origin);
    if (req.method !== 'GET' || req.url.startsWith('//') || url.origin !== origin.origin) { res.writeHead(405); return res.end(); }
    const log = {path: url.pathname, year: url.searchParams.get('year'), stream: url.searchParams.get('stream'),
      has_cursor: Boolean(url.searchParams.get('cursor')), started_ms: started};
    requests.push(log);
    try {
      const remote = await fetch(url, {headers: {'OAI-Sites-Authorization': 'Bearer ' + token}, redirect: 'error', signal: AbortSignal.timeout(120000)});
      log.headers_ms = performance.now() - started;
      const bytes = Buffer.from(await remote.arrayBuffer());
      Object.assign(log, {status: remote.status, response_bytes: bytes.length, total_ms: performance.now() - started});
      // Never copy dispatch credentials, cookies, or private response headers to
      // Chromium/traces. Only headers needed to serve the response are allowed.
      const headers = {};
      for (const key of ['content-type', 'cache-control', 'etag', 'last-modified']) if (remote.headers.has(key)) headers[key] = remote.headers.get(key);
      if (url.pathname === '/atlas-geography.json') {
        const geo = JSON.parse(bytes); receipt.reference_release = geo.reference_release; receipt.capabilities = geo.contentCapabilities;
      }
      if (url.pathname.startsWith('/api/')) {
        try { const data = JSON.parse(bytes); log.revision = data.revision ?? null; log.has_next_cursor = Boolean(data.next_cursor); }
        catch { log.invalid_json = true; }
      }
      res.writeHead(remote.status, headers); res.end(bytes);
    } catch { log.failed = true; log.total_ms = performance.now() - started; if (!res.headersSent) res.writeHead(502); res.end('Verification transport unavailable'); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  browser = await chromium.launch(); receipt.conditions.browser_version = browser.version();
  const context = await browser.newContext({viewport: {width: 1440, height: 1080}}), page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  const cdp = await context.newCDPSession(page);
  await cdp.send('Performance.enable');
  const metrics = async () => Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(row => [row.name, row.value]));
  const canvas = async () => page.locator('.atlas-pixel-canvas').evaluate(node => ({...node.dataset}));
  const firstRequest = requests.length, initialStart = performance.now();
  await page.goto('http://127.0.0.1:' + server.address().port, {waitUntil: 'domcontentloaded', timeout: 120000});
  await page.locator('#loading').waitFor({state: 'hidden', timeout: 180000});
  await page.waitForFunction(() => document.querySelector('.atlas-pixel-canvas')?.dataset.rendered === 'true', null, {timeout: 180000});
  receipt.initial = {elapsed_ms: performance.now() - initialStart, canvas: await canvas(), year: await page.locator('#map-year').textContent(),
    error: await page.locator('#year-error').textContent(), request_range: [firstRequest, requests.length], metrics: await metrics()};
  console.log(JSON.stringify({initial_ms: Math.round(receipt.initial.elapsed_ms), error: receipt.initial.error})); save();
  async function select(year, label, sequence = [year]) {
    const before = await canvas(), beforeMetrics = await metrics(), from = requests.length;
    await page.evaluate(() => { window.__atlasBenchmarkStart = performance.now(); });
    for (let i = 0; i < sequence.length; i++) {
      await page.evaluate(value => { document.querySelector('#year-input').value = String(value); document.querySelector('#year-form').requestSubmit(); }, sequence[i]);
      if (i < sequence.length - 1) await page.waitForTimeout(60);
    }
    await page.waitForFunction(({yearLabel, uploads}) => document.querySelector('#map-year')?.textContent === yearLabel &&
      document.querySelector('#loading')?.hidden && Number(document.querySelector('.atlas-pixel-canvas')?.dataset.uploads) > uploads,
    {yearLabel: formatYear(year), uploads: Number(before.uploads)}, {timeout: 180000});
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const elapsed = await page.evaluate(() => performance.now() - window.__atlasBenchmarkStart), after = await canvas(), afterMetrics = await metrics();
    const result = {label, year, sequence, elapsed_ms: elapsed, request_range: [from, requests.length],
      error: await page.locator('#year-error').textContent(), canvas_before: before, canvas_after: after,
      script_seconds: afterMetrics.ScriptDuration - beforeMetrics.ScriptDuration, task_seconds: afterMetrics.TaskDuration - beforeMetrics.TaskDuration,
      heap_used_bytes: afterMetrics.JSHeapUsedSize,
      ownership_compilation_delta: Number(after.compilations) - Number(before.compilations),
      ownership_upload_delta: Number(after.ownershipUploads) - Number(before.ownershipUploads)};
    navigation.push(result); console.log(JSON.stringify({label, year, elapsed_ms: Math.round(elapsed), script_ms: Math.round(result.script_seconds * 1000), error: result.error})); save();
  }
  cdp.on('Tracing.dataCollected', data => { if (trace.length < 100000) trace.push(...data.value); });
  await cdp.send('Tracing.start', {categories: 'devtools.timeline,blink.user_timing,v8', transferMode: 'ReportEvents'});
  const [target, nearby, distant] = suite === 'supported' ? [2020, 2021, 1900] : [1950, 1951, 1800];
  await select(target, 'first-distant-year');
  await select(nearby, 'warm-nearby-year');
  await select(target, 'warm-return');
  await select(distant, 'warm-distant-year');
  await select(target, 'rapid-latest-wins', [nearby, 1000, distant, target]);
  const tracingComplete = new Promise(resolve => cdp.once('Tracing.tracingComplete', resolve));
  await cdp.send('Tracing.end'); await tracingComplete;
  fs.writeFileSync(output.replace(/\.json$/, '') + '-trace.json.gz', gzipSync(JSON.stringify({traceEvents: trace}), {level: 9}));
  // Form validation must not invoke a network read or replace the current map.
  const from = requests.length, oldYear = await page.locator('#map-year').textContent();
  await page.locator('#year-input').fill('0');
  await page.evaluate(() => document.querySelector('#year-form').requestSubmit());
  receipt.invalid_year = {previous_year: oldYear, visible_year: await page.locator('#map-year').textContent(),
    error: await page.locator('#year-error').textContent(), new_requests: requests.length - from};
  await page.screenshot({path: output.replace(/\.json$/, '') + '-' + target + '.png'});
  receipt.completed_at_utc = new Date().toISOString(); receipt.completed = true; save();
  console.log(JSON.stringify({completed: true, samples: navigation.length, output}));
} catch (error) {
  receipt.completed = false; receipt.failure = error.name === 'TimeoutError' ? 'browser-timeout' : 'verification-failed'; save();
  console.error(JSON.stringify({completed: false, reason: receipt.failure, output})); process.exitCode = 1;
} finally { await browser?.close(); if (server) await new Promise(resolve => server.close(resolve)); }

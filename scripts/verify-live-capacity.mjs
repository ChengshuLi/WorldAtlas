import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

const [output] = process.argv.slice(2);
const origin = 'https://worldatlas-explorer.chengshu-li-2013.chatgpt.site';
if (!output?.startsWith('data/engineering/') || !process.stdin.isTTY || fs.existsSync(output)) {
  throw Error('Use a fresh owned engineering receipt path and hidden credential stdin');
}
process.stdin.setRawMode(true);
console.log('Ready for existing private verification credential on hidden stdin.');
const token = await new Promise((resolve, reject) => {
  let input = '';
  process.stdin.on('data', chunk => {
    input += chunk.toString();
    if (input.length > 8192) return reject(Error('Invalid hidden input'));
    if (!/[\r\n]/.test(input)) return;
    process.stdin.pause(); process.stdin.setRawMode(false);
    try {
      const value = JSON.parse(input.trim()).token;
      input = '';
      if (typeof value !== 'string' || !value || /[\r\n]/.test(value)) throw Error();
      resolve(value);
    } catch { reject(Error('Invalid hidden input')); }
  });
});
const receipt = {version: 1, checked_at_utc: new Date().toISOString(), site: origin, read_only: true,
  requests: [], objects: [], limits: [
    'Registered media inventory only; unregistered objects, provider billable storage and account allowances are not measured.',
    'One-byte ranged reads establish availability and provider-reported object size, not whole-object integrity.',
    'Configured database budget is an application guard, never a provider quota.'
  ]};
function safeBytes(value) {
  assert.ok(typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ||
    typeof value === 'string' && /^(0|[1-9][0-9]*)$/.test(value), 'Exact nonnegative byte count required');
  const integer = BigInt(value);
  assert.ok(integer <= BigInt(Number.MAX_SAFE_INTEGER), 'Byte count exceeds exact numeric range');
  return Number(integer);
}
async function get(route, {range = false} = {}) {
  const url = new URL(route, origin);
  assert.equal(url.origin, origin);
  assert.ok(url.pathname === '/api/storage/capacity' || url.pathname === '/api/storage/v2/export-marker' ||
    url.pathname === '/api/storage/v2/export/media' || range && url.pathname.startsWith('/api/media/'));
  assert.ok(receipt.requests.length < 1024, 'Bounded request inventory');
  const log = {path: url.pathname, range}; receipt.requests.push(log);
  const response = await fetch(url, {method: 'GET', redirect: 'error', signal: AbortSignal.timeout(60000),
    headers: {'OAI-Sites-Authorization': 'Bearer ' + token, ...(range ? {Range: 'bytes=0-0'} : {})}});
  log.status = response.status;
  const chunks = []; let size = 0;
  for await (const chunk of response.body) {
    size += chunk.length;
    assert.ok(size <= (range ? 1 : 4 * 1024 * 1024), 'Bounded response bytes');
    chunks.push(chunk);
  }
  log.bytes = size;
  const bytes = Buffer.concat(chunks);
  if (range) return {status: response.status, contentRange: response.headers.get('content-range'), bytes: size};
  assert.equal(response.status, 200, 'Successful read-only API response required');
  log.sha256 = createHash('sha256').update(bytes).digest('hex');
  return JSON.parse(bytes);
}
try {
  receipt.before_marker = await get('/api/storage/v2/export-marker');
  receipt.capacity = await get('/api/storage/capacity');
  const media = [], cursors = new Set(); let cursor = '';
  for (let page = 0; page < 10; page++) {
    const query = new URLSearchParams({limit: '200'}); if (cursor) query.set('cursor', cursor);
    const result = await get('/api/storage/v2/export/media?' + query);
    assert.equal(result.snapshot_marker.fingerprint, receipt.before_marker.fingerprint, 'Same snapshot required');
    media.push(...result.records.map(row => ({id: row.id, object_key: row.object_key, bytes: safeBytes(row.bytes), sha256: row.sha256, status: row.status})));
    cursor = result.next_cursor;
    if (!cursor) break;
    assert.ok(!cursors.has(cursor)); cursors.add(cursor);
  }
  assert.ok(!cursor, 'Bounded media inventory must be complete');
  receipt.media_inventory = media;
  assert.equal(media.length, receipt.capacity.media.registered_objects);
  assert.equal(media.reduce((sum, row) => sum + row.bytes, 0), safeBytes(receipt.capacity.media.registered_bytes));
  for (const row of media) {
    assert.ok(Number.isSafeInteger(row.bytes) && row.bytes > 0);
    const response = await get('/api/media/' + encodeURIComponent(row.id), {range: true});
    assert.equal(response.status, 206); assert.equal(response.bytes, 1);
    const match = /^bytes 0-0\/(\d+)$/.exec(response.contentRange ?? '');
    assert.ok(match, 'Actual R2 object size is required');
    const actualBytes = Number(match[1]); assert.equal(actualBytes, row.bytes);
    receipt.objects.push({...row, actual_bytes: actualBytes, measurement: 'R2 object.size via Content-Range', whole_sha256_verified: false});
  }
  receipt.after_marker = await get('/api/storage/v2/export-marker');
  assert.equal(receipt.after_marker.fingerprint, receipt.before_marker.fingerprint);
  assert.equal(receipt.capacity.revision, receipt.before_marker.revision);
  receipt.registered_object_size_bytes = receipt.objects.reduce((sum, row) => sum + row.actual_bytes, 0);
  receipt.completed = true;
} catch {
  receipt.completed = false;
  receipt.failure = 'Read-only availability, bounded-response, snapshot or size assertion failed; inspect categorized requests.';
  process.exitCode = 1;
} finally {
  const json = JSON.stringify(receipt, null, 2) + '\n';
  assert.ok(!json.includes(token), 'Credential must never appear in a receipt');
  fs.mkdirSync(path.dirname(output), {recursive: true}); fs.writeFileSync(output, json, {flag: 'wx', mode: 0o600});
  console.log(JSON.stringify({completed: receipt.completed, requests: receipt.requests.length, objects: receipt.objects.length, output}));
}

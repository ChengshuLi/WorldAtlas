import test from 'node:test';
import assert from 'node:assert/strict';
import {deflateRawSync, crc32} from 'node:zlib';
import {githubAPI} from '../scripts/issue-claim-contract.mjs';
import {requestAccounting} from '../scripts/github-quota.mjs';
import {readReportArchive, loadGeographicReport, reportHash} from '../scripts/geographic-report-artifact.mjs';

// Real single-file ZIP records, with both archive formats used by uploaders.
function archive(raw, {method = 8, descriptor = false, name = 'geography-check.json', attributes = 0} = {}) {
  const filename = Buffer.from(name), packed = method === 8 ? deflateRawSync(raw) : raw;
  const crc = crc32(raw), flags = descriptor ? 8 : 0;
  const local = Buffer.alloc(30); local.writeUInt32LE(0x04034b50); local.writeUInt16LE(20, 4);
  local.writeUInt16LE(flags, 6); local.writeUInt16LE(method, 8); local.writeUInt16LE(filename.length, 26);
  if (!descriptor) { local.writeUInt32LE(crc, 14); local.writeUInt32LE(packed.length, 18); local.writeUInt32LE(raw.length, 22); }
  const data = descriptor ? Buffer.alloc(16) : Buffer.alloc(0);
  if (descriptor) { data.writeUInt32LE(0x08074b50); data.writeUInt32LE(crc, 4); data.writeUInt32LE(packed.length, 8); data.writeUInt32LE(raw.length, 12); }
  const central = Buffer.alloc(46); central.writeUInt32LE(0x02014b50); central.writeUInt16LE(0x0314, 4);
  central.writeUInt16LE(20, 6); central.writeUInt16LE(flags, 8); central.writeUInt16LE(method, 10);
  central.writeUInt32LE(crc, 16); central.writeUInt32LE(packed.length, 20); central.writeUInt32LE(raw.length, 24);
  central.writeUInt16LE(filename.length, 28); central.writeUInt32LE(attributes, 38);
  const end = Buffer.alloc(22); end.writeUInt32LE(0x06054b50); end.writeUInt16LE(1, 8); end.writeUInt16LE(1, 10);
  end.writeUInt32LE(46 + filename.length, 12); end.writeUInt32LE(local.length + filename.length + packed.length + data.length, 16);
  return Buffer.concat([local, filename, packed, data, central, filename, end]);
}
const report = Buffer.from(JSON.stringify({version: 1, status: 'not-applicable'}) + '\n');
const digest = reportHash(report);
for (const method of [0, 8]) for (const descriptor of [false, true]) test(`actual ZIP records: method ${method}, descriptor ${descriptor}`, () => {
  assert.deepEqual(readReportArchive(archive(report, {method, descriptor}), digest), JSON.parse(report));
});
test('different valid report bytes cannot impersonate trusted job output', () => {
  assert.throws(() => readReportArchive(archive(Buffer.from('{}')), digest), /trusted geography job digest/);
});
test('path traversal, alternate names, symlinks and directories are rejected without extraction', () => {
  for (const options of [{name: '../scripts/merge-integration.mjs'}, {name: 'another.json'},
    {attributes: (0xa000 << 16) >>> 0}, {attributes: 0x10}]) {
    assert.throws(() => readReportArchive(archive(report, options), digest));
  }
});
test('corrupt CRC, inconsistent directory, missing data and multiple entries fail closed', () => {
  for (const mutate of [raw => raw.writeUInt16LE(2, raw.length - 12),
    raw => raw.writeUInt32LE(0, raw.length - 6), raw => raw.writeUInt32LE(0, 14),
    raw => raw.writeUInt32LE(0, raw.readUInt32LE(raw.length - 6) + 16)]) {
    const raw = archive(report); mutate(raw); assert.throws(() => readReportArchive(raw, digest));
  }
  assert.throws(() => readReportArchive(archive(report).subarray(1), digest));
});
test('inflation is bounded even when claimed uncompressed size is small', () => {
  const raw = archive(Buffer.alloc(33 * 1024 * 1024));
  const central = raw.readUInt32LE(raw.length - 6);
  raw.writeUInt32LE(10, 22); raw.writeUInt32LE(10, central + 24);
  assert.throws(() => readReportArchive(raw, digest));
});
function transport(overrides = {}) {
  const calls = [], artifact = {id: 12, name: 'geography-1234567890123456-1', expired: false, size_in_bytes: 300};
  const options = {repo: 'owner/repo', runId: '123', artifactName: artifact.name, expectedHash: digest, token: 'synthetic-token',
    api: async route => { calls.push(route); return {total_count: 1, artifacts: [artifact]}; },
    fetchImpl: async (url, init) => {
      calls.push({url, init});
      if (url.startsWith('https://api.github.com/')) return new Response(null, {status: 302, headers: {location: 'https://results.blob.core.windows.net/artifact?signature=fixture'}});
      return new Response(archive(report));
    }, ...overrides};
  return {options, calls, artifact};
}
test('bounded actual ZIP download authenticates only fixed API host, retains exact report digest', async () => {
  const f = transport(); assert.deepEqual(await loadGeographicReport(f.options), JSON.parse(report));
  assert.equal(f.calls[1].init.headers.Authorization, 'Bearer synthetic-token');
  assert.equal(f.calls[2].init.headers, undefined); assert.equal(f.calls[2].init.redirect, 'error');
});
test('missing trusted digest and poisoned same-name artifact are blocked', async () => {
  const a = transport({expectedHash: undefined}); await assert.rejects(loadGeographicReport(a.options), /trusted geographic artifact outputs/);
  const b = transport(); const original = b.options.fetchImpl;
  b.options.fetchImpl = async (url, init) => url.startsWith('https://api.github.com/') ? original(url, init) : new Response(archive(Buffer.from('{}')));
  await assert.rejects(loadGeographicReport(b.options), /trusted geography job digest/);
});
test('duplicate, expired and incomplete artifact inventories are blocked', async () => {
  for (const kind of ['duplicate', 'expired', 'incomplete']) {
    const f = transport();
    if (kind === 'expired') f.artifact.expired = true;
    else f.options.api = async () => ({total_count: 2, artifacts: kind === 'duplicate' ? [f.artifact, f.artifact] : [f.artifact]});
    await assert.rejects(loadGeographicReport(f.options)); assert.equal(f.calls.filter(call => typeof call === 'object').length, 0);
  }
});
test('foreign or credential-bearing delivery addresses never receive a fetch', async () => {
  for (const location of ['https://attacker.example/a?secret=x', 'http://results.blob.core.windows.net/a', 'https://u:p@results.blob.core.windows.net/a']) {
    const f = transport({fetchImpl: async () => new Response(null, {status: 302, headers: {location}})});
    await assert.rejects(loadGeographicReport(f.options), /delivery host/);
  }
});

test('real shared client accounts inventory and redirect, signed delivery remains token-free', async () => {
  const f = transport(), accounting = requestAccounting('geographic-download'), requests = [];
  const api = githubAPI(f.options.token, {onRequest: accounting.observe, fetchImpl: async (url, init) => {
    requests.push({url, init});
    if (url.includes('/actions/runs/')) return Response.json({total_count: 1, artifacts: [f.artifact]});
    return new Response(null, {status: 302, headers: {location: 'https://results.blob.core.windows.net/a?signature=private-secret'}});
  }});
  const delivery = [];
  const result = await loadGeographicReport({...f.options, api, fetchImpl: async (url, init) => {
    delivery.push({url, init}); return new Response(archive(report));
  }});
  assert.deepEqual(result, JSON.parse(report)); assert.equal(requests.length, 2);
  assert.equal(accounting.receipt().actual_http_attempts, 2);
  assert.equal(delivery.length, 1); assert.equal(delivery[0].init.headers, undefined);
  assert(!JSON.stringify(accounting.receipt()).includes('private-secret'));
});
test('shared admission refusal stops artifact download before credential-free delivery', async () => {
  const f = transport(); let delivery = false;
  const api = githubAPI(f.options.token, {fetchImpl: async () => Response.json({total_count: 1, artifacts: [f.artifact]})});
  let budget = 1;
  api.setHTTPAdmission(() => {if (!budget--) throw Error('shared admission refused');});
  await assert.rejects(loadGeographicReport({...f.options, api, fetchImpl: async () => {delivery = true; return new Response(archive(report));}}), /shared admission refused/);
  assert.equal(delivery, false);
});

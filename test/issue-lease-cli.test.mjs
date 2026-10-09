import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';

// Execute the real CLI with synthetic credentials and HTTP. The injected child
// refuses every unrecognized destination; it cannot reach a real service.
function harness(mode) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-lease-cli-'));
  const out = path.join(directory, 'pending.json'), log = path.join(directory, 'http.json');
  const root = path.resolve(import.meta.dirname, '..');
  const gh = path.join(directory, 'gh');
  fs.writeFileSync(gh, '#!/bin/sh\nif [ "$1" = auth ] && [ "$2" = token ]; then printf synthetic-private-token; else exit 99; fi\n', {mode: 0o700});
  const shim = path.join(directory, 'http.mjs');
  fs.writeFileSync(shim, `
import fs from 'node:fs';
import {renderClaim} from ${JSON.stringify(pathToFileURL(path.join(root, 'scripts/issue-claim-contract.mjs')).href)};
import {renderWorkerResult} from ${JSON.stringify(pathToFileURL(path.join(root, 'scripts/worker-result.mjs')).href)};
let time = Date.parse('2026-10-09T00:00:00Z');
Date.now = () => time;
const realTimeout = globalThis.setTimeout;
globalThis.setTimeout = (callback, delay, ...args) => realTimeout(() => {time += delay; callback(...args);}, 0);
const out = ${JSON.stringify(out)}, log = ${JSON.stringify(log)}, mode = ${JSON.stringify(mode)};
let request = fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, 'utf8')) : undefined;
const rows = fs.existsSync(log) ? JSON.parse(fs.readFileSync(log, 'utf8')) : [];
const headers = {'x-ratelimit-limit':'5000','x-ratelimit-remaining':'4900','x-ratelimit-reset':String(Math.floor(time/1000)+3600),'x-ratelimit-resource':'core'};
globalThis.fetch = async (url, init) => {
 if(!url.startsWith('https://api.github.com/repos/ChengshuLi/WorldAtlas')) throw Error('Synthetic child refuses foreign HTTP');
 time += 200;
 rows.push({route:new URL(url).pathname, method:init.method}); fs.writeFileSync(log,JSON.stringify(rows));
 const route = new URL(url).pathname;
 if(init.method === 'POST' && route.endsWith('/issue-claims.yml/dispatches')) {
  request = {...JSON.parse(init.body).inputs, issue_number:26};
  if(mode === 'uncertain') throw Error('Synthetic lost dispatch response');
  return new Response(null,{status:204,headers});
 }
 if(route === '/repos/ChengshuLi/WorldAtlas') return Response.json({}, {headers});
 const claim = {...request,version:1,active:true,expires_at:'2026-10-10T00:00:00Z'};
 if(route.endsWith('/comments')) return Response.json([
  {id:1,user:{login:'github-actions[bot]'},body:renderClaim(claim)},
  ...(mode === 'cancelled' ? [] : [{id:2,user:{login:'github-actions[bot]'},body:renderWorkerResult('claim',{...request,accepted:true})}])
 ],{headers});
 const run = {id:55,display_title:'renew #26 '+request.request_id,status:'completed',conclusion:'cancelled'};
 if(route.endsWith('/issue-claims.yml/runs')) return Response.json({workflow_runs:[run]},{headers});
 if(route.endsWith('/actions/runs/55')) return Response.json(run,{headers});
 throw Error('Unrecognized synthetic route');
};
`);
  const run = () => spawnSync(process.execPath, ['--import', shim, path.join(root, 'scripts/issue-lease.mjs'),
    'renew', '--issue', '26', '--worker', 'synthetic-worker', '--branch', 'engineering/fixture',
    '--claim-id', 'synthetic-claim-unique', '--reason', 'Preserve original rationale', '--out', out], {cwd: root, encoding: 'utf8', timeout: 10000,
    env: {PATH: directory + path.delimiter + process.env.PATH}});
  return {run, out, rows: () => JSON.parse(fs.readFileSync(log, 'utf8')), close: () => fs.rmSync(directory, {recursive:true,force:true})};
}
for (const mode of ['accepted', 'uncertain']) test(`actual lease CLI ${mode} dispatch confirms ownership without a second write`, () => {
  const h = harness(mode);
  try {
    const result = h.run(); assert.equal(result.status, 0, result.stderr);
    const receipt = JSON.parse(fs.readFileSync(h.out, 'utf8'));
    assert.equal(receipt.accepted, true); assert.equal(h.rows().filter(row => row.method === 'POST').length, 1);
    assert.equal(receipt.request_accounting.actual_http_attempts, h.rows().length);
    assert(!result.stdout.includes('synthetic-private-token')); assert(!fs.readFileSync(h.out, 'utf8').includes('synthetic-private-token'));
  } finally {h.close();}
});
test('actual cancelled lease CLI preserves checkpoint; rerunning observes the same identity without dispatch', () => {
  const h = harness('cancelled');
  try {
    const first = h.run(); assert.equal(first.status, 2, first.stderr);
    const before = JSON.parse(fs.readFileSync(h.out, 'utf8'));
    assert.equal(before.execution_conclusion, 'cancelled'); assert.equal(before.accepted, false);
    assert.equal(before.request_reason, 'Preserve original rationale');
    assert.notEqual(before.reason, before.request_reason);
    const second = h.run(); assert.equal(second.status, 2, second.stderr);
    const after = JSON.parse(fs.readFileSync(h.out, 'utf8'));
    assert.equal(before.request_id, after.request_id); assert.equal(after.submitted, true);
    assert.equal(h.rows().filter(row => row.method === 'POST').length, 1);
  } finally {h.close();}
});

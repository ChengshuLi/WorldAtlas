import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPair, SignJWT} from 'jose';
import {protectedWorker} from '../hosted/cloudflare-access.js';
import {cloudflareConfig} from '../scripts/build-cloudflare.mjs';
import atlas from '../hosted/worker.js';

const pair = await generateKeyPair('RS256');
const other = await generateKeyPair('RS256');
const issuer = 'https://atlas-test.cloudflareaccess.com';
const env = {ATLAS_ACCESS_TEAM_DOMAIN: 'atlas-test.cloudflareaccess.com', ATLAS_ACCESS_AUD: 'atlas-audience'};
const token = (changes = {}, key = pair.privateKey) => new SignJWT({sub: 'owner', iat: Math.floor(Date.now()/1000),
  exp: Math.floor(Date.now()/1000)+3600, iss: issuer, aud: 'atlas-audience', ...changes})
  .setProtectedHeader({alg: 'RS256'}).sign(key);
const req = (path, jwt, method = 'GET') => new Request(`https://atlas.example${path}`, {
  method, headers: jwt ? {'Cf-Access-Jwt-Assertion': jwt} : {},
});

test('all static and API paths fail closed before the app can access data', async () => {
  let calls = 0;
  const worker = protectedWorker({fetch() {calls++; return new Response('private');}}, {keys: () => pair.publicKey});
  for (const path of ['/', '/assets/map.js', '/api/storage/v3/catalog']) {
    assert.equal((await worker.fetch(req(path), env)).status, 403);
    assert.equal((await worker.fetch(req(path, await token()), {})).status, 503);
    assert.equal((await worker.fetch(req(path, await token()), {...env, ATLAS_ACCESS_TEAM_DOMAIN: 'attacker.example'})).status, 503);
  }
  assert.equal(calls, 0);
});

test('forged, expired, wrong-issuer/audience and incomplete JWTs never reach the app', async () => {
  let calls = 0;
  const worker = protectedWorker({fetch() {calls++; return new Response('private');}}, {keys: () => pair.publicKey});
  const bad = [await token({}, other.privateKey), await token({exp: 1}), await token({iss: 'https://wrong.cloudflareaccess.com'}),
    await token({aud: 'other-app'}), await token({exp: undefined}), 'not-a-jwt'];
  for (const jwt of bad) assert.equal((await worker.fetch(req('/api/geography', jwt), env)).status, 403);
  assert.equal(calls, 0);
});

test('authenticated reads route normally and writes require explicit cutover', async () => {
  let calls = 0;
  const worker = protectedWorker({fetch(request, actualEnv, ctx) {
    calls++; assert.equal(actualEnv.ATLAS_ACCESS_AUD, env.ATLAS_ACCESS_AUD);
    assert.equal(ctx, 'context'); return new Response(request.method);
  }}, {keys: actualIssuer => {assert.equal(actualIssuer, issuer); return pair.publicKey;}});
  const jwt = await token();
  for (const path of ['/', '/api/geography']) assert.equal(await (await worker.fetch(req(path, jwt), env, 'context')).text(), 'GET');
  for (const flag of [undefined, '1', '', 'invalid']) {
    assert.equal((await worker.fetch(req('/api/import', jwt, 'POST'), {...env, ATLAS_READ_ONLY: flag}, 'context')).status, 503);
  }
  assert.equal(calls, 2);
  assert.equal(await (await worker.fetch(req('/api/import', jwt, 'POST'), {...env, ATLAS_READ_ONLY: '0'}, 'context')).text(), 'POST');
});

test('Cloudflare config protects assets and never provisions or migrates D1', () => {
  const config = cloudflareConfig();
  assert.equal(config.assets.run_worker_first, true);
  assert.equal(config.preview_urls, false);
  assert.equal(config.vars.ATLAS_CONTENT_BACKEND, 'postgres');
  assert.equal(config.vars.ATLAS_READ_ONLY, '1');
  assert.equal(config.vars.ATLAS_ACCESS_AUD, '');
  assert.equal(config.r2_buckets[0].bucket_name, 'worldatlas-archives');
  assert.equal('d1_databases' in config, false);
  assert.equal('DATABASE_URL' in config.vars, false);
});

test('authenticated wrapper preserves the real atlas API and static asset routing', async () => {
  const worker = protectedWorker(atlas, {keys: () => pair.publicKey});
  const actualEnv = {...env, ASSETS: {fetch: request => new Response(`asset:${new URL(request.url).pathname}`)}};
  const jwt = await token();
  assert.equal(await (await worker.fetch(req('/index.html', jwt), actualEnv)).text(), 'asset:/index.html');
  const response = await worker.fetch(req('/api/classifications', jwt), actualEnv);
  assert.equal(response.status, 200);
  assert.equal((await response.json()).version, 1);
  assert.equal((await worker.fetch(req('/api/import', jwt, 'POST'), actualEnv)).status, 503);
});

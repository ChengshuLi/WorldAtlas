// Native loopback HTTP validates the shared GitHub adapter's AbortSignal through
// headers and body consumption, including a persisted write with an unknown result.
// Scale the timer to 500 ms while asserting the production request uses 20 seconds.
import http from 'node:http';
import assert from 'node:assert/strict';
import {githubAPI} from '../../../scripts/issue-claim-contract.mjs';

const nativeFetch = globalThis.fetch, nativeTimeout = AbortSignal.timeout;
let mode = 'headers', calls = [], durable = [], writes = 0;
const timers = [];
const delay = (fn, ms) => timers.push(setTimeout(fn, ms));
const server = http.createServer((req, res) => {
  if (req.method === 'POST') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      writes++;
      durable.push({id: writes, body: JSON.parse(body).body});
      res.writeHead(201, {'content-type': 'application/json'});
      res.write('{"id":');
      delay(() => {if (!res.destroyed) res.end('1}');}, 2000);
    });
    return;
  }
  if (mode === 'headers') {
    delay(() => {
      if (!res.destroyed) {res.writeHead(200, {'content-type': 'application/json'});res.end('{}');}
    }, 2000);
    return;
  }
  res.writeHead(200, {'content-type': 'application/json'});
  if (mode === 'body') {
    res.write('{"slow":');
    delay(() => {if (!res.destroyed) res.end('true}');}, 2000);
    return;
  }
  assert.equal(req.url, '/repos/review/fixture/issues/42/comments');
  res.end(JSON.stringify(durable));
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
try {
  AbortSignal.timeout = ms => {assert.equal(ms, 20_000);return nativeTimeout(500);};
  const api = githubAPI('synthetic-native-review', {
    minimumRemaining: 0,
    readWaitMs: 60_000,
    sleep: async () => assert.fail('uncertain transport must not retry'),
    fetchImpl: (url, options) => {
      const u = new URL(url);
      assert.equal(u.origin, 'https://api.github.com');
      assert.equal(options.headers.Authorization, 'Bearer synthetic-native-review');
      calls.push({method: options.method, path: u.pathname});
      return nativeFetch(origin + u.pathname + u.search,
        {method: options.method, body: options.body, signal: options.signal});
    }
  });
  for (mode of ['headers', 'body']) {
    calls = [];
    await assert.rejects(api('/repos/review/fixture/issues/42/comments'), /abort|timeout/i);
    assert.equal(calls.length, 1);
    assert.equal(writes, 0);
  }
  // Persist the POST before aborting its successful 201 response body. The shared
  // transport refuses without replay; an explicit read can reconcile actual state.
  mode = 'persisted-write';calls = [];
  await assert.rejects(api('/repos/review/fixture/issues/42/comments', 'POST',
    {body: 'retained shared HTTP deadline control'}), /abort|timeout/i);
  assert.equal(writes, 1);
  assert.equal(calls.length, 1);
  assert.deepEqual(await api('/repos/review/fixture/issues/42/comments'), durable);
  assert.equal(writes, 1);
  assert.equal(calls.length, 2);
  assert.equal(durable[0].body, 'retained shared HTTP deadline control');
  console.log({persisted_POST201_aborted_body: true, explicit_read_reconciled: true,
    posts: writes, controls: 3});
} finally {
  AbortSignal.timeout = nativeTimeout;
  for (const timer of timers) clearTimeout(timer);
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
}

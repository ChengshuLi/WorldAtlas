import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {verifyRepair, applyPlan} from '../scripts/apply-supplement-source-hints.mjs';

const sha = value => createHash('sha256').update(value).digest('hex');
const oldPath = 'data/macro-foundation/new-location-source-profiles-v4.json.gz';
const retainedPath = 'data/reference-migrations/macro-improvements-v4/queue-checkpoint/new-location-source-profiles-v4.json.gz';
const wrap = scope => 'Original recorded date\n```json\n' + JSON.stringify(scope) + '\n```\nOriginal completion history';
function fixture(number = 520) {
  const scope = {member_location_ids: ['synthetic:' + number], release: {id: 'synthetic-release'},
    source_profile_hints: [{location_id: 'synthetic:' + number, durable_full_source_profile_path: oldPath,
      full_source_profile_canonical_sha256: 'a'.repeat(64)}]};
  const body = wrap(scope);
  const after = structuredClone(scope);
  after.source_profile_hints[0].durable_full_source_profile_path = retainedPath;
  after.source_profile_hints[0].full_source_profile_hash_scope = 'canonical-entry-utf8-json-without-trailing-newline';
  after.source_profile_artifact = {path: retainedPath};
  const candidate = wrap(after);
  return {issue: {number, body, state: 'closed', labels: [{name: 'status:ready'}], assignees: []},
    row: {number, state: 'closed', body: candidate, before_body_sha256: sha(body), after_body_sha256: sha(candidate)}};
}
function mockAPI({failReadback = false, activeIssue = null} = {}) {
  const fixtures = Array.from({length: 8}, (_, index) => fixture(520 + index));
  const issues = new Map(fixtures.map(item => [item.issue.number, item.issue]));
  const writes = [];
  const api = async (route, method = 'GET', body) => {
    const match = /\/issues\/(\d+)(?:\/(comments|timeline))?/.exec(route);
    assert.ok(match, route);
    const number = Number(match[1]);
    if (match[2] === 'timeline') return [];
    if (match[2] === 'comments') return number === activeIssue ? [{user: {login: 'github-actions[bot]'},
      body: '**Worker reservation:** another worker\n<!-- worldatlas-claim:v1\n' +
        JSON.stringify({version: 1, active: true, worker_id: 'other-worker', claim_id: 'synthetic-claim', branch: 'geography/synthetic', expires_at: '2026-10-04T00:00:00Z'}) + '\n-->'}] : [];
    const issue = issues.get(number);
    if (method === 'PATCH') {
      writes.push({number, body});
      issue.body = body.body + (failReadback && number === 521 ? '\nUnexpected concurrent edit' : '');
    }
    return structuredClone(issue);
  };
  return {api, writes, plan: {version: 1, issue: 554, repairs: fixtures.map(item => item.row)}};
}

test('stale body, state, candidate bytes and active worker/PR prevent writes', () => {
  const {issue, row} = fixture();
  assert.equal(verifyRepair(row, issue, null, []), 'eligible');
  assert.throws(() => verifyRepair(row, {...issue, body: issue.body + '\nOther edit'}, null, []), /replan/);
  assert.throws(() => verifyRepair(row, {...issue, state: 'open'}, null, []), /state changed/);
  assert.throws(() => verifyRepair({...row, body: row.body + '\nTamper'}, issue, null, []), /body hash changed/);
  assert.throws(() => verifyRepair(row, issue, {active: true}, []), /active worker/);
  assert.throws(() => verifyRepair(row, issue, null, [{state: 'open'}]), /active worker/);
});

test('unrelated scope and original prose cannot be overwritten', () => {
  const {issue, row} = fixture();
  const prose = row.body.replace('Original completion history', 'History removed');
  assert.throws(() => verifyRepair({...row, body: prose, after_body_sha256: sha(prose)}, issue, null, []), /history changed/);
  const release = row.body.replace('synthetic-release', 'different-release');
  assert.throws(() => verifyRepair({...row, body: release, after_body_sha256: sha(release)}, issue, null, []), /unrelated source fields/);
});

test('read-only preflight issues no writes and checks the complete batch before applying', async () => {
  const good = mockAPI();
  const receipt = await applyPlan(good.plan, good.api);
  assert.equal(receipt.completed, true);
  assert.equal(good.writes.length, 0);
  const blocked = mockAPI({activeIssue: 527});
  await assert.rejects(applyPlan(blocked.plan, blocked.api, {apply: true}), /active worker/);
  assert.equal(blocked.writes.length, 0, 'last-row blocker must prevent all writes');
});

test('bounded application reads back each correction and is idempotent', async () => {
  const fake = mockAPI();
  const receipt = await applyPlan(fake.plan, fake.api, {apply: true});
  assert.equal(receipt.completed, true);
  assert.equal(fake.writes.length, 8);
  assert.ok(receipt.results.every(row => row.observed_body_sha256 === row.expected_body_sha256));
  const replay = await applyPlan(fake.plan, fake.api, {apply: true});
  assert.equal(fake.writes.length, 8);
  assert.ok(replay.results.every(row => row.result === 'already-corrected'));
});

test('failed readback retains partial receipt and stops before remaining writes', async () => {
  const fake = mockAPI({failReadback: true});
  const checkpoints = [];
  await assert.rejects(applyPlan(fake.plan, fake.api, {apply: true,
    checkpoint: receipt => checkpoints.push(structuredClone(receipt))}), /readback mismatch/);
  assert.equal(fake.writes.length, 2);
  assert.equal(checkpoints.at(-1).completed, false);
  assert.equal(checkpoints.at(-1).results.length, 1);
  assert.equal(checkpoints.at(-1).results[0].number, 520);
});

test('unexpected issue scope cannot expand the mutation targets', async () => {
  const fake = mockAPI();
  fake.plan.repairs[0].number = 999;
  await assert.rejects(applyPlan(fake.plan, fake.api, {apply: true}), /exactly the original eight/);
  assert.equal(fake.writes.length, 0);
});


test('fresh body recheck prevents overwriting an edit after batch preflight', async () => {
  const fake = mockAPI();
  let reads = 0;
  const api = async (route, method, body) => {
    const response = await fake.api(route, method, body);
    if (/\/issues\/520$/.test(route) && (!method || method === 'GET') && ++reads === 2) {
      response.body += '\nNew current worker note';
    }
    return response;
  };
  await assert.rejects(applyPlan(fake.plan, api, {apply: true}), /replan/);
  assert.equal(fake.writes.length, 0);
});


test('scope property serialization order does not imply changed release or ownership', () => {
  const {issue, row} = fixture();
  const match = /```json\n(.*?)\n```/s.exec(row.body);
  const scope = JSON.parse(match[1]);
  const reordered = Object.fromEntries(Object.entries(scope).reverse());
  const body = row.body.replace(match[1], JSON.stringify(reordered));
  assert.equal(verifyRepair({...row, body, after_body_sha256: sha(body)}, issue, null, []), 'eligible');
});

test('a wrong hash label is rejected even when source scope is otherwise unchanged', () => {
  const {issue, row} = fixture();
  const body = row.body.replace('canonical-entry-utf8-json-without-trailing-newline', 'compressed-file');
  assert.throws(() => verifyRepair({...row, body, after_body_sha256: sha(body)}, issue, null, []), /restore the retained pointer/);
});

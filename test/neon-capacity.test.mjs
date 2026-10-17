import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {verifyNeonCapacity} from '../scripts/verify-neon-capacity.mjs';
import {expectedNeonProjectId} from '../scripts/verify-neon-project.mjs';

const key = 'synthetic-key-never-retained';

test('metadata workflow executes its actual entry points from only the declared code', t => {
  const root = path.resolve(import.meta.dirname, '..');
  const workflow = fs.readFileSync(path.join(root, '.github/workflows/neon-verify.yml'), 'utf8');
  const block = workflow.match(/sparse-checkout: \|\n((?:            .+\n)+)/);
  assert.ok(block);
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'neon-metadata-checkout-'));
  t.after(() => fs.rmSync(directory, {recursive:true, force:true}));
  for (const name of block[1].trim().split('\n').map(row => row.trim().replace(/^\//, ''))) {
    const destination = path.join(directory, name);
    fs.mkdirSync(path.dirname(destination), {recursive:true});
    fs.copyFileSync(path.join(root, name), destination);
  }
  const commands = [...workflow.matchAll(/run: node ([^\s]+) ([^\s]+)/g)];
  assert.ok(commands.length);
  for (const [, entry, output] of commands) {
    const result = spawnSync(process.execPath, [entry, output], {cwd:directory, encoding:'utf8', env:{PATH:process.env.PATH}});
    assert.equal(result.status, 1, result.stderr);
    const receipt = JSON.parse(fs.readFileSync(path.join(directory, output), 'utf8'));
    assert.equal(receipt.error_code, 'missing-or-invalid-api-key');
    assert.equal(receipt.read_only, true);
  }
});

function fixture({organizationStatus = 200, quota = {logical_size_bytes: 1000000000, active_time_seconds: 0}, org = true} = {}) {
  const requests = [];
  const project = {id: expectedNeonProjectId, ...(org ? {org_id: 'org-example'} : {}),
    history_retention_seconds: 21600, branch_logical_size_limit: 1024, settings: {quota, arbitrary_secret: key}, owner: {email: 'private@example.invalid'}};
  const fetchImpl = async (url, options) => {
    requests.push(url.pathname + url.search);
    assert.equal(url.origin, 'https://console.neon.tech'); assert.equal(options.method, 'GET');
    assert.equal(options.redirect, 'error'); assert.equal(options.headers.Authorization, 'Bearer ' + key);
    if (url.pathname.endsWith('/branches')) return Response.json({branches: [{id: 'br-production', name: 'production', default: true}]});
    if (url.pathname.endsWith('/endpoints')) return Response.json({endpoints: [
      {id: 'ep-production', branch_id: 'br-production', project_id: expectedNeonProjectId,
        autoscaling_limit_min_cu: 0.25, autoscaling_limit_max_cu: 2, suspend_timeout_seconds: 0},
      {id: 'ep-other', branch_id: 'br-other', autoscaling_limit_max_cu: 16}
    ]});
    if (url.pathname.startsWith('/api/v2/organizations/')) return Response.json(
      {id: 'org-example', plan: 'free', billing_contact: 'private@example.invalid'}, {status: organizationStatus});
    assert.equal(url.pathname, '/api/v2/projects/' + expectedNeonProjectId);
    return Response.json({project});
  };
  return {requests, project, fetchImpl};
}

test('account proof and configured quotas/compute remain typed, scoped and free of arbitrary private fields', async () => {
  const f = fixture(); const receipt = await verifyNeonCapacity({apiKey: key, projectId: expectedNeonProjectId, fetchImpl: f.fetchImpl});
  assert.equal(receipt.account_plan.plan, 'free'); assert.equal(receipt.configuration.project_quotas.active_time_seconds, 0);
  assert.equal(receipt.configuration.project_quotas.compute_time_seconds, null);
  assert.equal(receipt.configuration.branch_logical_size_limit_mib, 1024);
  assert.equal(receipt.configuration.history_retention_seconds, 21600);
  assert.deepEqual(receipt.configuration.production_branch_endpoints, [{id: 'ep-production', branch_id: 'br-production', autoscaling_limit_min_cu: 0.25, autoscaling_limit_max_cu: 2, suspend_timeout_seconds: 0}]);
  assert.equal(f.requests.length, 4); assert.ok(!JSON.stringify(receipt).includes(key));
  assert.ok(!JSON.stringify(receipt).includes('private@example.invalid'));
  assert.match(receipt.limitations.join(' '), /does not prove billing-plan allowances are unlimited/);
});

test('denied organization proof stays unavailable while actual project settings remain verified', async () => {
  const f = fixture({organizationStatus: 403});
  const r = await verifyNeonCapacity({apiKey: key, projectId: expectedNeonProjectId, fetchImpl: f.fetchImpl});
  assert.equal(r.status, 'verified'); assert.equal(r.account_plan.status, 'unavailable');
  assert.equal(r.account_plan.http_status, 403); assert.equal(r.account_plan.plan, undefined);
});

test('missing organization and quota are explicit unknowns, never inferred from public pricing', async () => {
  const f = fixture({org: false, quota: {}});
  const r = await verifyNeonCapacity({apiKey: key, projectId: expectedNeonProjectId, fetchImpl: f.fetchImpl});
  assert.equal(r.account_plan.status, 'unavailable'); assert.equal(f.requests.length, 3);
  assert.ok(Object.values(r.configuration.project_quotas).every(value => value === null));
});

test('wrong project and lossy quotas fail before a misleading capacity receipt can be produced', async () => {
  const f = fixture();
  await assert.rejects(verifyNeonCapacity({apiKey: key, projectId: 'other-project', fetchImpl: f.fetchImpl}), /unexpected-project-id/);
  assert.equal(f.requests.length, 0);
  for (const value of [-1, 1.5, Number.MAX_SAFE_INTEGER + 1, '1000']) {
    const malformed = fixture({quota: {logical_size_bytes: value}});
    await assert.rejects(verifyNeonCapacity({apiKey: key, projectId: expectedNeonProjectId, fetchImpl: malformed.fetchImpl}), /invalid-integer-setting/);
  }
});

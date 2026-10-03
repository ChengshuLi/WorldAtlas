import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {auditDeployment, budgetViolations, formatDeploymentBudget, immutableAssetCandidates} from '../scripts/deployment-budget.mjs';

async function fixture() {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'atlas-package-'));
  const entries = {'.openai/hosting.json': '{"project_id":"fixture"}', 'dist/client/ownership/runs.bin.gz': 'pinned map bytes',
    'dist/client/index.html': '<html></html>', 'dist/server/index.js': 'export default {}',
    'dist/drizzle/0000.sql': 'CREATE TABLE x(id INTEGER);', 'dist/server/drizzle/0000.sql': 'CREATE TABLE x(id INTEGER);',
    'data/archive.json': 'preserved outside deployment', 'drizzle/0000.sql': 'raw immutable source'};
  for (const [file, bytes] of Object.entries(entries)) {
    await fs.mkdir(path.dirname(path.join(root, file)), {recursive: true});
    await fs.writeFile(path.join(root, file), bytes);
  }
  return root;
}

test('exact upload archive accounting includes transport/config and preserves excluded sources', async () => {
  const root = await fixture();
  try {
    const archive = path.join(root, 'upload.tar.gz');
    const report = await auditDeployment({root, archivePath: archive});
    const bytes = await fs.readFile(archive);
    assert.equal(report.archive.compressed_bytes, bytes.length);
    assert.equal(report.archive.uncompressed_bytes, gunzipSync(bytes).length);
    assert.equal(report.archive.sha256, createHash('sha256').update(bytes).digest('hex'));
    assert.equal(report.file_bytes, report.files.reduce((sum, row) => sum + row.bytes, 0));
    assert.equal(Object.values(report.categories).reduce((sum, row) => sum + row.bytes, 0), report.file_bytes);
    assert.deepEqual(report.violations, []);
    const candidates = immutableAssetCandidates(report);
    assert.equal(candidates.status, 'proposed-only');
    assert.equal(candidates.uploads_verified, false);
    assert.equal(candidates.files.length, 1);
    assert.equal(candidates.files[0].object_key, `worldatlas/map-assets/sha256/${report.files.find(file => file.category === 'ownership').sha256}`);
    const target = path.join(root, 'extracted');
    await fs.mkdir(target);
    execFileSync('tar', ['-xzf', archive, '-C', target]);
    for (const file of report.files) {
      const extracted = await fs.readFile(path.join(target, file.path));
      assert.equal(extracted.length, file.bytes);
      assert.equal(createHash('sha256').update(extracted).digest('hex'), file.sha256);
    }
    assert.equal(await fs.readFile(path.join(target, 'drizzle/0000.sql'), 'utf8'), 'CREATE TABLE x(id INTEGER);');
    assert.equal(await fs.readFile(path.join(root, 'drizzle/0000.sql'), 'utf8'), 'raw immutable source');
    await assert.rejects(fs.access(path.join(target, 'data/archive.json')));
    const second = await auditDeployment({root});
    assert.deepEqual(second.archive, report.archive, 'fixed tar metadata gives reproducible bytes');
    await assert.rejects(auditDeployment({root, archivePath: archive}), /EEXIST/);
  } finally { await fs.rm(root, {recursive: true, force: true}); }
});

test('reserve breaches fail before hard limits and diagnostics name large files/categories', () => {
  const policy = {package_limit_bytes: 100, package_reserve_bytes: 20, asset_limit_bytes: 50, asset_reserve_bytes: 10};
  const report = {policy, file_bytes: 45, archive: {uncompressed_bytes: 81, compressed_bytes: 30},
    files: [{path: 'dist/client/ownership/large.gz', bytes: 41}], categories: {ownership: {files: 1, bytes: 41}}};
  report.violations = budgetViolations(report, policy);
  assert.equal(report.violations.length, 2);
  assert.match(report.violations[0], /target 80, hard limit 100; reduce by 1/);
  assert.match(formatDeploymentBudget(report), /ownership: 41 bytes/);
  assert.match(formatDeploymentBudget(report), /large.gz: 41 bytes/);
  assert.equal(budgetViolations({...report, archive: {uncompressed_bytes: 80}, files: [{path: 'x', bytes: 40}]}, policy).length, 0);
  assert.throws(() => budgetViolations(report, {...policy, package_reserve_bytes: 100}), /Reserve/);
});

test('staged Site inventory agrees with actual archive and rejects redundant transport/linked inputs', async () => {
  const root = await fixture();
  try {
    await assert.rejects(auditDeployment({root, layout: 'site'}), /redundant/);
    await fs.rm(path.join(root, 'drizzle'), {recursive: true});
    await fs.rename(path.join(root, 'dist/drizzle'), path.join(root, 'drizzle'));
    const report = await auditDeployment({root, layout: 'site'});
    assert.equal(report.files.filter(file => file.category === 'migration-transport').length, 2);
    await assert.rejects(auditDeployment({root, layout: 'site', archivePath: path.join(root, 'dist/new.tar.gz')}), /outside/);
    await fs.symlink(path.join(root, 'data/archive.json'), path.join(root, 'dist/client/linked.json'));
    await assert.rejects(auditDeployment({root, layout: 'site'}), /symlink/);
  } finally { await fs.rm(root, {recursive: true, force: true}); }
});

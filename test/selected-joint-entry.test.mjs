import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {trustedFixture} from './helpers/selected-joint-fixture.mjs';

const ENTRY = 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs';
function run(f, baseline, candidate, destination = path.join(f.root, 'complete'), extraEnv = {}) {
  const env = {...process.env, ...extraEnv}; delete env.NODE_OPTIONS; delete env.NODE_PATH;
  const trusted = f.git('rev-parse', 'HEAD').toString().trim();
  return spawnSync(process.execPath, ['--expose-gc', path.join(f.root, ENTRY), f.root, trusted,
    baseline, candidate, destination], {encoding:'utf8', env, timeout:30000});
}

test('actual joint CLI reports unseeded baseline as explicit cold validation, never unchanged success', async t => {
  const f = await trustedFixture(t);
  f.save('data/ownership-selection.json', {version:1}); const selected = f.commit();
  const result = run(f, selected, selected);
  assert.equal(result.status, 0, result.stderr);
  const report = JSON.parse(result.stdout);
  assert.equal(report.mode, 'legacy-cold-required');
  assert.equal(report.reuse_unavailable.cold, 'baseline-and-candidate');
  assert.equal(Object.hasOwn(report, 'native'), false);
  assert.equal(fs.existsSync(path.join(f.root, 'complete')), false);
});

test('actual joint CLI preserves a qualified baseline but requires cold validation of unsupported candidate', async t => {
  const f = await trustedFixture(t);
  f.save('data/source.json', {type:'FeatureCollection', features:[]}); const candidate = f.commit();
  const result = run(f, f.selected, candidate);
  assert.equal(result.status, 0, result.stderr);
  const report = JSON.parse(result.stdout);
  assert.equal(report.mode, 'legacy-cold-required');
  assert.equal(report.reuse_unavailable.cold, 'candidate');
  assert.match(report.reuse_unavailable.reason, /route changed/);
  assert.equal(fs.existsSync(path.join(f.root, 'complete')), false);
});

test('joint output collision and dangling symlink fail before qualification and preserve originals', async t => {
  const f = await trustedFixture(t), destination = path.join(f.root, 'complete');
  const sentinel = Buffer.from('original output sentinel'); fs.writeFileSync(destination, sentinel);
  let result = run(f, f.selected, f.selected, destination);
  assert.notEqual(result.status, 0); assert.match(result.stderr, /output already exists/);
  assert.deepEqual(fs.readFileSync(destination), sentinel);
  fs.unlinkSync(destination); fs.symlinkSync(path.join(f.root, 'absent-target'), destination);
  result = run(f, f.selected, f.selected, destination);
  assert.notEqual(result.status, 0); assert.match(result.stderr, /output already exists/);
  assert.equal(fs.readlinkSync(destination), path.join(f.root, 'absent-target'));
  assert.equal(fs.existsSync(path.join(f.root, 'absent-target')), false);
});

test('joint launcher authenticates its additional consumer module before importing it', async t => {
  const f = await trustedFixture(t), consumer = path.join(f.root, ENTRY.replace('selected-joint-entry', 'selected-checkpoint-continuous'));
  fs.appendFileSync(consumer, '\nthrow Error("unauthenticated consumer executed");\n');
  const result = run(f, f.selected, f.selected);
  assert.notEqual(result.status, 0); assert.match(result.stderr, /Joint code size differs/);
  assert.doesNotMatch(result.stderr, /Error: unauthenticated consumer executed/);
  assert.equal(fs.existsSync(path.join(f.root, 'complete')), false);
});

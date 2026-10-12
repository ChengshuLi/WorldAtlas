import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
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

test('actual joint CLI qualifies once, runs both real consumers and releases once', async t => {
  const f = await trustedFixture(t), coverage = path.join(f.root, 'coverage');
  const result = run(f, f.selected, f.selected, path.join(f.root, 'complete'), {NODE_V8_COVERAGE:coverage});
  assert.equal(result.status, 0, result.stderr);
  const report = JSON.parse(result.stdout);
  assert.equal(report.mode, 'authenticated-checkpoint-append-v1');
  assert.equal(report.native.status, 'no-new-native-loss');
  assert.equal(report.continuous.status, 'no-selected-footprint-change');
  assert.equal(report.continuous.complete_owners, 3);
  const publication = JSON.parse(fs.readFileSync(path.join(f.root, 'complete/publication.json')));
  assert.deepEqual(report.continuous.publication, publication);
  const derived = JSON.parse(fs.readFileSync(path.join(f.root, 'complete/derived-publication.json')));
  assert.deepEqual(report.continuous.derived_checkpoint, derived);
  assert.equal(derived.accepted_checkpoint, false);
  assert.equal(derived.validation_stage, 'native-passed-continuous-pending');
  assert.equal(derived.kind, 'derived-selected-checkpoint-candidate-v1');
  const encoded = fs.readFileSync(path.join(f.root, 'complete', derived.certificate.path));
  const decoded = gunzipSync(encoded), certificate = JSON.parse(decoded);
  assert.equal(createHash('sha256').update(encoded).digest('hex'), derived.certificate.sha256);
  assert.equal(createHash('sha256').update(decoded).digest('hex'), derived.certificate.decoded_sha256);
  assert.equal(certificate.entries.length, 3);
  const derivedFacts = JSON.parse(fs.readFileSync(path.join(f.root, 'complete', derived.facts.path)));
  assert.equal(derivedFacts.baseline_commit, f.selected);
  assert.equal(derivedFacts.candidate_commit, f.selected);
  assert.deepEqual(derivedFacts.candidate_selection, f.selection);
  assert.deepEqual(derivedFacts.certificate, derived.certificate);
  assert.equal(Object.hasOwn(derivedFacts, 'complete_cold_custody'), false);
  const counts = new Map();
  for (const file of fs.readdirSync(coverage)) for (const script of JSON.parse(fs.readFileSync(path.join(coverage, file))).result) {
    if (!script.url.startsWith('file://' + f.root + '/')) continue;
    for (const fn of script.functions) counts.set(fn.functionName, (counts.get(fn.functionName) ?? 0) + fn.ranges[0].count);
  }
  for (const name of ['selectedBootstrap', 'qualifyCheckpoint', 'qualifyTransition', 'compareSelectedCheckpointNative', 'checkpointContinuousOperands', 'releaseCheckpoint'])
    assert.equal(counts.get(name), 1, name);
  assert.equal(counts.get('loadSelection'), 0);
  assert.equal(counts.get('selectedCoordinateShard'), 0);
});


test('derived output union is admitted before complete serialization or compression', async t => {
  const f = await trustedFixture(t);
  const certificate = {entries:[['unicode \uD800 \uD83C\uDF0D', 1, null, true, '\n\\"']]};
  const facts = {kind:'tiny-provisional-control'};
  const plan = f.joint.planDerivedOutput(certificate, facts, 30, 4096);
  assert.equal(plan.decodedBytes, Buffer.byteLength(JSON.stringify(certificate) + '\n'));
  assert(plan.encodedLimit > 0 && plan.encodedLimit < 4096);
  assert.throws(() => f.joint.planDerivedOutput(certificate, facts, 30, 50), /before serialization/);
  assert.throws(() => f.joint.planDerivedOutput(certificate, facts, 4096, 4096), /prospective/);
});

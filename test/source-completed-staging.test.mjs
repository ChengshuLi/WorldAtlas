import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import childProcess from 'node:child_process';
import {syncBuiltinESMExports} from 'node:module';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {sourceCohort, publishCompletedSource} from '../scripts/prepare-delivery-handoff.mjs';
const sha = raw => createHash('sha256').update(raw).digest('hex');

function fixture(t, phase = 'physical', producerFailure = false) {
  const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'completed-source-')));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const python = path.join(root, 'fixture-python'); fs.writeFileSync(python, 'synthetic installed runtime');
  const raw = fs.readFileSync(python), pin = {path: python, bytes: raw.length, sha256: sha(raw)};
  t.mock.method(process, 'availableMemory', () => 4 * 1024 ** 3);
  t.mock.method(process, 'memoryUsage', () => ({rss: 64 * 1024 ** 2}));
  let calls = 0, publicationRefusal = false, refusalMessage = 'Current preparation RSS allowance exceeded', invalidOutput = false;
  const names = phase === 'physical' ? ['whole-target-support.json', 'execution-receipt.json']
    : ['original-stage-inputs.json', 'cohort-intervals.json', 'cohort-config.json', 'source-qualification.json', 'execution-receipt.json'];
  t.mock.method(childProcess, 'execFileSync', (command, args) => {
    assert.equal(command, python); calls++;
    const output = args[args.indexOf('--output') + 1]; fs.mkdirSync(output);
    fs.writeFileSync(path.join(output, names[0]), '{"synthetic":true}\n');
    if (producerFailure) throw Error('Synthetic producer refusal');
    for (const name of names.slice(1)) fs.writeFileSync(path.join(output, name), JSON.stringify({complete: true, original: name}) + '\n');
    if (invalidOutput) fs.writeFileSync(path.join(output, 'foreign.json'), '{}');
    return Buffer.alloc(0);
  });
  syncBuiltinESMExports();
  t.after(() => { t.mock.restoreAll(); syncBuiltinESMExports(); });
  const budget = {snapshot: () => ({accounted_bytes: 0, reserved_review_bytes: 0, limit_bytes: 8 * 1024 ** 2}),
    add: () => { if (publicationRefusal) throw Error(refusalMessage); }};
  const config = {version: 1, processing_allowance: {phaseBytes: 256 * 1024 ** 2, rssBytes: 256 * 1024 ** 2},
    runtime_inventory: {python: pin, files: [pin]}, [phase]: {version: 1, inputs: [], resources: {output_bytes: 1024 ** 2}}};
  const destination = '.cache/delivery-handoff/retention-control';
  return {root, config, reader: {budget}, phase, destination, names, calls: () => calls,
    refuse: message => { publicationRefusal = true; if (message) refusalMessage = message; }, allow: () => { publicationRefusal = false; },
    invalidOutput: () => { invalidOutput = true; }};
}

for (const phase of ['source', 'physical']) test(`${phase} completed bodies survive outer RSS refusal without outer completion or replay`, async t => {
  const f = fixture(t, phase), result = await sourceCohort(f.config, f.reader, f.root, f.destination, phase);
  const retained = path.join(f.root, result.retained_staging), output = path.join(retained, 'products');
  const originals = Object.fromEntries(f.names.map(name => [name, fs.readFileSync(path.join(output, name))]));
  assert.equal(f.calls(), 1); f.refuse();
  assert.throws(() => publishCompletedSource(f.root, f.destination, result, {phase}, false, f.reader),
    error => /RSS allowance exceeded/.test(error.message) && error.message.includes(result.retained_staging) && /outer publication incomplete/.test(error.message));
  assert.equal(fs.existsSync(path.join(f.root, f.destination)), false);
  assert.deepEqual(fs.readdirSync(output).sort(), [...f.names].sort());
  for (const [name, raw] of Object.entries(originals)) assert.deepEqual(fs.readFileSync(path.join(output, name)), raw);
  assert.ok(fs.existsSync(path.join(retained, 'admission.json')));
  assert.ok(fs.existsSync(path.join(retained, 'source-config.json')));
  assert.equal(f.calls(), 1);
});

test('successful existing publication discards temporary producer staging only after receipt exists', async t => {
  const f = fixture(t), result = await sourceCohort(f.config, f.reader, f.root, f.destination, f.phase);
  const originalDiscard = result.discard_staging;
  result.discard_staging = () => {
    assert.ok(fs.existsSync(path.join(f.root, f.destination, 'preparation.json')));
    originalDiscard();
  };
  const complete = publishCompletedSource(f.root, f.destination, result, {phase: f.phase}, false, f.reader);
  assert.equal(complete.resumed, false);
  assert.equal(fs.existsSync(path.join(f.root, result.retained_staging)), false);
  assert.equal(f.calls(), 1);
});

test('producer failure cleans incomplete staging and emits no outer receipt', async t => {
  const f = fixture(t, 'physical', true);
  await assert.rejects(sourceCohort(f.config, f.reader, f.root, f.destination, f.phase), /Synthetic producer refusal/);
  assert.equal(f.calls(), 1);
  assert.deepEqual(fs.readdirSync(path.join(f.root, '.cache/delivery-handoff')), []);
  assert.equal(fs.existsSync(path.join(f.root, f.destination)), false);
});

test('destination collision retains completed producer bodies and preserves foreign sentinel', async t => {
  const f = fixture(t), result = await sourceCohort(f.config, f.reader, f.root, f.destination, f.phase);
  fs.mkdirSync(path.join(f.root, f.destination)); fs.writeFileSync(path.join(f.root, f.destination, 'sentinel'), 'original');
  assert.throws(() => publishCompletedSource(f.root, f.destination, result, {phase: f.phase}, false, f.reader), /Occupied destination.*retained.*outer publication incomplete/);
  assert.equal(fs.readFileSync(path.join(f.root, f.destination, 'sentinel'), 'utf8'), 'original');
  assert.ok(fs.existsSync(path.join(f.root, result.retained_staging, 'products/execution-receipt.json')));
  assert.equal(f.calls(), 1);
});

test('invalid completed output inventory cleans private staging rather than retaining unvalidated products', async t => {
  const f = fixture(t); f.invalidOutput();
  await assert.rejects(sourceCohort(f.config, f.reader, f.root, f.destination, f.phase), /Incomplete or foreign source output inventory/);
  assert.deepEqual(fs.readdirSync(path.join(f.root, '.cache/delivery-handoff')), []);
});

test('dangling destination symlink preserves the link and retained completed producer bodies', async t => {
  const f = fixture(t), result = await sourceCohort(f.config, f.reader, f.root, f.destination, f.phase);
  fs.symlinkSync('missing-original', path.join(f.root, f.destination));
  assert.throws(() => publishCompletedSource(f.root, f.destination, result, {phase: f.phase}, false, f.reader), /Nonordinary output ancestor.*retained.*outer publication incomplete/);
  assert.equal(fs.readlinkSync(path.join(f.root, f.destination)), 'missing-original');
  assert.ok(fs.existsSync(path.join(f.root, result.retained_staging, 'products/execution-receipt.json')));
});

test('later cumulative-byte refusal preserves completed staging and no publication receipt', async t => {
  const f = fixture(t), result = await sourceCohort(f.config, f.reader, f.root, f.destination, f.phase);
  f.refuse('Aggregate evidence preparation budget exceeded');
  await assert.rejects(async () => publishCompletedSource(f.root, f.destination, result, {phase: f.phase}, false, f.reader), /Aggregate evidence preparation budget exceeded.*retained.*outer publication incomplete/);
  assert.ok(fs.existsSync(path.join(f.root, result.retained_staging, 'products/execution-receipt.json')));
  assert.equal(fs.existsSync(path.join(f.root, f.destination)), false);
  assert.equal(f.calls(), 1);
});

test('pre-science child admission refusal creates no staging or outer destination', async t => {
  const f = fixture(t); f.config.processing_allowance = {phaseBytes: 4 * 1024 ** 3, rssBytes: 4 * 1024 ** 3};
  await assert.rejects(sourceCohort(f.config, f.reader, f.root, f.destination, f.phase), /exceeds current memory admission/);
  assert.equal(f.calls(), 0);
  assert.equal(fs.existsSync(path.join(f.root, '.cache/delivery-handoff')), false);
});

test('delayed cleanup refuses a replaced staging directory and preserves the foreign sentinel after valid publication', async t => {
  const f = fixture(t), result = await sourceCohort(f.config, f.reader, f.root, f.destination, f.phase);
  const stage = path.join(f.root, result.retained_staging);
  fs.renameSync(stage, stage + '-original'); fs.mkdirSync(stage); fs.writeFileSync(path.join(stage, 'sentinel'), 'foreign');
  assert.throws(() => publishCompletedSource(f.root, f.destination, result, {phase: f.phase}, false, f.reader),
    error => /Outer publication complete/.test(error.message) && /cleanup.*identity changed/.test(error.message));
  assert.equal(fs.readFileSync(path.join(stage, 'sentinel'), 'utf8'), 'foreign');
  assert.ok(fs.existsSync(stage + '-original/products/execution-receipt.json'));
  assert.ok(fs.existsSync(path.join(f.root, f.destination, 'preparation.json')));
});

test('delayed cleanup refuses a replaced ancestor even when the original staging inode is restored', async t => {
  const f = fixture(t), result = await sourceCohort(f.config, f.reader, f.root, f.destination, f.phase);
  const stage = path.join(f.root, result.retained_staging), original = fs.statSync(stage);
  const parent = path.dirname(stage), movedParent = parent + '-original';
  fs.renameSync(parent, movedParent); fs.mkdirSync(parent);
  fs.renameSync(path.join(movedParent, path.basename(stage)), stage);
  const restored = fs.statSync(stage);
  assert.equal(restored.dev, original.dev); assert.equal(restored.ino, original.ino);
  fs.writeFileSync(path.join(parent, 'sentinel'), 'foreign ancestor');
  assert.throws(() => publishCompletedSource(f.root, f.destination, result, {phase: f.phase}, false, f.reader),
    error => /Outer publication complete.*cleanup.*identity changed/.test(error.message) && error.message.endsWith(parent));
  assert.equal(fs.readFileSync(path.join(parent, 'sentinel'), 'utf8'), 'foreign ancestor');
  assert.ok(fs.existsSync(path.join(stage, 'products/execution-receipt.json')));
  assert.ok(fs.existsSync(path.join(f.root, f.destination, 'preparation.json')));
});

for (const phase of ['source', 'physical']) test(`${phase} actual plain CLI retains completed products on final receipt-byte refusal`, t => {
  const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'completed-cli-')));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const python = path.join(root, 'fixture-runtime');
  const names = phase === 'physical' ? ['whole-target-support.json', 'execution-receipt.json']
    : ['original-stage-inputs.json', 'cohort-intervals.json', 'cohort-config.json', 'source-qualification.json', 'execution-receipt.json'];
  fs.writeFileSync(python, '#!/bin/sh\nwhile [ "$1" != "--output" ]; do shift; done\nshift\nmkdir "$1"\n' + names.map(name => `printf '{}\\n' > "$1/${name}"`).join('\n') + '\n', {mode: 0o700});
  const body = fs.readFileSync(python), pin = {path: python, bytes: body.length, sha256: sha(body)};
  const config = {version: 1, preparation_allowance: {phaseBytes: 1, rssBytes: 256 * 1024 ** 2},
    processing_allowance: {phaseBytes: 256 * 1024 ** 2, rssBytes: 256 * 1024 ** 2},
    runtime_inventory: {python: pin, files: [pin]}, [phase]: {version: 1, inputs: [], resources: {output_bytes: names.length * 3}}};
  for (let i = 0; i < 10; i++) config.preparation_allowance.phaseBytes = Buffer.byteLength(JSON.stringify(config)) + names.length * 3;
  fs.writeFileSync(path.join(root, 'config.json'), JSON.stringify(config));
  const entry = fileURLToPath(new URL('../scripts/prepare-delivery-handoff.mjs', import.meta.url));
  const run = childProcess.spawnSync(process.execPath, [entry, phase, 'config.json', '.cache/delivery-handoff/complete'],
    {cwd: root, encoding: 'utf8', env: {...process.env, NODE_OPTIONS: '', NODE_PATH: ''}});
  assert.equal(run.status, 1, run.stderr);
  assert.match(run.stderr, /Aggregate evidence preparation budget exceeded.*completed producer staging retained at/);
  assert.match(run.stderr, /outer publication incomplete/);
  assert.equal(fs.existsSync(path.join(root, '.cache/delivery-handoff/complete/preparation.json')), false);
  const stages = fs.readdirSync(path.join(root, '.cache/delivery-handoff')).filter(name => name.startsWith('source-'));
  assert.equal(stages.length, 1);
  for (const name of names) assert.equal(fs.readFileSync(path.join(root, '.cache/delivery-handoff', stages[0], 'products', name), 'utf8'), '{}\n');
  for (const name of ['source-config.json', 'admission.json']) assert.ok(fs.statSync(path.join(root, '.cache/delivery-handoff', stages[0], name)).size > 0);
});

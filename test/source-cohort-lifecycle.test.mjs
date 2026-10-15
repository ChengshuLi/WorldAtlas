import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync, spawnSync} from 'node:child_process';
import {sourceCohort, resumeSource, publish, jsonBytes, digest} from '../scripts/prepare-delivery-handoff.mjs';
import {candidateBudget} from '../scripts/native-ownership/native-preparation-guards.mjs';

function fixture(t, phase = 'physical') {
  const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'source-lifecycle-')));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const destination = '.cache/delivery-handoff/final';
  fs.writeFileSync(path.join(root, 'input.json'), '{}');
  const input = {commit: 'a'.repeat(40), path: 'input.json', bytes: 2, sha256: digest(Buffer.from('{}'))};
  const executable = path.join(root, 'synthetic-runtime');
  fs.writeFileSync(executable, 'synthetic child runner is injected');
  const python = {path: executable, bytes: fs.statSync(executable).size, sha256: digest(fs.readFileSync(executable))};
  const config = {version: 1, preparation_allowance: {phaseBytes: 134217728, rssBytes: 134217728},
    processing_allowance: {phaseBytes: 1048576, rssBytes: 1048576}, runtime_inventory: {python, files: [python]},
    [phase]: {version: 1, inputs: [input], physical_reproducer: input, resources: {output_bytes: 65536}}};
  const binding = value => ({phase, config_sha256: digest(jsonBytes(value)),
    program_sha256: digest(fs.readFileSync(new URL('../scripts/qualify-source-cohort.py', import.meta.url))),
    entry_sha256: digest(fs.readFileSync(new URL('../scripts/prepare-delivery-handoff.mjs', import.meta.url)))});
  let executions = 0, reads = 0;
  function reader() {
    return {budget: candidateBudget([], {reserveBytes: 0, reserveDescriptors: 0, allowance: config.preparation_allowance}),
      read(pin) {
        reads++;
        const raw = fs.readFileSync(path.join(root, pin.path));
        assert.equal(pin.mode, '100644');
        assert.equal(raw.length, pin.bytes); assert.equal(digest(raw), pin.sha256, 'immutable input differs');
        return raw;
      }};
  }
  function execute(actualExecutable, args) {
    executions++;
    assert.equal(actualExecutable, executable);
    const value = flag => args[args.indexOf(flag) + 1];
    const output = value('--output'), admission = JSON.parse(fs.readFileSync(value('--admission')));
    assert.equal(value('--publication-prefix'), destination);
    const names = phase === 'physical' ? ['whole-target-support.json'] :
      ['original-stage-inputs.json', 'cohort-intervals.json', 'cohort-config.json', 'source-qualification.json'];
    const products = Object.fromEntries(names.map(name => [name,
      jsonBytes(name === 'source-qualification.json' ? {fresh_admission: admission, original_elapsed: 17} : {retained: name})]));
    products['execution-receipt.json'] = jsonBytes({complete: true,
      program: {path: 'scripts/qualify-source-cohort.py', sha256: binding(config).program_sha256},
      fresh_admission: admission, elapsed_seconds: 17, peak_rss_bytes: 123456,
      outputs: names.map(name => ({path: destination + '/' + name, bytes: products[name].length, sha256: digest(products[name])}))});
    fs.mkdirSync(output);
    for (const [name, raw] of Object.entries(products)) fs.writeFileSync(path.join(output, name), raw);
  }
  const run = (value = config, options = {}) => sourceCohort(value, reader(), root, destination, phase,
    {binding: binding(value), execute, ...options});
  return {root, destination, config, binding, run, reader,
    counts: () => ({executions, reads})};
}

function snapshot(directory) {
  const files = {};
  for (const name of fs.readdirSync(directory).sort()) {
    const filename = path.join(directory, name);
    if (fs.statSync(filename).isDirectory()) {
      for (const [child, value] of Object.entries(snapshot(filename))) files[name + '/' + child] = value;
    } else files[name] = {raw: fs.readFileSync(filename), mtime: fs.statSync(filename).mtimeMs};
  }
  return files;
}

for (const phase of ['source', 'physical']) test(phase + ' completed child survives outer refusal and resumes without execution', async t => {
  const f = fixture(t, phase), first = await f.run(), stage = path.join(f.root, first.staging);
  const before = snapshot(stage), originalReceipt = first.products['execution-receipt.json'];
  assert.deepEqual(Object.keys(before).sort(), ['admission.json', 'source-config.json',
    ...Object.keys(first.products).map(name => 'products/' + name), 'products/preparation.json'].sort());
  assert.throws(() => publish(f.root, f.destination, first.products, f.binding(f.config), false,
    {add() { throw Error('Current preparation RSS allowance exceeded'); }}), /RSS allowance/);
  assert.equal(fs.existsSync(path.join(f.root, f.destination)), false);
  assert.deepEqual(snapshot(stage), before);
  await assert.rejects(f.run(), /explicit --resume/);
  const resumed = await f.run(f.config, {resume: true});
  assert.equal(f.counts().executions, 1);
  assert.ok(f.counts().reads > 0, 'resume authenticates immutable inputs with a fresh reader');
  assert.equal(resumed.observation.reused_child_outputs, true);
  assert.deepEqual(resumed.products, first.products);
  assert.deepEqual(resumed.products['execution-receipt.json'], originalReceipt);
  assert.deepEqual(snapshot(stage), before, 'old admission/runtime/timing and all retained bytes remain literal');
  publish(f.root, f.destination, resumed.products, f.binding(f.config), true, f.reader().budget);
  resumed.cleanup();
  assert.equal(fs.existsSync(stage), false);
  assert.deepEqual(fs.readFileSync(path.join(f.root, f.destination, 'execution-receipt.json')), originalReceipt);
  assert.equal(resumeSource(f.root, f.destination, f.config, f.binding(f.config), f.reader()).resumed, true);
});

test('changed, corrupt and incomplete private stages refuse without a second child', async t => {
  const changes = [
    ['phase config', (f, first, config) => { config.physical.resources.output_bytes++; }],
    ['outer config', (f, first, config) => { config.preparation_allowance.phaseBytes--; }],
    ['runtime binding', (f, first, config) => { config.runtime_inventory.files[0].sha256 = 'b'.repeat(64); }],
    ['corrupt product', (f, first) => fs.appendFileSync(path.join(f.root, first.staging, 'products/whole-target-support.json'), '\n')],
    ['partial receipt', (f, first) => fs.unlinkSync(path.join(f.root, first.staging, 'products/preparation.json'))],
    ['foreign output', (f, first) => fs.writeFileSync(path.join(f.root, first.staging, 'products/foreign.json'), '{}')],
    ['changed immutable input', f => fs.writeFileSync(path.join(f.root, 'input.json'), '[]')],
    ['admission drift', (f, first) => {
      const filename = path.join(f.root, first.staging, 'admission.json');
      const admission = JSON.parse(fs.readFileSync(filename)); admission.observed_unix_seconds--;
      fs.writeFileSync(filename, jsonBytes(admission));
    }],
    ['foreign execution binding', (f, first) => {
      const filename = path.join(f.root, first.staging, 'products/preparation.json');
      const preparation = JSON.parse(fs.readFileSync(filename)); preparation.binding.entry_sha256 = 'c'.repeat(64);
      fs.writeFileSync(filename, jsonBytes(preparation));
    }]
  ];
  for (const [name, change] of changes) await t.test(name, async t => {
    const f = fixture(t), first = await f.run(), config = structuredClone(f.config);
    change(f, first, config);
    const before = snapshot(path.join(f.root, first.staging));
    await assert.rejects(f.run(config, {resume: true}));
    assert.equal(f.counts().executions, 1);
    assert.equal(fs.existsSync(path.join(f.root, f.destination)), false);
    assert.deepEqual(snapshot(path.join(f.root, first.staging)), before, 'refusal preserves the retained attempt');
  });
});

test('resume without a retained stage refuses and failed child cleans its owned scratch', async t => {
  const f = fixture(t);
  await assert.rejects(f.run(f.config, {resume: true}), /No completed private source stage/);
  assert.equal(f.counts().executions, 0);
  await assert.rejects(f.run(f.config, {execute() { throw Error('synthetic child failed'); }}), /synthetic child failed/);
  assert.deepEqual(fs.readdirSync(path.join(f.root, '.cache/delivery-handoff')), []);
});

test('actual unchanged CLI --resume publishes retained stage and releases it without running the child', async t => {
  const f = fixture(t), env = {...process.env, GIT_CONFIG_GLOBAL: '/dev/null', GIT_CONFIG_NOSYSTEM: '1'};
  delete env.NODE_OPTIONS; delete env.NODE_PATH;
  const git = (...args) => execFileSync('git', ['-C', f.root, ...args], {env, encoding: 'utf8'}).trim();
  git('init', '--quiet'); git('add', 'input.json');
  git('-c', 'user.name=Lifecycle fixture', '-c', 'user.email=lifecycle@example.invalid',
    '-c', 'commit.gpgsign=false', 'commit', '--quiet', '-m', 'Synthetic immutable input');
  Object.assign(f.config.physical.inputs[0], {commit: git('rev-parse', 'HEAD'), git_blob_oid: git('rev-parse', 'HEAD:input.json')});
  const first = await f.run();
  fs.writeFileSync(path.join(f.root, 'config.json'), jsonBytes(f.config));
  // The synthetic runtime is deliberately nonexecutable. A mistaken child replay
  // therefore fails instead of silently producing a second synthetic result.
  const result = spawnSync(process.execPath, [fileURLToPath(new URL('../scripts/prepare-delivery-handoff.mjs', import.meta.url)),
    'physical', 'config.json', f.destination, '--resume'], {cwd: f.root, env, encoding: 'utf8', timeout: 30000, maxBuffer: 131072});
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(JSON.parse(result.stdout).observation.reused_child_outputs, true);
  assert.equal(f.counts().executions, 1);
  assert.equal(fs.existsSync(path.join(f.root, first.staging)), false);
  assert.deepEqual(fs.readFileSync(path.join(f.root, f.destination, 'execution-receipt.json')), first.products['execution-receipt.json']);
});

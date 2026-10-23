import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';

const source = fs.realpathSync(process.cwd());
const eastern = 'coordination/engineering/eastern-two-gap-repair-native-20261007';
const arctic = 'coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008';
for (const [label, module, exported] of [
  ['v2 dispatcher', 'scripts/native-ownership/validate-build-context-stage.mjs', 'validateBuildContextStage'],
  ['Arctic predecessor', `${arctic}/predecessor-context-v9.mjs`, 'validateChainedBuildContext']
]) test(`${label} parses the authenticated historical code index before requesting parts`, () => {
  const temporary = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'context-code-index-')));
  try {
    // The real custody API requires plain Node and a committed source fixture.
    // Its miniature package is synthetic; both validators and byte checks are real.
    const runner = path.join(temporary, 'boundary.mjs');
    fs.writeFileSync(runner, `
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {issueCurrentExecution}
  from ${JSON.stringify(pathToFileURL(path.join(source, eastern, 'current-execution.mjs')).href)};
import {${exported} as validate} from ${JSON.stringify(pathToFileURL(path.join(source, module)).href)};
const source = ${JSON.stringify(source)}, root = ${JSON.stringify(path.join(temporary, 'code'))};
fs.mkdirSync(root);
// The same minimal synthetic custody boundary used by current-execution-controls.
// No historical products or copied production import rosters are needed here.
for (const name of ['package.json', '.github/package-inputs.json',
  'scripts/build-static-inner.mjs', 'scripts/package-build.mjs',
  'scripts/native-ownership/validate-build-context-stage.mjs',
  ${JSON.stringify(eastern + '/current-execution.mjs')}]) {
  const to = path.join(root, name);
  fs.mkdirSync(path.dirname(to), {recursive:true});
  fs.writeFileSync(to, name.endsWith('.json') ? '{}' : '// Synthetic custody fixture only\\n');
}
const git = (...args) => execFileSync('git', ['-C', root, ...args], {stdio:'pipe'});
git('init', '-q'); git('add', '.');
git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'current code only');
const record = issueCurrentExecution({source:root, stage:root});
const fixture = path.join(source, 'test/fixtures/current-execution-authored');
const stagePath = 'data/native-context-migration/manifest.json';
const stageRaw = fs.readFileSync(path.join(fixture, 'stage-manifest.json')), stage = JSON.parse(stageRaw);
const indexRaw = fs.readFileSync(path.join(fixture, 'index.json'));
assert.equal(createHash('sha256').update(indexRaw).digest('hex'), 'de4a8f7aac3380fc7c5f1cc06ac9bbf0d170c0921d7ef72d5e46187439a80be9');
const codeBase = ${JSON.stringify(eastern + '/current-consumer-code')};
const firstPart = codeBase + '/' + JSON.parse(indexRaw).parts[0].path;
const stop = new Error('authenticated index requested its first part');
async function run({body=indexRaw, execution=record, part}={}) {
  const reads = [];
  const readFile = (name, role) => {
    assert.equal(role, 'candidate'); reads.push(name);
    if (name === stagePath) return stageRaw;
    if (name === codeBase + '/index.json') return body;
    assert.equal(name, firstPart, 'No unrelated historical input may be read');
    if (part) return part;
    throw stop;
  };
  let error;
  try { await validate({root, stagePath, stageRaw, stage, readFile, currentExecution:execution}); }
  catch (caught) { error = caught; }
  assert(error, 'This bounded control must stop before reconstruction');
  assert(!fs.existsSync(path.join(root, '.cache')), 'No reconstruction output may be created');
  return {error, reads:reads.filter(name => name !== stagePath)};
}
const positive = await run();
assert.equal(positive.error, stop);
assert.deepEqual(positive.reads, [codeBase + '/index.json', firstPart]);
const changed = Buffer.concat([indexRaw, Buffer.from(' ')]); // Valid JSON, different pinned bytes.
const tampered = await run({body:changed});
assert.equal(tampered.error.code, 'ERR_ASSERTION');
assert.deepEqual(tampered.reads, [codeBase + '/index.json']);
const unbranded = await run({execution:structuredClone(record)});
assert.match(unbranded.error.message, /authenticated package-boundary binding/);
assert.deepEqual(unbranded.reads, []);
const wrongPart = await run({part:Buffer.alloc(JSON.parse(indexRaw).parts[0].bytes)});
assert.equal(wrongPart.error.code, 'ERR_ASSERTION');
assert.deepEqual(wrongPart.reads, positive.reads);
process.stdout.write('authenticated index, source custody and part hash boundaries verified');
`);
    const output = execFileSync(process.execPath, [runner], {
      encoding:'utf8', env:{...process.env, NODE_OPTIONS:'', NODE_PATH:''}, maxBuffer:1024*1024
    });
    assert.equal(output, 'authenticated index, source custody and part hash boundaries verified');
  } finally { fs.rmSync(temporary, {recursive:true, force:true}); }
});

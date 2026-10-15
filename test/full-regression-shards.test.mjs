import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fullRegressionShard, integrationTestFiles, PACKAGED_ASSET_TESTS, DATABASE_NEIGHBOR_TESTS, MIGRATION_WORKER_TESTS, COMPONENT_CONTROL_TEST} from '../scripts/run-integration-tests.mjs';
import {integrationProfile, sourceDatabaseFocusedTests, SOURCE_DATABASE_TEST_PATHS} from '../scripts/integration-profile.mjs';

const inventory = fs.readdirSync('test').filter(name => name.endsWith('.test.mjs'))
  .map(name => `test/${name}`).sort();
function verifyAssignment(files) {
  const shards = [0, 1, 2].map(shard => fullRegressionShard(files, shard));
  assert.deepEqual(shards.flat().sort(), [...files].sort());
  assert.equal(new Set(shards.flat()).size, files.length);
  for (const name of PACKAGED_ASSET_TESTS.filter(name => files.includes(name))) {
    assert.deepEqual(shards.map((files, shard) => files.includes(name) ? shard : null).filter(n => n !== null), [0]);
  }
  for (const name of DATABASE_NEIGHBOR_TESTS.filter(name => files.includes(name))) {
    assert.deepEqual(shards.flatMap((files, shard) => files.includes(name) ? [shard] : []), [1]);
  }
  for (const name of MIGRATION_WORKER_TESTS.filter(name => files.includes(name))) {
    assert.deepEqual(shards.flatMap((files, shard) => files.includes(name) ? [shard] : []), [2]);
  }
  for (const name of [COMPONENT_CONTROL_TEST].filter(name => files.includes(name))) {
    assert.deepEqual(shards.flatMap((files, shard) => files.includes(name) ? [shard] : []), [1]);
  }
}
test('every real full-suite file runs once, with heavy migration tests separate from packaged parity', () => {
  verifyAssignment(inventory);
  for (const shard of [0, 1, 2]) assert.deepEqual(integrationTestFiles('full', shard), fullRegressionShard(inventory, shard));
});
test('inserting a new filename cannot move reserved heavy workloads or omit any discovered file', () => {
  for (const added of ['test/000-new.test.mjs', 'test/mmm-new.test.mjs', 'test/zzz-new.test.mjs']) {
    verifyAssignment([...inventory, added].sort());
  }
});
test('a partial or future inventory never invents a reserved test or omits an unknown file', () => {
  verifyAssignment(['test/future-one.test.mjs', 'test/future-two.test.mjs']);
  verifyAssignment(inventory.filter(name => !DATABASE_NEIGHBOR_TESTS.includes(name)));
  verifyAssignment([]);
});
test('duplicate inventory entries are rejected by the exhaustive coverage control', () => {
  assert.throws(() => verifyAssignment([...inventory, inventory[0]]));
});
test('test-runner edits and renames require actual full-suite validation', () => {
  for (const file of [{filename:'scripts/run-integration-tests.mjs'},
    {filename:'docs/runner.md', previous_filename:'scripts/run-integration-tests.mjs'}]) {
    assert.equal(integrationProfile('engineering/example', [file]), 'full');
  }
  assert.equal(integrationProfile('engineering/example', [{filename:'docs/runner.md'}]), 'evidence');
});
test('ordinary selected delivery has no unit inventory while software and explicit output proof retain asset checks',()=>{
  assert.throws(()=>integrationTestFiles('full',0,'selected-data'),/Invalid trusted test selection/);
  const reused=integrationTestFiles('full',0,'selected-output');
  assert.deepEqual(reused,['test/compact-ownership.test.mjs']);
  for(const file of PACKAGED_ASSET_TESTS)assert(integrationTestFiles('full',0,'complete').includes(file));
  for(const [profile,shard,selection] of [['evidence',0,'selected-data'],['full',1,'selected-data'],['full',0,'unknown']])
    assert.throws(()=>integrationTestFiles(profile,shard,selection),/Invalid trusted test selection/);
});


test('ordinary source database test-only changes select every actual changed consumer without changing default evidence work', () => {
  const names = [...SOURCE_DATABASE_TEST_PATHS].reverse();
  const files = names.map(filename => ({filename, status:'modified'}));
  const entries = new Map(names.map(name => [name, {type:'blob', mode:'100644', sha:'a'.repeat(40)}]));
  const expected = [...names].sort();
  assert.equal(integrationProfile('engineering/example', files, {}, entries), 'evidence');
  assert.deepEqual(sourceDatabaseFocusedTests('engineering/example', files, entries), expected);
  assert.deepEqual(integrationTestFiles('evidence', 0, 'complete', expected), expected);
  for (const file of files) {
    assert.deepEqual(sourceDatabaseFocusedTests('engineering/example', [file], entries), [file.filename]);
    assert.deepEqual(integrationTestFiles('evidence', 0, 'complete', [file.filename]), [file.filename]);
  }
  const defaults = integrationTestFiles('evidence', 0);
  assert.equal(defaults.length, 28);
  assert(defaults.every(name => !SOURCE_DATABASE_TEST_PATHS.includes(name)));
  assert.equal(sourceDatabaseFocusedTests('engineering/example', [{filename:defaults[0], status:'modified'}], entries), null);
  const mixed = [...files, {filename:defaults[0], status:'modified'}];
  entries.set(defaults[0], {type:'blob', mode:'100644', sha:'b'.repeat(40)});
  assert.deepEqual(sourceDatabaseFocusedTests('engineering/example', mixed, entries), mixed.map(file => file.filename).sort());
});

test('source database routing retains full validation for model, production, runner, unknown and nonordinary changes', () => {
  const filename = SOURCE_DATABASE_TEST_PATHS[0], valid = {filename, status:'modified'};
  const ordinary = {type:'blob', mode:'100644', sha:'a'.repeat(40)};
  const entries = new Map([[filename, ordinary]]);
  const declined = files => {
    assert.equal(integrationProfile('engineering/example', files, {}, entries), 'full');
    assert.equal(sourceDatabaseFocusedTests('engineering/example', files, entries), null);
  };
  for (const other of ['test/model.test.mjs', 'test/future.test.mjs', 'scripts/run-integration-tests.mjs',
    'scripts/verify-postgres-schema.mjs', 'hosted/records.js', 'data/hosted-type-catalog.json', 'test/helper.py'])
    declined([valid, {filename:other, status:'modified'}]);
  for (const status of ['added','removed','renamed','copied','changed','unchanged']) declined([{filename,status}]);
  declined([{...valid,previous_filename:'test/renamed.test.mjs'}]);
  declined([valid,valid]);
  for (const row of [undefined,{...ordinary,mode:'120000'},{...ordinary,mode:'100755'},
    {...ordinary,type:'tree'},{...ordinary,sha:'invalid'}]) {
    entries.set(filename,row); declined([valid]);
  }
  entries.set(filename,ordinary);
  assert.equal(integrationProfile('research/example', [valid], {}, entries), 'full');
  assert.equal(integrationProfile('engineering/example', [valid]), 'full');
});

test('focused database consumer override rejects missing, duplicate, foreign and wrong-profile inventories', () => {
  const name = SOURCE_DATABASE_TEST_PATHS[0];
  for (const roster of [[],{},[name,name],['test/model.test.mjs'],['test/issue-claims.test.mjs'],[null],
    [name,'test/nonexistent.test.mjs']]) assert.throws(() => integrationTestFiles('evidence',0,'complete',roster));
  for (const [profile,shard,selection] of [['full',0,'complete'],['evidence',1,'complete'],
    ['full',0,'selected-output'],['evidence',0,'selected-data']])
    assert.throws(() => integrationTestFiles(profile,shard,selection,[name]));
});


test('hosted evidence entrypoint refuses omitted or empty focused metadata before executing any tests', () => {
  for (const value of [undefined, '', '   ']) {
    const env = {...process.env, GITHUB_ACTIONS:'true', INTEGRATION_PROFILE:'evidence', INTEGRATION_SHARD:'0'};
    if (value === undefined) delete env.INTEGRATION_FOCUSED_TEST_FILES;
    else env.INTEGRATION_FOCUSED_TEST_FILES = value;
    const result = spawnSync(process.execPath, ['scripts/run-integration-tests.mjs'], {env,encoding:'utf8'});
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /Trusted focused test metadata is missing/);
    assert.doesNotMatch(result.stdout, /TAP version|"files"/);
  }
});

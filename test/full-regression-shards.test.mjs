import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fullRegressionShard, integrationTestFiles, PACKAGED_ASSET_TESTS, DATABASE_NEIGHBOR_TESTS, MIGRATION_WORKER_TESTS, COMPONENT_CONTROL_TEST} from '../scripts/run-integration-tests.mjs';
import {integrationProfile} from '../scripts/integration-profile.mjs';
import {currentExecutionClosure} from '../coordination/engineering/eastern-two-gap-repair-native-20261007/current-execution.mjs';

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
test('test-runner edits use actual focused runner controls', () => {
  for (const file of [{filename:'scripts/run-integration-tests.mjs'},
    {filename:'docs/runner.md', previous_filename:'scripts/run-integration-tests.mjs'}]) {
    assert.equal(integrationProfile('engineering/example', [file]), 'evidence');
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

// Exercise the existing production closure, not a second import resolver. If a
// builder starts consuming these methods, its focused-only route needs review.
test('focused comparison and checkpoint methods stay outside each actual builder execution closure',()=>{
  const prefix='coordination/engineering/selected-geography-effective-prevention-20261009/';
  const methods=['scripts/check-effective-geographic-regression.mjs','scripts/selected-checkpoint-native.mjs', 'scripts/run-geographic-check.py',
    prefix+'selected-checkpoint.mjs',prefix+'selected-joint-entry.mjs','test/fixtures/selected-checkpoint.mjs'];
  for(const entry of ['scripts/build-static-inner.mjs','scripts/build-hosted-inner.mjs','scripts/build-cloudflare-inner.mjs']) {
    const closure=currentExecutionClosure(process.cwd(),entry);
    for(const method of methods)assert(!closure.includes(method),entry+' now executes '+method);
  }
});

test('reviewed selection runs only its actual ordinary roster and rejects accidental empty or escaping input', () => {
  const cwd=process.cwd(),directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-reviewed-tests-'));
  const encoded=files=>Buffer.from(JSON.stringify(files)).toString('base64');
  try {
    fs.mkdirSync(path.join(directory,'test'));fs.writeFileSync(path.join(directory,'test/one.test.mjs'),'');
    fs.writeFileSync(path.join(directory,'test/unrelated.test.mjs'),'');process.chdir(directory);
    assert.deepEqual(integrationTestFiles('evidence',0,'reviewed',encoded(['test/one.test.mjs'])),['test/one.test.mjs']);
    assert.deepEqual(integrationTestFiles('full',0,'reviewed',encoded(['test/one.test.mjs'])),['test/one.test.mjs']);
    for(const files of [[],['test/missing.test.mjs'],['../one.test.mjs'],['test/one.test.mjs','test/one.test.mjs'],[null]])
      assert.throws(()=>integrationTestFiles('evidence',0,'reviewed',encoded(files)),/reviewed/);
    assert.throws(()=>integrationTestFiles('evidence',0,'reviewed',''),/roster/);
    assert.throws(()=>integrationTestFiles('full',1,'reviewed',encoded(['test/one.test.mjs'])),/selection/);
    fs.symlinkSync('one.test.mjs','test/link.test.mjs');
    assert.throws(()=>integrationTestFiles('evidence',0,'reviewed',encoded(['test/link.test.mjs'])),/reviewed/);
    fs.renameSync('test','real-tests');fs.symlinkSync('real-tests','test');
    assert.throws(()=>integrationTestFiles('evidence',0,'reviewed',encoded(['test/one.test.mjs'])),/reviewed/);
  } finally {process.chdir(cwd);fs.rmSync(directory,{recursive:true,force:true});}
});

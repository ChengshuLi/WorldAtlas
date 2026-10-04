import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fullRegressionShard, integrationTestFiles, PACKAGED_ASSET_TESTS, DATABASE_NEIGHBOR_TESTS, MIGRATION_WORKER_TESTS} from '../scripts/run-integration-tests.mjs';
import {integrationProfile} from '../scripts/integration-profile.mjs';

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

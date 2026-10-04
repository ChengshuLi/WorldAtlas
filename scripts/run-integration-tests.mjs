import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {compileHostedMigrations} from './compile-hosted-migrations.mjs';

export const PACKAGED_ASSET_TESTS = ['test/compact-ownership.test.mjs','test/prepared-parity.test.mjs'];

// Retained full-run TAP costs identify these database suites as heavy neighbors
// of model.test.mjs. Keep them on the otherwise lighter worker, while shard 0
// retains the packaged tests and their required build/browser setup.
export const DATABASE_NEIGHBOR_TESTS = [
  'test/temporal-geography.test.mjs', 'test/postgres-runtime-role.test.mjs',
  'test/reference-hierarchy-release.test.mjs', 'test/hosted-catalog.test.mjs'
];
export function fullRegressionShard(inventory, shard) {
  const placement = new Map([
    ...PACKAGED_ASSET_TESTS.map(name => [name, 0]),
    ...DATABASE_NEIGHBOR_TESTS.map(name => [name, 1]),
    ['test/model.test.mjs', 2]
  ]);
  const reserved = inventory.filter(name => placement.has(name) && placement.get(name) === shard);
  const ordinary = inventory.filter(name => !placement.has(name));
  return [...reserved, ...ordinary.filter((name, index) => index % 3 === shard)];
}

export function integrationTestFiles(profile, shard) {
  if (!['full','evidence'].includes(profile) || !Number.isInteger(shard) || shard < 0 || shard > 2 ||
      (profile === 'evidence' && shard !== 0)) throw Error('Invalid trusted integration test profile');
  const focused = ['handoff-scope','issue-claims','worker-result','regional-research-gate','geography-worker-lane',
    'evidence-quality','premerge-evidence','trusted-workflow-checkouts','merge-integration','merge-integration-client','merge-integration-entrypoint','integration-proof'];
  const inventory = fs.readdirSync('test').filter(name => name.endsWith('.test.mjs')).sort().map(name=>`test/${name}`);
  const files = profile === 'full' ? fullRegressionShard(inventory, shard)
    : focused.map(name => `test/${name}.test.mjs`);
  if (!files.length || files.some(name => !fs.existsSync(name))) throw Error('Missing integration test inventory');
  return files;
}
export function integrationNeedsBrowser(profile, shard) {
  return integrationTestFiles(profile, shard).some(name => /['"](?:@playwright\/test|playwright)['"]/.test(fs.readFileSync(name, 'utf8')));
}
export function prepareIntegrationTests(files) {
  if (files.some(name=>PACKAGED_ASSET_TESTS.includes(name)) && !fs.existsSync('dist/client/atlas-geography.json')) {
    throw Error('Packaged-asset regression requires the actual hosted build; missing dist/client/atlas-geography.json');
  }
  if (files.includes('test/stage-site-migrations.test.mjs')) {
    compileHostedMigrations({input:'drizzle', output:'dist/drizzle'});
  }
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const profile = process.env.INTEGRATION_PROFILE, shard = Number(process.env.INTEGRATION_SHARD);
  const files = integrationTestFiles(profile, shard);
  prepareIntegrationTests(files);
  console.log(JSON.stringify({profile, shard, files}));
  const result = spawnSync(process.execPath, ['--test','--test-reporter=tap','--test-concurrency=2', ...files], {
    encoding:'utf8', maxBuffer:64*1024*1024, env:{...process.env,...(profile==='full' && shard===0?{ATLAS_REQUIRE_STATIC:'1'}:{})}
  });
  process.stdout.write(result.stdout ?? '');
  process.stderr.write(result.stderr ?? '');
  if (result.status === 0 && !/^# skipped 0$/m.test(result.stdout ?? '')) throw Error('Regression did not establish zero skipped tests');
  if (result.status === 0 && /^# skipped [1-9]/m.test(result.stdout ?? '')) throw Error('Skipped tests cannot establish regression coverage');
  if (result.error) throw result.error;
  process.exitCode = result.status ?? 1;
}

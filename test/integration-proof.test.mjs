import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {successfulGeographyJob} from '../scripts/integration-proof.mjs';
import {integrationProfile, COORDINATION_PATHS, candidateGeographyCode} from '../scripts/integration-profile.mjs';

test('geography reuse requires one actual successful producer, independently of step projections', async () => {
  const geography = {id: 44, name: 'geography', status: 'completed', conclusion: 'success', steps: [
    'Checkout trusted geographic checker', 'Install trusted geographic dependencies',
    'Check proposed geography with trusted baseline code',
    'Run actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'
  ].map(name => ({name, status: 'completed', conclusion: 'success'}))};
  for (const mutate of [job => {job.id = 0;}, job => {job.status = 'in_progress';},
    job => {job.conclusion = 'failure';}, job => {job.conclusion = 'skipped';},
    job => {job.conclusion = 'cancelled';}, job => {job.name = 'other';}]) {
    const job = structuredClone(geography); mutate(job); assert.equal(successfulGeographyJob([job]), null);
  }
  for (const steps of [undefined, [], [{name: 'old display name', status: 'in_progress', conclusion: null}]]) {
    assert.equal(successfulGeographyJob([{...geography, steps}])?.id, 44);
  }
  assert.equal(successfulGeographyJob([geography], '.github/workflows/foreign.yml'), null);
  assert.equal(successfulGeographyJob([geography, structuredClone(geography)]), null);
});

test('explicit coordination allowlist defaults full for unknown/application/data/schema/import/deploy/rename impact',()=>{
  for(const filename of COORDINATION_PATHS) assert.equal(integrationProfile('engineering/job',[{filename}]),'evidence',filename);
  for(const filename of ['src/attributes.js','hosted/a.mjs','drizzle/0001.sql','data/hierarchy.json',
    'scripts/import.mjs','scripts/build-hosted.mjs','docs/unknown.json',
    '.github/workflows/deploy.yml','test/application.test.mjs']) {
    assert.equal(integrationProfile('engineering/job',[{filename}]),'full',filename);
    assert.equal(integrationProfile('engineering/job',[{filename:'docs/WORKER_COORDINATION.md',previous_filename:filename}]),'full',filename);
  }
  assert.equal(integrationProfile('engineering/job',[{filename:'docs/prompts/reviewer.md'}]),'evidence');
  assert.equal(integrationProfile('engineering/job',[]),'full');
});


test('queue profile retains geography owned scope and full fallback outside it',()=>{
 const branch='geography/regional-review-example',owned='data/regional-review/regional-review-example/';
 const reservation={mode:'geography',owned_paths:[owned]};
 assert.equal(integrationProfile(branch,[{filename:owned+'finding.json'}],reservation),'evidence');
 for(const file of [{filename:'src/main.js'},{filename:owned+'finding.json',previous_filename:'src/main.js'}])assert.equal(integrationProfile(branch,[file],reservation),'full');
});

// Package selection is a coordination control. Exercise its focused contracts
// when the runner omits application regression; full discovery runs that file
// separately, so do not register the same tests twice in the full profile.
if (process.env.INTEGRATION_PROFILE === 'evidence') await import('./deployment-budget-scope.test.mjs');

test('package CI coordination paths use focused tests while package verification, builders and runners stay full', () => {
  for (const filename of ['scripts/classify-deployment-budget.mjs',
    '.github/workflows/deployment-budget.yml']) {
    assert.equal(integrationProfile('engineering/example', [{filename}]), 'evidence', filename);
  }
  for (const filename of ['scripts/build-hosted.mjs', 'scripts/build-static.mjs', 'scripts/deployment-budget.mjs',
    'scripts/package-inputs.mjs', 'scripts/package-build.mjs', '.github/package-inputs.json',
    'scripts/build-cloudflare-inner.mjs', 'test/deployment-budget-scope.test.mjs', 'test/package-build.test.mjs', 'scripts/run-integration-tests.mjs', 'src/main.js', 'data/hierarchy.json', 'drizzle/0002.sql']) {
    assert.equal(integrationProfile('engineering/example', [{filename}]), 'full', filename);
  }
  assert.equal(integrationProfile('engineering/example', [{filename:'scripts/classify-deployment-budget.mjs', previous_filename:'src/main.js'}]), 'full');
});

test('geography software route is derived from changed checker inputs, retaining data and source-only routes', async () => {
 const changed = filename => [{filename, status: 'modified'}];
 const {CURRENT_REBIND_CODE} = await import('../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs');
 for (const name of CURRENT_REBIND_CODE) assert.equal(candidateGeographyCode('full', changed(name)), true, name);
 for (const name of ['scripts/run-geographic-check.py', 'scripts/check-effective-geographic-regression.mjs',
  'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs',
  'src/ownership-codec.js', 'src/native-grid.js', 'src/reference-metadata.js', 'requirements.txt']) {
  assert.equal(candidateGeographyCode('full', changed(name)), true, name);
  assert.equal(candidateGeographyCode('evidence', changed(name)), false, name);
  assert.equal(candidateGeographyCode('full', changed(name), 'selected-data'), false, name);
 }
 for (const name of ['data/geography/part-0.json', 'src/app.js', 'src/attributes.js',
  'research/geography/example/source.py', 'docs/WORKER_COORDINATION.md',
  'coordination/engineering/example/evidence-quality.json', 'scripts/native-ownership/verified-candidates.json']) {
  assert.equal(candidateGeographyCode('full', changed(name)), false, name);
 }
 assert.equal(candidateGeographyCode('full', [...changed('data/geography/part-0.json'),
  ...changed('coordination/engineering/example/source-adjudication.json')]), false);
 assert.equal(candidateGeographyCode('full', [{filename: 'docs/removed.txt', previous_filename: 'scripts/check-geographic-regression.py'}]), true);
});

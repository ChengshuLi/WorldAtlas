import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';

const baseline = 'a1fd3383e89dea4c4497bf3a6f469494871ad758';
const directory = 'data/engineering/storage-handoff-20261003-a9c2';
const documents = [
  'docs/ENGINEERING_HANDOFF.md', 'docs/LONG_TERM_STORAGE_PLAN.md', 'docs/LUNA_START_HERE.md',
  'docs/NEON_SETUP.md', 'docs/RESEARCH_CAPACITY.md', 'docs/STORAGE_EXPORT_V2.md',
  'docs/STRUCTURAL_VALIDATION.md'
];
const preserved = [
  'hosted/worker.js', 'hosted/research-catalog.js', 'hosted/postgres-adapter.js',
  'hosted/storage-export-v2-contract.js', 'scripts/export-hosted-storage-v2.mjs',
  'data/validation/neon-final-publication.json',
  'data/validation/neon-production-storage-migration.json',
  'data/validation/neon-production-forward-migrations.json',
  'data/engineering/provider-capacity-20261003-7e91/capacity-summary.json',
  'docs/PROVIDER_CAPACITY.md', 'docs/WORKER_COORDINATION.md', 'docs/PARALLEL_WORK_PROTOCOL.md',
  'data/research-geography-gate.json'
];
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const read = name => fs.readFileSync(name, 'utf8');
const checks = [];
const check = (name, operation) => { operation(); checks.push({name, outcome: 'passed'}); };
check('All relative Markdown destinations in edited documents exist', () => {
  for (const document of documents) {
    for (const match of read(document).matchAll(/\[[^\]]*\]\(([^\s)]+)\)/g)) {
      const destination = match[1].split('#')[0];
      if (!destination || /^[a-z]+:/i.test(destination)) continue;
      assert.ok(fs.existsSync(path.resolve(path.dirname(document), destination)), `${document}: ${destination}`);
    }
  }
});
check('Production cutover receipt verifies PostgreSQL/R2 and v2 factual export', () => {
  const receipt = JSON.parse(read('data/validation/neon-final-publication.json'));
  assert.equal(receipt.publication.backend, 'postgres-plus-r2');
  assert.equal(receipt.publication.status, 'succeeded');
  assert.equal(receipt.capabilities.storageExport, 2);
  assert.equal(receipt.capabilities.datedFootprints, 0);
  assert.equal(receipt.neon.factual_table_count, 23);
});
check('Capacity implementation distinguishes PostgreSQL measurement and original collection counts', () => {
  const capacity = read('hosted/research-catalog.js');
  assert.ok(capacity.includes("measurement='postgres-pg-database-size'"));
  assert.ok(read('hosted/postgres-adapter.js').includes('SELECT pg_database_size(current_database()) AS bytes'));
  const tableDeclaration = capacity.match(/const countedTables=\{([^}]+)\}/)[1];
  assert.equal((tableDeclaration.match(/:'atlas_/g) || []).length, 14);
  assert.ok(capacity.includes("'postgres-plus-r2':'single-d1-plus-r2'"));
});
check('Documented routes and exporter maintenance requirement exist in current source', () => {
  const worker = read('hosted/worker.js');
  for (const route of ['/api/storage/capacity', '/api/storage/v2/export-marker', '/api/storage/v2/catalog']) {
    assert.ok(worker.includes(route), route);
  }
  assert.ok(worker.includes('catalogPage(db,catalog[1]'));
  assert.ok(worker.includes('entityRelationshipsPage:entityMediaPage'));
  assert.ok(read('scripts/export-hosted-storage-v2.mjs').includes('read_only'));
});
check('No obsolete unprovisioned-PostgreSQL or current Site 17 transfer instructions remain in edited documents', () => {
  for (const document of documents) assert.doesNotMatch(read(document), /PostgreSQL is not yet provisioned|The deployed storage implementation is one D1|The current Site 17 transfer uses v1/);
});
const preservation = preserved.map(name => {
  const original = execFileSync('git', ['show', `${baseline}:${name}`], {maxBuffer: 32 * 1024 * 1024});
  const current = fs.readFileSync(name);
  assert.equal(hash(current), hash(original), `Preserved input changed: ${name}`);
  return {path: name, sha256: hash(original), unchanged: true};
});
const receipt = {issue: 56, baseline_commit: baseline, documents, checks, preservation,
  live_operations: false, deployment_required: false,
  limits: [
    'Documentation audit of retained receipts and current source, not a new live service measurement.',
    'No account-plan authorization, recovery certificate, geographic approval or new import permission.',
    'Hashes and route inspection do not establish new runtime or historical behavior.'
  ]};
fs.writeFileSync(`${directory}/audit.json`, JSON.stringify(receipt, null, 2) + '\n');
console.log(JSON.stringify({checks: 'passed', links: 'resolved', preserved_inputs: 'unchanged', limits: receipt.limits}));

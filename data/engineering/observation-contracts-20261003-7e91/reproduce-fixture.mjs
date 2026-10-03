// Read-only synthetic contract reproduction; no provider, import or geography work.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {resolveTypedObservations} from '../../../src/typed-observations.js';
const path = new URL('../../../test/fixtures/typed-observation-contract-v1.json', import.meta.url);
const bytes = fs.readFileSync(path);
const sha = value => createHash('sha256').update(value).digest('hex');
function run() {
  const fixture = JSON.parse(bytes);
  const snapshots = Object.keys(fixture.expected).map(Number).sort((a, b) => a - b).map(year => {
    const rows = resolveTypedObservations(fixture.observations, year, fixture);
    assert.deepEqual(rows.map(row => [row.field_id, row.value, row.status, row.evidence.id]), fixture.expected[year]);
    return {year, rows};
  });
  return JSON.stringify(snapshots);
}
const first = run(), second = run();
assert.equal(first, second);
assert.deepEqual(fs.readFileSync(path), bytes);
const args = process.argv.slice(2);
if (args.length && (args.length !== 2 || args[0] !== '--out')) throw Error('Use --out NEW_RECEIPT_PATH, or stdout');
const result = {version: 1, check: 'synthetic-contract-json-roundtrip', outcome: 'passed',
  fixture_kind: 'synthetic-only-not-historical-evidence', fixture_sha256: sha(bytes),
  run_one_sha256: sha(first), run_two_sha256: sha(second),
  years: JSON.parse(first).map(row => row.year), snapshots: JSON.parse(first),
  limits: ['Pure shared seam only; not actual hosted/static adapter parity',
    'No factual import, source truth, geographic approval, provider operation or certificate']};
const output = JSON.stringify(result, null, 2) + '\n';
if (args.length) fs.writeFileSync(args[1], output, {flag: 'wx'});
else process.stdout.write(output);

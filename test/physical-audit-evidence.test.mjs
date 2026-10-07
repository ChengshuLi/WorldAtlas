import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {validateEvidence, repositoryReader, sha256} from '../scripts/evidence-quality.mjs';

const manifestPath = 'coordination/engineering/physical-gap-audit-1005-20261005-local18/evidence-quality.json';

test('retained worldwide physical audit restores every original and verifies all five complete vintages', () => {
  const root = JSON.parse(fs.readFileSync(manifestPath));
  const stage = root.mandatory_input_stage;
  const childBytes = fs.readFileSync(stage.evidence_manifest);
  assert.equal(sha256(childBytes), stage.evidence_sha256);
  const child = JSON.parse(childBytes);
  const envelopeBytes = fs.readFileSync(stage.envelope_manifest);
  assert.equal(sha256(envelopeBytes), stage.envelope_sha256);
  const envelope = JSON.parse(envelopeBytes), reader = repositoryReader(process.cwd());
  assert.match(envelope.executed_code_commit, /^[a-f0-9]{40}$/);
  assert.ok(Array.isArray(envelope.code_inputs) && envelope.code_inputs.length);
  const codePaths = envelope.code_inputs.map(row => row.path);
  assert.equal(new Set(codePaths).size, codePaths.length, 'Raw archived code identities must be unique');
  for (const row of envelope.code_inputs) {
    assert.ok(row.path.startsWith('scripts/'), 'Execution-code binding must name project code');
    assert.deepEqual(child.outputs.find(output => output.path === row.path), row,
      'Retained code descriptor must agree with the authenticated execution envelope');
  }
  // This is historical verification, not execution of current candidate code.
  // Keep original packet bytes on the candidate reader; only explicitly bound
  // execution inputs come from the envelope's immutable execution vintage.
  const retainedReader = (commit = envelope.executed_code_commit) => (name, vintage) =>
    reader(name, vintage === 'candidate' && codePaths.includes(name) ? commit : vintage);
  assert.throws(() => validateEvidence(child, {readFile: retainedReader('0'.repeat(40))}),
    /ls-tree/, 'An unavailable historical code commit cannot become successful evidence');
  assert.throws(() => validateEvidence(child, {readFile: (name, vintage) => {
    const raw = retainedReader()(name, vintage);
    return name === 'scripts/evidence/immutable.py' ? Buffer.concat([raw, Buffer.from('changed')]) : raw;
  }}), /Input bytes mismatch/, 'Changed execution bytes must still fail');
  const result = validateEvidence(child, {readFile: retainedReader(),
    expectedIssue: 1005, expectedSubjects: root.subject_ids, expectedPins: root.baseline.pins});
  assert.equal(result.checked.length, child.baseline.files.length + child.sources.flatMap(s => s.files ?? []).length + child.outputs.length);
  const run = spawnSync(process.env.PYTHON || 'python3', ['-B', 'scripts/validate-physical-audit-evidence.py', '--manifest', manifestPath],
    {encoding: 'utf8', timeout: 180000, maxBuffer: 4 * 1024 * 1024});
  assert.equal(run.status, 0, `${run.stdout}\n${run.stderr}`);
  const verified = JSON.parse(run.stdout);
  assert.equal(verified.status, 'complete-typed-source-code-product-validation');
  assert.equal(verified.original_source.files_restored, 45);
  assert.equal(verified.vintages_checked, 5);
  assert.equal(verified.tiles_checked, 2160);
  assert.equal(verified.candidates, 96963);
  assert.equal(verified.residues, 343);
  assert.equal(verified.measurement_unknowns, 5);
  assert.equal(verified.final_files_byte_identical, true);
  const controls = spawnSync(process.env.PYTHON || 'python3', ['-B', '-c', `
import copy, importlib.util, json, sys
sys.path.insert(0, "scripts")
spec = importlib.util.spec_from_file_location('physical_validator', 'scripts/validate-physical-audit-evidence.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
root = json.load(open('${manifestPath}'))
child = json.load(open(root['mandatory_input_stage']['evidence_manifest']))
envelope = json.load(open(root['mandatory_input_stage']['envelope_manifest']))
reports = [json.load(open(row['path'])) for row in root['audit_reports']]
for kind in ('duplicate-code', 'missing-code', 'changed-code-pin', 'changed-child-code'):
    altered, changed = copy.deepcopy(envelope), copy.deepcopy(child)
    if kind == 'duplicate-code': altered['code_inputs'].append(copy.deepcopy(altered['code_inputs'][0]))
    elif kind == 'missing-code': altered['code_inputs'].pop()
    elif kind == 'changed-code-pin': altered['code_inputs'][0]['sha256'] = '0' * 64
    else:
        next(row for row in changed['outputs'] if row['path'] == altered['code_inputs'][0]['path'])['sha256'] = '0' * 64
    try: module.upstream_closure(changed, altered, reports)
    except ValueError as error:
        if 'execution' not in str(error): raise
    else: raise AssertionError('Actual archived execution admission accepted ' + kind)
print('actual archived execution rejection controls passed')
`], {encoding: 'utf8', timeout: 60000, maxBuffer: 1024 * 1024});
  assert.equal(controls.status, 0, controls.stdout + controls.stderr);
  assert.match(controls.stdout, /actual archived execution rejection controls passed/);

});

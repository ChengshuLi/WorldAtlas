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
  const result = validateEvidence(child, {readFile: repositoryReader(process.cwd()),
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
});

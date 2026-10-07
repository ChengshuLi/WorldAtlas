import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const packet = 'data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum';
const original = 'data/regional-review/regional-review-029dcbc646de003d';
const runOne = `${packet}/runs/2026-10-07/run-1`;
const date = new Date().toISOString().slice(0, 10);
const controlRoot = path.join(root, packet, 'controls', date);
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const readJSON = filename => JSON.parse(fs.readFileSync(filename, 'utf8'));
const writeJSON = (filename, value) => fs.writeFileSync(filename, `${JSON.stringify(value, null, 2)}\n`, {flag: 'wx'});
fs.mkdirSync(path.dirname(controlRoot), {recursive: true});
fs.mkdirSync(controlRoot, {recursive: false});

const originalCrosswalk = readJSON(path.join(root, runOne, 'scope-reproduction.json'));
const originalAssessments = readJSON(path.join(root, runOne, 'row-assessments.json'));
const validator = path.join(root, packet, 'verify-crosswalk.mjs');
const oldValidator = fs.readFileSync(path.join(root, original, 'validate-evidence.mjs'), 'utf8');
const replacements = [
  ["const reproduced = readJSON('scope-reproduction.json');", "const reproduced = JSON.parse(fs.readFileSync(process.env.WA_CROSSWALK_INPUT, 'utf8'));"] ,
  ["const rows = readJSON('row-assessments.json');", "const rows = JSON.parse(fs.readFileSync(process.env.WA_ASSESSMENTS_INPUT, 'utf8'));"] ,
  ["sha(fs.readFileSync(path.join(packet, 'scope-reproduction.json')))" , "sha(fs.readFileSync(process.env.WA_CROSSWALK_INPUT))"]
];
let legacyAdapter = oldValidator;
for (const [from, to] of replacements) {
  if (!legacyAdapter.includes(from)) throw new Error(`Original validator adapter anchor missing: ${from}`);
  legacyAdapter = legacyAdapter.replace(from, to);
}
const legacyPath = path.join(controlRoot, 'legacy-validator-input-adapter.mjs');
fs.writeFileSync(legacyPath, legacyAdapter, {flag: 'wx'});

const cases = [
  {id: 'missing-crosswalk-member', mutateCrosswalk(value) { value.rows.splice(81, 1); }},
  {id: 'duplicate-crosswalk-member', mutateCrosswalk(value) { value.rows[222] = structuredClone(value.rows[0]); }},
  {id: 'foreign-crosswalk-replacement', mutateCrosswalk(value) { value.rows[0].id = 'gb:AGO:ADM2:foreign-not-in-frozen-scope'; }},
  {id: 'extra-crosswalk-member', mutateCrosswalk(value) { value.rows.push({...value.rows[0], id: 'gb:AGO:ADM2:extra-not-in-frozen-scope'}); }},
  {id: 'crosswalk-parent-mismatch', mutateCrosswalk(value) { value.rows[0].assigned_parent_id = 'framework:province:foreign-parent:not-a-real-id'; }},
  {id: 'assessment-native-source-mismatch', mutateAssessment(value) { value.rows[0].source_native_id = 'foreign-native-id'; }},
  {id: 'assessment-parent-mismatch', mutateAssessment(value) { value.rows[0].assigned_parent_id = 'framework:province:foreign-parent:not-a-real-id'; }}
];
const results = [];
for (const test of cases) {
  const directory = path.join(controlRoot, test.id);
  fs.mkdirSync(directory);
  const crosswalk = structuredClone(originalCrosswalk);
  const assessments = structuredClone(originalAssessments);
  test.mutateCrosswalk?.(crosswalk);
  const crosswalkBytes = Buffer.from(`${JSON.stringify(crosswalk, null, 2)}\n`);
  assessments.scope_reproduction_sha256 = sha(crosswalkBytes);
  test.mutateAssessment?.(assessments);
  const crosswalkInput = path.join(directory, 'scope-reproduction.json');
  const assessmentInput = path.join(directory, 'row-assessments.json');
  fs.writeFileSync(crosswalkInput, crosswalkBytes, {flag: 'wx'});
  writeJSON(assessmentInput, assessments);
  const newOutput = path.join(directory, 'new-validator-success-must-not-exist.json');
  let newRejected = false;
  let newError = '';
  try {
    execFileSync(process.execPath, [validator, '--crosswalk', crosswalkInput, '--assessments', assessmentInput, '--output', newOutput],
      {cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe']});
  } catch (error) {
    newRejected = true;
    newError = String(error.stderr ?? error.message).trim().slice(-1200);
  }
  if (!newRejected || fs.existsSync(newOutput)) throw new Error(`Corrected validator accepted or emitted a receipt for ${test.id}`);
  const row = {
    id: test.id,
    crosswalk_input_sha256: sha(fs.readFileSync(crosswalkInput)),
    crosswalk_input_bytes: fs.statSync(crosswalkInput).size,
    assessment_input_sha256: sha(fs.readFileSync(assessmentInput)),
    assessment_input_bytes: fs.statSync(assessmentInput).size,
    assessment_hash_recomputed_to_actual_crosswalk: assessments.scope_reproduction_sha256 === sha(fs.readFileSync(crosswalkInput)),
    corrected_validator: {outcome: 'rejected-before-success-output', diagnostic: newError},
    legacy_validator: {outcome: 'not-run'}
  };
  if (test.id === 'missing-crosswalk-member') {
    const legacyOutput = path.join(directory, 'legacy-validator-result.json');
    const result = execFileSync(process.execPath, [legacyPath, '--output', legacyOutput], {
      cwd: root,
      encoding: 'utf8',
      env: {...process.env, WA_CROSSWALK_INPUT: crosswalkInput, WA_ASSESSMENTS_INPUT: assessmentInput},
      stdio: ['ignore', 'pipe', 'pipe']
    });
    const parsed = readJSON(legacyOutput);
    if (parsed.scope.count !== 223 || !fs.existsSync(legacyOutput)) throw new Error('Legacy positive acceptance reproduction did not produce its success receipt');
    row.legacy_validator = {
      outcome: 'accepted-invalid-222-row-crosswalk',
      output_path: path.relative(root, legacyOutput),
      output_sha256: sha(fs.readFileSync(legacyOutput)),
      output_scope_count: parsed.scope.count,
      output_crosswalk_rows: crosswalk.rows.length,
      output_unique_crosswalk_ids: new Set(crosswalk.rows.map(item => item.id)).size,
      adapter_sha256: sha(Buffer.from(legacyAdapter)),
      adapter_changes: 'Only crosswalk/assessment input locators and the matching whole-crosswalk hash read were redirected to the exact mutated input files; original validation predicates are otherwise unchanged.',
      stdout_tail: result.trim().slice(-600)
    };
  }
  results.push(row);
}
const output = {
  version: 1,
  issue: 1279,
  reproduced_at_utc: new Date().toISOString(),
  original_crosswalk_sha256: sha(fs.readFileSync(path.join(root, runOne, 'scope-reproduction.json'))),
  original_assessments_sha256: sha(fs.readFileSync(path.join(root, runOne, 'row-assessments.json'))),
  controls: results,
  interpretation: 'The old validator accepted the specific 222-row crosswalk after its actual input hash was recomputed. The superseding validator rejects the missing member and each directed identity, parent, duplicate, extra-row and assessment-correlation mutation before writing a success receipt.'
};
writeJSON(path.join(controlRoot, 'control-results.json'), output);
console.log(JSON.stringify({issue: output.issue, controls: results.map(row => ({id: row.id, new: row.corrected_validator.outcome, legacy: row.legacy_validator.outcome}))}, null, 2));

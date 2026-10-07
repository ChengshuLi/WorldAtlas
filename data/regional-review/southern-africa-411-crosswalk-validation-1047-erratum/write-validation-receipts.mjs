import {createHash} from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const packet = 'data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum';
const runs = [1, 2].map(n => `${packet}/runs/2026-10-07/run-${n}`);
const controls = `${packet}/controls/2026-10-07/control-results.json`;
const output = `${packet}/validation`;
const sha = value => createHash('sha256').update(value).digest('hex');
const bytes = file => fs.readFileSync(path.join(root, file));
const readJSON = file => JSON.parse(bytes(file));
fs.mkdirSync(path.join(root, output), {recursive: false});
const runData = runs.map(directory => {
  const crosswalk = bytes(`${directory}/scope-reproduction.json`);
  const assessments = bytes(`${directory}/row-assessments.json`);
  const validation = readJSON(`${directory}/validation.json`);
  if (validation.crosswalk.sha256 !== sha(crosswalk) || validation.assessments.sha256 !== sha(assessments) ||
      validation.crosswalk.rows !== 223 || validation.assessments.rows !== 223) {
    throw new Error(`Positive validation receipt does not bind 223 actual rows: ${directory}`);
  }
  return {directory, crosswalk_sha256: sha(crosswalk), assessments_sha256: sha(assessments),
    validation_sha256: sha(bytes(`${directory}/validation.json`))};
});
if (runData[0].crosswalk_sha256 !== runData[1].crosswalk_sha256 ||
    runData[0].assessments_sha256 !== runData[1].assessments_sha256) {
  throw new Error('Two complete crosswalk/assessment runs differ');
}
const controlData = readJSON(controls);
if (controlData.controls.length !== 7 ||
    controlData.controls.some(item => item.corrected_validator.outcome !== 'rejected-before-success-output') ||
    controlData.controls[0].legacy_validator.outcome !== 'accepted-invalid-222-row-crosswalk') {
  throw new Error('Directed control outcomes are incomplete');
}
const methodId = 'southern-africa-frozen-crosswalk-integrity';
const pairDigest = data => sha(Buffer.from(JSON.stringify({crosswalk_sha256: data.crosswalk_sha256,
  assessments_sha256: data.assessments_sha256})));
const records = [
  ['positive-control', {method_id: methodId, kind: 'positive-control', outcome: 'passed', runs: runData}],
  ['negative-control', {method_id: methodId, kind: 'negative-control', outcome: 'passed',
    control_results_path: controls, control_results_sha256: sha(bytes(controls)),
    expected_rejections: controlData.controls.map(item => item.id), legacy_acceptance_reproduced: true}],
  ['reproducibility', {method_id: methodId, kind: 'reproducibility', outcome: 'passed',
    run_one_sha256: pairDigest(runData[0]), run_two_sha256: pairDigest(runData[1]), runs: runData}]
];
for (const [name, result] of records) {
  fs.writeFileSync(path.join(root, output, `${name}.json`), `${JSON.stringify(result, null, 2)}\n`, {flag: 'wx'});
}
console.log(JSON.stringify({method_id: methodId, run_one_sha256: pairDigest(runData[0]),
  run_two_sha256: pairDigest(runData[1]), controls: controlData.controls.length}, null, 2));

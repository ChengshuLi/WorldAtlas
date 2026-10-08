import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const packet = 'data/regional-review/southern-africa-1286-integrity-erratum';
const original = 'data/regional-review/regional-review-029dcbc646de003d';
const prior = 'data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum/controls/2026-10-07';
const runTag = `${Date.now()}-${process.pid}`;
const controlRoot = path.join(root, packet, 'controls', `2026-10-08-${runTag}`);
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const read = file => fs.readFileSync(file, 'utf8');
const writeJson = (file, value) => fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, {flag: 'wx'});
const sourceCrosswalk = JSON.parse(read(path.join(root, original, 'scope-reproduction.json')));
const sourceAssessments = JSON.parse(read(path.join(root, original, 'row-assessments.json')));
const validator = path.join(root, packet, 'verify-integrity.mjs');
const validatorSha = sha(fs.readFileSync(validator));
const node = process.execPath;
const validationOutput = name => path.join(root, packet, 'vintages', `control-${runTag}-${name}`, 'validation.json');
const priorIds = [
  'missing-crosswalk-member', 'duplicate-crosswalk-member', 'foreign-crosswalk-replacement',
  'extra-crosswalk-member', 'crosswalk-parent-mismatch', 'assessment-native-source-mismatch',
  'assessment-parent-mismatch'
];

fs.mkdirSync(controlRoot, {recursive: true});
const runActual = (crosswalk, assessments, output) => execFileSync(node, [validator,
  '--code-sha256', validatorSha,
  '--crosswalk', crosswalk,
  '--assessments', assessments,
  '--output', output], {cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe']});
const captured = (id, inputCrosswalk, inputAssessments, output) => {
  const result = {id, crosswalk_sha256: sha(fs.readFileSync(inputCrosswalk)),
    assessments_sha256: sha(fs.readFileSync(inputAssessments)), output_path: path.relative(root, output)};
  try {
    const stdout = runActual(inputCrosswalk, inputAssessments, output);
    result.outcome = 'accepted';
    result.stdout_sha256 = sha(Buffer.from(stdout));
  } catch (error) {
    result.outcome = 'rejected-before-success-receipt';
    result.stderr_sha256 = sha(Buffer.from(error.stderr ?? ''));
    result.diagnostic = String(error.stderr ?? error.message).trim().slice(-500);
  }
  result.success_receipt_exists = fs.existsSync(output) && fs.statSync(output).isFile();
  return result;
};

const results = [];
for (const id of priorIds) {
  const directory = path.join(root, prior, id);
  const outDir = path.join(controlRoot, 'retained-' + id);
  fs.mkdirSync(outDir);
  const output = validationOutput('retained-' + id);
  results.push(captured(id,
    path.join(directory, 'scope-reproduction.json'),
    path.join(directory, 'row-assessments.json'), output));
}

const refresh = (crosswalk, assessments) => {
  const counts = {};
  const parents = {};
  for (const row of crosswalk.rows) {
    counts[row.iso] = (counts[row.iso] ?? 0) + 1;
    parents[row.assigned_parent_id] = (parents[row.assigned_parent_id] ?? 0) + 1;
  }
  crosswalk.issue_scope_count = crosswalk.rows.length;
  crosswalk.matched_scope_count = crosswalk.rows.length;
  crosswalk.unique_scope_ids = new Set(crosswalk.rows.map(row => row.id)).size;
  crosswalk.parent_scope_counts = parents;
  for (const [iso, count] of Object.entries(counts)) {
    if (crosswalk.country_summary[iso]) crosswalk.country_summary[iso].owned_scope_count = count;
  }
  assessments.counts = Object.fromEntries(['justified', 'correction-needed', 'insufficient-evidence']
    .map(kind => [kind, assessments.rows.filter(row => row.classification === kind).length]));
  return {crosswalk, assessments};
};
const define = (id, mutate) => {
  const directory = path.join(controlRoot, id);
  fs.mkdirSync(directory);
  const crosswalk = structuredClone(sourceCrosswalk);
  const assessments = structuredClone(sourceAssessments);
  mutate(crosswalk, assessments);
  const inputs = refresh(crosswalk, assessments);
  const crosswalkBytes = Buffer.from(`${JSON.stringify(inputs.crosswalk, null, 2)}\n`);
  inputs.assessments.scope_reproduction_sha256 = sha(crosswalkBytes);
  const crosswalkPath = path.join(directory, 'scope-reproduction.json');
  const assessmentPath = path.join(directory, 'row-assessments.json');
  writeJson(crosswalkPath, inputs.crosswalk);
  writeJson(assessmentPath, inputs.assessments);
  const result = captured(id, crosswalkPath, assessmentPath, validationOutput(id));
  result.coherent_crosswalk_counts = inputs.crosswalk.rows.length === inputs.crosswalk.matched_scope_count &&
    inputs.crosswalk.rows.length === inputs.crosswalk.unique_scope_ids;
  result.coherent_assessment_hash = inputs.assessments.scope_reproduction_sha256 === sha(fs.readFileSync(crosswalkPath));
  results.push(result);
};

define('coherent-false-source-hash', (crosswalk, assessments) => {
  crosswalk.country_summary.AGO.source.sha256 = '0'.repeat(64);
  for (const row of assessments.rows.filter(row => row.country === 'AGO')) row.source_artifact_sha256 = '0'.repeat(64);
});
define('moved-scientific-disposition', (crosswalk, assessments) => {
  const quela = assessments.rows.find(row => row.id === 'gb:AGO:ADM2:16411231B11923183554394');
  const maputo = assessments.rows.find(row => row.id === 'gb:MOZ:ADM2:85939544B59479814848654');
  quela.classification = 'correction-needed';
  maputo.classification = 'insufficient-evidence';
});
define('wrong-individual-source-descriptor', (crosswalk, assessments) => {
  assessments.rows.find(row => row.id === 'gb:AGO:ADM2:16411231B11923183554394').source_artifact_sha256 = '0'.repeat(64);
});
define('wrong-individual-disposition', (crosswalk, assessments) => {
  assessments.rows.find(row => row.id === 'gb:AGO:ADM2:16411231B11923183554394').classification = 'correction-needed';
});
define('coherent-missing-subject', (crosswalk, assessments) => {
  const id = 'gb:AGO:ADM2:16411231B99374961712721';
  crosswalk.rows = crosswalk.rows.filter(row => row.id !== id);
  assessments.rows = assessments.rows.filter(row => row.id !== id);
});
define('coherent-extra-subject', (crosswalk, assessments) => {
  const row = structuredClone(crosswalk.rows[0]);
  row.id = 'gb:AGO:ADM2:invented-extra-subject';
  crosswalk.rows.push(row);
  const assessment = structuredClone(assessments.rows[0]);
  assessment.id = row.id;
  assessments.rows.push(assessment);
});
define('coherent-duplicate-subject', (crosswalk, assessments) => {
  crosswalk.rows.push(structuredClone(crosswalk.rows[0]));
  assessments.rows.push(structuredClone(assessments.rows[0]));
});

const legacyValidator = path.join(root, 'data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum/verify-crosswalk.mjs');
const legacy = [];
for (const id of ['coherent-false-source-hash', 'moved-scientific-disposition']) {
  const directory = path.join(controlRoot, id);
  const output = path.join(directory, 'legacy-validator-success.json');
  const crosswalk = path.join(directory, 'scope-reproduction.json');
  const assessments = path.join(directory, 'row-assessments.json');
  const record = {id, validator_sha256: sha(fs.readFileSync(legacyValidator)),
    crosswalk_sha256: sha(fs.readFileSync(crosswalk)), assessments_sha256: sha(fs.readFileSync(assessments))};
  try {
    const stdout = execFileSync(node, [legacyValidator, '--crosswalk', crosswalk, '--assessments', assessments,
      '--output', output], {cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe']});
    record.outcome = 'accepted-invalid-pair';
    record.stdout_sha256 = sha(Buffer.from(stdout));
    record.output_sha256 = sha(fs.readFileSync(output));
    record.output_bytes = fs.statSync(output).size;
  } catch (error) {
    record.outcome = 'rejected';
    record.diagnostic = String(error.stderr ?? error.message).trim().slice(-500);
  }
  legacy.push(record);
}
if (legacy.some(row => row.outcome !== 'accepted-invalid-pair')) {
  throw new Error('Expected original validator false-acceptance controls did not reproduce');
}

const safeRoot = path.join(root, packet, 'vintages');
const validCrosswalk = path.join(root, original, 'scope-reproduction.json');
const validAssessments = path.join(root, original, 'row-assessments.json');
const safe = [];
const safeAttempt = (id, output, preservePath = null) => {
  const existedBefore = fs.existsSync(output);
  let before = null;
  if (preservePath) before = fs.readFileSync(preservePath);
  const record = {id, output_path: path.relative(root, output)};
  try {
    runActual(validCrosswalk, validAssessments, output);
    record.outcome = 'accepted';
  } catch (error) {
    record.outcome = 'rejected-before-success-receipt';
    record.diagnostic = String(error.stderr ?? error.message).trim().slice(-400);
  }
  record.receipt_exists = !existedBefore && fs.existsSync(output) && fs.statSync(output).isFile();
  record.preexisting_destination = existedBefore;
  if (preservePath) record.preserved_sentinel = before.equals(fs.readFileSync(preservePath));
  safe.push(record);
};
const existingFileParent = path.join(safeRoot, `safe-${runTag}-existing-file`);
fs.mkdirSync(existingFileParent);
const existingFile = path.join(existingFileParent, 'validation.json');
fs.writeFileSync(existingFile, 'immutable sentinel\n', {flag: 'wx'});
safeAttempt('existing-file', existingFile, existingFile);
const existingDirectory = path.join(safeRoot, `safe-${runTag}-existing-directory`);
fs.mkdirSync(existingDirectory);
const existingOutputDirectory = path.join(existingDirectory, 'validation.json');
fs.mkdirSync(existingOutputDirectory);
const directorySentinel = path.join(existingOutputDirectory, 'sentinel');
fs.writeFileSync(directorySentinel, 'directory sentinel\n', {flag: 'wx'});
safeAttempt('existing-directory', existingOutputDirectory, directorySentinel);
const symlinkTarget = path.join(root, original);
const symlinkPath = path.join(safeRoot, `safe-${runTag}-symlink-parent`);
fs.symlinkSync(symlinkTarget, symlinkPath, 'dir');
safeAttempt('symlink-parent', path.join(symlinkPath, 'validation.json'));
safeAttempt('path-traversal', path.join(root, packet, 'vintages/../controls/receipt.json'));
const partialDirectory = path.join(safeRoot, `safe-${runTag}-partial-success`);
fs.mkdirSync(partialDirectory);
const partialSentinel = path.join(partialDirectory, '.publication-incomplete');
fs.writeFileSync(partialSentinel, 'partial sentinel\n', {flag: 'wx'});
safeAttempt('partial-output-directory', path.join(partialDirectory, 'validation.json'), partialSentinel);
if (safe.some(row => row.outcome !== 'rejected-before-success-receipt' || row.receipt_exists || row.preserved_sentinel === false)) {
  throw new Error('Unsafe destination control accepted, emitted a receipt, or changed a sentinel');
}

for (const result of results) {
  if (result.outcome !== 'rejected-before-success-receipt' || result.success_receipt_exists) {
    throw new Error(`Replacement entry point accepted or emitted success for ${result.id}`);
  }
}
const output = {
  version: 1,
  issue: 1459,
  method: 'verify-integrity.mjs',
  validator_sha256: validatorSha,
  reproduced_at_utc: new Date().toISOString(),
  prior_directed_control_count: priorIds.length,
  coherent_adversarial_control_count: 7,
  total_control_count: results.length,
  controls: results,
  original_validator_false_acceptances: legacy,
  safe_destination_control_count: safe.length,
  safe_destination_controls: safe,
  interpretation: 'The replacement validator rejected all seven retained directed mutations and seven newly generated false-hash, moved-disposition, incorrect-descriptor, incorrect-disposition, and coherently refreshed missing/extra/duplicate subject controls before creating any success receipt. The exact prior validator accepted both independently reproduced false source-hash and moved-disposition pairs. Existing outputs, symlink/traversal paths and interrupted-output sentinels were preserved.'
};
writeJson(path.join(controlRoot, 'control-results.json'), output);
console.log(JSON.stringify({issue: output.issue, controls: results.length,
  rejected: results.filter(row => row.outcome === 'rejected-before-success-receipt').length,
  validator_sha256: validatorSha}, null, 2));

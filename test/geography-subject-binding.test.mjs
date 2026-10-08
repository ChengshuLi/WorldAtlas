import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {repositoryReader, sha256, subjectsHash, validateEvidence} from '../scripts/evidence-quality.mjs';
import {validatePremergeManifest} from '../scripts/premerge-evidence.mjs';

const base = 'de506f51100568e150e51f2926a5259b71e55272';
const contactPath = 'research/geography/gap-source-namibia-angola-20261006/inputs/source-contact-features.geojson';
const contactHash = '472ee9003155eb62c9e9aa7bfdff0e28dfab13a8c1cc18b2a30ca6b705cc2f14';
const propertyTemplate = {version: 1, path: contactPath, id_template: 'gb:{shapeGroup}:{shapeType}:{shapeID}',
  properties: ['shapeGroup', 'shapeType', 'shapeID']};
const identities = ['gb:AGO:ADM2:16411231B14510444140190', 'gb:AGO:ADM2:16411231B28551746118834',
  'gb:AGO:ADM2:16411231B36562728226085', 'gb:NAM:ADM2:8085530B15355770078360',
  'gb:NAM:ADM2:8085530B25496891828693', 'gb:NAM:ADM2:8085530B32015186497374',
  'gb:NAM:ADM2:8085530B43563455443088', 'gb:NAM:ADM2:8085530B54610932550654',
  'gb:NAM:ADM2:8085530B8620298556926', 'gb:NAM:ADM2:8085530B94702234009846'];
const direct = (subjects, binding) => Object.fromEntries(subjects.map(subject => [subject, binding]));
const descriptor = (path, raw) => ({path, bytes: raw.length, sha256: sha256(raw), hash_kind: 'file-bytes'});
function geographyManifest(raw, subjects, binding = propertyTemplate) {
  return {version: 1, issue: 1397, lane: 'geography', worker_id: 'source-binding-test',
    subject_ids: subjects, subject_ids_sha256: subjectsHash(subjects),
    baseline: {commit: base, files: [descriptor(binding.path, raw)],
      pins: {[binding.path]: sha256(raw)}, pin_files: {[binding.path]: binding.path},
      subject_files: direct(subjects, binding)},
    sources: [], outputs: [], methods: [], metrics: [], summaries: [], conclusions: [],
    stages: {research: 'partial', implementation: 'not-proposed', geographic_approval: 'unapproved'}, commands: []};
}

test('canonical contact IDs bind to the exact pinned source rows by declared properties', () => {
  const bytes = execFileSync('git', ['show', `${base}:${contactPath}`]);
  assert.equal(sha256(bytes), contactHash);
  const manifest = geographyManifest(bytes, identities);
  const result = validateEvidence(manifest, {readFile: repositoryReader(process.cwd()), expectedIssue: 1397,
    expectedLane: 'geography', expectedSubjects: identities, expectedPins: {[contactPath]: contactHash}});
  assert.equal(result.status, 'bytes-verified');
  const source = JSON.parse(bytes);
  assert.equal(source.features.length, identities.length);
  assert.deepEqual(source.features.map(feature => `gb:${feature.properties.shapeGroup}:${feature.properties.shapeType}:${feature.properties.shapeID}`).sort(),
    [...identities].sort());
});

function synthetic(features, subjects = ['gb:AGO:ADM2:001']) {
  const raw = Buffer.from(JSON.stringify({type: 'FeatureCollection', features}));
  const binding = {version: 1, path: 'contacts.json', id_template: 'gb:{shapeGroup}:{shapeType}:{shapeID}',
    properties: ['shapeGroup', 'shapeType', 'shapeID']};
  const manifest = geographyManifest(raw, subjects, binding);
  const readFile = (_path, vintage) => { assert.equal(vintage, base); return raw; };
  return {manifest, readFile};
}
const contactFeature = (properties = {shapeGroup: 'AGO', shapeType: 'ADM2', shapeID: '001'}) => ({type: 'Feature', properties, geometry: null});

test('composed bindings reject missing, non-string, duplicate and omitted or fabricated identities', () => {
  const cases = [
    synthetic([contactFeature({shapeGroup: 'AGO', shapeType: 'ADM2'})]),
    synthetic([contactFeature({shapeGroup: 'AGO', shapeType: 'ADM2', shapeID: 1})]),
    synthetic([contactFeature({shapeGroup: ' AGO', shapeType: 'ADM2', shapeID: '001'})]),
    synthetic([contactFeature(), contactFeature()]),
    synthetic([contactFeature()], ['gb:AGO:ADM2:002']),
  ];
  for (const fixture of cases) assert.throws(() => validateEvidence(fixture.manifest, {readFile: fixture.readFile}));
});

test('composed bindings reject unsafe templates, inconsistent per-file descriptors and unpinned paths', () => {
  const f = synthetic([contactFeature()], [identities[0]]);
  f.manifest.baseline.subject_files[identities[0]] = {...propertyTemplate, path: 'wrong.json'};
  assert.throws(() => validateEvidence(f.manifest, {readFile: f.readFile}), /unpinned/);
  const g = synthetic([contactFeature()], [identities[0]]);
  g.manifest.baseline.subject_files[identities[0]] = {...g.manifest.baseline.subject_files[identities[0]], id_template: 'gb:{shapeGroup}:{shapeType}:{missing}'};
  assert.throws(() => validateEvidence(g.manifest, {readFile: g.readFile}));
  const version = synthetic([contactFeature()], [identities[0]]);
  version.manifest.baseline.subject_files[identities[0]] = {...version.manifest.baseline.subject_files[identities[0]], version: 2};
  assert.throws(() => validateEvidence(version.manifest, {readFile: version.readFile}));
  const h = synthetic([contactFeature(), contactFeature({shapeGroup: 'AGO', shapeType: 'ADM2', shapeID: '002'})],
    ['gb:AGO:ADM2:001', 'gb:AGO:ADM2:002']);
  h.manifest.baseline.subject_files['gb:AGO:ADM2:002'] = 'contacts.json';
  assert.throws(() => validateEvidence(h.manifest, {readFile: h.readFile}), /consistent identity binding/);
});

test('trusted premerge manifest path accepts composed identities only against the declared immutable bytes', () => {
  const bytes = execFileSync('git', ['show', `${base}:${contactPath}`]);
  const outputPath = 'research/geography/namibia-angola-jog1501-20261007/README.md';
  const manifestPath = 'research/geography/namibia-angola-jog1501-20261007/evidence-quality.json';
  const output = Buffer.from('scope-bound output\n');
  const files = [{filename: outputPath, status: 'added'}, {filename: manifestPath, status: 'added'}];
  const pin = {[contactPath]: contactHash};
  const spec = {mode: 'geography', evidence_quality: {version: 1, manifest_path: manifestPath,
    subject_ids: identities, pins: pin, review_kind: 'source'}};
  const manifest = geographyManifest(bytes, identities);
  manifest.worker_id = 'source-binding-test';
  manifest.outputs = [descriptor(outputPath, output)];
  manifest.change_receipts = files.map(file => ({path: file.filename, status: file.status}));
  const readFile = (name, vintage) => {
    if (name === contactPath) { assert.equal(vintage, base); return bytes; }
    if (name === outputPath) { assert.equal(vintage, 'candidate'); return output; }
    throw Error(`Unexpected evidence read ${vintage}:${name}`);
  };
  const context = {readFile, files, manifestPath, issue: {number: 1397}, spec,
    reservation: {worker_id: 'source-binding-test', owned_paths: ['research/geography/namibia-angola-jog1501-20261007/']},
    branch: 'geography/namibia-angola-jog-1501-20261007',
    pr: {base: {sha: base}, changed_files: files.length}};
  assert.equal(validatePremergeManifest(manifest, context).change_files_checked, 2);
  manifest.baseline.subject_files[identities[0]] = {...propertyTemplate, path: 'other.json'};
  assert.throws(() => validatePremergeManifest(manifest, context), /unpinned/);
});

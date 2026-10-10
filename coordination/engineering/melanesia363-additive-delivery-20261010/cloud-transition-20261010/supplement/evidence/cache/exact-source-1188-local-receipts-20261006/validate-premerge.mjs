import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {validatePremergeManifest} from '../../scripts/premerge-evidence.mjs';
const manifestPath = 'coordination/engineering/exact-source-predicates-1188-20261006/evidence-quality.json';
const manifest = JSON.parse(fs.readFileSync(manifestPath));
const files = manifest.change_receipts.map(row => ({filename: row.path, status: row.status}));
const spec = {mode: 'engineering', evidence_quality: {subject_ids: [], pins: {}, review_kind: 'release'}};
const result = validatePremergeManifest(manifest, {manifestPath, files, issue: {number: 1188}, spec,
  reservation: {worker_id: manifest.worker_id}, branch: 'engineering/exact-source-predicates-1188-20261006',
  pr: {base: {sha: manifest.baseline.commit}},
  readFile: (path, vintage) => vintage === 'candidate' ? fs.readFileSync(path) :
    execFileSync('git', ['show', (vintage === 'base' ? manifest.baseline.commit : vintage) + ':' + path])});
console.log(JSON.stringify(result));

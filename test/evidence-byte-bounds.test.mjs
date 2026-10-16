import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {gzipSync} from 'node:zlib';
import {finiteBytes, addBytes, evidenceBytePlan, decodeEvidenceGzip, immutableResponseBytes} from '../scripts/evidence-byte-bounds.mjs';
import {validateEvidence, repositoryReader, sha256, subjectsHash} from '../scripts/evidence-quality.mjs';

const size = 36065990, commit = 'a'.repeat(40);
const descriptor = (name, raw) => ({path: name, bytes: raw.length, sha256: sha256(raw), hash_kind: 'file-bytes'});
function manifest(raw, outputs = []) {
  return {version: 1, issue: 2069, lane: 'engineering', worker_id: 'byte-bound-test', subject_ids: [], subject_ids_sha256: subjectsHash([]),
    baseline: {commit, files: [descriptor('baseline.bin', raw)], pins: {}}, sources: [], outputs,
    methods: [{id: 'bytes', kind: 'code', description: 'Exact byte controls', software: 'Node 24', units: 'bytes'}],
    metrics: [], summaries: [], conclusions: [], stages: {research: 'complete', implementation: 'proposed', geographic_approval: 'not-requested'}, commands: ['node --test test/evidence-byte-bounds.test.mjs']};
}
test('finite exact plans reject unsafe sizes, arithmetic overflow and duplicate identities', () => {
  for (const value of [-1, 0.5, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1]) assert.throws(() => finiteBytes(value), /finite/);
  assert.equal(finiteBytes(0), 0); assert.equal(addBytes(1, 2), 3);
  assert.throws(() => addBytes(Number.MAX_SAFE_INTEGER, 1), /finite/);
  assert.throws(() => immutableResponseBytes(Number.MAX_SAFE_INTEGER), /finite/);
  assert.throws(() => evidenceBytePlan([{path: 'one', bytes: 1}, {path: 'one', bytes: 1}]), /Duplicate/);
  assert.throws(() => evidenceBytePlan([{path: 'one', bytes: 1, uncompressed_bytes: 2}]), /uncompressed/);
});
test('actual Vietnam-sized files and a complete packet above the old aggregate cap retain exact hash checks', () => {
  const raw = Buffer.alloc(size, 91), baseline = Buffer.from('baseline');
  const outputs = Array.from({length: 8}, (_, i) => descriptor('source-' + i + '.bin', raw)), m = manifest(baseline, outputs);
  const plan = evidenceBytePlan([...m.baseline.files, ...outputs]);
  assert.ok(plan.encodedBytes > 256 * 1024 * 1024); assert.equal(plan.maxFileBytes, size);
  const readFile = name => name === 'baseline.bin' ? baseline : raw;
  assert.equal(validateEvidence(m, {readFile}).checked.length, 9);
  let reads = 0;
  assert.throws(() => validateEvidence(m, {readFile: () => {reads++;}, maxTotalBytes: plan.totalBytes - 1}), /budget/);
  assert.equal(reads, 0);
  outputs[0].sha256 = 'f'.repeat(64); assert.throws(() => validateEvidence(m, {readFile}), /bytes mismatch/);
  outputs[0] = {...descriptor('source-0.bin', raw), bytes: size - 1}; assert.throws(() => validateEvidence(m, {readFile}), /bytes mismatch/);
});
test('declared decoded bounds above the old cutoff remain exact and wrong expansions fail', () => {
  const raw = Buffer.alloc(size, 32), packed = gzipSync(raw), file = {...descriptor('source.gz', packed), uncompressed_bytes: raw.length, uncompressed_sha256: sha256(raw)};
  assert.equal(decodeEvidenceGzip(packed, file).length, size);
  const m = manifest(Buffer.from('baseline'), [file]);
  assert.equal(validateEvidence(m, {readFile: name => name === 'source.gz' ? packed : Buffer.from('baseline')}).checked.length, 2);
  assert.throws(() => decodeEvidenceGzip(packed, {...file, uncompressed_bytes: size - 1}), error => error.code === 'ERR_BUFFER_TOO_LARGE');
  assert.throws(() => decodeEvidenceGzip(packed, {...file, uncompressed_bytes: size + 1}), /bytes mismatch/);
  assert.throws(() => decodeEvidenceGzip(packed, {...file, uncompressed_sha256: 'f'.repeat(64)}), /bytes mismatch/);
  assert.throws(() => decodeEvidenceGzip(packed, file, {maxFileBytes: size - 1}), /budget/);
});
test('manifest arithmetic failures are rejected before any reader or decoder', () => {
  for (const mutate of [m => m.outputs[0].bytes = Number.MAX_SAFE_INTEGER, m => m.outputs[0].bytes = Infinity,
    m => {m.outputs[0].uncompressed_bytes = Number.MAX_SAFE_INTEGER; m.outputs[0].uncompressed_sha256 = 'a'.repeat(64);},
    m => m.outputs[0].path = '../escape']) {
    const m = manifest(Buffer.from('baseline'), [descriptor('next.bin', Buffer.from('next'))]); let reads = 0; mutate(m);
    assert.throws(() => validateEvidence(m, {readFile: () => {reads++;}})); assert.equal(reads, 0);
  }
});
test('real candidate and immutable Git readers use exact descriptors while unplanned callers retain their guard', () => {
  const directory = fs.mkdtempSync(path.join(process.cwd(), '.cache-byte-reader-')), raw = Buffer.alloc(size, 13), name = 'source.bin';
  const pin = descriptor(name, raw);
  const git = (...args) => execFileSync('git', ['-C', directory, ...args], {encoding: 'utf8'});
  try {
    fs.writeFileSync(path.join(directory, name), raw, {flag: 'wx'});
    const reader = repositoryReader(directory);
    assert.throws(() => reader(name, 'candidate'), /budget/);
    assert.equal(sha256(reader(name, 'candidate', pin)), pin.sha256);
    assert.throws(() => repositoryReader(directory, {maxFileBytes: size - 1})(name, 'candidate', pin), /budget/);
    assert.throws(() => reader(name, 'candidate', {...pin, bytes: size - 1}), /budget/);
    git('init', '--quiet'); git('add', name); git('-c', 'user.name=Byte test', '-c', 'user.email=byte-test@example.invalid', 'commit', '--quiet', '-m', 'Exact reader fixture');
    const head = git('rev-parse', 'HEAD').trim();
    assert.equal(sha256(reader(name, head, pin)), pin.sha256);
    assert.throws(() => reader(name, head, {...pin, bytes: size - 1}), /budget/);
    fs.appendFileSync(path.join(directory, name), 'x'); assert.throws(() => reader(name, 'candidate', pin), /budget/);
  } finally { fs.rmSync(directory, {recursive: true, force: true}); }
});

// One genuine complete-source chunk acquisition. No grid rows are computed.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gzipSync, gunzipSync} from 'node:zlib';
import {admitPhase, authenticateAdmittedBody} from './phase-admission.mjs';

const ROOT = process.cwd(), NS = 'coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008';
const ORIGINAL = 'c67345546a24479e29ff9e2872098c78b256209a';
const PROPOSAL = '859ca4643d61d472650dbda5a7c3682556ab78a4';
const GIT = '/Library/Developer/CommandLineTools/usr/bin/git';
const sha = body => createHash('sha256').update(body).digest('hex');
const LIMIT = 32 * 1024 * 1024, INPUT_RESERVE = 64 * 1024 * 1024, OUTPUT_RESERVE = 64 * 1024 * 1024;
const CODE = [`${NS}/acquire-operand.mjs`, `${NS}/phase-admission.mjs`, `${NS}/operand-codec.mjs`,
  `${NS}/append-scope.mjs`, 'src/native-runtime.js', 'src/native-grid.js',
  'scripts/native-ownership/compile-native-ownership.mjs', 'scripts/audit-grid-intervals.mjs'];
const ORIGINAL_CODE = {
  'src/native-grid.js': 'b54d593b9c6c1144e08cf2d536862dd9a14dd138e1851441dcbe4c487cf2d663',
  'src/native-runtime.js': '988f7069b6d39cbe0fa7bc3b0e4faaa61c2def7fb3d0ec68b87b5e14c7463600',
  'scripts/native-ownership/compile-native-ownership.mjs': '2cb66b2e3b15e48257976a9c4866e453174c0df961214a67a69d92c1dbbcd378',
  'scripts/audit-grid-intervals.mjs': '084b907b25cc51304a2317eaacfe9c0fd15eed49cb72ce2489c711f565bed1e9',
};

function destination(value) {
  assert(typeof value === 'string' && value && !value.split(path.sep).includes('..'));
  const output = path.resolve(value), cache = path.join(ROOT, '.cache');
  assert(output.startsWith(cache + path.sep), 'Fresh owned cache destination required');
  assert(!fs.existsSync(output), 'Existing output rejected');
  for (let current = output; ; current = path.dirname(current)) {
    try {
      const stat = fs.lstatSync(current);
      assert(!stat.isSymbolicLink(), 'Symlink output or ancestor');
      if (current !== output) assert(stat.isDirectory(), 'Ordinary output parent directory required');
    }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
    if (current === path.dirname(current)) break;
  }
  return output;
}

export async function acquire(head, ordinal, outputValue) {
  const output = destination(outputValue); // Before source/runtime body work.
  assert(/^[a-f0-9]{40}$/.test(head) && Number.isInteger(ordinal) && ordinal >= 0 && ordinal < 34);
  assert.equal(process.execArgv.length, 0); assert(!process.env.NODE_OPTIONS && !process.env.NODE_PATH);
  assert.equal(process.version, 'v24.19.0');
  const started = new Date().toISOString();
  const gitPin = {path: GIT, bytes: 7058848, mode: 0o755,
    sha256: '4c5ca299b5311572b4f948d11efd7c66dcadf30950fbf260688ee32f4a63f6a4'};
  // The expected Git digest is checked by the actual runtime receipt. It must
  // match the ordinary installed tool before any Git operation.
  const codePins = CODE.map(relative => {
    const file = path.join(ROOT, relative), stat = fs.lstatSync(file);
    assert(stat.isFile() && !stat.isSymbolicLink() && stat.size <= LIMIT);
    return {path: file, bytes: stat.size, mode: 0o644,
      sha256: '0'.repeat(64), relative}; // Independently resolved from Git after prospective admission.
  });
  const runtime = {path: process.execPath, bytes: 121304480, mode: 0o755,
    sha256: '9caea9deafcb0c7f22fac3206c32f0dcaf8d1f13460b0be3017fa09e7a4be4f6'};
  const admission = admitPhase({inputs: [gitPin, ...codePins], runtime,
    reservedInputBytes: INPUT_RESERVE, outputReserve: OUTPUT_RESERVE, metadataBytes: 1024 * 1024});
  authenticateAdmittedBody(admission, GIT); authenticateAdmittedBody(admission, process.execPath);
  let sourceBytes = 0;
  const reads = new Map();
  const codeReferences = new Map();
  function git(args, maxBuffer = LIMIT + 1) {
    return execFileSync(GIT, ['-C', ROOT, ...args], {maxBuffer, env: process.env});
  }
  assert.equal(git(['rev-parse', 'HEAD']).toString().trim(), head);
  assert.equal(path.resolve(git(['rev-parse', '--show-toplevel']).toString().trim()), ROOT);
  function body(commit, relative, expected) {
    assert(/^[a-f0-9]{40}$/.test(commit) && /^[a-zA-Z0-9._/-]+$/.test(relative) &&
      !relative.split('/').includes('..'));
    const line = git(['ls-tree', '-z', commit, '--', relative], 65536).toString();
    const match = /^100644 blob ([a-f0-9]{40})\t([^\0]+)\0$/.exec(line);
    assert(match && match[2] === relative, 'Whole ordinary Git source binding required');
    const bytes = Number(git(['cat-file', '-s', match[1]], 128).toString().trim());
    assert(Number.isSafeInteger(bytes) && bytes <= LIMIT);
    sourceBytes += bytes;
    assert(sourceBytes <= INPUT_RESERVE && reads.size + admission.descriptors < 512, 'Prospective source read cap');
    const raw = git(['cat-file', 'blob', match[1]], bytes + 1);
    assert.equal(raw.length, bytes);
    const digest = sha(raw);
    if (expected) assert.equal(digest, expected);
    reads.set(`${commit}:${relative}`, {commit, path: relative, mode: '100644', oid: match[1], bytes, sha256: digest});
    return raw;
  }
  for (const pin of codePins) {
    const reference = body(head, pin.relative);
    assert.equal(reference.length, pin.bytes);
    pin.sha256 = sha(reference);
    admission.snapshots.find(row => row.pin.path === pin.path).pin.sha256 = pin.sha256;
    authenticateAdmittedBody(admission, pin.path);
    codeReferences.set(pin.relative, reference.toString('utf8'));
    if (ORIGINAL_CODE[pin.relative]) assert.equal(pin.sha256, ORIGINAL_CODE[pin.relative]);
  }
  const {encodeOperandChunk, decodeOperandChunk} = await import('./operand-codec.mjs');
  const {proveCompletePolygonAppend, affectedRows} = await import('./append-scope.mjs');
  const {nativeRuntimeIndex} = await import('../../../src/native-runtime.js');
  const {compileNativeOwnership} = await import('../../../scripts/native-ownership/compile-native-ownership.mjs');
  const {nativePolygonIntervals} = await import('../../../src/native-grid.js');
  const {coverageRow} = await import('../../../scripts/audit-grid-intervals.mjs');
  const callables = [[acquire, `${NS}/acquire-operand.mjs`],
    [admitPhase, `${NS}/phase-admission.mjs`], [authenticateAdmittedBody, `${NS}/phase-admission.mjs`],
    [encodeOperandChunk, `${NS}/operand-codec.mjs`], [decodeOperandChunk, `${NS}/operand-codec.mjs`],
    [proveCompletePolygonAppend, `${NS}/append-scope.mjs`], [affectedRows, `${NS}/append-scope.mjs`],
    [nativeRuntimeIndex, 'src/native-runtime.js'], [compileNativeOwnership, 'scripts/native-ownership/compile-native-ownership.mjs'],
    [nativePolygonIntervals, 'src/native-grid.js'], [coverageRow, 'scripts/audit-grid-intervals.mjs']];
  function requireCallables() {
    for (const [callable, relative] of callables)
      assert(codeReferences.get(relative).includes(Function.prototype.toString.call(callable)),
        'Actual imported callable differs from complete immutable module');
  }
  requireCallables();
  const indexRaw = body(ORIGINAL, 'data/canonical-grid/eastern-v8/context-index.json',
    '2a1ba93fcdfc81da3247e6abacb49a5df6284d6c1ffd2b2a73f4e84c3b760716');
  const index = JSON.parse(indexRaw); assert.equal(index.parts.length, 34);
  const pin = index.parts[ordinal];
  function decoded(raw, bytes, expected) {
    assert(Number.isSafeInteger(bytes) && bytes <= LIMIT);
    sourceBytes += bytes; assert(sourceBytes <= INPUT_RESERVE, 'Decoded source cap before allocation');
    const value = gunzipSync(raw, {maxOutputLength: bytes});
    assert.equal(value.length, bytes); assert.equal(sha(value), expected); return value;
  }
  const encoded = body(ORIGINAL, `data/canonical-grid/eastern-v8/${pin.path}`, pin.sha256);
  assert.equal(encoded.length, pin.bytes);
  const originalDecoded = decoded(encoded, pin.decoded_bytes, pin.decoded_sha256);
  const features = JSON.parse(originalDecoded); assert.equal(features.length, pin.owners);
  const ids = new Set();
  features.forEach((feature, i) => {
    assert(!ids.has(feature.id)); ids.add(feature.id);
    assert.equal(feature.pixelIndex, pin.first_owner + i);
  });
  const variants = [], appendProofs = [];
  const targets = ['atlas:physical:CAN-15:NWT', 'atlas:physical:CAN-25:NUN'];
  if (features.some(feature => targets.includes(feature.id))) {
    const namespace = 'coordination/engineering/arctic-three-retained-land-fit-repair-20261008';
    const before = JSON.parse(decoded(body(PROPOSAL, `${namespace}/current-v8-part29.json.gz`,
      'fa286f44f47494cacab793e4109eb18db3e6016dc7103d930b9dff2dbf3573fb'), 12932407,
      'c34114912dc620dce0821e251877470b5a83385ab3bf1284408f077b78bbdec8'));
    const after = JSON.parse(decoded(body(PROPOSAL, `${namespace}/delivery/run-1/proposed-part-29.json.gz`,
      '5f76a01a2c43eeccb3a202507faf593f56157fe38bd89f541be3b64145bdb1a8'), 12932723,
      '4eca02f85d5e3a0974a96a38d59e46b0b71b41d2513dcf20ab27eb17fd5a0b4c'));
    const oldById = new Map(before.features.map(feature => [feature.id, feature]));
    const newById = new Map(after.features.map(feature => [feature.id, feature]));
    assert.equal(oldById.size, 1500); assert.equal(newById.size, 1500);
    for (const feature of features) if (targets.includes(feature.id)) {
      assert.deepEqual(feature.geometry, oldById.get(feature.id).geometry, 'Installed current native geometry mismatch');
      const geometry = newById.get(feature.id).geometry;
      appendProofs.push({id: feature.id, ...proveCompletePolygonAppend(feature.geometry, geometry)});
      variants.push({...feature, geometry});
    }
  }
  function guardOperandSize(rows) {
    let bytes = 0;
    for (const feature of rows) {
      const polygons = feature.geometry.type === 'Polygon' ? [feature.geometry.coordinates] : feature.geometry.coordinates;
      for (const polygon of polygons) for (const ring of polygon) bytes += ring.length * 16;
    }
    assert(Number.isSafeInteger(bytes) && bytes <= 24 * 1024 * 1024, 'Operand output bound before transformation');
  }
  guardOperandSize(features); guardOperandSize(variants);
  const originalOperand = encodeOperandChunk(features);
  const changedOperand = variants.length ? encodeOperandChunk(variants) : null;
  const outputs = [];
  let retainedCost = 0;
  fs.mkdirSync(output, {recursive: true});
  function publish(name, raw, compressed = false) {
    assert(raw.length <= LIMIT);
    const bytes = compressed ? gzipSync(raw, {level: 9}) : raw;
    assert(bytes.length <= LIMIT);
    retainedCost += bytes.length + (compressed ? raw.length : 0);
    assert(retainedCost <= OUTPUT_RESERVE, 'Full encoded and decoded output cap before write');
    fs.writeFileSync(path.join(output, name), bytes, {flag: 'wx', mode: 0o644});
    outputs.push({path: name, bytes: bytes.length, sha256: sha(bytes), mode: '100644',
      ...(compressed ? {decoded_bytes: raw.length, decoded_sha256: sha(raw)} : {})});
  }
  publish('original-coordinates.bin.gz', originalOperand.coordinates, true);
  publish('original-structure.json', Buffer.from(JSON.stringify(originalOperand.descriptor)));
  if (changedOperand) {
    publish('changed-coordinates.bin.gz', changedOperand.coordinates, true);
    publish('changed-structure.json', Buffer.from(JSON.stringify(changedOperand.descriptor)));
    publish('changed-complete-context-rows.json', Buffer.from(JSON.stringify(variants)));
  }
  for (const codePin of codePins) authenticateAdmittedBody(admission, codePin.path);
  requireCallables();
  authenticateAdmittedBody(admission, GIT); authenticateAdmittedBody(admission, process.execPath);
  assert.equal(git(['rev-parse', 'HEAD']).toString().trim(), head);
  const report = {version: 1, kind: 'complete-native-operand-chunk-acquisition', head,
    original_commit: ORIGINAL, proposal_commit: PROPOSAL, ordinal,
    original_context_pin: pin, original_owners: features.length,
    first_owner: pin.first_owner, last_owner: pin.first_owner + features.length - 1,
    changed_ids: variants.map(feature => feature.id), append_proofs: appendProofs,
    source_whole_bodies: [...reads.values()], source_encoded_plus_decoded_bytes: sourceBytes,
    upfront_phase_bytes: admission.bytes, upfront_input_reserve_bytes: INPUT_RESERVE,
    upfront_output_reserve_bytes: OUTPUT_RESERVE, actual_output_encoded_plus_decoded_bytes: retainedCost,
    installed_runtime: {...runtime, version: process.version, platform: process.platform, argv: process.execArgv},
    installed_git: {...gitPin, version: git(['--version'], 1024).toString().trim()}, executing_code: codePins,
    started_at: started, completed_at: new Date().toISOString(), outputs,
    grid_rows_computed: 0, successor_activated: false};
  const receipt = Buffer.from(JSON.stringify(report, null, 2) + '\n');
  assert(retainedCost + receipt.length <= OUTPUT_RESERVE);
  fs.writeFileSync(path.join(output, 'publication.json'), receipt, {flag: 'wx', mode: 0o644});
  return report;
}

if (process.argv[1] === path.join(ROOT, NS, 'acquire-operand.mjs')) {
  acquire(process.argv[2], Number(process.argv[3]), process.argv[4])
    .then(report => console.log(JSON.stringify({complete: true, ordinal: report.ordinal,
      owners: report.original_owners, changed_ids: report.changed_ids,
      phase_bytes: report.upfront_phase_bytes, grid_rows_computed: 0})))
    .catch(error => { console.error(error); process.exitCode = 1; });
}

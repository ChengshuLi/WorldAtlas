// Offline versioned preparation. Generation requires committed exact code.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import {bindNativeTopology} from './native-topology-binding.mjs';
import {loadNativeSourceInputs} from './native-only-inputs.mjs';
import {compileNativeOwnership} from './compile-native-ownership.mjs';
import {nativeCandidateManifest,NATIVE_CANONICAL_LATITUDE_SHA256} from './native-candidate-manifest.mjs';
import {committedPreparationFiles,createNativeCandidateOutput,requirePlainExecution,candidateBudget} from './native-preparation-guards.mjs';
import {shuffleOwnershipBytes} from '../../src/ownership-codec.js';

const options = {};
requirePlainExecution();
for (let n = 2; n < process.argv.length; n += 2) {
  const key = process.argv[n];
  if (!['--repo', '--baseline', '--vintage'].includes(key) || !process.argv[n + 1] || options[key])
    throw Error('Explicit repository, immutable baseline and fresh offline vintage required');
  options[key] = process.argv[n + 1];
}
const repo = fs.realpathSync(options['--repo']), baseline = options['--baseline'];
if (!/^[a-f0-9]{40}$/.test(baseline ?? '') || !/^[a-zA-Z0-9_-]+$/.test(options['--vintage'] ?? ''))
  throw Error('Invalid immutable baseline or vintage');
const head = execFileSync('git', ['-C', repo, 'rev-parse', 'HEAD'], {encoding: 'utf8'}).trim();
execFileSync('git', ['-C', repo, 'merge-base', '--is-ancestor', baseline, head]);
const urls = [import.meta.url, ...['native-only-inputs.mjs','compile-native-ownership.mjs',
  'native-candidate-manifest.mjs','native-preparation-guards.mjs','native-topology-binding.mjs'].map(name => new URL(name, import.meta.url)),
  ...['src/native-grid.js','src/ownership-codec.js','scripts/audit-grid-intervals.mjs']
    .map(name => new URL('../../' + name, import.meta.url))];
const names = ['package.json', ...urls.map(url => path.relative(repo, fileURLToPath(url)))];
const executed = committedPreparationFiles(repo, head, names);
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const started = performance.now();
const inputs = await loadNativeSourceInputs(repo, baseline);
const topology = bindNativeTopology(repo, head, inputs);
const latitudePath = 'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz';
const latitudeTree = execFileSync('git', ['-C', repo, 'ls-tree', '-z', head, '--', latitudePath], {encoding: 'utf8'});
if (!/^100644 blob /.test(latitudeTree) || latitudeTree.slice(latitudeTree.indexOf('\t') + 1) !== latitudePath + '\0')
  throw Error('Missing ordinary immutable normative latitude table');
const latitudeBlob = latitudeTree.split(' ')[2].split('\t')[0];
const latitudeLength = Number(execFileSync('git', ['-C', repo, 'cat-file', '-s', latitudeBlob], {encoding: 'utf8'}));
if (!Number.isInteger(latitudeLength) || latitudeLength < 1 || latitudeLength > 32 * 1024 * 1024)
  throw Error('Normative latitude file exceeds existing byte budget');
const latitudeEncoded = execFileSync('git', ['-C', repo, 'cat-file', 'blob', latitudeBlob], {maxBuffer: 32 * 1024 * 1024});
const latitudeBytes = gunzipSync(latitudeEncoded, {maxOutputLength: inputs.manifest.size * 8});
if (latitudeBytes.length !== inputs.manifest.size * 8 || digest(latitudeBytes) !== NATIVE_CANONICAL_LATITUDE_SHA256)
  throw Error('Immutable normative latitude bytes differ');
const latitudes = Float64Array.from({length: inputs.manifest.size}, (_, i) => latitudeBytes.readDoubleLE(i * 8));
const admission = candidateBudget([...inputs.sourceFiles, ...executed, ...topology.files, {bytes: latitudeEncoded.length}]);
const out = createNativeCandidateOutput(repo, '.cache/native-grid-candidates/' + options['--vintage']);
const products = [];
function write(relative, raw, decoded = raw) {
  if (!/^[a-zA-Z0-9_./-]+$/.test(relative) || relative.split('/').some(p => !p || p === '.' || p === '..') ||
    raw.length > 32 * 1024 * 1024 || decoded.length > 32 * 1024 * 1024)
    throw Error('Unsafe or oversized candidate product');
  const file = path.join(out, relative); fs.mkdirSync(path.dirname(file), {recursive: true});
  admission.add({bytes: raw.length}); // Enforce cumulative limits before writing each new product.
  fs.writeFileSync(file, raw, {flag: 'wx'});
  const descriptor = {path: relative, bytes: raw.length, sha256: digest(raw),
    decoded_bytes: decoded.length, decoded_sha256: digest(decoded)};
  products.push(descriptor); return descriptor;
}
const json = value => Buffer.from(JSON.stringify(value) + '\n');
// Normative rule input already exists in the immutable repository. Reference it
// explicitly; it is not a candidate output or an unresolved runtime asset path.
const latitude = {root:'repository',role:'immutable-normative-rule-input',path:latitudePath,commit:head,
  bytes:latitudeEncoded.length,sha256:digest(latitudeEncoded),decoded_bytes:latitudeBytes.length,
  decoded_sha256:digest(latitudeBytes)};
const compiled = await compileNativeOwnership(inputs.index, {size: inputs.manifest.size, latitudes,
  writePart: async (part, words) => {
    const raw = Buffer.alloc(words.length * 4);
    words.forEach((value, i) => raw.writeUInt32LE(value, i * 4));
    const bytes = gzipSync(shuffleOwnershipBytes(words), {level: 9});
    const descriptor = write(`native-v1/ownership/${part.kind}-${part.offset}.bin.gz`, bytes, raw);
    return {...part, ...descriptor, encoding: 'byte-shuffle'};
  },
  onBlock: block => fs.writeFileSync(path.join(out, 'progress.json'), json({phase: 'compiling', ...block}))
});
const rosterSha256 = digest(json(inputs.roster));
const manifest = nativeCandidateManifest({original: inputs.manifest, originalSha256: digest(inputs.manifestRaw),
  baselineCommit: baseline, evaluationCommit: head, releaseId: inputs.release.id,
  rosterSha256, ownerCount: inputs.roster.length, latitude, compiled});
write('manifest.json', json(manifest));
write('inputs.json', json({version: 1, baseline_commit: baseline, evaluation_commit: head,
  software: {node: process.version, v8: process.versions.v8, zlib: process.versions.zlib,
    platform: process.platform, arch: process.arch}, source_files: inputs.sourceFiles, normative_latitude_source: {path: latitudePath, commit: head,
    bytes: latitudeEncoded.length, sha256: digest(latitudeEncoded), decoded_sha256: digest(latitudeBytes)}, executed_sources: executed, vertices: inputs.vertices,
  retained_native_topology: topology, native_partitions: inputs.partitions, owner_roster: {count: inputs.roster.length, canonical_json_sha256: rosterSha256},
  geographic_release: inputs.release.id, original_ownership_run_assets_read: false}));
const reportBytes = json({version: 1, baseline_commit: baseline, evaluation_commit: head,
  ...compiled, scientific_approval: false, installation_ready: false,
  limits: ['Original native numerical membership; not source authority or factual geography approval.',
    'New offline candidate only; original assets, release, identities, point sets and live facts unchanged.',
    'Physical land/water and true native coverage omissions remain unclassified.']});
write('report.json.gz', gzipSync(reportBytes, {level: 9}), reportBytes);
write('preparation-budget.json', json({...admission.snapshot(), excludes_this_budget_file: true}));
fs.writeFileSync(path.join(out, 'progress.json'), json({phase: 'complete', elapsed_ms: performance.now() - started,
  maxRSS_raw: process.resourceUsage().maxRSS, products: products.length, aggregate_budget: admission.snapshot()}));
console.log(JSON.stringify({phase: 'complete', output: out, checked_cells: compiled.checked_cells,
  owners: inputs.roster.length, installation_ready: false}));

import test, {after} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import {loadOwnershipAssets} from '../src/ownership-assets.js';
import {ownershipRun,pickOwnership} from '../src/pixel-ownership.js';
import {bindNativeTopology,TOPOLOGY_ROOT} from '../scripts/native-ownership/native-topology-binding.mjs';
import {loadNativeSourceInputs} from '../scripts/native-ownership/native-only-inputs.mjs';
import {candidateBudget,originalCandidateAssets,committedPreparationFiles} from '../scripts/native-ownership/native-preparation-guards.mjs';
import {compileNativeOwnership} from '../scripts/native-ownership/compile-native-ownership.mjs';
import {shuffleOwnershipBytes} from '../src/ownership-codec.js';

const source = fileURLToPath(new URL('../scripts/native-ownership/', import.meta.url));
const atlas = fileURLToPath(new URL('../', import.meta.url));
const scratch = path.join(atlas, '.cache/native-preparer-tests');
fs.mkdirSync(scratch, {recursive: true});
const repo = fs.mkdtempSync(path.join(scratch, 'fixture-'));
after(() => fs.rmSync(repo, {recursive: true, force: true}));
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const json = value => Buffer.from(JSON.stringify(value) + '\n');
const latitudePath = 'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz';
const git = args => execFileSync('git', ['-C', repo, ...args], {encoding: 'utf8'}).trim();
function put(name, bytes) {
  const destination = path.join(repo, name); fs.mkdirSync(path.dirname(destination), {recursive: true});
  fs.writeFileSync(destination, bytes); return sha(bytes);
}
function inventory(directory) {
  return fs.readdirSync(directory, {withFileTypes: true}).flatMap(item => item.isDirectory() ?
    inventory(path.join(directory, item.name)).map(row => ({...row, path: item.name + '/' + row.path})) :
    item.name === 'progress.json' ? [] : [{path: item.name, sha256: sha(fs.readFileSync(path.join(directory, item.name)))}]);
}
let baseline;
test('actual committed CLI fixture produces two identical complete offline candidates', async () => {
  git(['init', '-q']); put('package.json', json({type: 'module'}));
  for (const name of ['prepare-native-candidate.mjs','native-only-inputs.mjs','compile-native-ownership.mjs',
    'native-candidate-manifest.mjs','native-preparation-guards.mjs','native-topology-binding.mjs','verify-native-candidate.mjs'])
    put('scripts/native-ownership/' + name, fs.readFileSync(path.join(source, name)));
  for (const name of ['src/native-grid.js','src/ownership-codec.js','src/ownership-assets.js','src/pixel-ownership.js','src/pixel-grid.js','scripts/audit-grid-intervals.mjs',latitudePath])
    put(name, fs.readFileSync(path.join(atlas, name)));
  const feature = {type: 'Feature', id: 'fixture-location', properties: {name: 'Fixture', parent_id: 'province'},
    geometry: {type: 'Polygon', coordinates: [[[0,0],[1,0],[1,1],[0,1],[0,0]]]}};
  const footprint = sha(Buffer.from(JSON.stringify([[feature.id, feature.geometry]])));
  const hierarchy = put('data/hierarchy.json', json({fixture: true}));
  const bounds = put('data/canonical-grid/bounds.json.gz', gzipSync(json([{id: feature.id, index: 1,
    province_id: 'province', province_index: 1, bounds: [0,0,262166,262166]}]), {level: 9}));
  const membership = Buffer.alloc(8); membership.writeUInt32LE(1, 4);
  const provinceHash = put('data/canonical-grid/province-membership.bin.gz', gzipSync(membership, {level: 9}));
  put('data/canonical-grid/manifest.json', json({version: 2, coordinateBits: 19, size: 262166,
    footprints_sha256: footprint, hierarchy_sha256: hierarchy, provinces: ['province'],
    bounds: {path: 'bounds.json.gz', sha256: bounds},
    province_membership: {path: 'province-membership.bin.gz', sha256: provinceHash}}));
  put('data/world-index.json', json({parts: ['geography/part-0.json']}));
  put('data/geography/part-0.json', json({type: 'FeatureCollection', features: [feature]}));
  const release = put('data/geographic-releases/fixture.json', json({releases: [{id: 'geography:fixture',
    footprints_sha256: footprint, hierarchy_sha256: hierarchy, expected_counts: {location: 1}}]}));
  put('data/geographic-releases/current-manifest.json', json({path: 'fixture.json', sha256: release}));
  git(['add', '-f', '.']); git(['-c', 'user.name=fixture', '-c', 'user.email=fixture@example.test',
    'commit', '-qm', 'immutable synthetic code/data fixture']); baseline = git(['rev-parse', 'HEAD']);
  const nativeInputs = await loadNativeSourceInputs(repo, baseline);
  const frozen = json({version:1,baseline_commit:baseline,evaluation_commit:baseline,
    source_files:nativeInputs.sourceFiles});
  put(TOPOLOGY_ROOT+'results-v1/inputs.json',frozen);
  put(TOPOLOGY_ROOT+'native-topology-v1.json',json({version:1,baseline_commit:baseline,evaluation_commit:baseline,
    method:'geos-native-planar-validity-v1',inputs_sha256:sha(frozen),checked_features:1,valid_nonempty_features:1,
    invalid_or_empty_features:0,unchecked_features:0,failures:[],
    partitions:[{path:'data/geography/part-0.json',checked_features:1,valid_nonempty_features:1,vertices:5}],
    limits:['Synthetic contract fixture; no real geography or scientific approval.']}));
  git(['add','-f',TOPOLOGY_ROOT]);git(['-c','user.name=fixture','-c','user.email=fixture@example.test',
    'commit','-qm','synthetic retained-topology contract fixture']);
  const cli = path.join(repo, 'scripts/native-ownership/prepare-native-candidate.mjs');
  for (const vintage of ['one', 'two']) {
    const result = JSON.parse(execFileSync(process.execPath, [cli, '--repo', repo, '--baseline', baseline,
      '--vintage', vintage], {encoding: 'utf8'}));
    assert.equal(result.checked_cells, 68731011556); assert.equal(result.owners, 1);
    assert.equal(result.installation_ready, false);
  }
  const one = path.join(repo, '.cache/native-grid-candidates/one');
  assert.deepEqual(inventory(one), inventory(path.join(repo, '.cache/native-grid-candidates/two')));
  const report = JSON.parse(gunzipSync(fs.readFileSync(path.join(one, 'report.json.gz'))));
  assert.equal(report.unchecked_cells, 0); assert.equal(report.per_owner_cells.length, 1);
  assert.ok(report.owned_cells > 0);
  const manifest = JSON.parse(fs.readFileSync(path.join(one, 'manifest.json')));
  assert.equal(manifest.native_latitudes.root,'repository');
  assert.equal(manifest.native_latitudes.role,'immutable-normative-rule-input');
  assert.equal(manifest.native_latitudes.path,latitudePath);
  assert.equal(manifest.native_latitudes.commit,git(['rev-parse','HEAD']));
  assert.equal(sha(Buffer.from(execFileSync('git',['-C',repo,'show',manifest.native_latitudes.commit+':'+latitudePath],
    {maxBuffer:32*1024*1024}))),manifest.native_latitudes.sha256);
  assert.equal(fs.existsSync(path.join(one,'native-v1/native-row-latitudes.f64le.gz')),false);
  const originalAssets = originalCandidateAssets(repo, manifest);
  assert.equal(sha(originalAssets.bounds), bounds); assert.equal(sha(originalAssets.province_membership), provinceHash);
  assert.equal(fs.existsSync(path.join(one, 'bounds.json.gz')), false, 'original identity assets resolve explicitly from Git');
  const decoded = await loadOwnershipAssets(manifest, async url => new Response(fs.readFileSync(path.join(one, url.slice(2)))));
  const normative = gunzipSync(fs.readFileSync(path.join(atlas, latitudePath)));
  // Independent integer half-space oracle for the fixture rectangle, not native scanlines.
  const threshold = lon => Number((BigInt(262166) * BigInt(lon) + 180n * (262166n - 1n) + 359n) / 360n);
  const start = threshold(0), end = threshold(1); let runs = 0, owned = 0;
  for (let y = 0; y < decoded.size; y++) {
    const latitude = normative.readDoubleLE(y * 8), covered = latitude > 0 && latitude <= 1;
    assert.equal(decoded.rows[y * 2], runs); assert.equal(decoded.rows[y * 2 + 1], covered ? 1 : 0);
    if (covered) {
      assert.deepEqual(ownershipRun(decoded, runs), {start, end, id: 1});
      assert.equal(pickOwnership(decoded, start - 1, y), 0); assert.equal(pickOwnership(decoded, start, y), 1);
      assert.equal(pickOwnership(decoded, end - 1, y), 1); assert.equal(pickOwnership(decoded, end, y), 0);
      runs++; owned += end - start;
    }
  }
  assert.equal(runs * 2, decoded.runs.length); assert.equal(owned, report.owned_cells);
  const verify = path.join(repo, 'scripts/native-ownership/verify-native-candidate.mjs');
  const verified = JSON.parse(execFileSync(process.execPath, [verify, '--repo', repo, '--one', 'one', '--two', 'two'],
    {encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe']}));
  assert.equal(verified.checked_cells, 68731011556);
  assert.equal(verified.unchecked_cells, 0);
  assert.equal(verified.owned_cells, report.owned_cells);
  assert.equal(verified.run_one_sha256, verified.run_two_sha256);
  const extra = path.join(repo, '.cache/native-grid-candidates/two/undeclared.json');
  fs.writeFileSync(extra, '{}');
  try {
    assert.throws(() => execFileSync(process.execPath, [verify, '--repo', repo, '--one', 'one', '--two', 'two'],
      {stdio: 'pipe'}), /Command failed/);
  } finally {fs.unlinkSync(extra);}
  assert.equal(git(['status', '--short', '--untracked-files=no']), '', 'original tracked sources untouched');
});
test('actual CLI refuses reused outputs and changed executed code before emitting a candidate', () => {
  const cli = path.join(repo, 'scripts/native-ownership/prepare-native-candidate.mjs');
  const args = vintage => [cli, '--repo', repo, '--baseline', baseline, '--vintage', vintage];
  const original = inventory(path.join(repo, '.cache/native-grid-candidates/one'));
  assert.throws(() => execFileSync(process.execPath, args('one'), {stdio: 'pipe'}), /Command failed/);
  assert.deepEqual(inventory(path.join(repo, '.cache/native-grid-candidates/one')), original);
  fs.appendFileSync(cli, '// changed executed code\n');
  assert.throws(() => execFileSync(process.execPath, args('changed-code'), {stdio: 'pipe'}), /Command failed/);
  assert.equal(fs.existsSync(path.join(repo, '.cache/native-grid-candidates/changed-code')), false);
});
test('aggregate byte/descriptor admission and explicit original identity references reject invalid contracts', () => {
  assert.throws(() => candidateBudget(Array.from({length: 9}, () => ({bytes: 32 * 1024 * 1024}))), /Aggregate/);
  assert.throws(() => candidateBudget(Array.from({length: 497}, () => ({bytes: 1}))), /Aggregate/);
  const budget = candidateBudget([{bytes: 1}], {reserveBytes: 0, reserveDescriptors: 0});
  assert.throws(() => budget.add({bytes: 33 * 1024 * 1024}), /whole-file/);
  const manifest = JSON.parse(fs.readFileSync(path.join(repo, '.cache/native-grid-candidates/one/manifest.json')));
  manifest.original_assets.bounds.path = 'data/other/bounds.json.gz';
  assert.throws(() => originalCandidateAssets(repo, manifest), /reference/);
});
test('canonical owner packing crosses low/high word boundaries with independently checked row spans', async () => {
  const size = 262166, normative = gunzipSync(fs.readFileSync(path.join(atlas, latitudePath)));
  const latitudes = Float64Array.from({length: size}, (_, y) => normative.readDoubleLE(y * 8));
  const ids = [8191,8192,8193,67108863];
  const index = ids.map((id,i) => ({index: id, polygons: [[Float64Array.from([
    i*2,0,i*2+1,0,i*2+1,1,i*2,1,i*2,0])]]}));
  const assets = new Map();
  const compiled = await compileNativeOwnership(index, {size,latitudes,rowBlock:511,partWords:4096,
    writePart: async (part, words) => {
      const raw = Buffer.alloc(words.length * 4); words.forEach((value,i) => raw.writeUInt32LE(value,i*4));
      const bytes = gzipSync(shuffleOwnershipBytes(words), {level:9}), name = `${part.kind}-${part.offset}.bin.gz`;
      assets.set('./'+name,bytes); return {...part,path:name,encoding:'byte-shuffle',sha256:sha(bytes),decoded_sha256:sha(raw)};
    }});
  const decoded = await loadOwnershipAssets(compiled, async url => new Response(assets.get(url)));
  const threshold = lon => Number((BigInt(size)*BigInt(lon)+180n*(BigInt(size)-1n)+359n)/360n);
  let runs = 0;
  for(let y=0;y<size;y++) {
    const covered = latitudes[y]>0&&latitudes[y]<=1;
    assert.equal(decoded.rows[y*2],runs); assert.equal(decoded.rows[y*2+1],covered?4:0);
    if(covered)for(let i=0;i<ids.length;i++) {
      const start=threshold(i*2),end=threshold(i*2+1);
      assert.deepEqual(ownershipRun(decoded,runs++),{start,end,id:ids[i]});
      assert.equal(pickOwnership(decoded,start,y),ids[i]); assert.equal(pickOwnership(decoded,end,y),0);
    }
  }
  assert.equal(runs*2,decoded.runs.length);
  assert.ok(compiled.parts.filter(p=>p.kind==='rows').length>1,'actual row transport split exercised');
  assert.ok(compiled.parts.filter(p=>p.kind==='runs').length>1,'actual run-part flush exercised');
});
test('actual CLI refuses inherited execution flags before candidate creation', () => {
  const cli = path.join(repo,'scripts/native-ownership/prepare-native-candidate.mjs');
  for(const launch of [
    {args:[cli],env:{...process.env,NODE_OPTIONS:'--no-warnings'}},
    {args:['--no-warnings',cli],env:{...process.env,NODE_OPTIONS:''}}
  ]) {
    try {execFileSync(process.execPath,[...launch.args,'--repo',repo,'--baseline',baseline,'--vintage','flags'],
      {env:launch.env,stdio:'pipe'});assert.fail('Injected launch must fail');}
    catch(error){assert.match(error.stderr?.toString()??'',/reviewed plain Node launch/);}
  }
  assert.equal(fs.existsSync(path.join(repo,'.cache/native-grid-candidates/flags')),false);
});

test('retained topology binds every source and complete partition accounting without asserting source authority', async () => {
  const inputs=await loadNativeSourceInputs(repo,baseline),head=git(['rev-parse','HEAD']);
  const binding=bindNativeTopology(repo,head,inputs);
  assert.equal(binding.checked_features,1);assert.equal(binding.native_audit_source_bytes_match,true);
  assert.match(binding.limits[0],/not a new audit/);
  for(const mutation of [
    value=>{value.sourceFiles[0].sha256='0'.repeat(64)},
    value=>{value.partitions[0].vertices++},
    value=>{value.partitions=[]},
    value=>{value.baselineCommit='0'.repeat(40)},
    value=>{value.roster=[]}
  ]) {
    const changed={...inputs,sourceFiles:inputs.sourceFiles.map(row=>({...row})),
      partitions:inputs.partitions.map(row=>({...row})),roster:[...inputs.roster]};
    mutation(changed);assert.throws(()=>bindNativeTopology(repo,head,changed),/topology/i);
  }
  assert.throws(()=>bindNativeTopology(repo,baseline,inputs),/Missing ordinary/);
});

test('undeclared nested module configuration fails before immutable code admission', () => {
  const head=git(['rev-parse','HEAD']),names=['package.json','src/native-grid.js'];
  assert.equal(committedPreparationFiles(repo,head,names).length,2);
  const nested=path.join(repo,'src/package.json');
  put('src/package.json',json({type:'module',imports:{'#hidden':'./changed.js'}}));
  try {
    assert.throws(()=>committedPreparationFiles(repo,head,names),/Undeclared module package configuration/);
    assert.throws(()=>committedPreparationFiles(repo,head,[...names,'src/package.json']),/Commit exact ordinary/);
  } finally {fs.unlinkSync(nested);}
});

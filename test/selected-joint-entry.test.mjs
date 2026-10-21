import {nativeLiteral} from './helpers/native-literal.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {spawnSync,execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {trustedFixture as checkpointFixture,appendNativeAuthority} from './fixtures/selected-checkpoint.mjs';
import {JOINT_CODE} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs';
import {trustedFixture} from './helpers/selected-joint-fixture.mjs';

const ENTRY = 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs';
function run(f, baseline, candidate, destination = path.join(f.root, 'complete'), extraEnv = {}) {
  const env = {...process.env, ...extraEnv}; delete env.NODE_OPTIONS; delete env.NODE_PATH;
  const trusted = f.git('rev-parse', 'HEAD').toString().trim();
  return spawnSync(process.execPath, [path.join(f.root, ENTRY), f.root, trusted,
    baseline, candidate, destination], {encoding:'utf8', env, timeout:30000});
}

const PHASES = ['trusted-startup', 'checkpoint-acquisition', 'baseline-qualification',
  'candidate-qualification', 'native-comparison', 'checkpoint-output'];
function assertPhases(result, expected) {
  const timings = result.stderr.trim().split('\n').filter(line => line.startsWith('{')).map(line => JSON.parse(line))
    .filter(row => Object.hasOwn(row, 'selected_joint_phase'));
  assert.deepEqual(timings.map(row => row.selected_joint_phase), expected);
  for (const timing of timings) {
    assert.deepEqual(Object.keys(timing).sort(), ['elapsed_ms', 'selected_joint_phase']);
    assert(Number.isSafeInteger(timing.elapsed_ms) && timing.elapsed_ms >= 0);
  }
  assert.doesNotMatch(result.stdout, /selected_joint_phase|elapsed_ms/);
}

test('actual joint CLI reports unseeded baseline as explicit cold validation, never unchanged success', async t => {
  const f = await trustedFixture(t);
  f.save('data/ownership-selection.json', {version:1}); const selected = f.commit();
  const result = run(f, selected, selected);
  assert.equal(result.status, 0, result.stderr);
  const report = JSON.parse(result.stdout);
  assert.equal(report.mode, 'legacy-cold-required');
  assert.equal(report.reuse_unavailable.cold, 'baseline-and-candidate');
  assertPhases(result, PHASES.slice(0, 3));
  assert.equal(Object.hasOwn(report, 'native'), false);
  assert.equal(fs.existsSync(path.join(f.root, 'complete')), false);
});

test('actual joint CLI preserves a qualified baseline but requires cold validation of unsupported candidate', async t => {
  const f = await trustedFixture(t);
  f.save('data/source.json', {type:'FeatureCollection', features:[]}); const candidate = f.commit();
  const result = run(f, f.selected, candidate);
  assert.equal(result.status, 0, result.stderr);
  const report = JSON.parse(result.stdout);
  assert.equal(report.mode, 'legacy-cold-required');
  assert.equal(report.reuse_unavailable.cold, 'candidate');
  assertPhases(result, PHASES.slice(0, 4));
  assert.match(report.reuse_unavailable.reason, /route changed/);
  assert.equal(fs.existsSync(path.join(f.root, 'complete')), false);
});

test('joint output collision and dangling symlink fail before qualification and preserve originals', async t => {
  const f = await trustedFixture(t), destination = path.join(f.root, 'complete');
  const sentinel = Buffer.from('original output sentinel'); fs.writeFileSync(destination, sentinel);
  let result = run(f, f.selected, f.selected, destination);
  assert.notEqual(result.status, 0); assert.match(result.stderr, /output already exists/);
  assertPhases(result, []);
  assert.deepEqual(fs.readFileSync(destination), sentinel);
  fs.unlinkSync(destination); fs.symlinkSync(path.join(f.root, 'absent-target'), destination);
  result = run(f, f.selected, f.selected, destination);
  assert.notEqual(result.status, 0); assert.match(result.stderr, /output already exists/);
  assertPhases(result, []);
  assert.equal(fs.readlinkSync(destination), path.join(f.root, 'absent-target'));
  assert.equal(fs.existsSync(path.join(f.root, 'absent-target')), false);
});

for(const module of ['scripts/selected-checkpoint-native.mjs','scripts/geography-prefetch.mjs'])
test('joint launcher authenticates additional module before importing it: '+module, async t => {
  const f = await trustedFixture(t), consumer = path.join(f.root, module);
  fs.appendFileSync(consumer, '\nthrow Error("unauthenticated consumer executed");\n');
  const result = run(f, f.selected, f.selected);
  assert.notEqual(result.status, 0); assert.match(result.stderr, /Joint code size differs/);
  assertPhases(result, []);
  assert.doesNotMatch(result.stderr, /Error: unauthenticated consumer executed/);
  assert.equal(fs.existsSync(path.join(f.root, 'complete')), false);
});

test('actual joint CLI qualifies once, runs the real native consumer and releases once', async t => {
  const f = await trustedFixture(t), coverage = path.join(f.root, 'coverage');
  const result = run(f, f.selected, f.selected, path.join(f.root, 'complete'), {NODE_V8_COVERAGE:coverage});
  assert.equal(result.status, 0, result.stderr);
  const report = JSON.parse(result.stdout);
  assert.equal(report.mode, 'authenticated-checkpoint-append-v1');
  assertPhases(result, PHASES);
  assert.equal(report.native.status, 'no-new-native-loss');
  assert.equal(report.continuous, undefined);
  assert.deepEqual(fs.readdirSync(path.join(f.root,'complete')).sort(), ['checkpoint-routes.json','derived-certificate.json.gz','derived-facts.json','derived-publication.json']);
  const derived = JSON.parse(fs.readFileSync(path.join(f.root, 'complete/derived-publication.json')));
  assert.deepEqual(report.derived_checkpoint, derived);
  assert.equal(derived.accepted_checkpoint, false);
  assert.equal(derived.validation_stage, 'native-passed');
  assert.equal(derived.kind, 'derived-selected-checkpoint-candidate-v1');
  const encoded = fs.readFileSync(path.join(f.root, 'complete', derived.certificate.path));
  const decoded = gunzipSync(encoded), certificate = JSON.parse(decoded);
  assert.equal(createHash('sha256').update(encoded).digest('hex'), derived.certificate.sha256);
  assert.equal(createHash('sha256').update(decoded).digest('hex'), derived.certificate.decoded_sha256);
  assert.equal(certificate.entries.length, 3);
  const derivedFacts = JSON.parse(fs.readFileSync(path.join(f.root, 'complete', derived.facts.path)));
  for (const name of fs.readdirSync(path.join(f.root, 'complete'))) {
    const encodedBody = fs.readFileSync(path.join(f.root, 'complete', name));
    const body = name.endsWith('.gz') ? gunzipSync(encodedBody) : encodedBody;
    assert.doesNotMatch(body.toString(), /selected_joint_phase|elapsed_ms/);
  }
  assert.equal(derivedFacts.baseline_commit, f.selected);
  assert.equal(derivedFacts.candidate_commit, f.selected);
  assert.deepEqual(derivedFacts.candidate_selection, f.selection);
  assert.deepEqual(derivedFacts.certificate, derived.certificate);
  assert.equal(Object.hasOwn(derivedFacts, 'complete_cold_custody'), false);
  assert.equal(derivedFacts.executing_authority_pins.length, 2);
  for (const pin of derivedFacts.executing_authority_pins) {
    assert.equal(pin.commit, derivedFacts.executing_commit);
    const body = f.git('show', pin.commit + ':' + pin.path);
    assert.equal(createHash('sha256').update(body).digest('hex'), pin.sha256);
    assert.equal(body.length, pin.bytes);
  }
  assert(derivedFacts.actual_reader_inventories.baseline.some(pin => pin.path === 'accepted/certificate.json.gz' && pin.whole_body_consumed));
  assert(Array.isArray(derivedFacts.actual_reader_inventories.candidate));
  const counts = new Map();
  for (const file of fs.readdirSync(coverage)) for (const script of JSON.parse(fs.readFileSync(path.join(coverage, file))).result) {
    if (!script.url.startsWith('file://' + f.root + '/')) continue;
    for (const fn of script.functions) counts.set(fn.functionName, (counts.get(fn.functionName) ?? 0) + fn.ranges[0].count);
  }
  for (const name of ['selectedBootstrap', 'qualifyCheckpoint', 'qualifyTransition', 'compareSelectedCheckpointNative', 'releaseCheckpoint'])
    assert.equal(counts.get(name), 1, name);
  assert.equal(counts.get('loadSelection'), 0);
  assert.equal(counts.get('selectedCoordinateShard'), 0);
});


test('actual warm joint entry reuses native-only custody without requiring addition polygons or a legacy target',async t=>{
  const f=await trustedFixture(t,{nativeOnly:true});
  f.save('unrelated.json',{newer:true});const newer=f.commit();
  const result=run(f,newer,newer);
  assert.equal(result.status,0,result.stderr);
  const report=JSON.parse(result.stdout);
  assert.equal(report.mode,'authenticated-checkpoint-append-v1');
  assert.equal(report.native.status,'no-new-native-loss');
  assert.deepEqual(report.native.native_row_scope.changed_rows,[]);
  const certificate=JSON.parse(gunzipSync(fs.readFileSync(path.join(f.root,'complete/derived-certificate.json.gz'))));
  assert.deepEqual(certificate.entries.find(row=>row[0]==='B')[9],[[1,0,10,20]]);
  assert.equal(f.ledger.current_targets.some(row=>row.target_id==='B'),false);
  const qualified=(await f.api.qualifyCheckpoint({reader:f.reader}));
  assert.equal(qualified.available,true);
  const row=qualified.state.additions.find(row=>row.representation==='native-cells');
  assert.equal(Object.hasOwn(row,'geometry'),false);
  assert.deepEqual(nativeLiteral(row.native_rows),[{y:2,runs:[[2,3,2]]}]);
  f.api.releaseCheckpoint(qualified.state);
});


test('actual warm native-only transition rejects coherently repinned same-count owner reassignment',async t=>{
  const f=await trustedFixture(t,{nativeOnly:true});
  const patch={...f.patch,rows:[{y:1,runs:[[2,3,1]]},{y:2,runs:[[2,3,3]]}]};
  f.save('candidate/patch.json',patch);const p=f.commit();
  const assets={...f.sidecar.logical_asset_map,patch:f.pin('candidate/patch.json',p)};
  f.save('candidate/envelope.json',{...f.envelope,...assets});const e=f.commit();
  f.save('candidate/sidecar.json',{...f.sidecar,logical_asset_map:assets,runtime_envelope:f.pin('candidate/envelope.json',e)});const sc=f.commit();
  const side=f.pin('candidate/sidecar.json',sc);
  f.save('data/ownership-selection.json',{...f.selection,additive_release:{path:side.path,bytes:side.bytes,sha256:side.sha256}});const candidate=f.commit();
  const result=run(f,f.selected,candidate);
  assert.notEqual(result.status,0);
  assert.match(result.stderr,/Candidate patch omitted, invented or reassigned original native intervals/);
  assertPhases(result, PHASES.slice(0, 3));
  assert.equal(fs.existsSync(path.join(f.root,'complete')),false);
});


test('actual joint CLI acquires only the appended completed-authority pins, then stays offline when warm',async t=>{
  const f=await checkpointFixture(t,{nativeAppend:true});
  for(const name of JOINT_CODE)f.save(name,fs.readFileSync(name));
  f.commit();
  const next=await appendNativeAuthority(f,{completedConstructor:true});
  const binding=JSON.parse(f.git('show',next.entry.source_authority.commit+':'+next.entry.source_authority.path));
  const pins=[next.entry.rule_preimage,next.entry.source_authority,next.entry.completed_constructor,
    binding.source_evidence,binding.native_patch];
  const unrelated=f.pin('appended/source.json');
  const remote=fs.mkdtempSync(path.join(path.dirname(f.root),'.joint-remote-'));
  t.after(()=>fs.rmSync(remote,{recursive:true,force:true}));
  execFileSync('git',['clone','--bare','--no-hardlinks',f.root,remote],{stdio:'ignore'});
  execFileSync('git',['-C',remote,'config','uploadpack.allowAnySHA1InWant','true']);
  execFileSync('git',['-C',remote,'config','uploadpack.allowFilter','true']);
  const url=pathToFileURL(remote).href;
  const unavailable=pathToFileURL(path.join(remote,'absent')).href;
  f.git('config','url.'+unavailable+'.insteadOf','https://github.com/ChengshuLi/WorldAtlas.git');
  const missing=p=>{try{f.git('cat-file','-e',p.git_blob_oid);return false;}catch{return true;}};
  for(const p of [...pins,unrelated]){
    fs.unlinkSync(path.join(f.root,'.git/objects',p.git_blob_oid.slice(0,2),p.git_blob_oid.slice(2)));
    assert(missing(p));
  }
  const objects=()=>new Set(f.git('cat-file','--batch-all-objects','--batch-check=%(objectname)').toString().trim().split('\n'));
  const before=objects();
  const refused=run(f,f.selected,next.candidate,path.join(f.root,'refused'),{GH_TOKEN:''});
  assert.notEqual(refused.status,0);assert.match(refused.stderr,/Geography object acquisition failed/);
  assert.equal(refused.stdout,'');assert(!fs.existsSync(path.join(f.root,'refused')));
  assert.deepEqual([...objects()].sort(),[...before].sort());
  f.git('config','--unset','url.'+unavailable+'.insteadOf');
  f.git('config','url.'+url+'.insteadOf','https://github.com/ChengshuLi/WorldAtlas.git');
  const cold=run(f,f.selected,next.candidate,path.join(f.root,'cold'),{GH_TOKEN:''});
  assert.equal(cold.status,0,cold.stderr);
  const report=JSON.parse(cold.stdout);
  assert.equal(report.mode,'authenticated-checkpoint-append-v1');
  assert.equal(report.native.status,'no-new-native-loss');
  assert.deepEqual(report.native.native_row_scope.changed_rows,[next.y]);
  assert.deepEqual([...objects()].filter(id=>!before.has(id)).sort(),pins.map(p=>p.git_blob_oid).sort());
  t.diagnostic('Imported '+pins.length+' exact blobs / '+pins.reduce((n,p)=>n+p.bytes,0)+' logical bytes; no network-byte or RSS claim');
  assert(missing(unrelated),'No source geometry or unrelated closure is acquired');
  for(const p of pins){
    const body=f.git('cat-file','blob',p.git_blob_oid);
    assert.equal(body.length,p.bytes);
    assert.equal(createHash('sha256').update(body).digest('hex'),p.sha256);
  }
  f.git('config','url.'+unavailable+'.insteadOf','https://github.com/ChengshuLi/WorldAtlas.git');
  f.git('config','--unset','url.'+url+'.insteadOf');
  const warm=run(f,f.selected,next.candidate,path.join(f.root,'warm'),{GH_TOKEN:''});
  assert.equal(warm.status,0,warm.stderr);
  assert.equal(JSON.parse(warm.stdout).native.status,'no-new-native-loss');
  assert(missing(unrelated));
  assert.deepEqual([...objects()].sort(),[...before,...pins.map(p=>p.git_blob_oid)].sort());
  // An absent producer commit retains the existing exact current-path alias.
  const absent=next.entry.completed_constructor.commit;
  fs.unlinkSync(path.join(f.root,'.git/objects',absent.slice(0,2),absent.slice(2)));
  const alias=run(f,f.selected,next.candidate,path.join(f.root,'alias'),{GH_TOKEN:''});
  assert.equal(alias.status,0,alias.stderr);
  assert.equal(JSON.parse(alias.stdout).native.status,'no-new-native-loss');
  assert.throws(()=>f.git('cat-file','-e',absent+'^{commit}'));
  // A known origin must not fall back to the identical current-path alias.
  const p=pins[0],originalTree=f.git('rev-parse',p.commit+':appended').toString().trim();
  assert.notEqual(originalTree,f.git('rev-parse',next.candidate+':appended').toString().trim());
  assert.equal(f.git('rev-parse',next.candidate+':'+p.path).toString().trim(),p.git_blob_oid);
  fs.unlinkSync(path.join(f.root,'.git/objects',originalTree.slice(0,2),originalTree.slice(2)));
  const mismatch=run(f,f.selected,next.candidate,path.join(f.root,'mismatch'),{GH_TOKEN:''});
  assert.notEqual(mismatch.status,0);assert.match(mismatch.stderr,/Geography object acquisition failed/);
  assert.equal(mismatch.stdout,'');assert(!fs.existsSync(path.join(f.root,'mismatch')));
});

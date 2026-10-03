import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {gzipSync} from 'node:zlib';
import {validateEvidence, sha256, subjectsHash, safeEvidencePath, repositoryReader} from '../scripts/evidence-quality.mjs';

const bytes = Buffer.from('synthetic control, not historical data\n');
const descriptor = {path:'control.txt', bytes:bytes.length, sha256:sha256(bytes), hash_kind:'file-bytes'};
const commit = 'a'.repeat(40);
function fixture() { return {
  version:1, issue:625, lane:'engineering', worker_id:'synthetic-test', subject_ids:[], subject_ids_sha256:subjectsHash([]),
  baseline:{commit, files:[descriptor], pins:{control_sha256:descriptor.sha256}, pin_files:{control_sha256:'control.txt'}},
  sources:[], outputs:[], methods:[{id:'control',description:'Synthetic byte verification',software:'Node 24',units:'bytes'}],
  metrics:[{id:'fraction',value:0.5,numerator:1,denominator:2,unit:'fraction',vintage:'current',input_sha256:descriptor.sha256,evaluation_commit:commit}],
  summaries:[{metric_id:'fraction',value:0.5,unit:'fraction'}], conclusions:[],
  stages:{research:'complete',implementation:'not-proposed',geographic_approval:'not-requested'}, commands:['node --test test/evidence-quality.test.mjs']
}; }
const reader = () => bytes;
test('verifies bytes without claiming factual correctness', () => {
  const r=validateEvidence(fixture(),{readFile:reader,expectedIssue:625});
  assert.equal(r.status,'bytes-verified'); assert.match(r.factual_validation,/independent/);
});
test('schema-only validation reports unverified bytes', () => assert.equal(validateEvidence(fixture()).status,'limited'));
test('known broken pins, stale baseline, entry hashes and contradictory summaries fail', () => {
  const mutations=[m=>m.baseline.pins.control_sha256='a'.repeat(61),m=>m.baseline.files[0].sha256='b'.repeat(64),
    m=>m.baseline.files[0].hash_kind='entry',m=>m.summaries[0].value=0.7,m=>m.metrics[0].denominator=3,
    m=>m.metrics[0].evaluation_commit='b'.repeat(40),m=>m.baseline.pin_files.control_sha256='wrong.txt'];
  for(const mutate of mutations){const m=structuredClone(fixture());mutate(m);assert.throws(()=>validateEvidence(m,{readFile:reader}));}
  assert.throws(()=>validateEvidence(fixture(),{readFile:()=>Buffer.from('changed')}),/bytes mismatch/);
  assert.throws(()=>validateEvidence(fixture(),{expectedSubjects:['missing']}),/scope/);
});
test('source access/license limits remain explicit; no unsafe retention', () => {
  const m=fixture();m.sources=[{id:'unavailable',url:'https://example.org/source',role:'control',vintage:'unknown',retrieved_at:'2026-10-03',
    license:{status:'unknown',terms:'not established'},retention:'restoration-only',verification:'unverified',temporal_status:'unknown',restoration:'Request a lawful export',limit:'Access unavailable'}];
  assert.equal(validateEvidence(m,{readFile:reader}).status,'limited');
  m.sources[0].retention='retained';m.sources[0].files=[descriptor];assert.throws(()=>validateEvidence(m),/reusable/);
  m.sources[0].retention='restoration-only';m.sources[0].temporal_status='historical';
  assert.throws(()=>validateEvidence(m),/interval/);
  m.sources[0].supported_interval={from:0,to:10};assert.throws(()=>validateEvidence(m),/year zero/);
});
test('research cannot grant approval; supported conclusions need known sources', () => {
  const m=fixture();m.lane='source-only';m.stages.geographic_approval='approved';assert.throws(()=>validateEvidence(m),/Research/);
  m.stages.geographic_approval='unapproved';m.conclusions=[{text:'Unsupported fact',status:'supported',source_ids:[]}];
  assert.throws(()=>validateEvidence(m),/conclusion/);
});
test('containing-file inventory verifies actual subject IDs, not optional properties.part', () => {
  const m=fixture(),raw=Buffer.from(JSON.stringify({features:[{properties:{id:'synthetic:A'}}]}));
  m.lane='geography';m.subject_ids=['synthetic:A'];m.subject_ids_sha256=subjectsHash(m.subject_ids);
  m.baseline.files=[{...descriptor,path:'geometry.json',bytes:raw.length,sha256:sha256(raw)}];
  m.baseline.pins={};m.baseline.subject_files={'synthetic:A':'geometry.json'};m.metrics=[];m.summaries=[];
  assert.equal(validateEvidence(m,{readFile:()=>raw}).status,'bytes-verified');
  m.baseline.subject_files['synthetic:A']='wrong.json';assert.throws(()=>validateEvidence(m),/unpinned/);
  m.baseline.subject_files['synthetic:A']='geometry.json';
  assert.throws(()=>validateEvidence(m,{readFile:()=>Buffer.from('{}')}),/bytes mismatch/);
});
test('compressed vs uncompressed hashes and decompression budgets are checked', () => {
  const m=fixture(),packed=gzipSync(bytes,{mtime:0});
  m.outputs=[{...descriptor,path:'control.gz',bytes:packed.length,sha256:sha256(packed),uncompressed_sha256:sha256(bytes),uncompressed_bytes:bytes.length}];
  assert.equal(validateEvidence(m,{readFile:name=>name.endsWith('.gz')?packed:bytes}).checked.length,2);
  m.outputs[0].uncompressed_sha256='f'.repeat(64);assert.throws(()=>validateEvidence(m,{readFile:name=>name.endsWith('.gz')?packed:bytes}),/Uncompressed/);
  assert.throws(()=>validateEvidence(fixture(),{maxFileBytes:1}),/budget/);
});
test('paths and symlinks cannot escape candidate reader', () => {
  for(const p of ['../secret','/secret','a/../b','a\\b','a//b'])assert.throws(()=>safeEvidencePath(p));
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'quality-'));
  try {fs.writeFileSync(path.join(dir,'real'),bytes);fs.symlinkSync('real',path.join(dir,'link'));
    assert.throws(()=>repositoryReader(dir)('link','candidate'),/symlinks/);
    assert.deepEqual(repositoryReader(dir)('real','candidate'),bytes);
  } finally {fs.rmSync(dir,{recursive:true,force:true});}
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {compactContextInputs} from '../scripts/native-ownership/compact-context-inputs.mjs';
import {validateContextInputStage,CONTEXT_STAGE_PATH} from '../scripts/native-ownership/validate-context-input-stage.mjs';
import {sha256,subjectsHash} from '../scripts/evidence-quality.mjs';
const ring=[[0,0],[1,0],[1,1],[0,0]];
const features=[{id:'B',properties:{parent_id:'P2',name:'Original B',fact:'retained'},geometry:{type:'MultiPolygon',coordinates:[[ring]]}},
 {id:'A',properties:{parent_id:'P1'},geometry:{type:'Polygon',coordinates:[ring]}}];
const bounds=[{id:'A',index:1,province_id:'P1'},{id:'B',index:2,province_id:'P2'}];
const sha=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
const footprint=sha(features.map(f=>[f.id,f.geometry]).sort((a,b)=>a[0].localeCompare(b[0])));
test('compact derivative preserves exact native geometry type, coordinates and original owner/parent mapping',()=>{
 const original=JSON.stringify(features),a=compactContextInputs(features,bounds,footprint),b=compactContextInputs(features,bounds,footprint);
 assert.deepEqual(a,b);assert.equal(JSON.stringify(features),original);
 assert.deepEqual(a.features.map(f=>[f.id,f.pixelIndex,f.properties.parent_id]),[['A',1,'P1'],['B',2,'P2']]);
 assert.equal(a.features[1].geometry.type,'MultiPolygon');assert.deepEqual(a.features[1].geometry,features[0].geometry);
 assert.equal(a.footprints_sha256,footprint);assert.equal(features[0].properties.fact,'retained');
});
test('incomplete IDs, wrong parents, drifted source digest and malformed native rings reject',()=>{
 assert.throws(()=>compactContextInputs(features.slice(1),bounds,footprint),/inventories/);
 assert.throws(()=>compactContextInputs([features[0],features[0]],bounds,footprint),/identity/);
 const wrong=structuredClone(features);wrong[0].properties.parent_id='wrong';
 assert.throws(()=>compactContextInputs(wrong,bounds,footprint),/parent/);
 assert.throws(()=>compactContextInputs(features,bounds,'0'.repeat(64)),/digest/);
 const broken=structuredClone(features);broken[0].geometry.coordinates[0][0][0][0]=NaN;
 assert.throws(()=>compactContextInputs(broken,bounds,footprint),/coordinates/);
});

// Exercise the live historical validator's code-closure gate without replaying geography.
test('context stage rejects coherently rehashed missing or duplicate executed sources before native loading',async()=>{
 const commit='a'.repeat(40),bytes=Buffer.from('immutable context-code fixture\n');
 const common=['package.json','scripts/native-ownership/compact-context-inputs.mjs','scripts/native-ownership/native-only-inputs.mjs',
  'scripts/native-ownership/native-preparation-guards.mjs','src/native-runtime.js','scripts/native-ownership/compile-native-ownership.mjs','src/native-grid.js','scripts/audit-grid-intervals.mjs'];
 const descriptor=(path,raw)=>({path,bytes:raw.length,sha256:sha256(raw),hash_kind:'file-bytes'});
 const prepare=[...common,'scripts/native-ownership/prepare-context-inputs.mjs'].map(path=>descriptor(path,bytes));
 const verify=[...common,'scripts/native-ownership/verify-context-inputs.mjs'].map(path=>descriptor(path,bytes));
 const files=[...prepare,verify.at(-1)],dir=CONTEXT_STAGE_PATH.slice(0,CONTEXT_STAGE_PATH.lastIndexOf('/'));
 for(const mutation of ['complete','missing','duplicate']){
  const inputs={baseline_commit:commit,execution_commit:commit,source_files:[],executed_sources:
   mutation==='missing'?prepare.slice(1):mutation==='duplicate'?[...prepare,prepare[0]]:prepare};
  const proof={verification_commit:commit,preparation_commit:commit,baseline_commit:commit,executed_sources:verify};
  const bodies=new Map([[dir+'/inputs.json',Buffer.from(JSON.stringify(inputs))],[dir+'/verification.json',Buffer.from(JSON.stringify(proof))]]);
  const manifest={version:1,issue:1010,lane:'engineering',worker_id:'context-code-fixture',subject_ids:[],subject_ids_sha256:subjectsHash([]),
   baseline:{commit,files},immutable_snapshots:files.map(f=>({...f,commit,snapshot_path:f.path})),
   transform:{kind:'original-native-to-compact-context-v1',original_commit:commit,generator_commit:commit,readback_commit:commit},
   sources:[],outputs:[...bodies].map(([path,raw])=>descriptor(path,raw)),methods:[],metrics:[],summaries:[],conclusions:[],
   stages:{research:'complete',implementation:'not-proposed',geographic_approval:'not-requested'},commands:['node --test test/compact-context-inputs.test.mjs']};
  let loaded=0;
  const readFile=(name,vintage)=>{
   if(name===CONTEXT_STAGE_PATH&&vintage==='candidate')return Buffer.from(JSON.stringify(manifest));
   if(vintage===commit&&files.some(f=>f.path===name))return bytes;
   assert.equal(vintage,'candidate');assert.ok(bodies.has(name),'Unexpected context-stage input');return bodies.get(name);
  };
  await assert.rejects(validateContextInputStage({readFile,loadSource:()=>{loaded++;throw Error('native loading boundary');}}),
   mutation==='complete'?/native loading boundary/:/Incomplete or duplicate executed context code closure/);
  assert.equal(loaded,mutation==='complete'?1:0,'Code closure must reject before any native source read');
 }
});

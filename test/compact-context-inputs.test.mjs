import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {compactContextInputs} from '../scripts/native-ownership/compact-context-inputs.mjs';
import {validateContextInputStage,CONTEXT_STAGE_PATH} from '../scripts/native-ownership/validate-context-input-stage.mjs';
import {sha256,subjectsHash} from '../scripts/evidence-quality.mjs';
import fs from 'node:fs';
import {gzipSync} from 'node:zlib';
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

test('each authenticated context-code vintage selects its own historical9 or current11 closure',async t=>{
 const originalCommit='a'.repeat(40),preparationCommit='b'.repeat(40),readbackCommit='c'.repeat(40);
 const compactPath='scripts/native-ownership/compact-context-inputs.mjs';
 const metadataPaths=['scripts/selected-reference-metadata.mjs','src/reference-metadata.js'];
 const common=['package.json',compactPath,'scripts/native-ownership/native-only-inputs.mjs',
  'scripts/native-ownership/native-preparation-guards.mjs','src/native-runtime.js',
  'scripts/native-ownership/compile-native-ownership.mjs','src/native-grid.js','scripts/audit-grid-intervals.mjs'];
 const currentCompact=fs.readFileSync(new URL('../scripts/native-ownership/compact-context-inputs.mjs',import.meta.url));
 const historicalCompact=Buffer.from("import {nativeRuntimeIndex} from '../../src/native-runtime.js';\n// Historical source-vintage fixture, without metadata helpers.\n");
 const descriptor=(path,raw)=>({path,bytes:raw.length,sha256:sha256(raw),hash_kind:'file-bytes'});
 const dir=CONTEXT_STAGE_PATH.slice(0,CONTEXT_STAGE_PATH.lastIndexOf('/'));
 async function exercise({preparation='current',readback='current',mutation,stage='readback',helper=metadataPaths[0]}={}){
  const rawCode=new Map([[originalCommit+':fixture-original.json',Buffer.from('{}\n')]]);
  const inventories={};
  for(const [label,profile,commit,entry] of [['preparation',preparation,preparationCommit,'prepare-context-inputs.mjs'],
   ['readback',readback,readbackCommit,'verify-context-inputs.mjs']]){
   inventories[label]=[...common,...(profile==='current'?metadataPaths:[]),'scripts/native-ownership/'+entry].map(name=>{
    const raw=name===compactPath?(profile==='current'?currentCompact:historicalCompact):Buffer.from('immutable '+name+'\n');
    rawCode.set(commit+':'+name,raw);return descriptor(name,raw);
   });
  }
  const historicalFiles=[...rawCode].map(([key,raw])=>{
   const separator=key.indexOf(':');return {...descriptor(key.slice(separator+1),raw),commit:key.slice(0,separator)};
  });
  if(mutation==='false-historical')inventories[stage]=inventories[stage].filter(file=>!metadataPaths.includes(file.path));
  if(mutation==='missing')inventories[stage]=inventories[stage].filter(file=>file.path!==helper);
  if(mutation==='duplicate')inventories[stage].push(inventories[stage].find(file=>file.path===helper));
  if(mutation==='extra')inventories[stage].push(descriptor('scripts/unexpected-context-helper.mjs',Buffer.from('extra')));
  const compact=compactContextInputs(features,bounds,footprint),rawPart=Buffer.from(JSON.stringify(compact.features)),encoded=gzipSync(rawPart);
  const part={path:'part-0.json.gz',bytes:encoded.length,sha256:sha256(encoded),uncompressed_bytes:rawPart.length,
   uncompressed_sha256:sha256(rawPart),first_owner:1,owners:2};
  const inputs={baseline_commit:originalCommit,execution_commit:preparationCommit,source_files:[],executed_sources:inventories.preparation,
   parts:[part],original_release:'geography:fixture',footprints_sha256:footprint,owner_sha256:compact.owner_sha256,
   vertices:8,installation_ready:false};
  const inputRaw=Buffer.from(JSON.stringify(inputs)),products=[{path:part.path,bytes:part.bytes,sha256:part.sha256},
   {path:'inputs.json',bytes:inputRaw.length,sha256:sha256(inputRaw)}].sort((a,b)=>a.path.localeCompare(b.path));
  const proof={baseline_commit:originalCommit,preparation_commit:preparationCommit,verification_commit:readbackCommit,
   source_files:[],executed_sources:inventories.readback,locations:2,vertices:8,footprints_sha256:footprint,
   owner_sha256:compact.owner_sha256,products,run_one_sha256:sha256(JSON.stringify(products)),run_two_sha256:sha256(JSON.stringify(products)),
   installation_ready:false,scientific_approval:false};
  const bodies=new Map([[dir+'/inputs.json',inputRaw],[dir+'/verification.json',Buffer.from(JSON.stringify(proof))],
   [dir+'/'+part.path,encoded]]);
  const outputs=[...bodies].map(([name,raw])=>({...descriptor(name,raw),...(name.endsWith('.gz')?
   {uncompressed_bytes:rawPart.length,uncompressed_sha256:sha256(rawPart)}:{})}));
  const manifest={version:1,issue:1010,lane:'engineering',worker_id:'context-vintage-fixture',subject_ids:[],subject_ids_sha256:subjectsHash([]),
   baseline:{version:2,commit:originalCommit,files:historicalFiles},
   immutable_snapshots:historicalFiles.map(file=>({...file,snapshot_path:file.path})),
   transform:{kind:'original-native-to-compact-context-v1',original_commit:originalCommit,generator_commit:preparationCommit,readback_commit:readbackCommit},
   sources:[],outputs,methods:[],metrics:[],summaries:[],conclusions:[],
   stages:{research:'complete',implementation:'not-proposed',geographic_approval:'not-requested'},commands:['node --test test/compact-context-inputs.test.mjs']};
  let loaded=0;const reads=new Map(),targetCommit=stage==='preparation'?preparationCommit:readbackCommit;
  const readFile=(name,vintage)=>{
   if(vintage==='candidate')return name===CONTEXT_STAGE_PATH?Buffer.from(JSON.stringify(manifest)):bodies.get(name);
   const key=vintage+':'+name,raw=rawCode.get(key);assert.ok(raw,'Unexpected historical input '+key);
   reads.set(key,(reads.get(key)??0)+1);
   // The generic evidence read succeeds. The execution-vintage authentication
   // must still reject a later changed helper before invoking loadSource.
   if(mutation==='tamper'&&vintage===targetCommit&&name===helper&&reads.get(key)>1)return Buffer.concat([raw,Buffer.from('changed')]);
   return raw;
  };
  readFile.assertAncestor=commit=>assert.ok([originalCommit,preparationCommit,readbackCommit].includes(commit));
  const loadSource=async()=>{loaded++;return {sourceFiles:[],bounds,manifest:{footprints_sha256:footprint},
   roster:compact.features.map(feature=>({id:feature.id,parent_id:feature.properties.parent_id})),release:{id:'geography:fixture'},vertices:8};};
  if(mutation){
   await assert.rejects(validateContextInputStage({readFile,loadSource}),mutation==='tamper'?/Executed context code differs/:
    /Incomplete or duplicate executed context code closure/);
   assert.equal(loaded,0,'Invalid executed-code closure must fail before native source loading');
  }else{
   const result=await validateContextInputStage({readFile,loadSource});assert.equal(result.status,'verified');
   assert.equal(result.locations,2);assert.equal(loaded,1);
  }
 }
 for(const [preparation,readback] of [['historical','historical'],['current','current'],['historical','current'],['current','historical']])
  await t.test(preparation+' preparation / '+readback+' readback',()=>exercise({preparation,readback}));
 for(const stage of ['preparation','readback']){
  await t.test(stage+' current source cannot claim historical inventory',()=>exercise({stage,mutation:'false-historical'}));
  await t.test(stage+' rejects extra inventory entry',()=>exercise({stage,mutation:'extra'}));
  for(const helper of metadataPaths)for(const mutation of ['missing','duplicate','tamper'])
   await t.test(stage+' '+mutation+' '+helper,()=>exercise({stage,helper,mutation}));
 }
});

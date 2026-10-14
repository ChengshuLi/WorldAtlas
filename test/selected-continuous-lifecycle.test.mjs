import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync,spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import {ImmutableReader,NativeAssetImage,loadSelection,inspectSelected,compareIntervals,compareRepairLedgers,readArtifactConsumption,validateReleaseCatalogue,validateArtifactSourceMetadata,loadNativeRowTable,acquireNativeRows,validateNativeRowCarry} from '../scripts/check-effective-geographic-regression.mjs';
import {assembleSupportedActivation} from '../coordination/engineering/additive-native-activation-20261009/assemble-supported-activation.mjs';
import {shuffleOwnershipBytes} from '../src/ownership-codec.js';
import {valueBytes,valueSha,readOriginalRuleAuthority,selectedCoordinateShard,joinSelectedCoordinateCertificate,acceptColdCoordinateCertificate,selectedAffectedPlan,possibleNeighbors,compareVersionedRepairLedgers} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const sha=b=>createHash('sha256').update(b).digest('hex'),root=process.cwd();
const retained=process.env.WORLDATLAS_LIFECYCLE_CONTROLS;
if(retained){assert.equal(fs.realpathSync(path.dirname(retained)),path.dirname(retained));assert.equal(fs.existsSync(retained),false);assert.throws(()=>fs.lstatSync(retained),{code:'ENOENT'});fs.mkdirSync(retained);}
let fixtureOrdinal=0;
function fixture(){
 const repo=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'selected-geography-fixture-')));
 const git=(...args)=>execFileSync('git',['-C',repo,...args],{stdio:['ignore','pipe','pipe']}).toString().trim();
 git('init');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid');
 const write=(name,value)=>{const raw=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value));fs.mkdirSync(path.dirname(path.join(repo,name)),{recursive:true});fs.writeFileSync(path.join(repo,name),raw);return raw;};
 const issued=[];
 const commit=()=>{git('add','.');git('commit','-m','Whole immutable synthetic fixture');const head=git('rev-parse','HEAD');issued.push(head);return head;};
 // Copy only real executing namespaces; no dependencies, datasets or checkout.
 for(const name of ['scripts/run-geographic-check.py','scripts/check-effective-geographic-regression.mjs','scripts/visible-gap-eligibility.mjs','src/native-grid.js','scripts/check-geographic-regression.py','scripts/evidence/immutable.py','scripts/evidence/geometry.py','scripts/ellipsoidal_area.py','src/ownership-codec.js','coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs','coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs'])write(name,fs.readFileSync(name));
 for(const name of ['package.json','requirements.txt','.github/evidence-policy.json'])write(name,fs.readFileSync(name));
 write('data/world-index.json',{parts:['geography/fixture.json']});write('data/geography/fixture.json',{type:'FeatureCollection',features:[]});
 write('data/hierarchy.json',[]);write('data/canonical-grid/manifest.json',{version:1});write('data/geographic-releases/index.json',{});
 const release=write('data/geographic-releases/release.json',{id:'geography:review:fixture'});
 write('data/geographic-releases/current-manifest.json',{path:'release.json',sha256:sha(release)});
 const owners=[{index:1,id:'old-owner',province_id:'parent',province_index:1},{index:2,id:'other-owner',province_id:'parent',province_index:1}];
 const bounds=write('data/canonical-grid/bounds.json.gz',gzipSync(Buffer.from(JSON.stringify(owners))));
 const origin=commit();
 const part=(kind,words)=>{const raw=Buffer.from(words.buffer),encoded=gzipSync(shuffleOwnershipBytes(words)),name=`native-v1/ownership/${kind}-0.bin.gz`;write('data/canonical-grid/fixture/'+name,encoded);return {kind,offset:0,words:words.length,path:name,bytes:encoded.length,sha256:sha(encoded),decoded_bytes:raw.length,decoded_sha256:sha(raw),encoding:'byte-shuffle'};};
 const select=(intervals,{extraSelection={},indices=false,badRows=false,transport=false,releaseId='geography:review:fixture'}={})=>{
  const rows=new Uint32Array(8),words=[];let cursor=0;
  for(let y=0;y<4;y++){rows[y*2]=cursor;rows[y*2+1]=(intervals[y]??[]).length;for(const [start,end,owner]of intervals[y]??[]){words.push(owner*4+start,end-1);cursor++;}}
  if(badRows)rows[2]++;
  const manifest={version:2,method:'native-linear-evenodd-first-owner-v1',size:4,coordinateBits:2,runWords:words.length,parts:[part('rows',rows),part('runs',Uint32Array.from(words))],geographic_release:releaseId,bounds:{sha256:sha(bounds),decoded_bytes:Buffer.byteLength(JSON.stringify(owners))},original_assets:{bounds:{role:'original-identity-parent-camera-context',commit:origin,path:'data/canonical-grid/bounds.json.gz',sha256:sha(bounds)}},native_latitudes:{sha256:'1'.repeat(64)}};
  const manifestPath=transport?'data/canonical-grid/transport/manifest.json':'data/canonical-grid/fixture/manifest.json';
  if(transport){
   let offset=0;const bodies=manifest.parts.map(p=>fs.readFileSync(path.join(repo,'data/canonical-grid/fixture',p.path)));
   const files=manifest.parts.map((p,i)=>{const item={path:p.path,offset,bytes:bodies[i].length,sha256:sha(bodies[i]),mode:'100644'};offset+=item.bytes;return item;});
   const whole=Buffer.concat(bodies),cut=Math.max(1,Math.floor(whole.length/2));let at=0;
   const parts=[whole.subarray(0,cut),whole.subarray(cut)].map((body,i)=>{const raw=gzipSync(body),item={path:'group/part-'+i+'.bin.gz',offset:at,bytes:raw.length,sha256:sha(raw),decoded_bytes:body.length,decoded_sha256:sha(body)};at+=body.length;write('data/canonical-grid/transport/bank/'+item.path,raw);return item;});
   const index={version:1,issue:1295,kind:'ordered-exact-original-byte-fragments',files,parts,whole_bytes:whole.length,whole_sha256:sha(whole)},encoded=write('data/canonical-grid/transport/bank/index.json',index);
   manifest.native_asset_transport={version:1,kind:index.kind,index:{path:'data/canonical-grid/transport/bank/index.json',bytes:encoded.length,sha256:sha(encoded)},logical_assets:files.length,original_compressed_bytes:whole.length};
  }
  const raw=write(manifestPath,manifest),digest=sha(raw);
  const products=[{path:'manifest.json',bytes:raw.length,sha256:digest},...manifest.parts];
  const receipt={method:manifest.method,checked_rows:4,checked_cells:16,unchecked_cells:0,checked_runs:words.length/2,installation_ready:false,products,two_run_products:products.length,run_one_sha256:sha(Buffer.from(JSON.stringify(products))),run_two_sha256:sha(Buffer.from(JSON.stringify(products)))};
  const receiptRaw=write('coordination/engineering/fixture/receipt.json',receipt),proofCommit=commit();
  write('scripts/native-ownership/verified-candidates.json',{version:1,candidates:{[digest]:{commit:proofCommit,path:'coordination/engineering/fixture/receipt.json',sha256:sha(receiptRaw),role:'reviewed-exhaustive-native-rule-comparison',installation_approval:false}}});
  write('data/ownership-selection.json',{version:1,method:manifest.method,manifest_path:manifestPath,sha256:digest,release_id:manifest.geographic_release,...extraSelection});
  return commit();
 };
 return {repo,git,write,commit,select,cleanup:()=>{
  if(retained){const objects=[...new Set(git('rev-list','--objects',...issued).split('\n').map(row=>row.split(' ')[0]))].map(oid=>{const type=git('cat-file','-t',oid),body=execFileSync('git',['-C',repo,'cat-file',type,oid],{maxBuffer:32*1024*1024});assert.equal(createHash('sha1').update(Buffer.from(type+' '+body.length+'\0')).update(body).digest('hex'),oid);return {oid,type,bytes:body.length,sha256:sha(body),base64:body.toString('base64')};});const result={kind:'complete-synthetic-immutable-entry-fixture',commits:issued,objects,source_approval:false};fs.writeFileSync(path.join(retained,`fixture-${fixtureOrdinal++}.json.gz`),gzipSync(Buffer.from(JSON.stringify(result))),{flag:'wx'});}
  fs.rmSync(repo,{recursive:true,force:true});
 }};
}


import * as native from '../scripts/check-effective-geographic-regression.mjs';
import * as helper from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {validatePersistedColdSide,reopenCompleteColdPlan,acquireContinuousSources,acquireContinuousSource,acquireCandidateContinuousSources,mayUseNonAdditiveShortcut} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs';
const P='coordination/engineering/selected-geography-effective-prevention-20261009/';
function sourceSides(f){
 const rect=(a,b)=>({type:'Polygon',coordinates:[[[a,0],[b,0],[b,1],[a,1],[a,0]]]});
 const install=(first,second,releaseId,{split=false}={})=>{
  const rows=['old-owner','other-owner'].map((id,i)=>({type:'Feature',id,properties:{id,parent_id:'parent'},geometry:i?second:first}));
  const selected=f.select([[[0,1,1]],[[2,3,2]],[],[]],{transport:true,releaseId}),selection=JSON.parse(fs.readFileSync(path.join(f.repo,'data/ownership-selection.json')));
  const groups=split?rows.map(row=>[row]):[rows];
  const sources=groups.map((features,i)=>({path:split?`source/current-${i}.json.gz`:'source/current.json.gz',logical_path:split?`data/geography/fixture-${i}.json`:'data/geography/fixture.json',body:Buffer.from(JSON.stringify({type:'FeatureCollection',features}))}));
  f.write('data/world-index.json',{parts:sources.map(p=>p.logical_path.slice(5))});
  for(const source of sources)f.write(source.path,gzipSync(source.body));
  const digest=sha(Buffer.from(JSON.stringify(rows.map(r=>[r.id,r.geometry]).sort((a,b)=>a[0].localeCompare(b[0])))));
  const release=f.write('data/geographic-releases/selected.json.gz',gzipSync(Buffer.from(JSON.stringify({releases:[{id:releaseId,footprints_sha256:digest}]}))));f.write('data/geographic-releases/current-manifest.json',{path:'selected.json.gz',sha256:sha(release)});const original=f.commit();
  const pin=name=>{const raw=execFileSync('git',['-C',f.repo,'show',original+':'+name]),[mode,,git_blob_oid]=f.git('ls-tree',original,'--',name).split(/[ \t]/);return {commit:original,path:name,mode,git_blob_oid,bytes:raw.length,sha256:sha(raw)};};
  const bank={version:1,kind:'complete-world-index-with-exact-encoded-overrides',release_id:releaseId,native_manifest_sha256:selection.sha256,footprints_sha256:digest,locations:2,world_index:pin('data/world-index.json'),unchanged_files:[],overrides:sources.map(source=>({...pin(source.path),logical_path:source.logical_path,encoding:'gzip',decoded_bytes:source.body.length,decoded_sha256:sha(source.body)}))};const raw=f.write('source/bank.json',bank);
  f.write('data/ownership-selection.json',{...selection,selected_geography:{version:1,kind:bank.kind,path:'source/bank.json',bytes:raw.length,sha256:sha(raw)}});return f.commit();
 };
 return {rect,install};
}
function issueStages(f,before,after){
 f.git('checkout',before);const directory=fs.mkdtempSync(path.join(f.repo,'cold-'));
 const env={...process.env};delete env.NODE_OPTIONS;delete env.NODE_PATH;
 const stagePaths=[path.join(directory,'before'),path.join(directory,'after')];
 const ack=[before,after].map((selected,i)=>{const r=spawnSync(process.execPath,['--expose-gc',path.join(f.repo,P+'selected-continuous-entry.mjs'),'coordinate',f.repo,before,selected,stagePaths[i]],{env,encoding:'utf8'});assert.equal(r.status,0,r.stderr);return JSON.parse(r.stdout);});
 const startup=native.selectedBootstrap(f.repo,before,after),r=startup.beforeReader;
 const context={repo:f.repo,runtimeBytes:r.runtimeBytes,executionBytes:r.executionBytes,gitExecutable:r.gitExecutable,identities:startup.identities};
 return {directory,stagePaths,ack,context};
}
const product=(directory,ack)=>{const publication=JSON.parse(fs.readFileSync(path.join(directory,'publication.json'))),facts=JSON.parse(fs.readFileSync(path.join(directory,'facts.json'))),encoded=fs.readFileSync(path.join(directory,'certificate.json.gz')),decoded=gunzipSync(encoded);return {publication,facts,certificate:JSON.parse(decoded),encoded_sha256:sha(encoded),decoded_sha256:sha(decoded)};};
function validate(f,state,selected,i,receipts=[]){const carriedState={context:state.context,code:[],ack:state.ack,receipts,lifecycle:[]};return validatePersistedColdSide(native,helper,{repo:f.repo,selected,directory:state.stagePaths[i],ack:state.ack[i],context:state.context,carriedState});}

test('genuine detached receipts reopen both complete certificates and preserve all changed-owner neighbors',()=>{
 const f=fixture();try{const {rect,install}=sourceSides(f),before=install(rect(0,1),rect(2,3),'before'),after=install(rect(0,2.2),rect(1.8,3.2),'after'),state=issueStages(f,before,after);
  const receipts=[validate(f,state,before,0)];receipts.push(validate(f,state,after,1,receipts));
  assert.equal(receipts[0].facts.complete_owners,2);assert.ok(receipts[0].inventory.length);assert.equal(Object.hasOwn(receipts[0],'resolver'),false);
  const closure=reopenCompleteColdPlan(native,helper,{repo:f.repo,baseline:before,candidate:after,...state,receipts,carriedBytes:2*valueBytes({context:state.context,ack:state.ack,receipts}).length});
  assert.deepEqual(closure.plan.changed_ids,['old-owner','other-owner']);assert.deepEqual(closure.plan.required_ids,['old-owner','other-owner']);assert.deepEqual(closure.plan.pairs,[['old-owner','other-owner']]);assert.equal(closure.rows.baseline.length,2);assert.equal(closure.rows.candidate.length,2);assert.ok(closure.complete_phase_bytes<=268435456);
  assert.throws(()=>helper.reopenColdCoordinateCertificate(structuredClone(receipts[0]),product(state.stagePaths[0],state.ack[0])),/Missing private/);
  const changed=product(state.stagePaths[0],state.ack[0]);changed.certificate.entries.pop();changed.decoded_sha256=valueSha(changed.certificate);assert.throws(()=>helper.reopenColdCoordinateCertificate(receipts[0],changed),/changed whole/);
  const rebound=product(state.stagePaths[0],state.ack[0]);rebound.facts.selected_commit=after;rebound.publication.facts.sha256=valueSha(rebound.facts);assert.throws(()=>helper.reopenColdCoordinateCertificate(receipts[0],rebound),/changed whole/);
  assert.throws(()=>validate(f,state,after,0),/Foreign cold certificate/);
  assert.throws(()=>validatePersistedColdSide(native,helper,{repo:f.repo,selected:before,directory:state.stagePaths[0],ack:state.ack[0],context:state.context}),/Incomplete cold carried/);
  const whole=fs.readFileSync(path.join(state.stagePaths[0],'certificate.json.gz'));fs.writeFileSync(path.join(state.stagePaths[0],'certificate.json.gz'),whole.subarray(0,whole.length-1));assert.throws(()=>validate(f,state,before,0),/mode\/whole length/);fs.writeFileSync(path.join(state.stagePaths[0],'certificate.json.gz'),whole);
  const missing=product(state.stagePaths[0],state.ack[0]);missing.certificate.inputs=[];const snapshot=native.loadSelection(new native.ImmutableReader(f.repo,before));assert.throws(()=>helper.acceptColdCoordinateCertificate(snapshot.geometrySources,missing.certificate,{...missing,expectedPublication:missing.publication}),/Incomplete cold/);
  const genuine=product(state.stagePaths[0],state.ack[0]),certificate=helper.acceptColdCoordinateCertificate(snapshot.geometrySources,genuine.certificate,{...genuine,expectedPublication:genuine.publication});
  const modified={...genuine,facts:{...genuine.facts,executing_commit:after},publication:structuredClone(genuine.publication)};modified.publication.facts.sha256=valueSha(modified.facts);modified.publication.facts.bytes=valueBytes(modified.facts).length;
  assert.throws(()=>helper.sealColdCoordinateCertificate(certificate,modified),/privately accepted whole product/);
 }finally{f.cleanup();}
});

test('reopened complete carry and runtime admission refuse before any cold body open',()=>{
 const f=fixture();try{const {rect,install}=sourceSides(f),before=install(rect(0,1),rect(2,3),'before'),after=install(rect(0,1.5),rect(2,3),'after'),state=issueStages(f,before,after),receipts=[validate(f,state,before,0)];receipts.push(validate(f,state,after,1,receipts));
  const original=fs.readFileSync;let opens=0;fs.readFileSync=function(...args){opens++;return original.apply(this,args);};
  try{assert.throws(()=>reopenCompleteColdPlan(native,helper,{repo:f.repo,baseline:before,candidate:after,...state,receipts,carriedBytes:Number.MAX_SAFE_INTEGER}),/Installed runtime\/metadata/);assert.equal(opens,0);
   assert.throws(()=>reopenCompleteColdPlan(native,helper,{repo:f.repo,baseline:before,candidate:after,...state,receipts,carriedBytes:1048576,context:{...state.context,runtimeBytes:Number.MAX_SAFE_INTEGER}}),/Installed runtime\/metadata/);assert.equal(opens,0);
   assert.throws(()=>reopenCompleteColdPlan(native,helper,{repo:f.repo,baseline:before,candidate:after,...state,receipts,carriedBytes:0}),/Incomplete reopened carry/);assert.equal(opens,0);
  }finally{fs.readFileSync=original;}
 }finally{f.cleanup();}
});

test('actual continuous entry emits full source inverses with independently ended acquisition stages',()=>{
 const f=fixture();try{const {rect,install}=sourceSides(f),before=install(rect(0,1),rect(2,3),'before'),after=install(rect(0,2.5),rect(2,3),'after');f.git('checkout',before);const env={...process.env};delete env.NODE_OPTIONS;delete env.NODE_PATH;
  const out=path.join(f.repo,'actual-continuous'),r=spawnSync(process.execPath,['--expose-gc',path.join(f.repo,P+'selected-continuous-entry.mjs'),'continuous',f.repo,before,before,after,out],{env,encoding:'utf8'});assert.equal(r.status,0,r.stderr);assert.match(r.stderr,/required-source-count/);assert.match(r.stderr,/coordinate-source/);assert.match(r.stderr,/required-side-selection/);const ack=JSON.parse(r.stdout),facts=JSON.parse(fs.readFileSync(path.join(out,'facts.json'))),body=JSON.parse(gunzipSync(fs.readFileSync(path.join(out,'operands.json.gz'))));
  const selectionStages=r.stderr.split('\n').filter(Boolean).map(line=>JSON.parse(line)).filter(row=>row.event==='start'&&row.selected_continuous_stage.endsWith('-selection'));
  // This non-additive fixture attempts two shortcut loads before the full path.
  // Count them honestly; additive comparisons skip that shortcut entirely.
  assert.equal(selectionStages.length,5);
  assert.equal(selectionStages.filter(row=>row.selected_continuous_stage.startsWith('shortcut-')).length,2);
  assert.equal(selectionStages.filter(row=>!row.selected_continuous_stage.startsWith('shortcut-')).length,3);
  assert.deepEqual(selectionStages.filter(row=>row.selected_continuous_stage==='required-side-selection').map(row=>row.selected),[before]);
  assert.deepEqual(ack.affected_ids,['old-owner','other-owner']);assert.equal(facts.lifecycle.filter(p=>p.kind==='complete-snapshot-bound-cold-validation').length,2);assert.equal(facts.lifecycle.filter(p=>p.kind==='complete-required-containing-source').length,2);assert.equal(facts.inverse.length,4);assert.ok(facts.lifecycle.every(p=>p.complete_phase_bytes<=268435456));assert.deepEqual(Object.keys(body.baseline).sort(),ack.affected_ids);assert.deepEqual(Object.keys(body.candidate).sort(),ack.affected_ids);
  for(const side of ['baseline','candidate'])assert.equal(fs.existsSync(path.join(out,side,'certificate.json.gz')),true);
 }finally{f.cleanup();}
});

test('sealed complete custody releases the genuine resolver and selected snapshot after the frame ends',()=>{
 const f=fixture();try{const {rect,install}=sourceSides(f),before=install(rect(0,1),rect(2,3),'before'),after=install(rect(0,1.5),rect(2,3),'after'),state=issueStages(f,before,after);
  const nativePath=path.join(f.repo,'scripts/check-effective-geographic-regression.mjs'),helperPath=path.join(f.repo,P+'selected-neighbor-prevention.mjs');
  const code=`import fs from 'node:fs';import assert from 'node:assert/strict';import {gunzipSync} from 'node:zlib';import {createHash} from 'node:crypto';import * as n from ${JSON.stringify(nativePath)};import * as h from ${JSON.stringify(helperPath)};
const [repo,selected,directory]=process.argv.slice(2),sha=b=>createHash('sha256').update(b).digest('hex');
const publication=JSON.parse(fs.readFileSync(directory+'/publication.json')),facts=JSON.parse(fs.readFileSync(directory+'/facts.json')),encoded=fs.readFileSync(directory+'/certificate.json.gz'),decoded=gunzipSync(encoded),product={publication,facts,certificate:JSON.parse(decoded),encoded_sha256:sha(encoded),decoded_sha256:sha(decoded)};
let snapshot=n.loadSelection(new n.ImmutableReader(repo,selected)),resolver=snapshot.geometrySources;const weakSnapshot=new WeakRef(snapshot),weakResolver=new WeakRef(resolver);
const certificate=h.acceptColdCoordinateCertificate(resolver,product.certificate,{...product,expectedPublication:publication});const receipt=h.sealColdCoordinateCertificate(certificate,product);snapshot=null;resolver=null;
await new Promise(r=>setImmediate(r));for(let i=0;i<3;i++){globalThis.gc();await new Promise(r=>setImmediate(r));}
assert.equal(weakSnapshot.deref(),undefined,'Private proof kept old selected snapshot live');assert.equal(weakResolver.deref(),undefined,'Private proof kept old resolver live');assert.equal(h.reopenColdCoordinateCertificate(receipt,product).entries.length,2);console.log('actual snapshot/resolver collected; complete reopened certificate preserved');`;
  const file=path.join(f.repo,'weak-lifetime.mjs');fs.writeFileSync(file,code);const result=spawnSync(process.execPath,['--expose-gc',file,f.repo,before,state.stagePaths[0]],{encoding:'utf8'});assert.equal(result.status,0,result.stderr);assert.match(result.stdout,/actually|actual snapshot\/resolver collected/);
 }finally{f.cleanup();}
});


test('ordinary Git source join authenticates whole-consumed inventory without inventing a SHA pin',()=>{
 const f=fixture();try{
  const name='source/ordinary.json',body=f.write(name,{type:'FeatureCollection',features:[{type:'Feature',id:'ordinary',properties:{},geometry:{type:'Point',coordinates:[0,0]}}]}),head=f.commit();
  const reader=new native.ImmutableReader(f.repo,head,{runtimeBytes:0,executionBytes:0}),expected={...reader.descriptor(name),kind:'ordinary-immutable-git-source'};
  assert.equal(expected.sha256,undefined);const actual=reader.read(name);assert.deepEqual(actual,body);
  const input={path:name,source:expected,bytes:actual.length,whole_body_sha256:sha(actual)},facts={inputs:[...reader.inventory.values()]};
  assert.doesNotThrow(()=>helper.validateColdSourceBody(input,expected,facts));
  for(const kind of ['missing-inventory','duplicate-inventory','wrong-inventory-OID','changed-SHA','not-whole']){
   const changed=structuredClone(facts);
   if(kind==='missing-inventory')changed.inputs=[];
   if(kind==='duplicate-inventory')changed.inputs.push(changed.inputs[0]);
   if(kind==='wrong-inventory-OID')changed.inputs[0].git_blob_oid='0'.repeat(40);
   if(kind==='changed-SHA')changed.inputs[0].sha256='0'.repeat(64);
   if(kind==='not-whole')changed.inputs[0].whole_body_consumed=false;
   assert.throws(()=>helper.validateColdSourceBody(input,expected,changed),/Missing or duplicate|Whole ordinary source/,kind);
  }
 }finally{f.cleanup();}
});

test('genuine acknowledged cold facts refuse coherent source SHA rebinding',()=>{
 const f=fixture();try{
  const {rect,install}=sourceSides(f),before=install(rect(0,1),rect(2,3),'before'),after=install(rect(0,1.2),rect(2,3),'after'),state=issueStages(f,before,after),startup=native.selectedBootstrap(f.repo,before,after),snapshot=native.loadSelection(startup.beforeReader),resolver=snapshot.geometrySources??new native.SelectedGeometrySources(snapshot),original=product(state.stagePaths[0],state.ack[0]);
  const changed=structuredClone(original);changed.certificate.inputs[0].whole_body_sha256='0'.repeat(64);changed.facts.inputs[0].sha256='0'.repeat(64);
  assert.throws(()=>helper.acceptColdCoordinateCertificate(resolver,changed.certificate,{...changed,expectedPublication:state.ack[0].publication}),/Cold facts differ from genuine acknowledged publication/);
 }finally{f.cleanup();}
});


test('same-vintage multi-source custody loads once and preserves exact independent source projections',()=>{
 const f=fixture();try{
  const {rect,install}=sourceSides(f),before=install(rect(0,1),rect(2,3),'before',{split:true}),after=install(rect(0,2.5),rect(2,3),'after',{split:true}),state=issueStages(f,before,after);
  const receipts=[validate(f,state,before,0)];receipts.push(validate(f,state,after,1,receipts));
  const closure=reopenCompleteColdPlan(native,helper,{repo:f.repo,baseline:before,candidate:after,...state,receipts,carriedBytes:2*valueBytes({context:state.context,ack:state.ack,receipts}).length});
  const loads=[],readers=[],counted={...native,loadSelection(reader){loads.push(reader.version);readers.push(reader);return native.loadSelection(reader);}};
  for(const [side,selected,i]of [['baseline',before,0],['candidate',after,1]]){
   const options={repo:f.repo,selected,names:closure.plan.source_paths[side],receipt:receipts[i],rows:closure.rows[side],inputs:closure.inputs[side],context:state.context,carriedBytes:2*valueBytes({closure,receipts}).length};
   assert.equal(options.names.length,2);
   const grouped=acquireContinuousSources(counted,helper,options);
   const independent=options.names.map(name=>acquireContinuousSource(native,helper,{...options,name}));
   assert.deepEqual(grouped.map(p=>p.features),independent.map(p=>p.features));assert.deepEqual(grouped.map(p=>p.inverse),independent.map(p=>p.inverse));
   assert(grouped[1].complete_phase_bytes>independent[1].complete_phase_bytes,'prior projections and growing inventory were not charged');
   assert(grouped[1].inputs.length>=independent[1].inputs.length);assert(grouped.every(p=>p.complete_phase_bytes<=268435456));
   assert.throws(()=>acquireContinuousSources(native,helper,{...options,names:[...options.names,'foreign.json']}),/Foreign required/);
   const wrong=structuredClone(options.inputs);wrong.find(p=>p.path===options.names[1]).whole_body_sha256='0'.repeat(64);
   assert.throws(()=>acquireContinuousSources(native,helper,{...options,inputs:wrong}),/Complete affected containing input/);
   assert.throws(()=>acquireContinuousSources(native,helper,{...options,selected:side==='baseline'?after:before}),/Reacquired selected source/);
   let reads=0;const original=native.SelectedGeometrySources.prototype.read;
   native.SelectedGeometrySources.prototype.read=function(...args){const result=original.apply(this,args);if(++reads===1)this.reader.version='f'.repeat(40);return result;};
   try{assert.throws(()=>acquireContinuousSources(native,helper,options),/selected side removed or rebound/);}finally{native.SelectedGeometrySources.prototype.read=original;}
   let opens=0;const blocked={...native,loadSelection(){opens++;throw Error('must not open');}};
   assert.throws(()=>acquireContinuousSources(blocked,helper,{...options,carriedBytes:Number.MAX_SAFE_INTEGER}),/Installed runtime\/metadata/);assert.equal(opens,0);
  }
  assert.deepEqual(loads,[before,after]);assert.notEqual(readers[0],readers[1]);
 }finally{f.cleanup();}
});

test('immutable additive selector only disables the shortcut and malformed hooks still fail the real child',()=>{
 const f=fixture();try{
  const {rect,install}=sourceSides(f),before=install(rect(0,1),rect(2,3),'before');
  const selected=JSON.parse(fs.readFileSync(path.join(f.repo,'data/ownership-selection.json')));
  f.write('data/ownership-selection.json',{...selected,additive_release:null});const after=f.commit();
  const reader=version=>new native.ImmutableReader(f.repo,version);
  assert.equal(mayUseNonAdditiveShortcut(reader(before),reader(before)),true);
  assert.equal(mayUseNonAdditiveShortcut(reader(before),reader(after)),false);
  assert.equal(mayUseNonAdditiveShortcut(reader(after),reader(before)),false);
  // A mutable working-tree selector cannot override immutable versions.
  f.write('data/ownership-selection.json',{...selected,additive_release:{forged:true}});
  assert.equal(mayUseNonAdditiveShortcut(reader(before),reader(before)),true);
  f.git('checkout','--','data/ownership-selection.json');f.git('checkout',before);
  const r=spawnSync(process.execPath,['--expose-gc',path.join(f.repo,P+'selected-continuous-entry.mjs'),'continuous',f.repo,before,before,after,path.join(f.repo,'malformed-additive')],{encoding:'utf8'});
  assert.notEqual(r.status,0);assert.match(r.stderr,/Unsupported committed additive hook/);assert.equal(r.stdout,'');
  assert.doesNotMatch(r.stderr,/shortcut-baseline-selection/);assert.match(r.stderr,/coordinate-selection/);
 }finally{f.cleanup();}
});

test('selected assembly reuses its privately authenticated source view without duplicate acquisition',()=>{
 const f=fixture();try{
  const {rect,install}=sourceSides(f),selected=install(rect(0,1),rect(2,3),'assembly-source-alias');
  const reader=new native.ImmutableReader(f.repo,selected),snapshot=native.loadSelection(reader);
  const before={used:reader.used,metadataBytes:reader.metadataBytes,inventory:[...reader.inventory]};
  const read=reader.read;reader.read=()=>assert.fail('Duplicate selected source acquisition');
  try{
   assert.equal(helper.currentRebindSourceView(snapshot),snapshot.geometrySources);
   // The authentic four-cell fixture must reach the unchanged Arctic-only
   // guard. It is not a production activation or a fabricated large snapshot.
   assert.throws(()=>assembleSupportedActivation({snapshot,
    baseAssets:{base_manifest:{},owner_roster:{}},logicalPaths:{ledger:'ledger.json',patch:'patch.json'}}),
   /Require actual selected Arctic successor/);
   assert.deepEqual({used:reader.used,metadataBytes:reader.metadataBytes,inventory:[...reader.inventory]},before);
  }finally{reader.read=read;}
 }finally{f.cleanup();}
});

test('selected assembly refuses an unauthenticated snapshot before any source acquisition',()=>{
 const f=fixture();try{
  const {rect,install}=sourceSides(f),selected=install(rect(0,1),rect(2,3),'assembly-source-forgery');
  const reader=new native.ImmutableReader(f.repo,selected),snapshot=native.loadSelection(reader);
  const read=reader.read;reader.read=()=>assert.fail('Unauthenticated source acquisition');
  try{
   for(const forged of [{...snapshot},{...snapshot,geometrySources:{...snapshot.geometrySources}}])
    assert.throws(()=>assembleSupportedActivation({snapshot:forged,
     baseAssets:{base_manifest:{},owner_roster:{}},logicalPaths:{ledger:'ledger.json',patch:'patch.json'}}),
    /Require unchanged privately authenticated selected base/);
  }finally{reader.read=read;}
 }finally{f.cleanup();}
});


test('candidate frame reuses exactly one snapshot and preserves independent complete projections',()=>{
 const f=fixture();try{
  const {rect,install}=sourceSides(f),before=install(rect(0,1),rect(2,3),'before',{split:true}),after=install(rect(0,2.5),rect(2,3),'after',{split:true}),state=issueStages(f,before,after),baselineReceipt=validate(f,state,before,0);
  const loads=[],readers=[],snapshotBytes=[],counted={...native,loadSelection(reader){loads.push(reader.version);readers.push(reader);const snapshot=native.loadSelection(reader);snapshotBytes.push(snapshot.metadataBytes);return snapshot;}};
  const options={repo:f.repo,baseline:before,candidate:after,...state,code:[],baselineReceipt,lifecycle:[]};
  const completed=acquireCandidateContinuousSources(counted,helper,options);
  assert.deepEqual(loads,[after]);assert.equal(completed.receipts[0],baselineReceipt);
  assert.deepEqual(Object.keys(completed).sort(),['closure','lifecycle','receipts','results']);
  const {closure,receipts}=completed;
  const independentlyLoaded=acquireContinuousSources(native,helper,{repo:f.repo,selected:after,names:closure.plan.source_paths.candidate,receipt:receipts[1],rows:closure.rows.candidate,inputs:closure.inputs.candidate,context:state.context,carriedBytes:2*valueBytes({closure,receipts}).length});
  assert.deepEqual(completed.results.map(r=>r.features),independentlyLoaded.map(r=>r.features));
  assert.deepEqual(completed.results.map(r=>r.inverse),independentlyLoaded.map(r=>r.inverse));
  const oldClosure=reopenCompleteColdPlan(native,helper,{repo:f.repo,baseline:before,candidate:after,...state,receipts,carriedBytes:2*valueBytes({context:state.context,ack:state.ack,receipts}).length});
  assert.deepEqual(closure.plan,oldClosure.plan);assert.deepEqual(closure.rows,oldClosure.rows);assert.deepEqual(closure.inputs,oldClosure.inputs);
  assert(closure.complete_phase_bytes-oldClosure.complete_phase_bytes>=2*snapshotBytes[0],'complete candidate snapshot must be charged during both-certificate planning');
  assert(completed.results[1].complete_phase_bytes>completed.results[0].complete_phase_bytes,'prior projection and growing inventory must remain charged');
  assert.throws(()=>acquireCandidateContinuousSources(native,helper,{...options,candidate:before}),/Foreign cold certificate/);
  assert.throws(()=>acquireCandidateContinuousSources(native,helper,{...options,baseline:after}),/baseline custody/);
  const missing=structuredClone(state.ack);missing.pop();assert.throws(()=>acquireCandidateContinuousSources(native,helper,{...options,ack:missing}),/baseline custody/);
  let sourceOpens=0;const original=native.SelectedGeometrySources.prototype.read;
  native.SelectedGeometrySources.prototype.read=function(...args){sourceOpens++;return original.apply(this,args);};
  try{
   const lowBudget={...native,ImmutableReader:class extends native.ImmutableReader{constructor(...args){super(...args);this.allowance=Object.freeze({phaseBytes:1,rssBytes:this.allowance.rssBytes});}}};
   assert.throws(()=>acquireCandidateContinuousSources(lowBudget,helper,options),/Installed runtime\/metadata/);assert.equal(sourceOpens,0);
   const blockedPlan={...helper,selectedCertificateAffectedPlan(...args){const result=helper.selectedCertificateAffectedPlan(...args);readers.at(-1).allowance=Object.freeze({phaseBytes:1,rssBytes:readers.at(-1).allowance.rssBytes});return result;}};
   assert.throws(()=>acquireCandidateContinuousSources(counted,blockedPlan,options),/Installed runtime\/metadata/);assert.equal(sourceOpens,0);
   const rebound={...helper,selectedCertificateAffectedPlan(...args){const result=helper.selectedCertificateAffectedPlan(...args);readers.at(-1).version=before;return result;}};
   assert.throws(()=>acquireCandidateContinuousSources(counted,rebound,options),/selected side removed or rebound/);assert.equal(sourceOpens,0);
  }finally{native.SelectedGeometrySources.prototype.read=original;}
  for(const alteration of ['whole-source','feature','geometry']){
   const altered={...helper,selectedCertificateAffectedPlan(...args){return helper.selectedCertificateAffectedPlan(...args);}};
   native.SelectedGeometrySources.prototype.read=function(...args){const result=original.apply(this,args);if(alteration==='whole-source')result.whole_sha256='0'.repeat(64);else if(alteration==='feature')result.collection.features[0].properties.forged=true;else result.collection.features[0].geometry.coordinates[0][1][0]+=0.125;return result;};
   try{assert.throws(()=>acquireCandidateContinuousSources(native,altered,options),/Complete affected containing input|Whole affected source record inverse/);}finally{native.SelectedGeometrySources.prototype.read=original;}
  }
 }finally{f.cleanup();}
});


test('candidate frame releases its snapshot and resolver before independent baseline acquisition',()=>{
 const f=fixture();try{
  const {rect,install}=sourceSides(f),before=install(rect(0,1),rect(2,3),'before'),after=install(rect(0,2.5),rect(2,3),'after'),state=issueStages(f,before,after);
  const code=`import assert from 'node:assert/strict';import * as n from ${JSON.stringify(path.join(f.repo,'scripts/check-effective-geographic-regression.mjs'))};import * as h from ${JSON.stringify(path.join(f.repo,P+'selected-neighbor-prevention.mjs'))};import {validatePersistedColdSide,acquireCandidateContinuousSources,acquireContinuousSources} from ${JSON.stringify(path.join(f.repo,P+'selected-continuous-entry.mjs'))};
const [repo,before,after,stateJson]=process.argv.slice(2),state=JSON.parse(stateJson),context=state.context;
const baselineReceipt=validatePersistedColdSide(n,h,{repo,selected:before,directory:state.stagePaths[0],ack:state.ack[0],context,carriedState:{context,code:[],ack:state.ack,receipts:[],lifecycle:[]}});
let weakSnapshot,weakResolver;const counted={...n,loadSelection(reader){const snapshot=n.loadSelection(reader);weakSnapshot=new WeakRef(snapshot);weakResolver=new WeakRef(snapshot.geometrySources);return snapshot;}};
const completed=acquireCandidateContinuousSources(counted,h,{repo,baseline:before,candidate:after,...state,code:[],baselineReceipt,lifecycle:[]});
await new Promise(r=>setImmediate(r));for(let i=0;i<3;i++){globalThis.gc();await new Promise(r=>setImmediate(r));}
assert.equal(weakSnapshot.deref(),undefined,'candidate frame retained selected snapshot');assert.equal(weakResolver.deref(),undefined,'candidate frame retained resolver');
const {closure,receipts}=completed,results=acquireContinuousSources(n,h,{repo,selected:before,names:closure.plan.source_paths.baseline,receipt:receipts[0],rows:closure.rows.baseline,inputs:closure.inputs.baseline,context,carriedBytes:2*h.valueBytes(completed).length});
assert.equal(results.length,1);assert.equal(completed.results.length,1);console.log('candidate snapshot/resolver collected before baseline acquisition; projections retained');`;
  const file=path.join(f.repo,'candidate-frame-lifetime.mjs');fs.writeFileSync(file,code,{flag:'wx'});
  const result=spawnSync(process.execPath,['--expose-gc',file,f.repo,before,after,JSON.stringify(state)],{encoding:'utf8'});assert.equal(result.status,0,result.stderr);assert.match(result.stdout,/candidate snapshot\/resolver collected before baseline acquisition/);
 }finally{f.cleanup();}
});

function completeFrameProbe(f,before,after,body) {
 f.git('checkout',before);
 const file=path.join(f.repo,'complete-frame-probe.mjs');
 const imports=`import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';
import * as n from ${JSON.stringify(path.join(f.repo,'scripts/check-effective-geographic-regression.mjs'))};
import * as h from ${JSON.stringify(path.join(f.repo,P+'selected-neighbor-prevention.mjs'))};
import * as entry from ${JSON.stringify(path.join(f.repo,P+'selected-continuous-entry.mjs'))};
const [repo,before,after]=process.argv.slice(2),startup=n.selectedBootstrap(repo,before,after),r=startup.beforeReader;
const context={repo,runtimeBytes:r.runtimeBytes,executionBytes:r.executionBytes,gitExecutable:r.gitExecutable,identities:startup.identities};
const options=(destination,carriedState)=>({repo,trusted:before,selected:before,destination:path.join(repo,destination),context,carriedState});
const empty=()=>({context,code:[],ack:[],receipts:[],lifecycle:[]});
`;
 fs.writeFileSync(file,imports+body,{flag:'wx'});
 const env={...process.env};delete env.NODE_OPTIONS;delete env.NODE_PATH;
 const result=spawnSync(process.execPath,['--expose-gc',file,f.repo,before,after],{env,encoding:'utf8'});
 assert.equal(result.status,0,result.stderr);return result;
}

test('complete single-vintage frames load once, preserve independent operands, and release each snapshot',()=>{
 const f=fixture();try{
  const {rect,install}=sourceSides(f),before=install(rect(0,1),rect(2,3),'before',{split:true}),after=install(rect(0,2.5),rect(2,3),'after',{split:true});
  const result=completeFrameProbe(f,before,after,`
const loads=[],weak=[];const counted={...n,loadSelection(reader){const snapshot=n.loadSelection(reader);loads.push(reader.version);weak.push([new WeakRef(snapshot),new WeakRef(snapshot.geometrySources)]);return snapshot;}};
const stagePaths=[path.join(repo,'complete-before'),path.join(repo,'complete-after')];
const old=entry.acquireCompleteColdSide(counted,h,options('complete-before',empty()));
assert.deepEqual(Object.keys(old).sort(),['ack','receipt']);
async function collected(index){await new Promise(resolve=>setImmediate(resolve));for(let i=0;i<3;i++){globalThis.gc();await new Promise(resolve=>setImmediate(resolve));}for(const ref of weak[index])assert.equal(ref.deref(),undefined,'completed single-vintage snapshot/resolver retained');}
await collected(0);
const ack=[old.ack],completed=entry.acquireCompleteCandidateSources(counted,h,{repo,trusted:before,baseline:before,candidate:after,stagePaths,ack,context,code:[],baselineReceipt:old.receipt,lifecycle:[]});
assert.deepEqual(loads,[before,after]);assert.equal(ack.length,2);await collected(1);
const {closure,receipts}=completed;
const independently=entry.acquireContinuousSources(n,h,{repo,selected:after,names:closure.plan.source_paths.candidate,receipt:receipts[1],rows:closure.rows.candidate,inputs:closure.inputs.candidate,context,carriedBytes:2*h.valueBytes(completed).length});
assert.deepEqual(completed.results.map(row=>row.features),independently.map(row=>row.features));assert.deepEqual(completed.results.map(row=>row.inverse),independently.map(row=>row.inverse));
const oldClosure=entry.reopenCompleteColdPlan(n,h,{repo,baseline:before,candidate:after,stagePaths,ack,receipts,context,carriedBytes:2*h.valueBytes({context,ack,receipts}).length});
assert.deepEqual(closure.plan,oldClosure.plan);assert.deepEqual(closure.rows,oldClosure.rows);
const baseline=entry.acquireContinuousSources(counted,h,{repo,selected:before,names:closure.plan.source_paths.baseline,receipt:receipts[0],rows:closure.rows.baseline,inputs:closure.inputs.baseline,context,carriedBytes:2*h.valueBytes(completed).length});
assert.deepEqual(loads,[before,after,before]);assert.equal(baseline.length,2);assert.equal(completed.results.length,2);
console.log('three real acquisitions; complete independent operands equal; both snapshot frames collected');`);
  assert.match(result.stdout,/three real acquisitions/);
 }finally{f.cleanup();}
});

test('coordinate helper resets retain all external custody and inventory, and refuse missing headroom before sources',()=>{
 const f=fixture();try{
  const {rect,install}=sourceSides(f),before=install(rect(0,1),rect(2,3),'before',{split:true}),after=install(rect(0,2.5),rect(2,3),'after',{split:true});
  const result=completeFrameProbe(f,before,after,`
const state=empty();state.code=[{retained:'x'.repeat(131072)}];let resets=0,joins=0,firstUsed;
const observe=reader=>{const phase=reader.phase.bind(reader);reader.phase=function(){phase();const own=this.runtimeBytes+this.executionBytes+this.metadataBytes+this.outputBytes,carry=2*h.valueBytes({carriedState:state,inventory:[...this.inventory.values()]}).length+this.coordinateResolverBytes;assert.equal(this.used,own+carry);assert(carry>262144);resets++;};};
const inspected={...h,selectedCoordinateShard(resolver,...args){if(!resets)observe(resolver.reader);const shard=h.selectedCoordinateShard(resolver,...args);if(firstUsed===undefined)firstUsed=shard.phases[0].complete_phase_bytes;else assert(shard.phases[0].complete_phase_bytes>firstUsed);return shard;},joinSelectedCoordinateCertificate(resolver,...args){const certificate=h.joinSelectedCoordinateCertificate(resolver,...args);joins++;return certificate;}};
entry.acquireCompleteColdSide(n,inspected,options('accounted',state));assert(resets>=6);assert.equal(joins,1);
let sourceOpens=0;const original=n.SelectedGeometrySources.prototype.read;n.SelectedGeometrySources.prototype.read=function(...args){sourceOpens++;return original.apply(this,args);};
try{
 const blocked={...h,selectedCoordinateShard(resolver,...args){const reader=resolver.reader,phase=reader.phase;reader.phase=function(){this.allowance=Object.freeze({phaseBytes:this.runtimeBytes+this.executionBytes+this.outputBytes+this.metadataBytes+1,rssBytes:this.allowance.rssBytes});return phase.call(this);};return h.selectedCoordinateShard(resolver,...args);}};
 assert.throws(()=>entry.acquireCompleteColdSide(n,blocked,options('blocked-carry',state)),/coordinate-frame carry/);assert.equal(sourceOpens,0);assert.equal(fs.existsSync(path.join(repo,'blocked-carry')),false);
}finally{n.SelectedGeometrySources.prototype.read=original;}
const joinState=empty();let joinsBlocked=0;
const joinBlocked={...h,joinSelectedCoordinateCertificate(resolver,...args){const reader=resolver.reader,phase=reader.phase;reader.phase=function(){const own=this.runtimeBytes+this.executionBytes+this.outputBytes+this.metadataBytes,external=2*h.valueBytes({carriedState:joinState,inventory:[...this.inventory.values()]}).length;assert(this.coordinateResolverBytes>0);this.allowance=Object.freeze({phaseBytes:own+external+1,rssBytes:this.allowance.rssBytes});joinsBlocked++;return phase.call(this);};return h.joinSelectedCoordinateCertificate(resolver,...args);}};
assert.throws(()=>entry.acquireCompleteColdSide(n,joinBlocked,options('blocked-join-resolver',joinState)),/coordinate-frame carry/);assert.equal(joinsBlocked,1);assert.equal(fs.existsSync(path.join(repo,'blocked-join-resolver')),false);
console.log('all shard/join resets carry complete metadata; external-only and join-resolver-only deficits refuse before publication');`);
  assert.match(result.stdout,/join-resolver-only deficits refuse/);
 }finally{f.cleanup();}
});

test('same-snapshot persisted custody refuses changed readback, selected identity and missing owners',()=>{
 const f=fixture();try{
  const {rect,install}=sourceSides(f),before=install(rect(0,1),rect(2,3),'before'),after=install(rect(0,2.5),rect(2,3),'after');
  const result=completeFrameProbe(f,before,after,`
const read=fs.readFileSync;let tampered=0;
fs.readFileSync=function(file,...args){const result=read.call(this,file,...args);if(String(file).endsWith('/tampered/certificate.json.gz')){tampered++;const copy=Buffer.from(result);copy[copy.length-1]^=1;return copy;}return result;};
try{assert.throws(()=>entry.acquireCompleteColdSide(n,h,options('tampered',empty())),/Whole cold product differs/);assert.equal(tampered,1);}finally{fs.readFileSync=read;}
const drifted={...h,joinSelectedCoordinateCertificate(resolver,...args){const result=h.joinSelectedCoordinateCertificate(resolver,...args);resolver.reader.version=after;return result;}};
assert.throws(()=>entry.acquireCompleteColdSide(n,drifted,options('drifted',empty())),/Selected cold side removed or rebound/);
const readSource=n.SelectedGeometrySources.prototype.read;n.SelectedGeometrySources.prototype.read=function(...args){const result=readSource.apply(this,args);result.collection.features.pop();return result;};
try{assert.throws(()=>entry.acquireCompleteColdSide(n,h,options('omitted',empty())),/Incomplete canonical source.owner roster/);assert.equal(fs.existsSync(path.join(repo,'omitted')),false);}finally{n.SelectedGeometrySources.prototype.read=readSource;}
console.log('actual generated custody rejects persisted tamper, commit drift, and missing whole-source owner');`);
  assert.match(result.stdout,/actual generated custody rejects/);
 }finally{f.cleanup();}
});

test('continuous entry requires its authenticated native-GC launch before output mutation',()=>{
 const f=fixture();try{
  const {rect,install}=sourceSides(f),before=install(rect(0,1),rect(2,3),'before');f.git('checkout',before);
  const output=path.join(f.repo,'no-native-gc'),env={...process.env};delete env.NODE_OPTIONS;delete env.NODE_PATH;
  const result=spawnSync(process.execPath,[path.join(f.repo,P+'selected-continuous-entry.mjs'),'continuous',f.repo,before,before,before,output],{env,encoding:'utf8'});
  assert.notEqual(result.status,0);assert.match(result.stderr,/authenticated native GC entry/);assert.equal(fs.existsSync(output),false);
 }finally{f.cleanup();}
});

test('complete frame charges separate resolver image metadata at the actual join reset',()=>{
 const f=fixture();try{
  const {rect,install}=sourceSides(f),before=install(rect(0,1),rect(2,3),'before',{split:true});
  const result=completeFrameProbe(f,before,before,`
const joins=[];let number=0;
for(const bytes of [0,131072]){
 const image=bytes?{index:{padding:'x'.repeat(bytes)},map:{logical_targets:[]}}:null;
 // Model the separate legacy image only after genuine immutable selection.
 // This metadata probe does not claim a new StockImage/source qualification.
 const modeled={...n,loadSelection(reader){const snapshot=n.loadSelection(reader),resolver=snapshot.geometrySources;
  const proxy=new Proxy(resolver,{get(target,key,receiver){return key==='image'?image:Reflect.get(target,key,receiver);}});
  return {...snapshot,geometrySources:proxy};}};
 const observed={...h,joinSelectedCoordinateCertificate(resolver,...args){const certificate=h.joinSelectedCoordinateCertificate(resolver,...args);joins.push(certificate.complete_phase_bytes);return certificate;}};
 entry.acquireCompleteColdSide(modeled,observed,options('image-'+number++,empty()));
}
assert(joins[1]-joins[0]>=2*131072,'separate live resolver image disappeared at join reset');
console.log(JSON.stringify({join_bytes:joins,extra_live_image_characters:131072,charged_growth:joins[1]-joins[0]}));`);
  assert.match(result.stdout,/charged_growth/);
 }finally{f.cleanup();}
});

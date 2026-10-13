import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {shuffleOwnershipBytes} from '../src/ownership-codec.js';
import {valueBytes,valueSha,coordinateBounds,validateCurrentRebindLimits} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {deriveCoordinateDelta,projectSourceFeatures,projectNativeRows,qualifyTransition} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
const MODULE='coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
const PROGRAMME='coordination/engineering/selected-geography-effective-prevention-20261009/supported-programs.json';
const CATALOGUE='coordination/engineering/selected-checkpoint-reuse-20261012/accepted-checkpoints.json';
const CODE=[MODULE,'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs','scripts/check-effective-geographic-regression.mjs','src/ownership-codec.js'];
const sha=b=>createHash('sha256').update(b).digest('hex');
const polygon=(x,y=0)=>({type:'Polygon',coordinates:[[[x,y],[x+.2,y],[x+.2,y+.2],[x,y+.2],[x,y]]]});
const feature=(id,x)=>({type:'Feature',id,properties:{id,parent_id:'parent'},geometry:polygon(x)});
function fixtures(){
 const features=[feature('A',0),feature('B',1),feature('C',5)];
 const rows=features.map((f,i)=>[f.id,i+1,'parent',1,'data/source.json',i,valueSha(f),valueSha(f.geometry),valueSha({base_geometry_sha256:valueSha(f.geometry),additions:[]}),coordinateBounds(f.geometry)]);
 return {features,certificate:{version:2,kind:'selected-coordinate-neighbor-certificate-v2',entry_fields:['id','index','parent_id','parent_index','source','ordinal','whole_feature_sha256','geometry_sha256','effective_geometry_sha256','boxes'],binding:{selection:{old:true},sources:[],owners_sha256:valueSha(rows.map(r=>r.slice(0,4)))},entries:rows,inputs:[]}};
}
function addition(id,target,index,base,x){const geometry=polygon(x);return {component_id:id,target_id:target,pixelIndex:index,base_geometry_sha256:base,geometry,geometry_sha256:valueSha(geometry)};}

test('serialized lookalikes cannot mint state or projectors',()=>{
 const state={version:1,kind:'verified-selected-state-v1',certificate:fixtures().certificate};
 assert.throws(()=>projectSourceFeatures({state,ids:['A'],budget:{}}),/private qualified/);
 assert.throws(()=>projectNativeRows({state,rows:[0],budget:{}}),/private qualified/);
 assert.throws(()=>qualifyTransition({state,reader:{},budget:{}}),/private qualified/);
});
test('append arithmetic retains all rows and discovers unchanged and changed neighbors in both vintages',()=>{
 const {certificate}=fixtures(), a=addition('a','A',1,certificate.entries[0][7],1.05), b=addition('b','C',3,certificate.entries[2][7],1.1);
 const result=deriveCoordinateDelta({certificate,oldAdditions:[],additions:[a,b],selection:{next:true}});
 assert.equal(result.certificate.entries.length,3);
 assert.strictEqual(result.certificate.entries[1],certificate.entries[1]);
 assert.deepEqual(result.plan.changed_ids,['A','C']);
 assert.deepEqual(result.plan.required_ids,['A','B','C']);
 assert.deepEqual(result.plan.pairs,[['A','B'],['A','C'],['B','C']]);
 assert.equal(result.certificate.entries[0][8],valueSha({base_geometry_sha256:certificate.entries[0][7],additions:[a]}));
 assert.deepEqual(result.certificate.entries[0][9],[[0,0,1.25,.2]]);
 assert.deepEqual(result.plan.source_bindings.baseline.selection,{old:true});
 assert.deepEqual(result.plan.source_bindings.candidate.selection,{next:true});
});
test('delta arithmetic rejects omitted old primitives, same-count owner swaps and stale base hashes',()=>{
 const {certificate}=fixtures(), old=addition('old','A',1,certificate.entries[0][7],.3);
 const before=deriveCoordinateDelta({certificate,oldAdditions:[],additions:[old],selection:{}}).certificate;
 assert.throws(()=>deriveCoordinateDelta({certificate:before,oldAdditions:[old],additions:[],selection:{}}),/Old effective/);
 assert.throws(()=>deriveCoordinateDelta({certificate:before,oldAdditions:[old],additions:[{...old,pixelIndex:2}],selection:{}}),/Old effective/);
 assert.throws(()=>deriveCoordinateDelta({certificate,oldAdditions:[],additions:[{...old,base_geometry_sha256:'0'.repeat(64)}],selection:{}}),/stale base/);
 assert.throws(()=>deriveCoordinateDelta({certificate,oldAdditions:[],additions:[{...old,geometry:polygon(20)}],selection:{}}),/changed geometry/);
 assert.throws(()=>deriveCoordinateDelta({certificate,oldAdditions:[],additions:[old,old],selection:{}}),/Duplicate/);
});

// This is a fresh miniature trusted repository, not a test-only authority hook.
// The real entry reads its ordinary committed catalogue and products exactly as
// production does. Candidate edits never control that executing catalogue.
async function trustedFixture(t,{incompleteNative=false}={}){
 const root=fs.mkdtempSync(path.join(process.cwd(),'.checkpoint-test-'));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const git=(...a)=>execFileSync('git',['-c','core.hooksPath=/dev/null','-c','user.name=Checkpoint fixture','-c','user.email=checkpoint@example.invalid','-C',root,...a],{env:{...process.env,GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_NO_LAZY_FETCH:'1'},stdio:['ignore','pipe','pipe']});
 const save=(name,value)=>{const f=path.join(root,name);fs.mkdirSync(path.dirname(f),{recursive:true});fs.writeFileSync(f,Buffer.isBuffer(value)?value:valueBytes(value));};
 const commit=()=>{git('add','.');git('commit','-qm','Checkpoint fixture');return git('rev-parse','HEAD').toString().trim();};
 git('init','-q');save(PROGRAMME,fs.readFileSync(PROGRAMME));for(const name of CODE)save(name,fs.readFileSync(name));save('package.json',{type:'module'});
 const {features,certificate}=fixtures(), source={type:'FeatureCollection',features};save('data/source.json',source);
 const reference={id:'geography:fixture',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)};
 const encode=(name,kind,values)=>{const words=Uint32Array.from(values),canonical=Buffer.from(words.buffer),encoded=gzipSync(shuffleOwnershipBytes(words));save('data/'+name,encoded);return {path:name,kind,offset:0,bytes:encoded.length,sha256:sha(encoded),decoded_bytes:canonical.length,decoded_sha256:sha(canonical),words:words.length,encoding:'byte-shuffle'};};
 const parts=[encode('native/rows.bin.gz','rows',[0,1,incompleteNative?2:1,1,2,1,3,0]),encode('native/runs.bin.gz','runs',[4,0,8,0,13,1])];
 const compressedParts=parts.map(p=>fs.readFileSync(path.join(root,'data',p.path))),whole=Buffer.concat(compressedParts),fragment=gzipSync(whole);
 save('data/transport/fragment.gz',fragment);
 const index={version:1,kind:'ordered-exact-original-byte-fragments',whole_bytes:whole.length,whole_sha256:sha(whole),files:parts.map((p,i)=>({path:p.path,mode:'100644',offset:i?parts[0].bytes:0,bytes:p.bytes,sha256:p.sha256})),parts:[{path:'fragment.gz',offset:0,bytes:fragment.length,sha256:sha(fragment),decoded_bytes:whole.length,decoded_sha256:sha(whole)}]};save('data/transport/index.json',index);
 const manifest={version:1,size:4,coordinateBits:2,method:'native-linear-evenodd-first-owner-v1',native_latitudes:[],hierarchy_sha256:reference.hierarchy_sha256,original_assets:{},parts,runWords:6,native_asset_transport:{version:1,kind:index.kind,index:{path:'data/transport/index.json',bytes:valueBytes(index).length,sha256:valueSha(index)},logical_assets:2,original_compressed_bytes:whole.length}};
 save('data/manifest.json',manifest);save('data/owners.json',[{id:'A',index:1},{id:'B',index:2},{id:'C',index:3}]);
 const primitive=addition('old','A',1,certificate.entries[0][7],.3);
 const literal={...primitive,base_geometry:features[0].geometry,disposition:'assigned',native_cells:1,source_receipt_sha256:'c'.repeat(64)};
 const originalPatch={version:1,kind:'unassigned-native-cells-v1',rows:[{y:1,runs:[[2,3,1]]}]};
 save('original/patch-one.json',originalPatch);save('original/rule.json',{version:1});const one=commit();
 const pin=(name,at=git('rev-parse','HEAD').toString().trim())=>{const body=git('show',at+':'+name),tree=git('ls-tree',at,'--',name).toString().split(/\s+/);return {commit:at,path:name,mode:tree[0],git_blob_oid:tree[2],bytes:body.length,sha256:sha(body)};};
 save('original/publication.json',{assets:[{path:'patch-one.json',bytes:pin('original/patch-one.json').bytes,sha256:pin('original/patch-one.json').sha256}]});
 const two=commit();save('original/binding.json',{native_proof:{publication:pin('original/publication.json'),assets:[pin('original/patch-one.json',one)]}});const three=commit();
 const entry={policy_id:'retained-source-literal-additions',policy_version:1,rule_preimage:pin('original/rule.json',one),rule_sha256:pin('original/rule.json',one).sha256,source_authority:pin('original/binding.json',three)};entry.authority_sha256=valueSha(entry);
 const registry={version:1,kind:'retained-rule-authority-registry-v1',entries:[entry]};save('data/registry.json',registry);
 const baseSelection={version:1,method:manifest.method,manifest_path:'data/manifest.json',sha256:pin('data/manifest.json',one).sha256,release_id:reference.id,selected_geography:{version:1,kind:'complete-world-index-with-exact-encoded-overrides',path:'data/bank.json',bytes:1,sha256:'d'.repeat(64)}};
 const target={target_id:'A',pixelIndex:1,geometry:features[0].geometry,geometry_sha256:valueSha(features[0].geometry)};
 const currentRows=[{y:1,runs:[[0,1,2]]}];
 const request={base_selection:baseSelection,authority_registry_sha256:valueSha(registry),current_targets:[target],current_rows:currentRows,original_patch_sha256s:[valueSha(originalPatch)],acquisition:{predecessor_rows:[],predecessor_proof:null,native_inputs:[]}};
 const rebind={request,result:{native:{rows:originalPatch.rows}},facts:{acquisition_phases:[]},publication:{},operating:{}};
 for(const [name,body]of Object.entries(rebind))save('accepted-rebind/'+name+'.json',body);const four=commit();
 const rc={version:1,kind:'qualified-native-additive-current-bank-rebind-v1',execution_commit:one,base_selection:baseSelection,authority_registry_sha256:valueSha(registry),...Object.fromEntries(Object.keys(rebind).map(name=>[name,pin('accepted-rebind/'+name+'.json',four)]))};save('accepted-rebind/certificate.json',rc);const five=commit();
 const ledger={version:2,kind:'native-additive-repair-ledger-v2',authority_registry_sha256:valueSha(registry),scope_ids:['old','rejected'],rows:[{...literal,authority_sha256:entry.authority_sha256},{component_id:'rejected',disposition:'rejected',reason:'complete original exception',authority_sha256:entry.authority_sha256}],parent_inventory:{components:2,roster_sha256:'e'.repeat(64)},current_rebind:pin('accepted-rebind/certificate.json',five),current_targets:[target]};save('data/ledger.json',ledger);const six=commit();
 const normalized=[{...literal,authority_sha256:entry.authority_sha256,rule_sha256:entry.rule_sha256}];
 const effective={...reference,footprints_sha256:valueSha({domain:'worldatlas-effective-native-footprints:v2',base_reference:reference,authority_registry_sha256:valueSha(registry),ledger_sha256:pin('data/ledger.json',six).sha256,components:normalized})};
 const patch={version:2,kind:'unassigned-native-cells-v1',authority_registry_sha256:valueSha(registry),ledger_sha256:pin('data/ledger.json',six).sha256,base_reference:reference,effective_reference:effective,rows:originalPatch.rows};save('data/patch.json',patch);const seven=commit();
 const assets={base_manifest:pin('data/manifest.json',one),owner_roster:pin('data/owners.json',one),ledger:pin('data/ledger.json',six),patch:pin('data/patch.json',seven)};
 const envelope={version:2,kind:'retained-native-base-plus-delta-v2',base_reference:reference,effective_reference:effective,...assets};save('data/envelope.json',envelope);const eight=commit();
 const sidecar={version:2,kind:'retained-native-additive-selection-v2',base_selection:baseSelection,authority_registry:pin('data/registry.json',four),logical_asset_map:assets,runtime_envelope:pin('data/envelope.json',eight)};save('data/sidecar.json',sidecar);const nine=commit();
 const selection={...baseSelection,additive_release:{path:'data/sidecar.json',bytes:pin('data/sidecar.json',nine).bytes,sha256:pin('data/sidecar.json',nine).sha256}};save('data/ownership-selection.json',selection);const selected=commit();
 const sourcePin={...pin('data/source.json',one),kind:'ordinary-immutable-git-source'};
 const additions=normalized.map(row=>({...row,base_geometry:target.geometry,base_geometry_sha256:target.geometry_sha256}));
 const derived=deriveCoordinateDelta({certificate,oldAdditions:[],additions,selection}).certificate;
 const full={...derived,binding:{...derived.binding,release:reference,sources:[sourcePin]},inputs:[{path:'data/source.json',source:sourcePin,whole_body_sha256:sourcePin.sha256,bytes:sourcePin.bytes}]};
 const execution_code=CODE.map(name=>pin(name,one)),runtime=[{path:process.execPath,bytes:fs.statSync(process.execPath).size,sha256:'f'.repeat(64)}];
 const facts={version:1,kind:'trusted-selected-coordinate-stage-v1',candidate_code_executed:false,selected_commit:selected,executing_commit:one,execution_code,runtime,binding:full.binding,complete_owners:3,complete_sources:1};
 const compressed=gzipSync(valueBytes(full));save('accepted/certificate.json.gz',compressed);save('accepted/facts.json',facts);
 const publication={version:1,kind:facts.kind,complete:true,facts:{path:'facts.json',bytes:valueBytes(facts).length,sha256:valueSha(facts)},certificate:{path:'certificate.json.gz',bytes:compressed.length,sha256:sha(compressed),decoded_bytes:valueBytes(full).length,decoded_sha256:valueSha(full)}};save('accepted/publication.json',publication);
 const inventory=[PROGRAMME,'data/source.json','data/manifest.json','data/owners.json','data/registry.json','data/ledger.json','data/patch.json','data/sidecar.json','data/envelope.json','data/native/rows.bin.gz','data/native/runs.bin.gz'].map(name=>pin(name,selected));
 save('accepted/custody.json',{complete_cold_custody:[{facts,publication,effective_additions:additions,inventory}]});
 save('accepted/routes.json',inventory.map(p=>p.path).sort().map(name=>({path:name,tree:git('ls-tree','-z',selected,'--',name).toString()})));const accepted=commit();
 const rootRow={id:'fixture',accepted_head:accepted,selected_commit:selected,selection_sha256:valueSha(selection),execution_commit:one,execution_code_sha256:valueSha(execution_code),runtime_sha256:valueSha(runtime),facts:pin('accepted/facts.json'),certificate:{...pin('accepted/certificate.json.gz'),decoded_bytes:valueBytes(full).length,decoded_sha256:valueSha(full)},publication:pin('accepted/publication.json'),custody:pin('accepted/custody.json'),routes:pin('accepted/routes.json')};
 save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[rootRow]});commit();
 const api=await import(pathToFileURL(path.join(root,MODULE))),native=await import(pathToFileURL(path.join(root,'scripts/check-effective-geographic-regression.mjs')));
 const reader=new native.ImmutableReader(root,selected,{allowance:{phaseBytes:512*1024**2,rssBytes:512*1024**2}}),budget={shared:reader.budget,carriedBytes:1024};
 return {api,native,reader,budget,selected,root,git,save,commit,pin,ledger,patch,sidecar,envelope,selection,rootRow};
}

test('real catalogue entry qualifies a complete state, retains exceptions and projects exact feature/native rows',async t=>{
 const f=await trustedFixture(t), result=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 assert.equal(result.available,true);const state=result.state;
 assert.equal(state.ledger.rows.length,2);assert.equal(state.ledger.rows[1].disposition,'rejected');
 const sources=f.api.projectSourceFeatures({state,ids:['A','B'],budget:f.budget});
 assert.deepEqual(sources.features.map(p=>p.id),['A','B']);assert.equal(sources.inverse.length,2);
 const native=f.api.projectNativeRows({state,rows:[1],budget:f.budget});
 assert.deepEqual(native.rows,[{y:1,runs:[[0,1,2]]}]);assert.deepEqual(native.acquired_rows,[]);
 const fresh=f.api.projectNativeRows({state,rows:[0,1,2,3],budget:f.budget});
 assert.deepEqual(fresh.rows,[{y:0,runs:[[0,1,1]]},{y:1,runs:[[0,1,2]]},{y:2,runs:[[1,2,3]]},{y:3,runs:[]}]);
 assert.deepEqual(fresh.acquired_rows,[0,2,3]);assert.ok(fresh.custody.new_whole_inputs.length>=2);
 assert.throws(()=>f.api.projectNativeRows({state:JSON.parse(JSON.stringify(state)),rows:[1],budget:f.budget}),/private qualified/);
 f.api.releaseCheckpoint(state);assert.throws(()=>f.api.projectSourceFeatures({state,ids:['A'],budget:f.budget}),/private qualified/);
});
test('unchanged actual selection at a newer commit reuses the original accepted checkpoint',async t=>{
 const f=await trustedFixture(t);f.save('unrelated.json',{new:true});const newer=f.commit();
 const reader=new f.native.ImmutableReader(f.root,newer,{allowance:f.reader.allowance}),budget={shared:reader.budget,carriedBytes:0};
 const result=f.api.qualifyCheckpoint({reader,budget});assert.equal(result.available,true);
 assert.equal(result.state.selected_commit,newer);assert.equal(result.state.accepted_execution.historical_selected_commit,f.selected);
 const transition=f.api.qualifyTransition({state:result.state,reader,budget});assert.equal(transition.available,true);
 assert.deepEqual(transition.changedIds,[]);assert.deepEqual(transition.changedNativeRows,[]);
 assert.deepEqual(transition.plan.required_ids,[]);
});
test('committed qualifier edits need no manual catalogue fingerprint refresh',async t=>{
 const f=await trustedFixture(t), catalogue=fs.readFileSync(path.join(f.root,CATALOGUE));
 fs.appendFileSync(path.join(f.root,MODULE),'\n// reviewed non-scientific change\n');const newer=f.commit();
 const reader=new f.native.ImmutableReader(f.root,newer,{allowance:f.reader.allowance}),budget={shared:reader.budget,carriedBytes:0};
 assert.equal(f.api.qualifyCheckpoint({reader,budget}).available,true);
 assert.deepEqual(fs.readFileSync(path.join(f.root,CATALOGUE)),catalogue);
});
test('changed same-count source owners cannot reuse accepted custody, and undercharged shared budgets are rejected',async t=>{
 const f=await trustedFixture(t);f.save('data/source.json',{type:'FeatureCollection',features:[feature('B',0),feature('A',1),feature('C',5)]});const candidate=f.commit();
 const reader=new f.native.ImmutableReader(f.root,candidate,{allowance:f.reader.allowance}),budget={shared:reader.budget,carriedBytes:0};
 const result=f.api.qualifyCheckpoint({reader,budget});assert.equal(result.available,false);assert.match(result.reason,/routing alternative changed/);
 assert.throws(()=>f.api.qualifyCheckpoint({reader,budget:{shared:{},carriedBytes:0}}),/actual shared/);
 assert.throws(()=>f.api.qualifyCheckpoint({reader,budget:{shared:reader.budget,carriedBytes:-1}}),/caller-carried/);
});
test('corrupt accepted products and dirty executing code are rejected rather than treated as no change',async t=>{
 const f=await trustedFixture(t);f.rootRow.certificate.decoded_sha256='0'.repeat(64);
 f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[f.rootRow]});f.commit();
 assert.throws(()=>f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget}),/decoded output is corrupt/);
 f.save(MODULE,Buffer.concat([fs.readFileSync(path.join(f.root,MODULE)),Buffer.from('\n// drift\n')]));
 const reader=new f.native.ImmutableReader(f.root,f.selected,{allowance:f.reader.allowance});
 assert.throws(()=>f.api.qualifyCheckpoint({reader,budget:{shared:reader.budget,carriedBytes:0}}),/changed executing checkpoint method/);
});

test('native projection rejects an incomplete complete row partition despite matching encoded and decoded hashes',async t=>{
 const f=await trustedFixture(t,{incompleteNative:true}),result=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 assert.equal(result.available,true);
 assert.throws(()=>f.api.projectNativeRows({state:result.state,rows:[2],budget:f.budget}),/row partition omitted/);
});
test('a forged candidate-selected checkpoint catalogue cannot replace trusted execution authority',async t=>{
 const f=await trustedFixture(t);const original=f.git('rev-parse','HEAD').toString().trim();
 f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[]});const candidate=f.commit();
 f.git('checkout','-q',original);
 const reader=new f.native.ImmutableReader(f.root,candidate,{allowance:f.reader.allowance}),budget={shared:reader.budget,carriedBytes:0};
 assert.equal(f.api.qualifyCheckpoint({reader,budget}).available,true);
});

function candidateProducts(f,{ledger=f.ledger,patch=f.patch}={}){
 f.save('candidate/ledger.json',ledger);const l=f.commit();
 patch={...patch,ledger_sha256:f.pin('candidate/ledger.json',l).sha256};f.save('candidate/patch.json',patch);const p=f.commit();
 const assets={...f.sidecar.logical_asset_map,ledger:f.pin('candidate/ledger.json',l),patch:f.pin('candidate/patch.json',p)};
 f.save('candidate/envelope.json',{...f.envelope,...assets});const e=f.commit();
 f.save('candidate/sidecar.json',{...f.sidecar,logical_asset_map:assets,runtime_envelope:f.pin('candidate/envelope.json',e)});const sc=f.commit();
 const side=f.pin('candidate/sidecar.json',sc);
 f.save('data/ownership-selection.json',{...f.selection,additive_release:{path:side.path,bytes:side.bytes,sha256:side.sha256}});return f.commit();
}
test('actual transition rejects missing complete exception records and native owner reassignment',async t=>{
 const f=await trustedFixture(t), result=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 const ledger={...f.ledger,scope_ids:['old'],rows:[f.ledger.rows[0]]};
 const candidate=candidateProducts(f,{ledger});
 const reader=new f.native.ImmutableReader(f.root,candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
 assert.throws(()=>f.api.qualifyTransition({state:result.state,reader,budget:f.budget}),/Old complete ledger/);
 f.reader.used=0;
 assert.throws(()=>f.api.projectNativeRows({state:result.state,rows:[1],budget:f.budget}),/reset or undercharged/);
});
test('actual transition rejects same-count changed native ownership without reacquiring original science',async t=>{
 const f=await trustedFixture(t), result=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 const candidate=candidateProducts(f,{patch:{...f.patch,rows:[{y:1,runs:[[2,3,2]]}]}});
 const reader=new f.native.ImmutableReader(f.root,candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
 assert.throws(()=>f.api.qualifyTransition({state:result.state,reader,budget:f.budget}),/omitted, invented or reassigned/);
});
test('actual transition refuses a stale base and preserves the usable baseline for candidate-only cold validation',async t=>{
 const f=await trustedFixture(t), result=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 f.save('candidate/sidecar.json',{...f.sidecar,base_selection:{...f.sidecar.base_selection,release_id:'geography:new'}});const a=f.commit(),p=f.pin('candidate/sidecar.json',a);
 f.save('data/ownership-selection.json',{...f.selection,release_id:'geography:new',additive_release:{path:p.path,bytes:p.bytes,sha256:p.sha256}});const candidate=f.commit();
 const reader=new f.native.ImmutableReader(f.root,candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
 const transition=f.api.qualifyTransition({state:result.state,reader,budget:f.budget});
 assert.equal(transition.available,false);assert.equal(transition.cold,'candidate');assert.strictEqual(transition.baseline,result.state);
});

test('private source reuse snapshots caller scope and admits each external carry increase before returning',async t=>{
 const f=await trustedFixture(t),{state}=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 const ids=['A'],projection=f.api.projectSourceFeatures({state,ids,budget:f.budget});
 ids[0]='B';assert.throws(()=>f.api.projectSourceFeatures({state,ids:['B'],budget:f.budget,reuse:projection}),/incomplete source projection reuse/);
 const initial=f.budget.carriedBytes;f.budget.carriedBytes+=4096;
 const used=f.reader.used;
 const reused=f.api.projectSourceFeatures({state,ids:['A'],budget:f.budget,reuse:projection});
 assert.equal(reused.features[0].id,'A');assert.equal(f.reader.used,used+4096);
 f.budget.carriedBytes=initial;
 assert.throws(()=>f.api.projectSourceFeatures({state,ids:['A'],budget:f.budget,reuse:projection}),/reset or undercharged/);
 f.budget.carriedBytes=f.reader.phaseLimit;
 assert.throws(()=>f.api.projectSourceFeatures({state,ids:['A'],budget:f.budget,reuse:projection}),/External carried-state increase/);
});
test('fast selection admission rejects unknown patch fields and malformed complete effective references',async t=>{
 const f=await trustedFixture(t),{state}=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 const candidate=candidateProducts(f,{patch:{...f.patch,unexpected_permission:true}});
 const reader=new f.native.ImmutableReader(f.root,candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
 assert.throws(()=>f.api.qualifyTransition({state,reader,budget:f.budget}),/complete native patch schema/);
});

test('an unchanged accepted current-rebind proof cannot excuse a coherently repinned omitted target roster',async t=>{
 const f=await trustedFixture(t),{state}=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 const candidate=candidateProducts(f,{ledger:{...f.ledger,current_targets:[]}});
 const reader=new f.native.ImmutableReader(f.root,candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
 assert.throws(()=>f.api.qualifyTransition({state,reader,budget:f.budget}),/Ledger complete current target roster differs/);
});
test('coherently copied malformed geography references still fail exact fast-path admission',async t=>{
 const f=await trustedFixture(t),{state}=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 const effective={...f.patch.effective_reference};delete effective.id;
 f.envelope={...f.envelope,effective_reference:effective};
 const candidate=candidateProducts(f,{patch:{...f.patch,effective_reference:effective}});
 const reader=new f.native.ImmutableReader(f.root,candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
 assert.throws(()=>f.api.qualifyTransition({state,reader,budget:f.budget}),/complete effective reference/);
});


test('consumer admission authenticates the private complete transition rather than a forged scope wrapper',async t=>{
 const f=await trustedFixture(t),{state}=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 const reader=new f.native.ImmutableReader(f.root,f.selected,{allowance:f.reader.allowance,budget:f.reader.budget});
 const transition=f.api.qualifyTransition({state,reader,budget:f.budget});
 assert.equal(transition.available,true);
 assert.equal(f.api.authenticateTransition({transition,budget:f.budget}),transition);
 assert.throws(()=>transition.changedNativeRows.push(1),TypeError);
 assert.throws(()=>transition.plan.required_ids.push('omitted-neighbor'),TypeError);
 for(const forged of [{...transition},{...transition,plan:{...transition.plan,required_ids:[],pairs:[]}},{...transition,changedNativeRows:[]},JSON.parse(JSON.stringify(transition))])
  assert.throws(()=>f.api.authenticateTransition({transition:forged,budget:f.budget}),/private qualified selected transition/);
 f.api.releaseCheckpoint(state);
 assert.throws(()=>f.api.authenticateTransition({transition,budget:f.budget}),/private qualified selected transition/);
});


test('trusted programme policy evolves independently of unchanged selected scientific routes',async t=>{
 const f=await trustedFixture(t), originalPolicy=JSON.parse(fs.readFileSync(path.join(f.root,PROGRAMME)));
 const extra=structuredClone(originalPolicy.programs.at(-1));extra.source_profile='reviewed-fixture-policy';
 f.save(PROGRAMME,{...originalPolicy,programs:[...originalPolicy.programs,extra]});const newer=f.commit();
 const reader=new f.native.ImmutableReader(f.root,newer,{allowance:f.reader.allowance}),budget={shared:reader.budget,carriedBytes:0};
 const result=f.api.qualifyCheckpoint({reader,budget});assert.equal(result.available,true);
 const forged=structuredClone(extra);forged.source_profile='candidate-only-unknown-producer';
 f.save(PROGRAMME,{...originalPolicy,programs:[...originalPolicy.programs,extra,forged]});const candidate=f.commit();
 f.git('checkout','-q',newer);
 const after=new f.native.ImmutableReader(f.root,candidate,{allowance:reader.allowance,budget:reader.budget});
 const transition=f.api.qualifyTransition({state:result.state,reader:after,budget});assert.equal(transition.available,true);
 assert.deepEqual(transition.changedIds,[]);
 const helper=await import(pathToFileURL(path.join(f.root,CODE[1])));
 assert.throws(()=>helper.readSupportedProgrammeAuthority(after,{preimageVersion:forged.preimage_version,
  sourceProfile:forged.source_profile,sourceCode:forged.source_executed_code,nativeCode:forged.native_executed_code}),/Unknown\/ambiguous/);
});
test('policy-route exception never permits an incomplete archived census or adjacent input drift',async t=>{
 const f=await trustedFixture(t), original=f.git('rev-parse','HEAD').toString().trim();
 const routes=JSON.parse(f.git('show',f.rootRow.routes.commit+':'+f.rootRow.routes.path));
 f.save('accepted/routes.json',routes.filter(p=>p.path!==PROGRAMME));const incomplete=f.commit();
 f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',
  checkpoints:[{...f.rootRow,routes:f.pin('accepted/routes.json',incomplete)}]});f.commit();
 assert.throws(()=>f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget}),/Incomplete trusted present\/absent route census/);
 f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',
  checkpoints:[{...f.rootRow,routes:{...f.rootRow.routes,sha256:'0'.repeat(64)}}]});f.commit();
 const corruptReader=new f.native.ImmutableReader(f.root,f.selected,{allowance:f.reader.allowance});
 assert.throws(()=>f.api.qualifyCheckpoint({reader:corruptReader,budget:{shared:corruptReader.budget,carriedBytes:0}}),/Whole immutable input differs/);
 f.git('checkout','-q',original);
 f.save('data/owners.json',[{id:'B',index:1},{id:'A',index:2},{id:'C',index:3}]);const changed=f.commit();
 const reader=new f.native.ImmutableReader(f.root,changed,{allowance:f.reader.allowance}),budget={shared:reader.budget,carriedBytes:0};
 const result=f.api.qualifyCheckpoint({reader,budget});assert.equal(result.available,false);assert.match(result.reason,/routing alternative changed/);
});


test('removed or changed trusted producer eligibility cannot silently reuse accepted policy',async t=>{
 const f=await trustedFixture(t), original=f.git('rev-parse','HEAD').toString().trim();
 const policy=JSON.parse(fs.readFileSync(path.join(f.root,PROGRAMME)));
 for(const edit of [p=>p.programs.pop(),p=>p.current_rebind_migrations.pop(),p=>{p.programs[0].source_executed_code[0].sha256='0'.repeat(64);}]){
  f.git('checkout','-q',original);const changed=structuredClone(policy);edit(changed);f.save(PROGRAMME,changed);f.commit();
  const reader=new f.native.ImmutableReader(f.root,f.selected,{allowance:f.reader.allowance}),budget={shared:reader.budget,carriedBytes:0};
  const result=f.api.qualifyCheckpoint({reader,budget});assert.equal(result.available,false);assert.match(result.reason,/preserves accepted eligibility/);
 }
});


test('archived child custody is retained in its actual parent inventory without crossing invocations',async t=>{
 const f=await trustedFixture(t), first=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});assert.equal(first.available,true);
 for(const p of [f.rootRow.facts,f.rootRow.certificate,f.rootRow.custody,f.rootRow.routes]){
  const actual=f.reader.inventory.get(p.commit+':'+p.path);assert.ok(actual?.whole_body_consumed);assert.equal(actual.sha256,p.sha256);
 }
 assert.ok([...f.reader.inventory.values()].some(p=>p.path===CATALOGUE&&p.whole_body_consumed));
 const secondReader=new f.native.ImmutableReader(f.root,f.selected,{allowance:f.reader.allowance});
 assert.notStrictEqual(secondReader.inventory,f.reader.inventory);assert.equal(secondReader.inventory.size,0);
 const secondBudget={shared:secondReader.budget,carriedBytes:0};
 const second=f.api.qualifyCheckpoint({reader:secondReader,budget:secondBudget});assert.equal(second.available,true);
 assert.notStrictEqual(secondReader.inventory,f.reader.inventory);
 f.api.releaseCheckpoint(first.state);assert.deepEqual(f.api.projectNativeRows({state:second.state,rows:[1],budget:secondBudget}).rows,[{y:1,runs:[[0,1,2]]}]);
});


test('accepted AUS producer limits retain canonical optional log bounds and reject nearby unsupported admission',()=>{
 // Exact limits from accepted40d792b2 request, pinned by the AUS advance-002
 // rebind certificate1b4e5c60. The ordinary output cap is checked at the call.
 const limits={complete_phase_bytes:536870912,descriptors:512,monitor_bytes:4194304,
  output_bytes:16777216,rss_bytes:805306368,sampled_stop_bytes:704643072,
  stderr_bytes:40960,stdout_bytes:8192,wall_seconds:1200};
 assert.strictEqual(validateCurrentRebindLimits(limits),limits);
 const legacy={...limits};delete legacy.monitor_bytes;delete legacy.stderr_bytes;delete legacy.stdout_bytes;
 assert.strictEqual(validateCurrentRebindLimits(legacy),legacy);
 for(const edit of [x=>{x.unreviewed_bytes=1;},x=>{delete x.complete_phase_bytes;},x=>{x.monitor_bytes=0;},
  x=>{x.stderr_bytes=33554433;},x=>{x.stdout_bytes=1.5;},x=>{x.descriptors=513;},
  x=>{x.sampled_stop_bytes=x.rss_bytes+1;},x=>{x.output_bytes=Number.MAX_SAFE_INTEGER;}]){
  const bad={...limits};edit(bad);assert.throws(()=>validateCurrentRebindLimits(bad));
 }
});

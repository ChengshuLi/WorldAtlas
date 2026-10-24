import assert from 'node:assert/strict';
import {after} from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import {gzipSync,gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {shuffleOwnershipBytes} from '../../src/ownership-codec.js';
import {nativeRowLatitudes} from '../../src/native-grid.js';
import {valueBytes,valueSha,coordinateBounds,mergeCompletedNativePatches} from '../../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {mapCellSelectionFixture} from './map-cell-selection.mjs';
import {JOINT_CODE} from '../../coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs';
const MODULE='coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
const CODE=[MODULE,'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs','scripts/native-word-store.mjs','scripts/native-patch-store.mjs','scripts/check-effective-geographic-regression.mjs',
  'scripts/selected-reference-metadata.mjs','src/reference-metadata.js','src/native-grid.js','src/ownership-codec.js','scripts/package-startup-ownership.mjs','src/ownership-assets.js','src/ownership-method.js'];
const sha=b=>createHash('sha256').update(b).digest('hex');
const polygon=(x,y=0)=>({type:'Polygon',coordinates:[[[x,y],[x+.2,y],[x+.2,y+.2],[x,y+.2],[x,y]]]});
const feature=(id,x)=>({type:'Feature',id,properties:{id,parent_id:'parent'},geometry:polygon(x)});
function fixtures(sourceFeatures){
 const features=structuredClone(sourceFeatures??[feature('A',0),feature('B',1),feature('C',5)]);
 const rows=features.map((f,i)=>[f.id,i+1,'parent',1,'data/source.json',i,valueSha(f),valueSha(f.geometry),valueSha({base_geometry_sha256:valueSha(f.geometry),additions:[]}),coordinateBounds(f.geometry)]);
 return {features,certificate:{version:2,kind:'selected-coordinate-neighbor-certificate-v2',entry_fields:['id','index','parent_id','parent_index','source','ordinal','whole_feature_sha256','geometry_sha256','effective_geometry_sha256','boxes'],binding:{selection:{old:true},sources:[],owners_sha256:valueSha(rows.map(r=>r.slice(0,4)))},entries:rows,inputs:[]}};
}
function addition(id,target,index,base,x){const geometry=polygon(x);return {component_id:id,target_id:target,pixelIndex:index,base_geometry_sha256:base,geometry,geometry_sha256:valueSha(geometry)};}

// Each consumer owns its complete physical repository and mutable helpers.
function fixtureRepository(root){
 const git=(...a)=>execFileSync('git',['-c','core.hooksPath=/dev/null','-c','user.name=Checkpoint fixture','-c','user.email=checkpoint@example.invalid','-C',root,...a],{env:{...process.env,GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_NO_LAZY_FETCH:'1'},maxBuffer:33554433,stdio:['ignore','pipe','pipe']});
 const save=(name,value)=>{const f=path.join(root,name);fs.mkdirSync(path.dirname(f),{recursive:true});fs.writeFileSync(f,Buffer.isBuffer(value)?value:valueBytes(value));};
 const commit=()=>{git('add','.');git('commit','-qm','Checkpoint fixture');return git('rev-parse','HEAD').toString().trim();};
 const pin=(name,at=git('rev-parse','HEAD').toString().trim())=>{const body=git('show',at+':'+name),tree=git('ls-tree',at,'--',name).toString().split(/\s+/);return {commit:at,path:name,mode:tree[0],git_blob_oid:tree[2],bytes:body.length,sha256:sha(body)};};
 return {root,git,save,commit,pin};
}

// Keep the original miniature history construction in one private seed for each
// normalized option set. No consumer imports a seed module or receives its data.
// Seeds live only for this Node test invocation; copies never share Git objects.
const trustedSeeds=new Map();
after(()=>{for(const seed of trustedSeeds.values())fs.rmSync(seed.root,{recursive:true,force:true});});

function buildTrustedSeed(root,{incompleteNative,codeRoutes,nativeAppend,nativeConsumer,sourceOverride,physicalLogicalSource,originalPatchRows,overrideLogicalPath,nativeLayout,sourceFeatures,finalBank,packageRoles}){
 const {git,save,commit,pin}=fixtureRepository(root);
 git('init','-q');if(codeRoutes)save('data/scientific.js',{fixture:'scientific input, not executed code'});for(const name of new Set([...CODE,...(finalBank?JOINT_CODE:[])]))save(name,fs.readFileSync(name));save('package.json',{type:'module'});
 const {features,certificate}=fixtures(sourceFeatures), source={type:'FeatureCollection',features};save('data/source.json',source);
 if(sourceOverride)save('data/selected-source.json.gz',gzipSync(valueBytes(source)));
 const reference={id:'geography:fixture',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)};
 const encode=(name,kind,values,offset=0)=>{const words=Uint32Array.from(values),canonical=Buffer.from(words.buffer),encoded=gzipSync(shuffleOwnershipBytes(words));save('data/'+name,encoded);return {path:name,kind,offset,bytes:encoded.length,sha256:sha(encoded),decoded_bytes:canonical.length,decoded_sha256:sha(canonical),words:words.length,encoding:'byte-shuffle'};};
 const size=nativeLayout?.size??(nativeAppend?262166:4),coordinateBits=Math.ceil(Math.log2(size));
 const table=nativeLayout?.rows??(nativeAppend?Array.from({length:size*2},(_,i)=>i%2?0:3):[0,1,incompleteNative?2:1,1,2,1,3,0]);
 if(nativeAppend&&!nativeLayout)table.splice(0,6,0,1,1,1,2,1);
 const runs=nativeLayout?.runs??[2**coordinateBits,0,2*2**coordinateBits,0,3*2**coordinateBits+1,1];
 const partWords=nativeLayout?.runPartWords??runs.length;
 if(!Number.isSafeInteger(partWords)||partWords<=0||partWords%2)throw Error('Fixture requires complete positive run-word partitions');
 const parts=[encode(finalBank?'native-v1/ownership/rows-0.bin.gz':'native/rows.bin.gz','rows',table)];
 for(let offset=0;offset<runs.length;offset+=partWords)
  parts.push(encode(finalBank?`native-v1/ownership/runs-${offset}.bin.gz`:nativeLayout?`native/runs-${offset}.bin.gz`:'native/runs.bin.gz','runs',runs.slice(offset,offset+partWords),offset));
 const compressedParts=parts.map(p=>fs.readFileSync(path.join(root,'data',p.path))),whole=Buffer.concat(compressedParts),fragment=gzipSync(whole);
 save('data/transport/fragment.gz',fragment);
 let assetOffset=0;
 const index={version:1,kind:'ordered-exact-original-byte-fragments',whole_bytes:whole.length,whole_sha256:sha(whole),files:parts.map(p=>{const offset=assetOffset;assetOffset+=p.bytes;return {path:p.path,mode:'100644',offset,bytes:p.bytes,sha256:p.sha256};}),parts:[{path:'fragment.gz',offset:0,bytes:fragment.length,sha256:sha(fragment),decoded_bytes:whole.length,decoded_sha256:sha(whole)}]};save('data/transport/index.json',index);
 const manifest={version:1,size,coordinateBits,method:'native-linear-evenodd-first-owner-v1',native_latitudes:[],hierarchy_sha256:reference.hierarchy_sha256,original_assets:{},parts,runWords:runs.length,native_asset_transport:{version:1,kind:index.kind,index:{path:'data/transport/index.json',bytes:valueBytes(index).length,sha256:valueSha(index)},logical_assets:parts.length,original_compressed_bytes:whole.length}};
 const owners=features.map((feature,index)=>({id:feature.id,index:index+1}));
 if(!nativeConsumer)save('data/owners.json',owners);
 if(nativeAppend){
  const latitudes=nativeRowLatitudes(size),bytes=Buffer.alloc(size*8);
  latitudes.forEach((v,i)=>bytes.writeDoubleLE(v,i*8));save('original/latitudes.f64le.gz',gzipSync(bytes));
  const initial=commit(),body=git('show',initial+':original/latitudes.f64le.gz'),tree=git('ls-tree',initial,'--','original/latitudes.f64le.gz').toString().split(/\s+/);
  manifest.native_latitudes={root:'repository',commit:initial,path:'original/latitudes.f64le.gz',mode:tree[0],git_blob_oid:tree[2],bytes:body.length,sha256:sha(body),decoded_bytes:bytes.length,decoded_sha256:sha(bytes)};
  if(finalBank){
    const name='coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz';
    const encoded=fs.readFileSync(name),decoded=gunzipSync(encoded);save(name,encoded);const at=commit();
    manifest.version=2;manifest.footprints_sha256=reference.footprints_sha256;manifest.geographic_release=reference.id;
    manifest.native_latitudes={root:'repository',role:'immutable-normative-rule-input',...pin(name,at),decoded_bytes:decoded.length,decoded_sha256:sha(decoded)};
  }
  manifest.original_assets={bounds:{sha256:sha(fs.readFileSync(path.join(root,'data/owners.json')))}};
 }
 if(nativeConsumer){
  const bytes=Buffer.alloc(size*8);nativeRowLatitudes(size).forEach((v,i)=>bytes.writeDoubleLE(v,i*8));
  const encoded=gzipSync(bytes);save('data/latitudes.f64le.gz',encoded);const at=commit();
  manifest.native_latitudes={root:'repository',commit:at,path:'data/latitudes.f64le.gz',bytes:encoded.length,sha256:sha(encoded),decoded_bytes:bytes.length,decoded_sha256:sha(bytes)};
  save('data/owners.json',owners);
 }
 save('data/manifest.json',manifest);
 if(finalBank){
  save('data/world-index.json',{parts:['source.json']});save('data/hierarchy.json',{fixture:'unchanged hierarchy'});
  save('data/canonical-grid/manifest.json',manifest);save('data/geographic-releases/index.json',{releases:[]});
  const release={reference};save('data/geographic-releases/fixture.json',release);
  save('data/geographic-releases/current-manifest.json',{path:'fixture.json',sha256:valueSha(release)});
 }

 const primitive=addition('old','A',1,certificate.entries[0][7],.3);
 const literal={...primitive,base_geometry:features[0].geometry,disposition:'assigned',native_cells:1,source_receipt_sha256:'c'.repeat(64)};
 const originalPatch={version:1,kind:'unassigned-native-cells-v1',rows:originalPatchRows??[{y:1,runs:[[2,3,1]]}]};
 save('original/patch-one.json',originalPatch);save('original/rule.json',{version:1});const one=commit();
 save('original/publication.json',{assets:[{path:'patch-one.json',bytes:pin('original/patch-one.json').bytes,sha256:pin('original/patch-one.json').sha256}]});
 const two=commit();let packageBinding={};
 if(packageRoles){for(const name of ['source-publication','source-inventory','source-operating','native-inventory','native-operating'])save('original/'+name+'.json',{});const metadata=commit();
  const inputs=['source-publication','source-inventory','source-operating'].map(name=>pin('original/'+name+'.json',metadata));
  save('original/native-request.json',{additive:{publication_path:inputs[0].path,inventory_path:inputs[1].path,operating_path:inputs[2].path,inputs}});const requestAt=commit();
  packageBinding={original_pins:{native_request:pin('original/native-request.json',requestAt)},inventory:pin('original/native-inventory.json',metadata),operating:pin('original/native-operating.json',metadata)};}
 save('original/binding.json',{...(packageRoles?{original_pins:packageBinding.original_pins}:{}),native_proof:{publication:pin('original/publication.json'),assets:[pin('original/patch-one.json',one)],...(packageRoles?{inventory:packageBinding.inventory,operating:packageBinding.operating}:{})}});const three=commit();
 const entry={policy_id:'retained-source-literal-additions',policy_version:1,rule_preimage:pin('original/rule.json',one),rule_sha256:pin('original/rule.json',one).sha256,source_authority:pin('original/binding.json',three)};entry.authority_sha256=valueSha(entry);
 const registry={version:1,kind:'retained-rule-authority-registry-v1',entries:[entry]};save('data/registry.json',registry);
 const baseSelection={version:1,...(finalBank?{artifact_consumption:{fixture:'accepted immutable source inventory'}}:{}),method:manifest.method,manifest_path:'data/manifest.json',sha256:pin('data/manifest.json',one).sha256,release_id:reference.id,selected_geography:{version:1,kind:'complete-world-index-with-exact-encoded-overrides',path:'data/bank.json',bytes:1,sha256:'d'.repeat(64)}};
 const target={target_id:'A',pixelIndex:1,geometry:features[0].geometry,geometry_sha256:valueSha(features[0].geometry)};
 const currentRows=[{y:1,runs:[[0,1,2]]}];
 const request={base_selection:baseSelection,authority_registry_sha256:valueSha(registry),current_targets:[target],current_rows:currentRows,original_patch_sha256s:[valueSha(originalPatch)],acquisition:{predecessor_rows:[],predecessor_proof:null,native_inputs:[]}};
 const rebind={request,result:{native:{rows:originalPatch.rows}},facts:{acquisition_phases:[]},publication:{},operating:packageRoles?{execution_custody:{}}:{}};
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

 return {root,data:{selected,ledger,patch,sidecar,envelope,selection,manifest,features,registry}};
}

// The real entry reads each independent copy's ordinary committed catalogue and
// products. Qualification, readers and private module state are always fresh.
async function trustedFixture(t,{incompleteNative=false,codeRoutes=false,nativeAppend=false,nativeConsumer=false,sourceOverride=false,physicalLogicalSource=false,originalPatchRows,overrideLogicalPath='data/source.json',nativeLayout,sourceFeatures,finalBank=false,packageRoles=false}={}){
 // Snapshot caller-owned rows before both keying and building the private seed.
 const options={incompleteNative,codeRoutes,nativeAppend,nativeConsumer,sourceOverride,physicalLogicalSource,finalBank,packageRoles,
  originalPatchRows:structuredClone(originalPatchRows??[{y:1,runs:[[2,3,1]]}]),overrideLogicalPath,nativeLayout:structuredClone(nativeLayout??null),sourceFeatures:structuredClone(sourceFeatures??null)};
 const key=JSON.stringify(options);
 let seed=finalBank?null:trustedSeeds.get(key);
 if(!seed){
  const root=fs.mkdtempSync(path.join(process.cwd(),'.checkpoint-seed-'));
  try{seed=buildTrustedSeed(root,options);if(finalBank)t.after(()=>fs.rmSync(root,{recursive:true,force:true}));else trustedSeeds.set(key,seed);}
  catch(error){fs.rmSync(root,{recursive:true,force:true});throw error;}
 }
 const root=fs.mkdtempSync(path.join(process.cwd(),'.checkpoint-test-'));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 fs.cpSync(seed.root,root,{recursive:true});
 const data=structuredClone(seed.data);
 const api=await import(pathToFileURL(path.join(root,MODULE))),native={...await import(pathToFileURL(path.join(root,'scripts/check-effective-geographic-regression.mjs')))};
 const reader=new native.ImmutableReader(root,data.selected);
 return {...data,...fixtureRepository(root),api,native,reader};
}

// Genuine pinned source/native qualification, followed by the public private-state
// admission and transition. The full lattice is a two-MiB normative input, while
// the proposed and projected repair is one cell; no research result is invented.
async function appendNativeAuthority(f,{owner=0,targetOwners,name='appended',completedConstructor=false,mutateConstructor=()=>{},nativePatchRows,mutateEvidence=()=>{},mutateLedger=()=>{},mutatePatch=()=>{},duplicateAuthority=false,membershipPath='data/geography/part-0.json'}={}) {
 const family='gb:TST:ADM2',latitudes=nativeRowLatitudes(f.manifest.size);
 const requested=(targetOwners??[owner]).map(owner=>{
  const feature=f.features[owner],bounds=coordinateBounds(feature.geometry)[0],target=family+':'+feature.id;
  const y=latitudes.findIndex(v=>v<(bounds[1]+bounds[3])/2),x=Math.floor(((bounds[0]+bounds[2])/2+180)/360*f.manifest.size);
  return {owner,feature,target,y,x};
 });
 const {y,x}=requested[0];
 const raw={type:'FeatureCollection',features:f.features.map(p=>({type:'Feature',properties:{shapeID:p.id},geometry:p.geometry}))};
 f.save(name+'/source.json',raw);
 f.save('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',{
  products:[{key:family,parts:[{path:name+'/source.json',bytes:valueBytes(raw).length,sha256:valueSha(raw)}],
   feature_count:raw.features.length,original_bytes:valueBytes(raw).length,original_sha256:valueSha(raw)}]});
 f.save(name+'/physical.json',{results:requested.map(({target,feature})=>({target,issues:[],support:{mapped_land_support:feature.geometry}}))});
 f.save(name+'/measured.json',requested.map(({target,feature})=>({target,consumed:{geometry:feature.geometry},selected:{id:feature.id,geometry:feature.geometry}})));
 f.save(name+'/physical.py',Buffer.from('# immutable bounded fixture\n'));
 f.save('data/world-index.json',{parts:[membershipPath.slice('data/'.length)]});
 f.save('data/semantic-report.json',{changes:f.features.map(p=>({id:p.id,replaces:[family+':'+p.id]}))});
 f.save(membershipPath,{type:'FeatureCollection',features:f.features.map(p=>({...p,
  properties:{...p.properties,metadata:{source_member_ids:[family+':'+p.id]}}}))});
 f.save(name+'/native-patch.json',{rows:nativePatchRows===undefined?mergeCompletedNativePatches(requested.map(({owner,x,y})=>({rows:[{y,runs:[[x,x+1,owner+1]]}]})),f.manifest.size):structuredClone(nativePatchRows)});const originals=f.commit();
 const physicalEvidence=f.pin(name+'/physical.json',originals);
 const evidence={version:1,kind:'source-target-native-evidence-v1',
  catalogue:f.pin('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',originals),
  owner_roster:f.pin('data/owners.json',originals),physical_evidence:physicalEvidence,
  physical_input:f.pin(name+'/measured.json',originals),physical_reproduction:f.pin(name+'/physical.py',originals),
  native_latitudes:f.manifest.native_latitudes,
  native_contract:Object.fromEntries(['size','coordinateBits','method','native_latitudes','hierarchy_sha256','original_assets'].map(k=>[k,f.manifest[k]])),
  base_reference:f.envelope.base_reference,families:[{source_id:family,parts:[f.pin(name+'/source.json',originals)]}],
  targets:requested.map(({target,feature,owner})=>({id:target,target_id:feature.id,pixelIndex:owner+1,source_family:family,base_geometry:feature.geometry,
   source_receipt_sha256:physicalEvidence.sha256,coverage_classes:['mapped_land_support']})),
  source_membership:{index:f.pin('data/world-index.json',originals),lineage:f.pin('data/semantic-report.json',originals),parts:[f.pin(membershipPath,originals)]}};
 mutateEvidence(evidence);f.save(name+'/evidence.json',evidence);const ev=f.commit();
 const operands={source_evidence:f.pin(name+'/evidence.json',ev),native_patch:f.pin(name+'/native-patch.json',originals)};
 f.save(name+'/rule.json',{version:1,kind:'source-target-native-rule-v1',...operands});
 f.save(name+'/binding.json',{version:1,kind:'source-target-native-custody-v1',...operands});const authority=f.commit();
 const entry={policy_id:'retained-source-literal-additions',policy_version:1,rule_preimage:f.pin(name+'/rule.json',authority),
  rule_sha256:f.pin(name+'/rule.json',authority).sha256,source_authority:f.pin(name+'/binding.json',authority)};entry.authority_sha256=valueSha(entry);
 const reader=new f.native.ImmutableReader(f.root,authority);
 const {readRetainedRegistryAuthority}=await import(pathToFileURL(path.join(f.root,CODE[1])));
 const proof=readRetainedRegistryAuthority(reader,entry);
 assert(Object.isFrozen(proof));assert.strictEqual(proof.source_rows,proof.original_ledger.rows);
 for(const component of proof.original_ledger.rows)for(const row of component.native_rows)for(const run of row.runs)
  assert(proof.native_proof.native_patches[0].rows.find(candidate=>candidate.y===row.y)?.runs.includes(run));
 if(completedConstructor){
  const constructed={version:1,kind:'existing-source-target-native-constructor-result',
   inputs:Object.fromEntries(Object.entries(operands).map(([role,pin])=>[role,{commit:pin.commit,path:pin.path}])),
   rule_sha256:entry.rule_sha256,component_ids:structuredClone(proof.source_scope_ids),ledger_rows:structuredClone(proof.source_rows),limitations:proof.limitations};
  mutateConstructor(constructed);f.save(name+'/constructed.json',constructed);const completed=f.commit();
  entry.completed_constructor=f.pin(name+'/constructed.json',completed);
 }
 const entries=[...f.registry.entries,entry];
 if(duplicateAuthority){
  f.save(name+'/binding-duplicate.json',{version:1,kind:'source-target-native-custody-v1',...operands});const duplicate=f.commit();
  const other={...entry,source_authority:f.pin(name+'/binding-duplicate.json',duplicate)};delete other.authority_sha256;
  other.authority_sha256=valueSha(other);entries.push(other);
 }
 const registry={...f.registry,entries:entries.sort((a,b)=>a.authority_sha256.localeCompare(b.authority_sha256))};
 const ledger={...f.ledger,authority_registry_sha256:valueSha(registry),
  scope_ids:[...f.ledger.scope_ids,...proof.original_ledger.scope_ids],
  rows:[...structuredClone(f.ledger.rows),...proof.original_ledger.rows.map(row=>({...row,authority_sha256:entry.authority_sha256}))]};
 mutateLedger(ledger,proof,entry);
 ledger.rows.sort((a,b)=>a.component_id.localeCompare(b.component_id));ledger.scope_ids=ledger.rows.map(p=>p.component_id);
 const normalized=ledger.rows.filter(p=>p.disposition==='assigned').map(row=>({...row,rule_sha256:row.rule_sha256??registry.entries.find(p=>p.authority_sha256===row.authority_sha256).rule_sha256}));
 f.save(name+'/registry.json',registry);f.save(name+'/ledger.json',ledger);const l=f.commit();
 const effective={...f.envelope.base_reference,footprints_sha256:valueSha({domain:'worldatlas-effective-native-footprints:v2',base_reference:f.envelope.base_reference,
  authority_registry_sha256:valueSha(registry),ledger_sha256:f.pin(name+'/ledger.json',l).sha256,components:normalized})};
 const patch={...f.patch,authority_registry_sha256:valueSha(registry),ledger_sha256:f.pin(name+'/ledger.json',l).sha256,
  effective_reference:effective,rows:structuredClone([...f.patch.rows,...proof.native_proof.native_patches.flatMap(p=>p.rows)]).sort((a,b)=>a.y-b.y)};
 mutatePatch(patch);f.save(name+'/patch.json',patch);const p=f.commit();
 const assets={...f.sidecar.logical_asset_map,ledger:f.pin(name+'/ledger.json',l),patch:f.pin(name+'/patch.json',p)};
 const envelope={...f.envelope,effective_reference:effective,...assets};f.save(name+'/envelope.json',envelope);const e=f.commit();
 const sidecar={...f.sidecar,authority_registry:f.pin(name+'/registry.json',l),logical_asset_map:assets,runtime_envelope:f.pin(name+'/envelope.json',e)};
 f.save(name+'/sidecar.json',sidecar);const sc=f.commit(),side=f.pin(name+'/sidecar.json',sc);
 const selection={...f.selection,additive_release:{path:side.path,bytes:side.bytes,sha256:side.sha256}};
 f.save('data/ownership-selection.json',selection);const candidate=f.commit();
 return {candidate,proof,entry,registry,ledger,patch,sidecar,selection,envelope,effective,y,x};
}

export {MODULE,CODE,sha,polygon,feature,fixtures,addition,trustedFixture,appendNativeAuthority};

// The existing three-owner reference fixture supplies the complete real base
// reader contract. The catalogue below is synthetic accepted custody, with one
// retained rejected component and no additive cells; no scientific run is claimed.
export async function referenceCheckpointFixture(t,{finalBank=false}={}) {
 const f=mapCellSelectionFixture(t), current=f.current;
 const raw=(version,name)=>execFileSync('git',['-C',f.repo,'show',version+':'+name],{maxBuffer:Infinity});
 const json=(version,name)=>JSON.parse(raw(version,name));
 const manifest=json(f.base,f.selection.manifest_path), baseSelection=structuredClone(f.selection);
 delete baseSelection.additive_release; delete baseSelection.reference_projection;
 for(const name of ['data/hierarchy.json','data/geography/fixture.json','data/geographic-releases/current-manifest.json','data/geographic-releases/releases.json.gz'])
  f.write(name,raw(f.base,name));
 for(const name of new Set([...CODE,...JOINT_CODE]))f.write(name,fs.readFileSync(name));
 f.write('package.json',{type:'module'});
 const put=(name,value)=>{f.write(name,value);const version=f.commit();return f.pin(name,version);};
 const retainedRows=finalBank?[{y:f.cells[1].y,runs:[[f.cells[1].x,f.cells[1].x+1,1]]}]:[];
 const originalPatch={version:1,kind:'unassigned-native-cells-v1',rows:retainedRows};
 const patchPin=put('accepted/empty-patch.json',originalPatch);
 const rule=put('accepted/rule.json',{synthetic:'retained rejected component'});
 const publication=put('accepted/native-publication.json',{assets:[{path:'patch-empty.json',bytes:patchPin.bytes,sha256:patchPin.sha256}]});
 // The original publication name and actual immutable asset locator must join.
 const asset=put('accepted/patch-empty.json',JSON.parse(raw(patchPin.commit,patchPin.path)));
 const binding=put('accepted/binding.json',{native_proof:{publication,assets:[asset]}});
 const entry={policy_id:'retained-source-literal-additions',policy_version:1,rule_preimage:rule,rule_sha256:rule.sha256,source_authority:binding};
 entry.authority_sha256=valueSha(entry);
 const registry={version:1,kind:'retained-rule-authority-registry-v1',entries:[entry]},registryPin=put('accepted/registry.json',registry);
 const target={target_id:'A',pixelIndex:1,geometry:f.features[0].geometry,geometry_sha256:valueSha(f.features[0].geometry)},targets=finalBank?[target]:[];
 const literal={...addition('old','A',1,target.geometry_sha256,.3),base_geometry:target.geometry,disposition:'assigned',native_cells:1,source_receipt_sha256:'c'.repeat(64)};
 const additions=finalBank?[{...literal,authority_sha256:entry.authority_sha256,rule_sha256:entry.rule_sha256}]:[];
 const request={base_selection:baseSelection,authority_registry_sha256:valueSha(registry),current_targets:targets,current_rows:retainedRows,
  original_patch_sha256s:[valueSha(originalPatch)],acquisition:{predecessor_rows:[],predecessor_proof:null,native_inputs:[]}};
 const products={request,result:{native:{rows:retainedRows}},facts:{acquisition_phases:[]},publication:{},operating:{}};
 const pins=Object.fromEntries(Object.entries(products).map(([name,body])=>[name,put('accepted/rebind-'+name+'.json',body)]));
 const rebind=put('accepted/rebind.json',{version:1,kind:'qualified-native-additive-current-bank-rebind-v1',execution_commit:f.original,
  base_selection:baseSelection,authority_registry_sha256:valueSha(registry),...pins});
 const ledger={version:2,kind:'native-additive-repair-ledger-v2',authority_registry_sha256:valueSha(registry),scope_ids:finalBank?['old','rejected']:['rejected'],
  rows:[...(finalBank?[{...literal,authority_sha256:entry.authority_sha256}]:[]),{component_id:'rejected',disposition:'rejected',reason:'synthetic retained exception',authority_sha256:entry.authority_sha256}],
  parent_inventory:{components:finalBank?2:1,roster_sha256:'e'.repeat(64)},current_rebind:rebind,current_targets:targets};
 const ledgerPin=put('accepted/ledger.json',ledger),reference={id:manifest.geographic_release,hierarchy_sha256:manifest.hierarchy_sha256,footprints_sha256:manifest.footprints_sha256};
 const effective={...reference,footprints_sha256:valueSha({domain:'worldatlas-effective-native-footprints:v2',base_reference:reference,
  authority_registry_sha256:valueSha(registry),ledger_sha256:ledgerPin.sha256,components:additions})};
 const patch={version:2,kind:'unassigned-native-cells-v1',authority_registry_sha256:valueSha(registry),ledger_sha256:ledgerPin.sha256,
  base_reference:reference,effective_reference:effective,rows:retainedRows};
 const bounds=f.pin('data/canonical-grid/bounds.json.gz',f.original);
 const assets={base_manifest:f.pin(f.selection.manifest_path,f.base),owner_roster:bounds,ledger:ledgerPin,patch:put('accepted/patch.json',patch)};
 const envelope={version:2,kind:'retained-native-base-plus-delta-v2',base_reference:reference,effective_reference:effective,...assets};
 const sidecar={version:2,kind:'retained-native-additive-selection-v2',base_selection:baseSelection,authority_registry:registryPin,
  logical_asset_map:assets,runtime_envelope:put('accepted/envelope.json',envelope)};
 const side=put('accepted/sidecar.json',sidecar),selection={...baseSelection,additive_release:{path:side.path,bytes:side.bytes,sha256:side.sha256}};
 f.write('data/ownership-selection.json',selection);const selected=f.commit();
 const api=await import(pathToFileURL(path.join(f.repo,MODULE))),native=await import(pathToFileURL(path.join(f.repo,'scripts/check-effective-geographic-regression.mjs')));
 const reader=new native.ImmutableReader(f.repo,selected);
 const qualified={state:{patch,additions}};
 for(const name of ['data/hierarchy.json','data/geography/fixture.json','data/geographic-releases/current-manifest.json','data/geographic-releases/releases.json.gz'])f.write(name,raw(current,name));
 const currentReference=f.projection.reference;
 const currentEffective={...currentReference,footprints_sha256:valueSha({domain:'worldatlas-effective-native-footprints:v2',
  base_reference:currentReference,authority_registry_sha256:valueSha(registry),ledger_sha256:ledgerPin.sha256,components:additions})};
 const currentPatch={...patch,base_reference:currentReference,effective_reference:currentEffective};
 const currentAssets={...assets,patch:put('current/patch.json',currentPatch)};
 const currentEnvelope={...envelope,...currentAssets,base_reference:currentReference,effective_reference:currentEffective};
 const currentSidecar={...sidecar,logical_asset_map:currentAssets,runtime_envelope:put('current/envelope.json',currentEnvelope)};
 const currentSide=put('current/sidecar.json',currentSidecar);
 Object.assign(f.selection,selection,{additive_release:{path:currentSide.path,bytes:currentSide.bytes,sha256:currentSide.sha256}});
 const candidate=f.project();
 return {...f,api,native,selected,candidate,state:qualified.state,reader,manifest,sidecar:currentSidecar,selection};
}

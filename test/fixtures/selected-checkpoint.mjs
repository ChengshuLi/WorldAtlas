import assert from 'node:assert/strict';
import {after} from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {shuffleOwnershipBytes} from '../../src/ownership-codec.js';
import {nativeRowLatitudes} from '../../src/native-grid.js';
import {valueBytes,valueSha,coordinateBounds} from '../../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {mapCellSelectionFixture} from './map-cell-selection.mjs';
import {deriveCoordinateDelta} from '../../coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
const MODULE='coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
const PROGRAMME='coordination/engineering/selected-geography-effective-prevention-20261009/supported-programs.json';
const CATALOGUE='coordination/engineering/selected-checkpoint-reuse-20261012/accepted-checkpoints.json';
const CODE=[MODULE,'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs','scripts/check-effective-geographic-regression.mjs',
  'scripts/selected-reference-metadata.mjs','src/reference-metadata.js','src/native-grid.js','src/ownership-codec.js'];
const sha=b=>createHash('sha256').update(b).digest('hex');
const polygon=(x,y=0)=>({type:'Polygon',coordinates:[[[x,y],[x+.2,y],[x+.2,y+.2],[x,y+.2],[x,y]]]});
const feature=(id,x)=>({type:'Feature',id,properties:{id,parent_id:'parent'},geometry:polygon(x)});
function fixtures(){
 const features=[feature('A',0),feature('B',1),feature('C',5)];
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

function buildTrustedSeed(root,{incompleteNative,codeRoutes,nativeAppend,sourceOverride,physicalLogicalSource,originalPatchRows,overrideLogicalPath}){
 const {git,save,commit,pin}=fixtureRepository(root);
 git('init','-q');if(codeRoutes)save('data/scientific.js',{fixture:'scientific input, not executed code'});save(PROGRAMME,fs.readFileSync(PROGRAMME));for(const name of CODE)save(name,fs.readFileSync(name));save('package.json',{type:'module'});
 const {features,certificate}=fixtures(), source={type:'FeatureCollection',features};save('data/source.json',source);
 if(sourceOverride)save('data/selected-source.json.gz',gzipSync(valueBytes(source)));
 const reference={id:'geography:fixture',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)};
 const encode=(name,kind,values)=>{const words=Uint32Array.from(values),canonical=Buffer.from(words.buffer),encoded=gzipSync(shuffleOwnershipBytes(words));save('data/'+name,encoded);return {path:name,kind,offset:0,bytes:encoded.length,sha256:sha(encoded),decoded_bytes:canonical.length,decoded_sha256:sha(canonical),words:words.length,encoding:'byte-shuffle'};};
 const size=nativeAppend?262166:4,coordinateBits=Math.ceil(Math.log2(size));
 const table=nativeAppend?Array.from({length:size*2},(_,i)=>i%2?0:3):[0,1,incompleteNative?2:1,1,2,1,3,0];
 if(nativeAppend)table.splice(0,6,0,1,1,1,2,1);
 const parts=[encode('native/rows.bin.gz','rows',table),encode('native/runs.bin.gz','runs',[2**coordinateBits,0,2*2**coordinateBits,0,3*2**coordinateBits+1,1])];
 const compressedParts=parts.map(p=>fs.readFileSync(path.join(root,'data',p.path))),whole=Buffer.concat(compressedParts),fragment=gzipSync(whole);
 save('data/transport/fragment.gz',fragment);
 const index={version:1,kind:'ordered-exact-original-byte-fragments',whole_bytes:whole.length,whole_sha256:sha(whole),files:parts.map((p,i)=>({path:p.path,mode:'100644',offset:i?parts[0].bytes:0,bytes:p.bytes,sha256:p.sha256})),parts:[{path:'fragment.gz',offset:0,bytes:fragment.length,sha256:sha(fragment),decoded_bytes:whole.length,decoded_sha256:sha(whole)}]};save('data/transport/index.json',index);
 const manifest={version:1,size,coordinateBits,method:'native-linear-evenodd-first-owner-v1',native_latitudes:[],hierarchy_sha256:reference.hierarchy_sha256,original_assets:{},parts,runWords:6,native_asset_transport:{version:1,kind:index.kind,index:{path:'data/transport/index.json',bytes:valueBytes(index).length,sha256:valueSha(index)},logical_assets:2,original_compressed_bytes:whole.length}};
 save('data/owners.json',[{id:'A',index:1},{id:'B',index:2},{id:'C',index:3}]);
 if(nativeAppend){
  const latitudes=nativeRowLatitudes(size),bytes=Buffer.alloc(size*8);
  latitudes.forEach((v,i)=>bytes.writeDoubleLE(v,i*8));save('original/latitudes.f64le',bytes);
  const initial=commit(),body=git('show',initial+':original/latitudes.f64le'),tree=git('ls-tree',initial,'--','original/latitudes.f64le').toString().split(/\s+/);
  manifest.native_latitudes={commit:initial,path:'original/latitudes.f64le',mode:tree[0],git_blob_oid:tree[2],bytes:body.length,sha256:sha(body)};
  manifest.original_assets={bounds:{sha256:sha(fs.readFileSync(path.join(root,'data/owners.json')))}};
 }
 save('data/manifest.json',manifest);
 const primitive=addition('old','A',1,certificate.entries[0][7],.3);
 const literal={...primitive,base_geometry:features[0].geometry,disposition:'assigned',native_cells:1,source_receipt_sha256:'c'.repeat(64)};
 const originalPatch={version:1,kind:'unassigned-native-cells-v1',rows:originalPatchRows??[{y:1,runs:[[2,3,1]]}]};
 save('original/patch-one.json',originalPatch);save('original/rule.json',{version:1});const one=commit();
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
 const sourcePin=sourceOverride?{...pin('data/selected-source.json.gz',one),kind:'selected-exact-encoded-override',
  logical_path:overrideLogicalPath,encoding:'gzip',decoded_bytes:valueBytes(source).length,decoded_sha256:valueSha(source)}
  :{...pin('data/source.json',one),kind:'ordinary-immutable-git-source'};
 const additions=normalized.map(row=>({...row,base_geometry:target.geometry,base_geometry_sha256:target.geometry_sha256}));
 const derived=deriveCoordinateDelta({certificate,oldAdditions:[],additions,selection}).certificate;
 const full={...derived,binding:{...derived.binding,release:reference,sources:[sourcePin]},inputs:[{path:'data/source.json',source:sourcePin,whole_body_sha256:sourcePin.decoded_sha256??sourcePin.sha256,bytes:sourcePin.decoded_bytes??sourcePin.bytes}]};
 const execution_code=CODE.map(name=>pin(name,one)),runtime=[{path:process.execPath,bytes:fs.statSync(process.execPath).size,sha256:'f'.repeat(64)}];
 const facts={version:1,kind:'trusted-selected-coordinate-stage-v1',candidate_code_executed:false,selected_commit:selected,executing_commit:one,execution_code,runtime,binding:full.binding,complete_owners:3,complete_sources:1};
 const compressed=gzipSync(valueBytes(full));save('accepted/certificate.json.gz',compressed);save('accepted/facts.json',facts);
 const publication={version:1,kind:facts.kind,complete:true,facts:{path:'facts.json',bytes:valueBytes(facts).length,sha256:valueSha(facts)},certificate:{path:'certificate.json.gz',bytes:compressed.length,sha256:sha(compressed),decoded_bytes:valueBytes(full).length,decoded_sha256:valueSha(full)}};save('accepted/publication.json',publication);
 const inventory=[...(codeRoutes?['src/native-grid.js','data/scientific.js']:[]),PROGRAMME,...(sourceOverride?['data/selected-source.json.gz',...(physicalLogicalSource?['data/source.json']:[])]:['data/source.json']),'data/manifest.json','data/owners.json','data/registry.json','data/ledger.json','data/patch.json','data/sidecar.json','data/envelope.json','data/native/rows.bin.gz','data/native/runs.bin.gz'].map(name=>pin(name,selected));
 save('accepted/custody.json',{complete_cold_custody:[{facts,publication,effective_additions:additions,inventory}]});
 save('accepted/routes.json',[...new Set([...inventory.map(p=>p.path),'data/source.json'])].sort().map(name=>({path:name,tree:git('ls-tree','-z',selected,'--',name).toString()})));const accepted=commit();
 const rootRow={id:'fixture',accepted_head:accepted,selected_commit:selected,selection_sha256:valueSha(selection),execution_commit:one,execution_code_sha256:valueSha(execution_code),runtime_sha256:valueSha(runtime),facts:pin('accepted/facts.json'),certificate:{...pin('accepted/certificate.json.gz'),decoded_bytes:valueBytes(full).length,decoded_sha256:valueSha(full)},publication:pin('accepted/publication.json'),custody:pin('accepted/custody.json'),routes:pin('accepted/routes.json')};
 save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[rootRow]});commit();
 return {root,data:{selected,ledger,patch,sidecar,envelope,selection,rootRow,manifest,features,registry}};
}

// The real entry reads each independent copy's ordinary committed catalogue and
// products. Qualification, readers and private module state are always fresh.
async function trustedFixture(t,{incompleteNative=false,codeRoutes=false,nativeAppend=false,sourceOverride=false,physicalLogicalSource=false,originalPatchRows,overrideLogicalPath='data/source.json'}={}){
 // Snapshot caller-owned rows before both keying and building the private seed.
 const options={incompleteNative,codeRoutes,nativeAppend,sourceOverride,physicalLogicalSource,
  originalPatchRows:structuredClone(originalPatchRows??[{y:1,runs:[[2,3,1]]}]),overrideLogicalPath};
 const key=JSON.stringify(options);
 let seed=trustedSeeds.get(key);
 if(!seed){
  const root=fs.mkdtempSync(path.join(process.cwd(),'.checkpoint-seed-'));
  try{seed=buildTrustedSeed(root,options);trustedSeeds.set(key,seed);}
  catch(error){fs.rmSync(root,{recursive:true,force:true});throw error;}
 }
 const root=fs.mkdtempSync(path.join(process.cwd(),'.checkpoint-test-'));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 fs.cpSync(seed.root,root,{recursive:true});
 const data=structuredClone(seed.data);
 const api=await import(pathToFileURL(path.join(root,MODULE))),native=await import(pathToFileURL(path.join(root,'scripts/check-effective-geographic-regression.mjs')));
 const reader=new native.ImmutableReader(root,data.selected);
 return {...data,...fixtureRepository(root),api,native,reader};
}

// Genuine pinned source/native qualification, followed by the public private-state
// admission and transition. The full lattice is a two-MiB normative input, while
// the proposed and projected repair is one cell; no research result is invented.
async function appendNativeAuthority(f,{owner=0,name='appended',mutateEvidence=()=>{},mutateLedger=()=>{},mutatePatch=()=>{},duplicateAuthority=false,membershipPath='data/geography/part-0.json'}={}) {
 const family='gb:TST:ADM2',feature=f.features[owner],target=family+':'+feature.id;
 const latitudes=nativeRowLatitudes(f.manifest.size),y=latitudes.findIndex(v=>v<.1);
 const x=Math.floor((owner+.1+180)/360*f.manifest.size);
 const raw={type:'FeatureCollection',features:f.features.map(p=>({type:'Feature',properties:{shapeID:p.id},geometry:p.geometry}))};
 f.save(name+'/source.json',raw);
 f.save('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',{
  products:[{key:family,parts:[{path:name+'/source.json',bytes:valueBytes(raw).length,sha256:valueSha(raw)}],
   feature_count:raw.features.length,original_bytes:valueBytes(raw).length,original_sha256:valueSha(raw)}]});
 f.save(name+'/physical.json',{results:[{target,issues:[],support:{mapped_land_support:feature.geometry}}]});
 f.save(name+'/measured.json',[{target,consumed:{geometry:feature.geometry},selected:{id:feature.id,geometry:feature.geometry}}]);
 f.save(name+'/physical.py',Buffer.from('# immutable bounded fixture\n'));
 f.save('data/world-index.json',{parts:[membershipPath.slice('data/'.length)]});
 f.save('data/semantic-report.json',{changes:f.features.map(p=>({id:p.id,replaces:[family+':'+p.id]}))});
 f.save(membershipPath,{type:'FeatureCollection',features:f.features.map(p=>({...p,
  properties:{...p.properties,metadata:{source_member_ids:[family+':'+p.id]}}}))});
 f.save(name+'/native-patch.json',{rows:[{y,runs:[[x,x+1,owner+1]]}]});const originals=f.commit();
 const evidence={version:1,kind:'source-target-native-evidence-v1',
  catalogue:f.pin('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',originals),
  owner_roster:f.pin('data/owners.json',originals),physical_evidence:f.pin(name+'/physical.json',originals),
  physical_input:f.pin(name+'/measured.json',originals),physical_reproduction:f.pin(name+'/physical.py',originals),
  native_latitudes:f.manifest.native_latitudes,
  native_contract:Object.fromEntries(['size','coordinateBits','method','native_latitudes','hierarchy_sha256','original_assets'].map(k=>[k,f.manifest[k]])),
  base_reference:f.envelope.base_reference,families:[{source_id:family,parts:[f.pin(name+'/source.json',originals)]}],
  targets:[{id:target,target_id:feature.id,pixelIndex:owner+1,source_family:family,base_geometry:feature.geometry,
   source_receipt_sha256:f.pin(name+'/physical.json',originals).sha256,coverage_classes:['mapped_land_support']}],
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
 assert.strictEqual(proof.original_ledger.rows[0].native_rows[0].runs[0],proof.native_proof.native_patches[0].rows[0].runs[0]);
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

export {MODULE,PROGRAMME,CATALOGUE,CODE,sha,polygon,feature,fixtures,addition,trustedFixture,appendNativeAuthority};

// The existing three-owner reference fixture supplies the complete real base
// reader contract. The catalogue below is synthetic accepted custody, with one
// retained rejected component and no additive cells; no scientific run is claimed.
export async function referenceCheckpointFixture(t) {
 const f=mapCellSelectionFixture(t), current=f.current;
 const raw=(version,name)=>execFileSync('git',['-C',f.repo,'show',version+':'+name],{maxBuffer:Infinity});
 const json=(version,name)=>JSON.parse(raw(version,name));
 const manifest=json(f.base,f.selection.manifest_path), baseSelection=structuredClone(f.selection);
 delete baseSelection.additive_release; delete baseSelection.reference_projection;
 for(const name of ['data/hierarchy.json','data/geography/fixture.json','data/geographic-releases/current-manifest.json','data/geographic-releases/releases.json.gz'])
  f.write(name,raw(f.base,name));
 for(const name of [...CODE,'scripts/selected-checkpoint-native.mjs'])f.write(name,fs.readFileSync(name));
 f.write(PROGRAMME,fs.readFileSync(PROGRAMME));f.write('package.json',{type:'module'});
 const put=(name,value)=>{f.write(name,value);const version=f.commit();return f.pin(name,version);};
 const patchPin=put('accepted/empty-patch.json',{version:1,kind:'unassigned-native-cells-v1',rows:[]});
 const rule=put('accepted/rule.json',{synthetic:'retained rejected component'});
 const publication=put('accepted/native-publication.json',{assets:[{path:'patch-empty.json',bytes:patchPin.bytes,sha256:patchPin.sha256}]});
 // The original publication name and actual immutable asset locator must join.
 const asset=put('accepted/patch-empty.json',JSON.parse(raw(patchPin.commit,patchPin.path)));
 const binding=put('accepted/binding.json',{native_proof:{publication,assets:[asset]}});
 const entry={policy_id:'retained-source-literal-additions',policy_version:1,rule_preimage:rule,rule_sha256:rule.sha256,source_authority:binding};
 entry.authority_sha256=valueSha(entry);
 const registry={version:1,kind:'retained-rule-authority-registry-v1',entries:[entry]},registryPin=put('accepted/registry.json',registry);
 const request={base_selection:baseSelection,authority_registry_sha256:valueSha(registry),current_targets:[],current_rows:[],
  original_patch_sha256s:[valueSha({version:1,kind:'unassigned-native-cells-v1',rows:[]})],acquisition:{predecessor_rows:[],predecessor_proof:null,native_inputs:[]}};
 const products={request,result:{native:{rows:[]}},facts:{acquisition_phases:[]},publication:{},operating:{}};
 const pins=Object.fromEntries(Object.entries(products).map(([name,body])=>[name,put('accepted/rebind-'+name+'.json',body)]));
 const rebind=put('accepted/rebind.json',{version:1,kind:'qualified-native-additive-current-bank-rebind-v1',execution_commit:f.original,
  base_selection:baseSelection,authority_registry_sha256:valueSha(registry),...pins});
 const ledger={version:2,kind:'native-additive-repair-ledger-v2',authority_registry_sha256:valueSha(registry),scope_ids:['rejected'],
  rows:[{component_id:'rejected',disposition:'rejected',reason:'synthetic retained exception',authority_sha256:entry.authority_sha256}],
  parent_inventory:{components:1,roster_sha256:'e'.repeat(64)},current_rebind:rebind,current_targets:[]};
 const ledgerPin=put('accepted/ledger.json',ledger),reference={id:manifest.geographic_release,hierarchy_sha256:manifest.hierarchy_sha256,footprints_sha256:manifest.footprints_sha256};
 const effective={...reference,footprints_sha256:valueSha({domain:'worldatlas-effective-native-footprints:v2',base_reference:reference,
  authority_registry_sha256:valueSha(registry),ledger_sha256:ledgerPin.sha256,components:[]})};
 const patch={version:2,kind:'unassigned-native-cells-v1',authority_registry_sha256:valueSha(registry),ledger_sha256:ledgerPin.sha256,
  base_reference:reference,effective_reference:effective,rows:[]};
 const bounds=f.pin('data/canonical-grid/bounds.json.gz',f.original);
 const assets={base_manifest:f.pin(f.selection.manifest_path,f.base),owner_roster:bounds,ledger:ledgerPin,patch:put('accepted/patch.json',patch)};
 const envelope={version:2,kind:'retained-native-base-plus-delta-v2',base_reference:reference,effective_reference:effective,...assets};
 const sidecar={version:2,kind:'retained-native-additive-selection-v2',base_selection:baseSelection,authority_registry:registryPin,
  logical_asset_map:assets,runtime_envelope:put('accepted/envelope.json',envelope)};
 const side=put('accepted/sidecar.json',sidecar),selection={...baseSelection,additive_release:{path:side.path,bytes:side.bytes,sha256:side.sha256}};
 f.write('data/ownership-selection.json',selection);const selected=f.commit();
 const api=await import(pathToFileURL(path.join(f.repo,MODULE))),native=await import(pathToFileURL(path.join(f.repo,'scripts/check-effective-geographic-regression.mjs')));
 const neighbors=await import(pathToFileURL(path.join(f.repo,CODE[1]))),reader=new native.ImmutableReader(f.repo,selected);
 const snapshot=native.loadBaseSelection(reader),resolver=native.selectedGeometrySourceAlias(snapshot);
 const certificate=neighbors.joinSelectedCoordinateCertificate(resolver,[neighbors.selectedCoordinateShard(resolver,resolver.paths)]);
 const execution_code=CODE.map(name=>f.pin(name,selected)),runtime=[{path:process.execPath,bytes:fs.statSync(process.execPath).size,sha256:'f'.repeat(64)}];
 const facts={version:1,kind:'trusted-selected-coordinate-stage-v1',candidate_code_executed:false,selected_commit:selected,executing_commit:selected,
  execution_code,runtime,binding:certificate.binding,complete_owners:3,complete_sources:1};
 const compressed=gzipSync(valueBytes(certificate)),certificatePin=put('accepted/certificate.json.gz',compressed),factsPin=put('accepted/facts.json',facts);
 const output={version:1,kind:facts.kind,complete:true,facts:{path:'facts.json',bytes:factsPin.bytes,sha256:factsPin.sha256},
  certificate:{path:'certificate.json.gz',bytes:compressed.length,sha256:sha(compressed),decoded_bytes:valueBytes(certificate).length,decoded_sha256:valueSha(certificate)}};
 const outputPin=put('accepted/publication.json',output);
 const inventory=[...reader.inventory.values(),f.pin(PROGRAMME,selected)];
 const custody=put('accepted/custody.json',{complete_cold_custody:[{facts,publication:output,effective_additions:[],inventory}]});
 const paths=new Set(inventory.map(p=>p.path).filter(p=>!/\.(mjs|py)$/.test(p)&&p!=='requirements.txt'));paths.delete('data/ownership-selection.json');
 for(const part of manifest.parts)paths.add(path.posix.join(path.posix.dirname(selection.manifest_path),part.path));
 for(const input of certificate.inputs){paths.add(input.path);paths.add(input.source.path);}
 const routes=put('accepted/routes.json',[...paths].sort().map(name=>({path:name,tree:reader.treeRoute(name)})));
 const rootRow={id:'reference-fixture',accepted_head:selected,selected_commit:selected,selection_sha256:valueSha(selection),execution_commit:selected,
  execution_code_sha256:valueSha(execution_code),runtime_sha256:valueSha(runtime),facts:factsPin,
  certificate:{...certificatePin,decoded_bytes:valueBytes(certificate).length,decoded_sha256:valueSha(certificate)},publication:outputPin,custody,routes};
 put(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[rootRow]});
 const qualified=api.qualifyCheckpoint({reader});assert.equal(qualified.available,true);t.after(()=>api.releaseCheckpoint(qualified.state));
 for(const name of ['data/hierarchy.json','data/geography/fixture.json','data/geographic-releases/current-manifest.json','data/geographic-releases/releases.json.gz'])f.write(name,raw(current,name));
 const currentReference=f.projection.reference;
 const currentEffective={...currentReference,footprints_sha256:valueSha({domain:'worldatlas-effective-native-footprints:v2',
  base_reference:currentReference,authority_registry_sha256:valueSha(registry),ledger_sha256:ledgerPin.sha256,components:[]})};
 const currentPatch={...patch,base_reference:currentReference,effective_reference:currentEffective};
 const currentAssets={...assets,patch:put('current/patch.json',currentPatch)};
 const currentEnvelope={...envelope,...currentAssets,base_reference:currentReference,effective_reference:currentEffective};
 const currentSidecar={...sidecar,logical_asset_map:currentAssets,runtime_envelope:put('current/envelope.json',currentEnvelope)};
 const currentSide=put('current/sidecar.json',currentSidecar);
 Object.assign(f.selection,selection,{additive_release:{path:currentSide.path,bytes:currentSide.bytes,sha256:currentSide.sha256}});
 const candidate=f.project();
 return {...f,api,native,selected,candidate,state:qualified.state,reader,certificate,manifest,sidecar:currentSidecar,selection};
}

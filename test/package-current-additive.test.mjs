import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {gzipSync,gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {selectedDataCheckoutPatterns,loadPackageInputs} from '../scripts/package-inputs.mjs';
import {committedPackageInputs} from '../scripts/package-output-artifact.mjs';
import {prepareCurrentSelectedAdditive} from '../scripts/package-current-additive.mjs';
import {additiveReleaseFootprintDigest,bindAdditiveLedgerFeatures,footprintValueSha256,loadedBaseFootprintSha256} from '../src/effective-footprint.js';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const rectangle=(a,b,c,d)=>({type:'Polygon',coordinates:[[[a,b],[c,b],[c,d],[a,d],[a,b]]]});
const logical=(name,pin)=>({path:'additive-repairs/'+name,bytes:pin.bytes,sha256:pin.sha256});
async function write(root,name,value){
 const raw=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value));
 await fs.mkdir(path.dirname(path.join(root,name)),{recursive:true});await fs.writeFile(path.join(root,name),raw);
 return {path:name,bytes:raw.length,sha256:sha(raw)};
}
async function saveSelection(f){await write(f.root,'data/ownership-selection.json',f.selection);}
async function saveProjection(f){f.selection.reference_projection=await write(f.root,'inputs/reference-metadata.json',f.projection);await saveSelection(f);}
async function saveEnvelope(f){
 f.sidecar.runtime_envelope=await write(f.root,'inputs/runtime-envelope.json',{additiveRelease:f.envelope});
 f.selection.additive_release=await write(f.root,'inputs/selection.json',f.sidecar);await saveSelection(f);
}
async function savePatch(f){
 const pin=await write(f.root,f.sidecar.logical_asset_map.patch?.path??'inputs/patch.json',f.patch);
 f.sidecar.logical_asset_map.patch=pin;f.envelope.patch=logical('patch.json',pin);await saveEnvelope(f);
}
// Bounded current-product model: three immutable owners and one additive run.
// Receipts/source pins below deliberately have no files. Ordinary packaging
// consumes the accepted whole projection, without reopening source authority.
async function fixture(t,{metadata=false,ledgerBytes}={}){
 const root=await fs.realpath(await fs.mkdtemp(path.join(os.tmpdir(),'atlas-current-additive-')));
 t.after(()=>fs.rm(root,{recursive:true,force:true}));
 await write(root,'.github/package-inputs.json',{version:1,inputs:['.github/package-inputs.json','data/ownership-selection.json','inputs/'],optional_inputs:[],verification_paths:[],generated_outputs:[]});
 const originalFeatures=['A','B','C'].map((id,i)=>({type:'Feature',id,pixelIndex:i+1,geometry:rectangle(i*2,0,i*2+1,1),properties:{id,name:id,parent_id:i===2?'Q':'P',metadata:{}}}));
 const owners=originalFeatures.map(feature=>({id:feature.id,index:feature.pixelIndex,province_id:feature.properties.parent_id,province_index:feature.id==='C'?2:1,bounds:[feature.pixelIndex-1,0,feature.pixelIndex,1],center:[feature.pixelIndex-.5,.5]}));
 const rosterRaw=Buffer.from(JSON.stringify(owners)),bounds=gzipSync(rosterRaw),rosterPin=await write(root,'inputs/owners.json.gz',bounds);
 const native={id:'geography:native',footprints_sha256:loadedBaseFootprintSha256(originalFeatures),hierarchy_sha256:'b'.repeat(64)};
 const manifest={geographic_release:native.id,footprints_sha256:native.footprints_sha256,hierarchy_sha256:native.hierarchy_sha256,size:16,original_assets:{bounds:{bytes:bounds.length,sha256:rosterPin.sha256}}};
 const manifestPin=await write(root,'inputs/base-native-manifest.json',manifest);
 const selection={version:1,release_id:native.id,manifest_path:manifestPin.path,sha256:manifestPin.sha256,source_map:{path:'qualified/original-source-map.json',sha256:'1'.repeat(64)},artifact_certificate:{path:'qualified/original-certificate.json',sha256:'2'.repeat(64)},review:{path:'qualified/original-review.json',sha256:'3'.repeat(64)}};
 const current=metadata?{...native,id:'geography:metadata',hierarchy_sha256:'c'.repeat(64)}:native;
 const features=structuredClone(originalFeatures),before=originalFeatures[0].properties;
 const after={...structuredClone(before),parent_id:'Q',metadata:{reference_corrections:[{id:'A',action:'reparent',current_name:'A',current_parent_id:'P',new_parent_id:'Q',rationale:'Synthetic sourced parent correction',evidence:[{url:'https://example.invalid/reference',title:'Synthetic reference',inspected_fact:'A belongs to Q'}]}]}};
 if(metadata)features[0].properties=after;
 const acceptedPin=(name,sha256)=>({commit:'1'.repeat(40),path:name,mode:'100644',git_blob_oid:'2'.repeat(40),bytes:1,sha256});
 const projection={version:1,kind:'native-reference-metadata-projection-v1',native_selection:structuredClone(selection),native_reference:native,reference:current,original_owner_roster_sha256:rosterPin.sha256,hierarchy:{before:acceptedPin('qualified/original-hierarchy.json',native.hierarchy_sha256),after:acceptedPin('qualified/current-hierarchy.json',current.hierarchy_sha256)},receipts:[acceptedPin('qualified/reference-receipt.json','4'.repeat(64))],source_updates:[{logical_path:'data/geography/original.json',before:acceptedPin('qualified/original-source.json','5'.repeat(64)),after:acceptedPin('qualified/current-source.json','6'.repeat(64))}],location_changes:[{location_id:'A',before_properties:structuredClone(before),after_properties:after}],group_changes:[],provinces:['P','Q']};
 const addition=rectangle(1,0,2,1),rule='d'.repeat(64);
 const ledger={version:1,kind:'native-additive-repair-ledger-v1',rule_sha256:rule,base_reference:current,parent_inventory:{components:1,report_sha256:'e'.repeat(64),roster_sha256:'f'.repeat(64)},scope_ids:['gap-1'],assigned_cells:2,rows:[{component_id:'gap-1',disposition:'assigned',target_id:'A',pixelIndex:1,base_geometry:features[0].geometry,base_geometry_sha256:footprintValueSha256(features[0].geometry),geometry:addition,geometry_sha256:footprintValueSha256(addition),source_receipt_sha256:'a'.repeat(64),native_cells:2}]};
 const ledgerBody=Buffer.from(JSON.stringify(ledger));
 const ledgerPin=await write(root,'inputs/ledger.json',ledgerBytes===undefined?ledgerBody:Buffer.concat([ledgerBody,Buffer.alloc(ledgerBytes-ledgerBody.length,0x20)]));
 const envelope={version:1,kind:'retained-native-base-plus-delta-v1',base_reference:current,effective_reference:{...current,id:'geography:effective'},base_manifest:logical('base-native-manifest.json',manifestPin),ledger:logical('ledger.json',ledgerPin),owner_roster:{...logical('owners.json.gz',rosterPin),encoding:'gzip',decoded_bytes:rosterRaw.length,decoded_sha256:sha(rosterRaw)}};
 envelope.effective_reference.footprints_sha256=additiveReleaseFootprintDigest(current,bindAdditiveLedgerFeatures(features,ledger,envelope,current));
 const patch={version:1,kind:'unassigned-native-cells-v1',base_reference:current,effective_reference:envelope.effective_reference,ledger_sha256:ledgerPin.sha256,rule_sha256:rule,rows:[{y:3,runs:[[3,5,1]]}]};
 const sidecar={version:2,kind:'retained-native-additive-selection-v2',base_selection:structuredClone(selection),logical_asset_map:{base_manifest:manifestPin,owner_roster:{...rosterPin,encoding:'gzip',decoded_bytes:rosterRaw.length,decoded_sha256:sha(rosterRaw)},ledger:ledgerPin}};
 const f={root,selection,sidecar,projection,patch,envelope,ledger,owners,originalFeatures,features,native,current,selectedGrid:{manifest,sha256:manifestPin.sha256,bounds},geographicRelease:{...current,prepared_at:'synthetic'},originalManifest:Buffer.from(JSON.stringify(manifest)),originalBounds:Buffer.from(bounds)};
 await savePatch(f);if(metadata)await saveProjection(f);return f;
}
async function assertPublished(f,result,out){
 await result.publish(out);
 for(const [role,pin]of Object.entries(f.sidecar.logical_asset_map)){
  const emitted=result.additiveRelease[role],raw=await fs.readFile(path.join(out,emitted.path)),source=await fs.readFile(path.join(f.root,pin.path));
  assert.equal(raw.length,emitted.bytes);assert.equal(sha(raw),emitted.sha256);
  if(['ledger','patch'].includes(role)){
   const body=gunzipSync(raw),original=pin.encoding==='gzip'?gunzipSync(source):source;
   assert.equal(emitted.encoding,'gzip');assert.equal(body.length,emitted.decoded_bytes);assert.equal(sha(body),emitted.decoded_sha256);assert.deepEqual(body,original);
  }else assert.deepEqual(raw,source);
 }
 assert.deepEqual(await fs.readFile(path.join(out,result.additiveRelease.base_manifest.path)),f.originalManifest);
 assert.deepEqual(await fs.readFile(path.join(out,result.additiveRelease.owner_roster.path)),f.originalBounds);
}

test('ordinary current additive consumption emits exactly four selected assets and whole input inventory',async t=>{
 const f=await fixture(t),result=await prepareCurrentSelectedAdditive(f),out=path.join(f.root,'out');
 assert.deepEqual(result.reference_release,result.additiveRelease.effective_reference);assert.equal(result.referenceMetadata,undefined);
 assert.equal(result.additiveRelease.base_manifest.sha256,f.selectedGrid.sha256);assert.deepEqual(result.additiveRelease.base_reference,f.native);
 assert.equal(result.input_inventory.length,6);assert.ok(result.input_inventory.every(pin=>pin.whole_body_consumed&&pin.mode==='100644'&&/^[a-f0-9]{40}$/.test(pin.git_blob_oid)));
 await assertPublished(f,result,out);assert.deepEqual(await fs.readdir(out),['additive-repairs']);await assert.rejects(result.publish(out),/already exists/);
});

test('accepted whole reference metadata separates original N, current M and effective E without changing original assets',async t=>{
 const f=await fixture(t,{metadata:true}),before={...structuredClone(f.selectedGrid),bounds:Buffer.from(f.selectedGrid.bounds)},result=await prepareCurrentSelectedAdditive(f),out=path.join(f.root,'out');
 assert.equal(result.selection.release_id,f.native.id);assert.deepEqual(result.additiveRelease.base_reference,f.current);assert.deepEqual(result.reference_release,f.envelope.effective_reference);
 const pin=f.selection.reference_projection;
 assert.deepEqual(result.referenceMetadata,{version:1,asset:{path:'reference-metadata/current.json',bytes:pin.bytes,sha256:pin.sha256},native_reference:f.native,reference:f.current});
 assert.equal(result.input_inventory.length,7);assert.deepEqual(result.input_inventory.find(row=>row.path===pin.path),{...pin,mode:'100644',git_blob_oid:createHash('sha1').update('blob '+pin.bytes+'\0').update(await fs.readFile(path.join(f.root,pin.path))).digest('hex'),whole_body_consumed:true});
 await assertPublished(f,result,out);assert.deepEqual(await fs.readFile(path.join(out,result.referenceMetadata.asset.path)),await fs.readFile(path.join(f.root,pin.path)));
 assert.deepEqual(f.selectedGrid,before);assert.deepEqual(f.sidecar.base_selection,f.projection.native_selection);assert.equal(f.owners[0].province_id,'P');assert.equal(f.features[0].properties.parent_id,'Q');
});

test('ordinary no-projection consumption stays strict about native selection, parents, geometry and missing input',async t=>{
 const f=await fixture(t);
 await assert.rejects(prepareCurrentSelectedAdditive({...f,selectedGrid:{...f.selectedGrid,sha256:'0'.repeat(64)}}),/native selection differs/);
 await assert.rejects(prepareCurrentSelectedAdditive({...f,geographicRelease:{...f.geographicRelease,id:'geography:other'}}),/reference differs/);
 const changed=structuredClone(f.features);changed[0].properties.parent_id='Q';await assert.rejects(prepareCurrentSelectedAdditive({...f,features:changed}),/owner identity or parent/);
 changed[0].properties.parent_id='P';changed[0].geometry=rectangle(0,0,2,1);await assert.rejects(prepareCurrentSelectedAdditive({...f,features:changed}),/foreign base owner\/geometry/);
 await fs.unlink(path.join(f.root,f.sidecar.logical_asset_map.patch.path));await assert.rejects(prepareCurrentSelectedAdditive(f),{code:'ENOENT'});
});

test('reference projection pointer requires exact declared ordinary whole bytes',async t=>{
 const f=await fixture(t,{metadata:true}),pin={...f.selection.reference_projection};
 for(const mutate of [p=>p.bytes++,p=>p.sha256='0'.repeat(64),p=>p.path='../escape.json',p=>p.path='undeclared.json']){
  f.selection.reference_projection={...pin};mutate(f.selection.reference_projection);await saveSelection(f);await assert.rejects(prepareCurrentSelectedAdditive(f),/whole length|whole checksum|Undeclared/);
 }
 f.selection.reference_projection=pin;await saveSelection(f);
 const target=path.join(f.root,pin.path),raw=await fs.readFile(target);await fs.rename(target,target+'.retained');await fs.symlink(target+'.retained',target);
 await assert.rejects(prepareCurrentSelectedAdditive(f),/ordinary path/);await fs.unlink(target);await fs.writeFile(target,raw);
 await fs.unlink(target);await assert.rejects(prepareCurrentSelectedAdditive(f),{code:'ENOENT'});
});

test('reference metadata rejects stale current/native references and original source or roster pins',async t=>{
 const f=await fixture(t,{metadata:true}),original=structuredClone(f.projection);
 for(const mutate of [p=>p.native_reference.id='geography:foreign',p=>p.native_selection.source_map.sha256='0'.repeat(64),p=>p.native_selection.artifact_certificate.sha256='0'.repeat(64),p=>p.native_selection.review.sha256='0'.repeat(64),p=>p.original_owner_roster_sha256='0'.repeat(64),p=>p.hierarchy.before.sha256='0'.repeat(64),p=>p.reference.footprints_sha256='0'.repeat(64),p=>p.reference.id='geography:stale']){
  f.projection=structuredClone(original);mutate(f.projection);await saveProjection(f);await assert.rejects(prepareCurrentSelectedAdditive(f),/misidentifies|owner roster|hierarchy bytes|selected geographic release/);
 }
 f.projection=original;await saveProjection(f);
 await assert.rejects(prepareCurrentSelectedAdditive({...f,geographicRelease:f.native}),/selected geographic release/);
 f.selection.release_id=f.current.id;await saveSelection(f);await assert.rejects(prepareCurrentSelectedAdditive(f),/different native base/);
});

test('reference metadata admits only receipted actual parents and the complete current province inventory',async t=>{
 const f=await fixture(t,{metadata:true}),original=structuredClone(f.projection);
 for(const mutate of [p=>p.location_changes=[],p=>p.location_changes[0].before_properties.parent_id='wrong',p=>p.location_changes[0].after_properties.metadata.reference_corrections=[],p=>p.location_changes.push(structuredClone(p.location_changes[0])),p=>p.provinces=['P'],p=>p.provinces=['P','Q','unused']]){
  f.projection=structuredClone(original);mutate(f.projection);await saveProjection(f);await assert.rejects(prepareCurrentSelectedAdditive(f),/owner identity or parent|stale original parent|Non-parent|correction|duplicate|absent current province|empty or foreign province/,String(mutate));
 }
 f.projection=original;await saveProjection(f);
 const changed=structuredClone(f.features);changed[1].properties.parent_id='Q';await assert.rejects(prepareCurrentSelectedAdditive({...f,features:changed}),/owner identity or parent/);
 for(const mutate of [rows=>rows[0].pixelIndex=2,rows=>rows[0].id='foreign',rows=>rows.pop()]){const rows=structuredClone(f.features);mutate(rows);await assert.rejects(prepareCurrentSelectedAdditive({...f,features:rows}),/owner identity or parent|Incomplete/);}
});

test('metadata requires a new additive envelope and patch bound to current M rather than native N',async t=>{
 const f=await fixture(t,{metadata:true}),current=structuredClone(f.envelope.base_reference),effective=structuredClone(f.envelope.effective_reference);
 f.envelope.base_reference=f.native;await saveEnvelope(f);await assert.rejects(prepareCurrentSelectedAdditive(f),/reference differs from selected base/);
 f.envelope.base_reference=current;f.envelope.effective_reference.hierarchy_sha256=f.native.hierarchy_sha256;await saveEnvelope(f);await assert.rejects(prepareCurrentSelectedAdditive(f),/reference differs from selected base/);
 f.envelope.effective_reference=effective;f.patch.base_reference=f.native;await savePatch(f);await assert.rejects(prepareCurrentSelectedAdditive(f),/patch source\/ledger differs/);
});

test('projection cannot rebind the exact original base manifest or owner roster',async t=>{
 const f=await fixture(t,{metadata:true});
 await assert.rejects(prepareCurrentSelectedAdditive({...f,selectedGrid:{...f.selectedGrid,manifest:{...f.selectedGrid.manifest,size:17}}}),/base manifest differs/);
 const changed=Buffer.from(f.selectedGrid.bounds);changed[0]^=1;
 await assert.rejects(prepareCurrentSelectedAdditive({...f,selectedGrid:{...f.selectedGrid,bounds:changed}}),/owner roster differs/);
 const decoded=structuredClone(f.owners);decoded[0].bounds=[0,0,999,999];
 const raw=Buffer.from(JSON.stringify(decoded)),encoded=gzipSync(raw),pin=await write(f.root,'inputs/owners.json.gz',encoded);
 f.sidecar.logical_asset_map.owner_roster={...pin,encoding:'gzip',decoded_bytes:raw.length,decoded_sha256:sha(raw)};
 f.envelope.owner_roster={...logical('owners.json.gz',pin),encoding:'gzip',decoded_bytes:raw.length,decoded_sha256:sha(raw)};await saveEnvelope(f);
 await assert.rejects(prepareCurrentSelectedAdditive(f),/owner roster differs/);
});

test('coherently repinned invalid patch rows remain rejected with metadata applied',async t=>{
 const f=await fixture(t,{metadata:true});f.patch.rows[0].runs[0][2]=0;await savePatch(f);
 await assert.rejects(prepareCurrentSelectedAdditive(f),/Conflicting or foreign current additive run/);
});

test('both projection and additive output use the same all-assets ordinary destination admission',async t=>{
 const f=await fixture(t,{metadata:true}),result=await prepareCurrentSelectedAdditive(f),sentinel=path.join(f.root,'sentinel');await fs.mkdir(sentinel);await fs.writeFile(path.join(sentinel,'retained'),'original');
 for(const directory of ['reference-metadata','additive-repairs']){
  const out=path.join(f.root,'out-'+directory);await fs.mkdir(out);await fs.symlink(sentinel,path.join(out,directory));
  await assert.rejects(result.publish(out),/destination must be ordinary/);assert.deepEqual(await fs.readdir(sentinel),['retained']);assert.equal(await fs.readFile(path.join(sentinel,'retained'),'utf8'),'original');assert.deepEqual(await fs.readdir(out),[directory]);
 }
 const out=path.join(f.root,'existing');await fs.mkdir(path.join(out,'reference-metadata'),{recursive:true});await fs.writeFile(path.join(out,'reference-metadata/current.json'),'retained');
 await assert.rejects(result.publish(out),/already exists/);assert.deepEqual(await fs.readdir(out),['reference-metadata']);assert.equal(await fs.readFile(path.join(out,'reference-metadata/current.json'),'utf8'),'retained');
});

test('the selection itself must remain an ordinary file',async t=>{
 const f=await fixture(t),name=path.join(f.root,'data/ownership-selection.json');await fs.rename(name,name+'.retained');await fs.symlink(name+'.retained',name);
 await assert.rejects(prepareCurrentSelectedAdditive(f),/Current selection must be ordinary/);
});

// This exact byte boundary is the complete ledger rejected in hosted #2325.
// Whitespace padding changes transport bytes, not the fixture's native scope.
test('current packaging accepts the 34920857-byte ledger with exact whole custody',async t=>{
 const f=await fixture(t,{ledgerBytes:34920857}),result=await prepareCurrentSelectedAdditive(f);
 const ledger=result.input_inventory.find(row=>row.path===f.sidecar.logical_asset_map.ledger.path);
 assert.equal(ledger.bytes,34920857);assert.equal(ledger.whole_body_consumed,true);
 assert.equal(ledger.sha256,f.envelope.ledger.sha256);
 assert.equal(result.additiveRelease.ledger.decoded_bytes,34920857);
 assert.equal(result.additiveRelease.ledger.decoded_sha256,ledger.sha256);
 assert(result.additiveRelease.ledger.bytes<25*1024*1024);
 await result.publish(path.join(f.root,'published'));
 const emitted=await fs.readFile(path.join(f.root,'published',result.additiveRelease.ledger.path));
 assert.equal(emitted.length,result.additiveRelease.ledger.bytes);assert.equal(sha(gunzipSync(emitted)),ledger.sha256);
 const original=await fs.readFile(path.join(f.root,ledger.path));
 await fs.writeFile(path.join(f.root,ledger.path),original.subarray(0,-1));
 await assert.rejects(prepareCurrentSelectedAdditive(f),/whole length/);
 await fs.writeFile(path.join(f.root,ledger.path),original);
 original[original.length-1]=0x09;await fs.writeFile(path.join(f.root,ledger.path),original);
 await assert.rejects(prepareCurrentSelectedAdditive(f),/whole checksum/);
});


test('package-derived gzip preserves exact source bodies and effective identities deterministically',async t=>{
 const f=await fixture(t),pins=[f.selection.additive_release,f.sidecar.runtime_envelope,...Object.values(f.sidecar.logical_asset_map)];
 const original=await Promise.all(pins.map(pin=>fs.readFile(path.join(f.root,pin.path))));
 const first=await prepareCurrentSelectedAdditive(f),second=await prepareCurrentSelectedAdditive(f);
 assert.deepEqual(first.additiveRelease,second.additiveRelease);assert.deepEqual(first.reference_release,f.envelope.effective_reference);
 await assertPublished(f,first,path.join(f.root,'first'));await assertPublished(f,second,path.join(f.root,'second'));
 for(let i=0;i<pins.length;i++)assert.deepEqual(await fs.readFile(path.join(f.root,pins[i].path)),original[i]);
 for(const role of ['ledger','patch']){
  assert.equal(first.additiveRelease[role].decoded_sha256,f.envelope[role].sha256);
  assert.equal(first.additiveRelease[role].path,f.envelope[role].path+'.gz');
  assert.equal((await fs.stat(path.join(f.root,'first',f.envelope[role].path)).catch(()=>null)),null,'Raw delivery copy must not survive');
 }
});

test('already encoded source ledger and patch retain their exact transport without recompression',async t=>{
 const f=await fixture(t);
 for(const role of ['ledger','patch']){
  const source=f.sidecar.logical_asset_map[role],body=await fs.readFile(path.join(f.root,source.path)),encoded=gzipSync(body,{level:1});
  const pin=await write(f.root,source.path,encoded),fields={encoding:'gzip',decoded_bytes:body.length,decoded_sha256:sha(body)};
  f.sidecar.logical_asset_map[role]={...pin,...fields};f.envelope[role]={...logical(role+'.json.gz',pin),...fields};
 }
 await saveEnvelope(f);const result=await prepareCurrentSelectedAdditive(f);
 assert.deepEqual(result.additiveRelease,f.envelope);await assertPublished(f,result,path.join(f.root,'out'));
});

test('derived gzip path collision fails before publication and source mutation',async t=>{
 const f=await fixture(t);f.envelope.patch.path=f.envelope.ledger.path+'.gz';await saveEnvelope(f);
 const original=await fs.readFile(path.join(f.root,f.sidecar.runtime_envelope.path));
 await assert.rejects(prepareCurrentSelectedAdditive(f),/Duplicate native additive assets/);
 assert.deepEqual(await fs.readFile(path.join(f.root,f.sidecar.runtime_envelope.path)),original);
 assert.equal(await fs.stat(path.join(f.root,'out')).catch(()=>null),null);
});


for(const metadata of [false,true])test('cold selected-data checkout preserves reused current output '+(metadata?'with':'without')+' reference metadata',async t=>{
 const f=await fixture(t,{metadata}),definition=loadPackageInputs(f.root);
 const verification=['data/verification/body.json','research/geography/verification/body.json','coordination/engineering/verification/body.json'];
 definition.verification_paths=verification;
 for(const name of verification)await write(f.root,name,{verification_only:true});
 const expectations='coordination/engineering/current/selected-delivery-expectations.json';
 await write(f.root,expectations,{synthetic_checkout_operand:true});
 await write(f.root,'.github/package-inputs.json',definition);
 const git=(args,input)=>execFileSync('git',['-C',f.root,'-c','core.hooksPath='+os.devNull,
  '-c','user.name=Fixture','-c','user.email=fixture@example.invalid',...args],
  {encoding:'utf8',input,env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:os.devNull}});
 git(['init','-q']);await fs.appendFile(path.join(f.root,'.git/info/exclude'),'\nout-before/\nout-after/\n');
 git(['add','.']);git(['commit','-qm','Synthetic retained-output input boundary']);
 const source=committedPackageInputs(f.root,definition),before=await prepareCurrentSelectedAdditive(f),outBefore=path.join(f.root,'out-before');
 await assertPublished(f,before,outBefore);
 const entries=new Map(git(['ls-tree','-rz','HEAD']).split('\0').filter(Boolean).map(line=>{
  const [metadata,name]=line.split('\t'),[mode,type,sha]=metadata.split(' ');return [name,{mode,type,sha}];
 }));
 git(['sparse-checkout','set','--no-cone','--stdin'],selectedDataCheckoutPatterns(definition,entries,expectations).join('\n')+'\n');
 git(['checkout','--detach','-q','HEAD']);
 for(const name of verification)await assert.rejects(fs.stat(path.join(f.root,name)),{code:'ENOENT'});
 assert.deepEqual(committedPackageInputs(f.root,definition),source);
 const after=await prepareCurrentSelectedAdditive(f),outAfter=path.join(f.root,'out-after');
 const {publish:beforePublish,...beforeValues}=before,{publish:afterPublish,...afterValues}=after;
 assert.deepEqual(afterValues,beforeValues,'All current role reads, complete whole pins and effective output identities stay exact');
 await assertPublished(f,after,outAfter);
 for(const directory of await fs.readdir(outBefore))for(const name of await fs.readdir(path.join(outBefore,directory)))
  assert.deepEqual(await fs.readFile(path.join(outAfter,directory,name)),await fs.readFile(path.join(outBefore,directory,name)));
 await fs.unlink(path.join(f.root,f.sidecar.logical_asset_map.patch.path));
 await assert.rejects(prepareCurrentSelectedAdditive(f),{code:'ENOENT'});
});


import {preparePublicCloudflarePackage,PUBLIC_PACKAGE_RECEIPT} from '../scripts/build-cloudflare.mjs';
import {legacyPublicMapRelease} from '../hosted/cloudflare-access.js';
async function publicationFixture(t){
 const f=await fixture(t,{metadata:true});
 const release={...f.current,version:10,source_id:'fixture-source',reference_date:'2026-10-01',membership_sha256:'a'.repeat(64),location_ids_sha256:'b'.repeat(64),changes_sha256:'c'.repeat(64),expected_counts:{location:3}};
 const prior={...release,id:legacyPublicMapRelease,version:6};
 await write(f.root,'data/geographic-releases/index.json',{version:1,releases:[release]});
 const operation=await write(f.root,'.github/operations/neon-geographic-production.json',{fixture:'closed operation'});
 const definition=loadPackageInputs(f.root);definition.inputs.push('data/geographic-releases/','.github/operations/neon-geographic-production.json','package-lock.json');definition.generated_outputs=['dist/'];
 await write(f.root,'.github/package-inputs.json',definition);await write(f.root,'package-lock.json',{lockfileVersion:3});await write(f.root,'.github/workflows/worker-merge.yml','fixture producer body');
 const git=(...args)=>execFileSync('git',['-C',f.root,...args],{encoding:'utf8'}).trim();git('init','-q');git('add','.');git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','prepared pair');
 const receipt={version:1,status:'verified',mode:'geography-production',github:{head_sha:git('rev-parse','HEAD')},operation_sha256:operation.sha256,geography:{status:'published',target:release,prior}};
 const receiptFile='data/validation/neon-forward-migrations/receipt.json';await write(f.root,receiptFile,receipt);
 let builds=0,queries=0,live={...release,status:'published'},legacy=true;
 const fetchImpl=async(url,options)=>{queries++;assert.equal(options.redirect,'error');const u=new URL(url);if(u.pathname==='/api/geography/release'){assert.equal(u.searchParams.get('release_id'),release.id);return Response.json(live);}const page={release_id:legacy?prior.id:release.id,hierarchy_sha256:prior.hierarchy_sha256,footprints_sha256:prior.footprints_sha256};return Response.json(page,{headers:{'X-Atlas-Legacy-Map-Release':prior.id}});};
 const build=async()=>{builds++;await write(f.root,'dist/client/atlas-geography.json',{additiveRelease:{base_reference:f.current}});await write(f.root,'dist/client/assets/app.js','actual fixture output');await write(f.root,'dist/cloudflare/index.js','actual fixture Worker output');await write(f.root,'dist/cloudflare/wrangler.json',{name:'worldatlas-explorer',vars:{ATLAS_PUBLIC_READ_ONLY:'1',ATLAS_READ_ONLY:'1',ATLAS_CONTENT_BACKEND:'postgres'}});await write(f.root,'.cache/package-input-build.json',{version:1,kind:'cloudflare',preflight:{passed:true,errors:[],inputs:{head:git('rev-parse','HEAD')}},input_definition_sha256:sha(await fs.readFile(path.join(f.root,'.github/package-inputs.json')))});};
 return {...f,release,prior,receipt,receiptFile,git,args:{root:f.root,fetchImpl,build,env:{ATLAS_PUBLIC_READ_ONLY:'1'}},get builds(){return builds;},get queries(){return queries;},set live(value){live=value;},set legacy(value){legacy=value;}};
}
test('coordinated publication selects M not N/E, stops before build, and resumes exact retained output without rebuilding',async t=>{
 const f=await publicationFixture(t);assert.notEqual(f.native.id,f.release.id);assert.notEqual(f.envelope.effective_reference.id,f.release.id);
 for(const actual of [null,{...f.release,status:'staged'},{...f.release,status:'published',hierarchy_sha256:'f'.repeat(64)}]){f.live=actual;await assert.rejects(preparePublicCloudflarePackage(f.args));assert.equal(f.builds,0);}
 f.live={...f.release,status:'published'};f.legacy=false;await assert.rejects(preparePublicCloudflarePackage(f.args),/Previous live map pair/);assert.equal(f.builds,0);f.legacy=true;
 const built=await preparePublicCloudflarePackage(f.args);assert.equal(built.reused,false);assert.equal(f.builds,1);assert.equal(built.receipt.source.producer,undefined,'Owner publication output is not relabelled as a stock integration artifact');
 const resumed=await preparePublicCloudflarePackage(f.args);assert.equal(resumed.reused,true);assert.equal(f.builds,1);assert.deepEqual(resumed.receipt,built.receipt);
 await write(f.root,'package-lock.json',{lockfileVersion:3,changed:true});
 await assert.rejects(preparePublicCloudflarePackage(f.args),/Actual original source image differs/);
 f.git('add','package-lock.json');await assert.rejects(preparePublicCloudflarePackage(f.args),/Actual original source image differs/);
 f.git('restore','--staged','--worktree','package-lock.json');
 await write(f.root,'inputs/untracked.json',{unexpected:true});await assert.rejects(preparePublicCloudflarePackage(f.args),/Actual original source image differs/);await fs.unlink(path.join(f.root,'inputs/untracked.json'));
 assert.equal((await preparePublicCloudflarePackage(f.args)).reused,true);assert.equal(f.builds,1,'dirty, staged and untracked source changes never reuse or rebuild a package');
 await write(f.root,'dist/client/assets/app.js','substituted bytes');await assert.rejects(preparePublicCloudflarePackage(f.args),/output changed/);assert.equal(f.builds,1,'bad retained output cannot silently rebuild or publish');
});
test('coordinated publication refuses stale operation/source/configuration and uncompleted build without output custody',async t=>{
 const f=await publicationFixture(t);
 for(const change of [{status:'failed'},{operation_sha256:'f'.repeat(64)},{github:{head_sha:'f'.repeat(40)}}]){await write(f.root,f.receiptFile,{...f.receipt,...change});await assert.rejects(preparePublicCloudflarePackage(f.args),/source-bound geographic/);assert.equal(f.builds,0);}
 await write(f.root,f.receiptFile,f.receipt);
 await assert.rejects(preparePublicCloudflarePackage({...f.args,env:{ATLAS_PUBLIC_READ_ONLY:'0'}}),/read-only/);assert.equal(f.builds,0);
 await assert.rejects(preparePublicCloudflarePackage({...f.args,build:async()=>{throw Error('Actual builder interrupted');}}),/builder interrupted/);
 await assert.rejects(fs.stat(path.join(f.root,PUBLIC_PACKAGE_RECEIPT)),/ENOENT/);
 const result=await preparePublicCloudflarePackage(f.args);assert.equal(result.reused,false);assert.equal(f.builds,1);
 await assert.rejects(preparePublicCloudflarePackage({...f.args,env:{ATLAS_PUBLIC_READ_ONLY:'1',ATLAS_ACCESS_AUD:'changed'}}),/different source/);assert.equal(f.builds,1);
});

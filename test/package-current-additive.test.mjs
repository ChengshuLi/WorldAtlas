import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
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
async function fixture(t,{metadata=false}={}){
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
 const ledgerPin=await write(root,'inputs/ledger.json',ledger);
 const envelope={version:1,kind:'retained-native-base-plus-delta-v1',base_reference:current,effective_reference:{...current,id:'geography:effective'},base_manifest:logical('base-native-manifest.json',manifestPin),ledger:logical('ledger.json',ledgerPin),owner_roster:{...logical('owners.json.gz',rosterPin),encoding:'gzip',decoded_bytes:rosterRaw.length,decoded_sha256:sha(rosterRaw)}};
 envelope.effective_reference.footprints_sha256=additiveReleaseFootprintDigest(current,bindAdditiveLedgerFeatures(features,ledger,envelope,current));
 const patch={version:1,kind:'unassigned-native-cells-v1',base_reference:current,effective_reference:envelope.effective_reference,ledger_sha256:ledgerPin.sha256,rule_sha256:rule,rows:[{y:3,runs:[[3,5,1]]}]};
 const sidecar={version:2,kind:'retained-native-additive-selection-v2',base_selection:structuredClone(selection),logical_asset_map:{base_manifest:manifestPin,owner_roster:{...rosterPin,encoding:'gzip',decoded_bytes:rosterRaw.length,decoded_sha256:sha(rosterRaw)},ledger:ledgerPin}};
 const f={root,selection,sidecar,projection,patch,envelope,ledger,owners,originalFeatures,features,native,current,selectedGrid:{manifest,sha256:manifestPin.sha256,bounds},geographicRelease:{...current,prepared_at:'synthetic'},originalManifest:Buffer.from(JSON.stringify(manifest)),originalBounds:Buffer.from(bounds)};
 await savePatch(f);if(metadata)await saveProjection(f);return f;
}
async function assertPublished(f,result,out){
 await result.publish(out);
 for(const [role,pin]of Object.entries(f.sidecar.logical_asset_map))assert.deepEqual(await fs.readFile(path.join(out,result.additiveRelease[role].path)),await fs.readFile(path.join(f.root,pin.path)));
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

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {prepareReferenceMetadataProjection} from '../scripts/selected-reference-metadata.mjs';
import {scientificNativeSelection} from '../src/reference-metadata.js';
import {selectedDeliveryReference,finalizedSelection,prepareReferenceMetadata,composeAuthorities,sourceEvidence,jsonBytes,validateDeliverySelectionTransition,finalizeDelivery} from '../scripts/prepare-delivery-handoff.mjs';
import {compactContextInputs} from '../scripts/native-ownership/compact-context-inputs.mjs';
import {prepareCurrentSelectedAdditive} from '../scripts/package-current-additive.mjs';
import {requireAssemblyWithoutReferenceMetadata} from '../scripts/assemble-selected-package.mjs';
import {loadedBaseFootprintSha256,footprintValueSha256,bindAdditiveLedgerFeatures,additiveReleaseFootprintDigest} from '../src/effective-footprint.js';
const sha=raw=>createHash('sha256').update(raw).digest('hex'),commit='a'.repeat(40);
const plain=pin=>({path:pin.path,bytes:pin.bytes,sha256:pin.sha256});
const rectangle=x=>({type:'Polygon',coordinates:[[[x,0],[x+1,0],[x+1,1],[x,1],[x,0]]]});
async function fixture(t){
 const root=await fs.realpath(await fs.mkdtemp(path.join(os.tmpdir(),'atlas-metadata-wiring-')));t.after(()=>fs.rm(root,{recursive:true,force:true}));
 const bodies=new Map(),pins=new Map();
 async function put(name,value){const raw=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value));await fs.mkdir(path.dirname(path.join(root,name)),{recursive:true});await fs.writeFile(path.join(root,name),raw);const pin={commit,path:name,mode:'100644',git_blob_oid:createHash('sha1').update('blob '+raw.length+'\0').update(raw).digest('hex'),bytes:raw.length,sha256:sha(raw)};bodies.set(pin.sha256,raw);pins.set(name,pin);return pin;}
 const reader={pin:(version,name)=>{assert.equal(version,commit);assert.ok(pins.has(name),name);return pins.get(name);},read:pin=>{assert.ok(bodies.has(pin.sha256),pin.path);return bodies.get(pin.sha256);},json:pin=>JSON.parse(reader.read(pin))};
 const original=['A','B','C'].map((id,i)=>({type:'Feature',id,pixelIndex:i+1,properties:{id,name:id,parent_id:i===2?'Q':'P',metadata:{}},geometry:rectangle(i*2)}));
 const owners=original.map(f=>({id:f.id,index:f.pixelIndex,province_id:f.properties.parent_id,province_index:f.id==='C'?2:1,bounds:[f.pixelIndex-1,0,f.pixelIndex,1]}));
 const beforeGroups=[['c','continent',null],['s','subcontinent','c'],['r','region','s'],['a','area','r'],['P','province','a'],['Q','province','a']].map(([id,level,parent_id])=>({id,name:id,level,parent_id}));
 const afterGroups=structuredClone(beforeGroups);afterGroups.at(-1).name='Current Q';
 const beforeHierarchy=await put('inputs/hierarchy-before.json',beforeGroups),afterHierarchy=await put('inputs/hierarchy-after.json',afterGroups);
 const native={id:'geography:native',footprints_sha256:loadedBaseFootprintSha256(original),hierarchy_sha256:beforeHierarchy.sha256},current={...native,id:'geography:metadata',hierarchy_sha256:afterHierarchy.sha256};
 const rosterRaw=Buffer.from(JSON.stringify(owners)),roster=await put('inputs/owners.json.gz',gzipSync(rosterRaw));
 const latitudeRaw=Buffer.alloc(16*8),latitudePin=await put('inputs/latitudes.f64le.gz',gzipSync(latitudeRaw));
 const nativeLatitudes={...latitudePin,decoded_bytes:latitudeRaw.length,decoded_sha256:sha(latitudeRaw)};
 const manifest={coordinateBits:19,method:'native-linear-evenodd-first-owner-v1',native_latitudes:nativeLatitudes,geographic_release:native.id,footprints_sha256:native.footprints_sha256,hierarchy_sha256:native.hierarchy_sha256,size:16,original_assets:{bounds:{sha256:roster.sha256}}};
 const baseManifest=await put('inputs/base-manifest.json',manifest),selection={version:1,method:manifest.method,release_id:native.id,sha256:baseManifest.sha256,manifest_path:baseManifest.path,selected_geography:{path:'inputs/original-source-map.json',bytes:1,sha256:'b'.repeat(64)}};
 const currentFeatures=structuredClone(original),before=original[0].properties,after=currentFeatures[0].properties;
 after.parent_id='Q';after.metadata.reference_corrections=[{id:'A',action:'reparent',current_name:'A',current_parent_id:'P',new_parent_id:'Q',rationale:'Synthetic sourced correction',evidence:[{url:'https://example.invalid/reference',title:'Synthetic reference',inspected_fact:'A belongs to Q'}]}];
 const change={location_id:'A',before_properties:before,after_properties:after};
 const receipt=await put('inputs/receipt.json',{before_sha256:beforeHierarchy.sha256,after_sha256:afterHierarchy.sha256,footprints_sha256_before:native.footprints_sha256,footprints_sha256_after:native.footprints_sha256,reference_only:true,historical_claims_transferred:false,summary:{geometry_changes:0},relationships:[],source_evidence:[{url:'https://example.invalid/reference',source_sha256:'c'.repeat(64)}],before_units:beforeGroups,retired_units:[],group_changes:[{id:'Q',before:beforeGroups.at(-1),after:afterGroups.at(-1)}],changed_location_properties:[change]});
 const beforeSource=await put('inputs/source-before.json',{type:'FeatureCollection',features:original}),afterSource=await put('inputs/source-after.json',{type:'FeatureCollection',features:currentFeatures});
 const projection=prepareReferenceMetadataProjection({selection,manifest,owners,reference:current,hierarchy:{before:beforeHierarchy,after:afterHierarchy},receipts:[receipt],source_updates:[{logical_path:'data/geography/part-0.json',before:beforeSource,after:afterSource}],read:reader.read});
 const projectionPin=await put('inputs/projection.json',projection);selection.reference_projection=plain(projectionPin);
 const registry='d'.repeat(64),addition=rectangle(1),ledger={version:1,kind:'native-additive-repair-ledger-v1',rule_sha256:registry,base_reference:current,parent_inventory:{components:1,report_sha256:'e'.repeat(64),roster_sha256:'f'.repeat(64)},scope_ids:['gap'],assigned_cells:1,rows:[{component_id:'gap',disposition:'assigned',target_id:'A',pixelIndex:1,base_geometry:original[0].geometry,base_geometry_sha256:footprintValueSha256(original[0].geometry),geometry:addition,geometry_sha256:footprintValueSha256(addition),source_receipt_sha256:'1'.repeat(64),native_cells:1}]};
 const ledgerPin=await put('inputs/ledger.json',ledger),logical=(name,pin)=>({...plain(pin),path:'additive-repairs/'+name});
 const envelope={version:1,kind:'retained-native-base-plus-delta-v1',base_reference:current,effective_reference:{...current,id:'geography:effective'},base_manifest:logical('manifest.json',baseManifest),owner_roster:{...logical('owners.json.gz',roster),encoding:'gzip',decoded_bytes:rosterRaw.length,decoded_sha256:sha(rosterRaw)},ledger:logical('ledger.json',ledgerPin)};
 envelope.effective_reference.footprints_sha256=additiveReleaseFootprintDigest(current,bindAdditiveLedgerFeatures(currentFeatures,ledger,envelope,current));
 const patchPin=await put('inputs/patch.json',{version:1,kind:'unassigned-native-cells-v1',base_reference:current,effective_reference:envelope.effective_reference,ledger_sha256:ledgerPin.sha256,rule_sha256:registry,rows:[{y:3,runs:[[3,4,1]]}]});envelope.patch=logical('patch.json',patchPin);
 const envelopePin=await put('inputs/envelope.json',envelope),sidecar={version:2,kind:'retained-native-additive-selection-v2',base_selection:scientificNativeSelection(selection),runtime_envelope:plain(envelopePin),logical_asset_map:{base_manifest:plain(baseManifest),owner_roster:{...plain(roster),encoding:'gzip',decoded_bytes:rosterRaw.length,decoded_sha256:sha(rosterRaw)},ledger:plain(ledgerPin),patch:plain(patchPin)}};
 const sidecarPin=await put('inputs/sidecar.json',sidecar);selection.additive_release=plain(sidecarPin);await put('data/ownership-selection.json',selection);
 await put('.github/package-inputs.json',{version:1,inputs:['.github/package-inputs.json','data/ownership-selection.json','inputs/'],optional_inputs:[],verification_paths:[],generated_outputs:[]});
 const referenceMetadata={version:1,asset:{...plain(projectionPin),path:'reference-metadata/current.json'},native_reference:native,reference:current};
 const atlas={parts:['geography/catalog.json.gz'],additiveRelease:envelope,reference_release:envelope.effective_reference,referenceMetadata};
 const originalRoot=path.join(root,'retained'),output={files:[]};
 const outputBody=async(name,raw)=>{const pin=await put('retained/dist/client/'+name,raw);output.files.push({path:'dist/client/'+name,bytes:pin.bytes,sha256:pin.sha256});};
 for(const role of ['base_manifest','owner_roster','ledger','patch'])await outputBody(envelope[role].path,reader.read(pins.get(sidecar.logical_asset_map[role].path)));
 await outputBody(referenceMetadata.asset.path,reader.read(projectionPin));await outputBody(atlas.parts[0],gzipSync(Buffer.from(JSON.stringify(currentFeatures.map(f=>({...f,geometry:null}))))));
 const originalIndex=await put('data/geographic-releases/index.json',{version:1,original_catalog_sha256:'7'.repeat(64),releases:[{...native,version:1}]});
 const releases=await put('data/geographic-releases/releases-v2.json.gz',gzipSync(Buffer.from(JSON.stringify({version:1,original_catalog_sha256:'7'.repeat(64),releases:[{...native,version:1},{...current,version:2,metadata:{metadata_migration_sha256:{correction:receipt.sha256}}}]}))));
 await put('data/geographic-releases/current-manifest.json',{path:'releases-v2.json.gz',sha256:releases.sha256,predecessor_index_sha256:originalIndex.sha256});
 const preparationConfig={version:1,selector:pins.get('data/ownership-selection.json'),native_manifest:baseManifest,owner_roster:{...roster,encoding:'gzip',decoded_bytes:rosterRaw.length,decoded_sha256:sha(rosterRaw)},current_release:{commit,path:'data/geographic-releases/current-manifest.json'},hierarchy:projection.hierarchy,receipts:projection.receipts,source_updates:projection.source_updates};
 return {root,reader,put,pins,bodies,selection,sidecar,projection,projectionPin,manifest,owners,original,currentFeatures,native,current,referenceMetadata,atlas,originalRoot,preparationConfig,outputManifest:{source:{selection:structuredClone(selection)},output},metadataApplication:{projection,selection,manifest,read:reader.read}};
}

test('delivery finalization preserves the exact metadata pointer while the sidecar stays scientific N',async t=>{
 const f=await fixture(t),originalRaw=Buffer.from(JSON.stringify(f.selection,null,2)+'\n'),next={path:'inputs/next-sidecar.json',bytes:123,sha256:'9'.repeat(64)};
 const raw=finalizedSelection(originalRaw,f.sidecar,next),selection=JSON.parse(raw);
 assert.deepEqual(selection.reference_projection,f.selection.reference_projection);assert.deepEqual(scientificNativeSelection(selection),f.sidecar.base_selection);assert.equal(finalizedSelection(raw,f.sidecar,next),raw);
 assert.deepEqual(selectedDeliveryReference(f.selection,f.manifest,f.reader,commit),{native:f.native,reference:f.current,projectionPin:f.projectionPin});
 const stale=structuredClone(f.selection);stale.reference_projection.sha256='0'.repeat(64);assert.throws(()=>selectedDeliveryReference(stale,f.manifest,f.reader,commit),/whole identity differs/);
 const changed=structuredClone(f.sidecar);changed.base_selection.release_id='geography:foreign';assert.throws(()=>finalizedSelection(originalRaw,changed,next),/complete original base/);
});

test('compact current context derives receipted parents from complete projection inputs and keeps native geometry and indices',async t=>{
 const f=await fixture(t),before=structuredClone(f.owners),source=JSON.stringify(f.currentFeatures);
 assert.throws(()=>compactContextInputs(f.currentFeatures,f.owners,f.native.footprints_sha256),/parent differs/);
 const compact=compactContextInputs(f.currentFeatures,f.owners,f.native.footprints_sha256,{metadataApplication:f.metadataApplication});
 assert.deepEqual(compact.features.map(row=>[row.id,row.pixelIndex,row.properties.parent_id]),[['A',1,'Q'],['B',2,'P'],['C',3,'Q']]);
 assert.deepEqual(compact.features.map(row=>row.geometry),f.original.map(row=>row.geometry));assert.deepEqual(f.owners,before);assert.equal(JSON.stringify(f.currentFeatures),source);
 const drift=structuredClone(f.currentFeatures);drift[0].properties.parent_id='P';assert.throws(()=>compactContextInputs(drift,f.owners,f.native.footprints_sha256,{metadataApplication:f.metadataApplication}),/parent differs/);
 const bad={...f.metadataApplication,read:pin=>pin.path==='inputs/receipt.json'?Buffer.from('{}'):f.reader.read(pin)};assert.throws(()=>compactContextInputs(f.currentFeatures,f.owners,f.native.footprints_sha256,{metadataApplication:bad}),/Whole reference metadata input differs/);
 const projection=structuredClone(f.projection);projection.location_changes=[];assert.throws(()=>compactContextInputs(f.currentFeatures,f.owners,f.native.footprints_sha256,{metadataApplication:{...f.metadataApplication,projection}}),/changes differ/);
});

test('metadata application declines retained assembly and requires the existing full build fallback',async t=>{
 const f=await fixture(t);
 assert.doesNotThrow(()=>requireAssemblyWithoutReferenceMetadata(scientificNativeSelection(f.selection)));
 assert.throws(()=>requireAssemblyWithoutReferenceMetadata(f.selection),/requires a full build/);
 assert.throws(()=>requireAssemblyWithoutReferenceMetadata({...f.selection,reference_projection:null}),/requires a full build/);
});

test('reference-metadata preparation derives one canonical application from stock receipts and the actual current release registry',async t=>{
 const f=await fixture(t),result=prepareReferenceMetadata(f.preparationConfig,f.reader);
 assert.deepEqual(Object.keys(result.products),['reference-metadata.json']);assert.deepEqual(JSON.parse(result.products['reference-metadata.json']),f.projection);
 assert.equal(result.input_inventory.length,11);assert.ok(result.input_inventory.every(pin=>pin.whole_body_consumed&&pin.roles.length>0&&/^[a-f0-9]{40}$/.test(pin.git_blob_oid)));
 for(const name of ['data/ownership-selection.json','data/geographic-releases/current-manifest.json','data/geographic-releases/index.json','data/geographic-releases/releases-v2.json.gz','inputs/receipt.json','inputs/source-before.json','inputs/source-after.json'])assert.ok(result.input_inventory.some(pin=>pin.path===name),name);
 assert.deepEqual(prepareReferenceMetadata(f.preparationConfig,f.reader),result);
});

test('reference-metadata preparation rejects handwritten current identities, extra config, stale native/owner pins and incomplete source receipts',async t=>{
 const f=await fixture(t);
 for(const mutate of [c=>c.reference=f.current,c=>c.current_release={...c.current_release,reference:f.current},c=>c.native_manifest.sha256='0'.repeat(64),c=>c.owner_roster.sha256='0'.repeat(64),c=>c.receipts=[],c=>c.source_updates=[]]){const config=structuredClone(f.preparationConfig);mutate(config);assert.throws(()=>prepareReferenceMetadata(config,f.reader));}
 const pointer=f.reader.json(f.pins.get('data/geographic-releases/current-manifest.json'));pointer.sha256='0'.repeat(64);await f.put('data/geographic-releases/current-manifest.json',pointer);
 assert.throws(()=>prepareReferenceMetadata(f.preparationConfig,f.reader),/release whole identity differs/);
});

// One old and one newly qualified native component exercise real composition.
// Original science remains N; only the emitted application's reference becomes M.
async function compositionFixture(t,{prior='native'}={}){
 const f=await fixture(t),base=prior==='native'?f.native:f.current;
 const rule=await f.put('inputs/old-rule.json',jsonBytes({original:'rule'})),authorityPin=await f.put('inputs/old-authority.json',{original:'authority'});
 const authority={policy_id:'retained-source-literal-additions',policy_version:1,rule_preimage:rule,rule_sha256:rule.sha256,source_authority:authorityPin};
 const entry={authority_sha256:sha(jsonBytes(authority)),...authority},registry={version:1,kind:'retained-rule-authority-registry-v1',entries:[entry]},registryPin=await f.put('inputs/registry-v2.json',jsonBytes(registry));
 const oldRow={representation:'native-cells',component_id:'old-native',target_id:'A',pixelIndex:1,disposition:'assigned',base_geometry:f.original[0].geometry,base_geometry_sha256:footprintValueSha256(f.original[0].geometry),native_rows:[{y:2,runs:[[1,2,1]]}],native_bounds:[0,0,1,1],native_cells:1,source_receipt_sha256:'f'.repeat(64),authority_sha256:entry.authority_sha256,rule_sha256:entry.rule_sha256};
 const rebind=await f.put('inputs/original-rebind.json',{original:'qualified-rebind'});
 const priorLedger={version:2,kind:'native-additive-repair-ledger-v2',authority_registry_sha256:registryPin.sha256,parent_inventory:{components:1,report_sha256:'e'.repeat(64),roster_sha256:'f'.repeat(64)},rows:[oldRow],scope_ids:[oldRow.component_id],current_rebind:rebind,current_targets:[{target_id:'A',pixelIndex:1,geometry:f.original[0].geometry,geometry_sha256:footprintValueSha256(f.original[0].geometry)}]};
 const ledgerPin=await f.put('inputs/ledger-v2.json',jsonBytes(priorLedger));
 const priorPatch={version:2,kind:'unassigned-native-cells-v1',base_reference:base,effective_reference:{...base,id:'geography:prior-effective',footprints_sha256:'4'.repeat(64)},ledger_sha256:ledgerPin.sha256,authority_registry_sha256:registryPin.sha256,rows:oldRow.native_rows};
 const patchPin=await f.put('inputs/patch-v2.json',jsonBytes(priorPatch)),logical=(name,pin)=>({...plain(pin),path:'additive-repairs/'+name});
 const assets={base_manifest:f.preparationConfig.native_manifest,owner_roster:f.preparationConfig.owner_roster,ledger:ledgerPin,patch:patchPin};
 const envelope={version:2,kind:'retained-native-base-plus-delta-v2',base_reference:base,effective_reference:priorPatch.effective_reference,base_manifest:logical('manifest.json',assets.base_manifest),owner_roster:{...logical('owners.json.gz',assets.owner_roster),encoding:'gzip',decoded_bytes:assets.owner_roster.decoded_bytes,decoded_sha256:assets.owner_roster.decoded_sha256},ledger:logical('ledger-v2.json',ledgerPin),patch:logical('patch-v2.json',patchPin)};
 const envelopePin=await f.put('inputs/envelope-v2.json',{additiveRelease:envelope,reference_release:envelope.effective_reference});
 const sidecar={version:2,kind:'retained-native-additive-selection-v2',base_selection:scientificNativeSelection(f.selection),authority_registry:registryPin,runtime_envelope:envelopePin,logical_asset_map:assets};
 const sidecarPin=await f.put('inputs/sidecar-v2.json',sidecar);f.selection.additive_release=plain(sidecarPin);let selector=await f.put('data/ownership-selection.json',f.selection);
 async function incoming({scientificBase=f.native}={}){
  const evidence={version:1,kind:'source-target-native-evidence-v1',base_reference:scientificBase,native_contract:Object.fromEntries(['size','coordinateBits','method','native_latitudes','hierarchy_sha256','original_assets'].map(key=>[key,f.manifest[key]])),physical_evidence:{sha256:'f'.repeat(64)},targets:[{id:'source:A',target_id:'A',pixelIndex:1,source_family:'fixture',base_geometry:f.original[0].geometry,source_receipt_sha256:'f'.repeat(64)}]};
  const source=await f.put('inputs/new-evidence.json',evidence),candidate={rows:[{y:3,runs:[[2,4,1]]}]},candidatePin=await f.put('inputs/new-native-patch.json',candidate);
  const binding={version:1,kind:'source-target-native-custody-v1',source_evidence:source,native_patch:candidatePin},preimage={...binding,kind:'source-target-native-rule-v1'};
  const bindingPin=await f.put('inputs/new-binding.json',jsonBytes(binding)),rulePin=await f.put('inputs/new-rule.json',jsonBytes(preimage));
  const {authority_sha256,rule_sha256,...literal}=oldRow,row={...literal,component_id:'source-target:'+sha(jsonBytes({target_id:'A',evidence:source.sha256})),native_rows:candidate.rows,native_cells:2};
  const construction=await f.put('inputs/new-construction.json',{component_ids:[row.component_id],ledger_rows:[row],rule_sha256:rulePin.sha256});
  return {version:1,selector,rule_preimage:rulePin,source_authority:bindingPin,ledger:construction,native_patch:candidatePin,effective_release_id:'geography:next-effective'};
 }
 const config=await incoming();
 return {...f,sidecar,envelope,priorLedger,priorPatch,config,incoming,async savePrior(){const pin=await f.put(envelopePin.path,{additiveRelease:envelope,reference_release:envelope.effective_reference});sidecar.runtime_envelope=pin;const hook=await f.put(sidecarPin.path,sidecar);f.selection.additive_release=plain(hook);selector=await f.put('data/ownership-selection.json',f.selection);config.selector=selector;},async saveProjection(projection){const pin=await f.put(f.projectionPin.path,projection);f.selection.reference_projection=plain(pin);selector=await f.put('data/ownership-selection.json',f.selection);config.selector=selector;}};
}

for(const prior of ['native','current'])test('composition bridges prior '+prior+' to M while retaining every inherited row and incoming scientific N',async t=>{
 const f=await compositionFixture(t,{prior}),products=composeAuthorities(f.config,f.reader),ledger=JSON.parse(products['selected-ledger.json']),patch=JSON.parse(products['patch.json']),wrapped=JSON.parse(products['runtime-envelope.json']),envelope=wrapped.additiveRelease;
 assert.deepEqual(envelope.base_reference,f.current);assert.deepEqual(patch.base_reference,f.current);assert.equal(envelope.effective_reference.hierarchy_sha256,f.current.hierarchy_sha256);assert.deepEqual(patch.effective_reference,envelope.effective_reference);
 assert.deepEqual(ledger.rows.find(row=>row.component_id===f.priorLedger.rows[0].component_id),f.priorLedger.rows[0]);
 for(const key of ['parent_inventory','current_rebind','current_targets'])assert.deepEqual(ledger[key],f.priorLedger[key]);
 assert.deepEqual(envelope.base_manifest,f.envelope.base_manifest);assert.deepEqual(envelope.owner_roster,f.envelope.owner_roster);assert.deepEqual(patch.rows,[...f.priorPatch.rows,{y:3,runs:[[2,4,1]]}]);
 assert.equal(envelope.effective_reference.footprints_sha256,additiveReleaseFootprintDigest(f.current,bindAdditiveLedgerFeatures(f.currentFeatures,ledger,envelope,f.current)));
 const output=JSON.parse((await sourceEvidence({version:1,selector:{commit,path:'data/ownership-selection.json'},source_evidence:{version:1,kind:'source-target-native-evidence-v1'}},f.reader))['source-evidence.json']);
 assert.deepEqual(output.base_reference,f.native);assert.equal(output.native_contract.hierarchy_sha256,f.native.hierarchy_sha256);
 const mistaken=await f.incoming({scientificBase:f.current});assert.throws(()=>composeAuthorities(mistaken,f.reader),/baseline\/contract/);
});

test('composition refuses unknown prior bases, mixed prior hierarchy, changed geometry and transferred history under coherent new pins',async t=>{
 const f=await compositionFixture(t),old=structuredClone(f.envelope);
 f.envelope.base_reference={...f.native,id:'geography:foreign'};await f.savePrior();assert.throws(()=>composeAuthorities(f.config,f.reader),/Prior cumulative reference/);
 Object.assign(f.envelope,structuredClone(old));f.envelope.effective_reference.hierarchy_sha256=f.current.hierarchy_sha256;await f.savePrior();assert.throws(()=>composeAuthorities(f.config,f.reader),/Prior cumulative reference/);
 Object.assign(f.envelope,structuredClone(old));await f.savePrior();
 const source=JSON.parse(f.reader.read(f.projection.source_updates[0].after));source.features[0].geometry=rectangle(10);const sourcePin=await f.put('inputs/changed-after-source.json',source),projection=structuredClone(f.projection);projection.source_updates[0].after=sourcePin;await f.saveProjection(projection);
 assert.throws(()=>composeAuthorities(f.config,f.reader),/geometry/);
 const receipt=JSON.parse(f.reader.read(f.projection.receipts[0]));receipt.historical_claims_transferred=true;const receiptPin=await f.put('inputs/transferred-receipt.json',receipt),history=structuredClone(f.projection);history.receipts[0]=receiptPin;await f.saveProjection(history);
 assert.throws(()=>composeAuthorities(f.config,f.reader),/non-metadata reference receipt/);
});

test('delivery evidence compares scientific selectors and fully qualifies a changed metadata pointer',async t=>{
 const f=await compositionFixture(t),original={selection:scientificNativeSelection(f.selection),selector:{commit},sidecar:f.sidecar},current={selection:f.selection,selector:{commit},sidecar:f.sidecar};
 validateDeliverySelectionTransition(original,current,f.reader);
 const changed={...current,selection:{...f.selection,release_id:'geography:foreign'}};assert.throws(()=>validateDeliverySelectionTransition(original,changed,f.reader),/Delivery base/);
 const receipt=JSON.parse(f.reader.read(f.projection.receipts[0]));receipt.historical_claims_transferred=true;const pin=await f.put('inputs/bad-evidence-receipt.json',receipt),projection=structuredClone(f.projection);projection.receipts[0]=pin;await f.saveProjection(projection);
 assert.throws(()=>validateDeliverySelectionTransition(original,current,f.reader),/non-metadata reference receipt/);
});

test('composition qualification passes original encoded whole source bytes to the existing projection validator',async t=>{
 const f=await compositionFixture(t),projection=structuredClone(f.projection);
 for(const role of ['before','after']){
  const raw=f.reader.read(projection.source_updates[0][role]),pin=await f.put('inputs/encoded-source-'+role+'.json.gz',gzipSync(raw));
  projection.source_updates[0][role]={...pin,encoding:'gzip',decoded_bytes:raw.length,decoded_sha256:sha(raw)};
 }
 await f.saveProjection(projection);const result=composeAuthorities(f.config,f.reader);
 assert.deepEqual(JSON.parse(result['runtime-envelope.json']).additiveRelease.base_reference,f.current);
 assert.deepEqual(f.reader.read(f.sidecar.logical_asset_map.owner_roster),f.reader.read(f.preparationConfig.owner_roster));
});

// Exercise both production boundaries, substituting only whole immutable Git
// transport with the bounded fixture reader. No package declarations or final
// selector are synthesized after finalizeDelivery emits the actual products.
test('actual finalizer declares a fresh M projection and its exact seven-body output is consumable by ordinary packaging',async t=>{
 const f=await compositionFixture(t,{prior:'current'}),prefix='coordination/engineering/metadata-finalize-consumption/';
 f.reader.git=(...args)=>{assert.deepEqual(args,['rev-parse','HEAD']);return Buffer.from(commit);};
 f.reader.hasPath=(version,name)=>{assert.equal(version,commit);return f.pins.has(name);};
 const originalManifest=Buffer.from(f.reader.read(f.preparationConfig.native_manifest)),originalRoster=Buffer.from(f.reader.read(f.preparationConfig.owner_roster));
 const projectionPin=await f.put(prefix+'reference-metadata.json',f.projection);f.selection.reference_projection=plain(projectionPin);
 const selector=await f.put('data/ownership-selection.json',f.selection),baselinePin=f.pins.get('.github/package-inputs.json'),baseline=f.reader.json(baselinePin);
 assert.ok(!baseline.inputs.some(name=>name===projectionPin.path||name.endsWith('/')&&projectionPin.path.startsWith(name)));
 const custody=await f.put('inputs/finalize-custody.json',{whole:'retained custody'}),operating=await f.put('inputs/finalize-operating.json',{execution_custody:{terminal:custody}});
 const rebind=await f.put('inputs/finalize-rebind.json',{request:custody,facts:custody,publication:custody,result:custody,operating});
 const ledger={...f.priorLedger,current_rebind:rebind},ledgerPin=await f.put(prefix+'selected-ledger.json',jsonBytes(ledger));
 const envelope={...structuredClone(f.envelope),ledger:{...f.envelope.ledger,bytes:ledgerPin.bytes,sha256:ledgerPin.sha256}};
 const effective={...f.current,id:'geography:finalized-effective',footprints_sha256:additiveReleaseFootprintDigest(f.current,bindAdditiveLedgerFeatures(f.currentFeatures,ledger,envelope,f.current))};
 envelope.effective_reference=effective;
 const patchPin=await f.put(prefix+'patch.json',jsonBytes({...f.priorPatch,base_reference:f.current,effective_reference:effective,ledger_sha256:ledgerPin.sha256}));
 envelope.patch={...envelope.patch,bytes:patchPin.bytes,sha256:patchPin.sha256};
 const runtimeEnvelope=await f.put(prefix+'runtime-envelope.json',{reference_release:effective,additiveRelease:envelope}),sidecarPath=prefix+'selection-sidecar.json';
 const config={version:1,selector,package_inputs:baselinePin,new_prefix:prefix,sidecar_output:sidecarPath,registry:f.sidecar.authority_registry,ledger:ledgerPin,selected_ledger:ledgerPin,rebind,patch:patchPin,runtime_envelope:runtimeEnvelope};
 const products=finalizeDelivery(config,f.reader),definition=JSON.parse(products['package-inputs.json']),selection=JSON.parse(products['ownership-selection.json']),sidecar=JSON.parse(products['selection-sidecar.json']);
 assert.deepEqual(definition.inputs.slice(0,baseline.inputs.length),baseline.inputs);
 assert.ok(definition.inputs.includes(projectionPin.path),'The actual consumed projection must be declared, beyond preparation evidence');
 assert.ok(JSON.parse(products['package-roles.json']).paths.some(pin=>pin.path===projectionPin.path));
 const currentPaths=[sidecarPath,runtimeEnvelope.path,...Object.values(sidecar.logical_asset_map).map(pin=>pin.path),projectionPin.path];
 assert.equal(new Set(currentPaths).size,7);
 assert.deepEqual(definition.inputs.slice(baseline.inputs.length),currentPaths.filter(name=>!baseline.inputs.some(old=>old===name||old.endsWith('/')&&name.startsWith(old))).sort());
 assert.deepEqual(selection.reference_projection,plain(projectionPin));assert.equal(selection.release_id,f.native.id);assert.deepEqual(sidecar.base_selection,scientificNativeSelection(f.selection));
 await f.put(sidecarPath,products['selection-sidecar.json']);await f.put('data/ownership-selection.json',products['ownership-selection.json']);await f.put('.github/package-inputs.json',products['package-inputs.json']);
 const args={root:f.root,selectedGrid:{manifest:f.manifest,sha256:f.selection.sha256,bounds:originalRoster},geographicRelease:f.current,features:f.currentFeatures};
 const result=await prepareCurrentSelectedAdditive(args);
 assert.equal(result.input_inventory.length,7);assert.deepEqual(result.input_inventory.map(pin=>pin.path).sort(),[...currentPaths].sort());
 assert.deepEqual(result.referenceMetadata.reference,f.current);assert.deepEqual(result.referenceMetadata.native_reference,f.native);assert.deepEqual(result.additiveRelease.base_reference,f.current);assert.equal(f.currentFeatures[0].properties.parent_id,'Q');assert.equal(f.owners[0].province_id,'P');
 const destination=path.join(f.root,'finalized-package');await result.publish(destination);
 assert.deepEqual(await fs.readFile(path.join(destination,result.referenceMetadata.asset.path)),f.reader.read(projectionPin));
 assert.deepEqual(await fs.readFile(path.join(destination,result.additiveRelease.base_manifest.path)),originalManifest);assert.deepEqual(await fs.readFile(path.join(destination,result.additiveRelease.owner_roster.path)),originalRoster);
 await f.put('.github/package-inputs.json',{...definition,inputs:definition.inputs.filter(name=>name!==projectionPin.path)});
 await assert.rejects(prepareCurrentSelectedAdditive(args),/Undeclared current additive input/);
 assert.deepEqual(await fs.readFile(path.join(f.root,f.preparationConfig.native_manifest.path)),originalManifest);assert.deepEqual(await fs.readFile(path.join(f.root,f.preparationConfig.owner_roster.path)),originalRoster);
});

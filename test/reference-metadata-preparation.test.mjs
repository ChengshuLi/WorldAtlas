import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {prepareReferenceMetadataProjection} from '../scripts/selected-reference-metadata.mjs';
import {scientificNativeSelection} from '../src/reference-metadata.js';
import {prepareReferenceMetadata} from '../scripts/prepare-delivery-handoff.mjs';
import {compactContextInputs} from '../scripts/native-ownership/compact-context-inputs.mjs';
import {loadedBaseFootprintSha256} from '../src/effective-footprint.js';
const sha=raw=>createHash('sha256').update(raw).digest('hex'),commit='a'.repeat(40);
const plain=pin=>({path:pin.path,bytes:pin.bytes,sha256:pin.sha256});
const rectangle=x=>({type:'Polygon',coordinates:[[[x,0],[x+1,0],[x+1,1],[x,1],[x,0]]]});
async function fixture(t,{rosterBytes,rosterGzip=true,aliasSeed=false}={}){
 const root=await fs.realpath(await fs.mkdtemp(path.join(os.tmpdir(),'atlas-metadata-wiring-')));t.after(()=>fs.rm(root,{recursive:true,force:true}));
 const bodies=new Map(),pins=new Map();
 async function put(name,value){const raw=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value));await fs.mkdir(path.dirname(path.join(root,name)),{recursive:true});await fs.writeFile(path.join(root,name),raw);const pin={commit,path:name,mode:'100644',git_blob_oid:createHash('sha1').update('blob '+raw.length+'\0').update(raw).digest('hex'),bytes:raw.length,sha256:sha(raw)};bodies.set(pin.sha256,raw);pins.set(name,pin);return pin;}
 const reader={pin:(version,name)=>{assert.equal(version,commit);assert.ok(pins.has(name),name);return pins.get(name);},read:pin=>{assert.ok(bodies.has(pin.sha256),pin.path);return bodies.get(pin.sha256);},json:pin=>JSON.parse(reader.read(pin))};
 const original=['A','B','C'].map((id,i)=>({type:'Feature',id,pixelIndex:i+1,properties:{id,name:id,parent_id:i===2?'Q':'P',metadata:{}},geometry:rectangle(i*2)}));
 if(aliasSeed)for(const feature of original){feature.properties.reference_owner='Recorded winner';Object.assign(feature.properties.metadata,{reference_polity:'Stale alias',reference_owner_id:'owner:Q1',reference_owner_evidence:{winner:{owner_id:'owner:Q1',name:'Recorded winner',share:.75}},semantic_review:{status:'open'}});}
 const owners=original.map(f=>({id:f.id,index:f.pixelIndex,province_id:f.properties.parent_id,province_index:f.id==='C'?2:1,bounds:[f.pixelIndex-1,0,f.pixelIndex,1]}));
 const beforeGroups=[['c','continent',null],['s','subcontinent','c'],['r','region','s'],['a','area','r'],['P','province','a'],['Q','province','a']].map(([id,level,parent_id])=>({id,name:id,level,parent_id}));
 const afterGroups=structuredClone(beforeGroups);afterGroups.at(-1).name='Current Q';
 const beforeHierarchy=await put('inputs/hierarchy-before.json',beforeGroups),afterHierarchy=await put('inputs/hierarchy-after.json',afterGroups);
 const native={id:'geography:native',footprints_sha256:loadedBaseFootprintSha256(original),hierarchy_sha256:beforeHierarchy.sha256},current={...native,id:'geography:metadata',hierarchy_sha256:afterHierarchy.sha256};
 const ownerJson=Buffer.from(JSON.stringify(owners)),rosterRaw=rosterBytes===undefined?ownerJson:Buffer.concat([ownerJson,Buffer.alloc(rosterBytes-ownerJson.length,32)]);
 const roster=await put('inputs/owners.json.gz',rosterGzip?gzipSync(rosterRaw):rosterRaw);
 const latitudeRaw=Buffer.alloc(16*8),latitudePin=await put('inputs/latitudes.f64le.gz',gzipSync(latitudeRaw));
 const nativeLatitudes={...latitudePin,decoded_bytes:latitudeRaw.length,decoded_sha256:sha(latitudeRaw)};
 const manifest={coordinateBits:19,method:'native-linear-evenodd-first-owner-v1',native_latitudes:nativeLatitudes,geographic_release:native.id,footprints_sha256:native.footprints_sha256,hierarchy_sha256:native.hierarchy_sha256,size:16,original_assets:{bounds:{sha256:roster.sha256}}};
 const baseManifest=await put('inputs/base-manifest.json',manifest),selection={version:1,method:manifest.method,release_id:native.id,sha256:baseManifest.sha256,manifest_path:baseManifest.path,selected_geography:{path:'inputs/original-source-map.json',bytes:1,sha256:'b'.repeat(64)}};
 const currentFeatures=structuredClone(original),before=original[0].properties,after=currentFeatures[0].properties;
 after.parent_id='Q';after.metadata.reference_corrections=[{id:'A',action:'reparent',current_name:'A',current_parent_id:'P',new_parent_id:'Q',rationale:'Synthetic sourced correction',evidence:[{url:'https://example.invalid/reference',title:'Synthetic reference',inspected_fact:'A belongs to Q'}]}];
 const change={location_id:'A',before_properties:before,after_properties:after};
 const receipt=await put('inputs/receipt.json',{before_sha256:beforeHierarchy.sha256,after_sha256:afterHierarchy.sha256,footprints_sha256_before:native.footprints_sha256,footprints_sha256_after:native.footprints_sha256,reference_only:true,historical_claims_transferred:false,summary:{geometry_changes:0},relationships:[],source_evidence:[{url:'https://example.invalid/reference',source_sha256:'c'.repeat(64)}],before_units:beforeGroups,retired_units:[],group_changes:[{id:'Q',before:beforeGroups.at(-1),after:afterGroups.at(-1)}],changed_location_properties:[change]});
 const beforeSource=await put('data/geography/part-0.json',{type:'FeatureCollection',features:original}),afterSource=await put('inputs/source-after.json',{type:'FeatureCollection',features:currentFeatures});
 const sourceBank=await put('inputs/original-source-map.json',{version:1,kind:'complete-world-index-with-exact-encoded-overrides',release_id:native.id,native_manifest_sha256:baseManifest.sha256,footprints_sha256:native.footprints_sha256,unchanged_files:[beforeSource],overrides:[]});
 selection.selected_geography={version:1,kind:'complete-world-index-with-exact-encoded-overrides',...plain(sourceBank)};
 const projection=prepareReferenceMetadataProjection({selection,manifest,owners,reference:current,hierarchy:{before:beforeHierarchy,after:afterHierarchy},receipts:[receipt],source_updates:[{logical_path:'data/geography/part-0.json',before:beforeSource,after:afterSource}],read:reader.read});
 const projectionPin=await put('inputs/projection.json',projection);selection.reference_projection=plain(projectionPin);
 await put('data/ownership-selection.json',selection);
 const originalIndex=await put('data/geographic-releases/index.json',{version:1,original_catalog_sha256:'7'.repeat(64),releases:[{...native,version:1}]});
 const releases=await put('data/geographic-releases/releases-v2.json.gz',gzipSync(Buffer.from(JSON.stringify({version:1,original_catalog_sha256:'7'.repeat(64),releases:[{...native,version:1},{...current,version:2,metadata:{metadata_migration_sha256:{correction:receipt.sha256}}}]}))));
 await put('data/geographic-releases/current-manifest.json',{path:'releases-v2.json.gz',sha256:releases.sha256,predecessor_index_sha256:originalIndex.sha256});
 const preparationConfig={version:1,selector:pins.get('data/ownership-selection.json'),native_manifest:baseManifest,owner_roster:{...roster,encoding:'gzip',decoded_bytes:rosterRaw.length,decoded_sha256:sha(rosterRaw)},current_release:{commit,path:'data/geographic-releases/current-manifest.json'},hierarchy:projection.hierarchy,receipts:projection.receipts,source_updates:projection.source_updates};
 return {root,reader,put,pins,bodies,selection,projection,projectionPin,manifest,owners,original,currentFeatures,native,current,preparationConfig,metadataApplication:{projection,selection,manifest,read:reader.read}};
}

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

test('reference-metadata preparation derives one canonical application from stock receipts and the actual current release registry',async t=>{
 const f=await fixture(t),result=prepareReferenceMetadata(f.preparationConfig,f.reader);
 assert.deepEqual(Object.keys(result.products),['reference-metadata.json']);assert.deepEqual(JSON.parse(result.products['reference-metadata.json']),f.projection);
 assert.equal(result.input_inventory.length,12);assert.ok(result.input_inventory.every(pin=>pin.whole_body_consumed&&pin.roles.length>0&&/^[a-f0-9]{40}$/.test(pin.git_blob_oid)));
 for(const name of ['data/ownership-selection.json','data/geographic-releases/current-manifest.json','data/geographic-releases/index.json','data/geographic-releases/releases-v2.json.gz','inputs/receipt.json','data/geography/part-0.json','inputs/source-after.json','inputs/original-source-map.json'])assert.ok(result.input_inventory.some(pin=>pin.path===name),name);
 assert.deepEqual(prepareReferenceMetadata(f.preparationConfig,f.reader),result);
});

test('reference preparation admits exact large encoded/decoded owner bodies',async t=>{
 // Capacity fixtures with complete three-owner semantics; no geographic proof.
 for(const options of [{rosterBytes:34920857},{rosterBytes:64*1024*1024+1,rosterGzip:false}]){
  const f=await fixture(t,options),pin=f.preparationConfig.owner_roster,original=Buffer.from(f.reader.read(pin));
  const prepared=prepareReferenceMetadata(f.preparationConfig,f.reader);
  assert.deepEqual(JSON.parse(prepared.products['reference-metadata.json']),f.projection);
  assert(prepared.input_inventory.some(row=>row.path===pin.path&&row.bytes===original.length&&row.whole_body_consumed));

  for(const raw of [original.subarray(0,-1),Buffer.concat([original,Buffer.from(' ')])]){
   const reader={...f.reader,read:p=>p.sha256===pin.sha256?raw:f.reader.read(p)};
   assert.throws(()=>prepareReferenceMetadata(f.preparationConfig,reader),/Whole reference preparation input differs/);
  }
  const corrupt=Buffer.from(original);corrupt[0]^=1;
  const reader={...f.reader,read:p=>p.sha256===pin.sha256?corrupt:f.reader.read(p)};
  assert.throws(()=>prepareReferenceMetadata(f.preparationConfig,reader),/Whole reference preparation input differs/);
  if(options.rosterGzip!==false)for(const change of [
   {decoded_bytes:pin.decoded_bytes-1},{decoded_bytes:pin.decoded_bytes+1},{decoded_sha256:'0'.repeat(64)},
   {decoded_bytes:0},{decoded_bytes:Number.MAX_SAFE_INTEGER+1}
  ]){
   const altered={...pin,...change},config={...f.preparationConfig,owner_roster:altered};
   assert.throws(()=>prepareReferenceMetadata(config,f.reader));
  }
  assert.deepEqual(f.reader.read(pin),original);
 }
});

test('reference preparation rejects a later identical source pin before publishing a projection',async t=>{
 const f=await fixture(t),config=structuredClone(f.preparationConfig),before=config.source_updates[0].before;
 // This reader returns the exact same bytes. Only issued origin custody differs.
 before.commit='b'.repeat(40);
 assert.deepEqual(f.reader.read(before),f.reader.read(f.preparationConfig.source_updates[0].before));
 assert.throws(()=>prepareReferenceMetadata(config,f.reader),/does not start at the actual selected source/);
 for(const change of [{path:'inputs/same-bytes.json'},{encoding:'gzip',decoded_bytes:before.bytes,decoded_sha256:before.sha256}]){
  const altered=structuredClone(f.preparationConfig);Object.assign(altered.source_updates[0].before,change);
  assert.throws(()=>prepareReferenceMetadata(altered,f.reader),/does not start at the actual selected source/);
 }
 assert.deepEqual(JSON.parse(prepareReferenceMetadata(f.preparationConfig,f.reader).products['reference-metadata.json']),f.projection);
});

test('reference preparation authenticates the selected source bank and refuses missing or duplicate source membership',async t=>{
 for(const mutate of [bank=>bank.unchanged_files=[],bank=>bank.unchanged_files.push({...bank.unchanged_files[0]}),bank=>bank.native_manifest_sha256='0'.repeat(64)]){
  const f=await fixture(t),bank=f.reader.json(f.pins.get('inputs/original-source-map.json'));mutate(bank);
  const pin=await f.put('inputs/original-source-map.json',bank),selection={...f.selection,selected_geography:{...f.selection.selected_geography,...plain(pin)}};
  const config={...f.preparationConfig,selector:await f.put('data/ownership-selection.json',selection)};
  assert.throws(()=>prepareReferenceMetadata(config,f.reader),/actual selected source|Duplicate or foreign|source\/native\/release/);
 }
 const f=await fixture(t),pin=f.pins.get('inputs/original-source-map.json');
 f.bodies.set(pin.sha256,Buffer.alloc(pin.bytes,32));
 assert.throws(()=>prepareReferenceMetadata(f.preparationConfig,f.reader),/Whole reference preparation input differs/);
});

test('reference-metadata preparation rejects handwritten current identities, extra config, stale native/owner pins and incomplete source receipts',async t=>{
 const f=await fixture(t);
 for(const mutate of [c=>c.reference=f.current,c=>c.current_release={...c.current_release,reference:f.current},c=>c.native_manifest.sha256='0'.repeat(64),c=>c.owner_roster.sha256='0'.repeat(64),c=>c.receipts=[],c=>c.source_updates=[]]){const config=structuredClone(f.preparationConfig);mutate(config);assert.throws(()=>prepareReferenceMetadata(config,f.reader));}
 const pointer=f.reader.json(f.pins.get('data/geographic-releases/current-manifest.json'));pointer.sha256='0'.repeat(64);await f.put('data/geographic-releases/current-manifest.json',pointer);
 assert.throws(()=>prepareReferenceMetadata(f.preparationConfig,f.reader),/release whole identity differs/);
});

async function aliasPreparationFixture(t){
 const f=await fixture(t,{aliasSeed:true}),config=structuredClone(f.preparationConfig);
 const before=structuredClone(f.currentFeatures[0].properties),after=structuredClone(before);after.metadata.reference_polity=after.reference_owner;
 const features=structuredClone(f.currentFeatures);features[0].properties=after;
 const receipt={before_sha256:f.current.hierarchy_sha256,after_sha256:f.current.hierarchy_sha256,
  footprints_sha256_before:f.current.footprints_sha256,footprints_sha256_after:f.current.footprints_sha256,
  reference_only:true,historical_claims_transferred:false,summary:{geometry_changes:0},relationships:[],retired_units:[],group_changes:[],
  before_units:f.reader.json(config.hierarchy.after),source_evidence:[{url:'https://example.invalid/recorded-winner',source_sha256:config.source_updates[0].after.sha256}],
  changed_location_properties:[{location_id:'A',before_properties:before,after_properties:after}]};
 const refresh=async()=>{config.receipts[1]=await f.put('inputs/alias-receipt.json',receipt);config.source_updates[0].after=await f.put('inputs/alias-source.json',{type:'FeatureCollection',features});};
 await refresh();return {...f,config,receipt,features,refresh};
}

for(const compressed of [false,true]) test('same-M preparation binds a complete alias receipt without minting a release or losing the prior reparent: '+(compressed?'gzip':'plain'),async t=>{
 const f=await aliasPreparationFixture(t),release=Buffer.from(f.reader.read(f.pins.get('data/geographic-releases/releases-v2.json.gz')));
 if(compressed){
  const raw=f.reader.read(f.config.receipts[1]),pin=await f.put('inputs/alias-receipt.json.gz',gzipSync(raw));
  f.config.receipts[1]={...pin,encoding:'gzip',decoded_bytes:raw.length,decoded_sha256:sha(raw)};
  for(const change of [{encoding:'unknown'},{decoded_bytes:raw.length-1},{decoded_sha256:'0'.repeat(64)},{decoded_bytes:undefined}]){
   const config=structuredClone(f.config);Object.assign(config.receipts[1],change);assert.throws(()=>prepareReferenceMetadata(config,f.reader));
  }
 }
 const prepared=prepareReferenceMetadata(f.config,f.reader),projection=JSON.parse(prepared.products['reference-metadata.json']);
 assert.deepEqual(projection.reference,f.current);assert.deepEqual(projection.native_reference,f.native);
 assert.deepEqual(projection.receipts,f.config.receipts);assert.equal(projection.location_changes[0].after_properties.parent_id,'Q');
 assert.equal(projection.location_changes[0].after_properties.metadata.reference_polity,'Recorded winner');
 assert.deepEqual(projection.location_changes[0].after_properties.metadata.reference_corrections,f.currentFeatures[0].properties.metadata.reference_corrections);
 assert.deepEqual(f.reader.read(f.pins.get('data/geographic-releases/releases-v2.json.gz')),release);
 assert.ok(prepared.input_inventory.some(p=>p.sha256===f.config.receipts[1].sha256&&p.whole_body_consumed));
 // A real reparent absent from M is never exempted by the later alias receipt.
 const value=JSON.parse((await import('node:zlib')).gunzipSync(release));value.releases.at(-1).metadata.metadata_migration_sha256={};
 const changed=await f.put('data/geographic-releases/releases-v2.json.gz',gzipSync(Buffer.from(JSON.stringify(value))));
 const pointer=f.reader.json(f.pins.get('data/geographic-releases/current-manifest.json'));pointer.sha256=changed.sha256;await f.put('data/geographic-releases/current-manifest.json',pointer);
 assert.throws(()=>prepareReferenceMetadata(f.config,f.reader),/does not bind every applied metadata receipt/);
});

test('same-M alias preparation refuses coherent hidden edits, missing scope and stale receipt chains',async t=>{
 for(const mutate of [
  f=>{f.receipt.changed_location_properties[0].after_properties.metadata.reference_owner_evidence.winner.owner_id='owner:Q2';f.features[0].properties.metadata.reference_owner_evidence.winner.owner_id='owner:Q2';},
  f=>{f.receipt.changed_location_properties[0].after_properties.metadata.reference_polity='Wrong';f.features[0].properties.metadata.reference_polity='Wrong';},
  f=>{f.receipt.changed_location_properties[0].after_properties.metadata.semantic_review.status='approved';f.features[0].properties.metadata.semantic_review.status='approved';},
  f=>{f.features[0].geometry.coordinates[0][1][0]=.25;},
  f=>{f.features[1].properties.metadata.reference_polity='Recorded winner';},
  f=>{f.receipt.changed_location_properties=[];},
  f=>{f.receipt.before_sha256=f.native.hierarchy_sha256;},
  f=>{f.receipt.changed_location_properties[0].before_properties.parent_id='P';},
 ]){const f=await aliasPreparationFixture(t);mutate(f);await f.refresh();assert.throws(()=>prepareReferenceMetadata(f.config,f.reader));}
 const f=await aliasPreparationFixture(t);f.config.receipts.reverse();assert.throws(()=>prepareReferenceMetadata(f.config,f.reader),/chain|Stale|original|hierarchy/);
});

test('reference preparation accepts the final-map selector while retaining original N source custody',async t=>{
 const f=await fixture(t),native=structuredClone(f.selection);delete native.reference_projection;
 const selection={version:2,kind:'selected-final-native-bank-v2',native_selection:native,
  prepared_bank:{path:'data/canonical-grid/current-startup/index.json',bytes:1,sha256:'9'.repeat(64)},
  reference:f.current,reference_projection:f.selection.reference_projection};
 const config={...f.preparationConfig,selector:await f.put('data/ownership-selection.json',selection)};
 const prepared=prepareReferenceMetadata(config,f.reader);
 assert.deepEqual(JSON.parse(prepared.products['reference-metadata.json']),f.projection);
 assert(!prepared.input_inventory.some(pin=>pin.path===selection.prepared_bank.path),
  'Reference preparation authenticates original source metadata, not current ownership replay');
});

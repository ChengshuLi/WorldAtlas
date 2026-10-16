import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {gridProjection,appendRelease,composeEvidence,applyInstall,safe,patchJSONText,validateMetadataStages} from '../scripts/install-macro-reference.mjs';
import {preparedEvidenceJSON} from '../src/prepared-evidence.js';
import {assertReferenceOnlyFeatureChange,assertReferenceOnlyLocationChange,projectReferenceFeatures,projectReferenceOwners,assertAppliedReferenceProperties} from '../src/reference-metadata.js';
import {prepareReferenceMetadataProjection,validateReferenceMetadataProjection} from '../scripts/selected-reference-metadata.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex');
const fixture=()=>{const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]},feature={id:'London',geometry,properties:{id:'London',name:'London',parent_id:'p'}};const proof={footprints_sha256:'a'.repeat(64),hierarchy_sha256:'b'.repeat(64),location_index_sha256:'c'.repeat(64)};const before={locations:new Map([['London',feature]]),units:[{id:'p',level:'province'}],groups:new Map(),members:new Map(),proof};const after={...before,proof:{...proof,hierarchy_sha256:'d'.repeat(64)},units:[{id:'q',level:'province'}],locations:new Map([['London',{...feature,properties:{...feature.properties,parent_id:'q'}}]])};return {before,after,geometry};};

test('JSON projection retains original nested formatting and appends bounded one-line entries',()=>{
 const text='{\n  "proof": {\n    "sha256": "old",\n    "number": 1.00\n  },\n  "batches": [\n    {\n      "id": "retained",\n      "value": 2e0\n    }\n  ]\n}\n',value=JSON.parse(text);value.proof.sha256='new';value.batches.push({id:'new',value:3});value.projection={method:'metadata'};
 const result=patchJSONText(text,value);assert.deepEqual(JSON.parse(result),value);assert.ok(result.includes('"number": 1.00'));assert.ok(result.includes('    {\n      "id": "retained",\n      "value": 2e0\n    }'));assert.ok(result.includes('{"id":"new","value":3}'));assert.ok(result.includes('"projection": {"method":"metadata"}'));assert.equal(patchJSONText(text,JSON.parse(text)),text);
});

test('JSON projection handles changed array rows, escaped strings, empty containers and removals',()=>{
 const text=' {"rows": [{"id":"a\\\"b","value":1},{"id":"c","value":2}],"empty":{},"list":[]}\n',next=JSON.parse(text);next.rows[1].value=3;next.empty.new=true;next.list.push('first');
 const result=patchJSONText(text,next);assert.deepEqual(JSON.parse(result),next);assert.ok(result.includes('{"id":"a\\\"b","value":1}'));next.rows.shift();assert.deepEqual(JSON.parse(patchJSONText(text,next)),next);
});

test('province projection changes only province metadata and retains canonical cell/index bounds',()=>{
 const {before,after}=fixture(),manifest={...before.proof,parts:[{kind:'runs',sha256:'immutable'}],provinces:['p']},bounds=[{id:'London',index:1,bounds:[1,2,3,4],province_id:'p',province_index:1}];
 const result=gridProjection(manifest,bounds,before,after);
 assert.deepEqual(result.bounds,[{...bounds[0],province_id:'q'}]);assert.deepEqual(result.manifest.parts,manifest.parts);assert.deepEqual(result.provinces,['q']);assert.equal(gunzipSync(result.membership).readUInt32LE(4),1);assert.equal(result.manifest.footprints_sha256,before.proof.footprints_sha256);
 assert.throws(()=>gridProjection(manifest,[{...bounds[0],province_id:'wrong'}],before,after),/Invalid original grid/);
 before.locations.set('Paris',{...before.locations.get('London'),id:'Paris'});after.locations.set('Paris',{...after.locations.get('London'),id:'Paris'});
 assert.throws(()=>gridProjection(manifest,[bounds[0],{...bounds[0],index:2}],before,after),/Invalid original grid/);
});

test('append-only release retains original generations and drops regenerated baseline',()=>{
 const old={releases:[{id:'baseline',version:1},{id:'prior',version:2}],batches:[{path:'release-1.json',sha256:'old1'},{path:'release-2.json',sha256:'old2'},{path:'sources.json',sha256:'oldsource'}],new_entities:2,total_memberships:20,changes:3};
 const release={id:'new',version:3,source_id:'s3'},payloads=new Map([['sources.json',Buffer.from(JSON.stringify({sources:[{id:'baseline-source'},{id:'s3'}],ingestion_id:'s3'}))],['release-1.json',Buffer.from('regenerated baseline')],['release-3.json',Buffer.from(JSON.stringify({release}))],['entities-province-0.json',Buffer.from('{"entities":[]}')]]);
 const next={releases:[{id:'baseline',version:1},release],batches:[...payloads].map(([p,b])=>({path:p,sha256:sha(b)})),new_entities:1,total_memberships:30,changes:5};const original=structuredClone(old),result=appendRelease(old,next,p=>payloads.get(p));
 assert.deepEqual(old,original);assert.deepEqual(result.index.releases,[...old.releases,release]);assert.deepEqual(result.index.batches.slice(0,3),old.batches);assert.equal(result.files.has('release-1.json'),false);assert.equal(result.files.has('entities-province-v3-0.json'),true);assert.deepEqual(JSON.parse(result.files.get('sources-3.json')).sources,[{id:'s3'}]);assert.deepEqual(result.index.sources_batches,['sources.json','sources-3.json']);
});

test('evidence composes unchanged territory while preserving original supported facts',()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-evidence-'));try{const {before,after,geometry}=fixture();fs.writeFileSync(path.join(directory,'source.json'),'original bytes');const pin=sha(preparedEvidenceJSON([['London',geometry]]));const receipt={original_geography:{historical:'original'},revalidated_geography:before.proof,source_product_files:[{path:'source.json',sha256:sha('original bytes')}],entities:[{entity_id:'London',kind:'location',member_locations:1,original_footprint_sha256:pin,revalidated_footprint_sha256:pin,result:'identical-footprint'}],records:42};
 const result=composeEvidence(receipt,before,after,directory);assert.deepEqual(result.original_geography,receipt.original_geography);assert.deepEqual(result.revalidated_geography,after.proof);assert.equal(result.records,42);assert.deepEqual(result.entities,receipt.entities);assert.equal(result.historical_membership_assigned,false);
 after.locations.get('London').geometry={type:'Polygon',coordinates:[]};assert.throws(()=>composeEvidence(receipt,before,after,directory),/territory changed/);
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
});

test('apply rejects unapproved hash and rolls back partial metadata transaction',()=>{
 const base=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-install-'));try{const data=path.join(base,'data'),stage=path.join(base,'stage');fs.mkdirSync(data);fs.mkdirSync(path.join(stage,'after'),{recursive:true});for(const name of ['one.json','two.json']){fs.writeFileSync(path.join(data,name),'original '+name);fs.writeFileSync(path.join(stage,'after',name),'replacement '+name);}fs.writeFileSync(path.join(data,'history.bin'),'immutable history');const report={preserved:{'history.bin':sha('immutable history')},immutable_grid_parts:[],originals:Object.fromEntries(['one.json','two.json'].map(p=>[p,sha('original '+p)])),writes:Object.fromEntries(['one.json','two.json'].map(p=>[p,sha('replacement '+p)]))};const prepared={data,stage,report,validation_sha256:'reviewed'};
 assert.throws(()=>applyInstall(prepared,{expectedValidation:'wrong'}),/exact reviewed/);assert.throws(()=>applyInstall(prepared,{expectedValidation:'reviewed',failAfter:1}),/Injected/);for(const p of ['one.json','two.json'])assert.equal(fs.readFileSync(path.join(data,p),'utf8'),'original '+p);assert.equal(fs.readFileSync(path.join(data,'history.bin'),'utf8'),'immutable history');assert.equal(fs.existsSync(path.join(data,'.macro-reference-install.lock')),false);
 }finally{fs.rmSync(base,{recursive:true,force:true});}
});

test('immutable bytes changing after preparation block application',()=>{
 const base=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-guard-'));try{const data=path.join(base,'data'),stage=path.join(base,'stage');fs.mkdirSync(data);fs.mkdirSync(stage);fs.writeFileSync(path.join(data,'history'),'changed');assert.throws(()=>applyInstall({data,stage,validation_sha256:'ok',report:{immutable_grid_parts:[],preserved:{history:sha('original')},originals:{},writes:{}}},{expectedValidation:'ok'}),/Historical bytes changed/);assert.throws(()=>safe(data,'../secret'),/Unsafe/);
 }finally{fs.rmSync(base,{recursive:true,force:true});}
});

test('successful metadata install records a committed journal and retains rollback originals',()=>{
 const base=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-commit-'));try{
  const data=path.join(base,'data'),stage=path.join(base,'stage');fs.mkdirSync(data);fs.mkdirSync(path.join(stage,'after'),{recursive:true});fs.writeFileSync(path.join(data,'metadata.json'),'original');fs.writeFileSync(path.join(stage,'after','metadata.json'),'replacement');
  const report={immutable_grid_parts:[],preserved:{},originals:{'metadata.json':sha('original')},writes:{'metadata.json':sha('replacement')}};
  const result=applyInstall({data,stage,report,validation_sha256:'checked'},{expectedValidation:'checked'}),journal=JSON.parse(fs.readFileSync(path.join(result.rollback_archive,'journal.json')));
  assert.equal(journal.state,'committed');assert.deepEqual(journal.installed,['metadata.json']);assert.equal(fs.readFileSync(path.join(data,'metadata.json'),'utf8'),'replacement');assert.equal(fs.readFileSync(path.join(result.rollback_archive,'metadata.json'),'utf8'),'original');assert.equal(fs.existsSync(path.join(data,'.macro-reference-install.lock')),false);
 }finally{fs.rmSync(base,{recursive:true,force:true});}
});


test('compressed release append preserves prior descriptors and checks compressed/payload bytes',()=>{
 const release={id:'six',version:6,source_id:'source:six'},old={releases:[{id:'five',version:5}],batches:[{path:'old.json.gz',sha256:'immutable',payload_sha256:'immutable-raw',encoding:'gzip'}],new_entities:44,total_memberships:10,changes:20,sources_batches:['old.json.gz']};
 const payloads=new Map([['sources.json',Buffer.from(JSON.stringify({sources:[{id:'baseline'},{id:'source:six'}]}))],['release-6.json',Buffer.from(JSON.stringify({release}))]]);
 const next={releases:[release],batches:[...payloads].map(([name,raw])=>({path:name,sha256:sha(raw),route:'/api/geography/stage'})),new_entities:0,total_memberships:30,changes:3};
 const before=structuredClone(old),result=appendRelease(old,next,name=>payloads.get(name),{compressed:true});
 assert.deepEqual(old,before);assert.deepEqual(result.index.batches[0],old.batches[0]);assert.equal(result.index.new_entities,44);
 for(const batch of result.index.batches.slice(1)){const packed=result.files.get(batch.path);assert.equal(sha(packed),batch.sha256);assert.equal(sha(gunzipSync(packed)),batch.payload_sha256);assert.equal(packed[9],255);assert.equal(batch.encoding,'gzip');}
 assert.deepEqual(result.index.sources_batches,['old.json.gz','sources-6.json.gz']);
 assert.throws(()=>appendRelease({...old,batches:[...old.batches,{path:'release-6.json.gz'}]},next,name=>payloads.get(name),{compressed:true}),/overwrite/);
 payloads.set('release-6.json',Buffer.from('changed'));assert.throws(()=>appendRelease(old,next,name=>payloads.get(name),{compressed:true}),/hash mismatch/);
});

test('reference-only metadata mode validates exact archived group and source-backed parent merge',()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-reference-stage-'));
 try{
  const units=[{id:'c',name:'C',level:'continent',parent_id:null},{id:'s',name:'S',level:'subcontinent',parent_id:'c'},{id:'r',name:'R',level:'region',parent_id:'s'},{id:'a',name:'A',level:'area',parent_id:'r'},{id:'old',name:'P',level:'province',parent_id:'a'},{id:'kept',name:'P',level:'province',parent_id:'a'}];
  const features=['one','two'].map((id,i)=>({id,properties:{id,name:id,parent_id:i?'kept':'old'},geometry:{type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]}}));
  const before={units,groups:new Map(units.map(row=>[row.id,row])),features,locations:new Map(features.map(row=>[row.id,row])),proof:{hierarchy_sha256:'before',footprints_sha256:'footprints'}};
  const afterFeatures=structuredClone(features);afterFeatures[0].properties.parent_id='kept';
  const afterUnits=units.filter(row=>row.id!=='old');const after={units:afterUnits,groups:new Map(afterUnits.map(row=>[row.id,row])),features:afterFeatures,locations:new Map(afterFeatures.map(row=>[row.id,row])),proof:{hierarchy_sha256:'after',footprints_sha256:'footprints'}};
  const receipt={before_sha256:'before',after_sha256:'after',footprints_sha256_before:'footprints',footprints_sha256_after:'footprints',reference_only:true,historical_claims_transferred:false,summary:{geometry_changes:0},before_units:units,retired_units:[units[4]],group_changes:[{id:'old',before:units[4],after:null}],changed_location_properties:[{location_id:'one',before_properties:features[0].properties,after_properties:afterFeatures[0].properties}],relationships:[{old_entity_id:'old',new_entity_id:'kept',change_type:'merge',reference_only:true,history_transfer:'none'}],source_evidence:[{url:'https://example.org/retained',source_sha256:'a'.repeat(64)}]};
  const file=path.join(directory,'receipt.json'),save=value=>fs.writeFileSync(file,JSON.stringify(value));save(receipt);
  validateMetadataStages(before,after,[file],{mode:'reference-correction'});
  for(const mutate of [x=>x.before_sha256='stale',x=>x.historical_claims_transferred=true,x=>x.relationships=[],x=>x.before_units[4].name='invented',x=>x.source_evidence=[]]){const bad=structuredClone(receipt);mutate(bad);save(bad);assert.throws(()=>validateMetadataStages(before,after,[file],{mode:'reference-correction'}),/Stale|retired parent|before identities|source URLs/);}
  save(receipt);afterFeatures[0].properties.name='changed';assert.throws(()=>validateMetadataStages(before,after,[file],{mode:'reference-correction'}),/Non-parent/);
  assert.throws(()=>validateMetadataStages(before,after,[],{mode:'reference-correction'}),/Exactly one/);
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
});

function parentProjectionFixture(){
 const properties={id:'member',name:'Member',parent_id:'old',metadata:{source_id:'original:source',framework_match:{id:'original:fallback',overlap:.8},reference_corrections:[{original:'retained history'}]}};
 const after=structuredClone(properties);after.parent_id='new';
 after.metadata.reference_corrections.push({id:'member',action:'reparent',current_name:'Member',current_parent_id:'old',new_parent_id:'new',rationale:'Explicit dated source correspondence; no boundary or historical transfer.',evidence:[{url:'https://example.org/retained-source',title:'Retained source',inspected_fact:'The exact original member belongs to this named parent.'}]});
 const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]};
 const features=[{type:'Feature',id:'member',properties,geometry},{type:'Feature',id:'retained',properties:{id:'retained',name:'Retained',parent_id:'old'},geometry}];
 const changes=[{location_id:'member',before_properties:properties,after_properties:after}];
 const owners=[{id:'member',index:1,province_id:'old',province_index:2,bounds:[1,2,3,4],camera:{original:true}},{id:'retained',index:2,province_id:'old',province_index:2,bounds:[5,6,7,8]}];
 return{properties,after,features,changes,owners,provinces:['new','old']};
}

test('current metadata projection retains original fallback/history, geometry, owner indices and camera bytes',()=>{
 const f=parentProjectionFixture(),original=JSON.stringify(f),features=projectReferenceFeatures(f.features,f.changes),owners=projectReferenceOwners(f.owners,f.changes,f.provinces);
 assertReferenceOnlyFeatureChange(f.features[0],features[0]);
 assert.equal(features[0].properties.parent_id,'new');assert.equal(features[0].geometry,f.features[0].geometry);
 assert.equal(features[1],f.features[1]);assert.deepEqual(features[0].properties.metadata.framework_match,{id:'original:fallback',overlap:.8});
 assert.deepEqual(features[0].properties.metadata.reference_corrections.slice(0,1),f.properties.metadata.reference_corrections);
 assert.deepEqual(owners,[{...f.owners[0],province_id:'new',province_index:1},f.owners[1]]);
 assert.equal(owners[0].camera,f.owners[0].camera);assert.equal(owners[0].bounds,f.owners[0].bounds);
 assert.equal(JSON.stringify(f),original,'Original qualification/source/context objects must remain unchanged');
 const before={locations:new Map(f.features.map(row=>[row.id,row])),units:f.provinces.map(id=>({id,level:'province'})),proof:{footprints_sha256:'a'.repeat(64),hierarchy_sha256:'b'.repeat(64)}};
 const after={...before,locations:new Map(features.map(row=>[row.id,row])),proof:{...before.proof,hierarchy_sha256:'c'.repeat(64)}};
 const manifest={...before.proof,parts:[{kind:'rows',sha256:'unchanged rows'},{kind:'runs',sha256:'unchanged runs'}]};
 const installed=gridProjection(manifest,f.owners,before,after);
 assert.deepEqual(installed.bounds,owners,'Installer and current application use one projection');
 assert.deepEqual(installed.manifest.parts,manifest.parts);assert.equal(installed.manifest.footprints_sha256,manifest.footprints_sha256);
});

test('reference metadata cannot hide source edits, old-history edits or an unrelated correction append',()=>{
 for(const mutate of [
  row=>row.metadata.source_id='replaced source',
  row=>row.metadata.framework_match.overlap=.9,
  row=>row.metadata.reference_corrections[0].original='rewritten history',
  row=>row.metadata.reference_corrections.pop(),
  row=>row.metadata.reference_corrections[1].current_parent_id='foreign',
  row=>row.metadata.reference_corrections[1].new_parent_id='foreign',
  row=>row.metadata.reference_corrections[1].id='foreign member',
  row=>row.metadata.reference_corrections[1].action='replace',
  row=>row.metadata.reference_corrections[1].evidence=[],
  row=>row.metadata.reference_corrections[1].evidence[0].inspected_fact='',
  row=>row.metadata.reference_corrections[1].approved=true,
  row=>row.name='renamed member',
 ]){
  const f=parentProjectionFixture();mutate(f.after);
  // A normal parent-only receipt need not append writer history. Removing only
  // the newly appended correction remains legal; changing an existing one does not.
  if(f.after.metadata.reference_corrections.length===1){assertReferenceOnlyLocationChange(f.properties,f.after);continue;}
  assert.throws(()=>assertReferenceOnlyLocationChange(f.properties,f.after),/Non-parent|history|exact sourced|different parent/);
 }
 const f=parentProjectionFixture(),changed={...f.features[0],properties:f.after,geometry:{type:'Polygon',coordinates:[]}};
 assert.throws(()=>assertReferenceOnlyFeatureChange(f.features[0],changed),/geometry/);
 assert.throws(()=>assertReferenceOnlyFeatureChange(f.features[0],{...f.features[0],type:'Foreign',properties:f.after}),/geometry/);
});

test('complete reference projections reject missing, duplicate, foreign, stale and wrong-parent joins',()=>{
 const f=parentProjectionFixture();
 assert.throws(()=>projectReferenceFeatures([f.features[0],f.features[0]],f.changes),/Duplicate/);
 assert.throws(()=>projectReferenceFeatures(f.features,[...f.changes,...f.changes]),/duplicate/);
 assert.throws(()=>projectReferenceFeatures([f.features[1]],f.changes),/foreign/);
 const stale=structuredClone(f.changes);stale[0].before_properties.metadata.source_id='wrong';
 assert.throws(()=>projectReferenceFeatures(f.features,stale),/stale/);
 assert.throws(()=>projectReferenceOwners([f.owners[0],f.owners[0]],f.changes,f.provinces),/Duplicate/);
 assert.throws(()=>projectReferenceOwners(f.owners,[...f.changes,...f.changes],f.provinces),/duplicate/);
 const wrong=structuredClone(f.owners);wrong[0].province_id='foreign';
 assert.throws(()=>projectReferenceOwners(wrong,f.changes,f.provinces),/stale/);
 assert.throws(()=>projectReferenceOwners(f.owners,f.changes,['old']),/absent/);
 assert.throws(()=>projectReferenceOwners(f.owners,f.changes,[...f.provinces,'empty']),/empty/);
 assert.throws(()=>projectReferenceOwners(f.owners,f.changes,['new','new']),/inventory/);
 const foreign=structuredClone(f.changes);foreign[0].location_id='missing';
 assert.throws(()=>projectReferenceOwners(f.owners,foreign,f.provinces),/foreign/);
});

function wholeMetadataProjectionFixture(){
 const f=parentProjectionFixture(),features=[...f.features,{type:'Feature',id:'existing',properties:{id:'existing',name:'Existing',parent_id:'new'},geometry:f.features[0].geometry}];
 const owners=[...f.owners,{id:'existing',index:3,province_id:'new',province_index:1,bounds:[9,10,11,12]}];
 const units=[{id:'c',name:'C',level:'continent',parent_id:null},{id:'s',name:'S',level:'subcontinent',parent_id:'c'},
  {id:'r',name:'R',level:'region',parent_id:'s'},{id:'a',name:'A',level:'area',parent_id:'r'},
  {id:'old',name:'Old',level:'province',parent_id:'a',metadata:{child_count:2}},{id:'new',name:'New',level:'province',parent_id:'a',metadata:{child_count:1}}];
 const afterUnits=structuredClone(units);afterUnits[4].metadata.child_count=1;afterUnits[5].metadata.child_count=2;
 const bodies=new Map();let serial=0;
 const put=(name,value)=>{const raw=Buffer.from(JSON.stringify(value)),pin={commit:(++serial).toString(16).padStart(40,'0'),path:name,mode:'100644',git_blob_oid:createHash('sha1').update('blob '+raw.length+'\0').update(raw).digest('hex'),bytes:raw.length,sha256:sha(raw)};bodies.set(pin.commit+':'+pin.path,raw);return pin;};
 const hierarchy={before:put('data/hierarchy.json',units),after:put('data/hierarchy.json',afterUnits)};
 const source={before:put('data/geography/part-0.json',{type:'FeatureCollection',features}),after:put('data/geography/part-0.json',{type:'FeatureCollection',features:projectReferenceFeatures(features,f.changes)})};
 const native={id:'geography:original',footprints_sha256:'a'.repeat(64),hierarchy_sha256:hierarchy.before.sha256};
 const reference={...native,id:'geography:current-metadata',hierarchy_sha256:hierarchy.after.sha256};
 const receipt={before_sha256:native.hierarchy_sha256,after_sha256:reference.hierarchy_sha256,
  footprints_sha256_before:native.footprints_sha256,footprints_sha256_after:native.footprints_sha256,
  reference_only:true,historical_claims_transferred:false,summary:{geometry_changes:0},relationships:[],before_units:units,retired_units:[],
  group_changes:[4,5].map(index=>({id:units[index].id,before:units[index],after:afterUnits[index]})),
  changed_location_properties:f.changes,source_evidence:[{url:'https://example.org/retained-source',source_sha256:'c'.repeat(64)}]};
 const receiptPin=put('data/reference-correction.json',receipt);
 const manifest={geographic_release:native.id,footprints_sha256:native.footprints_sha256,hierarchy_sha256:native.hierarchy_sha256,
  original_assets:{bounds:{sha256:'b'.repeat(64)}}};
 const selection={version:1,method:'native-linear-evenodd-first-owner-v1',manifest_path:'data/native.json',sha256:'d'.repeat(64),release_id:native.id,
  selected_geography:{version:1,kind:'complete-world-index-with-exact-encoded-overrides',path:'data/source-bank.json',bytes:100,sha256:'e'.repeat(64)},
  artifact_consumption:{certificate:{original:'unchanged'},review:{original:'unchanged'}}};
 const config={selection,manifest,owners,reference,hierarchy,receipts:[receiptPin],source_updates:[{logical_path:'data/geography/part-0.json',...source}],
  read:pin=>bodies.get(pin.commit+':'+pin.path)};
 return{...f,features,owners,units,afterUnits,receipt,source,put,bodies,config};
}

test('whole metadata application authenticates actual source/hierarchy/receipts without replacing native qualification',()=>{
 const f=wholeMetadataProjectionFixture(),original=JSON.stringify({selection:f.config.selection,manifest:f.config.manifest,owners:f.owners,features:f.features});
 const projection=prepareReferenceMetadataProjection(f.config);
 const applied=validateReferenceMetadataProjection({...f.config,projection,originalSources:new Map([['data/geography/part-0.json',f.source.before]])});
 assert.equal(applied.reference.id,'geography:current-metadata');assert.equal(applied.nativeReference.id,'geography:original');
 assert.equal(applied.owners[0].province_id,'new');assert.equal(applied.owners[0].index,1);
 assert.deepEqual(applied.units,f.afterUnits);assert.equal(applied.sourceUpdates.size,1);
 assert.deepEqual(projection.native_selection,f.config.selection);
 const withApplication={...f.config.selection,reference_projection:{path:'data/projection.json',bytes:1,sha256:'f'.repeat(64)}};
 validateReferenceMetadataProjection({...f.config,selection:withApplication,projection});
 assert.equal(JSON.stringify({selection:f.config.selection,manifest:f.config.manifest,owners:f.owners,features:f.features}),original);
});

test('whole metadata application rejects coherently repinned geometry, source metadata, incomplete scope and history transfer',()=>{
 for(const mutate of [
  f=>{const next={type:'FeatureCollection',features:projectReferenceFeatures(f.features,f.changes)};next.features[0].geometry={type:'Polygon',coordinates:[]};f.config.source_updates[0].after=f.put('data/geography/part-0.json',next);},
  f=>{const after=structuredClone(f.receipt);after.changed_location_properties[0].after_properties.metadata.source_id='changed original source';f.config.receipts=[f.put('data/reference-correction.json',after)];},
  f=>{const after=structuredClone(f.receipt);after.historical_claims_transferred=true;f.config.receipts=[f.put('data/reference-correction.json',after)];},
  f=>{const after=structuredClone(f.receipt);after.summary.geometry_changes=1;f.config.receipts=[f.put('data/reference-correction.json',after)];},
  f=>{const after=structuredClone(f.receipt);after.before_sha256='0'.repeat(64);f.config.receipts=[f.put('data/reference-correction.json',after)];},
  f=>f.config.source_updates=[],
  f=>f.config.source_updates.push(f.config.source_updates[0]),
  f=>{const after=structuredClone(f.receipt);after.changed_location_properties=[];f.config.receipts=[f.put('data/reference-correction.json',after)];},
  f=>f.config.owners[0].index=99,
  f=>f.config.selection.sha256='0'.repeat(64),
 ]){
  const f=wholeMetadataProjectionFixture(),projection=prepareReferenceMetadataProjection(f.config);mutate(f);
  projection.receipts=f.config.receipts;projection.source_updates=f.config.source_updates;
  assert.throws(()=>validateReferenceMetadataProjection({...f.config,projection}),/geometry|Non-parent|metadata|Reference|reference|owner/);
 }
 const f=wholeMetadataProjectionFixture(),projection=prepareReferenceMetadataProjection(f.config);
 assert.throws(()=>validateReferenceMetadataProjection({...f.config,projection,originalSources:new Map([['data/geography/part-0.json',f.source.after]])}),/actual selected source/);
 const missing=structuredClone(projection);missing.location_changes=[];
 assert.throws(()=>validateReferenceMetadataProjection({...f.config,projection:missing}),/complete original/);
 const changedNative=structuredClone(f.config.selection);changedNative.artifact_consumption.certificate.original='rebound';
 assert.throws(()=>validateReferenceMetadataProjection({...f.config,selection:changedNative,projection}),/original native selection/);
});


test('current application retains every changed source property and only existing database defaults',()=>{
 const f=parentProjectionFixture(),actual={...structuredClone(f.after),active:1,reference_owner:null};
 assert.doesNotThrow(()=>assertAppliedReferenceProperties(actual,f.after));
 for(const mutate of [x=>delete x.metadata.reference_corrections,x=>x.metadata.framework_match.id='changed',x=>x.name='stale',x=>x.active=0,x=>x.unexpected='foreign']){
  const bad=structuredClone(actual);mutate(bad);assert.throws(()=>assertAppliedReferenceProperties(bad,f.after),/complete applied source/);
 }
});


test('raw nonfinite JSON numbers cannot masquerade as retained null source metadata',()=>{
 const before={id:'member',name:'Member',parent_id:'old',metadata:{source_id:null}};
 const after=JSON.parse('{"id":"member","name":"Member","parent_id":"old","metadata":{"source_id":1e999}}');
 assert.equal(after.metadata.source_id,Infinity);
 assert.throws(()=>assertReferenceOnlyLocationChange(before,after),/Nonfinite/);
 assert.throws(()=>assertAppliedReferenceProperties(after,before),/Nonfinite/);
 assert.throws(()=>assertAppliedReferenceProperties({...before,missing:undefined},before),/missing/);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {gridProjection,appendRelease,composeEvidence,applyInstall,safe,patchJSONText,validateMetadataStages} from '../scripts/install-macro-reference.mjs';
import {preparedEvidenceJSON} from '../src/prepared-evidence.js';
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

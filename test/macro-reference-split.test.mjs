import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {validateMetadataRelationships,prepareGeographicRelease,metadataRelationshipEvidence} from '../scripts/prepare-geographic-release.mjs';
import {footprintHash} from '../scripts/check-prepared.mjs';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const unit=(id,level,parent_id)=>({id,name:id,level,parent_id,metadata:{original:id}});
const identity=row=>({id:row.id,name:row.name,kind:row.level??row.kind,parent_id:row.parent_id});
test('large source collections retain a bounded reference to the exact archived receipt',()=>{
 const source_evidence=Array.from({length:100},(_,i)=>({url:`https://example.org/source/${i}`,source_sha256:'a'.repeat(64)}));
 const pair={receipt_sha256:'b'.repeat(64),relationship:{change_type:'split'},source_evidence};
 const proof=metadataRelationshipEvidence(pair);
 assert.equal(proof.source_evidence_ref.records,100);
 assert.equal(proof.source_evidence_ref.receipt_sha256,pair.receipt_sha256);
 assert.equal(proof.source_evidence_ref.json_pointer,'/source_evidence');
 assert.match(proof.source_evidence_ref.content_sha256,/^[a-f0-9]{64}$/);
 assert.ok(Buffer.byteLength(JSON.stringify(proof))<1024);
 const other=structuredClone(pair);other.source_evidence[0].url+='changed';
 assert.notEqual(metadataRelationshipEvidence(other).source_evidence_ref.content_sha256,proof.source_evidence_ref.content_sha256);
 assert.deepEqual(metadataRelationshipEvidence({...pair,source_evidence:source_evidence.slice(0,1)}).source_evidence,source_evidence.slice(0,1));
});
function fixture(){
 const units=[unit('c','continent',null),unit('s','subcontinent','c'),unit('old','region','s'),unit('neighbor','region','s'),unit('a1','area','old'),unit('a2','area','old'),unit('a3','area','neighbor'),unit('p1','province','a1'),unit('p2','province','a2'),unit('p3','province','a3')];
 const locations=[1,2,3].map(i=>({id:`l${i}`,name:`l${i}`,parent_id:`p${i}`,kind:'location'}));
 const replacements=[unit('west','region','s'),unit('east','region','s')];
 const receipt={reference_only:true,historical_claims_transferred:false,summary:{geometry_changes:0},before_units:structuredClone(units),retired_units:[structuredClone(units[2])],group_changes:[{id:'old',before:structuredClone(units[2]),after:null},...replacements.map(row=>({id:row.id,before:null,after:row})),...units.filter(row=>['a1','a2'].includes(row.id)).map(row=>({id:row.id,before:structuredClone(row),after:{...row,parent_id:row.id==='a1'?'west':'east'}}))],changed_location_properties:[],relationships:replacements.map(row=>({old_entity_id:'old',new_entity_id:row.id,change_type:'split',reference_only:true,history_transfer:'none'})),source_evidence:[{url:'https://example.org/test-only-split',source_sha256:'a'.repeat(64)}]};
 return {units,locations,beforeGroups:new Map(units.map(row=>[row.id,identity(row)])),beforeLocations:new Map(locations.map(row=>[row.id,row])),beforeUnitRecords:new Map(units.map(row=>[row.id,row])),registry:new Map([...units.map(identity),...locations].map(row=>[row.id,row])),receipt,receiptSha256:'b'.repeat(64)};
}
test('same-tier reference split preserves exact archived originals and disjoint descendant members',()=>{
 const f=fixture(),before=JSON.stringify(f),pairs=validateMetadataRelationships(f);
 assert.equal(pairs.length,2);assert.deepEqual(pairs.map(pair=>[pair.old_entity_id,pair.new_entity_id,pair.change_type]),[['old','west','split'],['old','east','split']]);assert.equal(JSON.stringify(f),before);
 assert.ok(pairs.every(pair=>pair.receipt_sha256===f.receiptSha256&&pair.relationship.history_transfer==='none'));
});
test('split successors require unique explicit new-group deltas and a complete crosswalk',()=>{
 for(const mutate of [f=>f.receipt.relationships.pop(),f=>f.receipt.relationships.push(structuredClone(f.receipt.relationships[0])),f=>f.receipt.group_changes.find(row=>row.id==='west').before={},f=>f.receipt.relationships[0].new_entity_id='neighbor',f=>f.receipt.relationships[0].old_entity_id='neighbor',f=>f.receipt.group_changes.push({id:'extra',before:null,after:unit('extra','province','a3')})]){const f=fixture();mutate(f);assert.throws(()=>validateMetadataRelationships(f));}
});
test('split endpoints cannot change tier, containing parent, registry identity or source/history proof',()=>{
 for(const mutate of [f=>f.receipt.group_changes.find(row=>row.id==='west').after.level='area',f=>f.receipt.group_changes.find(row=>row.id==='west').after.parent_id='c',f=>f.registry.delete('old'),f=>f.registry.get('old').kind='area',f=>f.receipt.historical_claims_transferred=true,f=>f.receipt.summary.geometry_changes=1,f=>f.receipt.source_evidence=[],f=>f.receipt.retired_units[0].metadata.original='forged']){const f=fixture();mutate(f);assert.throws(()=>validateMetadataRelationships(f));}
});
test('a same-count swap of unrelated territory fails exact split-member conservation',()=>{
 const f=fixture(),delta=f.receipt.group_changes.find(row=>row.id==='a2');delta.after.parent_id='neighbor';
 const other=f.units.find(row=>row.id==='a3');f.receipt.group_changes.push({id:other.id,before:structuredClone(other),after:{...other,parent_id:'east'}});
 assert.throws(()=>validateMetadataRelationships(f),/exact disjoint union/);
});
test('explicit local-group retirement retains every descendant and exact full archive',()=>{
 const f=fixture();f.receipt.group_changes=[];f.receipt.retired_units=[];f.receipt.relationships=[];
 for(const id of ['a1','p1']){const old=f.units.find(row=>row.id===id);f.receipt.group_changes.push({id,before:structuredClone(old),after:null});f.receipt.retired_units.push(structuredClone(old));f.receipt.relationships.push({old_entity_id:id,new_entity_id:null,change_type:'retire',reference_only:true,history_transfer:'none'});}
 const old=f.locations[0];f.receipt.changed_location_properties=[{location_id:old.id,before_properties:{...old},after_properties:{...old,parent_id:'p2'}}];
 const pairs=validateMetadataRelationships(f);assert.equal(pairs.length,2);assert.ok(pairs.every(pair=>pair.change_type==='retire'&&pair.new_entity_id===null));
 for(const mutate of [g=>g.receipt.relationships.pop(),g=>g.receipt.relationships[0].new_entity_id='a2',g=>g.receipt.changed_location_properties[0].after_properties.parent_id=null,g=>g.receipt.retired_units[0].metadata.original='edited']){const g={...f,receipt:structuredClone(f.receipt)};mutate(g);assert.throws(()=>validateMetadataRelationships(g));}
});
test('preparation emits every split pair and retains new identities, predecessor and original baseline',async()=>{
 const f=fixture(),directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-macro-split-'));
 try{
  const data=path.join(directory,'data'),geography=path.join(directory,'geography'),output=path.join(directory,'output');fs.mkdirSync(path.join(data,'hosted-catalog'),{recursive:true});fs.mkdirSync(path.join(data,'geographic-decisions'));fs.mkdirSync(geography);
  const write=(file,value)=>fs.writeFileSync(file,JSON.stringify(value));
  const entities=[...f.units.map(identity),...f.locations].map(row=>({...row,active:1,is_example:0,source_id:'source:original'})),catalogBytes=JSON.stringify({entities});fs.writeFileSync(path.join(data,'hosted-catalog/entities.json'),catalogBytes);write(path.join(data,'hosted-catalog/index.json'),{archive_sha256:'c'.repeat(64),batches:[{kind:'entities',path:'entities.json',sha256:sha(catalogBytes)}]});
  const features=f.locations.map((row,i)=>({type:'Feature',id:row.id,properties:{...row},geometry:{type:'Polygon',coordinates:[[[i,0],[i+.5,0],[i+.5,.5],[i,.5],[i,0]]]}}));write(path.join(data,'macro-corrections.json'),{footprints_sha256_before:footprintHash(features)});
  fs.writeFileSync(path.join(data,'geographic-decision-migration.json.gz'),gzipSync(JSON.stringify({before_units:f.units,group_changes:[],changes:[]})));
  for(let i=0;i<6;i++)write(path.join(data,'geographic-decisions',`${i}.json`),{decisions:[]});
  const current=new Map(f.units.map(row=>[row.id,row]));for(const delta of f.receipt.group_changes)if(delta.after)current.set(delta.id,delta.after);else current.delete(delta.id);
  write(path.join(geography,'hierarchy.json'),[...current.values()]);write(path.join(geography,'world-index.json'),{parts:['locations.json']});write(path.join(geography,'locations.json'),{features});const receiptFile=path.join(directory,'receipt.json');write(receiptFile,f.receipt);
  const result=await prepareGeographicRelease({data,geographyData:geography,output,geometryManifests:[],metadataMigrations:[receiptFile]});
  const changes=result.batches.filter(row=>row.path.startsWith('2-changes')).flatMap(row=>JSON.parse(fs.readFileSync(path.join(output,row.path))).changes),splits=changes.filter(row=>row.change_type==='split');
  assert.equal(splits.length,2);assert.equal(new Set(splits.map(row=>row.id)).size,2);assert.deepEqual(splits.map(row=>row.new_entity_id).sort(),['east','west']);assert.ok(!changes.some(row=>row.change_type==='retire'&&row.old_entity_id==='old'));assert.ok(splits.every(row=>row.evidence.history_transfer==='none'&&row.evidence.metadata_relationship));
  assert.equal(result.new_entities,2);const baseline=result.releases[0];assert.equal(baseline.expected_counts.region,2);assert.equal(result.releases[1].expected_counts.region,3);assert.equal(result.releases[1].footprints_sha256,baseline.footprints_sha256);
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
});

function creationFixture(){
 const f=fixture(),extra={id:'l4',name:'l4',parent_id:'p1',kind:'location'};f.locations.push(extra);f.beforeLocations.set(extra.id,extra);f.registry.set(extra.id,extra);
 const newArea=unit('new:a','area','neighbor'),newProvince=unit('new:p','province','new:a');
 f.receipt.retired_units=[];f.receipt.group_changes=[newArea,newProvince].map(row=>({id:row.id,before:null,after:row}));
 f.receipt.relationships=[{old_entity_id:null,new_entity_id:newArea.id,change_type:'create',reference_only:true,history_transfer:'none',derived_from_id:'a1'},{old_entity_id:null,new_entity_id:newProvince.id,change_type:'create',reference_only:true,history_transfer:'none',derived_from_id:'p1'}];
 const location=f.locations[0];f.receipt.changed_location_properties=[{location_id:location.id,before_properties:{...location},after_properties:{...location,parent_id:'new:p'}}];return f;
}
test('explicit reference creation can extract a location while retaining its original populated groups',()=>{
 const f=creationFixture(),pairs=validateMetadataRelationships(f);assert.equal(pairs.length,2);assert.ok(pairs.every(row=>row.old_entity_id===null&&row.change_type==='create'));
 assert.equal(f.beforeLocations.size,4);assert.equal(f.receipt.retired_units.length,0);
 for(const mutate of [g=>g.receipt.relationships.pop(),g=>g.receipt.relationships.push(structuredClone(g.receipt.relationships[0])),g=>g.receipt.relationships[0].old_entity_id='a1',g=>g.receipt.relationships[0].derived_from_id='p1',g=>g.receipt.relationships[1].derived_from_id='unknown',g=>g.registry.get('p1').kind='area',g=>g.receipt.changed_location_properties[0].after_properties.parent_id=null]){const g=creationFixture();mutate(g);assert.throws(()=>validateMetadataRelationships(g));}
});
test('sourced creations and explicit local-group retirements can share a conserving receipt',()=>{
 const f=creationFixture();for(const id of ['p2','a2']){const old=f.units.find(row=>row.id===id);f.receipt.group_changes.push({id,before:structuredClone(old),after:null});f.receipt.retired_units.push(structuredClone(old));f.receipt.relationships.push({old_entity_id:id,new_entity_id:null,change_type:'retire',reference_only:true,history_transfer:'none'});}
 const old=f.locations[1];f.receipt.changed_location_properties.push({location_id:old.id,before_properties:{...old},after_properties:{...old,parent_id:'new:p'}});const pairs=validateMetadataRelationships(f);assert.equal(pairs.length,4);assert.equal(pairs.filter(row=>row.change_type==='create').length,2);assert.equal(pairs.filter(row=>row.change_type==='retire').length,2);
});
test('release creation crosswalks retain source relationship evidence without null-old retirement collisions',async()=>{
 const f=creationFixture(),directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-macro-create-'));
 try{
  const data=path.join(directory,'data'),geography=path.join(directory,'geography'),output=path.join(directory,'output');fs.mkdirSync(path.join(data,'hosted-catalog'),{recursive:true});fs.mkdirSync(path.join(data,'geographic-decisions'));fs.mkdirSync(geography);
  const write=(file,value)=>fs.writeFileSync(file,JSON.stringify(value));
  const entities=[...f.units.map(identity),...f.locations].map(row=>({...row,active:1,is_example:0,source_id:'source:original'})),catalogBytes=JSON.stringify({entities});fs.writeFileSync(path.join(data,'hosted-catalog/entities.json'),catalogBytes);write(path.join(data,'hosted-catalog/index.json'),{archive_sha256:'c'.repeat(64),batches:[{kind:'entities',path:'entities.json',sha256:sha(catalogBytes)}]});
  const features=f.locations.map((row,i)=>({type:'Feature',id:row.id,properties:{...row},geometry:{type:'Polygon',coordinates:[[[i,0],[i+.5,0],[i+.5,.5],[i,.5],[i,0]]]}}));write(path.join(data,'macro-corrections.json'),{footprints_sha256_before:footprintHash(features)});
  fs.writeFileSync(path.join(data,'geographic-decision-migration.json.gz'),gzipSync(JSON.stringify({before_units:f.units,group_changes:[],changes:[]})));for(let i=0;i<6;i++)write(path.join(data,'geographic-decisions',`${i}.json`),{decisions:[]});
  write(path.join(geography,'hierarchy.json'),[...f.units,...f.receipt.group_changes.map(row=>row.after)]);for(const delta of f.receipt.changed_location_properties)features.find(row=>row.id===delta.location_id).properties=delta.after_properties;
  write(path.join(geography,'world-index.json'),{parts:['locations.json']});write(path.join(geography,'locations.json'),{features});const receiptFile=path.join(directory,'receipt.json');write(receiptFile,f.receipt);
  const result=await prepareGeographicRelease({data,geographyData:geography,output,geometryManifests:[],metadataMigrations:[receiptFile]});
  const changes=result.batches.filter(row=>row.path.startsWith('2-changes')).flatMap(row=>JSON.parse(fs.readFileSync(path.join(output,row.path))).changes),creates=changes.filter(row=>row.change_type==='create');assert.equal(creates.length,2);assert.ok(creates.every(row=>row.old_entity_id===null&&row.evidence.metadata_relationship.relationship.change_type==='create'));assert.equal(result.releases[1].expected_counts.location,4);assert.equal(result.releases[0].footprints_sha256,result.releases[1].footprints_sha256);assert.equal(changes.filter(row=>row.change_type==='retire').length,0);
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
});

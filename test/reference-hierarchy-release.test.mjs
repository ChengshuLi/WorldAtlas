import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {footprintHash} from '../scripts/check-prepared.mjs';
import {prepareGeographicRelease,validateMetadataRelationships} from '../scripts/prepare-geographic-release.mjs';

const sha=raw=>createHash('sha256').update(raw).digest('hex');
const normalized=row=>({id:row.id,name:row.name,parent_id:row.parent_id,kind:row.level??row.kind});
const receiptHash='a'.repeat(64);
function fixture(){
 const units=[
  {id:'c',name:'Continent',level:'continent',parent_id:null},
  {id:'s',name:'Subcontinent',level:'subcontinent',parent_id:'c'},
  {id:'r',name:'Region',level:'region',parent_id:'s'},
  {id:'a',name:'Area',level:'area',parent_id:'r'},
  {id:'old',name:'Named province',level:'province',parent_id:'a',metadata:{original:'preserve \n raw strings'}},
  {id:'survivor',name:'Named province',level:'province',parent_id:'a'},
  {id:'other',name:'Other province',level:'province',parent_id:'a'},
 ];
 const props=[{id:'l1',name:'One',parent_id:'old'},
  {id:'l2',name:'Two',parent_id:'survivor'},
  {id:'l3',name:'Three',parent_id:'survivor'},
  {id:'l4',name:'Four',parent_id:'other'}];
 const beforeGroups=new Map(units.map(row=>[row.id,normalized(row)]));
 const beforeLocations=new Map(props.map(row=>[row.id,{...row,kind:'location'}]));
 const relationship={old_entity_id:'old',new_entity_id:'survivor',change_type:'merge',
  reference_only:true,history_transfer:'none',proposal_id:'test:independent-source',
  evidence:{literal_json:' { "unicode": "阿", "precision": 1.0 } '}};
 const receipt={reference_only:true,historical_claims_transferred:false,summary:{geometry_changes:0},
  before_units:structuredClone(units),retired_units:[structuredClone(units[4])],
  group_changes:[{id:'old',before:structuredClone(units[4]),after:null}],
  changed_location_properties:[{location_id:'l1',before_properties:props[0],
   after_properties:{...props[0],parent_id:'survivor'}}],
  relationships:[relationship],source_evidence:[{url:'https://example.org/inspected-source',source_sha256:'b'.repeat(64)}]};
 const registry=new Map([...beforeGroups,...beforeLocations].map(([id,row])=>[id,structuredClone(row)]));
 return {beforeGroups,beforeLocations,beforeUnitRecords:new Map(units.map(row=>[row.id,structuredClone(row)])),
  receipt,receiptSha256:receiptHash,registry};
}

test('explicit metadata parent merge conserves full descendant identities and exact relationship provenance',()=>{
 const input=fixture(),before=JSON.stringify(input.receipt),pairs=validateMetadataRelationships(input);
 assert.equal(pairs.length,1);assert.equal(pairs[0].old_entity_id,'old');assert.equal(pairs[0].new_entity_id,'survivor');
 assert.deepEqual(pairs[0].relationship,input.receipt.relationships[0]);
 assert.equal(pairs[0].receipt_sha256,receiptHash);assert.equal(JSON.stringify(input.receipt),before);
});

test('receipts without the opt-in relationship field preserve the legacy preparation contract',()=>{
 const input=fixture();delete input.receipt.relationships;delete input.receipt.before_units;
 delete input.receipt.source_evidence;assert.deepEqual(validateMetadataRelationships(input),[]);
});

test('missing, duplicate, extra and unretired merge endpoints cannot masquerade as complete crosswalks',()=>{
 for(const mutate of [
  input=>input.receipt.relationships=[],
  input=>input.receipt.relationships.push(structuredClone(input.receipt.relationships[0])),
  input=>input.receipt.relationships[0].old_entity_id='other',
  input=>input.receipt.relationships[0].new_entity_id='missing',
 ]){const input=fixture();mutate(input);assert.throws(()=>validateMetadataRelationships(input),/every retired parent|extra, duplicate, unretired or missing/);}
});

test('same-tier registered identities and adjacent parent conservation are required',()=>{
 let input=fixture();input.receipt.relationships[0].new_entity_id='a';
 assert.throws(()=>validateMetadataRelationships(input),/same-tier/);
 input=fixture();input.registry.get('old').kind='area';
 assert.throws(()=>validateMetadataRelationships(input),/registered stable same-tier/);
 input=fixture();input.beforeGroups.get('survivor').parent_id='r';
 input.receipt.before_units.find(row=>row.id==='survivor').parent_id='r';
 input.beforeUnitRecords.get('survivor').parent_id='r';
 assert.throws(()=>validateMetadataRelationships(input),/adjacent-tier|unchanged adjacent-tier/);
});

test('a same-count swap of unrelated territories fails exact descendant-footprint conservation',()=>{
 const input=fixture();
 for(const [id,parent_id] of [['l2','other'],['l4','survivor']]){
  const original=input.beforeLocations.get(id),before={id,name:original.name,parent_id:original.parent_id};
  input.receipt.changed_location_properties.push({location_id:id,before_properties:before,
   after_properties:{...before,parent_id}});
 }
 // The survivor still has three members. Their identities are not the original union.
 assert.throws(()=>validateMetadataRelationships(input),/exact union/);
});

test('complete original unit records, explicit source proof and zero historical transfer are required',()=>{
 for(const mutate of [
  input=>input.receipt.retired_units[0].metadata.original='rewritten',
  input=>input.receipt.group_changes[0].before.metadata.original='rewritten',
  input=>input.receipt.before_units.pop(),
  input=>{
   input.receipt.before_units.find(row=>row.id==='old').metadata.original='forged in both';
   input.receipt.group_changes[0].before.metadata.original='forged in both';
   input.receipt.retired_units[0].metadata.original='forged in both';
  },
  input=>input.receipt.source_evidence=[],
  input=>input.receipt.historical_claims_transferred=true,
  input=>input.receipt.relationships[0].history_transfer='copy-records',
 ]){const input=fixture();mutate(input);assert.throws(()=>validateMetadataRelationships(input),/original|archive|source URLs|history|every retired/);}
});

test('small release preparation preserves the exact baseline, merge provenance and every original member',async()=>{
 const f=fixture(),temporary=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-reference-merge-'));
 try{
  const data=path.join(temporary,'data'),before=path.join(temporary,'before'),after=path.join(temporary,'after');
  const published=path.join(temporary,'published'),output=path.join(temporary,'prepared');
  for(const directory of [path.join(data,'hosted-catalog'),path.join(data,'geographic-decisions'),before,after])fs.mkdirSync(directory,{recursive:true});
  const write=(file,value)=>fs.writeFileSync(file,JSON.stringify(value));
  const units=[...f.beforeUnitRecords.values()],locations=[...f.beforeLocations.values()];
  const entities=[...f.beforeGroups.values(),...locations].map(row=>({...row,active:1,is_example:0,source_id:'source:original'}));
  const catalog=JSON.stringify({entities});fs.writeFileSync(path.join(data,'hosted-catalog/entities.json'),catalog);
  write(path.join(data,'hosted-catalog/index.json'),{archive_sha256:'c'.repeat(64),batches:[{kind:'entities',path:'entities.json',sha256:sha(catalog)}]});
  const features=locations.map((row,i)=>({type:'Feature',id:row.id,properties:{id:row.id,name:row.name,parent_id:row.parent_id},
   geometry:{type:'Polygon',coordinates:[[[i,0],[i+.5,0],[i+.5,.5],[i,.5],[i,0]]]}}));
  const footprints=footprintHash(features);write(path.join(data,'macro-corrections.json'),{footprints_sha256_before:footprints});
  fs.writeFileSync(path.join(data,'geographic-decision-migration.json.gz'),gzipSync(JSON.stringify({before_units:units,group_changes:[],changes:[]})));
  for(let i=0;i<6;i++)write(path.join(data,'geographic-decisions',`${i}.json`),{decisions:[]});
  write(path.join(before,'hierarchy.json'),units);write(path.join(before,'world-index.json'),{parts:['locations.json']});
  write(path.join(before,'locations.json'),{features});
  const currentUnits=new Map(units.map(row=>[row.id,row]));
  for(const delta of f.receipt.group_changes)if(delta.after)currentUnits.set(delta.id,delta.after);else currentUnits.delete(delta.id);
  const currentFeatures=structuredClone(features);
  for(const delta of f.receipt.changed_location_properties)currentFeatures.find(row=>row.id===delta.location_id).properties=delta.after_properties;
  write(path.join(after,'hierarchy.json'),[...currentUnits.values()]);write(path.join(after,'world-index.json'),{parts:['locations.json']});
  write(path.join(after,'locations.json'),{features:currentFeatures});
  const receiptFile=path.join(temporary,'receipt.json');write(receiptFile,f.receipt);
  const snapshot=directory=>fs.readdirSync(directory,{recursive:true,withFileTypes:true}).filter(row=>row.isFile())
   .map(row=>{const file=path.join(row.parentPath,row.name);return[path.relative(directory,file),sha(fs.readFileSync(file))];}).sort(([a],[b])=>a.localeCompare(b));
  const inputs=new Map([data,before,after].map(directory=>[directory,snapshot(directory)])),receiptBytes=fs.readFileSync(receiptFile);
  const baseline=await prepareGeographicRelease({data,geographyData:before,output:published,geometryManifests:[],metadataMigrations:[]});
  const registryManifest=path.join(published,'index.json'),registrySnapshot=snapshot(published);
  const generated=await prepareGeographicRelease({data,geographyData:after,output,reviewedVersion:3,
   registryManifests:[registryManifest],geometryManifests:[],metadataMigrations:[receiptFile]});
  assert.deepEqual(generated.releases[0],baseline.releases[0],'Baseline release stays exactly immutable');
  assert.deepEqual(fs.readFileSync(path.join(output,'release-1.json')),fs.readFileSync(path.join(published,'release-1.json')));
  assert.deepEqual(generated.registered_identity_manifest_sha256,{[sha(fs.readFileSync(registryManifest))]:baseline.releases.at(-1).id});
  assert.equal(generated.new_entities,0);assert.equal(generated.releases[1].expected_counts.location,locations.length);
  assert.equal(generated.releases[1].expected_counts.province,2);assert.equal(generated.total_memberships,entities.length);
  assert.equal(generated.releases[1].footprints_sha256,footprints);assert.equal(generated.releases[0].footprints_sha256,footprints);
  assert.deepEqual(currentFeatures.map(row=>row.geometry),features.map(row=>row.geometry));
  const changes=[],members=new Map();
  for(const batch of generated.batches){
   const raw=fs.readFileSync(path.join(output,batch.path));assert.equal(sha(raw),batch.sha256);assert.ok(raw.byteLength<=1048576);
   const payload=JSON.parse(raw);if(payload.release_id!==generated.releases[1].id)continue;
   changes.push(...payload.changes??[]);for(const member of payload.memberships??[]){assert.ok(!members.has(member.entity_id));members.set(member.entity_id,member);}
  }
  const pair=f.receipt.relationships[0],merge=changes.filter(row=>row.old_entity_id===pair.old_entity_id);
  assert.equal(merge.length,1);assert.equal(merge[0].change_type,'merge');assert.equal(merge[0].new_entity_id,pair.new_entity_id);
  assert.deepEqual(merge[0].evidence.metadata_relationship.relationship,pair);
  assert.deepEqual(merge[0].evidence.metadata_relationship.source_evidence,f.receipt.source_evidence);
  assert.equal(merge[0].evidence.metadata_relationship.receipt_sha256,sha(receiptBytes));
  assert.deepEqual(changes.map(row=>[row.change_type,row.old_entity_id,row.new_entity_id]).sort(),[['merge','old','survivor'],['reparent','l1','l1']]);
  assert.deepEqual([...members.keys()].sort(),entities.map(row=>row.id).sort());
  assert.deepEqual([...members.values()].filter(row=>row.kind==='location').map(row=>row.entity_id).sort(),locations.map(row=>row.id).sort());
  for(const original of entities){
   const member=members.get(original.id);assert.equal(member.kind,original.kind);assert.equal(member.reference_name,original.name);
   assert.equal(member.active,Number(original.id!==pair.old_entity_id));
   assert.equal(member.parent_id,original.id==='l1'?pair.new_entity_id:original.parent_id);
   assert.equal(member.evidence.original_source_id,original.source_id);assert.equal(member.evidence.history_transfer,'none');
  }
  assert.ok(changes.every(row=>row.evidence.history_transfer==='none'));
  await assert.rejects(prepareGeographicRelease({data,geographyData:after,output:path.join(temporary,'without-receipt'),
   registryManifests:[registryManifest],geometryManifests:[],metadataMigrations:[]}),/Unreceipted geographic identity/);
  assert.equal(fs.existsSync(path.join(temporary,'without-receipt')),false);
  for(const [directory,original] of inputs)assert.deepEqual(snapshot(directory),original,'Original input tree remains unchanged');
  assert.deepEqual(snapshot(published),registrySnapshot,'Original registry and batches remain unchanged');
  assert.deepEqual(fs.readFileSync(receiptFile),receiptBytes);
 }finally{fs.rmSync(temporary,{recursive:true,force:true});}
});

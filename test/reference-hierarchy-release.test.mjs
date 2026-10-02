import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {prepareGeographicRelease,validateMetadataRelationships} from '../scripts/prepare-geographic-release.mjs';

const root=path.resolve(import.meta.dirname,'..'),data=path.join(root,'data');
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const read=file=>JSON.parse(file.endsWith('.gz')?gunzipSync(fs.readFileSync(file)):fs.readFileSync(file));
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

test('the complete real candidate validates all 49,589 locations and the 55-county source-backed merge',()=>{
 const receipt=read(path.join(data,'reference-hierarchy-corrections/migration-receipt.json.gz'));
 const beforeGroups=new Map(receipt.before_units.map(row=>[row.id,normalized(row)])),beforeLocations=new Map();
 const world=read(path.join(data,'world-index.json'));
 for(const part of world.parts)for(const feature of read(path.join(data,part)).features){
  const p=feature.properties;beforeLocations.set(feature.id,{id:feature.id,name:p.name,parent_id:p.parent_id,kind:'location'});
 }
 assert.equal(beforeLocations.size,49589);assert.equal(beforeGroups.size,5705);
 const pairs=validateMetadataRelationships({beforeGroups,beforeLocations,receipt,
  receiptSha256:sha(fs.readFileSync(path.join(data,'reference-hierarchy-corrections/migration-receipt.json.gz')))});
 assert.equal(pairs.length,1);assert.equal(pairs[0].new_entity_id,'framework:province:west-virginia:4c9dc6438fb1');
 const proof=receipt.affected_group_footprints.find(row=>row.id===pairs[0].new_entity_id);
 assert.equal(proof.before.member_location_ids.length,54);assert.equal(proof.after.member_location_ids.length,55);
 assert.ok(proof.after.member_location_ids.includes('gb:USA:ADM2:52423323B20661288428578'));
 assert.equal(receipt.unchanged_geometry_ids.length,49589);
 assert.equal(receipt.footprints_sha256_before,receipt.footprints_sha256_after);
 assert.equal(receipt.historical_claims_transferred,false);
});

test('full candidate release preparation emits the explicit merge, archived predecessor and exact unchanged baseline',async()=>{
 const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-reference-hierarchy-release-'));
 const receiptFile=path.join(data,'reference-hierarchy-corrections/migration-receipt.json.gz'),receipt=read(receiptFile);
 const registryManifest=path.join(data,'geographic-releases/index.json'),published=read(registryManifest);
 const snapshot=new Map([registryManifest,path.join(data,'hierarchy.json'),path.join(data,'hosted-catalog/index.json')]
  .map(file=>[file,sha(fs.readFileSync(file))]));
 try{
  const geography=path.join(temporary,'geography'),output=path.join(temporary,'prepared');fs.mkdirSync(geography);
  const deltas=new Map(receipt.group_changes.map(row=>[row.id,row]));
  const units=receipt.before_units.flatMap(row=>deltas.has(row.id)?deltas.get(row.id).after?[deltas.get(row.id).after]:[]:[row]);
  fs.writeFileSync(path.join(geography,'hierarchy.json'),JSON.stringify(units));
  const index=read(path.join(data,'world-index.json'));fs.copyFileSync(path.join(data,'world-index.json'),path.join(geography,'world-index.json'));
  const pair=receipt.relationships[0];
  for(const part of index.parts){
   const target=path.join(geography,part);fs.mkdirSync(path.dirname(target),{recursive:true});
   const raw=fs.readFileSync(path.join(data,part));
   fs.writeFileSync(target,part===receipt.candidate.changed_geography_part?Buffer.from(raw.toString().replace(pair.old_entity_id,pair.new_entity_id)):raw);
  }
  const generated=await prepareGeographicRelease({data,geographyData:geography,output,reviewedVersion:3,
   registryManifests:[registryManifest],metadataMigrations:[path.join(data,'macro-boundary-migration.json.gz'),receiptFile]});
  assert.deepEqual(generated.releases[0],published.releases[0],'Baseline release stays exactly immutable');
  assert.equal(generated.new_entities,0);assert.equal(generated.releases[1].expected_counts.location,49589);
  assert.equal(generated.releases[1].expected_counts.province,5132);
  assert.equal(generated.releases[1].footprints_sha256,receipt.footprints_sha256_after);
  const changes=[],members=new Map();
  for(const batch of generated.batches){
   const raw=fs.readFileSync(path.join(output,batch.path));assert.equal(sha(raw),batch.sha256);assert.ok(raw.byteLength<=1048576);
   const payload=JSON.parse(raw);if(payload.release_id!==generated.releases[1].id)continue;
   changes.push(...payload.changes??[]);for(const member of payload.memberships??[])members.set(member.entity_id,member);
  }
  const merge=changes.filter(row=>row.old_entity_id===pair.old_entity_id);
  assert.equal(merge.length,1);assert.equal(merge[0].change_type,'merge');assert.equal(merge[0].new_entity_id,pair.new_entity_id);
  assert.deepEqual(merge[0].evidence.metadata_relationship.relationship,pair);
  assert.deepEqual(merge[0].evidence.metadata_relationship.source_evidence,receipt.source_evidence);
  assert.equal(merge[0].evidence.metadata_relationship.receipt_sha256,sha(fs.readFileSync(receiptFile)));
  assert.equal(merge[0].evidence.history_transfer,'none');assert.equal(members.get(pair.old_entity_id).active,0);
  assert.equal(members.get(pair.old_entity_id).reference_name,'West Virginia');
  assert.equal(members.get('gb:USA:ADM2:52423323B20661288428578').parent_id,pair.new_entity_id);
  for(const [file,hash] of snapshot)assert.equal(sha(fs.readFileSync(file)),hash,'Original atlas/registry remains unchanged');
 }finally{fs.rmSync(temporary,{recursive:true,force:true});}
});

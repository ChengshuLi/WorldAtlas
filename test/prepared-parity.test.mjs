import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {decodeDerived} from '../src/derived-records.js';
import {decodeReferences} from '../src/reference-records.js';
import {derivedRecordsAt} from '../derived.mjs';
import {resolveAttributes} from '../src/attributes.js';
import {resolveTemporal} from '../src/temporal.js';
import {snapshot} from '../database.mjs';
import {temporalCatalog} from '../temporal.mjs';
import {runtimeOwnershipBucket,runtimeOwnershipData} from '../src/runtime-ownership.js';

const root=path.resolve(import.meta.dirname,'..');
const read=file=>JSON.parse(file.endsWith('.gz')?gunzipSync(fs.readFileSync(file)):fs.readFileSync(file,'utf8'));
function canonical(value){
 if(Array.isArray(value))return value.map(canonical);
 if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().filter(k=>value[k]!==undefined).map(k=>[k,canonical(value[k])]));
 return value;
}
function fingerprint(rows){
 const hash=createHash('sha256');
 for(const row of [...rows].sort((a,b)=>String(a.id??a.location_id).localeCompare(String(b.id??b.location_id))))hash.update(JSON.stringify(canonical(row))).update('\n');
 return hash.digest('hex');
}
function prepared(directory,kind){
 const index=read(path.join(directory,'index.json'));
 const parts=index.parts.map(p=>read(path.join(directory,typeof p==='string'?p:p.path)));
 if(kind==='owner'&&index.evidence_parts)index.evidence=index.evidence_parts.flatMap(p=>read(path.join(directory,p.path)));
 return {index,parts};
}

// Interpret the on-disk tables independently of the production codecs. Checking
// only two callers of the same codec could conceal a corrupted compact table.
function expectedReferences({index,parts},year){
 if(index.version===1)return parts.flat().filter(r=>r.valid_from<=year&&year<r.valid_to);
 return parts.flatMap(part=>part.flatMap(([location_id,values])=>values.flatMap(([type,value,share,coverage])=>{
  const t=index.types[type];
  return t.valid_from<=year&&year<t.valid_to?[{...t,id:`reference:${location_id}:${t.attribute}:${t.valid_from}`,location_id,value:index.values[value],metadata:{...t.metadata,share,coverage}}]:[];
 })));
}
function expectedOwners({index,parts},year){
 const records=[];
 for(const [location_id,intervals] of parts.flat()){
  const row=intervals.find(r=>r[0]<=year&&year<r[1]);if(!row)continue;
  const [valid_from,valid_to,owner,status,evidence]=row;
  let category_id=owner,metadata=evidence,resolvedStatus=status;
  if(index.version===2){
   category_id=owner==null?null:index.owner_ids[owner];resolvedStatus=index.statuses_order[status];
   index.parityMetadata ||= new Map();metadata=index.parityMetadata.get(evidence);
   if(!metadata){const [name,share,coverage,candidates,sources,dated]=index.evidence[evidence];metadata={owner_name:name==null?null:index.labels[name],share,coverage,candidates:candidates.map(([i,s])=>[index.owner_ids[i],s]),source_record_ids:sources.map(i=>index.source_ids[i]),footprint:dated?'dated':'reference'};index.parityMetadata.set(evidence,metadata);}
  }
  records.push({valid_from,valid_to,category_id,status:resolvedStatus,metadata,id:`ownership:${location_id}:${valid_from}`,location_id,attribute:'owner',value:category_id?(metadata.owner_name||index.entities[category_id].name):null,method:'majority-area',source:index.source,source_url:index.source_url});
 }
 return records;
}
function ownershipSnapshots(directory,years){
 const index=read(path.join(directory,'index.json')),selected=new Map(years.map(year=>[year,[]])),needed=new Set();
 for(const p of index.parts)for(const [id,intervals] of read(path.join(directory,p.path)))for(const year of years){
  let left=0,right=intervals.length;
  while(left<right){const mid=(left+right)>>>1;if(intervals[mid][0]<=year)left=mid+1;else right=mid;}
  const row=intervals[left-1];if(row&&row[1]>year){selected.get(year).push([id,[row]]);if(index.version===2)needed.add(row[4]);}
 }
 if(index.version===2){
  const evidence=new Map();let offset=0;
  for(const p of index.evidence_parts){const rows=read(path.join(directory,p.path));for(let i=0;i<rows.length;i++)if(needed.has(offset+i))evidence.set(offset+i,rows[i]);offset+=rows.length;}
  assert.equal(evidence.size,needed.size);index.evidence=new Proxy({}, {get:(_,key)=>evidence.get(Number(key))});
 }
 const output=new Map();
 for(const [year,rows] of selected)output.set(year,expectedOwners({index,parts:[rows]},year));
 return output;
}
function selectedStates(records,year,examples){
 const locations=new Map();
 for(const r of records)if(r.valid_from<=year&&r.valid_to>year&&(!r.is_example||examples)){
  const old=locations.get(r.location_id);if(!old||old.is_example>r.is_example)locations.set(r.location_id,r);
 }
 return [...locations.values()];
}

test('ownership codecs preserve identity, dated labels, competing evidence and the BC/AD edge',()=>{
 const source='Explicit majority fixture',source_url='https://example.org/fixture';
 const entities={'owner:fixed':{name:'Reference label'}};
 const metadata=(name,share,coverage,candidates,ids,footprint='reference')=>({owner_name:name,share,coverage,candidates,source_record_ids:ids,footprint});
 const rows=[[-1,1,null,'no-majority',metadata(null,.45,.45,[['owner:fixed',.45]],['partial'])],[1,1000,'owner:fixed','derived',metadata('Old label',.7,.7,[['owner:fixed',.7]],['early'])],[1000,1100,'owner:fixed','derived',metadata('New label',.8,.8,[['owner:fixed',.8]],['late'],'dated')],[1100,1200,null,'disputed',metadata(null,.8,1,[['owner:fixed',.8]],['claim-a','claim-b'])]];
 const v1={index:{version:1,source,source_url,entities},parts:[[['location:fixture',rows]]]};
 const v2={index:{version:2,source,source_url,entities,owner_ids:['owner:fixed'],labels:['Old label','New label'],source_ids:['partial','early','late','claim-a','claim-b'],statuses_order:['derived','disputed','no-majority','unknown'],evidence:[[null,.45,.45,[[0,.45]],[0],0],[0,.7,.7,[[0,.7]],[1],0],[1,.8,.8,[[0,.8]],[2],1],[null,.8,1,[[0,.8]],[3,4],0]]},parts:[[['location:fixture',[[-1,1,null,2,0],[1,1000,0,0,1],[1000,1100,0,0,2],[1100,1200,null,1,3]]]]]};
 for(const year of [-2,-1,1,999,1000,1099,1100,1199,1200]){
  const expected=expectedOwners(v1,year);
  assert.deepEqual(decodeDerived(v1.parts,v1.index,year),expected);
  assert.deepEqual(decodeDerived(v2.parts,v2.index,year),expected);
 }
 const old=decodeDerived(v2.parts,v2.index,999)[0],renamed=decodeDerived(v2.parts,v2.index,1000)[0];
 assert.equal(old.category_id,renamed.category_id);assert.equal(old.value,'Old label');assert.equal(renamed.value,'New label');
 assert.equal(renamed.metadata.footprint,'dated');assert.equal(decodeDerived(v2.parts,v2.index,1100)[0].value,null);
});

test('actual environmental tables decode exactly at all normal-period boundaries',()=>{
 const data=prepared(path.join(root,'data/reference-attributes'),'reference');
 assert.equal(data.index.version,2);
 assert.equal(data.parts.flat().reduce((n,[,v])=>n+v.length,0),data.index.records);
 for(const year of [-3000,-1,1,1000,1900,1901,1930,1931,1960,1961,1990,1991,2020,2021,2025,2026]){
  const expected=expectedReferences(data,year),decoded=decodeReferences(data.parts,data.index,year);
  assert.equal(decoded.length,expected.length,`reference count at ${year}`);
  assert.equal(fingerprint(decoded),fingerprint(expected),`reference value/provenance at ${year}`);
 }
 assert.equal(expectedReferences(data,2021).length,0);
 assert.equal(expectedReferences(data,2026).filter(r=>r.attribute==='climate').length,data.index.climate_counts['1991']);
 for(const r of expectedReferences(data,2026)){
  assert.ok(r.source&&r.metadata.source_url);assert.ok(r.metadata.share>=0&&r.metadata.share<=1);
  assert.ok(r.value===null||typeof r.value==='string'&&r.value.trim()&&!/^(N\/A|unknown|not mapped)$/i.test(r.value),`Missing source class must be an explicit unknown: ${r.location_id}`);
  if(r.attribute==='vegetation')assert.match(r.source,/potential natural/);
 }
});

test('reference codecs preserve supported precision and do not bridge unsupported intervals',()=>{
 const type={attribute:'population',valid_from:1900,valid_to:1901,method:'estimate',status:'estimate',source:'Dated census fixture',metadata:{precision:'hundreds',source_year:1900}};
 const record={...type,id:'reference:l:population:1900',location_id:'l',value:1200,metadata:{...type.metadata,share:null,coverage:null}};
 const v1={version:1},v2={version:2,types:[type],values:[1200]};
 for(const year of [1899,1900,1901,2026]){
  const expected=year===1900?[record]:[];
  assert.deepEqual(decodeReferences([[record]],v1,year),expected);
  assert.deepEqual(decodeReferences([[['l',[[0,0,null,null]]]]],v2,year),expected);
 }
});

const ownerPath=path.join(root,'data/ownership-history/index.json');
const haveOwners=fs.existsSync(ownerPath)&&fs.existsSync(path.join(root,'data/ownership-runtime/index.json'));
test('actual prepared historical records match independent compact-table interpretation',{skip:!haveOwners&&!process.env.ATLAS_REQUIRE_PREPARED?'ownership preparation not finished':false},()=>{
 assert.ok(haveOwners,'Ownership preparation is required for publication');
 const years=[-3000,-1,1,1000,1444,1901,1931,1961,1991,2020,2024,2025,2026],owners=ownershipSnapshots(path.dirname(ownerPath),years),references=prepared(path.join(root,'data/reference-attributes'),'reference');
 for(const year of years){
  const expected=[...owners.get(year),...expectedReferences(references,year)];
  assert.equal(fingerprint(derivedRecordsAt(year)),fingerprint(expected),`server prepared values/evidence at ${year}`);
 }
 assert.equal(owners.get(2025).length,0,'Unsupported recent ownership is not carried forward');
 assert.equal(owners.get(2026).length,0,'Modern political references are resolved separately');
});

const staticRoot=fs.existsSync(path.join(root,'dist/client/atlas-geography.json'))?path.join(root,'dist/client'):path.join(root,'dist');
const haveStatic=fs.existsSync(path.join(staticRoot,'atlas-geography.json'))&&fs.existsSync(path.join(staticRoot,'ownership-runtime/index.json'));
test('static and server exports resolve every active location identically, with examples on and off',{skip:!haveStatic&&!process.env.ATLAS_REQUIRE_STATIC?'full static export not built':false},()=>{
 assert.ok(haveStatic,'A complete static build is required for publication');
 const manifest=read(path.join(staticRoot,'atlas-geography.json'));
 const reference={...manifest,features:manifest.parts.flatMap(p=>read(path.join(staticRoot,p))),temporal:{...manifest.temporal,entities:manifest.entityParts.flatMap(p=>read(path.join(staticRoot,p))),history:manifest.temporalHistoryParts.flatMap(p=>read(path.join(staticRoot,p)))}};
 const history=read(path.join(staticRoot,'atlas-history.json.gz'));
 const years=[-3000,-1,1,1000,1444,1901,1931,1961,1991,2020,2024,2025,2026],owners=ownershipSnapshots(path.join(root,'data/ownership-history'),years),references=prepared(path.join(staticRoot,'reference-attributes'),'reference');
 const runtime=read(path.join(staticRoot,'ownership-runtime/index.json')),buckets=new Map();
 assert.equal(runtime.source_index_sha256,createHash('sha256').update(fs.readFileSync(ownerPath)).digest('hex'),'Static ownership is derived from the current prepared source');
 const db=new DatabaseSync(path.join(root,'data/atlas.sqlite'),{readOnly:true});
 try{
  const serverFeatures=db.prepare('SELECT id,name,parent_id,reference_owner,metadata,active FROM locations WHERE active=1 ORDER BY id').all().map(({metadata,...properties})=>({id:properties.id,properties:{...properties,metadata:JSON.parse(metadata)}}));
  const serverUnits=db.prepare('WITH RECURSIVE used(id) AS (SELECT parent_id FROM locations WHERE active=1 UNION SELECT u.parent_id FROM units u JOIN used x ON u.id=x.id WHERE u.parent_id IS NOT NULL) SELECT * FROM units WHERE id IN (SELECT id FROM used)').all().map(u=>({...u,metadata:JSON.parse(u.metadata)}));
  const serverReference={features:serverFeatures,units:serverUnits,temporal:temporalCatalog(db)};
  assert.equal(fingerprint(reference.units),fingerprint(serverUnits),'Static geographic tiers and parent memberships match the database');
  assert.equal(reference.features.length,serverFeatures.length);
  assert.equal(fingerprint(reference.features.map(f=>({id:f.id,properties:f.properties}))),fingerprint(serverFeatures.map(f=>({id:f.id,properties:f.properties}))), 'Static location catalog matches the database');
  assert.equal(fingerprint(reference.temporal.entities),fingerprint(serverReference.temporal.entities),'Static identity catalog preserves archived entities');
  assert.equal(fingerprint(reference.temporal.history),fingerprint(serverReference.temporal.history),'Static dated identity records match the database');
  for(const year of years){
   const selected=runtimeOwnershipBucket(runtime,year);let staticOwners=[];
   if(selected){if(!buckets.has(selected.path)){buckets.set(selected.path,read(path.join(staticRoot,'ownership-runtime',selected.path)));while(buckets.size>2)buckets.delete(buckets.keys().next().value);}const data=runtimeOwnershipData(runtime,buckets.get(selected.path),year);staticOwners=decodeDerived(data.parts,data.index,year);}
   const staticOwnerFingerprint=fingerprint(staticOwners),preparedOwnerFingerprint=fingerprint(owners.get(year)),referenceRecords=expectedReferences(references,year);
   for(const examples of [false,true]){
    const server=snapshot(db,year,examples);
    assert.equal(staticOwnerFingerprint,preparedOwnerFingerprint,`Actual static temporal transport preserves prepared source values at ${year}`);
    const exported={states:selectedStates(history.states,year,examples),attributes:[...staticOwners,...referenceRecords,...(history.attributes||[]).filter(r=>r.valid_from<=year&&r.valid_to>year&&(!r.is_example||examples))]};
    assert.deepEqual(server.polities,[],'Normal Political mode has no independent source polygon layer');
    const serverTemporal=resolveTemporal(serverReference,year,examples),staticTemporal=resolveTemporal(reference,year,examples);
    const resolve=(features,state,temporal)=>[...resolveAttributes(features,year,{states:state.states,records:state.attributes,temporal,examples}).values()];
    const actual=resolve(serverTemporal.features,server,serverTemporal),expected=resolve(staticTemporal.features,exported,staticTemporal);
    assert.equal(actual.length,expected.length,`active locations at ${year}/${examples}`);
    assert.equal(fingerprint(actual),fingerprint(expected),`all resolved fields/provenance at ${year}/${examples}`);
   }
  }
 }finally{db.close();}
});

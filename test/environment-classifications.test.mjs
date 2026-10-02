import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,readdirSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {environmentClassifications,environmentalClassification,validEnvironmentalClassification,classificationValues} from '../src/environment-classifications.js';
import {resolveAttributes} from '../src/attributes.js';
import {categoryColor} from '../src/model.js';
import {previewImport} from '../src/import-records.js';
import {openDatabase,importRecords} from '../database.mjs';
import {importBatch,attributesAt} from '../hosted/records.js';
import worker from '../hosted/worker.js';

const fields=['topography','vegetation','climate'];
const features=[{id:'location',properties:{name:'Reference location'}}];
const source={id:'source',name:'Documented test source',license:'CC0',vintage:'1000',supported_from:1000,supported_to:1100,status:'historical'};
const tiers=['continent','subcontinent','region','area','province'];
const units=tiers.map((level,i)=>({id:level,name:level,level,parent_id:i?tiers[i-1]:null}));
const row=(id,attribute,value,extra={})=>({id,location_id:'location',attribute,value,valid_from:1000,valid_to:1100,method:'direct',source:'Documented test source',source_id:'source',...extra});
class D1{
 constructor(beforeGuard=false){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');for(const name of readdirSync(new URL('../drizzle/',import.meta.url)).filter(f=>f.endsWith('.sql')&&(!beforeGuard||Number(f.slice(0,4))<7)).sort())this.sqlite.exec(readFileSync(new URL(`../drizzle/${name}`,import.meta.url),'utf8'));}
 prepare(sql){const db=this.sqlite;let args=[];return {bind(...values){args=values;return this;},async all(){return {results:db.prepare(sql).all(...args)};},async first(){return db.prepare(sql).get(...args)??null;},run(){return {meta:{changes:Number(db.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN');try{const result=statements.map(s=>s.run());this.sqlite.exec('COMMIT');return result;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
async function databases(beforeGuard=false){
 const local=openDatabase(':memory:'),hosted=new D1(beforeGuard);
 importRecords(local,{units,locations:[{id:'location',name:'Reference location',parent_id:'province',geometry:{type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]}}]});
 await importBatch(hosted,JSON.parse(readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));
 await importBatch(hosted,{sources:[source],entities:[...units.map(u=>({id:u.id,name:u.name,kind:u.level,parent_id:u.parent_id})),{id:'location',kind:'location',name:'Reference location',parent_id:'province'}]});
 return {local,hosted};
}

test('fixed environmental classifications have unique stable identities and cover every existing reference value',()=>{
 const identities=new Set();
 for(const attribute of fields){
  assert.ok(environmentClassifications[attribute].length>0);
  assert.ok(classificationValues(attribute).length>0);
  for(const entry of environmentClassifications[attribute]){
   assert.ok(entry.id.startsWith(attribute+':'));assert.ok(!identities.has(entry.id));identities.add(entry.id);
   for(const spelling of [entry.id,entry.label,...entry.aliases]){
    assert.equal(environmentalClassification(attribute,spelling)?.id,entry.id,`${attribute}: ${spelling}`);
    assert.equal(validEnvironmentalClassification(attribute,spelling),true);
   }
  }
  assert.equal(validEnvironmentalClassification(attribute,null),true);
  for(const value of ['unknown','invented free-form description','',3,true,[],{}])assert.equal(validEnvironmentalClassification(attribute,value),false,`${attribute}: ${JSON.stringify(value)}`);
 }
 const index=JSON.parse(readFileSync(new URL('../data/reference-attributes/index.json',import.meta.url)));
 for(const value of index.values)assert.ok(fields.some(attribute=>validEnvironmentalClassification(attribute,value)),`Unmapped retained reference value: ${value}`);
 assert.equal(environmentalClassification('vegetation','farmlands').id,'vegetation:farmlands');
 assert.equal(environmentalClassification('topography','flatland').id,'topography:flat');
 assert.equal(environmentalClassification('climate','oceanic').id,'climate:oceanic');
 assert.notEqual(environmentalClassification('climate','oceanic').id,environmentalClassification('climate','Cfb').id,'A broad sourced climate must not invent a finer Köppen class');
 assert.equal(validEnvironmentalClassification('vegetation','climate:Cfb'),false);
});

test('classification API exposes the exact fixed vocabulary independently of database content',async()=>{
 const response=await worker.fetch(new Request('https://example.org/api/classifications'),{});
 assert.equal(response.status,200);
 const result=await response.json();
 assert.deepEqual(result,{version:1,unknown:null,attributes:environmentClassifications});
});

test('aliases and stable IDs produce identical whole-location values, colors and category identities',()=>{
 for(const [attribute,alias]of [['topography','flatland'],['vegetation','farmlands'],['climate','oceanic']]){
  const entry=environmentalClassification(attribute,alias),resolve=value=>resolveAttributes(features,1050,{records:[row('claim',attribute,value)]}).get('location');
  for(const spelling of [alias,entry.id,entry.label]){
   const state=resolve(spelling);assert.equal(state[attribute],entry.label);assert.equal(state.category_ids[attribute],entry.id);
   assert.equal(categoryColor(state.category_ids[attribute]),categoryColor(entry.id));
   assert.equal(state.provenance[attribute].id,'claim');
  }
  const unknown=resolve(null);assert.equal(unknown[attribute],null);assert.equal(unknown.category_ids[attribute],null);
  const unmapped=resolve('invented retained historical text');assert.equal(unmapped[attribute],null);assert.equal(unmapped.category_ids[attribute],null,'Old free-form evidence must not create a new legend category');
  const blocked=resolveAttributes(features,1050,{records:[row('direct',attribute,'invented retained historical text'),row('derived',attribute,entry.id,{method:'derived'})]}).get('location');assert.equal(blocked[attribute],null,'Unsupported direct evidence must not quietly fall back to a weaker assignment');
 }
});

test('preview, both importers and raw SQL reject environmental typos while retaining explicit unknowns',async()=>{
 const {local,hosted}=await databases();try{
  for(const [attribute,invalid]of [['topography','flattland'],['vegetation','farmland-ish mixed country'],['climate','oceannic']]){
   const invalidRow=row(`invalid:${attribute}`,attribute,invalid);
   assert.throws(()=>previewImport(JSON.stringify({records:[invalidRow]})),/classification|vocabulary/i);
   assert.throws(()=>importRecords(local,{attribute_records:[invalidRow]}),/classification|vocabulary/i);
   await assert.rejects(importBatch(hosted,{records:[invalidRow]}),error=>error.status===400&&/classification|vocabulary/i.test(error.message));
   assert.throws(()=>local.prepare('INSERT INTO attribute_records VALUES(?,?,?,?,?,?,?,?,?,?,?,?)').run(invalidRow.id,'location',attribute,JSON.stringify(invalid),null,1000,1100,'direct','sourced',source.name,0,'{}'),/classification|vocabulary/i);
   assert.throws(()=>hosted.sqlite.prepare('INSERT INTO atlas_attribute_records(id,location_id,attribute,value,valid_from,valid_to,method,status,source_id) VALUES(?,?,?,?,?,?,?,?,?)').run(invalidRow.id,'location',attribute,JSON.stringify(invalid),1000,1100,'direct','sourced','source'),/classification|vocabulary/i);
   const unknown=row(`unknown:${attribute}`,attribute,null);
   assert.equal(previewImport(JSON.stringify({records:[unknown]})).rows[0].value,null);
   importRecords(local,{attribute_records:[unknown]});await importBatch(hosted,{records:[unknown]});
  }
  assert.equal(local.prepare('SELECT count(*) n FROM attribute_records').get().n,3);
  assert.equal(hosted.sqlite.prepare('SELECT count(*) n FROM atlas_attribute_records').get().n,3);
  const state=resolveAttributes(features,1050,{records:(await attributesAt(hosted,1050)).records}).get('location');for(const attribute of fields){assert.equal(state[attribute],null);assert.equal(state.category_ids[attribute],null);}
 }finally{local.close();hosted.sqlite.close();}
});

test('grandfathered free-form evidence is retained and exact hosted replays stay idempotent without admitting new text',async()=>{
 const {local,hosted}=await databases(true);try{
  const original=row('retained-legacy','climate','Ancient poetic source description',{status:'sourced'});
  hosted.sqlite.prepare('INSERT INTO atlas_attribute_records(id,location_id,attribute,value,valid_from,valid_to,method,status,source_id) VALUES(?,?,?,?,?,?,?,?,?)').run(original.id,'location','climate',JSON.stringify(original.value),1000,1100,'direct','sourced','source');
  const before=JSON.stringify(hosted.sqlite.prepare('SELECT * FROM atlas_attribute_records').all());
  hosted.sqlite.exec(readFileSync(new URL('../drizzle/0007_fixed_environment_classifications.sql',import.meta.url),'utf8'));
  await importBatch(hosted,{ingestion_id:'legacy-replay',records:[original]});
  assert.equal((await importBatch(hosted,{ingestion_id:'legacy-replay',records:[original]})).duplicate,true);
  assert.equal(JSON.stringify(hosted.sqlite.prepare('SELECT * FROM atlas_attribute_records').all()),before);
  await assert.rejects(importBatch(hosted,{records:[{...original,id:'new-free-form'}]}),error=>error.status===400&&/classification|vocabulary/i.test(error.message));
  await assert.rejects(importBatch(hosted,{records:[{...original,value:'Different new poetic description'}]}),error=>error.status===400&&/classification|vocabulary/i.test(error.message));
  await assert.rejects(importBatch(hosted,{records:[{...original,value:'climate:Af'}]}),/Stable ID collision/);
  const resolved=resolveAttributes(features,1050,{records:(await attributesAt(hosted,1050)).records}).get('location');assert.equal(resolved.climate,null);assert.equal(resolved.category_ids.climate,null);assert.equal(resolved.provenance.climate.metadata.unmapped_source_value,original.value);
 }finally{local.close();hosted.sqlite.close();}
});

test('accepted aliases and canonical identities remain source evidence instead of rewriting imported records',async()=>{
 const {local,hosted}=await databases();try{
  const claims=[row('flat','topography','flatland'),row('farmland','vegetation','vegetation:farmlands'),row('oceanic','climate','oceanic')];
  assert.equal(previewImport(JSON.stringify({records:claims})).rows.length,3);
  importRecords(local,{attribute_records:claims});await importBatch(hosted,{records:claims});
  const hostedClaims=(await attributesAt(hosted,1050)).records;
  const localClaims=local.prepare('SELECT * FROM attribute_records').all().map(r=>({...r,value:JSON.parse(r.value)}));
  for(const original of claims){assert.equal(hostedClaims.find(r=>r.id===original.id).value,original.value);assert.equal(localClaims.find(r=>r.id===original.id).value,original.value);}
  const left=resolveAttributes(features,1050,{records:localClaims}).get('location'),right=resolveAttributes(features,1050,{records:hostedClaims}).get('location');
  for(const attribute of fields){assert.equal(left[attribute],right[attribute]);assert.equal(left.category_ids[attribute],right.category_ids[attribute]);}
 }finally{local.close();hosted.sqlite.close();}
});

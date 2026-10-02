import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {resolveAttributes,locationAttributes,unresolvedAttributeStatuses} from '../src/attributes.js';
import {categoryColor,populationColor} from '../src/model.js';
import {previewImport} from '../src/import-records.js';
import {openDatabase,importRecords} from '../database.mjs';
import {importBatch,attributesAt} from '../hosted/records.js';
const root=path.resolve(import.meta.dirname,'..');
const features=[{id:'l',properties:{reference_owner:'Modern owner',metadata:{reference_owner_id:'owner:modern'}}}];
const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]};
const tiers=['continent','subcontinent','region','area','province'];
const units=tiers.map((level,at)=>({id:level,name:level,level,...(at?{parent_id:tiers[at-1]}:{})}));
const claim=(id,attribute,value,extra={})=>({id,location_id:'l',attribute,value,valid_from:1000,valid_to:1100,method:'direct',status:'sourced',source:'Observed source',source_id:'source',...extra});
const values={owner:'Known owner',culture:'Known culture',religion:'Known faith',population:42,rank:'city',habitation:'inhabited',topography:'flatland',vegetation:'farmlands',climate:'oceanic'};
const categorical=['owner','culture','religion'];
class D1{
 constructor(beforeGuard=false){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');for(const file of fs.readdirSync(path.join(root,'drizzle')).filter(f=>f.endsWith('.sql')&&(!beforeGuard||Number(f.slice(0,4))<6)).sort())this.sqlite.exec(fs.readFileSync(path.join(root,'drizzle',file),'utf8'));}
 prepare(sql){const sqlite=this.sqlite;let args=[];return {bind(...v){args=v;return this;},async all(){return {results:sqlite.prepare(sql).all(...args)};},async first(){return sqlite.prepare(sql).get(...args)??null;},run(){return {meta:{changes:Number(sqlite.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const results=statements.map(s=>s.run());this.sqlite.exec('COMMIT');return results;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
async function hosted(beforeGuard=false){const db=new D1(beforeGuard);await importBatch(db,JSON.parse(fs.readFileSync(path.join(root,'data/hosted-type-catalog.json'))));await importBatch(db,{sources:[{id:'source',name:'Observed source',license:'CC0',vintage:'1000',supported_from:1000,supported_to:2027,status:'historical'}],entities:[...units.map(u=>({id:u.id,kind:u.level,name:u.name,parent_id:u.parent_id??null})),{id:'l',kind:'location',name:'l',parent_id:'province'},...categorical.map(kind=>({id:`category:${kind}`,kind:kind==='owner'?'polity':kind,name:values[kind]}))],categories:categorical.map(kind=>({id:`category:${kind}`,kind,name:values[kind],source_id:'source'}))});return db;}
function local(){const db=openDatabase(':memory:');importRecords(db,{units,locations:[{id:'l',name:'l',parent_id:'province',geometry}],attribute_entities:categorical.map(kind=>({id:`category:${kind}`,kind,name:values[kind],source:'Observed source'}))});return db;}
const rawHosted=(db,row)=>db.sqlite.prepare('INSERT INTO atlas_attribute_records(id,location_id,attribute,value,category_id,valid_from,valid_to,method,status,source_id,is_example,metadata) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)').run(row.id,'l',row.attribute,JSON.stringify(row.value),row.category_id??null,row.valid_from,row.valid_to,row.method,row.status,'source',0,'{}');
const rawLocal=(db,row)=>db.prepare('INSERT INTO attribute_records VALUES(?,?,?,?,?,?,?,?,?,?,?,?)').run(row.id,'l',row.attribute,JSON.stringify(row.value),row.category_id??null,row.valid_from,row.valid_to,row.method,row.status,'Observed source',0,'{}');

test('malformed unresolved evidence resolves to the unknown fill for every attribute, including category IDs',()=>{
 for(const status of unresolvedAttributeStatuses){
  const records=locationAttributes.map(attribute=>claim(`${status}:${attribute}`,attribute,values[attribute],{status,...(categorical.includes(attribute)?{category_id:`category:${attribute}`}:{})}));
  const result=resolveAttributes(features,1050,{records}).get('l');
  for(const attribute of locationAttributes){assert.equal(result[attribute],null,`${status}/${attribute}`);assert.equal(result.provenance[attribute].status,status);const fill=attribute==='population'?populationColor(result.population,100):categoryColor(result.category_ids[attribute]??result[attribute]);assert.equal(fill,categoryColor(null),`${attribute} must use the actual map's unknown-fill expression`);if(categorical.includes(attribute))assert.equal(result.category_ids[attribute],null);}
 }
 const reference=structuredClone(features);reference[0].properties.metadata.reference_polity_status='disputed';
 assert.equal(resolveAttributes(reference,2026).get('l').owner,null);assert.equal(resolveAttributes(reference,2026).get('l').category_ids.owner,null);
});

test('direct unresolved evidence blocks weaker assignments and modern fallback without losing its provenance',()=>{
 for(const status of unresolvedAttributeStatuses)for(const attribute of locationAttributes){
  const records=[claim('direct',attribute,null,{status,valid_from:2026,valid_to:2027}),claim('derived',attribute,values[attribute],{method:'derived',status:'derived',valid_from:2026,valid_to:2027}),claim('reference',attribute,values[attribute],{method:'reference',status:'reference',valid_from:2026,valid_to:2027})];
  if(attribute==='rank')records.push(claim('literal-zero','population',0,{valid_from:2026,valid_to:2027}));
  const result=resolveAttributes(features,2026,{records}).get('l');assert.equal(result[attribute],null,`${status}/${attribute}`);assert.equal(result.provenance[attribute].id,'direct');assert.equal(result.provenance[attribute].status,status);if(categorical.includes(attribute))assert.equal(result.category_ids[attribute],null);
 }
});

test('API, local import, UI preview and raw SQL reject both unresolved/non-null contract violations',async()=>{
 const db=await hosted(),legacy=local();try{
  for(const status of unresolvedAttributeStatuses){
   for(const attribute of locationAttributes){const invalid=claim(`invalid:${status}:${attribute}`,attribute,values[attribute],{status,valid_from:1200,valid_to:1300,...(categorical.includes(attribute)?{category_id:`category:${attribute}`}:{})});await assert.rejects(importBatch(db,{records:[invalid]}),/Unresolved attribute/);assert.throws(()=>importRecords(legacy,{attribute_records:[invalid]}),/Unresolved attribute/);assert.throws(()=>previewImport(JSON.stringify({records:[invalid]})),/Unresolved attribute/);assert.throws(()=>rawHosted(db,invalid),/Unresolved attribute/);assert.throws(()=>rawLocal(legacy,invalid),/Unresolved attribute/);}
   const categoryOnly=claim(`category-only:${status}`,'owner',null,{status,category_id:'category:owner',valid_from:1200,valid_to:1300});await assert.rejects(importBatch(db,{records:[categoryOnly]}),/Unresolved attribute|known categorical/);assert.throws(()=>importRecords(legacy,{attribute_records:[categoryOnly]}),/Unresolved attribute|known categorical/);assert.throws(()=>previewImport(JSON.stringify({records:[categoryOnly]})),/Unresolved attribute/);assert.throws(()=>rawHosted(db,categoryOnly),/Unresolved attribute/);assert.throws(()=>rawLocal(legacy,categoryOnly),/Unresolved attribute|known categorical/);
   const start=1000+unresolvedAttributeStatuses.indexOf(status),valid=claim(`valid:${status}`,'owner',null,{status,valid_from:start,valid_to:start+1});await importBatch(db,{records:[valid]});importRecords(legacy,{attribute_records:[valid]});assert.equal(previewImport(JSON.stringify({records:[valid]})).rows[0].value,null);
  }
  assert.equal(db.sqlite.prepare('SELECT count(*) n FROM atlas_attribute_records').get().n,3);assert.equal(legacy.prepare('SELECT count(*) n FROM attribute_records').get().n,3);
 }finally{db.sqlite.close();legacy.close();}
});

test('0006 preserves populated claims, retirements and all existing schema objects while suppressing retained malformed claims',async()=>{
 const db=await hosted(true);try{
  // Malformed retained evidence was legal before 0006. Do not rewrite it.
  rawHosted(db,claim('old-malformed','owner','Known owner',{status:'unknown',category_id:'category:owner'}));rawHosted(db,claim('old-pop','population',42));await importBatch(db,{retirements:[{id:'withdraw-pop',collection:'records',target_id:'old-pop',source_id:'source',reason:'Observed correction'}]});
  const rows=table=>JSON.stringify(db.sqlite.prepare(`SELECT * FROM ${table} ORDER BY id`).all()),before=Object.fromEntries(['atlas_attribute_records','atlas_evidence_retirements','atlas_entities','atlas_sources'].map(t=>[t,rows(t)])),objects=db.sqlite.prepare("SELECT type,name,sql FROM sqlite_master WHERE type IN ('index','trigger') ORDER BY type,name").all();
  db.sqlite.exec(fs.readFileSync(path.join(root,'drizzle/0006_unresolved_attribute_status_guard.sql'),'utf8'));
  for(const [table,pinned]of Object.entries(before))assert.equal(rows(table),pinned);assert.deepEqual(db.sqlite.prepare("SELECT type,name,sql FROM sqlite_master WHERE type IN ('index','trigger') AND name!='atlas_attribute_unresolved_status' ORDER BY type,name").all(),objects);assert.deepEqual(db.sqlite.prepare('PRAGMA foreign_key_check').all(),[]);
  const result=resolveAttributes(features,1050,{records:(await attributesAt(db,1050)).records}).get('l');assert.equal(result.owner,null);assert.equal(result.category_ids.owner,null);assert.equal(result.provenance.owner.id,'old-malformed');
  assert.throws(()=>rawHosted(db,claim('new-invalid','climate','oceanic',{status:'disputed'})),/Unresolved attribute/);assert.throws(()=>db.sqlite.exec("UPDATE atlas_attribute_records SET value='null' WHERE id='old-malformed'"),/append-only/);assert.throws(()=>db.sqlite.exec("DELETE FROM atlas_attribute_records WHERE id='old-malformed'"),/retained/);
 }finally{db.sqlite.close();}
});

test('opening a populated legacy local database retains malformed historical claims and applies the new INSERT guard',()=>{
 const folder=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-unresolved-legacy-')),file=path.join(folder,'atlas.sqlite');try{
  const old=openDatabase(file);importRecords(old,{units,locations:[{id:'l',name:'l',parent_id:'province',geometry}]});old.exec('DROP TRIGGER attribute_record_unresolved_status');rawLocal(old,claim('old-malformed','population',42,{status:'unknown'}));const before=JSON.stringify(old.prepare('SELECT * FROM attribute_records').all());old.close();
  const reopened=openDatabase(file);assert.equal(JSON.stringify(reopened.prepare('SELECT * FROM attribute_records').all()),before);assert.throws(()=>rawLocal(reopened,claim('new-invalid','climate','oceanic',{status:'disputed'})),/Unresolved attribute/);assert.deepEqual(reopened.prepare('PRAGMA foreign_key_check').all(),[]);reopened.close();
 }finally{fs.rmSync(folder,{recursive:true,force:true});}
});

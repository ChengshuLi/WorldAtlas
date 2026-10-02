import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {openDatabase,importRecords} from '../database.mjs';
import {classificationValues,environmentalAttributes} from '../src/environment-classifications.js';
import {compileEnvironmentGuards,hostedEnvironmentGuardSql} from '../scripts/compile-environment-classification-guards.mjs';

const units=['continent','subcontinent','region','area','province'].map((level,i,all)=>({id:level,name:level,level,parent_id:i?all[i-1]:null}));
const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]};
const seed={units,locations:[{id:'l',name:'Location',parent_id:'province',geometry}]};
const schema=fs.readFileSync(new URL('../data/schema.sql',import.meta.url),'utf8');
const marker='-- Fixed environmental classification guards: generated from src/environment-classifications.js.';
const typed=(db,id,attribute,value,from=1000,hosted=false)=>db.prepare(`INSERT ${hosted?'OR IGNORE ':''}INTO ${hosted?'atlas_':''}attribute_records(id,location_id,attribute,value,valid_from,valid_to,method,status,${hosted?'source_id':'source'}) VALUES(?,'l',?,?,?,?,'direct','sourced',?)`).run(id,attribute,JSON.stringify(value),from,from+1,hosted?'s':'Source');
const snapshot=(db,id,attribute,value,from=1000)=>db.prepare(`INSERT INTO states(id,location_id,valid_from,valid_to,${attribute},source) VALUES(?,'l',?,?,?,'Source')`).run(id,from,from+1,value);
const history=(db,id,attribute,value,from=1000)=>db.prepare("INSERT INTO entity_history(id,entity_id,field,valid_from,valid_to,value,source) VALUES(?,'l','attributes',?,?,?,'Source')").run(id,from,from+1,JSON.stringify({[attribute]:value}));
function local(legacy=false){const db=legacy?new DatabaseSync(':memory:'):openDatabase(':memory:');if(legacy)db.exec(schema.slice(0,schema.indexOf(marker)));importRecords(db,seed);return db;}
function hosted(legacy=false){const db=new DatabaseSync(':memory:');db.exec('PRAGMA foreign_keys=ON');for(const file of fs.readdirSync(new URL('../drizzle/',import.meta.url)).filter(file=>file.endsWith('.sql')).sort()){if(legacy&&file.startsWith('0007_'))continue;db.exec(fs.readFileSync(new URL(`../drizzle/${file}`,import.meta.url),'utf8'));}db.exec("INSERT INTO atlas_sources(id,name,license,vintage,supported_from,supported_to,status) VALUES('s','Source','CC0','2026',-3000,2027,'historical')");for(const [i,kind]of ['continent','subcontinent','region','area','province','location'].entries()){db.prepare('INSERT INTO atlas_entity_types(id,name,geographic_level) VALUES(?,?,?)').run(kind,kind,5-i);db.prepare('INSERT INTO atlas_entities(id,kind,name,parent_id) VALUES(?,?,?,?)').run(kind==='location'?'l':kind,kind,kind,i?['continent','subcontinent','region','area','province'][i-1]:null);}return db;}

test('fixed environmental database guards reproduce exactly from the shared registry',()=>{assert.doesNotThrow(()=>compileEnvironmentGuards({check:true}));assert.equal(fs.readFileSync(new URL('../drizzle/0007_fixed_environment_classifications.sql',import.meta.url),'utf8'),hostedEnvironmentGuardSql());});

test('all fixed IDs, display labels, explicit legacy aliases and null pass raw local and hosted SQL',()=>{
 const db=local(),remote=hosted();let row=0;
 try{for(const attribute of environmentalAttributes)for(const value of [...classificationValues(attribute),null]){const id=`class-${++row}`,from=1000+row;typed(db,id,attribute,value,from);typed(remote,id,attribute,value,from,true);snapshot(db,row,attribute,value,from);history(db,id,attribute,value,from);}assert.equal(db.prepare('SELECT count(*) n FROM attribute_records').get().n,row);assert.equal(remote.prepare('SELECT count(*) n FROM atlas_attribute_records').get().n,row);}finally{db.close();remote.close();}
});

test('unlisted environmental values reject every local import and raw snapshot/history/typed insertion',()=>{
 const db=local(),remote=hosted();try{for(const attribute of environmentalAttributes){const value=`Unlisted ${attribute}`,record={id:`bad-${attribute}`,location_id:'l',attribute,value,valid_from:1000,valid_to:1001,source:'Source'};
  assert.throws(()=>importRecords(db,{attribute_records:[record]}),/classification/);
  assert.throws(()=>importRecords(db,{states:[{location_id:'l',valid_from:1000,valid_to:1001,[attribute]:value,source:'Source'}]}),/classification/);
  assert.throws(()=>importRecords(db,{entity_history:[{id:record.id,entity_id:'l',field:'attributes',value:{[attribute]:value},valid_from:1000,valid_to:1001,source:'Source'}]}),/classification/);
  assert.throws(()=>typed(db,record.id,attribute,value),/classification/);assert.throws(()=>typed(remote,record.id,attribute,value,1000,true),/classification/);assert.throws(()=>snapshot(db,1,attribute,value),/classification/);assert.throws(()=>history(db,record.id,attribute,value),/classification/);
 }for(const table of ['attribute_records','states','entity_history'])assert.equal(db.prepare(`SELECT count(*) n FROM ${table}`).get().n,0);}finally{db.close();remote.close();}
});

test('adding local guards preserves existing unrecognized evidence byte for byte and blocks changed values',()=>{
 const db=local(true);try{typed(db,'legacy','climate','Old free-form climate');snapshot(db,1,'topography','Old free-form terrain',1001);history(db,'legacy','vegetation','Old free-form vegetation',1002);const before=Object.fromEntries(['attribute_records','states','entity_history'].map(table=>[table,JSON.stringify(db.prepare(`SELECT * FROM ${table}`).all())]));db.exec(schema);for(const [table,bytes]of Object.entries(before))assert.equal(JSON.stringify(db.prepare(`SELECT * FROM ${table}`).all()),bytes);
 assert.throws(()=>typed(db,'new','climate','Old free-form climate',1003),/classification/);assert.throws(()=>db.exec("UPDATE states SET topography='Another free-form terrain' WHERE id=1"),/classification/);assert.throws(()=>db.exec("UPDATE entity_history SET value='{\"vegetation\":\"Another free-form vegetation\"}' WHERE id='legacy'"),/classification/);
 assert.throws(()=>db.exec("INSERT OR REPLACE INTO states(id,location_id,valid_from,valid_to,topography,source) VALUES(1,'l',1001,1002,'Another free-form terrain','Source')"),/classification/);assert.throws(()=>db.exec("INSERT OR REPLACE INTO entity_history(id,entity_id,field,valid_from,valid_to,value,source) VALUES('legacy','l','attributes',1002,1003,'{\"vegetation\":\"Another free-form vegetation\"}','Source')"),/classification/);
 db.exec("UPDATE states SET population=42 WHERE id=1");assert.equal(db.prepare('SELECT topography FROM states WHERE id=1').get().topography,'Old free-form terrain');assert.deepEqual(db.prepare('PRAGMA foreign_key_check').all(),[]);}finally{db.close();}
});

test('hosted migration retains old claim bytes, permits exact retries and still rejects stable-ID collisions',()=>{
 const db=hosted(true);try{typed(db,'legacy','climate','Old free-form climate',1000,true);const before=JSON.stringify(db.prepare('SELECT * FROM atlas_attribute_records').all());db.exec(hostedEnvironmentGuardSql());assert.equal(JSON.stringify(db.prepare('SELECT * FROM atlas_attribute_records').all()),before);typed(db,'legacy','climate','Old free-form climate',1000,true);assert.equal(JSON.stringify(db.prepare('SELECT * FROM atlas_attribute_records').all()),before);assert.throws(()=>typed(db,'legacy','climate','Changed free-form climate',1000,true),/Stable ID collision/);assert.throws(()=>typed(db,'new','climate','Old free-form climate',1001,true),/classification/);assert.deepEqual(db.prepare('PRAGMA foreign_key_check').all(),[]);}finally{db.close();}
});

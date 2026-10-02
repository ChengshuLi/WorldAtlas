import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {gzipSync,gunzipSync} from 'node:zlib';
import {openDatabase,importRecords} from '../database.mjs';
import {restoreReferenceArchive} from '../reference-archive.mjs';
const polygon={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]};
const units=[{id:'c',name:'Continent',level:'continent',parent_id:null},{id:'s',name:'Subcontinent',level:'subcontinent',parent_id:'c'},{id:'r',name:'Region',level:'region',parent_id:'s'},{id:'a',name:'Area',level:'area',parent_id:'r'},{id:'p',name:'Province',level:'province',parent_id:'a'}];
const makeArchive=()=>({version:1,kind:'undated-cartographic-reference-archive',historical_effective_year:null,units,locations:[{id:'old',name:'Original territory',parent_id:'p',geometry:polygon,reference_owner:'Original reference territory',metadata:{license:'Public Domain'}}],original_entities:[{id:'settlement',kind:'settlement',name:'Example settlement',parent_id:'old',valid_from:null,valid_to:null,source:null,is_example:1}],original_records:{states:{rows:[[17,'old',1000,1100,'Owner',null,null,null,null,null,null,null,1,'Original fixture']]},boundaries:{rows:[]},entity_history:{rows:[['original-name','settlement','name',1000,1100,'en','preferred','"Old name"','Original name fixture',1]]},entity_links:{rows:[]}}});
function withArchive(archive,fn){const folder=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-archive-'));const file=path.join(folder,'archive.json.gz');fs.writeFileSync(file,gzipSync(JSON.stringify(archive)));try{return fn(file);}finally{fs.rmSync(folder,{recursive:true,force:true});}}

test('reference restoration preserves archived IDs, source context and exact original records idempotently',()=>{
 const db=openDatabase(':memory:');try{withArchive(makeArchive(),file=>{
  const first=restoreReferenceArchive(db,file);assert.equal(first.locations,1);assert.equal(first.states,1);assert.equal(first.entity_history,1);assert.equal(first.entities,1);
  assert.equal(db.prepare("SELECT active FROM locations WHERE id='old'").get().active,0);
  assert.equal(db.prepare("SELECT reference_owner FROM locations WHERE id='old'").get().reference_owner,'Original reference territory');
  assert.deepEqual(Object.values(db.prepare('SELECT * FROM states WHERE id=17').get()),makeArchive().original_records.states.rows[0]);
  assert.deepEqual(Object.values(db.prepare("SELECT * FROM entity_history WHERE id='original-name'").get()),makeArchive().original_records.entity_history.rows[0]);
  assert.equal(db.prepare('SELECT count(*) n FROM entity_links').get().n,0);
  assert.deepEqual(restoreReferenceArchive(db,file),{units:0,locations:0,entities:0,states:0,boundaries:0,entity_history:0,entity_links:0});
 });}finally{db.close();}
});

test('existing active territory names, geometry, parents and owner context are never overwritten',()=>{
 const db=openDatabase(':memory:');try{
  const geometry={type:'Polygon',coordinates:[[[2,0],[3,0],[3,1],[2,0]]]};
  importRecords(db,{units:units.map(u=>({...u,name:`Current ${u.name}`})),locations:[{id:'old',name:'User territory',parent_id:'p',geometry,reference_owner:'User context',metadata:{source_name:'User source'}}]});
  const before=db.prepare("SELECT * FROM locations WHERE id='old'").get();const unitBefore=db.prepare("SELECT * FROM units WHERE id='p'").get();
  withArchive(makeArchive(),file=>restoreReferenceArchive(db,file));
  assert.deepEqual(db.prepare("SELECT * FROM locations WHERE id='old'").get(),before);assert.deepEqual(db.prepare("SELECT * FROM units WHERE id='p'").get(),unitBefore);
 }finally{db.close();}
});

test('original record ID conflicts fail explicitly and restoration rolls back broken archives',()=>{
 const db=openDatabase(':memory:');try{
  importRecords(db,{units,locations:[{id:'user',name:'User territory',parent_id:'p',geometry:polygon}],states:[{location_id:'user',valid_from:1000,valid_to:1100,owner:'User evidence',source:'User source'}]});
  const archive=makeArchive();archive.original_records.states.rows[0][0]=1;
  withArchive(archive,file=>assert.throws(()=>restoreReferenceArchive(db,file),/Archive record collision: states\/1/));
  assert.equal(db.prepare("SELECT count(*) n FROM locations WHERE id='old'").get().n,0);
  const broken=makeArchive();broken.locations[0].parent_id='missing-province';
  withArchive(broken,file=>assert.throws(()=>restoreReferenceArchive(db,file),/requires a province/));
  assert.equal(db.prepare("SELECT count(*) n FROM locations WHERE id='old'").get().n,0);
  assert.equal(db.prepare('SELECT count(*) n FROM states').get().n,1);
 }finally{db.close();}
});

test('the published source archive restores every original record into a fresh reference database',()=>{
 const db=openDatabase(':memory:');try{
  const archiveURL=new URL('../data/geographic-migration-archive.json.gz',import.meta.url);
  const archive=JSON.parse(gunzipSync(fs.readFileSync(archiveURL)));
  const archived=new Set(archive.locations.map(l=>l.id));
  const hosts=new Set(archive.original_records.states.rows.map(r=>r[1]));
  const index=JSON.parse(fs.readFileSync(new URL('../data/world-index.json',import.meta.url),'utf8'));
  const current=index.parts.flatMap(part=>JSON.parse(fs.readFileSync(new URL(`../data/${part}`,import.meta.url),'utf8')).features).filter(f=>hosts.has(f.id)&&!archived.has(f.id));
  const currentUnits=JSON.parse(fs.readFileSync(new URL('../data/hierarchy.json',import.meta.url),'utf8'));
  importRecords(db,{units:currentUnits,locations:current.map(f=>({...f.properties,geometry:f.geometry}))});
  const first=restoreReferenceArchive(db,archiveURL);assert.equal(first.locations,archive.locations.length);assert.equal(first.states,9);assert.equal(first.entity_history,6);
  for(const table of ['states','boundaries','entity_history','entity_links'])for(const row of archive.original_records[table].rows)assert.deepEqual(Object.values(db.prepare(`SELECT * FROM ${table} WHERE id=?`).get(row[0])),row);
  assert.equal(db.prepare('SELECT count(*) n FROM locations WHERE active=0').get().n,archive.locations.length);
  assert.deepEqual(restoreReferenceArchive(db,archiveURL),{units:0,locations:0,entities:0,states:0,boundaries:0,entity_history:0,entity_links:0});
 }finally{db.close();}
});

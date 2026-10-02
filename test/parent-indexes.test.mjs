import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {openDatabase,importRecords} from '../database.mjs';

const indexes=['units_parent_id','locations_parent_id'];
const units=[
 {id:'c',name:'Continent',level:'continent',parent_id:null},
 {id:'s',name:'Subcontinent',level:'subcontinent',parent_id:'c'},
 {id:'r',name:'Region',level:'region',parent_id:'s'},
 {id:'a',name:'Area',level:'area',parent_id:'r'},
 {id:'p',name:'Province',level:'province',parent_id:'a'},
 {id:'unused',name:'Unused province',level:'province',parent_id:'a'},
];
const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]};
const deletion='WITH RECURSIVE used(id) AS (SELECT parent_id FROM locations UNION SELECT u.parent_id FROM units u JOIN used x ON u.id=x.id WHERE u.parent_id IS NOT NULL) DELETE FROM units WHERE id NOT IN (SELECT id FROM used)';
const plan=(db,sql,...params)=>db.prepare('EXPLAIN QUERY PLAN '+sql).all(...params).map(row=>row.detail);
function assertIndexedParents(db){
 for(const table of ['units','locations']){
  const details=plan(db,`SELECT id FROM ${table} WHERE parent_id=?`,'p');
  assert.ok(details.some(detail=>new RegExp(`SEARCH ${table} USING (?:COVERING )?INDEX ${table}_parent_id`).test(detail)),details.join('\n'));
 }
 const details=plan(db,deletion);
 assert.ok(details.some(detail=>/SEARCH locations USING COVERING INDEX locations_parent_id/.test(detail)),details.join('\n'));
 assert.ok(details.some(detail=>/SEARCH units USING COVERING INDEX units_parent_id/.test(detail)),details.join('\n'));
}

test('parent lookups and unused-unit foreign-key checks use local parent indexes',()=>{
 const db=openDatabase(':memory:');
 try{assertIndexedParents(db);}finally{db.close();}
});

test('opening a populated pre-index database installs parent indexes without rewriting geography or evidence',()=>{
 const folder=mkdtempSync(join(tmpdir(),'atlas-parent-indexes-')),file=join(folder,'legacy.sqlite');
 let db;
 try{
  db=new DatabaseSync(file);
  const legacy=readFileSync(new URL('../data/schema.sql',import.meta.url),'utf8').replace(/^CREATE INDEX IF NOT EXISTS (?:units|locations)_parent_id ON (?:units|locations)\(parent_id\);\n/gm,'');
  db.exec(legacy);
  importRecords(db,{units,locations:[{id:'l',name:'Local territory',parent_id:'p',geometry,reference_owner:'Reference owner',metadata:{source_name:'Preservation fixture'}}],states:[{location_id:'l',valid_from:1000,valid_to:1100,population:42,rank:'town',source:'Snapshot fixture'}],entity_history:[{id:'name',entity_id:'l',field:'name',value:'Dated title',valid_from:1000,valid_to:1100,source:'Name fixture'}],attribute_records:[{id:'population',location_id:'l',attribute:'population',value:42,valid_from:1100,valid_to:1200,source:'Typed fixture',method:'direct',status:'sourced'}]});
  assert.ok(!db.prepare("SELECT name FROM sqlite_schema WHERE type='index'").all().some(row=>indexes.includes(row.name)));
  const tables=db.prepare("SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name").all().map(row=>row.name);
  const before=Object.fromEntries(tables.map(table=>[table,db.prepare(`SELECT * FROM ${table} ORDER BY id`).all()]));
  const originalIndexes=db.prepare("SELECT name,sql FROM sqlite_schema WHERE type='index' ORDER BY name").all();
  db.close();db=openDatabase(file);
  assertIndexedParents(db);
  for(const [table,rows] of Object.entries(before))assert.deepEqual(db.prepare(`SELECT * FROM ${table} ORDER BY id`).all(),rows,`${table} rows preserved`);
  assert.deepEqual(db.prepare("SELECT name,sql FROM sqlite_schema WHERE type='index' ORDER BY name").all().filter(row=>!indexes.includes(row.name)),originalIndexes);
  assert.deepEqual(db.prepare('PRAGMA foreign_key_check').all(),[]);
  db.close();db=openDatabase(file);assertIndexedParents(db);
  for(const [table,rows] of Object.entries(before))assert.deepEqual(db.prepare(`SELECT * FROM ${table} ORDER BY id`).all(),rows,`${table} rows remain preserved after reopening`);
 }finally{db?.close();rmSync(folder,{recursive:true,force:true});}
});

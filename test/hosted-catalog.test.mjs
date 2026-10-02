import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {DatabaseSync} from 'node:sqlite';
import {openDatabase,importRecords} from '../database.mjs';
import {prepareHostedCatalog} from '../scripts/prepare-hosted-catalog.mjs';
import {importBatch,entityProfile,attributesAt,namesAt} from '../hosted/records.js';
const hash=value=>createHash('sha256').update(value).digest('hex');
class D1 {
 constructor(){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');for(const file of fs.readdirSync(new URL('../drizzle/',import.meta.url)).filter(f=>f.endsWith('.sql')).sort())this.sqlite.exec(fs.readFileSync(new URL(`../drizzle/${file}`,import.meta.url),'utf8'));if(!this.sqlite.prepare("SELECT 1 FROM sqlite_master WHERE type='trigger' AND name='atlas_entities_immutable'").get())this.sqlite.exec(fs.readFileSync(new URL('../hosted/records-constraints.sql',import.meta.url),'utf8'));}
 prepare(sql){const sqlite=this.sqlite;let args=[];return{bind(...values){args=values;return this;},async all(){return{results:sqlite.prepare(sql).all(...args)};},async first(){return sqlite.prepare(sql).get(...args)??null;},run(){return{meta:{changes:Number(sqlite.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const rows=statements.map(s=>s.run());this.sqlite.exec('COMMIT');return rows;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
const units=[{id:'c',name:'Continent',level:'continent'},{id:'s',name:'Subcontinent',level:'subcontinent',parent_id:'c'},{id:'r',name:'Region',level:'region',parent_id:'s'},{id:'a',name:'Area',level:'area',parent_id:'r'},{id:'p',name:'Province',level:'province',parent_id:'a'},{id:'retired-p',name:'Retired province',level:'province',parent_id:'a'}];
const polygon={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]};

test('hosted catalog keeps active ancestor closure and categories as undated identities without ancient source coverage',async()=>{
 const folder=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-hosted-catalog-'));const file=path.join(folder,'atlas.sqlite');const archive=path.join(folder,'archive.json.gz');fs.writeFileSync(archive,'Immutable geometry evidence');
 const db=openDatabase(file);try{importRecords(db,{units,locations:[{id:'current',name:'Current territory',parent_id:'p',geometry:polygon},{id:'archived',name:'Archived territory',parent_id:'retired-p',geometry:polygon}],attribute_entities:[{id:'owner:former',kind:'owner',name:'Former owner',source:'Original identity registry'}]});db.prepare("UPDATE locations SET active=0 WHERE id='archived'").run();}finally{db.close();}
 const hosted=new D1();try{
  const output=path.join(folder,'output');const manifest=prepareHostedCatalog({databasePath:file,output,archivePath:archive});const rows=[];
  for(const batch of manifest.batches){const payload=JSON.parse(fs.readFileSync(path.join(output,batch.path)));rows.push(payload);await importBatch(hosted,payload);}
  const entity=(id)=>hosted.sqlite.prepare('SELECT * FROM atlas_entities WHERE id=?').get(id);
  assert.equal(entity('p').active,1);assert.equal(entity('a').active,1);assert.equal(entity('retired-p').active,0);assert.equal(entity('archived').active,0);assert.equal(JSON.parse(entity('retired-p').metadata).archived,true);
  assert.equal(manifest.counts.active_units,5);assert.equal(manifest.counts.archived_units,1);
  const category=hosted.sqlite.prepare("SELECT * FROM atlas_categories WHERE id='owner:former'").get();const source=hosted.sqlite.prepare('SELECT * FROM atlas_sources WHERE id=?').get(category.source_id);
  assert.equal(source.status,'reference');assert.equal(source.supported_from,2026);assert.equal(source.supported_to,2027);assert.equal(JSON.parse(source.metadata).identity_only,true);assert.equal(JSON.parse(source.metadata).attribute_coverage_not_asserted,true);
  assert.equal((await entityProfile(hosted,'owner:former',1000)).display_name,null);assert.equal((await entityProfile(hosted,'owner:former',2026)).display_name,'Former owner');
  await assert.rejects(importBatch(hosted,{names:[{id:'fake-ancient','entity_id':'owner:former',name:'Invented ancient name',valid_from:1000,valid_to:1001,source_id:source.id}]}),/supported source interval/);
  assert.equal((await attributesAt(hosted,1000)).records.length,0);assert.equal((await namesAt(hosted,1000)).records.length,0);
 }finally{hosted.sqlite.close();fs.rmSync(folder,{recursive:true,force:true});}
});

test('every generated hosted catalog batch imports through the actual service and generated D1 constraints',async()=>{
 const folder=new URL('../data/hosted-catalog/',import.meta.url);const manifest=JSON.parse(fs.readFileSync(new URL('index.json',folder),'utf8'));const db=new D1();const activeUnitIds=new Set();let batches=0;
 try{
  for(const batch of manifest.batches){const raw=fs.readFileSync(new URL(batch.path,folder));assert.equal(hash(raw),batch.sha256);assert.ok(raw.byteLength<=1024*1024);const payload=JSON.parse(raw);assert.ok(batch.rows<=250);for(const row of payload.entities??[])if(['province','area','region','subcontinent','continent'].includes(row.kind)&&row.active===1)activeUnitIds.add(row.id);const result=await importBatch(db,payload);assert.equal(result.duplicate,false);batches++;}
  assert.equal(db.sqlite.prepare('SELECT count(*) n FROM atlas_entities').get().n,manifest.counts.entities+manifest.counts.categories);
  assert.equal(db.sqlite.prepare('SELECT count(*) n FROM atlas_sources').get().n,manifest.counts.sources);
  assert.equal(db.sqlite.prepare('SELECT count(*) n FROM atlas_categories').get().n,manifest.counts.categories);
  assert.equal(db.sqlite.prepare("SELECT count(*) n FROM atlas_entities WHERE kind='location' AND active=1").get().n,49614);
  // The deployed identity registry is immutable. Current memberships are
  // validated independently in geographic-release-preparation.mjs.
  const retained=JSON.parse(gunzipSync(fs.readFileSync(new URL('../data/geographic-decision-migration.json.gz',import.meta.url))));
  const expected=new Set(retained.before_units.map(row=>row.id));assert.deepEqual(activeUnitIds,expected);
  assert.equal(db.sqlite.prepare('SELECT count(*) n FROM atlas_attribute_records').get().n,0);assert.equal(db.sqlite.prepare('SELECT count(*) n FROM atlas_names').get().n,0);assert.equal(db.sqlite.prepare('SELECT count(*) n FROM atlas_relationships').get().n,0);
  assert.equal((await attributesAt(db,-3000)).records.length,0);assert.equal((await namesAt(db,-3000)).records.length,0);
  const first=JSON.parse(fs.readFileSync(new URL(manifest.batches[0].path,folder)));assert.equal((await importBatch(db,first)).duplicate,true);
  console.log(JSON.stringify({catalog_batches_imported:batches,entities:manifest.counts.entities,categories:manifest.counts.categories,sources:manifest.counts.sources,active_units:activeUnitIds.size,archived_units:manifest.counts.archived_units}));
 }finally{db.sqlite.close();}
});

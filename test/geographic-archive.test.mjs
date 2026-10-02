import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {openDatabase,importRecords} from '../database.mjs';
import {archiveLocationReference,restoreGeographicRepairArchive} from '../geographic-archive.mjs';

const units=['continent','subcontinent','region','area','province'].map((level,i,all)=>({id:level,name:level,level,parent_id:i?all[i-1]:null}));
const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]};
test('a reference correction retains exact claim bytes, original coordinates and the complete original chain',()=>{
 const db=openDatabase(':memory:');try{
  importRecords(db,{units,locations:[{id:'original',name:'Original reference',parent_id:'province',geometry,metadata:{source_name:'Test source'}}],states:[{location_id:'original',valid_from:1000,valid_to:1100,population:42,source:'Test source'}]});
  const before=db.prepare("SELECT * FROM locations WHERE id='original'").get(),claim=db.prepare('SELECT * FROM states').get(),id=archiveLocationReference(db,before);
  db.prepare("UPDATE locations SET name='Corrected reference',geometry=? WHERE id='original'").run(JSON.stringify({type:'Polygon',coordinates:[[[0,0],[2,0],[2,1],[0,0]]]}));
  const archived=JSON.parse(db.prepare('SELECT snapshot FROM reference_location_archives WHERE id=?').get(id).snapshot);
  assert.deepEqual(archived.location,{...before});assert.deepEqual(archived.claims.states,[{...claim}]);assert.deepEqual(db.prepare('SELECT * FROM states').get(),claim);
  assert.deepEqual(archived.parent_chain.map(u=>u.id),['province','area','region','subcontinent','continent']);assert.equal(archived.history_transfer,false);assert.equal(archived.historical_effective_year,null);
  assert.equal(archiveLocationReference(db,before),id);assert.equal(db.prepare('SELECT count(*) n FROM reference_location_archives').get().n,1);
  assert.throws(()=>db.prepare("UPDATE reference_location_archives SET source='Replacement' WHERE id=?").run(id),/immutable/);
  assert.throws(()=>db.prepare('DELETE FROM reference_location_archives WHERE id=?').run(id),/immutable/);
 }finally{db.close();}
});
test('all receipted predecessor identities restore without overwriting active geography or transferring evidence',()=>{
 const db=openDatabase(':memory:');try{
  const folder=new URL('../data/geographic-repair-evidence/',import.meta.url),archive=JSON.parse(gunzipSync(fs.readFileSync(new URL('archive.json.gz',folder))));
  const first=restoreGeographicRepairArchive(db,folder);assert.equal(first.locations,52);assert.equal(first.snapshots,52);
  for(const entry of archive.locations){const row=db.prepare('SELECT * FROM locations WHERE id=?').get(entry.id);assert.equal(row.active,0);assert.deepEqual(JSON.parse(row.geometry),entry.feature.geometry);assert.equal(db.prepare('SELECT count(*) n FROM reference_location_archives WHERE location_id=?').get(entry.id).n,1);}
  assert.equal(db.prepare('SELECT count(*) n FROM states').get().n,0);assert.equal(db.prepare('SELECT count(*) n FROM attribute_records').get().n,0);
  const id=archive.locations[0].id;db.prepare("UPDATE locations SET name='Current active label',active=1 WHERE id=?").run(id);const current=db.prepare('SELECT * FROM locations WHERE id=?').get(id);
  assert.equal(restoreGeographicRepairArchive(db,folder).locations,0);assert.deepEqual(db.prepare('SELECT * FROM locations WHERE id=?').get(id),current);assert.equal(db.prepare('SELECT count(*) n FROM reference_location_archives').get().n,52);
 }finally{db.close();}
});

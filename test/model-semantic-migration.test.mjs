import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {openDatabase,seedDatabase,importRecords,geography,snapshot} from '../database.mjs';

test('semantic replacements preserve source history and custom locations without transferring their values',()=>{
 const legacy=openDatabase(':memory:');
 try{
  seedDatabase(legacy);
  const london=legacy.prepare("SELECT parent_id FROM locations WHERE id='atlas:city:GBR-Greater London'").get();
  const geometry={type:'Polygon',coordinates:[[[0,51],[.01,51],[.01,51.01],[0,51]]]};
  legacy.prepare('UPDATE locations SET name=?,parent_id=?,geometry=?,active=1 WHERE id=?').run('City of London original',london.parent_id,JSON.stringify(geometry),'GBR-4809');
  importRecords(legacy,{locations:[{id:'custom:preserved',name:'Imported fixture',parent_id:london.parent_id,geometry}],states:[{location_id:'GBR-4809',valid_from:1900,valid_to:1901,population:1234,source:'Source-footprint regression fixture'}]});
  seedDatabase(legacy);
  assert.equal(legacy.prepare("SELECT active FROM locations WHERE id='GBR-4809'").get().active,0);
  assert.equal(legacy.prepare("SELECT active FROM locations WHERE id='custom:preserved'").get().active,1);
  assert.deepEqual(JSON.parse(legacy.prepare("SELECT geometry FROM locations WHERE id='GBR-4809'").get().geometry),geometry);
  assert.equal(legacy.prepare("SELECT population FROM states WHERE location_id='GBR-4809' AND valid_from=1900").get().population,1234);
  assert.equal(legacy.prepare("SELECT count(*) n FROM states WHERE location_id='atlas:city:GBR-Greater London' AND valid_from=1900").get().n,0);
  seedDatabase(legacy);
  assert.equal(legacy.prepare("SELECT count(*) n FROM states WHERE location_id='GBR-4809' AND valid_from=1900").get().n,1);
 }finally{legacy.close();}
});

import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {openDatabase,seedDatabase,importRecords,geography,snapshot} from '../database.mjs';

test('topology migration retires duplicate coverage while preserving its imported history',()=>{
  const legacy=openDatabase(':memory:');
  try {
    seedDatabase(legacy);
    const removed=JSON.parse(fs.readFileSync('data/topology-report.json','utf8')).retired.find(r=>r.name==='Xianggang');
    assert.ok(removed);
    const parent=legacy.prepare("SELECT parent_id FROM locations WHERE id='atlas:territory:HKG' LIMIT 1").get().parent_id;
    const geometry={type:'Polygon',coordinates:[[[114,22],[115,22],[115,23],[114,22]]]};
    // Restore an archived source as active to reproduce the legacy duplicate.
    legacy.prepare('UPDATE locations SET name=?,parent_id=?,geometry=?,active=1 WHERE id=?').run('Xianggang',parent,JSON.stringify(geometry),removed.id);
    importRecords(legacy,{states:[{location_id:removed.id,valid_from:1900,valid_to:1901,source:'Preserve archived history fixture',owner:'Fixture'}]});
    seedDatabase(legacy);
    assert.equal(legacy.prepare('SELECT active FROM locations WHERE id=?').get(removed.id).active,0);
    assert.equal(legacy.prepare('SELECT count(*) n FROM states WHERE location_id=?').get(removed.id).n,1);
    assert.deepEqual(JSON.parse(legacy.prepare('SELECT geometry FROM locations WHERE id=?').get(removed.id).geometry),geometry);
    assert.ok(!geography(legacy).features.some(f=>f.id===removed.id));
    assert.ok(!snapshot(legacy,1900).states.some(s=>s.location_id===removed.id));
    seedDatabase(legacy);assert.equal(legacy.prepare('SELECT count(*) n FROM states WHERE location_id=?').get(removed.id).n,1);
  }finally{legacy.close();}
});

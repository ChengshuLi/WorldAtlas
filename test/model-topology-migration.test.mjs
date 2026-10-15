import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {migrateTopology} from '../topology.mjs';
import {geometry,location,migrationDatabase,migrationRead} from './fixtures/model-migration.mjs';

test('topology migration retires duplicate coverage while preserving its imported history',()=>{
  const report=JSON.parse(fs.readFileSync('data/topology-report.json'));
  const removed=report.retired.find(r=>r.name==='Xianggang');assert.ok(removed);
  const current=location('atlas:territory:HKG',{topology_version:report.version});
  const legacy=migrationDatabase([current,location(removed.id)],[{location_id:removed.id,valid_from:1900,valid_to:1901,source:'Preserve archived history fixture',owner:'Fixture'}]);
  try {
    const states=legacy.prepare('SELECT * FROM states').all();
    const read=migrationRead([current],{'topology-report.json':{version:report.version,retired:[removed]}});
    migrateTopology(legacy,read);
    assert.equal(legacy.prepare('SELECT active FROM locations WHERE id=?').get(removed.id).active,0);
    assert.equal(legacy.prepare('SELECT active FROM locations WHERE id=?').get(current.id).active,1);
    assert.deepEqual(legacy.prepare('SELECT * FROM states').all(),states);
    assert.deepEqual(JSON.parse(legacy.prepare('SELECT geometry FROM locations WHERE id=?').get(removed.id).geometry),geometry);
    const locations=legacy.prepare('SELECT * FROM locations ORDER BY id').all();
    migrateTopology(legacy,read);
    assert.deepEqual(legacy.prepare('SELECT * FROM states').all(),states);
    assert.deepEqual(legacy.prepare('SELECT * FROM locations ORDER BY id').all(),locations);
  } finally {legacy.close();}
});

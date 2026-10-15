import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {migrateReference} from '../reference.mjs';
import {geometry,location,migrationDatabase,migrationRead} from './fixtures/model-migration.mjs';

test('semantic replacements preserve source history and custom locations without transferring their values',()=>{
  const target='atlas:city:GBR-Greater London',old='GBR-4809',current=location(target);
  const retired=JSON.parse(fs.readFileSync('data/semantic-report.json')).retired.find(r=>r.id===old);
  assert.ok(retired,'bundled semantic report retains the original source identity');
  const legacy=migrationDatabase([current,location(old,{source_name:'Natural Earth'}),location('custom:preserved')],[{location_id:old,valid_from:1900,valid_to:1901,population:1234,source:'Source-footprint regression fixture'}]);
  try {
    const states=legacy.prepare('SELECT * FROM states').all();
    const read=migrationRead([current],{'semantic-report.json':{retired:[retired]}});
    migrateReference(legacy,read);
    assert.equal(legacy.prepare('SELECT active FROM locations WHERE id=?').get(old).active,0);
    assert.equal(legacy.prepare("SELECT active FROM locations WHERE id='custom:preserved'").get().active,1);
    assert.deepEqual(JSON.parse(legacy.prepare('SELECT geometry FROM locations WHERE id=?').get(old).geometry),geometry);
    assert.deepEqual(legacy.prepare('SELECT * FROM states').all(),states);
    assert.equal(legacy.prepare('SELECT count(*) n FROM states WHERE location_id=?').get(target).n,0);
    const locations=legacy.prepare('SELECT * FROM locations ORDER BY id').all();
    migrateReference(legacy,read);
    assert.deepEqual(legacy.prepare('SELECT * FROM locations ORDER BY id').all(),locations);
    assert.deepEqual(legacy.prepare('SELECT * FROM states').all(),states);
  } finally {legacy.close();}
});

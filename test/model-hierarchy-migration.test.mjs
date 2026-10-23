import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {migrateHierarchy,validateHierarchy} from '../hierarchy.mjs';
import {location,migrationDatabase,migrationRead} from './fixtures/model-migration.mjs';

test('legacy hierarchy migration preserves historical records and repairs skipped parents',()=>{
  const id='atlas:city:GBR-Greater London',current=location(id,{hierarchy_version:3});
  const legacy=migrationDatabase([current],[{location_id:id,valid_from:1800,valid_to:1801,owner:'Preserved fixture',source:'Migration regression fixture'}]);
  try {
    const states=legacy.prepare('SELECT * FROM states').all();
    legacy.exec('DROP TRIGGER location_parent_update');
    legacy.prepare("UPDATE locations SET parent_id='region',metadata=json_remove(metadata,'$.hierarchy_version') WHERE id=?").run(id);
    legacy.exec(fs.readFileSync('data/schema.sql','utf8'));
    // Calling the migration directly prevents migrateReference from repairing it first.
    const read=migrationRead([current]);migrateHierarchy(legacy,read);
    validateHierarchy(legacy.prepare('SELECT * FROM units').all(),legacy.prepare('SELECT * FROM locations').all());
    assert.deepEqual(legacy.prepare('SELECT * FROM states').all(),states);
    assert.equal(legacy.prepare('SELECT parent_id FROM locations WHERE id=?').get(id).parent_id,'province');
    assert.equal(JSON.parse(legacy.prepare('SELECT metadata FROM locations WHERE id=?').get(id).metadata).hierarchy_version,3);
    migrateHierarchy(legacy,read);
    assert.deepEqual(legacy.prepare('SELECT * FROM states').all(),states);
  } finally {legacy.close();}
});

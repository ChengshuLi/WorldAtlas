import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {openDatabase,seedDatabase,importRecords,geography,snapshot} from '../database.mjs';
import {validateHierarchy} from '../hierarchy.mjs';

test('legacy hierarchy migration preserves historical records and repairs skipped parents',()=>{
  const legacy=openDatabase(':memory:');
  try {
    seedDatabase(legacy);
    importRecords(legacy,{states:[{location_id:'atlas:city:GBR-Greater London',valid_from:1800,valid_to:1801,owner:'Preserved fixture',source:'Migration regression fixture'}]});
    const count=legacy.prepare('SELECT count(*) n FROM states').get().n;
    const region=legacy.prepare("SELECT id FROM units WHERE level='region' AND name='Britain'").get().id;
    legacy.exec('DROP TRIGGER location_parent_update');
    legacy.prepare("UPDATE locations SET parent_id=?,metadata=json_remove(metadata,'$.hierarchy_version') WHERE id='atlas:city:GBR-Greater London'").run(region);
    legacy.exec(fs.readFileSync('data/schema.sql','utf8'));
    seedDatabase(legacy);
    const data=geography(legacy);validateHierarchy(data.units,data.features.map(f=>f.properties));
    assert.equal(legacy.prepare('SELECT count(*) n FROM states').get().n,count);
    assert.equal(snapshot(legacy,1800).states[0].owner,'Preserved fixture');
    assert.equal(legacy.prepare("SELECT level FROM units WHERE id=(SELECT parent_id FROM locations WHERE id='atlas:city:GBR-Greater London')").get().level,'province');
  } finally {legacy.close();}
});

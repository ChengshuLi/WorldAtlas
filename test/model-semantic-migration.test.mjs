import {readOwnerLabels} from '../src/owner-labels.js';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {geography} from '../database.mjs';
import {resolveAttributes} from '../src/attributes.js';
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


test('the nine retained Somaliland decisions replace only stale reference aliases during ordinary migration',()=>{
  const ids=['1722628585645','17415415044999','34990175799989','41100750476456','49158080079573','58560427797094','5876262576033','65673290719307','82555432245075'].map(suffix=>'gb:SOM:ADM2:84685775B'+suffix);
  const source=JSON.parse(fs.readFileSync('data/geography/part-22.json')).features.filter(f=>ids.includes(f.properties.id));
  assert.equal(source.length,9);assert.deepEqual(source.map(f=>f.properties.id).sort(),[...ids].sort());
  for(const {properties:p} of source){
    assert.equal(p.reference_owner,'Somaliland');assert.equal(p.metadata.reference_polity,p.reference_owner);
    assert.equal(p.metadata.reference_owner_id,'owner:Q34754');assert.equal(p.metadata.reference_owner_evidence.winner.owner_id,p.metadata.reference_owner_id);
    assert.equal(p.metadata.reference_owner_evidence.winner.name,p.reference_owner);assert.ok(p.metadata.reference_owner_evidence.winner.share>.5);
    assert.equal(p.metadata.reference_polity_status,'reference');assert.equal(p.metadata.semantic_review.status,'open');
    assert.equal(p.metadata.footprint_repair.history_transfer,false);
  }
  // The synthetic adjacent-tier chain isolates metadata migration from geography preparation.
  const current=source.map(({properties:p,geometry})=>({...p,parent_id:'province',geometry}));
  const original=current.map(row=>({...row,metadata:{...row.metadata,reference_polity:'Somalia'}}));
  const unrelated={...location('custom:untouched',{reference_polity:'Other polity',reference_owner_id:'owner:uncaptured'}),reference_owner:'Other territory'};
  const db=migrationDatabase([...original,unrelated],[{location_id:ids[0],valid_from:1900,valid_to:1901,owner:'Retained historical claim',source:'Migration regression fixture'}]);
  try{
    const before=db.prepare('SELECT * FROM locations ORDER BY id').all(),states=db.prepare('SELECT * FROM states').all();
    const read=migrationRead([...current,unrelated],{'semantic-report.json':{retired:[]}});
    migrateReference(db,read);
    const after=db.prepare('SELECT * FROM locations ORDER BY id').all();
    for(let index=0;index<before.length;index++){
      const expected=JSON.parse(before[index].metadata),actual=JSON.parse(after[index].metadata);delete actual.reference_revision;
      if(ids.includes(before[index].id))expected.reference_polity='Somaliland';
      assert.deepEqual(actual,expected);assert.deepEqual({...after[index],metadata:null},{...before[index],metadata:null});
    }
    const data=geography(db),features=data.features,ownerLabels=readOwnerLabels(data.ownerLabels),modern=resolveAttributes(features,2026,{ownerLabels}),past=resolveAttributes(features,1900,{ownerLabels});
    for(const id of ids){assert.equal(modern.get(id).owner,'Somaliland');assert.equal(modern.get(id).category_ids.owner,'owner:Q34754');assert.equal(past.get(id).owner,null);}
    assert.equal(modern.get(unrelated.id).owner,null,'Uncaptured fixture owner has no raw-source label fallback');assert.equal(modern.get(unrelated.id).category_ids.owner,unrelated.metadata.reference_owner_id);assert.deepEqual(db.prepare('SELECT * FROM states').all(),states);
    migrateReference(db,read);assert.deepEqual(db.prepare('SELECT * FROM locations ORDER BY id').all(),after);
  }finally{db.close();}
});

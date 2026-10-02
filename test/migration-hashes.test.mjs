import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';

// Published or frozen migrations are append-only. New migrations may extend
// this registry; correcting old SQL would invalidate retained installations.
const frozen={
 '0000_bizarre_sentry.sql':'a7d4945214a37835bc6cbe8c6c0bfe2073d15fbf76fa1c510e6db072b64ba699',
 '0001_evidence_retirements.sql':'1f29f4af9eb41425dbd932b9d68e1c54406cb99221a02a2a1bc6b6cab2e3846f',
 '0002_geographic_reference_releases.sql':'fc03e50b1c7053d9ffe89534395bcbb644e3192231122eca51a424fd14753c53',
 '0003_unsettled_location_rank.sql':'dc249cb326203bee26446fb010e0f2c05d8bd9bcbb918649199382d517e0fa4d',
 '0004_population_precision_guard.sql':'302660bc2d4d673bab67820d3c54637ca8cd50460ace57e3142fb3c6f40da447',
 'meta/0000_snapshot.json':'e8fd244d13001d742632e0678dfc72210f5226cad757dfd4316128d5c38f777d',
 'meta/0001_snapshot.json':'c87009a65f84744b2716ce5e0499f0167d26fb61cd381df3cc64e7895df4bc3f',
 'meta/0002_snapshot.json':'410a03e184a5169e3d9a34055d5247b610e34e799b48c8f35ea3ac04ee2f68b9',
 'meta/0003_snapshot.json':'a092e2550c751a59ee02ea724448c126eb570790e99ec899cf071f7f7dc26838',
 'meta/0004_snapshot.json':'de04bfc01382c7c96844b96acaf38fccc92bd4e63308eceb786cfa87c4c53cae',
};
test('frozen migration SQL and snapshots retain their published identities',()=>{
 for(const [path,expected]of Object.entries(frozen))assert.equal(createHash('sha256').update(fs.readFileSync(new URL(`../drizzle/${path}`,import.meta.url))).digest('hex'),expected,`Frozen migration changed: ${path}; add a new migration instead`);
 const journal=JSON.parse(fs.readFileSync(new URL('../drizzle/meta/_journal.json',import.meta.url)));
 for(const [idx,entry]of journal.entries.slice(0,5).entries()){
  assert.equal(entry.idx,idx);
  assert.ok(frozen[`${entry.tag}.sql`],`Unexpected frozen journal identity ${entry.tag}`);
  if(idx){const snapshot=JSON.parse(fs.readFileSync(new URL(`../drizzle/meta/${String(idx).padStart(4,'0')}_snapshot.json`,import.meta.url))),previous=JSON.parse(fs.readFileSync(new URL(`../drizzle/meta/${String(idx-1).padStart(4,'0')}_snapshot.json`,import.meta.url)));assert.equal(snapshot.prevId,previous.id);}
 }
 assert.ok(journal.entries.length>=5);
});

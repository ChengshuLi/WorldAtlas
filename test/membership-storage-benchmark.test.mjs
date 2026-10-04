import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {gzipSync} from 'node:zlib';
import {PGlite} from '@electric-sql/pglite';
import {candidateDDL,originalDDL,membershipRow,dictionaryEntry,insertCandidate,insertOriginal,measureRelations,digest,immutableDDL,verifyEvidenceDictionary,inspectInputs} from '../scripts/benchmark-membership-storage.mjs';

const source=fs.readFileSync(new URL('../postgres/schema.sql',import.meta.url),'utf8');
const row=(entity_id,evidence='{"original":true}')=>membershipRow('release',{entity_id,parent_id:null,reference_name:'Name',source_id:'source',active:1,evidence});
const keys={releases:new Map([['release',1]]),entities:new Map([['entity',1],['other',2]]),sources:new Map([['source',1]])};
async function target(t,candidate=true) {
  const db=new PGlite();t.after(()=>db.close());await db.exec(candidate?candidateDDL:originalDDL(source));
  if(candidate)await db.exec("INSERT INTO release_keys VALUES(1,'release');INSERT INTO entity_keys VALUES(1,'entity','location'),(2,'other','location');INSERT INTO source_keys VALUES(1,'source')");
  else await db.exec("INSERT INTO atlas_geographic_releases VALUES('release');INSERT INTO atlas_entities VALUES('entity','location'),('other','location');INSERT INTO atlas_sources VALUES('source')");
  return db;
}
test('evidence dictionary retains whitespace, key order and duplicate JSON keys byte exactly',()=>{
  const values=new Map(),raw='{ "x": 1, "x": 2 }';
  assert.equal(dictionaryEntry(values,raw).fresh,true);
  assert.equal(dictionaryEntry(values,raw).fresh,false);
  assert.equal(dictionaryEntry(values,'{"x":2}').fresh,true);
  assert.equal(values.size,2);assert.equal(values.get(digest(raw)).raw,raw);
});
test('digest collision is rejected instead of replacing original evidence',()=>{
  const values=new Map(),hash=()=> 'a'.repeat(64);dictionaryEntry(values,'{}',hash);
  assert.throws(()=>dictionaryEntry(values,'{"changed":true}',hash),/collision/);
  assert.equal(values.values().next().value.raw,'{}');
});
test('prototype reconstructs every external field and counts all dictionary/index overhead',async t=>{
  const original=await target(t,false),candidate=await target(t),evidence=new Map();
  const rows=[row('entity','{ "x":1,"x":2 }'),{...row('other'),parent_id:'entity',active:0}];
  await original.transaction(tx=>insertOriginal(tx,rows));
  await insertCandidate(candidate,rows,keys,evidence);
  const select='SELECT * FROM atlas_geographic_memberships ORDER BY entity_id COLLATE "C"';
  assert.deepEqual((await candidate.query(select)).rows,(await original.query(select)).rows);
  const sizes=await measureRelations(candidate);assert.equal(sizes.relations.length,5);
  assert.equal(sizes.total_relation_bytes,sizes.relations.reduce((n,r)=>n+r.total_bytes,0));
  assert.ok(sizes.indexes.length>=11);
});
test('identical evidence deduplicates while separate release/entity memberships remain',async t=>{
  const db=await target(t),evidence=new Map();await insertCandidate(db,[row('entity'),row('other')],keys,evidence);
  assert.equal((await db.query('SELECT count(*)::integer AS n FROM membership_values')).rows[0].n,2);
  assert.equal((await db.query('SELECT count(*)::integer AS n FROM evidence_values')).rows[0].n,1);
});
test('duplicate membership rejects atomically and retains earlier immutable rows',async t=>{
  const db=await target(t),evidence=new Map();await insertCandidate(db,[row('entity')],keys,evidence);
  await assert.rejects(insertCandidate(db,[row('other','{"new":true}'),row('entity')],keys,evidence),/duplicate key/);
  assert.equal((await db.query('SELECT count(*)::integer AS n FROM membership_values')).rows[0].n,1);
  assert.equal((await db.query('SELECT count(*)::integer AS n FROM evidence_values')).rows[0].n,1);
  assert.equal(evidence.size,1);
});
test('missing key or invalid evidence cannot silently repair original data',async t=>{
  const db=await target(t),evidence=new Map();
  await assert.rejects(insertCandidate(db,[row('missing')],keys,evidence),/Missing stable/);
  assert.equal(evidence.size,0);
  assert.equal((await db.query('SELECT count(*)::integer AS n FROM membership_values')).rows[0].n,0);
  assert.throws(()=>membershipRow('r',{entity_id:'a',source_id:'s',evidence:'[]'}),/JSON object/);
  await assert.rejects(db.query('INSERT INTO membership_values VALUES(1,1,999,null,1,1,999)'),/foreign key/);
});
test('candidate immutable history rejects updates/deletes and detects a conflicting digest payload',async t=>{
  const db=await target(t),evidence=new Map();await db.exec(immutableDDL(['evidence_values','membership_values','entity_keys']));
  await insertCandidate(db,[row('entity')],keys,evidence);
  assert.equal(await verifyEvidenceDictionary(db),1);
  for(const sql of ['UPDATE evidence_values SET raw=\'{}\'','DELETE FROM membership_values','UPDATE entity_keys SET id=\'changed\' WHERE key=1'])
    await assert.rejects(db.exec(sql),/append-only/);
  await db.query('INSERT INTO evidence_values VALUES(999,$1,$2)',['b'.repeat(64),'{}']);
  await assert.rejects(verifyEvidenceDictionary(db),/Damaged evidence/);
});
test('name, active and damaged digest constraints reject invalid prototype writes',async t=>{
  const db=await target(t);await db.query('INSERT INTO evidence_values VALUES(1,$1,$2)',['a'.repeat(64),'{}']);
  for(const [name,active] of [[' ',1],['valid',2]])await assert.rejects(db.query('INSERT INTO membership_values VALUES(1,1,null,$1,$2,1,1)',[name,active]),/check constraint/);
  await assert.rejects(db.query("INSERT INTO evidence_values VALUES(2,'damaged','{}')"),/check constraint/);
});
test('original prototype schema fails closed if the expected index inventory changes',()=>{
  assert.throws(()=>originalDDL(source.replace('CREATE INDEX "geographic_membership_page"','CREATE UNIQUE INDEX "geographic_membership_page"')),/inventory changed/);
});

test('transaction handles are rejected so a caller rollback cannot poison the client dictionary',async t=>{
  const db=await target(t),evidence=new Map();
  await assert.rejects(db.transaction(tx=>insertCandidate(tx,[row('entity')],keys,evidence)),/must own the transaction/);
  assert.equal(evidence.size,0);
  await insertCandidate(db,[row('entity')],keys,evidence);
  assert.equal(await verifyEvidenceDictionary(db),1);
});
test('input inspection preserves source pins and rejects corrupted batches or changed predecessor manifests',t=>{
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'membership-input-control-'));t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  const payload=JSON.stringify({release_id:'release',memberships:[{...row('entity'),kind:'location'}]});
  fs.writeFileSync(path.join(directory,'memberships.json'),payload);fs.writeFileSync(path.join(directory,'sources.json'),'{}');
  const manifest={releases:[{id:'release',version:1}],batches:[{path:'memberships.json',sha256:digest(payload)}],sources_batches:['sources.json']};
  fs.writeFileSync(path.join(directory,'index.json'),JSON.stringify(manifest));
  assert.equal(inspectInputs(directory).inventory.membership_rows,1);
  assert.equal(inspectInputs(directory).inventory.source_pins[0].sha256,digest('{}'));
  fs.writeFileSync(path.join(directory,'memberships.json'),payload+' ');assert.throws(()=>inspectInputs(directory),/hash mismatch/);
  fs.writeFileSync(path.join(directory,'memberships.json'),payload);
  const altered={...manifest,releases:[{id:'different',version:1}]};fs.writeFileSync(path.join(directory,'releases-v1-gzip.json.gz'),gzipSync(JSON.stringify(altered)));
  assert.throws(()=>inspectInputs(directory),/Predecessor manifest/);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {DatabaseSync} from 'node:sqlite';
import {prepareGeographicRelease} from '../scripts/prepare-geographic-release.mjs';
import {footprintHash} from '../scripts/check-prepared.mjs';
import {importBatch,entityProfile,attributesAt} from '../hosted/records.js';
import {stageGeographicRelease,finalizeGeographicRelease,geographicRelease,geographicMembershipPage,geographicChangePage,referenceMembership} from '../hosted/geographic-releases.js';

const root=path.resolve(import.meta.dirname,'..'),data=path.join(root,'data');
const tiers=['continent','subcontinent','region','area','province','location'];
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const bytes=file=>fs.readFileSync(file);
const read=file=>JSON.parse(file.endsWith('.gz')?gunzipSync(bytes(file)):bytes(file));
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const binary=(a,b)=>Buffer.compare(Buffer.from(a),Buffer.from(b));
// Deliberately independent from exported service hash helpers.
const hashRows=(rows,key)=>sha(JSON.stringify(rows.toSorted((a,b)=>binary(a[key],b[key])).map(canonical)));
const normalizedMember=(m,kind)=>({entity_id:m.entity_id,kind,parent_id:m.parent_id??null,reference_name:m.reference_name??null,active:m.active,source_id:m.source_id,evidence:typeof m.evidence==='string'?JSON.parse(m.evidence):m.evidence});
const normalizedChange=c=>({id:c.id,old_entity_id:c.old_entity_id??null,new_entity_id:c.new_entity_id??null,change_type:c.change_type,source_id:c.source_id,evidence:typeof c.evidence==='string'?JSON.parse(c.evidence):c.evidence});
class D1 {
 constructor(){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');for(const file of fs.readdirSync(path.join(root,'drizzle')).filter(f=>f.endsWith('.sql')).sort())this.sqlite.exec(bytes(path.join(root,'drizzle',file)).toString());}
 prepare(sql){const sqlite=this.sqlite;let args=[];return {bind(...values){args=values;return this;},async all(){return {results:sqlite.prepare(sql).all(...args)};},async first(){return sqlite.prepare(sql).get(...args)??null;},run(){return {meta:{changes:Number(sqlite.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const result=statements.map(s=>s.run());this.sqlite.exec('COMMIT');return result;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
const tableHash=(db,table,where='1',args=[])=>{const h=createHash('sha256');for(const row of db.sqlite.prepare(`SELECT * FROM ${table} WHERE ${where} ORDER BY id`).iterate(...args))h.update(JSON.stringify(canonical(row))+'\n');return h.digest('hex');};
const assetSnapshot=(folder,index)=>new Map(['index.json',...index.batches.map(b=>b.path)].map(p=>[p,sha(bytes(path.join(folder,p)))]));
const assertSnapshot=(folder,snapshot)=>{for(const [p,hash] of snapshot)assert.equal(sha(bytes(path.join(folder,p))),hash,`Immutable asset changed: ${p}`);};

// Exhaustive dataset gate: this test intentionally exercises the real preparation,
// staging, publication and profile code rather than a miniature substitute schema.
test('both complete geographic reference releases publish against real D1 constraints without rewriting identities or historical evidence',async t=>{
 const folder=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-geographic-release-'));
 const catalogFolder=path.join(data,'hosted-catalog'),catalog=read(path.join(catalogFolder,'index.json'));
 const archiveFile=path.join(data,'geographic-migration-archive.json.gz'),archiveHash=sha(bytes(archiveFile));
 const catalogSnapshot=assetSnapshot(catalogFolder,catalog),preparedFolder=path.join(data,'geographic-releases');
 const preparedIndex=read(path.join(preparedFolder,'index.json')),preparedSnapshot=assetSnapshot(preparedFolder,preparedIndex);
 const migration=read(path.join(data,'geographic-decision-migration.json.gz'));
 const original=new Map(),db=new D1();
 try {
  let generated;
  await t.test('preparation is reproducible and preserves every immutable catalog/archive asset',async()=>{
   generated=await prepareGeographicRelease({data,output:folder});
   assert.deepEqual(generated,preparedIndex);
   for(const batch of generated.batches){const raw=bytes(path.join(folder,batch.path));assert.equal(sha(raw),batch.sha256,batch.path);assert.ok(raw.byteLength<=1048576,batch.path);assert.equal(sha(bytes(path.join(preparedFolder,batch.path))),batch.sha256);const payload=JSON.parse(raw);assert.ok((payload.memberships?.length??0)+(payload.changes?.length??0)+(payload.entities?.length??0)+(payload.sources?.length??0)+Number(Boolean(payload.release))<=250);}
   assert.equal(generated.original_catalog_sha256,catalogSnapshot.get('index.json'));
   assert.equal(archiveHash,catalog.archive_sha256);assertSnapshot(catalogFolder,catalogSnapshot);assertSnapshot(preparedFolder,preparedSnapshot);
  });
  await t.test('all original catalog batches import through the actual record service and all migrations',async()=>{
   for(const batch of catalog.batches){const raw=bytes(path.join(catalogFolder,batch.path));assert.equal(sha(raw),batch.sha256);const payload=JSON.parse(raw);for(const e of payload.entities??[])if(tiers.includes(e.kind)){assert.ok(!original.has(e.id));original.set(e.id,e);}assert.equal((await importBatch(db,payload)).duplicate,false);}
   assert.equal(db.sqlite.prepare('PRAGMA foreign_keys').get().foreign_keys,1);
   assert.equal(db.sqlite.prepare('SELECT count(*) n FROM atlas_entities').get().n,catalog.counts.entities+catalog.counts.categories);
   for(const u of migration.before_units){const e=original.get(u.id);assert.ok(e,`Original group missing ${u.id}`);assert.equal(e.name,u.name);assert.equal(e.parent_id,u.parent_id);}
   assert.equal([...original.values()].filter(e=>e.active&&e.kind!=='location').length,migration.before_units.length);
  });
  const originalRegistryHash=tableHash(db,'atlas_entities'),originalSourceHash=tableHash(db,'atlas_sources');
  const kindMap=new Map([...original.values()].map(e=>[e.id,e.kind]));
  const sourcePayload=read(path.join(folder,'sources.json'));
  const manifests=new Map(generated.releases.map(r=>[r.id,r])),memberships=new Map(generated.releases.map(r=>[r.id,new Map()])),changes=new Map(generated.releases.map(r=>[r.id,[]]));
  const newIds=[];
  // A dated test claim proves that real existing evidence survives both releases;
  // unchanged bytes of the source archive separately preserve all actual legacy claims.
  const fixtureId=[...original.values()].find(e=>e.active&&e.kind==='location').id;
  const historicalSource={id:'test:geographic-release:historical-source',name:'Test-only dated evidence',url:'https://example.org/test-fixture',license:'CC0',vintage:'Test fixture',supported_from:1000,supported_to:2027,status:'historical'};
  await importBatch(db,{sources:[historicalSource],names:[{id:'test:geographic-release:ancient-name',entity_id:fixtureId,name:'Dated historical name',valid_from:1000,valid_to:1100,source_id:historicalSource.id},{id:'test:geographic-release:modern-name',entity_id:fixtureId,name:'Dated modern name',valid_from:2026,valid_to:2027,source_id:historicalSource.id}],records:[{id:'test:geographic-release:population',location_id:fixtureId,attribute:'population',value:42,valid_from:1000,valid_to:1100,source_id:historicalSource.id}]});
  const historyHash=tableHash(db,'atlas_attribute_records'),namesHash=tableHash(db,'atlas_names');
  await t.test('all bounded release batches stage through the real service and remain unpublished',async()=>{
   for(const batch of generated.batches){const payload=read(path.join(folder,batch.path));if(batch.route==='/api/records/import'){for(const e of payload.entities??[]){assert.ok(!original.has(e.id));assert.notEqual(e.kind,'location');kindMap.set(e.id,e.kind);newIds.push(e.id);}assert.equal((await importBatch(db,payload)).duplicate,false);}else{assert.equal(batch.route,'/api/geography/stage');assert.equal((await stageGeographicRelease(db,payload)).duplicate,false);for(const m of payload.memberships??[]){const rows=memberships.get(payload.release_id);assert.ok(!rows.has(m.entity_id));rows.set(m.entity_id,m);}changes.get(payload.release_id)?.push(...(payload.changes??[]));}}
   assert.equal(newIds.length,generated.new_entities);assert.equal(await geographicRelease(db),null);assert.equal(await referenceMembership(db,fixtureId),null);
   assert.equal(tableHash(db,'atlas_entities',`id NOT IN (${newIds.map(()=>'?').join(',')})`,newIds),originalRegistryHash,'Every original registry column must remain unchanged');
  });
  // Compare every original row directly, including inactive entities and metadata.
  await t.test('original registry, sources, real archived claims and fixture evidence remain unchanged',()=>{
   for(const batch of catalog.batches){const payload=read(path.join(catalogFolder,batch.path));for(const e of payload.entities??[]){const actual=db.sqlite.prepare('SELECT * FROM atlas_entities WHERE id=?').get(e.id);for(const [key,value] of Object.entries(e))assert.deepEqual(key==='metadata'?JSON.parse(actual[key]):actual[key],value,`${e.id}.${key}`);}for(const s of payload.sources??[]){const actual=db.sqlite.prepare('SELECT * FROM atlas_sources WHERE id=?').get(s.id);for(const [key,value] of Object.entries(s))assert.deepEqual(key==='metadata'?JSON.parse(actual[key]):actual[key],value,`${s.id}.${key}`);}}
   assert.equal(tableHash(db,'atlas_attribute_records'),historyHash);assert.equal(tableHash(db,'atlas_names'),namesHash);assert.equal(sha(bytes(archiveFile)),archiveHash);assertSnapshot(catalogFolder,catalogSnapshot);
   assert.equal(tableHash(db,'atlas_sources','id NOT IN (?,?,?)',[historicalSource.id,...sourcePayload.sources.map(s=>s.id)]),originalSourceHash);
  });
  const baseline=generated.releases[0],reviewed=generated.releases[1],baselineRows=memberships.get(baseline.id),reviewedRows=memberships.get(reviewed.id);
  const current=new Map(read(path.join(data,'hierarchy.json')).map(u=>[u.id,{name:u.name,parent_id:u.parent_id,kind:u.level}]));
  const features=read(path.join(data,'world-index.json')).parts.flatMap(p=>read(path.join(data,p)).features);
  const pinnedOwnership=read(path.join(data,'ownership-history/index.json'));
  assert.equal(footprintHash(features),pinnedOwnership.footprints_sha256,'A names/membership release must preserve the already prepared footprint version');
  for(const f of features)current.set(f.id,{name:f.properties.name,parent_id:f.properties.parent_id,kind:'location'});
  await t.test('every baseline/current/archive membership and source proof matches the intended inventories',()=>{
   assert.equal(baselineRows.size,original.size);assert.equal(reviewedRows.size,original.size+newIds.length);assert.equal(reviewedRows.size,generated.total_memberships);
   for(const [id,e] of original){const old=baselineRows.get(id);assert.deepEqual([old.reference_name,old.parent_id,old.active],[e.name,e.parent_id,e.active]);assert.equal(old.evidence.original_source_id,e.source_id);assert.equal(old.evidence.original_archive_sha256,archiveHash);}
   for(const [id,m] of reviewedRows){const now=current.get(id),old=original.get(id);assert.ok(now||old);assert.deepEqual([m.reference_name,m.parent_id,m.active],[now?.name??old.name,now?.parent_id??old.parent_id,Number(Boolean(now))],id);assert.equal(kindMap.get(id),now?.kind??old.kind);assert.equal(m.evidence.history_transfer,'none');}
   for(const r of generated.releases){const ms=[...memberships.get(r.id).values()];assert.equal(hashRows(ms.map(m=>normalizedMember(m,kindMap.get(m.entity_id))),'entity_id'),r.membership_sha256);const ids=ms.filter(m=>m.active&&kindMap.get(m.entity_id)==='location').map(m=>m.entity_id).sort(binary);assert.equal(sha(JSON.stringify(ids)),r.location_ids_sha256);assert.deepEqual(Object.fromEntries([...tiers].reverse().map(k=>[k,ms.filter(m=>m.active&&kindMap.get(m.entity_id)===k).length])),r.expected_counts);assert.equal(r.footprints_sha256,footprintHash(features));for(const [name,digest] of Object.entries(r.metadata.decision_sha256))assert.equal(sha(bytes(path.join(data,'geographic-decisions',name))),digest);assert.equal(r.metadata.migration_sha256,sha(bytes(path.join(data,'geographic-decision-migration.json.gz'))));assert.equal(r.metadata.historical_membership_not_asserted,true);for(const m of ms.filter(m=>m.active)){const tier=tiers.indexOf(kindMap.get(m.entity_id));if(tier===0)assert.equal(m.parent_id,null);else{const parent=memberships.get(r.id).get(m.parent_id);assert.equal(parent?.active,1,m.entity_id);assert.equal(kindMap.get(parent.entity_id),tiers[tier-1],m.entity_id);}}}
   assert.equal(baseline.hierarchy_sha256,sha(JSON.stringify(migration.before_units)));assert.equal(reviewed.hierarchy_sha256,sha(bytes(path.join(data,'hierarchy.json'))));
   assert.equal(baseline.location_ids_sha256,reviewed.location_ids_sha256);assert.equal(baseline.footprints_sha256,reviewed.footprints_sha256);
   for(const s of sourcePayload.sources){assert.equal(s.status,'reference');assert.deepEqual([s.supported_from,s.supported_to],[2026,2027]);assert.equal(s.metadata.historical_membership_not_asserted,true);}
  });
  await t.test('the entire crosswalk accounts exactly for created, retired, renamed and reparented identities',()=>{
   const delta=changes.get(reviewed.id),seen=new Set(),expected=new Set();assert.equal(delta.length,generated.changes);assert.equal(changes.get(baseline.id).length,0);
   for(const [id,m] of reviewedRows){const old=original.get(id);if(!old)expected.add(`create:${id}`);else if(old.active&&!m.active)expected.add(`deactivate:${id}`);else if(m.active){if(old.name!==m.reference_name)expected.add(`rename:${id}`);if(old.parent_id!==m.parent_id)expected.add(`reparent:${id}`);}}
   for(const c of delta){const endpoint=c.old_entity_id??c.new_entity_id,key=`${['merge','retire'].includes(c.change_type)?'deactivate':c.change_type}:${endpoint}`;assert.ok(expected.has(key),key);assert.ok(!seen.has(key));seen.add(key);assert.equal(c.evidence.history_transfer,'none');assert.ok(c.evidence.migration_sha256);if(c.new_entity_id!=null)assert.equal(reviewedRows.get(c.new_entity_id)?.active,1);if(['rename','reparent'].includes(c.change_type)){assert.equal(c.old_entity_id,c.new_entity_id);const old=original.get(endpoint),now=reviewedRows.get(endpoint);assert.deepEqual(c.evidence.before,{name:old.name,parent_id:old.parent_id,active:old.active});assert.deepEqual(c.evidence.after,{name:now.reference_name,parent_id:now.parent_id,active:now.active});}if(c.change_type==='merge'){assert.notEqual(c.old_entity_id,c.new_entity_id);assert.equal(kindMap.get(c.old_entity_id),kindMap.get(c.new_entity_id));assert.equal(reviewedRows.get(c.old_entity_id).active,0);}}
   assert.deepEqual(seen,expected);assert.equal(hashRows(delta.map(normalizedChange),'id'),reviewed.changes_sha256);
  });
  await t.test('actual streamed finalization verifies every SQL row and publishes both immutable versions',async()=>{
   for(const r of generated.releases){const published=await finalizeGeographicRelease(db,r.id);assert.equal(published.status,'published');assert.deepEqual(published.expected_counts,r.expected_counts);assert.equal((await finalizeGeographicRelease(db,r.id)).duplicate,true);}
   assert.equal((await geographicRelease(db)).id,reviewed.id);assert.equal((await geographicRelease(db,baseline.id)).id,baseline.id);
   await assert.rejects(stageGeographicRelease(db,{release_id:reviewed.id,memberships:[]}),/immutable/);
   assert.throws(()=>db.sqlite.prepare('UPDATE atlas_geographic_memberships SET reference_name=? WHERE release_id=? AND entity_id=?').run('Tamper',reviewed.id,fixtureId),/immutable/);
   assert.throws(()=>db.sqlite.prepare('DELETE FROM atlas_geographic_releases WHERE id=?').run(baseline.id),/retained/);
   assert.equal(db.sqlite.prepare('PRAGMA foreign_key_check').all().length,0);
  });
  await t.test('profile overlays and complete indexed pages preserve dated-name priority and older-release access',async()=>{
   for(const c of changes.get(reviewed.id).filter(c=>['rename','reparent'].includes(c.change_type))){const id=c.old_entity_id,profile=await entityProfile(db,id,2026),old=original.get(id),now=reviewedRows.get(id);assert.equal(profile.name,now.reference_name);assert.equal(profile.parent_id,now.parent_id);assert.equal(profile.original_registry.name,old.name);assert.equal(profile.original_registry.parent_id,old.parent_id);assert.equal((await entityProfile(db,id,2026,{releaseId:baseline.id})).name,old.name);assert.equal((await entityProfile(db,id,2026,{releaseId:baseline.id})).parent_id,old.parent_id);assert.equal((await entityProfile(db,id,500)).display_name,null);}
   assert.equal((await entityProfile(db,fixtureId,1000)).display_name,'Dated historical name');assert.equal((await entityProfile(db,fixtureId,1100)).display_name,null);assert.equal((await entityProfile(db,fixtureId,2026)).display_name,'Dated modern name');assert.equal((await attributesAt(db,1000,{locationIds:[fixtureId]})).records[0].value,42);
   const archived=[...reviewedRows.values()].find(m=>!m.active&&original.get(m.entity_id)?.active);assert.equal((await entityProfile(db,archived.entity_id,2026)).active,0);assert.equal((await entityProfile(db,archived.entity_id,2026,{releaseId:baseline.id})).active,1);
   for(const r of generated.releases){let cursor='',count=0,previous='';const expected=[...memberships.get(r.id).values()].filter(m=>m.active).sort((a,b)=>binary(a.entity_id,b.entity_id));do{const page=await geographicMembershipPage(db,{releaseId:r.id,cursor,limit:250});for(const m of page.records){assert.ok(binary(m.entity_id,previous)>0);assert.equal(m.entity_id,expected[count++].entity_id);previous=m.entity_id;}cursor=page.next_cursor;}while(cursor);assert.equal(count,expected.length);}
   let cursor='',count=0;do{const page=await geographicChangePage(db,{releaseId:reviewed.id,cursor,limit:127});count+=page.records.length;cursor=page.next_cursor;}while(cursor);assert.equal(count,generated.changes);
   assert.equal(tableHash(db,'atlas_attribute_records'),historyHash);assert.equal(tableHash(db,'atlas_names'),namesHash);assert.equal(sha(bytes(archiveFile)),archiveHash);assertSnapshot(catalogFolder,catalogSnapshot);
  });
 } finally {db.sqlite.close();fs.rmSync(folder,{recursive:true,force:true});}
});

test('a same-ID footprint edit cannot be stamped onto the immutable baseline release',async()=>{
 const folder=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-geographic-footprint-')),fixture=path.join(folder,'data'),output=path.join(folder,'output');
 fs.mkdirSync(fixture);const firstPart=read(path.join(data,'world-index.json')).parts[0],geography=path.dirname(firstPart);
 try {
  for(const item of fs.readdirSync(data))if(item!==geography)fs.symlinkSync(path.join(data,item),path.join(fixture,item));
  fs.mkdirSync(path.join(fixture,geography));
  for(const item of fs.readdirSync(path.join(data,geography)))if(path.join(geography,item)!==firstPart)fs.symlinkSync(path.join(data,geography,item),path.join(fixture,geography,item));
  const originalBytes=bytes(path.join(data,firstPart)),payload=JSON.parse(originalBytes),originalIds=payload.features.map(f=>f.id);
  const translate=coordinates=>{if(typeof coordinates[0]==='number')coordinates[0]+=0.001;else coordinates.forEach(translate);};
  // Translate the entire real polygon, retaining ring closure and topology.
  translate(payload.features[0].geometry.coordinates);
  assert.deepEqual(payload.features.map(f=>f.id),originalIds,'The mutation must preserve every stable ID');
  fs.writeFileSync(path.join(fixture,firstPart),JSON.stringify(payload));
  await assert.rejects(prepareGeographicRelease({data:fixture,output}),/pinned pre-migration location footprints/);
  assert.equal(fs.existsSync(output),false,'No baseline/review manifest or membership can be written after the failed footprint gate');
  assert.deepEqual(bytes(path.join(data,firstPart)),originalBytes,'Actual location data remain immutable');
 } finally {fs.rmSync(folder,{recursive:true,force:true});}
});

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {DatabaseSync} from 'node:sqlite';
import {execFileSync} from 'node:child_process';
import {prepareGeographicRelease,validateGeometryMigrations,validateReviewedIdentities} from '../scripts/prepare-geographic-release.mjs';
import {footprintHash} from '../scripts/check-prepared.mjs';
import {importBatch,entityProfile,attributesAt} from '../hosted/records.js';
import {stageGeographicRelease,finalizeGeographicRelease,geographicRelease,geographicMembershipPage,geographicChangePage,referenceMembership} from '../hosted/geographic-releases.js';

const root=path.resolve(import.meta.dirname,'..'),data=path.join(root,'data');
const geographyData=process.env.ATLAS_REVIEWED_GEOGRAPHY??data;
const migrationFolder=process.env.ATLAS_DRIZZLE_MIGRATIONS??path.join(root,'drizzle');
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
 constructor(){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');for(const file of fs.readdirSync(migrationFolder).filter(f=>f.endsWith('.sql')).sort())this.sqlite.exec(bytes(path.join(migrationFolder,file)).toString());}
 prepare(sql){const sqlite=this.sqlite;let args=[];return {bind(...values){args=values;return this;},async all(){return {results:sqlite.prepare(sql).all(...args)};},async first(){return sqlite.prepare(sql).get(...args)??null;},run(){return {meta:{changes:Number(sqlite.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const result=statements.map(s=>s.run());this.sqlite.exec('COMMIT');return result;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
const tableHash=(db,table,where='1',args=[])=>{const h=createHash('sha256');for(const row of db.sqlite.prepare(`SELECT * FROM ${table} WHERE ${where} ORDER BY id`).iterate(...args))h.update(JSON.stringify(canonical(row))+'\n');return h.digest('hex');};
const assetSnapshot=(folder,index)=>new Map(['index.json',...index.batches.map(b=>b.path)].map(p=>[p,sha(bytes(path.join(folder,p)))]));
const assertSnapshot=(folder,snapshot)=>{for(const [p,hash] of snapshot)assert.equal(sha(bytes(path.join(folder,p))),hash,`Immutable asset changed: ${p}`);};
function reviewedProofOptions(folder){
 const installedFile=path.join(data,'publication-geography-receipt.json');
 if(!fs.existsSync(installedFile)||!read(installedFile).sources?.geometryProofs)return {};
 const bundle=path.join(data,'macro-improvements/combined-restoration'),index=read(path.join(bundle,'installation-proof-index.json.gz'));
 assert.equal(index.history_transfer,false);const archive=path.join(bundle,index.archive.path),raw=bytes(archive);
 assert.equal(sha(raw),index.archive.sha256);assert.equal(raw.length,index.archive.bytes);
 const proof=path.join(folder,'reviewed-proof');fs.mkdirSync(proof);
 // Extract only exhaustive, hash-pinned regular files; reject traversal and links.
 execFileSync('python3',['-c',`
import gzip,hashlib,json,pathlib,sys,tarfile
index=json.loads(gzip.decompress(pathlib.Path(sys.argv[1]).read_bytes()));target=pathlib.Path(sys.argv[3]).resolve()
expected={f['path']:f['sha256'] for f in index['files']};assert len(expected)==len(index['files'])
with tarfile.open(sys.argv[2]) as archive:
 members=archive.getmembers();assert len(members)==len(expected) and {m.name for m in members}==set(expected)
 for member in members:
  name=pathlib.PurePosixPath(member.name);assert member.isfile() and not name.is_absolute() and '..' not in name.parts
  raw=archive.extractfile(member).read();assert hashlib.sha256(raw).hexdigest()==expected[member.name]
  destination=target/member.name;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(raw)
`,path.join(bundle,'installation-proof-index.json.gz'),archive,proof]);
 const receipt=read(path.join(proof,'aggregate-source-receipt.json'));
 assert.equal(sha(bytes(path.join(proof,'aggregate-source-receipt.json'))),read(installedFile).sources.sourceReceipt.sha256);
 assert.equal(receipt.historical_claims_transferred,false);
 const geometryManifests=[path.join(data,'geographic-repair-evidence/index.json'),path.join(proof,'replacement-migration/index.json'),path.join(proof,'creation-migration/index.json')];
 const metadataMigrations=['macro-boundary-migration.json.gz','macro-foundation/migration-repairs.json.gz','macro-foundation/migration-areas.json.gz','macro-foundation/migration-regions.json.gz'].map(p=>path.join(data,p));
 metadataMigrations.push(path.join(proof,'reference-receipt.json'));
 const identityProofSequence=read(path.join(bundle,'identity-proof-sequence.json'));
 assert.deepEqual(identityProofSequence,{version:1,steps:[{type:'geometry',sha256:sha(bytes(geometryManifests[0]))},...metadataMigrations.map(p=>({type:'metadata',sha256:sha(bytes(p))})),...geometryManifests.slice(1).map(p=>({type:'geometry',sha256:sha(bytes(p))}))]});
 // The isolated fixture begins with the original registry, so every subsequent
 // identity is generated/imported here. Live publication additionally reuses
 // previously registered identities through its immutable release manifests.
 return {geometryManifests,metadataMigrations,identityProofSequence,reviewedVersion:4};
}

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
  const proofOptions=reviewedProofOptions(folder);
  let generated;
  await t.test('preparation is reproducible and preserves every immutable catalog/archive asset',async()=>{
   generated=await prepareGeographicRelease({data,geographyData,output:folder,...proofOptions});
   if(geographyData===data&&generated.releases[1].id===preparedIndex.releases[1].id)assert.deepEqual(generated,preparedIndex);
   for(const batch of generated.batches){const raw=bytes(path.join(folder,batch.path));assert.equal(sha(raw),batch.sha256,batch.path);assert.ok(raw.byteLength<=1048576,batch.path);if(geographyData===data&&generated.releases[1].id===preparedIndex.releases[1].id)assert.equal(sha(bytes(path.join(preparedFolder,batch.path))),batch.sha256);const payload=JSON.parse(raw);assert.ok((payload.memberships?.length??0)+(payload.changes?.length??0)+(payload.entities?.length??0)+(payload.sources?.length??0)+Number(Boolean(payload.release))<=250);}
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
  const fixtureId=generated.validated_geometry?.retired_location_ids[0]??[...original.values()].find(e=>e.active&&e.kind==='location').id;
  const historicalSource={id:'test:geographic-release:historical-source',name:'Test-only dated evidence',url:'https://example.org/test-fixture',license:'CC0',vintage:'Test fixture',supported_from:1000,supported_to:2027,status:'historical'};
  await importBatch(db,{sources:[historicalSource],names:[{id:'test:geographic-release:ancient-name',entity_id:fixtureId,name:'Dated historical name',valid_from:1000,valid_to:1100,source_id:historicalSource.id},{id:'test:geographic-release:modern-name',entity_id:fixtureId,name:'Dated modern name',valid_from:2026,valid_to:2027,source_id:historicalSource.id}],records:[{id:'test:geographic-release:population',location_id:fixtureId,attribute:'population',value:42,valid_from:1000,valid_to:1100,source_id:historicalSource.id}]});
  const historyHash=tableHash(db,'atlas_attribute_records'),namesHash=tableHash(db,'atlas_names');
  await t.test('all bounded release batches stage through the real service and remain unpublished',async()=>{
   for(const batch of generated.batches){const payload=read(path.join(folder,batch.path));if(batch.route==='/api/records/import'){for(const e of payload.entities??[]){assert.ok(!original.has(e.id));if(e.kind==='location')assert.ok(generated.validated_geometry.added_location_ids.includes(e.id));kindMap.set(e.id,e.kind);newIds.push(e.id);}assert.equal((await importBatch(db,payload)).duplicate,false);}else{assert.equal(batch.route,'/api/geography/stage');assert.equal((await stageGeographicRelease(db,payload)).duplicate,false);for(const m of payload.memberships??[]){const rows=memberships.get(payload.release_id);assert.ok(!rows.has(m.entity_id));rows.set(m.entity_id,m);}changes.get(payload.release_id)?.push(...(payload.changes??[]));}}
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
  const current=new Map(read(path.join(geographyData,'hierarchy.json')).map(u=>[u.id,{name:u.name,parent_id:u.parent_id,kind:u.level}]));
  const features=read(path.join(geographyData,'world-index.json')).parts.flatMap(p=>read(path.join(geographyData,p)).features);
  const originalFootprints=read(path.join(data,'macro-corrections.json')).footprints_sha256_before;
  assert.equal(baseline.footprints_sha256,originalFootprints,'The original baseline must retain its original geometry version');
  assert.equal(reviewed.footprints_sha256,footprintHash(features),'The reviewed version must describe actual reviewed geometry');
  for(const f of features)current.set(f.id,{name:f.properties.name,parent_id:f.properties.parent_id,kind:'location'});
  await t.test('every baseline/current/archive membership and source proof matches the intended inventories',()=>{
   assert.equal(baselineRows.size,original.size);assert.equal(reviewedRows.size,original.size+newIds.length);assert.equal(reviewedRows.size,generated.total_memberships);
   for(const [id,e] of original){const old=baselineRows.get(id);assert.deepEqual([old.reference_name,old.parent_id,old.active],[e.name,e.parent_id,e.active]);assert.equal(old.evidence.original_source_id,e.source_id);assert.equal(old.evidence.original_archive_sha256,archiveHash);}
   for(const [id,m] of reviewedRows){const now=current.get(id),old=original.get(id);assert.ok(now||old);assert.deepEqual([m.reference_name,m.parent_id,m.active],[now?.name??old.name,now?.parent_id??old.parent_id,Number(Boolean(now))],id);assert.equal(kindMap.get(id),now?.kind??old.kind);assert.equal(m.evidence.history_transfer,'none');}
   for(const r of generated.releases){const ms=[...memberships.get(r.id).values()];assert.equal(hashRows(ms.map(m=>normalizedMember(m,kindMap.get(m.entity_id))),'entity_id'),r.membership_sha256);const ids=ms.filter(m=>m.active&&kindMap.get(m.entity_id)==='location').map(m=>m.entity_id).sort(binary);assert.equal(sha(JSON.stringify(ids)),r.location_ids_sha256);assert.deepEqual(Object.fromEntries([...tiers].reverse().map(k=>[k,ms.filter(m=>m.active&&kindMap.get(m.entity_id)===k).length])),r.expected_counts);assert.equal(r.footprints_sha256,r.version===1?originalFootprints:footprintHash(features));for(const [name,digest] of Object.entries(r.metadata.decision_sha256))assert.equal(sha(bytes(path.join(data,'geographic-decisions',name))),digest);assert.equal(r.metadata.migration_sha256,sha(bytes(path.join(data,'geographic-decision-migration.json.gz'))));assert.equal(r.metadata.historical_membership_not_asserted,true);for(const m of ms.filter(m=>m.active)){const tier=tiers.indexOf(kindMap.get(m.entity_id));if(tier===0)assert.equal(m.parent_id,null);else{const parent=memberships.get(r.id).get(m.parent_id);assert.equal(parent?.active,1,m.entity_id);assert.equal(kindMap.get(parent.entity_id),tiers[tier-1],m.entity_id);}}}
   assert.equal(baseline.hierarchy_sha256,sha(JSON.stringify(migration.before_units)));assert.equal(reviewed.hierarchy_sha256,sha(bytes(path.join(geographyData,'hierarchy.json'))));
   if(generated.validated_geometry){assert.notEqual(baseline.footprints_sha256,reviewed.footprints_sha256);assert.equal(generated.validated_geometry.baseline_footprints_sha256,baseline.footprints_sha256);assert.equal(generated.validated_geometry.current_footprints_sha256,reviewed.footprints_sha256);}else{assert.equal(baseline.location_ids_sha256,reviewed.location_ids_sha256);assert.equal(baseline.footprints_sha256,reviewed.footprints_sha256);}
   for(const s of sourcePayload.sources){assert.equal(s.status,'reference');assert.deepEqual([s.supported_from,s.supported_to],[2026,2027]);assert.equal(s.metadata.historical_membership_not_asserted,true);}
  });
  await t.test('the entire crosswalk accounts exactly for created, retired, renamed and reparented identities',()=>{
   const delta=changes.get(reviewed.id),seen=new Set(),expected=new Set();assert.equal(delta.length,generated.changes);assert.equal(changes.get(baseline.id).length,0);
   for(const [id,m] of reviewedRows){const old=original.get(id);if(!old)expected.add(`create:${id}`);else if(old.active&&!m.active)expected.add(`deactivate:${id}`);else if(m.active){if(old.name!==m.reference_name)expected.add(`rename:${id}`);if(old.parent_id!==m.parent_id)expected.add(`reparent:${id}`);}}
   for(const id of generated.validated_geometry?.changed_location_ids??[])if(reviewedRows.get(id)?.active)expected.add(`retain:${id}`);
   const geometryPairs=new Set(),splitPairs=new Set(),expectedSplits=new Map();
   for(const file of proofOptions.metadataMigrations??[])for(const relationship of read(file).relationships??[])if(relationship.change_type==='split'&&original.has(relationship.old_entity_id)&&reviewedRows.get(relationship.old_entity_id)?.active===0){const pair=JSON.stringify(['split',relationship.old_entity_id,relationship.new_entity_id]);assert.ok(!expectedSplits.has(pair),'Duplicate declared split pair');expectedSplits.set(pair,{relationship,receipt_sha256:sha(bytes(file))});}
   for(const c of delta){const endpoint=c.old_entity_id??c.new_entity_id,key=`${['merge','retire','split'].includes(c.change_type)?'deactivate':c.change_type}:${endpoint}`;assert.ok(expected.has(key),key);if(c.evidence.geometry_migration){const pairKey=JSON.stringify([c.change_type,c.old_entity_id,c.new_entity_id]);assert.ok(!geometryPairs.has(pairKey));geometryPairs.add(pairKey);assert.ok(c.evidence.geometry_migration.receipt_sha256);}else if(c.change_type==='split'){const pair=JSON.stringify([c.change_type,c.old_entity_id,c.new_entity_id]),declared=expectedSplits.get(pair);assert.ok(declared,'Split is not in an exact pinned metadata receipt');assert.ok(!splitPairs.has(pair),'Duplicate split successor');splitPairs.add(pair);assert.equal(c.evidence.metadata_relationship?.receipt_sha256,declared.receipt_sha256);assert.deepEqual(c.evidence.metadata_relationship.relationship,declared.relationship);assert.equal(reviewedRows.get(c.old_entity_id).active,0);assert.equal(kindMap.get(c.old_entity_id),kindMap.get(c.new_entity_id));assert.notEqual(c.old_entity_id,c.new_entity_id);}else assert.ok(!seen.has(key));seen.add(key);assert.equal(c.evidence.history_transfer,'none');assert.ok(c.evidence.migration_sha256);if(c.new_entity_id!=null)assert.equal(reviewedRows.get(c.new_entity_id)?.active,1);if(['rename','reparent'].includes(c.change_type)){assert.equal(c.old_entity_id,c.new_entity_id);const old=original.get(endpoint),now=reviewedRows.get(endpoint);assert.deepEqual(c.evidence.before,{name:old.name,parent_id:old.parent_id,active:old.active});assert.deepEqual(c.evidence.after,{name:now.reference_name,parent_id:now.parent_id,active:now.active});}if(c.change_type==='merge'){assert.notEqual(c.old_entity_id,c.new_entity_id);assert.equal(kindMap.get(c.old_entity_id),kindMap.get(c.new_entity_id));assert.equal(reviewedRows.get(c.old_entity_id).active,0);}}
   assert.deepEqual(seen,expected);assert.deepEqual(splitPairs,new Set(expectedSplits.keys()),'Every declared retired identity split must account for every successor exactly once');assert.equal(hashRows(delta.map(normalizedChange),'id'),reviewed.changes_sha256);
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
   const retiredTarget=changes.get(reviewed.id).find(c=>c.old_entity_id===fixtureId&&['merge','replace','split'].includes(c.change_type))?.new_entity_id;if(retiredTarget)assert.equal((await attributesAt(db,1000,{locationIds:[retiredTarget]})).records.length,0,'Archived evidence must never migrate automatically to a surviving footprint');
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
  await assert.rejects(prepareGeographicRelease({data:fixture,output}),/pinned pre-migration location footprints|unreceipted footprint mutation/);
  assert.equal(fs.existsSync(output),false,'No baseline/review manifest or membership can be written after the failed footprint gate');
  assert.deepEqual(bytes(path.join(data,firstPart)),originalBytes,'Actual location data remain immutable');
 } finally {fs.rmSync(folder,{recursive:true,force:true});}
});

function replacementProofFixture(){
 const folder=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-geographic-proof-'));
 const feature=(id,at)=>({type:'Feature',id,properties:{id,name:id,parent_id:'fixture:province'},geometry:{type:'Polygon',coordinates:[[[at,0],[at+.8,0],[at+.8,.8],[at,.8],[at,0]]]}});
 const before=Array.from({length:111},(_,at)=>feature(`before:${at}`,at));
 const after=before.slice(0,107).map((f,at)=>({...f,id:`after:${at}`,properties:{...f.properties,id:`after:${at}`}}));
 after[0].geometry={type:'MultiPolygon',coordinates:[before[0].geometry.coordinates,...before.slice(107).map(f=>f.geometry.coordinates)]};
 const receipt={geometry_stage_validated:true,historical_claims_transferred:false,before_footprints_sha256:footprintHash(before),after_footprints_sha256:footprintHash(after),changed_ids:[],removed_ids:before.map(f=>f.id),added_ids:after.map(f=>f.id),reused_ids:[],archives:before.map(f=>({id:f.id,feature:f})),new_entities:after.map(f=>({id:f.id,kind:'location',name:f.properties.name,parent_id:f.properties.parent_id})),relationships:[{kind:'source-backed-replacement',proposal_id:'test-only:111-to-107',before_ids:before.map(f=>f.id),after_ids:after.map(f=>f.id),history_transfer:false,identity_pairs:before.map((f,at)=>({before_id:f.id,after_id:after[at<107?at:0].id,evidence:{method:'Exact synthetic polygon equivalence/union; test-only source'}}))}],source_evidence:[{url:'https://example.org/test-only-geographic-fixture',source_sha256:'0'.repeat(64)}]};
 const manifest={before_footprints_sha256:receipt.before_footprints_sha256,after_footprints_sha256:receipt.after_footprints_sha256,history_transfer:false,files:{}};
 const save=()=>{fs.writeFileSync(path.join(folder,'migration-receipt.json'),JSON.stringify(receipt));manifest.files['migration-receipt.json']={archive_path:'migration-receipt.json',sha256:sha(bytes(path.join(folder,'migration-receipt.json')))};fs.writeFileSync(path.join(folder,'index.json'),JSON.stringify(manifest));};save();
 const options=()=>({features:after,baselineIds:before.map(f=>f.id),baselineFootprints:footprintHash(before),manifestFiles:[path.join(folder,'index.json')]});
 return {folder,before,after,receipt,manifest,save,options};
}
test('precise 111-retired/107-new geography replacements preserve every original identity and reject aggregate-only mappings',()=>{
 const f=replacementProofFixture();try{const proof=validateGeometryMigrations(f.options());assert.equal(proof.retiredIds.size,111);assert.equal(proof.addedIds.size,107);assert.equal(proof.pairs.length,111);assert.equal(proof.baselineFeatures.length,111);assert.ok(proof.pairs.every(p=>p.change_type==='replace'&&p.history_transfer==='none'));assert.equal(footprintHash(proof.baselineFeatures),footprintHash(f.before));delete f.receipt.relationships[0].identity_pairs;f.save();assert.throws(()=>validateGeometryMigrations(f.options()),/precise identity_pairs/);}finally{fs.rmSync(f.folder,{recursive:true,force:true});}
});
test('an untouched ID with edited land, wrong archived original, or tampered source archive cannot enter a reference release',()=>{
 const f=replacementProofFixture();try{f.after[1].geometry=structuredClone(f.after[1].geometry);f.after[1].geometry.coordinates[0][1][0]+=.01;assert.throws(()=>validateGeometryMigrations(f.options()),/unreceipted footprint mutation/);f.after[1].geometry=structuredClone(f.before[1].geometry);f.receipt.archives[1].feature=structuredClone(f.before[1]);f.receipt.archives[1].feature.geometry.coordinates[0][1][0]+=.01;f.save();assert.throws(()=>validateGeometryMigrations(f.options()),/reconstruct the pinned/);fs.appendFileSync(path.join(f.folder,'migration-receipt.json'),' ');assert.throws(()=>validateGeometryMigrations(f.options()),/archive hash mismatch/);}finally{fs.rmSync(f.folder,{recursive:true,force:true});}
});
test('unvalidated geometry, historical transfer, or omitted identity dispositions are rejected before any output',()=>{
 const f=replacementProofFixture();try{f.receipt.geometry_stage_validated=false;f.save();assert.throws(()=>validateGeometryMigrations(f.options()),/independent validation/);f.receipt.geometry_stage_validated=true;f.receipt.historical_claims_transferred=true;f.save();assert.throws(()=>validateGeometryMigrations(f.options()),/zero historical transfer/);f.receipt.historical_claims_transferred=false;f.receipt.removed_ids.pop();f.save();assert.throws(()=>validateGeometryMigrations(f.options()),/exact archived original/);}finally{fs.rmSync(f.folder,{recursive:true,force:true});}
});

test('later release preparation reuses registered identities while retaining the exact original baseline manifest',async()=>{
 const folder=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-geographic-next-version-'));try{
  const firstFolder=path.join(folder,'first'),nextFolder=path.join(folder,'next');
  const proofOptions=reviewedProofOptions(folder),nextVersion=(proofOptions.reviewedVersion??2)+1;
  const first=await prepareGeographicRelease({data,geographyData,output:firstFolder,...proofOptions});
  const next=await prepareGeographicRelease({data,geographyData,output:nextFolder,...proofOptions,reviewedVersion:nextVersion,referenceDate:'2027-01-01',registryManifests:[path.join(firstFolder,'index.json')]});
  assert.deepEqual(next.releases[0],first.releases[0],'Original baseline release identity, date, geometry and membership hashes are immutable');assert.equal(next.new_entities,0,'Previously registered identities must not be imported again with a new origin');assert.equal(next.releases[1].version,nextVersion);assert.equal(next.releases[1].reference_date,'2027-01-01');assert.notEqual(next.releases[1].id,first.releases[1].id);assert.equal(next.total_memberships,first.total_memberships);
  assert.ok(next.registered_identity_manifest_sha256);assert.ok(next.batches.every(b=>!b.path.startsWith('entities-')));
 }finally{fs.rmSync(folder,{recursive:true,force:true});}
});

test('replaying a previously registered creation preserves true archived-group and identity-collision guards',()=>{
 const folder=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-creation-replay-'));
 try{
  const before=tiers.slice(0,-1).map((level,i)=>({id:level,name:level,level,parent_id:i?tiers[i-1]:null,metadata:{child_count:1}}));
  const oldLocation={id:'old-land',name:'Old land',kind:'location',parent_id:'province',active:1};
  const group={id:'new-province',name:'New province',level:'province',parent_id:'area',metadata:{child_count:1}};
  const added={id:'new-land',name:'New land',kind:'location',parent_id:group.id};
  const after=before.map(row=>row.id==='area'?{...row,metadata:{child_count:2}}:row).concat(group);
  const snapshot=path.join(folder,'after-hierarchy.json');fs.writeFileSync(snapshot,JSON.stringify(after));
  const original=new Map([...before.map(row=>[row.id,{...row,kind:row.level,active:1}]),[oldLocation.id,oldLocation]]);
  const current=new Map([...after.map(row=>[row.id,{id:row.id,name:row.name,kind:row.level,parent_id:row.parent_id}]),[oldLocation.id,oldLocation],[added.id,added]]);
  const registered={id:group.id,name:group.name,kind:group.level,parent_id:group.parent_id,active:1};
  const proof={manifest_sha256:'0'.repeat(64),files:{'after-hierarchy.json':{file:snapshot}},creationProofs:[{location_id:added.id}],changed:new Set(),removed:new Set(),added:new Set([added.id]),receipt:{new_entities:[added]}};
  const options={original,current,migration:{before_units:before},geometryProof:{proofs:[proof]},metadataProofs:[],registry:new Map([...original,[group.id,registered]])};
  assert.doesNotThrow(()=>validateReviewedIdentities(options),'Exact previously registered source creation remains replayable');
  assert.throws(()=>validateReviewedIdentities({...options,registry:new Map([...original,[group.id,{...registered,name:'Different immutable identity'}]])}),/exact original definition/);
  const archived={...registered,active:0};
  assert.throws(()=>validateReviewedIdentities({...options,original:new Map([...original,[group.id,archived]]),registry:new Map([...original,[group.id,archived]])}),/revives an archived group/);
 }finally{fs.rmSync(folder,{recursive:true,force:true});}
});

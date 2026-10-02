import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import {DatabaseSync} from 'node:sqlite';
import {importBatch,registerMedia} from '../hosted/records.js';
import {stageGeographicRelease,finalizeGeographicRelease,geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '../hosted/geographic-releases.js';
import {storageExportCollections,exportStorageMarker,exportStoragePage} from '../hosted/storage-export.js';
import {exportHostedStorage} from '../scripts/export-hosted-storage.mjs';
import {readVerifiedStorageSnapshot,restorePostgresStorage} from '../scripts/restore-postgres-storage.mjs';
import {packStorageCheckpoint,unpackStorageCheckpoint,checkpointLimits} from '../scripts/storage-checkpoint.mjs';

const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
class D1{
 constructor(){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');for(const file of fs.readdirSync(new URL('../drizzle/',import.meta.url)).filter(file=>file.endsWith('.sql')).sort())this.sqlite.exec(fs.readFileSync(new URL('../drizzle/'+file,import.meta.url),'utf8'));}
 prepare(sql){const sqlite=this.sqlite;let args=[];return {bind(...values){args=values;return this;},async all(){return {results:sqlite.prepare(sql).all(...args)};},async first(){return sqlite.prepare(sql).get(...args)??null;},run(){return {meta:{changes:Number(sqlite.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const result=statements.map(statement=>statement.run());this.sqlite.exec('COMMIT');return result;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
async function fixture(t){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-storage-checkpoint-')),source=path.join(root,'source'),db=new D1();
 t.after(()=>{db.sqlite.close();fs.rmSync(root,{recursive:true,force:true});});
 await importBatch(db,JSON.parse(fs.readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));
 const sourceRecord=(id,status='historical')=>({id,name:'Public fixture '+id,url:'https://example.org/public-fixture',license:'CC0',vintage:'2026',supported_from:status==='reference'?2026:-3000,supported_to:2027,status});
 const tiers=['continent','subcontinent','region','area','province','location'];
 const entities=Array.from({length:6},(_,continent)=>tiers.map((kind,index)=>({id:`${kind}-${continent}`,kind,name:'Public '+kind,parent_id:index?`${tiers[index-1]}-${continent}`:null}))).flat();
 await importBatch(db,{sources:[sourceRecord('history'),sourceRecord('reference','reference'),sourceRecord('example','example'),...Array.from({length:14},(_,index)=>({...sourceRecord('public-'+index),metadata:{public_notes:'public-source-content-'.repeat(500)}}))],entities:[...entities,{id:'archived',kind:'place',name:'Archived identity',active:0},{id:'example-person',kind:'person',name:'Marked example',is_example:1}],categories:[{id:'owner:fixture',kind:'owner',name:'Fixture polity',source_id:'history'}]});
 db.sqlite.prepare("INSERT INTO atlas_attribute_records(id,location_id,attribute,value,valid_from,valid_to,method,status,source_id,metadata) VALUES('original','location-0','population',' \n 42 \t',1000,1100,'direct','sourced','history',?)").run('{ "precision" : "census", "duplicate":1,"duplicate":2 }');
 await importBatch(db,{names:[{id:'name',entity_id:'location-0',name:'Dated fixture name',source_id:'history',valid_from:1000,valid_to:1100}],relationships:[{id:'example-link',source_entity_id:'location-0',target_entity_id:'example-person',relationship_type:'associated_with',source_id:'example',is_example:1}],retirements:[{id:'withdrawal',collection:'records',target_id:'original',source_id:'history',reason:'Preserved fixture evidence'}]});
 const digest='a'.repeat(64);await registerMedia(db,{id:'media',object_key:'media/'+digest,sha256:digest,bytes:42,mime:'audio/wav',name:'Public audio metadata',license:'CC0',attribution:'Public fixture',source_id:'history'});
 await importBatch(db,{media_links:[{id:'media-link',media_id:'media',entity_id:'location-0',role:'audio',source_id:'history'}]});
 const memberships=entities.map(entity=>({entity_id:entity.id,kind:entity.kind,parent_id:entity.parent_id,reference_name:entity.name,active:1,source_id:'reference',evidence:{public_fixture:true}})),changes=[{id:'retain',old_entity_id:'location-0',new_entity_id:'location-0',change_type:'retain',source_id:'reference',evidence:{public_fixture:true}}];
 const release={id:'release',version:1,source_id:'reference',reference_date:'2026-10-01',hierarchy_sha256:'b'.repeat(64),footprints_sha256:'c'.repeat(64),membership_sha256:await geographicMembershipHash(memberships),location_ids_sha256:await geographicLocationIdsHash(memberships),changes_sha256:await geographicChangesHash(changes),expected_counts:Object.fromEntries(tiers.map(kind=>[kind,6]))};
 await stageGeographicRelease(db,{release,memberships,changes});await finalizeGeographicRelease(db,'release');
 const token='private-fixture-auth-never-exported';
 const fetcher=async(input,options)=>{
  assert.equal(options.headers['OAI-Sites-Authorization'],'Bearer '+token);const url=new URL(input);
  if(url.pathname.endsWith('/export-marker'))return Response.json({...await exportStorageMarker(db),read_only:true});
  return Response.json(await exportStoragePage(db,url.pathname.split('/').at(-1),{cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')??200)}));
 };
 await exportHostedStorage({origin:'https://example.org/',output:source,token,fetcher});
 return {root,source,token,packed:path.join(root,'packed'),unpacked:path.join(root,'unpacked')};
}
const readManifest=directory=>JSON.parse(fs.readFileSync(path.join(directory,'checkpoint.json')));
function mutateManifest(directory,mutate){const manifest=readManifest(directory);mutate(manifest);fs.writeFileSync(path.join(directory,'checkpoint.json'),JSON.stringify(manifest,null,2)+'\n');}

test('checkpoint packing deterministically preserves all fourteen exported tables and every original byte',async t=>{
 const f=await fixture(t),original=readVerifiedStorageSnapshot(f.source);
 assert.ok(storageExportCollections.every(collection=>original.proofs[collection].count>0));
 const packed=await packStorageCheckpoint({directory:f.source,output:f.packed,rawPartBytes:64*1024});
 assert.equal(packed.status,'packed');assert.equal(packed.network_requests,0);assert.equal(packed.database_calls,0);assert.equal(packed.media_bytes_included,false);
 const manifest=readManifest(f.packed);assert.ok(manifest.parts.length>1);
 assert.equal(fs.existsSync(path.join(f.packed,'resume.json')),false);
 for(const part of manifest.parts){
  const bytes=fs.readFileSync(path.join(f.packed,part.path));assert.ok(bytes.length<16*1024*1024);assert.equal(bytes.length,part.bytes);assert.equal(sha(bytes),part.sha256);
  assert.equal(bytes.readUInt32LE(4),0);assert.equal(bytes[9],255);
  const raw=gunzipSync(bytes);assert.equal(raw.length,part.raw_bytes);assert.equal(sha(raw),part.raw_sha256);
 }
 const second=path.join(f.root,'second');await packStorageCheckpoint({directory:f.source,output:second,rawPartBytes:64*1024});
 assert.deepEqual(fs.readFileSync(path.join(f.packed,'checkpoint.json')),fs.readFileSync(path.join(second,'checkpoint.json')));
 for(const part of manifest.parts)assert.deepEqual(fs.readFileSync(path.join(f.packed,part.path)),fs.readFileSync(path.join(second,part.path)));
 const unpacked=await unpackStorageCheckpoint({directory:f.packed,output:f.unpacked});assert.equal(unpacked.status,'unpacked');
 for(const file of manifest.files){const before=fs.readFileSync(path.join(f.source,file.path)),after=fs.readFileSync(path.join(f.unpacked,file.path));assert.deepEqual(after,before);assert.equal(sha(after),file.sha256);assert.equal(before.includes(Buffer.from(f.token)),false);}
 const restored=readVerifiedStorageSnapshot(f.unpacked);assert.deepEqual(restored.proofs,original.proofs);assert.equal(restored.manifest_sha256,original.manifest_sha256);
 assert.equal(restored.collections.records[0].value,' \n 42 \t');assert.equal(restored.collections.records[0].metadata,'{ "precision" : "census", "duplicate":1,"duplicate":2 }');
 assert.equal(restored.collections.entities.find(row=>row.id==='archived').active,0);assert.equal(restored.collections.relationships[0].is_example,1);assert.equal(restored.collections.retirements[0].target_id,'original');
 assert.equal((await packStorageCheckpoint({directory:f.source,output:f.packed,rawPartBytes:64*1024})).status,'verified-existing');
 assert.equal((await unpackStorageCheckpoint({directory:f.packed,output:f.unpacked})).status,'verified-existing');
 const dry=await restorePostgresStorage({directory:f.unpacked,dryRun:true});assert.equal(dry.network_requests,0);assert.deepEqual(dry.collections,original.proofs);
});

test('checkpoint rejects compressed tampering, original hashes and unsafe paths without publishing partial output',async t=>{
 const f=await fixture(t);await packStorageCheckpoint({directory:f.source,output:f.packed,rawPartBytes:64*1024});
 const scenarios={
  compressed:directory=>fs.appendFileSync(path.join(directory,readManifest(directory).parts[0].path),'tampered'),
  original:directory=>mutateManifest(directory,manifest=>{manifest.files[1].sha256='d'.repeat(64);}),
  traversal:directory=>mutateManifest(directory,manifest=>{manifest.files[1].path='../outside.json';}),
  backslash:directory=>mutateManifest(directory,manifest=>{manifest.parts[0].path='parts\\part-000001.gz';}),
  oversized:directory=>mutateManifest(directory,manifest=>{manifest.parts[0].bytes=checkpointLimits.compressedPartBytes;}),
  totals:directory=>mutateManifest(directory,manifest=>{manifest.total_raw_bytes++;}),
 };
 for(const [name,tamper]of Object.entries(scenarios)){
  const input=path.join(f.root,name),output=path.join(f.root,name+'-output');fs.cpSync(f.packed,input,{recursive:true});tamper(input);
  await assert.rejects(unpackStorageCheckpoint({directory:input,output}));assert.equal(fs.existsSync(output),false);
  assert.equal(fs.readdirSync(f.root).some(entry=>entry.startsWith('.'+name+'-output.staging-')),false);
 }
 assert.equal(fs.existsSync(path.join(f.root,'outside.json')),false);
});

test('a recomputed gzip hash cannot bypass the independent decompression bound',async t=>{
 const f=await fixture(t);await packStorageCheckpoint({directory:f.source,output:f.packed,rawPartBytes:64*1024});
 mutateManifest(f.packed,manifest=>{
  const part=manifest.parts[0],file=path.join(f.packed,part.path),raw=gunzipSync(fs.readFileSync(file));
  const malicious=gzipSync(Buffer.concat([raw,Buffer.from('extra')]),{level:9});fs.writeFileSync(file,malicious);
  manifest.total_gzip_bytes+=malicious.length-part.bytes;part.bytes=malicious.length;part.sha256=sha(malicious);
 });
 await assert.rejects(unpackStorageCheckpoint({directory:f.packed,output:f.unpacked}),/decompression byte limit/);assert.equal(fs.existsSync(f.unpacked),false);
});

test('symlinked checkpoint parts and changed source exports are rejected without replacing evidence',async t=>{
 const f=await fixture(t);await packStorageCheckpoint({directory:f.source,output:f.packed,rawPartBytes:64*1024});
 const first=readManifest(f.packed).parts[0],part=path.join(f.packed,first.path),outside=path.join(f.root,'outside.gz');fs.renameSync(part,outside);fs.symlinkSync(outside,part);
 await assert.rejects(unpackStorageCheckpoint({directory:f.packed,output:f.unpacked}),/symlink/);assert.equal(fs.existsSync(f.unpacked),false);
 const sourcePart=JSON.parse(fs.readFileSync(path.join(f.source,'index.json'))).collections.records.parts[0];fs.appendFileSync(path.join(f.source,sourcePart.path),' ');
 await assert.rejects(packStorageCheckpoint({directory:f.source,output:path.join(f.root,'invalid-source')}));assert.equal(fs.existsSync(path.join(f.root,'invalid-source')),false);
});

test('existing destinations are immutable and ordinary restore validates source hashes before any database call',async t=>{
 const f=await fixture(t);await packStorageCheckpoint({directory:f.source,output:f.packed});await unpackStorageCheckpoint({directory:f.packed,output:f.unpacked});
 const index=fs.readFileSync(path.join(f.unpacked,'index.json'));
 const page=JSON.parse(index).collections.records.parts[0];fs.appendFileSync(path.join(f.unpacked,page.path),' ');
 await assert.rejects(unpackStorageCheckpoint({directory:f.packed,output:f.unpacked}));assert.deepEqual(fs.readFileSync(path.join(f.unpacked,'index.json')),index);
 let calls=0;const driver={query:async()=>{calls++;},runTransaction:async()=>{calls++;}};
 await assert.rejects(restorePostgresStorage({directory:f.unpacked,driver,acknowledgeOwnerRestore:true}),/bytes changed/);assert.equal(calls,0);
 await assert.rejects(packStorageCheckpoint({directory:f.source,output:f.packed,rawPartBytes:64*1024}),/never overwrite/);
 await assert.rejects(packStorageCheckpoint({directory:f.source,output:path.join(f.source,'nested')}),/outside/);
 await assert.rejects(unpackStorageCheckpoint({directory:f.packed,output:path.join(f.packed,'nested')}),/outside/);
});

test('verified existing destinations reject checkpoint identity-summary tampering',async t=>{
 const f=await fixture(t);await packStorageCheckpoint({directory:f.source,output:f.packed});await unpackStorageCheckpoint({directory:f.packed,output:f.unpacked});
 for(const [key,value]of [['source_snapshot_fingerprint','e'.repeat(64)],['source_revision',999],['source_backend','postgres']]){
  const changed=path.join(f.root,'changed-'+key);fs.cpSync(f.packed,changed,{recursive:true});mutateManifest(changed,manifest=>{manifest[key]=value;});
  await assert.rejects(packStorageCheckpoint({directory:f.source,output:changed}),/never overwrite/);
  await assert.rejects(unpackStorageCheckpoint({directory:changed,output:f.unpacked}),/never overwrite/);
 }
});

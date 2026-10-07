// Execute this verifier directly from its pinned Git blob (README command).
// Project imports below are supplied by the immutable Git loader, not mutable
// working-tree files. Only an isolated in-memory SQLite store is used.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {registerHooks} from 'node:module';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {DatabaseSync} from 'node:sqlite';
import assert from 'node:assert/strict';

const [executionCommit,output]=process.argv.slice(1);
if(!/^[a-f0-9]{40}$/.test(executionCommit??''))throw Error('Supply exact execution commit');
const root=fs.realpathSync(process.cwd()),baseline='d7d209a18b96b5d86ba31795c422e6bf439cd72d';
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const git=(...args)=>execFileSync('git',['-C',root,...args],{maxBuffer:32*1024*1024});
const code=new Map(),phaseInputs={catalog:[],staging:[]};
const read=(commit,file)=>git('show',`${commit}:${file}`);
const input=(file,phase)=>{const bytes=read(baseline,file);phaseInputs[phase].push({path:file,sha256:sha(bytes),bytes:bytes.length});return bytes;};
const destination=path.resolve(root,output??'');
const owner=path.join(root,'coordination/engineering/release-membership-admission-1150');
if(!destination.startsWith(owner+path.sep)||!destination.endsWith('.json'))throw Error('Use a fresh owned JSON output');
for(let current=destination;current!==root;current=path.dirname(current)){
 if(fs.existsSync(current)&&fs.lstatSync(current).isSymbolicLink())throw Error('Output symlink refused');
}
if(fs.existsSync(destination)||!fs.statSync(path.dirname(destination)).isDirectory())throw Error('Output must have a fresh filename and existing owned parent');
registerHooks({load(url,context,next){
 if(url.startsWith('file:')){
  const file=fileURLToPath(url);
  if(file.startsWith(root+path.sep)&&/\.(?:js|mjs)$/.test(file)){
   const relative=path.relative(root,file).split(path.sep).join('/'),bytes=read(executionCommit,relative);
   code.set(relative,{path:relative,bytes:bytes.length,sha256:sha(bytes)});
   return {format:'module',source:bytes.toString('utf8'),shortCircuit:true};
  }
 }
 return next(url,context);
}});
const moduleURL=file=>pathToFileURL(path.join(root,file)).href;
const {publishGeographicReleases}=await import(moduleURL('scripts/bootstrap-geographic-release.mjs'));
const {importBatch}=await import(moduleURL('hosted/records.js'));
const {stageGeographicRelease,geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash}=await import(moduleURL('hosted/geographic-releases.js'));
const migrations=git('ls-tree','-r','--name-only',executionCommit,'drizzle').toString().trim().split('\n').filter(f=>f.endsWith('.sql')).map(file=>{
 const bytes=read(executionCommit,file);code.set(file,{path:file,bytes:bytes.length,sha256:sha(bytes)});return bytes;
});
const codeBytes=[...code.values()].reduce((n,p)=>n+p.bytes,0);
if([...code.values()].some(p=>p.bytes>32*1024*1024)||codeBytes>32*1024*1024)throw Error('Fixture code admission exceeded');
class D1{
 constructor(){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');
  for(const bytes of migrations)this.sqlite.exec(bytes.toString());
 }
 prepare(sql){let args=[];const db=this.sqlite;return{bind(...values){args=values;return this;},async all(){return{results:db.prepare(sql).all(...args)};},async first(){return db.prepare(sql).get(...args)??null;},run(){return{meta:{changes:Number(db.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const result=statements.map(s=>s.run());this.sqlite.exec('COMMIT');return result;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
// Admit the complete registry-seeding phase before creating/populating the test
// store. It is separate from the successor phase; neither is a whole-world run.
const index=JSON.parse(input('data/hosted-catalog/index.json','catalog')),catalog=[];
let catalogBytes=phaseInputs.catalog[0].bytes;
for(const part of index.batches.filter(p=>['entity_types','sources','entities'].includes(p.kind))){
 const bytes=input('data/hosted-catalog/'+part.path,'catalog');assert.equal(sha(bytes),part.sha256);
 catalogBytes+=bytes.length;if(bytes.length>32*1024*1024||catalogBytes*3+codeBytes>256*1024*1024)throw Error('Complete catalog fixture phase exceeds admission');
 catalog.push({part,bytes});
}
if(catalog.length+code.size+2>512)throw Error('Catalog fixture descriptor budget exceeded');
const db=new D1();
try{
 for(const {bytes}of catalog)await importBatch(db,JSON.parse(bytes));catalog.length=0;
 const originalRows=new Map();for(const table of ['atlas_entities','atlas_sources'])for(const row of db.sqlite.prepare(`SELECT * FROM ${table} ORDER BY id`).iterate())originalRows.set(table+':'+row.id,sha(JSON.stringify(row)));
 const registryBytes=input('data/geographic-releases/releases-v7-repacked-gzip.json.gz','staging');
 assert.equal(sha(registryBytes),'08faf0b0ad3b1a26c8c7d4e1f79cd17960d064baaaad74906f92a789cd99dbc7');
 const original=JSON.parse(gunzipSync(registryBytes,{maxOutputLength:32*1024*1024})),release=original.releases.at(-1);
 // This is explicitly successor7-only admission/staging, not a simulated claim
 // that the six predecessors are already published or a full-world delivery.
 const manifest={...original,releases:[release]};
 const request=async route=>{assert.ok(route.startsWith('/api/geography/release?'));return Response.json(null);};
 const inputOrdered=createHash('sha256');let inputRows=0,outputRows=0,writes=0,interrupted=false,replays=0;
 const captured=new Map();
 const readBatch=part=>{const raw=input('data/geographic-releases/'+part.path,'staging');
  const decoded=part.encoding==='gzip'?gunzipSync(raw,{maxOutputLength:32*1024*1024}):raw;
  const p=JSON.parse(decoded);for(const row of p.memberships??[]){inputOrdered.update(JSON.stringify(row)+'\n');inputRows++;}
  captured.set(part.path,raw);return raw;
 };
 const bodies=[];
 const batch=async(part,body)=>{writes++;bodies.push({part,body:Buffer.from(body)});
  for(const row of JSON.parse(body).memberships??[])outputRows++;
  if(part.route==='/api/records/import')return importBatch(db,JSON.parse(body));
  const result=await stageGeographicRelease(db,JSON.parse(body));
  if(!interrupted&&result.counts.memberships>0){interrupted=true;throw Error('Injected interrupted response after durable staging');}
  return result;
 };
 await assert.rejects(publishGeographicReleases({manifest,readBatch,batch,request,mode:'stage',concurrency:1}),/Injected interrupted response/);
 const firstCount=db.sqlite.prepare('SELECT count(*) n FROM atlas_geographic_memberships WHERE release_id=?').get(release.id).n;assert.ok(firstCount>0&&firstCount<84833);
 // Retry exact captured immutable inputs. Counting outputs anew avoids treating
 // the intentionally interrupted first attempt as a completed result.
 bodies.length=0;outputRows=0;const retryOrdered=createHash('sha256');
 const result=await publishGeographicReleases({manifest,readBatch:part=>captured.get(part.path)??input('data/geographic-releases/'+part.path,'staging'),request,mode:'stage',concurrency:1,
  batch:async(part,body)=>{bodies.push({part,body:Buffer.from(body)});const payload=JSON.parse(body);
   for(const row of payload.memberships??[]){retryOrdered.update(JSON.stringify(row)+'\n');outputRows++;}
   const response=await(part.route==='/api/records/import'?importBatch(db,payload):stageGeographicRelease(db,payload));if(response.duplicate)replays++;return response;}});
 assert.equal(result[0].status,'staged');assert.equal(inputRows,84833);assert.equal(outputRows,inputRows);assert.equal(retryOrdered.digest('hex'),inputOrdered.digest('hex'));
 const members=db.sqlite.prepare('SELECT m.*,e.kind FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id WHERE m.release_id=? ORDER BY m.entity_id').all(release.id).map(r=>({...r,evidence:JSON.parse(r.evidence)}));
 const changes=db.sqlite.prepare('SELECT * FROM atlas_geographic_changes WHERE release_id=? ORDER BY id').all(release.id).map(r=>({...r,evidence:JSON.parse(r.evidence)}));
 assert.equal(members.length,84833);assert.equal(await geographicMembershipHash(members),release.membership_sha256);assert.equal(await geographicLocationIdsHash(members),release.location_ids_sha256);assert.equal(await geographicChangesHash(changes),release.changes_sha256);
 for(const table of ['atlas_entities','atlas_sources'])for(const row of db.sqlite.prepare(`SELECT * FROM ${table} ORDER BY id`).iterate()){
  const previous=originalRows.get(table+':'+row.id);if(previous)assert.equal(sha(JSON.stringify(row)),previous,'Original registry/source row changed');
 }
 const row=bodies.find(b=>JSON.parse(b.body).memberships?.length),altered=JSON.parse(row.body);altered.memberships[0].reference_name+=' conflicting';
 await assert.rejects(stageGeographicRelease(db,altered),e=>e.status===409&&/Ingestion ID/.test(e.message));
 const requestHash=createHash('sha256');for(const {body}of bodies)requestHash.update(body).update('\n');
 const ledger={baseline,execution_commit:executionCommit,catalog_inputs:phaseInputs.catalog,staging_inputs:phaseInputs.staging,execution_code:[...code.values()],
  memberships:members.length,changes:changes.length,requests:bodies.length,duplicate_replays:replays,interrupted_durable_memberships:firstCount,catalog_phase_admitted_bytes:catalogBytes*3,
  original_registry_source_rows_verified:originalRows.size,predecessor_definitions_sha256:sha(JSON.stringify(original.releases.slice(0,-1))),
  request_bodies_sha256:requestHash.digest('hex'),membership_sha256:release.membership_sha256,location_ids_sha256:release.location_ids_sha256,changes_sha256:release.changes_sha256,
  limits:'Isolated successor7-only staging; authentic original stable registry seeded separately. No finalization, live import, source authority or geography approval.'};
 const bytes=Buffer.from(JSON.stringify(ledger,null,2)+'\n');if(bytes.length>32*1024*1024)throw Error('Verification output exceeds file budget');
 fs.writeFileSync(destination,bytes,{flag:'wx'});
 console.log(JSON.stringify({memberships:ledger.memberships,changes:ledger.changes,requests:ledger.requests,replays,output}));
}finally{db.sqlite.close();}

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {compileHostedMigrations} from '../scripts/compile-hosted-migrations.mjs';
import {stageSiteMigrations,validateSiteMigrationInputs} from '../scripts/stage-site-migrations.mjs';

const root=path.resolve(import.meta.dirname,'..'),source=path.join(root,'drizzle');
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const read=file=>JSON.parse(fs.readFileSync(file));
const sqlFiles=directory=>fs.readdirSync(directory).filter(file=>file.endsWith('.sql')).sort();
function site(){const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-site-migrations-'));fs.mkdirSync(path.join(directory,'.openai'));fs.writeFileSync(path.join(directory,'.openai','hosting.json'),'{}');return directory;}
function snapshot(directory){return new Map(fs.readdirSync(directory,{recursive:true}).filter(file=>fs.statSync(path.join(directory,file)).isFile()).map(file=>[file,sha(fs.readFileSync(path.join(directory,file)))]));}
function equalSnapshot(directory,expected){assert.deepEqual(snapshot(directory),expected);}

test('explicit legacy staging retains every original migration and metadata byte and deploys exactly 0000–0007',()=>{
 const directory=site(),before=snapshot(source),compiledBefore=snapshot(path.join(root,'dist/drizzle'));
 const worker=path.join(directory,'dist/server');fs.mkdirSync(worker,{recursive:true});
 fs.writeFileSync(path.join(worker,'wrangler.json'),JSON.stringify({vars:{ATLAS_CONTENT_BACKEND:'postgres'}}));
 const fetchBefore=globalThis.fetch;globalThis.fetch=()=>{throw Error('No provider/network work is authorized by packaging');};
 try{
  const result=stageSiteMigrations(directory,{legacyD1Only:true});
  assert.equal(result.legacy_d1_only,true);assert.equal(result.deployment_migrations,8);
  assert.equal(result.retained_source_migrations,sqlFiles(source).length);assert.ok(result.retained_source_migrations>=10);
  equalSnapshot(path.join(directory,'drizzle-source'),before);equalSnapshot(source,before);
  equalSnapshot(path.join(root,'dist/drizzle'),compiledBefore);
  for(const folder of [path.join(directory,'drizzle'),path.join(worker,'drizzle')]){
   assert.deepEqual(sqlFiles(folder),sqlFiles(source).slice(0,8));
   const journal=read(path.join(folder,'meta/_journal.json'));
   assert.deepEqual(journal.entries,read(path.join(source,'meta/_journal.json')).entries.slice(0,8));
   assert.deepEqual(fs.readdirSync(path.join(folder,'meta')).sort(),['0000_snapshot.json','0001_snapshot.json','0002_snapshot.json','0003_snapshot.json','0004_snapshot.json','0005_snapshot.json','0006_snapshot.json','0007_snapshot.json','_journal.json']);
   const receipt=read(path.join(folder,'transport-receipt.json'));
   assert.equal(receipt.legacy_d1_only,true);assert.equal(receipt.retained_source_sha256,result.retained_source_sha256);
   assert.equal(receipt.full_transport_receipt_sha256,sha(fs.readFileSync(path.join(root,'dist/drizzle/transport-receipt.json'))));
   assert.equal(receipt.migrations.length,8);assert.equal(receipt.retained_source_migrations.length,sqlFiles(source).length);
   assert.deepEqual(receipt.omitted_deployment_migrations.map(row=>row.file),sqlFiles(source).slice(8));
   for(const row of receipt.migrations)assert.equal(sha(fs.readFileSync(path.join(folder,row.file))),row.transport_sha256);
   for(const row of receipt.meta)assert.equal(sha(fs.readFileSync(path.join(folder,row.file))),row.sha256);
   for(const row of receipt.retained_source_migrations)assert.equal(sha(fs.readFileSync(path.join(source,row.file))),row.sha256);
  }
  assert.deepEqual(snapshot(path.join(directory,'drizzle')),snapshot(path.join(worker,'drizzle')));
  assert.equal(read(path.join(worker,'wrangler.json')).vars.ATLAS_CONTENT_BACKEND,'postgres');
  assert.equal(fs.existsSync(path.join(directory,'dist/drizzle')),false,'Redundant dist/drizzle is not created');
 }finally{globalThis.fetch=fetchBefore;fs.rmSync(directory,{recursive:true,force:true});}
});

test('default staging keeps the complete derivative and opt-in retries remove old forward files',()=>{
 const directory=site();try{
  const defaultResult=stageSiteMigrations(directory);
  assert.equal(Object.hasOwn(defaultResult,'legacy_d1_only'),false);
  assert.deepEqual(sqlFiles(path.join(directory,'drizzle')),sqlFiles(source));
  assert.deepEqual(read(path.join(directory,'drizzle/meta/_journal.json')),read(path.join(source,'meta/_journal.json')));
  fs.writeFileSync(path.join(directory,'drizzle','9999_stale.sql'),'stale');
  fs.writeFileSync(path.join(directory,'dist/server/drizzle','9999_stale.sql'),'stale');
  const first=stageSiteMigrations(directory,{legacyD1Only:true}),firstFiles=snapshot(path.join(directory,'drizzle'));
  assert.deepEqual(stageSiteMigrations(directory,{legacyD1Only:true}),first);
  equalSnapshot(path.join(directory,'drizzle'),firstFiles);
  assert.deepEqual(sqlFiles(path.join(directory,'dist/server/drizzle')),sqlFiles(source).slice(0,8));
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
});

test('all forward migration/source/journal hashes are checked before any deployment cutoff',()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-stage-preflight-'));
 const input=path.join(directory,'source'),compiled=path.join(directory,'compiled');
 fs.cpSync(source,input,{recursive:true});
 try{
  compileHostedMigrations({input,output:compiled});
  assert.equal(validateSiteMigrationInputs(input,compiled).receipt.migrations.length,sqlFiles(source).length);
  const forward=sqlFiles(input).at(-1),original=fs.readFileSync(path.join(input,forward));
  fs.appendFileSync(path.join(input,forward),'\n');
  assert.throws(()=>validateSiteMigrationInputs(input,compiled),/source\/build mismatch/);
  fs.writeFileSync(path.join(input,forward),original);
  fs.unlinkSync(path.join(compiled,forward));
  assert.throws(()=>validateSiteMigrationInputs(input,compiled),/Full canonical migration inventory/);
  compileHostedMigrations({input,output:compiled});
  const receiptFile=path.join(compiled,'transport-receipt.json'),receipt=read(receiptFile);
  [receipt.migrations[0],receipt.migrations[1]]=[receipt.migrations[1],receipt.migrations[0]];
  fs.writeFileSync(receiptFile,JSON.stringify(receipt));
  assert.throws(()=>validateSiteMigrationInputs(input,compiled),/Full canonical migration inventory/);
  compileHostedMigrations({input,output:compiled});
  fs.appendFileSync(path.join(compiled,'meta/_journal.json'),' ');
  assert.throws(()=>validateSiteMigrationInputs(input,compiled),/metadata mismatch/);
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
});

test('the eight staged migrations have the original eight-migration schema and no forward tables',()=>{
 const directory=site(),original=new DatabaseSync(':memory:'),derivative=new DatabaseSync(':memory:');
 try{
  stageSiteMigrations(directory,{legacyD1Only:true});
  for(const file of sqlFiles(source).slice(0,8)){
   original.exec(fs.readFileSync(path.join(source,file),'utf8'));
   derivative.exec(fs.readFileSync(path.join(directory,'drizzle',file),'utf8'));
  }
  const normalize=sql=>sql?.replace(/SELECT CASE WHEN (.+) THEN (RAISE\(ABORT,'(?:''|[^'])*'\)) END;/g,(_,condition,raise)=>`SELECT ${raise} WHERE ${condition};`);
  const objects=db=>db.prepare("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").all().map(row=>({...row,sql:normalize(row.sql)}));
  assert.deepEqual(objects(derivative),objects(original));
  assert.equal(derivative.prepare("SELECT count(*) n FROM sqlite_master WHERE name LIKE 'atlas_temporal_%' OR name LIKE 'atlas_footprint_%'").get().n,0);
  assert.deepEqual(derivative.prepare('PRAGMA foreign_key_check').all(),[]);
 }finally{original.close();derivative.close();fs.rmSync(directory,{recursive:true,force:true});}
});

test('staging requires explicit valid mode, a separate real checkout and a supported CLI flag',()=>{
 assert.throws(()=>stageSiteMigrations(root,{legacyD1Only:true}),/separate Site checkout/);
 const directory=site();try{
  assert.throws(()=>stageSiteMigrations(directory,{legacyD1Only:'true'}),/explicit boolean/);
  fs.symlinkSync(root,path.join(directory,'dist'),'dir');
  assert.throws(()=>stageSiteMigrations(directory,{legacyD1Only:true}),/must not be symlinks/);
  fs.unlinkSync(path.join(directory,'dist'));
  const bad=spawnSync(process.execPath,[path.join(root,'scripts/stage-site-migrations.mjs'),directory,'--unknown'],{encoding:'utf8'});
  assert.notEqual(bad.status,0);assert.match(bad.stderr,/explicit --legacy-d1-only/);
  const good=spawnSync(process.execPath,[path.join(root,'scripts/stage-site-migrations.mjs'),directory,'--legacy-d1-only'],{encoding:'utf8'});
  assert.equal(good.status,0,good.stderr);assert.equal(JSON.parse(good.stdout).legacy_d1_only,true);
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
});

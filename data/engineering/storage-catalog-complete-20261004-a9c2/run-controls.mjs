import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {PGlite} from '@electric-sql/pglite';
import {storageQueries} from '../../../scripts/measure-neon-storage.mjs';

const root='data/engineering/storage-catalog-complete-20261004-a9c2/';
const write=(name,value)=>fs.writeFileSync(root+name,JSON.stringify(value,null,2)+'\n');
const tests=spawnSync(process.execPath,['--test','test/neon-table-storage.test.mjs','test/neon-capacity.test.mjs','test/neon-verification.test.mjs'],{encoding:'utf8',maxBuffer:8*1024*1024});
fs.writeFileSync(root+'tests-final-01.log',tests.stdout+tests.stderr);
if(tests.status!==0)throw Error('Scoped tests failed; preserve log');
const count=Number(tests.stdout.match(/tests (\d+)/)?.[1]),passed=Number(tests.stdout.match(/pass (\d+)/)?.[1]);
if(!Number.isInteger(count)||count!==passed)throw Error('Test count unavailable');
write('tests-receipt-01.json',{status:'passed',test_count:count,pass_count:passed,exit_code:tests.status,checked_at_utc:new Date().toISOString(),runtime:process.version,log:'tests-final-01.log',limitations:['Isolated and mocked controls only; production secret/API/SQL not accessed.']});
const db=new PGlite();
try{
  await db.exec("CREATE TABLE atlas_storage_probe(id text PRIMARY KEY,value text); INSERT INTO atlas_storage_probe VALUES('retained',repeat('evidence',5000)); CREATE TABLE non_application_probe(id integer); CREATE TABLE worldatlas_schema_migrations(id text PRIMARY KEY);");
  await db.exec('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY');
  const results=[];for(const query of storageQueries)results.push(await db.query(query));
  if(results[1].rows[0].read_only!=='on'||JSON.stringify(results[2].rows.map(r=>r.table_name))!==JSON.stringify(['atlas_storage_probe','non_application_probe','worldatlas_schema_migrations']))throw Error('Catalog control mismatch');
  let denied=null;try{await db.query("DELETE FROM atlas_storage_probe");}catch(error){denied=error.code;}
  if(denied!=='25006')throw Error('Readonly denial not observed');
  await db.exec('ROLLBACK');const preserved=await db.query('SELECT count(*)::integer AS count FROM atlas_storage_probe');
  if(preserved.rows[0].count!==1)throw Error('Isolated source changed');
  write('isolated-catalog-01.json',{checked_at_utc:new Date().toISOString(),runtime:process.version,environment:'PGlite isolated in-memory PostgreSQL; synthetic fixture, not production',results,denied_write_sqlstate:denied,rows_preserved:preserved.rows[0].count,query_sha256:createHash('sha256').update(JSON.stringify(storageQueries)).digest('hex')});
}finally{await db.close();}
for(const kind of ['positive-control','negative-control'])write(kind+'-01.json',{method_id:'public-catalog-completeness',kind,outcome:'passed',checked_at_utc:new Date().toISOString(),evidence:['tests-final-01.log','isolated-catalog-01.json'],scope:kind==='positive-control'?'Actual fixed catalog SQL executed on isolated PostgreSQL with read-only transaction and complete public table/index inventory including owner registry and explicitly unclassified public fixture. Mocked exact production binding/driver controls also pass.':'Isolated PostgreSQL denies DELETE with SQLSTATE25006 and retains original row; target mismatch, timeout, overflow, unsafe output and credential-bearing exception tests reject. No production mutation probe.'});
write('source-inventory-01.json',{ancestry:spawnSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).stdout.trim(),measurement_vintage:'uncommitted candidate bytes; isolated controls only',files:['scripts/measure-neon-storage.mjs','test/neon-table-storage.test.mjs','.github/workflows/neon-table-storage.yml',root+'run-controls.mjs'].map(path=>{const b=fs.readFileSync(path);return {path,bytes:b.length,sha256:createHash('sha256').update(b).digest('hex')};})});

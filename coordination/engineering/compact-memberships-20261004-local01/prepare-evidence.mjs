import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
const owned='coordination/engineering/compact-memberships-20261004-local01';
const base='a4e8292889f47ddab76ff1676583780d1b19aa2e';
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
const log=fs.readFileSync(owned+'/contract-tests.log','utf8');
const counts=Object.fromEntries(['tests','pass','fail','cancelled','skipped','todo'].map(key=>{
 const match=log.match(new RegExp('^# '+key+' (\\d+)$','m'));if(!match)throw Error('Missing actual TAP count');return [key,Number(match[1])];
}));
if(counts.tests!==35||counts.pass!==35||counts.fail||counts.cancelled||counts.skipped||counts.todo)throw Error('Contract suite did not complete');
const passedNames=[...log.matchAll(/^ok \d+ - (.+)$/gm)].map(x=>x[1]);
const prefixes=['compact contract preserves','compact membership rejects','compact dictionary preserves','failed copy rolls','copy parity rejects','application role can'];
const compactNames=prefixes.map(prefix=>passedNames.find(name=>name.startsWith(prefix)));
if(compactNames.some(name=>!name))throw Error('Missing compact controls');
const result={version:1,scope:'local-pglite-contract-tests',counts,compact_tests:compactNames,
 test_log_sha256:digest(log),production_capacity_verified:false,private_backup_verified:false,
 limitations:['Small synthetic fixtures only; the full compatible production-size contract is not measured in this PR.',
 'Production migration, current backup, role/schema/export/recovery inventories, capacity/reclamation and publisher delivery remain subsequent issue parts.']};
fs.writeFileSync(owned+'/test-results.json',JSON.stringify(result,null,2)+'\n');
const files=['postgres/membership-storage-v1.sql','scripts/compact-membership-storage.mjs','test/compact-membership-storage.test.mjs',
 ...fs.readdirSync(owned).filter(x=>x!=='evidence-quality.json').map(x=>owned+'/'+x)];
const descriptor=(name,original=false)=>{const raw=original?execFileSync('git',['show',base+':'+name]):fs.readFileSync(name);return {path:name,bytes:raw.length,sha256:digest(raw),hash_kind:'file-bytes',...(name.endsWith('.gz')?{uncompressed_bytes:gunzipSync(raw).length,uncompressed_sha256:digest(gunzipSync(raw))}:{})};};
const baselineNames=['postgres/schema.sql','postgres/runtime-role.sql','hosted/geographic-releases.js','hosted/postgres-adapter.js',
 'hosted/storage-export-v2-contract.js','hosted/storage-export-v3-contract.js','scripts/verify-postgres-schema.mjs','scripts/current-postgres-recovery.mjs','package-lock.json'];
const outputs=files.map(name=>descriptor(name));
const metrics=Object.entries(counts).map(([key,value])=>({id:'test-'+key,value,unit:'count',vintage:'baseline',evaluation_commit:base,input_sha256:outputs.find(x=>x.path===owned+'/test-results.json').sha256}));
const manifest={version:1,issue:783,lane:'engineering',worker_id:'engineering-compact-memberships-20261004-local01',
 subject_ids:[],subject_ids_sha256:digest('[]'),baseline:{commit:base,files:baselineNames.map(name=>({...descriptor(name,true),role:'original-source'})),pins:{},pin_files:{}},
 sources:[],outputs,methods:[{id:'guarded-contract',kind:'code',description:'Actual isolated original-schema PostgreSQL/PGlite fixtures; full row parity, original guards, new/retried service publication, raw JSON spelling, invalid parent/source/withdrawal, failed/corrupt copy, rollback and adverse default ACL controls.',software:'Node24 and locked PGlite0.5.8',units:'test count'}],
 metrics,metric_bindings:metrics.map(x=>({metric_id:x.id,path:owned+'/test-results.json',json_pointer:'/counts/'+x.id.slice(5)})),summaries:[],
 conclusions:[],
 stages:{research:'complete',implementation:'implemented',geographic_approval:'not-requested'},
 change_receipts:files.map(name=>({path:name,status:'added'})).concat([{path:owned+'/evidence-quality.json',status:'added'}]),
 commands:['node --test --test-concurrency=2 --test-reporter=tap test/compact-membership-storage.test.mjs test/postgres-contract.test.mjs test/postgres-adapter.test.mjs test/geographic-releases.test.mjs > '+owned+'/contract-tests.log','node '+owned+'/prepare-evidence.mjs','node scripts/evidence-quality.mjs '+owned+'/evidence-quality.json']};
fs.writeFileSync(owned+'/evidence-quality.json',JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({outputs:outputs.length,metrics:metrics.length}));

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {generateKeyPairSync,createHash} from 'node:crypto';
import {loadRecoveryReservation,validateRecoveryWindow,validatedOwnerConnection,assertRestoredInventory,boundedOwnerJSON,runCurrentPostgresRecovery,isolatedRestoreSQL,isolatedOriginalChecks} from '../scripts/current-postgres-recovery.mjs';
import {backupRecipientFingerprint} from '../scripts/recovery-backup-envelope.mjs';
import {storageExportV2Contract,storageExportV2Collections,v2MarkerIdentity} from '../hosted/storage-export-v2-contract.js';
const sha=x=>createHash('sha256').update(x).digest('hex');
const now=Date.parse('2026-10-04T06:00:00Z'),head='a'.repeat(40),toolSHA='b'.repeat(64);
const {publicKey}=generateKeyPairSync('rsa',{modulusLength:3072,publicKeyEncoding:{type:'spki',format:'pem'}});
const claim={active:true,live_work:true,issue_number:51,claim_id:'fixture',worker_id:'fixture-holder',branch:'engineering/fixture',expires_at:new Date(now+3600000).toISOString()};
function window(){const marker={version:2,backend:'postgres',read_only:true,revision:1,contract:storageExportV2Contract,counts:Object.fromEntries(storageExportV2Collections.map(k=>[k,0])),catalog_sha256:storageExportV2Contract.postgres_catalog_sha256,geographic_releases_sha256:'c'.repeat(64),footprint_versions_sha256:'d'.repeat(64)};marker.fingerprint=sha(JSON.stringify(v2MarkerIdentity(marker)));return {version:1,issue:51,queue:714,operator_worker_id:'engineering-central-publication-20261003',primary_main_commit:head,capture_tool_sha256:toolSHA,method:'readonly-native-pg-dump-and-isolated-restore',backup_recipient_public_key:publicKey,backup_recipient_sha256:backupRecipientFingerprint(publicKey),observed_at_utc:new Date(now).toISOString(),expires_at_utc:new Date(now+1800000).toISOString(),claim_id:claim.claim_id,holder_worker_id:claim.worker_id,claim_branch:claim.branch,site:{project_id:'appgprj_6abdf87277c08191bce4a22b8dfb25db',version:24,deployment_id:'appgdep_fixture'},read_only:true,drain_verified:true,restore_writes_operator:'engineering-central-publication-20261003',rollback_receipt_url:'https://github.com/ChengshuLi/WorldAtlas/issues/714',source_marker:marker};}
const validate=(value,c=claim,n=now)=>validateRecoveryWindow(value,c,{head,toolSHA,now:n});
test('accepts only pinned live publisher read window',()=>assert.equal(validate(window()).issue,51));
for(const [label,change] of [
 ['writable source',w=>w.source_marker.read_only=false],['legacy projection',w=>w.source_marker.legacy_projection=true],['wrong main',w=>w.primary_main_commit='e'.repeat(40)],['wrong tool',w=>w.capture_tool_sha256='e'.repeat(64)],['wrong publisher',w=>w.operator_worker_id='other'],['undrained requests',w=>w.drain_verified=false],['unpinned recipient',w=>w.backup_recipient_sha256='e'.repeat(64)],['missing count',w=>delete w.source_marker.counts[storageExportV2Collections[0]]],['changed fingerprint',w=>w.source_marker.fingerprint='e'.repeat(64)],['expired window',w=>w.expires_at_utc=new Date(now).toISOString()],['old observation',w=>w.observed_at_utc=new Date(now-660000).toISOString()],['future observation',w=>w.observed_at_utc=new Date(now+1).toISOString()],['unbounded window',w=>w.expires_at_utc=new Date(now+1800001).toISOString()]
])test(`rejects ${label}`,()=>{const w=window();change(w);assert.throws(()=>validate(w));});
for(const [field,value] of [['active',false],['live_work',false],['issue_number',22],['claim_id','other'],['worker_id','other'],['branch','other'],['expires_at',new Date(now).toISOString()]])test(`rejects canonical claim ${field} mismatch`,()=>assert.throws(()=>validate(window(),{...claim,[field]:value})));
test('end validation permits elapsed capture time within original window',()=>assert.doesNotThrow(()=>validateRecoveryWindow(window(),claim,{head,toolSHA,now:now+1200000,phase:'end'})));
// Production acceptance belongs to the publisher's child, not the source author.
function delegated(){
 const handoffReceipt={id:123,html_url:'https://github.com/ChengshuLi/WorldAtlas/issues/714#issuecomment-123',user:{type:'User'},author_association:'OWNER',body:'Merged implementation handed off with preserved evidence; publisher owns production acceptance.'};
 const spec={max_prs:1,depends_on:[],scope:'Current SQL recovery only',mode:'engineering',production_operation:{source_issue:51,queue:714,publisher_worker_id:'engineering-central-publication-20261003',handoff_receipt_url:handoffReceipt.html_url}};
 const reservationIssue={number:900,state:'open',labels:['type:engineering','kind:work-item','status:ready'],body:'<!-- worldatlas-work:v1\n'+JSON.stringify(spec)+'\n-->'};
 const sourceClaim={...claim,active:false,live_work:false,released_at:new Date(now-1).toISOString()};
 const c={...claim,issue_number:900,worker_id:spec.production_operation.publisher_worker_id,mode:'engineering'};
 const w={...window(),reservation_issue:900,reservation_scope_sha256:sha(JSON.stringify(spec)),holder_worker_id:c.worker_id};
 return {w,c,context:{reservationIssue,sourceClaim,handoffReceipt},spec};
}
const validateDelegated=fixture=>validateRecoveryWindow(fixture.w,fixture.c,{head,toolSHA,now,...fixture.context});
test('released implementer can move on while publisher holds its own recovery child',()=>assert.equal(validateDelegated(delegated()).reservation_issue,900));
for(const [label,change] of [
 ['active source claim even without live work',d=>d.context.sourceClaim.active=true],
 ['expired active source claim',d=>{d.context.sourceClaim.active=true;d.context.sourceClaim.expires_at=new Date(now-1).toISOString();}],
 ['unsettled source live flag',d=>d.context.sourceClaim.live_work=true],
 ['missing original release',d=>delete d.context.sourceClaim.released_at],
 ['future original release',d=>d.context.sourceClaim.released_at=new Date(now+1).toISOString()],
 ['different source issue',d=>d.context.sourceClaim.issue_number=22],
 ['implementation holder retained on operation',d=>{d.c.worker_id='fixture-holder';d.w.holder_worker_id=d.c.worker_id;}],
 ['non-engineering operation holder',d=>d.c.mode='geography'],
 ['blocked operation',d=>d.context.reservationIssue.labels.push('status:blocked')],
 ['closed operation',d=>d.context.reservationIssue.state='closed'],
 ['unscoped operation',d=>d.context.reservationIssue.body='no scope'],
 ['missing ready label',d=>d.context.reservationIssue.labels=d.context.reservationIssue.labels.filter(x=>x!=='status:ready')],
 ['wrong child issue',d=>d.context.reservationIssue.number=901],
 ['changed scope pin',d=>d.w.reservation_scope_sha256='a'.repeat(64)],
 ['unauthorized handoff',d=>d.context.handoffReceipt.author_association='NONE'],
 ['different handoff comment',d=>d.context.handoffReceipt.html_url='https://github.com/ChengshuLi/WorldAtlas/issues/714#issuecomment-124'],
 ['unconfirmed publisher live reservation',d=>d.c.live_work=false],
 ['expired publisher reservation',d=>d.c.expires_at=new Date(now).toISOString()],
 ['invalid reservation number',d=>d.w.reservation_issue='900']
])test('delegated recovery rejects '+label,()=>{const d=delegated();change(d);assert.throws(()=>validateDelegated(d));});
for(const [field,value] of [['source_issue',22],['queue',22],['publisher_worker_id','other']])test('delegated recovery rejects operation '+field,()=>{const d=delegated();d.spec.production_operation[field]=value;d.context.reservationIssue.body='<!-- worldatlas-work:v1\n'+JSON.stringify(d.spec)+'\n-->';d.w.reservation_scope_sha256=sha(JSON.stringify(d.spec));assert.throws(()=>validateDelegated(d));});
test('delegated operation dependencies must still be complete',()=>{
 const d=delegated();d.spec.depends_on=[732];d.context.reservationIssue.body='<!-- worldatlas-work:v1\n'+JSON.stringify(d.spec)+'\n-->';d.w.reservation_scope_sha256=sha(JSON.stringify(d.spec));
 assert.throws(()=>validateDelegated(d));d.context.dependencies=[{number:732,state:'open'}];assert.throws(()=>validateDelegated(d));d.context.dependencies=[{number:732,state:'closed'}];assert.doesNotThrow(()=>validateDelegated(d));
});
test('final readback rejects a newly reserved source and a changed operation scope',()=>{
 const d=delegated();
 assert.doesNotThrow(()=>validateRecoveryWindow(d.w,d.c,{head,toolSHA,now:now+1200000,phase:'end',...d.context}));
 for(const context of [{...d.context,sourceClaim:{...d.context.sourceClaim,active:true}},{...d.context,reservationIssue:{...d.context.reservationIssue,body:d.context.reservationIssue.body.replace('Current SQL recovery only','Widened scope')}}])assert.throws(()=>validateRecoveryWindow(d.w,d.c,{head,toolSHA,now:now+1200000,phase:'end',...context}));
});
test('fresh start/end reservation reads fetch child and original instead of cached author claim',async()=>{
 const d=delegated(),calls=[];
 const comments=c=>[{id:55,user:{login:'github-actions[bot]'},body:'**Worker reservation:** fixture\n<!-- worldatlas-claim:v1\n'+JSON.stringify({version:1,...c})+'\n-->'}];
 const api=async route=>{calls.push(route);if(route.includes('/issues/51/comments'))return comments(d.context.sourceClaim);if(route.includes('/issues/900/comments'))return comments(d.c);if(route.endsWith('/issues/900'))return d.context.reservationIssue;if(route.endsWith('/issues/comments/123'))return d.context.handoffReceipt;throw Error('unexpected route');};
 const first=await loadRecoveryReservation(d.w,api);
 assert.doesNotThrow(()=>validateRecoveryWindow(d.w,first.claim,{head,toolSHA,now,...first}));
 d.context.sourceClaim.active=true;
 const final=await loadRecoveryReservation(d.w,api);
 assert.throws(()=>validateRecoveryWindow(d.w,final.claim,{head,toolSHA,now,phase:'end',...final}));
 assert.equal(calls.filter(x=>x.includes('/issues/51/comments')).length,2);
 assert.equal(calls.filter(x=>x.endsWith('/issues/900')).length,2);
});
const host='ep-fixture.us-east-2.aws.neon.tech',uri=`postgresql://neondb_owner:fixture-password@${host}/neondb?sslmode=require`;
test('owner secret parsed without including connection URI in result',()=>assert.deepEqual(validatedOwnerConnection(uri,host),{host,password:'fixture-password'}));
for(const bad of [uri.replace('neondb_owner','worldatlas_app'),uri.replace('/neondb?','/other?'),uri.replace('sslmode=require','sslmode=disable'),uri.replace('fixture-password','bad%0Asecret'),uri.replace(host,'ep-other.us-east-2.aws.neon.tech'),uri+'#fragment'])test('rejects unsafe owner endpoint or identity '+bad.replace('fixture-password','redacted'),()=>assert.throws(()=>validatedOwnerConnection(bad,host)));
const inventory=()=>({identity:{database_name:'neondb'},collections:{locations:{count:1,ordered_rows_sha256:'a'}},owner_registry:[{migration_id:'original',applied_at:'original timestamp'}],permissions:[{owner:'neondb_owner',app_select:false}],sequence:[{last_value:5,is_called:true}]});
test('isolated database identity can differ while original bytes and state remain exact',()=>{const before=inventory(),target=inventory();target.identity.database_name='postgres';assert.doesNotThrow(()=>assertRestoredInventory(before,target,inventory()));});
for(const field of ['collections','owner_registry','permissions','sequence'])test(`detects restored ${field} corruption`,()=>{const target=inventory();target[field]=[];assert.throws(()=>assertRestoredInventory(inventory(),target,inventory()));});
test('detects source change during backup',()=>{const after=inventory();after.sequence[0].last_value++;assert.throws(()=>assertRestoredInventory(inventory(),inventory(),after));});
test('bounded owner API accepts valid object',async()=>assert.deepEqual(await boundedOwnerJSON(new Response('{"endpoints":[]}')),{endpoints:[]}));
for(const body of ['[]','null','invalid',JSON.stringify({oversized:'a'.repeat(2*1024*1024)})])test('bounded owner API rejects malformed or oversized response '+body.length,async()=>assert.rejects(()=>boundedOwnerJSON(new Response(body))));
test('owner API rejects HTTP failures',async()=>assert.rejects(()=>boundedOwnerJSON(new Response('{}',{status:403}))));
test('untrusted execution fails before any provider access and writes sanitized failure receipt',async()=>{const dir=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-recovery-test-')),output=path.join(dir,'receipt');let calls=0;try{const result=await runCurrentPostgresRecovery({env:{NEON_API_KEY:'fixture-secret'},fetcher:()=>{calls++;throw Error('unexpected network');},output});assert.equal(calls,0);assert.equal(result.status,'failed');assert.equal(result.failure_stage,'authorize');assert.equal(fs.readFileSync(path.join(output,'public-receipts/receipt.json'),'utf8').includes('fixture-secret'),false);await assert.rejects(()=>runCurrentPostgresRecovery({env:{},output}),/preserve-existing/);}finally{fs.rmSync(dir,{recursive:true,force:true});}});

const restoreHeader="-- PostgreSQL database dump\nSELECT pg_catalog.set_config('search_path', '', false);\n-- Name: synthetic; Type: TABLE DATA\nCOPY original FROM stdin;\nSELECT pg_catalog.set_config('search_path', '', false);\n\\.\n";
test('restore session header adjustment preserves every factual COPY byte',()=>{const source=Buffer.from(restoreHeader),result=isolatedRestoreSQL(source),at=source.indexOf(Buffer.from('\n-- Name: '));assert.deepEqual(result.subarray(result.indexOf(Buffer.from('\n-- Name: '))),source.subarray(at));assert.match(result.toString(),/public,pg_catalog/);});
test('restore header fails closed on missing or duplicate session setup',()=>{assert.throws(()=>isolatedRestoreSQL(Buffer.from('-- Name: missing')));assert.throws(()=>isolatedRestoreSQL(Buffer.from(restoreHeader.replace('-- PostgreSQL database dump',"SELECT pg_catalog.set_config('search_path', '', false);"))));});
test('local constraint revalidation requires exact immutable original schema',()=>{const schema=fs.readFileSync('postgres/schema.sql');assert.equal(isolatedOriginalChecks(schema).match(/ADD CONSTRAINT/g).length,4);assert.throws(()=>isolatedOriginalChecks(Buffer.concat([schema,Buffer.from(' ')])));});

test('new recovery window and child may track original issue51, retaining released-source and scope guards',()=>{
 const d=delegated();d.w.queue=51;d.spec.production_operation.queue=51;
 d.spec.production_operation.handoff_receipt_url='https://github.com/ChengshuLi/WorldAtlas/issues/51#issuecomment-123';
 d.context.handoffReceipt.html_url=d.spec.production_operation.handoff_receipt_url;
 d.context.reservationIssue.body='<!-- worldatlas-work:v1\n'+JSON.stringify(d.spec)+'\n-->';
 d.w.reservation_scope_sha256=sha(JSON.stringify(d.spec));assert.doesNotThrow(()=>validateDelegated(d));
 d.w.queue=714;assert.throws(()=>validateDelegated(d),/operation-not-publisher-owned/);
});
test('original-issue recovery cannot use unrelated tracking issue',()=>{const w=window();w.queue=22;assert.throws(()=>validate(w),/invalid-publisher-window/);});

test('actual Neon database/default ACLs use same-name isolated target and inert provider roles',()=>{const code=fs.readFileSync('scripts/current-postgres-recovery.mjs','utf8');assert.match(code,/CREATE ROLE cloud_admin NOLOGIN/);assert.match(code,/CREATE ROLE neon_superuser NOLOGIN/);assert.match(code,/CREATE DATABASE neondb OWNER neondb_owner/);assert.match(code,/\['exec','-i',target,'pg_restore','--file=-'\]/);assert.doesNotMatch(code,/'--no-owner','--role'/);});

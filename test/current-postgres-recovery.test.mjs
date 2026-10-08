import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {generateKeyPairSync,createHash} from 'node:crypto';
import {nativeReadbackFailureCode,isolatedFilesystemUsage,loadRecoveryReservation,validateRecoveryWindow,validatedOwnerConnection,assertRestoredInventory,boundedOwnerJSON,runCurrentPostgresRecovery,isolatedDatabaseACLList,isolatedDatabaseACLSQL,isolatedRestoreSQL,isolatedOriginalChecks,verifyRecoveryHosting} from '../scripts/current-postgres-recovery.mjs';
import {backupRecipientFingerprint} from '../scripts/recovery-backup-envelope.mjs';
import {cloudflareFixture} from './fixtures/cloudflare-publication.mjs';
import {storageExportV2Contract,storageExportV2Collections,v2MarkerIdentity} from '../hosted/storage-export-v2-contract.js';
const sha=x=>createHash('sha256').update(x).digest('hex');
const now=Date.parse('2026-10-04T06:00:00Z'),head='a'.repeat(40),toolSHA='b'.repeat(64);
const {publicKey}=generateKeyPairSync('rsa',{modulusLength:3072,publicKeyEncoding:{type:'spki',format:'pem'}});
const claim={active:true,live_work:true,issue_number:51,claim_id:'fixture',worker_id:'fixture-holder',branch:'engineering/fixture',expires_at:new Date(now+3600000).toISOString()};
function window(){const marker={version:2,backend:'postgres',read_only:true,revision:1,contract:storageExportV2Contract,counts:Object.fromEntries(storageExportV2Collections.map(k=>[k,0])),catalog_sha256:storageExportV2Contract.postgres_catalog_sha256,geographic_releases_sha256:'c'.repeat(64),footprint_versions_sha256:'d'.repeat(64)};marker.fingerprint=sha(JSON.stringify(v2MarkerIdentity(marker)));return {version:1,issue:51,queue:714,operator_worker_id:'engineering-central-publication-20261003',primary_main_commit:head,capture_tool_sha256:toolSHA,method:'readonly-native-pg-dump-and-isolated-restore',backup_recipient_public_key:publicKey,backup_recipient_sha256:backupRecipientFingerprint(publicKey),observed_at_utc:new Date(now).toISOString(),expires_at_utc:new Date(now+1800000).toISOString(),claim_id:claim.claim_id,holder_worker_id:claim.worker_id,claim_branch:claim.branch,site:{project_id:'appgprj_6abdf87277c08191bce4a22b8dfb25db',version:24,deployment_id:'appgdep_fixture'},read_only:true,drain_verified:true,restore_writes_operator:'engineering-central-publication-20261003',rollback_receipt_url:'https://github.com/ChengshuLi/WorldAtlas/issues/714',source_marker:marker};}
const validate=(value,c=claim,n=now)=>validateRecoveryWindow(value,c,{head,toolSHA,now:n});
test('accepts only pinned live publisher read window',()=>assert.equal(validate(window()).issue,51));
function cloudflareWindow(){const w=window();delete w.site;w.hosting={kind:'cloudflare',origin:'https://worldatlas-explorer.chengshu-worldatlas.workers.dev',worker_version:'ec1f8278-3e1b-4532-b84b-79241459e54b',deployment_id:100,primary_commit:head,package_inventory_sha256:'e'.repeat(64),acceptance_url:'https://github.com/ChengshuLi/WorldAtlas/issues/849#issuecomment-98',result_url:'https://github.com/ChengshuLi/WorldAtlas/issues/849#issuecomment-99'};w.registry_deployment_id=101;w.operation_id='daeb977a-ac2e-4ac9-b082-5628f91cf16c';return w;}
test('Cloudflare recovery pins actual delivery without fabricated Site identity',()=>assert.doesNotThrow(()=>validate(cloudflareWindow())));
for(const [label,mutate] of [['mixed hosting identities',w=>w.site=window().site],['other provider',w=>w.hosting.kind='other'],['other origin',w=>w.hosting.origin='https://other.invalid'],['missing result',w=>delete w.hosting.result_url],['missing operation',w=>delete w.registry_deployment_id],['unpinned assets',w=>delete w.hosting.package_inventory_sha256]])test('Cloudflare window rejects '+label,()=>{const w=cloudflareWindow();mutate(w);assert.throws(()=>validate(w));});
test('restored compact dictionaries, raw evidence, sequence state and view/function ACLs must all match',()=>{
 const before={identity:{database_name:'neondb'},compact_storage:{physical:{evidence:{ordered_rows_sha256:'raw'}},sequences:{dictionary:{last_value:5,is_called:true}}},permissions:[{object_name:'atlas_geographic_memberships',acl:'SELECT'}],sequence_permissions:[{owner:'neondb_owner',acl:null}],function_permissions:[{owner:'neondb_owner',acl:'private'}]};
 assert.doesNotThrow(()=>assertRestoredInventory(before,structuredClone(before),before));
 for(const mutate of [v=>v.compact_storage.physical.evidence.ordered_rows_sha256='different',v=>v.compact_storage.sequences.dictionary.last_value++,v=>v.permissions[0].acl='INSERT',v=>v.sequence_permissions[0].acl='public',v=>v.function_permissions[0].acl='public']){const value=structuredClone(before);mutate(value);assert.throws(()=>assertRestoredInventory(before,value,before));}
});
test('Cloudflare host mismatch stops verification before any public requests',async()=>{
 let reads=0;await assert.rejects(()=>verifyRecoveryHosting(cloudflareWindow(),async()=>({environment:'other'}),()=>{reads++;throw Error('unexpected');}),/hosting-delivery-registry-mismatch/);assert.equal(reads,0);
});
function hostingFixture(){
 const w=cloudflareWindow(),host=w.hosting;
 const cf=cloudflareFixture({primary:head,worker:host.worker_version});
 host.acceptance_url=cf.url;
 const delivery=cf.deployment;
 const native={id:101,sha:head,environment:'worldatlas-production',task:'worldatlas-publication',payload:{worldatlas_publication:{version:1,operation_id:w.operation_id,publisher_worker_id:w.operator_worker_id,primary_commit:head,kind:'recovery',issues:[51],started_at:w.observed_at_utc,expires_at:w.expires_at_utc,rollback_url:w.rollback_receipt_url}}};
 const result=cf.result;
 const deliveredStatus={id:20,state:'success',log_url:host.result_url},nativeStatus={id:21,state:'in_progress'};
 const data={w,delivery,native,result,deliveredStatus,nativeStatus,extra:[],observed:structuredClone(w.source_marker),mutation:503,requests:[]};
 data.api=async route=>{const url=new URL('https://fixture.invalid'+route),p=url.pathname;if(p.endsWith('/deployments/100'))return delivery;if(p.endsWith('/deployments/100/statuses'))return [deliveredStatus];if(p.endsWith('/deployments/101/statuses'))return [nativeStatus];if(p.endsWith('/deployments'))return [delivery,native,...data.extra];if(p.endsWith('/issues/comments/99'))return cf.receipt();throw Error('unexpected fixture route '+p);};
 data.fetcher=async(url,options)=>{data.requests.push({url,method:options.method??'GET'});return options.method?new Response('',{status:data.mutation}):new Response(JSON.stringify(data.observed));};
 return data;
}
test('actual-delivery registry, fresh marker and all public mutation guards are required at recovery',async()=>{
 const f=hostingFixture(),result=await verifyRecoveryHosting(f.w,f.api,f.fetcher);assert.equal(result.kind,'cloudflare');assert.deepEqual(f.requests.map(row=>row.method),['GET','POST','PUT','PATCH','DELETE']);
});
for(const [label,mutate] of [
 ['unsettled delivery',f=>f.deliveredStatus.state='in_progress'],['wrong result URL',f=>f.deliveredStatus.log_url='https://example.invalid'],['unclean delivery',f=>f.result.cleanup_confirmed=false],['wrong Worker',f=>f.result.worker_version='different'],['changed package',f=>f.delivery.payload.worldatlas_cloudflare.package_inventory_sha256='different'],['wrong recovery operation',f=>f.native.payload.worldatlas_publication.operation_id='other'],['drifted source',f=>f.observed.revision++],['public writes enabled',f=>f.mutation=400],
])test('recovery host verification rejects '+label,async()=>{const f=hostingFixture();mutate(f);await assert.rejects(()=>verifyRecoveryHosting(f.w,f.api,f.fetcher));});
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

test('database ACL selection retains exactly the native same-name owner entry',()=>{
 const row='3991; 0 0 ACL - DATABASE neondb neondb_owner';
 assert.equal(isolatedDatabaseACLList('; Archive TOC\n3990; 1262 16396 DATABASE - neondb neondb_owner\n'+row+'\n4000; 0 0 ACL public TABLE atlas_sources neondb_owner\n'),row+'\n');
 for(const toc of ['',row+'\n'+row,row.replace('neondb neondb_owner','other neondb_owner'),row.replace('neondb_owner','postgres'),row+'\n3992; 0 0 ACL - DATABASE other neondb_owner'])assert.throws(()=>isolatedDatabaseACLList(toc),/unexpected-native-database-acl-toc/);
});

test('database ACL rendering excludes the forced create prelude and rejects unexpected object or statements',()=>{
 const rendered="-- Name: neondb; Type: DATABASE; Schema: -; Owner: neondb_owner\n--\n\nCREATE DATABASE neondb;\nALTER DATABASE neondb OWNER TO neondb_owner;\n\\connect neondb\n-- Name: DATABASE neondb; Type: ACL; Schema: -; Owner: neondb_owner\n--\n\nGRANT ALL ON DATABASE neondb TO neon_superuser;\n\n\n--\n-- PostgreSQL database dump complete\n--\n";
 assert.equal(isolatedDatabaseACLSQL(rendered).toString(),'GRANT ALL ON DATABASE neondb TO neon_superuser;\n');
 for(const x of [rendered.replace('GRANT ALL','CREATE DATABASE other;\nGRANT ALL'),rendered.replace('TO neon_superuser','TO other'),rendered.replace('GRANT ALL','\\connect other\nGRANT ALL'),rendered.replace('Type: ACL','Type: TABLE'),rendered.replace('dump complete','incomplete'),rendered+rendered])assert.throws(()=>isolatedDatabaseACLSQL(x));
});

test('TOC-style early input close reproduces full-size spawnSync EPIPE despite successful child exit',async()=>{const {execFileSync}=await import('node:child_process');assert.throws(()=>execFileSync('head',['-c','10'],{input:Buffer.alloc(22510251),stdio:['pipe','pipe','pipe']}),error=>error.code==='EPIPE'&&error.status===0);});


test('native readback diagnostics retain only fixed process codes or terse SQLSTATE',()=>{
 assert.equal(nativeReadbackFailureCode({stderr:Buffer.from('ERROR:  53100\nprivate-value-do-not-copy')}),'native-query-sqlstate-53100');
 assert.equal(nativeReadbackFailureCode({code:'ENOBUFS',stderr:'private://credentials'}),'native-query-enobufs');
 assert.equal(nativeReadbackFailureCode({stderr:'ERROR: private credential source value'}),'native-query-failed');
 assert.equal(nativeReadbackFailureCode({stderr:'ERROR:  53100private-token'}),'native-query-failed');
 assert.equal(nativeReadbackFailureCode({stderr:'ERROR: TOKEN private-source-value'}),'native-query-failed');
 assert.equal(nativeReadbackFailureCode({stderr:'ERROR: TOKEN'}),'native-query-failed');
});
test('isolated disk readback accepts one bounded mount measurement and rejects malformed or unsafe totals',()=>{
 assert.deepEqual(isolatedFilesystemUsage('Filesystem 1024-blocks Used Available Capacity Mounted on\ntmpfs 3145728 2400000 745728 77% /var/lib/postgresql\n'),{capacity_bytes:3221225472,used_bytes:2457600000,available_bytes:763625472});
 for(const row of ['', 'tmpfs 10 9 2 90% /var/lib/postgresql', 'tmpfs 99999999999999999999 0 0 0% /var/lib/postgresql','tmpfs 10 1 9 10% /other','tmpfs 10 1 9 10% /var/lib/postgresql\ntmpfs 10 1 9 10% /var/lib/postgresql'])assert.throws(()=>isolatedFilesystemUsage(row));
});

/** Manual owner maintenance only, on exact reviewed main and an active publisher
 * reservation. No factual row is deleted; the verified old heap is retired only
 * in a separate phase after a native backup/restore and public API checks. */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {Pool,neonConfig} from '@neondatabase/serverless';
import {readClaim,workSpec,githubAPI,githubPages} from './issue-claim-contract.mjs';
import {expectedNeonProjectId,verifyNeonProject} from './verify-neon-project.mjs';
import {boundedOwnerJSON,validatedOwnerConnection,nativeMembershipDigestSQL} from './current-postgres-recovery.mjs';
import {exportStorageMarkerV2} from '../hosted/storage-export-v2.js';
import {exportStorageMarkerV4} from '../hosted/storage-export-v4.js';
import {compactMembershipCatalog} from '../hosted/membership-storage-profile.js';
import {verifyCompactMembershipRuntime} from './verify-compact-membership-runtime.mjs';
import {originalMembershipAPIPlan,verifyApplicationMembershipAPI} from './verify-live-membership-api-functions.mjs';
import {forwardMigrationDefinitions} from './neon-forward-migrations.mjs';
import {rehearseCompactMembershipStorage,rehearseCompactMembershipRollback,compactMembershipParity} from './compact-membership-storage.mjs';
const repo='ChengshuLi/WorldAtlas',branchId='br-summer-butterfly-ar8qikk5',workflow='.github/workflows/compact-membership-production.yml';
const sha=b=>createHash('sha256').update(b).digest('hex'),need=(v,code)=>{if(!v)throw Error(code);};
const phaseSet=['apply','verify','retire','rollback'];
// DROP removes legacy foreign-key triggers and locks their parent tables until
// COMMIT. A separate application connection cannot read those parents in the
// owner transaction. Keep the oracle/preflight inside, then prove reads outside.
export async function commitMembershipRetirement(engine,{prepare,authorize,onCommitted,afterCommit}){
 const parity=await engine.transaction(async tx=>{
  await tx.query('LOCK TABLE atlas_geographic_memberships,worldatlas_membership_rows,worldatlas_memberships_original_v1 IN SHARE ROW EXCLUSIVE MODE');
  const value=await prepare(tx);
  await authorize('before-drop');
  await tx.query('DROP TABLE worldatlas_memberships_original_v1');
  await authorize('before-commit');
  return value;
 });
 onCommitted(parity); // Persist that DROP committed, even if the later proof fails.
 await afterCommit();
 return parity;
}
export function checkOriginalMembershipIndexes(indexes){
 const expected={geographic_membership_page:'(release_id, active, entity_id)',geographic_membership_parent:'(release_id, active, parent_id, entity_id)'};
 need([1,2,3].includes(indexes.length),'unknown-original-index-inventory');
 for(const row of indexes){const definition=row.indexdef.replaceAll('"','').replace(/\s+/g,' ');
  if(row.indexname==='atlas_geographic_memberships_pkey')need(definition==='CREATE UNIQUE INDEX atlas_geographic_memberships_pkey ON public.atlas_geographic_memberships USING btree (release_id, entity_id)','changed-original-primary-key');
  else need(Object.hasOwn(expected,row.indexname)&&definition==='CREATE INDEX '+row.indexname+' ON public.atlas_geographic_memberships USING btree '+expected[row.indexname],'changed-original-membership-index');
 }
 need(indexes.some(x=>x.indexname==='atlas_geographic_memberships_pkey'),'missing-original-primary-key');
 return Object.keys(expected).filter(name=>!indexes.some(x=>x.indexname===name));
}
export async function restoreOriginalMembershipIndexes(engine,logicalBytes){
 const inventory=async()=>(await engine.query("SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='public' AND tablename='atlas_geographic_memberships' ORDER BY indexname")).rows;
 const missing=checkOriginalMembershipIndexes(await inventory());
 if(missing.length){
  const increment=missing.reduce((sum,name)=>sum+(name==='geographic_membership_parent'?162332672:122675200),0);
  need(Number.isSafeInteger(logicalBytes)&&logicalBytes+increment+32*1024**2<=1024**3,'original-index-rebuild-headroom-insufficient');
  const original=fs.readFileSync('postgres/schema.sql','utf8');need(sha(original)==='1a43333772e6059d4fa97ce60baad7a27239616693c86708d08eadbc73b97618','unreviewed-original-index-source');
  const statements=original.split('\n').filter(x=>/^CREATE INDEX "geographic_membership_(parent|page)" /.test(x));need(statements.length===2,'missing-original-index-definitions');
  await engine.transaction(async tx=>{await tx.query('LOCK TABLE atlas_geographic_memberships IN SHARE ROW EXCLUSIVE MODE');for(const sql of statements){const name=/CREATE INDEX "([^"]+)"/.exec(sql)[1];if(missing.includes(name))await tx.query(sql);}});
 }
 const restored=await inventory();need(checkOriginalMembershipIndexes(restored).length===0,'original-index-rebuild-incomplete');return {status:'original-indexes-restored',indexes:restored};
}
export function validateCompactProductionWindow(window,claim,issue,{head,toolSHA,now=Date.now(),phase='start'}={}){
 need(window?.version===1&&window.source_issue===783&&phaseSet.includes(window.phase)&&Number.isSafeInteger(window.reservation_issue)&&window.reservation_issue>783,'invalid-compact-window');
 need(claim?.active&&claim.mode==='engineering'&&claim.live_work&&claim.issue_number===window.reservation_issue&&claim.claim_id===window.claim_id&&claim.worker_id===window.operator_worker_id&&claim.branch===window.claim_branch&&Date.parse(claim.expires_at)>now,'inactive-compact-owner-claim');
 need(window.primary_main_commit===head&&window.tool_sha256===toolSHA,'unreviewed-compact-tool');
 const time=Date.parse(window.observed_at_utc),expires=Date.parse(window.expires_at_utc);need(time<=now&&(phase==='end'||now-time<=10*60000)&&expires>now&&expires-time<=60*60000,'stale-compact-window');
 const spec=workSpec(issue.body),operation=spec.production_operation;
 need(issue.number===window.reservation_issue&&issue.state==='open'&&spec.mode==='engineering'&&operation?.source_issue===783&&operation.publisher_worker_id===window.operator_worker_id&&sha(JSON.stringify(spec))===window.reservation_scope_sha256,'changed-compact-operation-scope');
 need(window.read_only===true&&window.drain_verified===true&&window.site?.project_id==='appgprj_6abdf87277c08191bce4a22b8dfb25db'&&Number.isSafeInteger(window.site.version)&&typeof window.site.deployment_id==='string'&&window.site.deployment_id.startsWith('appgdep_'),'undrained-compact-site');
 need(Number.isSafeInteger(window.backup?.run_id)&&/^[a-f0-9]{64}$/.test(window.backup.dump_sha256??'')&&/^[a-f0-9]{64}$/.test(window.backup.source_fingerprint??'')&&window.backup.private_recipient_decryption_verified===true,'missing-verified-native-backup');
 need(Number.isSafeInteger(window.registry_deployment_id)&&window.registry_deployment_id>0&&typeof window.operation_id==='string'&&window.operation_id.length>=16,'unregistered-compact-operation');
 if(window.database_only===true)need(operation.database_only===true&&window.site_deployment_postponed===true&&window.public_api_parity_verified!==true,'unreviewed-database-only-maintenance');
 if(window.phase==='retire')need(window.native_backup_preserved===true&&(window.public_api_parity_verified===true||window.database_only===true),'unverified-compact-retirement');
 return window;
}
const sizeSQL="SELECT pg_database_size(current_database())::bigint database_bytes,(SELECT coalesce(sum(pg_total_relation_size(c.oid)),0)::bigint FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r') relation_bytes";
export async function runCompactMembershipProduction({env=process.env,fetcher=fetch,output='data/validation/compact-membership-production'}={}){
 need(!fs.existsSync(output),'preserve-existing-compact-output');fs.mkdirSync(output,{recursive:true,mode:0o700});
 const receipt={version:1,status:'failed',started_at_utc:new Date().toISOString(),facts_removed:0},file=path.join(output,'receipt.json');let pool,client,appPool,appClient,stage='authorize',locked=false,ownerGet,ownerEngine;
 const secrets=[env.NEON_API_KEY,env.GITHUB_TOKEN];const save=()=>{const text=JSON.stringify(receipt,null,2)+'\n';need(!secrets.some(x=>x&&text.includes(x)),'unsafe-compact-receipt');fs.writeFileSync(file,text,{mode:0o600});};
 try{
  need(env.GITHUB_EVENT_NAME==='workflow_dispatch'&&env.GITHUB_REPOSITORY===repo&&env.GITHUB_WORKFLOW_REF===repo+'/'+workflow+'@refs/heads/main'&&/^[1-9]\d*$/.test(env.WINDOW_COMMENT_ID??'')&&env.NEON_PROJECT_ID===expectedNeonProjectId,'trusted-manual-main-required');
  const api=githubAPI(env.GITHUB_TOKEN),comment=await api('/repos/'+repo+'/issues/comments/'+env.WINDOW_COMMENT_ID);
  need(comment.user?.type==='User'&&comment.user.login===env.GITHUB_ACTOR&&['OWNER','MEMBER','COLLABORATOR'].includes(comment.author_association),'unauthorized-compact-publisher');
  const blocks=[...String(comment.body).matchAll(/<!-- worldatlas-compact-window:v1\n([\s\S]*?)\n-->/g)];need(blocks.length===1,'unique-compact-window-required');const requested=JSON.parse(blocks[0][1]);
  const freshReservation=async()=>{const issue=await api('/repos/'+repo+'/issues/'+requested.reservation_issue),claim=readClaim(await githubPages(api,'/repos/'+repo+'/issues/'+requested.reservation_issue+'/comments'));const spec=workSpec(issue.body);for(const id of spec.depends_on)need((await api('/repos/'+repo+'/issues/'+id)).state==='closed','unfinished-compact-dependency');return {claim,issue};};
  const {claim,issue}=await freshReservation(),window=validateCompactProductionWindow(requested,claim,issue,{head:env.GITHUB_SHA,toolSHA:sha(fs.readFileSync(fileURLToPath(import.meta.url)))});
  need(comment.html_url==='https://github.com/'+repo+'/issues/783#issuecomment-'+comment.id,'wrong-compact-tracking-issue');
  const deployment=await api('/repos/'+repo+'/deployments/'+window.registry_deployment_id),registered=deployment.payload?.worldatlas_publication;
  need(deployment.environment==='worldatlas-production'&&deployment.task==='worldatlas-publication'&&registered?.kind==='recovery'&&registered.operation_id===window.operation_id&&registered.publisher_worker_id===window.operator_worker_id&&registered.primary_commit===env.GITHUB_SHA,'registry-compact-mismatch');
  for(const record of await githubPages(api,'/repos/'+repo+'/deployments?environment=worldatlas-production')){
   const statuses=await githubPages(api,'/repos/'+repo+'/deployments/'+record.id+'/statuses');
   const status=statuses[0]?.state;
   if(record.id===window.registry_deployment_id)need(status==='in_progress','compact-operation-not-running');
   else need(['success','failure','inactive'].includes(status),'overlapping-unsettled-production-operation');
  }
  const backupRun=await api('/repos/'+repo+'/actions/runs/'+window.backup.run_id);need(backupRun.conclusion==='success'&&backupRun.event==='workflow_dispatch'&&backupRun.path==='.github/workflows/current-postgres-recovery.yml'&&backupRun.head_branch==='main','native-backup-run-unverified');
  receipt.window_comment_id=comment.id;receipt.phase=window.phase;receipt.operation_id=window.operation_id;receipt.backup=window.backup;receipt.main=env.GITHUB_SHA;receipt.run_id=env.GITHUB_RUN_ID;save();
  stage='owner-connection';receipt.project=await verifyNeonProject({apiKey:env.NEON_API_KEY,projectId:expectedNeonProjectId,fetchImpl:fetcher});need(receipt.project.branch.id===branchId&&receipt.project.project.configured_postgres_major===18,'changed-production-neon');
  const get=async suffix=>boundedOwnerJSON(await fetcher('https://console.neon.tech/api/v2/projects/'+expectedNeonProjectId+suffix,{headers:{Authorization:'Bearer '+env.NEON_API_KEY},redirect:'error',signal:AbortSignal.timeout(15000)}));
  ownerGet=get;
  const endpoints=(await get('/endpoints')).endpoints.filter(e=>e.branch_id===branchId&&e.type==='read_write');need(endpoints.length===1,'ambiguous-owner-endpoint');
  const uri=(await get('/connection_uri?'+new URLSearchParams({branch_id:branchId,database_name:'neondb',role_name:'neondb_owner',pooled:'false'}))).uri,connection=validatedOwnerConnection(uri,endpoints[0].host);secrets.push(uri,connection.password);
  neonConfig.webSocketConstructor=WebSocket;pool=new Pool({connectionString:uri,max:1,connectionTimeoutMillis:15000});pool.on('error',()=>{});client=await pool.connect();await client.query("SET statement_timeout='20min'; SET lock_timeout='5s'");
  need((await client.query('SELECT pg_try_advisory_lock(807245315,1) locked')).rows[0].locked===true,'shared-owner-lock-unavailable');locked=true;
  const query=async(sql,args)=>{const result=await client.query(sql,args);if(result?.rows&&result.fields){for(const field of result.fields.filter(x=>x.dataTypeID===20))for(const row of result.rows)if(row[field.name]!==null){const value=Number(row[field.name]);need(Number.isSafeInteger(value),'unsafe-owner-int8-result');row[field.name]=value;}}return result;};
  const tx={query,exec:sql=>client.query(sql)};
  const engine={query:tx.query,transaction:async fn=>{await client.query('BEGIN');try{const value=await fn(tx);await client.query('COMMIT');return value;}catch(error){await client.query('ROLLBACK');throw error;}}};
  ownerEngine=engine;
  const db={dialect:'postgres',prepare:sql=>({all:async()=>({results:(await query(sql)).rows}),first:async()=>(await query(sql)).rows[0]??null})};
  const appProof=async plan=>{
   if(!appClient){
    const appURI=(await get('/connection_uri?'+new URLSearchParams({branch_id:branchId,database_name:'neondb',role_name:'worldatlas_app',pooled:'false'}))).uri;
    let parsed;try{parsed=new URL(appURI);}catch{throw Error('invalid-application-proof-connection');}
    need(['postgres:','postgresql:'].includes(parsed.protocol)&&parsed.hostname===endpoints[0].host&&!parsed.port&&!parsed.hash&&decodeURIComponent(parsed.username)==='worldatlas_app'&&decodeURIComponent(parsed.pathname)==='/neondb'&&parsed.password&&parsed.searchParams.get('sslmode')==='require','unexpected-application-proof-connection');
    secrets.push(appURI,parsed.password,decodeURIComponent(parsed.password));
    appPool=new Pool({connectionString:appURI,max:1,connectionTimeoutMillis:15000});appPool.on('error',()=>{});appClient=await appPool.connect();
   }
   await appClient.query("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY; SET LOCAL statement_timeout='60s'; SET LOCAL lock_timeout='5s'");
   try{const proof=await verifyApplicationMembershipAPI((sql,args)=>appClient.query(sql,args),plan);await appClient.query('COMMIT');return proof;}
   catch(error){await appClient.query('ROLLBACK');throw error;}
  };
  receipt.before=(await query(sizeSQL)).rows[0];receipt.rows_before=(await query(nativeMembershipDigestSQL())).rows[0];save();
  if(window.phase==='apply'){
   stage='original-preflight';const marker=await exportStorageMarkerV2(db);need(marker.fingerprint===window.backup.source_fingerprint,'original-snapshot-changed-since-backup');
   need(receipt.rows_before.rows===window.expected_memberships&&receipt.rows_before.rows<=600000,'unreviewed-production-row-count');
   const indexes=(await client.query("SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='public' AND tablename='atlas_geographic_memberships' ORDER BY indexname")).rows;
   receipt.missing_original_indexes=checkOriginalMembershipIndexes(indexes);
   stage='committed-reconstructable-index-drop';receipt.index_drop_started=true;save();await engine.transaction(async tx=>{await tx.query('LOCK TABLE atlas_geographic_memberships IN SHARE ROW EXCLUSIVE MODE');await tx.query('DROP INDEX IF EXISTS geographic_membership_page');await tx.query('DROP INDEX IF EXISTS geographic_membership_parent');});receipt.original_indexes_dropped=true;receipt.after_index_drop=(await query(sizeSQL)).rows[0];save();
   stage='provider-headroom';let logical;for(let attempt=0;attempt<12;attempt++){const branch=(await get('/branches/'+branchId)).branch;logical=branch.logical_size;need(Number.isSafeInteger(logical)&&logical>=0,'missing-provider-logical-size');if(logical+232*1024**2<=1024**3)break;await new Promise(resolve=>setTimeout(resolve,5000));}
   receipt.provider_before_copy_bytes=logical;need(logical+232*1024**2<=1024**3,'actual-provider-headroom-insufficient');save();
   stage='compact-copy-and-switch';receipt.copy=await rehearseCompactMembershipStorage(engine,{copyOnServer:true,afterSwitch:async tx=>{await verifyCompactMembershipRuntime({query:tx.query},forwardMigrationDefinitions.slice(0,2));const current=await freshReservation();validateCompactProductionWindow(window,current.claim,current.issue,{head:env.GITHUB_SHA,toolSHA:sha(fs.readFileSync(fileURLToPath(import.meta.url))),phase:'end'});}});receipt.runtime=await verifyCompactMembershipRuntime({query:tx.query},forwardMigrationDefinitions.slice(0,2));
   if(window.database_only===true){stage='actual-application-api-functions';receipt.api_function_parity=await appProof(await originalMembershipAPIPlan(query));}
  }else if(window.phase==='rollback'){
   stage='original-rollback';const kind=(await query("SELECT relkind FROM pg_class WHERE oid='public.atlas_geographic_memberships'::regclass")).rows[0]?.relkind;
   if(kind==='v')receipt.rollback=await rehearseCompactMembershipRollback(engine);else need(kind==='r','unknown-membership-rollback-state');
   const logical=(await get('/branches/'+branchId)).branch.logical_size;receipt.original_index_recovery=await restoreOriginalMembershipIndexes(engine,logical);
  }else{
   stage='compact-preflight';const profile=await compactMembershipCatalog(db);need(profile.base_version===2,'unsupported-live-forward-base');receipt.profile=profile.profile;
   if(window.phase==='retire'){
    need(profile.profile==='retained-original','original-heap-not-retained');
    let plan;
    receipt.parity=await commitMembershipRetirement(engine,{
     prepare:async tx=>{
      stage='full-original-parity-before-retirement';
      await verifyCompactMembershipRuntime({query:tx.query},forwardMigrationDefinitions.slice(0,2));
      const current=await freshReservation();validateCompactProductionWindow(window,current.claim,current.issue,{head:env.GITHUB_SHA,toolSHA:sha(fs.readFileSync(fileURLToPath(import.meta.url))),phase:'end'});
      const value=await compactMembershipParity(tx);
      if(window.database_only===true){
       stage='application-api-before-retirement';plan=await originalMembershipAPIPlan(tx.query);
       receipt.api_function_parity_before_retirement=await appProof(plan);
       need(receipt.api_function_parity_before_retirement.status==='verified','unverified-runtime-api-retirement');
      }
      return value;
     },
     authorize:async point=>{
      stage='retirement-'+point;
      const current=await freshReservation();validateCompactProductionWindow(window,current.claim,current.issue,{head:env.GITHUB_SHA,toolSHA:sha(fs.readFileSync(fileURLToPath(import.meta.url))),phase:'end'});
      if(point==='before-drop'){receipt.retirement_drop_started=true;receipt.retirement_outcome='unconfirmed';save();}
     },
     onCommitted:parity=>{receipt.parity=parity;receipt.original_heap_retired=true;receipt.retirement_outcome='committed';stage='application-api-after-retirement-commit';save();},
     afterCommit:async()=>{if(plan)receipt.api_function_parity_after_retirement=await appProof(plan);}
    });
   }
   if(window.phase!=='rollback')receipt.runtime=await verifyCompactMembershipRuntime({query:tx.query},forwardMigrationDefinitions.slice(0,2));
  }
  stage='full-after-verification';receipt.rows_after=(await query(nativeMembershipDigestSQL())).rows[0];need(JSON.stringify(receipt.rows_before)===JSON.stringify(receipt.rows_after),'production-raw-membership-digest-changed');receipt.after=(await query(sizeSQL)).rows[0];
  if(window.phase!=='rollback'){const marker=await exportStorageMarkerV4(db);receipt.after_marker=marker;}
  receipt.provider_after_bytes=(await get('/branches/'+branchId)).branch.logical_size;
  if(window.phase==='retire'||window.phase==='verify'&&receipt.profile==='compact-only')need(receipt.after.database_bytes<800000000&&Number.isSafeInteger(receipt.provider_after_bytes)&&receipt.provider_after_bytes<800000000,'compact-final-budget-not-yet-verified');
  const final=await freshReservation();validateCompactProductionWindow(window,final.claim,final.issue,{head:env.GITHUB_SHA,toolSHA:sha(fs.readFileSync(fileURLToPath(import.meta.url))),phase:'end'});receipt.status='verified';
 }catch(error){
  if(receipt.phase==='apply'&&receipt.index_drop_started&&ownerEngine&&ownerGet){
   try{const kind=(await ownerEngine.query("SELECT relkind FROM pg_class WHERE oid='public.atlas_geographic_memberships'::regclass")).rows[0]?.relkind;
    if(kind==='r')receipt.original_index_recovery=await restoreOriginalMembershipIndexes(ownerEngine,(await ownerGet('/branches/'+branchId)).branch.logical_size);
    else receipt.original_index_recovery={status:'compact-switch-committed; use verified explicit rollback before retirement'};
   }catch{receipt.original_index_recovery={status:'unsettled; original facts retained, measured index restoration or apply retry required'};}
  }
  if(receipt.phase==='retire'&&receipt.retirement_drop_started&&receipt.original_heap_retired!==true)receipt.retirement_outcome='unconfirmed; read-only catalog verification required';
  receipt.failure_stage=stage;if(/^[0-9A-Z]{5}$/.test(error.code??''))receipt.sqlstate=error.code;receipt.error_code=/^[a-z0-9-]{1,100}$/.test(error.message)?error.message:'compact-production-operation-failed';}
 finally{
  if(appClient)appClient.release();if(appPool)await appPool.end();
  if(client){if(locked)try{receipt.lock_released=(await client.query('SELECT pg_advisory_unlock(807245315,1) unlocked')).rows[0].unlocked===true;}catch{receipt.lock_released=false;}client.release();}if(pool)await pool.end();if(locked&&!receipt.lock_released)receipt.status='failed';receipt.completed_at_utc=new Date().toISOString();receipt.limits=['Database-only windows verify pinned original API functions through an actual readonly application login, never claim deployed HTTP delivery or restored writes.','Live Site read-only/drain/API parity and private backup recipient recovery are authenticated publisher attestations; Actions verifies the successful native recovery run and source fingerprint.','Before retirement, rollback requires no new writes; after verified old heap retirement, disaster restoration uses the preserved original native backup in an isolated/provider-approved target.','Provider logical accounting may lag relation changes; failed capacity verification requires a subsequent verify, not deletion of factual rows.'];save();
 }
 return receipt;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){try{const receipt=await runCompactMembershipProduction();console.log(JSON.stringify({status:receipt.status,phase:receipt.phase,before:receipt.before,after:receipt.after,failure_stage:receipt.failure_stage,error_code:receipt.error_code}));if(receipt.status!=='verified')process.exitCode=1;}catch{console.error('Compact owner maintenance unavailable; retain receipts');process.exitCode=1;}}

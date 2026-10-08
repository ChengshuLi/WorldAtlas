import {readPublicationState,ghReadAPI} from './publication-plan.mjs';
import {validateCloudflareOperation,cloudflareOrigin,runtimePinFields} from './publication-cloudflare.mjs';
import {githubPages,readClaim,workSpec,activeIssueBlockers} from './issue-claim-contract.mjs';
import {validateIssueMetadata} from './check-handoff-scope.mjs';
import {checkedStorageV4Contract,v4MarkerIdentity} from '../hosted/storage-export-v4-contract.js';
import {createHash} from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const need=(value,message)=>{if(!value)throw Error(message);};
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const root='/repos/ChengshuLi/WorldAtlas';
function liveReservation(issue,comments,op,now){
 const spec=workSpec(issue.body),claim=readClaim(comments),labels=(issue.labels??[]).map(label=>label.name??label);
 validateIssueMetadata(op.claim_branch,issue);
 need(issue.number===op.reservation_issue&&issue.state==='open'&&spec.mode==='engineering'&&labels.includes('status:ready')&&!labels.includes('status:blocked')&&labels.filter(label=>label.startsWith('kind:')).join() === 'kind:work-item'&&!activeIssueBlockers(comments).length,'Unreviewed or blocked live acceptance issue');
 const scopeHash=createHash('sha256').update(JSON.stringify(spec)).digest('hex');
 need(claim?.active&&claim.live_work===true&&claim.issue_number===issue.number&&claim.mode==='engineering'&&claim.worker_id===op.worker_id&&claim.claim_id===op.claim_id&&claim.branch===op.claim_branch&&Date.parse(claim.expires_at)>now&&scopeHash===op.reservation_scope_sha256,'Unconfirmed own live acceptance reservation');
 return {spec,scopeHash,claimExpires:Date.parse(claim.expires_at)};
}
async function closedDependencies(api,spec){
 const dependencies=await Promise.all(spec.depends_on.map(issue=>api(root+'/issues/'+issue)));
 need(spec.depends_on.every(id=>dependencies.some(issue=>issue.number===id&&issue.state==='closed'&&!issue.pull_request)),'Acceptance dependency reopened or missing');
}
async function boundedJSON(response){
 need(response.status===200,'Provider/read verification failed');
 const reader=response.body.getReader();let bytes=0;const chunks=[];
 try{for(;;){const {value,done}=await reader.read();if(done)break;bytes+=value.byteLength;need(bytes<=2*1024*1024,'Provider/read response exceeds bound');chunks.push(Buffer.from(value));}}
 finally{await reader.cancel().catch(()=>{});reader.releaseLock();}
 try{return JSON.parse(Buffer.concat(chunks).toString('utf8'));}catch{throw Error('Provider/read body is not valid JSON');}
}
export async function runRepublish(config,options={}){
 need(typeof config.output==='string'&&path.isAbsolute(config.output),'Absolute fresh output directory required');
 let parent=path.dirname(config.output);
 for(;;){need(!(await fs.lstat(parent)).isSymbolicLink(),'Symlink output parent refused');const next=path.dirname(parent);if(next===parent)break;parent=next;}
 await fs.mkdir(config.output,{recursive:false});
 try{
  const result=await republishCurrentVersion({...config,api:ghReadAPI,...options});
  await fs.writeFile(path.join(config.output,'provider-deployment.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx',mode:0o600});
  return {output:config.output,provider_deployment_id:result.provider_after.id,worker_version:result.worker_version,delivery_settled:false};
 }catch(error){
  await fs.writeFile(path.join(config.output,'failure.json'),JSON.stringify({state:'not-settled',at:new Date().toISOString(),message:'Publication did not complete. Reconcile actual provider/registry state before retry; no settlement is inferred.'})+'\n',{flag:'wx',mode:0o600});
  throw error;
 }
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
 try{
  let input='';for await(const chunk of process.stdin){input+=chunk;need(Buffer.byteLength(input)<=65536,'Configuration exceeds admitted bound');}
  let config;try{config=JSON.parse(input);}catch{throw Error('Configuration is not valid JSON');}
  console.log(JSON.stringify(await runRepublish(config)));
 }catch{console.error('Publication not completed. Preserve the failed run and reconcile actual provider/registry state before retry.');process.exitCode=1;}
}
/** A bounded real deployment of the *current* immutable version. This proves the
 * migrated publisher path without advancing held application/geography changes.
 * New code releases still use the reviewed build/upload procedure in the handoff.
 * The caller registers the operation first and settles it only after served checks.
 */
export async function republishCurrentVersion({deployment_id,api,account_id,api_token,fetcher=fetch,now=Date.now}){
 need(Number.isSafeInteger(deployment_id)&&deployment_id>0&&/^[a-f0-9]{32}$/.test(account_id??'')&&typeof api_token==='string'&&api_token.length>0,'Missing authorized publication inputs');
 const deployment=await api(root+'/deployments/'+deployment_id),op=validateCloudflareOperation(deployment);
 need(!op.legacy&&op.kind==='cloudflare'&&op.publish_method==='republish-current-version'&&op.expected_worker_version===op.rollback_worker_version,'Only an explicit unchanged-version publication is supported');
 const expiry=Date.parse(op.expires_at);
 need(now()>=Date.parse(op.started_at)&&expiry-now()>=120000,'Publication window is expired or too short');
 need(Number.isSafeInteger(op.reservation_issue)&&op.issues.includes(op.reservation_issue),'Missing own acceptance reservation');
 const issue=await api(root+'/issues/'+op.reservation_issue);
 const {spec,scopeHash}=liveReservation(issue,await githubPages(api,root+'/issues/'+op.reservation_issue+'/comments'),op,now());
 await closedDependencies(api,spec);
 const state=await readPublicationState(api);
 need(state.unsettled.length===1&&state.unsettled[0].deployment_id===deployment_id&&state.unsettled[0].operation_id===op.operation_id,'Overlapping or unregistered publication');
 const statuses=await githubPages(api,root+'/deployments/'+deployment_id+'/statuses');
 need(statuses.sort((a,b)=>b.id-a.id)[0]?.state==='in_progress','Publication must be explicitly in progress');
 const delivered=state.cloudflare_delivery;
 need(delivered?.primary_commit===op.primary_commit&&delivered.package_inventory_sha256===op.package_inventory_sha256&&delivered.cloudflare.worker_version===op.expected_worker_version,'Current delivered code/package identity differs');
 if(!delivered.historical)need(runtimePinFields.every(field=>delivered[field]===op[field])&&delivered.release_id===op.release_id,'Current delivered runtime pins differ');
 const headers={Authorization:'Bearer '+api_token};
 const endpoint='https://api.cloudflare.com/client/v4/accounts/'+account_id+'/workers/scripts/worldatlas-explorer/deployments';
 const request=(url,options={})=>fetcher(url,{...options,redirect:'error',signal:AbortSignal.timeout(30000)});
 const providerBefore=await boundedJSON(await request(endpoint,{headers}));
 need(providerBefore.success===true&&Array.isArray(providerBefore.result?.deployments),'Missing actual provider deployment inventory');
 const before=providerBefore.result.deployments[0];
 need(before?.versions?.length===1&&before.versions[0].version_id===op.expected_worker_version&&before.versions[0].percentage===100,'Actual provider no longer serves the pinned current version');
 const marker=await boundedJSON(await request(cloudflareOrigin+'/api/storage/v4/export-marker'));
 checkedStorageV4Contract(marker?.contract);
 const collections=Object.keys(marker.contract.base_contract.definitions).sort();
 need(marker.version===4&&Number.isSafeInteger(marker.revision)&&marker.revision>=0&&marker.counts&&same(Object.keys(marker.counts).sort(),collections)&&collections.every(key=>Number.isSafeInteger(marker.counts[key])&&marker.counts[key]>=0)&&['geographic_releases_sha256','footprint_versions_sha256','catalog_sha256'].every(key=>/^[a-f0-9]{64}$/.test(marker[key]??'')),'Incomplete compact PostgreSQL marker');
 need(createHash('sha256').update(JSON.stringify(v4MarkerIdentity(marker))).digest('hex')===marker.fingerprint,'Compact PostgreSQL marker fingerprint does not match its actual contract/counters');
 need(marker.backend==='postgres'&&marker.read_only===true&&marker.fingerprint===op.source_fingerprint&&marker.catalog_sha256===op.catalog_sha256,'Current compact PostgreSQL marker differs');
 const release=await boundedJSON(await request(cloudflareOrigin+'/api/geography/release'));
 need(release.status==='published'&&release.id===op.release_id&&release.hierarchy_sha256===op.hierarchy_sha256&&release.footprints_sha256===op.footprint_sha256,'Published release differs from package pins');
 for(const method of ['POST','PUT','PATCH','DELETE']){
  const guard=await request(cloudflareOrigin+'/api/records/import',{method});
  need(guard.status===503,'Public writes are not blocked');await guard.body?.cancel();
 }
 // Refresh cooperative serialization and ownership immediately before the only
 // provider mutation. Earlier readonly probes are not an ongoing reservation.
 const finalRegistered=await api(root+'/deployments/'+deployment_id);
 need(same(finalRegistered.payload.worldatlas_cloudflare,deployment.payload.worldatlas_cloudflare),'Registered operation changed during checks');
 const finalState=await readPublicationState(api);
 need(finalState.unsettled.length===1&&finalState.unsettled[0].deployment_id===deployment_id&&finalState.unsettled[0].operation_id===op.operation_id,'Another operation began during checks');
 need(same(finalState.operation_ids,state.operation_ids)&&same(finalState.cloudflare_delivery,delivered),'Registry history or current delivery changed during checks');
 const finalStatuses=await githubPages(api,root+'/deployments/'+deployment_id+'/statuses');
 need(finalStatuses.sort((a,b)=>b.id-a.id)[0]?.state==='in_progress','Publication is no longer explicitly in progress');
 const finalIssue=await api(root+'/issues/'+op.reservation_issue);
 const finalReservation=liveReservation(finalIssue,await githubPages(api,root+'/issues/'+op.reservation_issue+'/comments'),op,now());
 need(finalReservation.scopeHash===scopeHash,'Acceptance reservation changed during checks');
 await closedDependencies(api,finalReservation.spec);
 const finalProvider=await boundedJSON(await request(endpoint,{headers}));
 const immediatelyBefore=finalProvider.result?.deployments?.[0];
 need(finalProvider.success===true&&immediatelyBefore?.id===before.id&&same(immediatelyBefore.versions,before.versions),'Provider changed during checks; preserve the newly serving version');
 need(Math.min(expiry,finalReservation.claimExpires)-now()>=60000,'Insufficient remaining publication or reservation time');
 // Never force or upload/replace code, bindings, secrets or storage. The provider
 // creates a new deployment referencing exactly the existing immutable version.
 const payload={strategy:'percentage',versions:[{version_id:op.expected_worker_version,percentage:100}],annotations:{'workers/message':'WorldAtlas tracked unchanged-version publication '+op.operation_id}};
 const created=await boundedJSON(await request(endpoint,{method:'POST',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify(payload)}));
 need(created.success===true&&/^[a-f0-9-]{36}$/.test(created.result?.id??''),'Provider deployment not confirmed; read back before retry');
 const providerAfter=await boundedJSON(await request(endpoint,{headers})),after=providerAfter.result?.deployments?.[0];
 need(providerAfter.success===true&&after?.id===created.result.id&&same(after.versions,payload.versions)&&now()<expiry,'Created deployment not confirmed by actual provider readback');
 return {version:1,method:op.publish_method,registry_deployment_id:deployment_id,operation_id:op.operation_id,primary_commit:op.primary_commit,provider_before:before,provider_after:after,worker_version:op.expected_worker_version,code_unchanged:true,storage_unchanged:true,public_mutations_blocked:true,delivery_settled:false,limits:['Provider deployment is verified; caller must still check served frontend/assets/API and record the authorized result and cleanup. An uncertain POST must be reconciled from actual provider history before retry.']};
}

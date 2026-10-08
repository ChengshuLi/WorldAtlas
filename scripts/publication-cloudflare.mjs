import fs from 'node:fs';
import {createHash} from 'node:crypto';

const repo='ChengshuLi/WorldAtlas';
export const cloudflareOrigin='https://worldatlas-explorer.chengshu-worldatlas.workers.dev';
export const cloudflareEnvironment='worldatlas-cloudflare-public';
const need=(value,message)=>{if(!value)throw Error(message);};
const hex=(value,length)=>new RegExp('^[a-f0-9]{'+length+'}$').test(value??'');
const uuid=value=>/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(value??'');
const positive=value=>Number.isSafeInteger(value)&&value>0;
const evidence=url=>typeof url==='string'&&url.startsWith('https://github.com/'+repo+'/');
const trusted=comment=>comment?.user?.type==='User'&&['OWNER','MEMBER','COLLABORATOR'].includes(comment.author_association);
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
function canonical(value){
 const ordered=v=>Array.isArray(v)?v.map(ordered):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,ordered(v[k])])):v;
 return JSON.stringify(ordered(value));
}
// This is a bounded, reviewed compatibility inventory, not an editable bootstrap.
// Capture and consume the same bytes; drift rejects before reading provider records.
const historyBytes=fs.readFileSync(new URL('../coordination/publication/cloudflare-history.json',import.meta.url));
need(hash(historyBytes)==='f71fa8429944d5e8d9d358d3960c6b18448b7cdc08cc8149248cd0d0cac4575a','Historical Cloudflare compatibility inventory changed');
const history=JSON.parse(historyBytes);
need(history.version===1&&history.records.length===7&&new Set(history.records.map(r=>r.deployment_id)).size===7,'Incomplete Cloudflare history inventory');
const legacy=new Map(history.records.map(row=>[row.deployment_id,row]));
export const runtimePinFields=['package_inventory_sha256','worker_sha256','config_sha256','assets_sha256','lookup_sha256','hierarchy_sha256','footprint_sha256','catalog_sha256','source_fingerprint'];
export function validateCloudflareDelivery(value){
 need(value?.version===1&&value.provider==='cloudflare'&&hex(value.primary_commit,40),'Missing Cloudflare primary identity');
 need(value.site===undefined&&value.source_commit===undefined&&!value.historical,'Cloudflare delivery cannot fabricate a Site/mirror or historical exception');
 const host=value.cloudflare;
 need(host?.origin===cloudflareOrigin&&uuid(host.worker_version)&&uuid(host.deployment_id)&&positive(host.registry_deployment_id),'Missing actual Cloudflare provider/registry identity');
 need(typeof value.release_id==='string'&&value.release_id.length>0&&runtimePinFields.every(field=>hex(value[field],64)),'Missing Cloudflare release/lookup/backend/package pins');
 need(value.backend==='postgres'&&value.read_only===true&&value.public_reads===true&&value.database_writes===false,'Cloudflare delivery must preserve public read-only PostgreSQL');
 need(Array.isArray(value.evidence_urls)&&value.evidence_urls.length>0&&value.evidence_urls.every(evidence),'Missing Cloudflare delivery evidence');
 return value;
}
export function validateCloudflareOperation(deployment){
 const op=deployment.payload?.worldatlas_cloudflare,old=legacy.get(deployment.id);
 need(op?.version===1&&uuid(op.operation_id)&&typeof op.worker_id==='string'&&op.worker_id.length>0&&hex(deployment.sha,40)&&op.primary_commit===deployment.sha,'Malformed Cloudflare operation identity');
 if(old){
  need(deployment.environment===old.environment&&deployment.task===old.task&&deployment.sha===old.primary_commit&&hash(canonical(deployment.payload))===old.payload_sha256,'Historical Cloudflare operation drift');
  const issues=op.issues??[op.issue];
  need(canonical(issues)===canonical(old.originating_issues),'Historical Cloudflare originating scope changed');
  return {...op,kind:deployment.environment===cloudflareEnvironment?'cloudflare':'staging',publisher_worker_id:op.worker_id,issues,legacy:old};
 }
 need(deployment.task===deployment.environment&&['worldatlas-cloudflare-public','worldatlas-cloudflare-staging','worldatlas-cloudflare-recovery'].includes(deployment.environment),'Unknown Cloudflare operation environment/task');
 need(op.protocol_version===2&&['cloudflare','staging','recovery'].includes(op.kind),'New Cloudflare operations require the reviewed protocol');
 need((op.kind==='cloudflare')===(deployment.environment===cloudflareEnvironment)&&(op.kind==='staging')===(deployment.environment==='worldatlas-cloudflare-staging'),'Cloudflare operation kind/environment mismatch');
 need(Array.isArray(op.issues)&&op.issues.length>0&&op.issues.every(positive)&&new Set(op.issues).size===op.issues.length&&(op.issue===undefined||op.issues.includes(op.issue)),'Missing unique Cloudflare originating issues');
 const start=Date.parse(op.started_at),end=Date.parse(op.expires_at);
 need(Number.isFinite(start)&&Number.isFinite(end)&&end>start&&end-start<=2*60*60*1000&&evidence(op.rollback_url)&&uuid(op.rollback_worker_version),'Missing bounded Cloudflare operation/rollback');
 need(hex(op.discovery_commit,40)&&hex(op.tool_commit,40)&&hex(op.authored_head,40)&&evidence(op.review_url)&&evidence(op.runtime_review_url)&&evidence(op.merge_receipt_url),'Missing reviewed tool/runtime/discovery provenance');
 need(op.origin===cloudflareOrigin&&op.backend==='postgres'&&op.read_only===true&&op.database_writes===false&&op.public_reads===(op.kind==='cloudflare'),'Invalid Cloudflare runtime/read-only scope');
 need(typeof op.release_id==='string'&&op.release_id.length>0&&runtimePinFields.every(field=>hex(op[field],64)),'Missing operation release/lookup/backend/package pins');
 need(op.expected_worker_version===undefined||uuid(op.expected_worker_version),'Invalid expected existing Worker version');
 return {...op,publisher_worker_id:op.worker_id};
}
function parseMarker(body){
 const matches=[...String(body).matchAll(/<!-- worldatlas-cloudflare-result:v1\s*\n([\s\S]*?)\n-->/g)];
 need(matches.length===1,'Exactly one Cloudflare result required');return JSON.parse(matches[0][1]);
}
function checkRows(rows,issues,{supplemental=false}={}){
 need(Array.isArray(rows)&&new Set(rows.map(row=>row.issue)).size===rows.length&&issues.every(issue=>rows.some(row=>row.issue===issue)),'Missing Cloudflare per-issue acceptance');
 need(rows.every(row=>positive(row.issue)&&(supplemental||issues.includes(row.issue))&&['verified','failed','deferred','not-applicable'].includes(row.outcome)&&Array.isArray(row.evidence_urls)&&row.evidence_urls.length>0&&row.evidence_urls.every(evidence)),'Invalid Cloudflare per-issue acceptance');
 if(!supplemental)need(rows.length===issues.length,'Extra Cloudflare acceptance scope');
}
/** Historical receipts remain byte-pinned. They establish the delivered primary
 * and package/Worker identity; absent explicit pins remain absent, never invented. */
export async function cloudflareResult(api,status,deployment,op){
 const match=new RegExp('^https://github.com/'+repo+'/issues/([1-9]\\d*)#issuecomment-([1-9]\\d*)$').exec(status.log_url??'');
 need(match&&op.issues.includes(Number(match[1])),'Cloudflare result must be on an originating issue');
 const comment=await api('/repos/'+repo+'/issues/comments/'+match[2]);
 need(comment.html_url===status.log_url&&trusted(comment),'Unauthorized Cloudflare result');
 if(op.legacy)need(comment.id===op.legacy.result_comment_id&&hash(comment.body)===op.legacy.result_body_sha256,'Historical Cloudflare result drift');
 if(op.legacy?.legacy_encoding==='disconnected-stage-json'){
  const blocks=[...comment.body.matchAll(/```json\s*\n([\s\S]*?)\n```/g)];need(blocks.length===1,'Missing disconnected staging receipt');
  const r=JSON.parse(blocks[0][1]);
  need(status.state==='success'&&r.github_staging_deployment_id===deployment.id&&r.operation_id===op.operation_id&&r.primary_commit===deployment.sha&&r.state==='disconnected-stage-verified'&&r.read_only===true&&r.database_connected===false,'Unverified historical disconnected stage');
  return {state:'verified',cleanup_confirmed:true,delivery:null,issue_checks:[{issue:797,outcome:'deferred',evidence_urls:[comment.html_url],historical_scope:'Authenticated route checks deferred in this disconnected staging operation'}],limits:['This exact legacy receipt attests no remaining temporary process; it is not public delivery or SQL acceptance.']};
 }
 const r=parseMarker(comment.body);
 need(r.version===1&&r.deployment_id===deployment.id&&r.operation_id===op.operation_id&&r.worker_id===op.worker_id&&r.primary_commit===deployment.sha,'Incoherent Cloudflare result identity');
 need(['verified','failed-settled','unsettled'].includes(r.state)&&r.cleanup_confirmed===(r.state!=='unsettled'),'Unconfirmed Cloudflare cleanup');
 let checks=r.issue_checks;
 if(op.legacy&&op.kind==='staging'&&checks===undefined){
  need(r.state==='verified'&&r.temporary_access_removed===true&&r.owner_only_policy_preserved===true&&r.read_only===true,'Unverified connected legacy stage');
  checks=[{issue:797,outcome:'verified',evidence_urls:[comment.html_url],historical_scope:'Declared private read-only connected staging checks only'}];
 }
 checkRows(checks,op.issues,{supplemental:!!op.legacy});
 if(r.state==='unsettled'){
  need(r.delivery===null||op.legacy&&r.delivery===undefined,'Unsettled Cloudflare operation cannot assert delivery');
  return {...r,delivery:null,issue_checks:checks};
 }
 need((r.state==='verified'&&status.state==='success')||(r.state==='failed-settled'&&['failure','error'].includes(status.state)),'Cloudflare status/result mismatch');
 let delivery=null;
 if(op.kind==='cloudflare'&&r.state==='verified'){
  need(uuid(r.worker_version)&&r.public_reads===true&&r.database_writes_enabled===false&&r.database_information_deleted===false&&r.original_site_and_storage_preserved===true&&evidence(r.acceptance_url),'Unverified public read-only Cloudflare delivery');
  if(op.legacy){
   need(hex(op.package_inventory_sha256,64),'Historical public package identity absent');
   delivery={version:1,provider:'cloudflare',historical:true,primary_commit:deployment.sha,cloudflare:{origin:cloudflareOrigin,worker_version:r.worker_version,registry_deployment_id:deployment.id},package_inventory_sha256:op.package_inventory_sha256,evidence_urls:[comment.html_url,r.acceptance_url],limits:['Historical registry establishes actual primary/Worker/package identity; explicit release/lookup/provider-deployment pins must be verified before new live work.']};
  }else{
   delivery=validateCloudflareDelivery(r.delivery);
   need(delivery.primary_commit===deployment.sha&&delivery.cloudflare.registry_deployment_id===deployment.id&&delivery.cloudflare.worker_version===r.worker_version&&runtimePinFields.every(field=>delivery[field]===op[field])&&delivery.release_id===op.release_id,'Cloudflare delivery/operation pin mismatch');
   need(op.expected_worker_version===undefined||op.expected_worker_version===r.worker_version,'Existing-version publication changed Worker');
  }
 }else need(r.delivery===null||op.legacy&&r.delivery===undefined,'Failed/recovery/staging cannot advance Cloudflare delivery');
 return {...r,delivery,issue_checks:checks};
}

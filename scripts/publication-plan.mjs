import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {githubPages} from './issue-claim-contract.mjs';

export const publicationRepo='ChengshuLi/WorldAtlas';
export const publicationEnvironment='worldatlas-production';
export const publicationTask='worldatlas-publication';
const root='/repos/'+publicationRepo;
const sha=value=>/^[a-f0-9]{40}$/.test(value??'');
const positive=value=>Number.isSafeInteger(value)&&value>0;
const need=(value,message)=>{if(!value)throw Error(message);};
const trusted=comment=>comment?.user?.type==='User'&&['OWNER','MEMBER','COLLABORATOR'].includes(comment.author_association);
export function marker(body,name){
 const matches=[...String(body??'').matchAll(new RegExp('<!-- '+name+'\\s*\\n([\\s\\S]*?)\\n-->','g'))];
 need(matches.length===1,'Exactly one '+name+' record required');return JSON.parse(matches[0][1]);
}
export function validateDelivery(value){
 need(value?.version===1&&sha(value.primary_commit)&&sha(value.source_commit),'Missing exact primary/mirror delivery identity');
 need(value.site?.project_id==='appgprj_6abdf87277c08191bce4a22b8dfb25db'&&positive(value.site.version)&&/^appgdep_/.test(value.site.deployment_id??''),'Missing Site delivery identity');
 need(typeof value.release_id==='string'&&value.release_id.length>0&&/^[a-f0-9]{64}$/.test(value.hierarchy_sha256??'')&&/^[a-f0-9]{64}$/.test(value.footprint_sha256??'')&&/^[a-f0-9]{64}$/.test(value.assets_sha256??''),'Missing release/data/assets delivery identity');
 need(Array.isArray(value.evidence_urls)&&value.evidence_urls.length>0&&value.evidence_urls.every(url=>typeof url==='string'&&url.startsWith('https://github.com/'+publicationRepo+'/')),'Missing delivery evidence');
 return value;
}
export function validateOperation(deployment){
 const op=deployment.payload?.worldatlas_publication;
 need(op?.version===1&&op.operation_id&&op.publisher_worker_id&&['site','recovery'].includes(op.kind),'Malformed publisher operation');
 need(sha(deployment.sha)&&deployment.sha===op.primary_commit&&Array.isArray(op.issues)&&op.issues.every(positive),'Unpinned operation scope');
 need(Number.isFinite(Date.parse(op.started_at))&&Number.isFinite(Date.parse(op.expires_at))&&Date.parse(op.expires_at)>Date.parse(op.started_at)&&typeof op.rollback_url==='string'&&op.rollback_url.startsWith('https://github.com/'+publicationRepo+'/'),'Missing bounded operation/rollback');
 return op;
}
async function resultReceipt(api,status,deployment,op){
 const match=new RegExp('^https://github.com/'+publicationRepo+'/issues/([1-9]\\d*)#issuecomment-([1-9]\\d*)$').exec(status.log_url??'');
 need(match&&op.issues.includes(Number(match[1])),'Operation result must be on an originating issue');
 const comment=await api(root+'/issues/comments/'+match[2]);
 need(comment.html_url===status.log_url&&trusted(comment),'Unauthorized operation result');
 const receipt=marker(comment.body,'worldatlas-publication-result:v1');
 need(receipt.version===1&&receipt.deployment_id===deployment.id&&receipt.operation_id===op.operation_id&&receipt.publisher_worker_id===op.publisher_worker_id&&receipt.primary_commit===deployment.sha,'Incoherent operation result identity');
 need(['verified','failed-settled','unsettled'].includes(receipt.state)&&receipt.cleanup_confirmed===(receipt.state!=='unsettled'),'Unconfirmed operation cleanup');
 need(Array.isArray(receipt.issue_checks)&&receipt.issue_checks.length===op.issues.length&&new Set(receipt.issue_checks.map(row=>row.issue)).size===op.issues.length&&receipt.issue_checks.every(row=>op.issues.includes(row.issue)&&['verified','failed','deferred','not-applicable'].includes(row.outcome)&&Array.isArray(row.evidence_urls)&&row.evidence_urls.length>0),'Missing separate per-issue acceptance outcomes');
 if(receipt.delivery!==null){
  need(op.kind==='site'&&receipt.state==='verified'&&status.state==='success','Failed/recovery operation cannot advance delivery');
  validateDelivery(receipt.delivery);need(receipt.delivery.primary_commit===deployment.sha,'Delivery/result commit mismatch');
 }
 need(receipt.delivery!==undefined,'Explicit delivery object or null required');
 need(op.kind!=='site'||receipt.state!=='verified'||receipt.delivery!==null,'Verified Site operation requires actual delivery identity');
 return receipt;
}
export async function readPublicationState(api){
 const deployments=await githubPages(api,root+'/deployments?environment='+publicationEnvironment);
 const deliveries=[],unsettled=[],checks=[];
 for(const deployment of deployments.sort((a,b)=>a.id-b.id)){
  // Other deployments in the reserved environment are visible blockers, not ignored.
  need(deployment.task===publicationTask,'Unknown operation in publisher environment');
  const op=validateOperation(deployment),statuses=await githubPages(api,root+'/deployments/'+deployment.id+'/statuses');
  need(new Set(statuses.map(row=>row.id)).size===statuses.length,'Duplicate deployment statuses');
  const latest=statuses.sort((a,b)=>b.id-a.id)[0];
  if(!latest||!['success','failure','error'].includes(latest.state)){unsettled.push({deployment_id:deployment.id,...op,reason:'No settled result; expiry does not establish cleanup'});continue;}
  const receipt=await resultReceipt(api,latest,deployment,op);
  if(receipt.state==='unsettled'){unsettled.push({deployment_id:deployment.id,...op,reason:'Explicitly unsettled'});continue;}
  need((receipt.state==='verified'&&latest.state==='success')||(receipt.state==='failed-settled'&&['failure','error'].includes(latest.state)),'Status/result settlement mismatch');
  if(receipt.delivery)deliveries.push(receipt.delivery);
  checks.push(...receipt.issue_checks.map(row=>({...row,operation_id:op.operation_id,result_url:latest.log_url})));
 }
 return {delivery:deliveries.at(-1)??null,deliveries,unsettled,checks};
}
// Only explicit original-issue references count; incidental #PR mentions are not criteria.
export function referencedIssues(body){
 const ids=new Set();
 for(const line of String(body??'').split('\n')){
  const match=/^\s*(?:Refs|Closes|Fixes|Resolves)\s+(.+)$/i.exec(line);
  if(!match)continue;
  for(const item of match[1].matchAll(/(?:^|[\s,])#([1-9]\d*)\b|https:\/\/github\.com\/ChengshuLi\/WorldAtlas\/issues\/([1-9]\d*)\b/g))ids.add(Number(item[1]??item[2]));
 }
 return [...ids].sort((a,b)=>a-b);
}
export async function publicationPlan(api,{bootstrap=null}={}){
 // Freeze target before any paginated reads; never build a moving branch.
 const target=(await api(root+'/commits/main')).sha;need(sha(target),'Invalid pinned main');
 const state=await readPublicationState(api);
 if(bootstrap)validateDelivery(bootstrap);
 const delivery=state.delivery??bootstrap;
 const labeled=(await githubPages(api,root+'/issues?state=open&labels=publisher-needed')).filter(issue=>!issue.pull_request);
 const pendingChecks=new Map();for(const check of state.checks)pendingChecks.set(check.issue,check);
 const residual=[...pendingChecks.values()].filter(row=>['failed','deferred'].includes(row.outcome));
 const issues=new Map(labeled.map(issue=>[issue.number,{...issue,discovery:['publisher-needed']}])) ;
 for(const row of residual){if(!issues.has(row.issue))issues.set(row.issue,{...await api(root+'/issues/'+row.issue),discovery:['outstanding-acceptance']});else issues.get(row.issue).discovery.push('outstanding-acceptance');}
 const plan={version:1,target_commit:target,last_delivery:delivery,unsettled_operations:state.unsettled,commits:[],pull_requests:[],issues:[],unlinked_commits:[],blockers:[]};
 if(!delivery)plan.blockers.push('No verified primary delivery boundary: reconstruct from original build/deployment evidence; never substitute mirror SHA or current main');
 else{
  // Compare API pagination is bounded independently of files (files are irrelevant).
  const commits=[];let total;
  for(let page=1;page<=100;page++){
   const comparison=await api(root+'/compare/'+delivery.primary_commit+'...'+target+'?per_page=100&page='+page);
   need(['ahead','identical'].includes(comparison.status)&&comparison.merge_base_commit?.sha===delivery.primary_commit,'Delivered commit is not an ancestor of pinned main');
   need(Number.isSafeInteger(comparison.total_commits)&&comparison.total_commits>=0&&Array.isArray(comparison.commits),'Incomplete comparison');
   if(total===undefined)total=comparison.total_commits;need(total===comparison.total_commits,'Comparison changed during pagination');
   commits.push(...comparison.commits);
   if(commits.length===total)break;
   need(commits.length<total&&comparison.commits.length===100&&page<100,'Incomplete commit pagination');
  }
  need(commits.length===total&&new Set(commits.map(c=>c.sha)).size===total&&commits.every(c=>sha(c.sha)),'Incomplete/duplicate commit inventory');
  // Check successive delivered receipts are monotone; a stale or divergent delivery cannot silently replace one.
  const history=[...(bootstrap?[bootstrap]:[]),...state.deliveries];
  for(let i=1;i<history.length;i++){
   const previous=history[i-1].primary_commit,current=history[i].primary_commit;
   const relation=await api(root+'/compare/'+previous+'...'+current+'?per_page=1');
   need(['ahead','identical'].includes(relation.status)&&relation.merge_base_commit?.sha===previous,'Non-monotone delivered history');
  }
  const pullMap=new Map(),commitSet=new Set(commits.map(c=>c.sha));
  for(const commit of commits){
   const associated=await githubPages(api,root+'/commits/'+commit.sha+'/pulls');
   const merged=associated.filter(pr=>pr.merged_at&&pr.base?.repo?.full_name===publicationRepo&&pr.base.ref==='main'&&commitSet.has(pr.merge_commit_sha));
   plan.commits.push({sha:commit.sha,message:commit.commit?.message??'',pull_requests:merged.map(pr=>pr.number)});
   if(!merged.length)plan.unlinked_commits.push(commit.sha);
   for(const pr of merged)pullMap.set(pr.number,pr);
  }
  for(const pr of [...pullMap.values()].sort((a,b)=>a.number-b.number)){
   const linked=referencedIssues(pr.body);
   plan.pull_requests.push({number:pr.number,url:pr.html_url,merge_commit:pr.merge_commit_sha,issues:linked,needs_manual_issue_mapping:linked.length===0});
   for(const number of linked){if(!issues.has(number))issues.set(number,{...await api(root+'/issues/'+number),discovery:['merged-pr']});else if(!issues.get(number).discovery.includes('merged-pr'))issues.get(number).discovery.push('merged-pr');}
  }
 }
 for(const issue of [...issues.values()].sort((a,b)=>a.number-b.number)){
  need(!issue.pull_request,'Issue reference points to a PR: inspect scope manually');
  plan.issues.push({number:issue.number,title:issue.title,state:issue.state,url:issue.html_url,labels:issue.labels.map(label=>typeof label==='string'?label:label.name),discovery:issue.discovery,last_check:pendingChecks.get(issue.number)??null,eligibility:'unreviewed'});
 }
 if(state.unsettled.length)plan.blockers.push('An active/unsettled operation blocks new live work');
 return plan;
}
export const ghReadAPI=async route=>JSON.parse(execFileSync('gh',['api',route],{encoding:'utf8',maxBuffer:32*1024*1024}));
if(process.argv[1]&&fileURLToPath(import.meta.url)===process.argv[1]){
 try{
  const args=process.argv.slice(2);need(args.length===0||(args.length===2&&args[0]==='--bootstrap'),'Usage: node scripts/publication-plan.mjs [--bootstrap VERIFIED-DELIVERY.json]');
  const bootstrapPath=args.length?args[1]:fileURLToPath(new URL('../coordination/publication/bootstrap.json',import.meta.url));
  const bootstrap=fs.existsSync(bootstrapPath)?JSON.parse(fs.readFileSync(bootstrapPath,'utf8')):null;
  const plan=await publicationPlan(ghReadAPI,{bootstrap});console.log(JSON.stringify(plan,null,2));
  if(plan.blockers.length)process.exitCode=2;
 }catch(error){console.error(error.message);process.exitCode=1;}
}

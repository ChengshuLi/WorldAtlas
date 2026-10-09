import {assertAuthorWorkerIdentity} from './worker-identity.mjs';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import {randomUUID} from 'node:crypto';
import {readClaim,canonicalIssueNumber,githubPages,githubAPI} from './issue-claim-contract.mjs';
import {observeIssueLease} from './issue-lease-client.mjs';
import {requestAccounting} from './github-quota.mjs';

const [action,...args]=process.argv.slice(2),options={};
for(let i=0;i<args.length;i+=2){const key=args[i]?.replace(/^--/,'');if(!['issue','worker','branch','claim-id','out','live-work','reason'].includes(key)||!args[i+1]||options[key])throw Error('Use action --issue N --worker unique-thread-id --branch lane/id [--claim-id UUID] [--out receipt.json]');options[key]=args[i+1];}
if(!['claim','renew','release','recover','inspect'].includes(action))throw Error('Choose claim, renew, release, recover or inspect and an issue number');
const issue_number=canonicalIssueNumber(options.issue),repo='ChengshuLi/WorldAtlas';
if(action!=='inspect'){
 if(!options.worker||!options.branch||action!=='claim'&&action!=='recover'&&!options['claim-id'])throw Error('Supply worker/branch and the held claim ID for renew/release');
 if(action==='claim'||action==='recover')assertAuthorWorkerIdentity(options.worker);
 if(options['live-work']&&!['true','false'].includes(options['live-work']))throw Error('live-work must be true or false');
}
const accounting=requestAccounting('claim-observer'),deadline=Date.now()+240000;
// No credential is written to a receipt or passed to a subprocess command line.
const token=execFileSync('gh',['auth','token'],{encoding:'utf8',timeout:20000,maxBuffer:16384}).trim();
const api=githubAPI(token,{onRequest:accounting.observe,minimumRemaining:16,deadlineRemaining:()=>deadline-Date.now()});
if(action==='inspect'){
 const comments=await githubPages(api,`/repos/${repo}/issues/${issue_number}/comments`);
 console.log(JSON.stringify(readClaim(comments),null,2));process.exit(0);
}
let previous;
if(options.out&&fs.existsSync(options.out)){
 const stored=JSON.parse(fs.readFileSync(options.out,'utf8'));
 if(stored.status==='pending'){
  if(stored.issue_number!==issue_number||stored.worker_id!==options.worker||stored.branch!==options.branch||stored.action!==action||
   options['claim-id']&&stored.claim_id!==options['claim-id']||stored.live_work!==(options['live-work']??'false')||(stored.request_reason??stored.reason)!==(options.reason??''))throw Error('Pending receipt belongs to another request; preserve it and use its original inputs');
  previous=stored;
 }
}
const request={action,issue_number,worker_id:options.worker,branch:options.branch,
 claim_id:previous?.claim_id??options['claim-id']??randomUUID(),request_id:previous?.request_id??randomUUID(),
 live_work:options['live-work']??'false',reason:options.reason??''};
const checkpoint=result=>{if(options.out)fs.writeFileSync(options.out,JSON.stringify({...result,request_accounting:accounting.receipt()},null,2)+'\n');};
const result=await observeIssueLease({api,repo,request,resuming:Boolean(previous?.submitted),timeoutMs:Math.max(1,deadline-Date.now()),checkpoint,
 submit:()=>api(`/repos/${repo}/actions/workflows/issue-claims.yml/dispatches`,'POST',{ref:'main',inputs:{
  action,issue_number:String(issue_number),worker_id:request.worker_id,branch:request.branch,claim_id:request.claim_id,
  request_id:request.request_id,live_work:options['live-work']??'false',reason:options.reason??''}})});
console.log(JSON.stringify({...result,request_accounting:accounting.receipt()},null,2));
if(!result.accepted)process.exitCode=2;

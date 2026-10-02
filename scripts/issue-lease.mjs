import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import {randomUUID} from 'node:crypto';
import {readClaim,canonicalIssueNumber,githubPages} from './issue-claim-contract.mjs';
import {confirmReservation} from './worker-result.mjs';

const [action,...args]=process.argv.slice(2),options={};
for(let i=0;i<args.length;i+=2){const key=args[i]?.replace(/^--/,'');if(!['issue','worker','branch','claim-id','out','live-work','reason'].includes(key)||!args[i+1]||options[key])throw Error('Use action --issue N --worker unique-thread-id --branch lane/id [--claim-id UUID] [--out receipt.json]');options[key]=args[i+1];}
if(!['claim','renew','release','recover','inspect'].includes(action))throw Error('Choose claim, renew, release, recover or inspect and an issue number');
canonicalIssueNumber(options.issue);
const repo='ChengshuLi/WorldAtlas',gh=args=>execFileSync('gh',args,{encoding:'utf8',maxBuffer:8*1024*1024}),sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const comments=()=>githubPages(async route=>JSON.parse(gh(['api',route])),`/repos/${repo}/issues/${options.issue}/comments`);
if(action==='inspect'){
 console.log(JSON.stringify(readClaim(await comments()),null,2));process.exit(0);
}
if(!options.worker||!options.branch||action!=='claim'&&action!=='recover'&&!options['claim-id'])throw Error('Supply worker/branch and the held claim ID for renew/release');
if(options['live-work']&&!['true','false'].includes(options['live-work']))throw Error('live-work must be true or false');
const claim_id=options['claim-id']??randomUUID(),request_id=randomUUID(),expectedTitle=`${action} #${options.issue} ${request_id}`;
let received=false,lastRunID=0;
 for(let attempt=0;attempt<3;attempt++){
  gh(['workflow','run','issue-claims.yml','--repo',repo,'--ref','main',...Object.entries({action,issue_number:options.issue,worker_id:options.worker,branch:options.branch,claim_id,request_id,live_work:options['live-work']??'false',reason:options.reason??''}).flatMap(([key,value])=>['-f',`${key}=${value}`])]);
  const started=Date.now();let run;
  while(Date.now()-started<240000){
   const runs=JSON.parse(gh(['api',`repos/${repo}/actions/workflows/issue-claims.yml/runs?event=workflow_dispatch&per_page=100`]));
   run=runs.workflow_runs?.find(r=>r.display_title===expectedTitle&&r.id>lastRunID);
   if(run?.status==='completed')break;
   await sleep(3000);
  }
  if(!run||run.status!=='completed')throw Error('Reservation is not confirmed; do not begin work. Inspect the workflow/issue before retrying.');
  if(run.conclusion==='cancelled'){lastRunID=run.id;await sleep(2000+Math.random()*3000);continue;}
  if(run.conclusion!=='success')throw Error(`Claim workflow ${run.id} failed; inspect current issue state before retrying`);
  const result=confirmReservation(await comments(),{request_id,issue_number:Number(options.issue),worker_id:options.worker,claim_id,branch:options.branch,action});
  result.workflow_url=run.html_url;
  if(options.out)fs.writeFileSync(options.out,JSON.stringify(result,null,2)+'\n');
  received=true;console.log(JSON.stringify(result,null,2));
  if(!result.accepted)process.exitCode=2;
  break;
 }
 if(!received)throw Error('Claim requests were superseded/cancelled; no ownership confirmed. Retry later with jitter or choose another issue.');

import {githubPages,canonicalIssueNumber} from './issue-claim-contract.mjs';
import {confirmReservation,readWorkerResult} from './worker-result.mjs';
import {quotaDelay} from './github-quota.mjs';

// A dispatch is a single mutation boundary. Observation may expire or see a
// cancelled execution; neither authorizes another dispatch or implementation.
export async function observeIssueLease({api,submit,repo,request,resuming=false,
 now=Date.now,sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms)),timeoutMs=240000,
 checkpoint=()=>{}}){
 if(!/^[-\w.]+\/[-\w.]+$/.test(repo??'')||canonicalIssueNumber(request?.issue_number)!==request.issue_number||
  !/^[-a-zA-Z0-9]{16,100}$/.test(request.request_id??'')||!['claim','renew','release','recover'].includes(request.action)||
  !Number.isSafeInteger(timeoutMs)||timeoutMs<=0)throw Error('Invalid reservation observation context');
 const started=now(),deadline=started+timeoutMs,root=`/repos/${repo}`;
 let runID,reads=0,submissionUncertain=false,submitted=resuming;
 const pending=(extra={})=>({accepted:false,status:'pending',...request,request_reason:request.reason??'',submitted,
  ...(submissionUncertain?{submission_uncertain:true}:{}),logical_observation_reads:reads,...extra});
 checkpoint(pending());
 if(!resuming){
  // Persist uncertainty before crossing the external boundary, including crashes.
  submitted=true;submissionUncertain=true;checkpoint(pending());
  try{await submit();submissionUncertain=false;checkpoint(pending());}
  catch(error){
   const actual=error.github?.http_status;
   if(error.quotaAdmission||[400,401,403,404,422,429].includes(actual)){
    submitted=false;submissionUncertain=false;
    const delay=quotaDelay(error,now());
    const result=pending({reason:error.message,...(delay!==null?{retry_at:new Date(now()+delay).toISOString()}:{})});
    checkpoint(result);return result;
   }
   // A lost response may hide a completed dispatch. Observe this same identity.
   checkpoint(pending({reason:'Dispatch response uncertain; observe the same request'}));
  }
 }
 let delay=15000;
 const read=async route=>{if(now()>=deadline)throw Object.assign(Error('Observation deadline'),{observationExpired:true});reads++;return api(route);};
 while(now()+delay<deadline){
  await sleep(delay);
  if(now()>=deadline)break;
  try{
   const comments=await githubPages(read,`${root}/issues/${request.issue_number}/comments`);
   if(now()>=deadline)break;
   const result=readWorkerResult(comments,'claim',request.request_id,request.issue_number);
   if(result){
    const confirmed=confirmReservation(comments,request,now());
    const complete={...confirmed,logical_observation_reads:reads,...(runID?{workflow_url:`https://github.com/${repo}/actions/runs/${runID}`}:{})};
    checkpoint(complete);return complete;
   }
   if(!runID){
    // Discover once, then query only the exact run. Complete pagination cannot
    // be replaced by absence from the latest 100 executions.
    for(let page=1;page<=100;page++){
     const response=await read(`${root}/actions/workflows/issue-claims.yml/runs?event=workflow_dispatch&per_page=100&page=${page}`);
     if(!Array.isArray(response.workflow_runs))throw Error('Incomplete claim workflow inventory');
     const run=response.workflow_runs.find(row=>row.display_title===`${request.action} #${request.issue_number} ${request.request_id}`);
     if(run){if(!Number.isSafeInteger(run.id)||run.id<1)throw Error('Invalid exact claim execution identity');runID=run.id;break;}
     if(response.workflow_runs.length<100)break;
     if(page===100)throw Error('Claim workflow inventory capped; no absence inferred');
    }
   }
   if(runID){
    const run=await read(`${root}/actions/runs/${runID}`);
    if(run.display_title!==`${request.action} #${request.issue_number} ${request.request_id}`)throw Error('Workflow identity changed');
    if(run.status==='completed'){
     // Older trusted workflows may expose only a canonical confirmation. Read
     // again after completion so an earlier partial mutation cannot confer work.
     const fresh=await githubPages(read,`${root}/issues/${request.issue_number}/comments`);
     if(now()>=deadline)break;
     if(run.conclusion==='success'||readWorkerResult(fresh,'claim',request.request_id,request.issue_number)){
      const confirmed=confirmReservation(fresh,request,now());
      const complete={...confirmed,workflow_url:`https://github.com/${repo}/actions/runs/${runID}`,logical_observation_reads:reads};checkpoint(complete);return complete;
     }
     const stopped=pending({workflow_url:`https://github.com/${repo}/actions/runs/${runID}`,execution_conclusion:run.conclusion,
      reason:'Execution is terminal without confirmed ownership; reconcile the same request before retrying'});
     checkpoint(stopped);return stopped;
    }
   }
  }catch(error){
   if(error.observationExpired)break;
   const quota=quotaDelay(error,now());
   if(quota!==null){
    const result=pending({retry_at:new Date(now()+quota).toISOString(),reason:error.message});checkpoint(result);return result;
   }
   // Temporary observations cannot prove an execution stopped. Do not submit
   // again; leave a recoverable identity even for transport/server failure.
   const result=pending({reason:error.message,...(runID?{workflow_url:`https://github.com/${repo}/actions/runs/${runID}`}:{})});
   checkpoint(result);return result;
  }
  delay=Math.min(60000,delay*2);
 }
 const result=pending({reason:'Observation ended without ownership confirmation; resume the same request'});
 checkpoint(result);return result;
}

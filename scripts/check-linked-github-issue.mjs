import fs from 'node:fs';
import {requestAccounting,quotaDelay} from './github-quota.mjs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {githubAPI,workSpec,verifyIssueScope} from './issue-claim-contract.mjs';
import {validateIssuePRBody,validateIssueMetadata,checkGitScope} from './check-handoff-scope.mjs';
import {evidenceRequirement,loadEvidencePolicy} from './evidence-policy.mjs';

export async function checkLinkedIssue({branch,event,token,fetchIssue,api,base,head='HEAD',run,evidencePolicy}){
 const pr=event.pull_request,repo=event.repository?.full_name;
 if(!pr||!/^[-\w.]+\/[-\w.]+$/.test(repo??''))throw Error('Supply a repository pull_request event');
 const {github_issue,issue_action}=validateIssuePRBody(pr.body??'');
 if(!token)throw Error('A read-only GitHub token is required');
 const client=api??githubAPI(token);let issue;
 if(fetchIssue){
  const response=await fetchIssue(`https://api.github.com/repos/${repo}/issues/${github_issue}`,{headers:{Authorization:`Bearer ${token}`,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'},signal:AbortSignal.timeout(15000)});
  if(!response.ok)throw Error(`Could not read linked GitHub issue (HTTP ${response.status})`);
  issue=await response.json();
 }else issue=await client(`/repos/${repo}/issues/${github_issue}`);
  if (issue.number !== github_issue) throw Error('Issue response does not match the PR linkage');
 const metadata=validateIssueMetadata(branch,issue),scope=verifyIssueScope({branch,issue});
 const policy=evidencePolicy??loadEvidencePolicy();
 try{metadata.evidence_policy=evidenceRequirement(issue,workSpec(issue.body),policy,branch);}
 catch(error){if(policy.mode!=='report-only')throw error;metadata.evidence_policy={status:'report-failure',reason:error.message};}
 const ownedPaths=scope.owned_paths;
 if(ownedPaths)metadata.owned_paths=ownedPaths;
 if(base)metadata.git_scope=checkGitScope({branch,base,head,run,prBody:pr.body??'',ownedPaths});
 return {github_issue,issue_action,...metadata};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const event=JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH,'utf8'));
 const accounting=requestAccounting('linked-issue');
 try{
  console.log(JSON.stringify({linked_issue_check:'passed',...await checkLinkedIssue({branch:process.env.LANE_BRANCH,event,token:process.env.GH_TOKEN,
   api:githubAPI(process.env.GH_TOKEN,{onRequest:accounting.observe}),base:process.env.BASE_SHA??event.pull_request?.base?.sha})}));
 }catch(error){
  const delay=quotaDelay(error);
  console.log(JSON.stringify({linked_issue_check:'refused',reason:error.message,...(error.github?{api_error:error.github}:{}),
   retryable:delay!==null,...(delay!==null?{retry_at:new Date(Date.now()+delay).toISOString()}:{})}));
  process.exitCode=1;
 }finally{console.log(JSON.stringify({request_accounting:accounting.receipt()}));}
}

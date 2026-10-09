import fs from 'node:fs';
import {requestAccounting,quotaDelay,completeReads} from './github-quota.mjs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {githubPages,githubAPI,linkedPulls,verifyClaimForPR,workSpec} from './issue-claim-contract.mjs';
import {validateIssuePRBody,validateIssueMetadata,checkGitScope,laneForBranch,validateEngineeringOwnedPaths} from './check-handoff-scope.mjs';
import {evidenceRequirement,loadEvidencePolicy} from './evidence-policy.mjs';

export async function checkLinkedIssue({branch,event,token,fetchIssue,api,checkClaim=false,base,head='HEAD',run,evidencePolicy}){
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
 const metadata=validateIssueMetadata(branch,issue);
 const policy=evidencePolicy??loadEvidencePolicy();
 try{metadata.evidence_policy=evidenceRequirement(issue,workSpec(issue.body),policy,branch);}
 catch(error){if(policy.mode!=='report-only')throw error;metadata.evidence_policy={status:'report-failure',reason:error.message};}
 const lane=laneForBranch(branch).lane,spec=['geography','engineering'].includes(lane)?workSpec(issue.body):null;
 if(lane==='engineering'&&spec.mode!=='engineering')throw Error('Issue ownership requires engineering mode');
 const ownedPaths=lane==='engineering'&&spec.owned_paths!==undefined?validateEngineeringOwnedPaths(spec.owned_paths):spec?.owned_paths;
 if(ownedPaths)metadata.owned_paths=ownedPaths;
 if(checkClaim){const [comments,prs]=await completeReads([githubPages(client,`/repos/${repo}/issues/${github_issue}/comments`),linkedPulls(client,repo,github_issue)]);Object.assign(metadata,verifyClaimForPR({branch,issue,comments,prs}));}
 if(base)metadata.git_scope=checkGitScope({branch,base,head,run,prBody:pr.body??'',ownedPaths});
 return {github_issue,issue_action,...metadata};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const event=JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH,'utf8'));
 const accounting=requestAccounting('linked-issue');
 try{
  console.log(JSON.stringify({linked_issue_check:'passed',...await checkLinkedIssue({branch:process.env.LANE_BRANCH,event,token:process.env.GH_TOKEN,
   api:githubAPI(process.env.GH_TOKEN,{onRequest:accounting.observe}),checkClaim:true,base:process.env.BASE_SHA??event.pull_request?.base?.sha})}));
 }catch(error){
  const delay=quotaDelay(error);
  console.log(JSON.stringify({linked_issue_check:'refused',reason:error.message,...(error.github?{api_error:error.github}:{}),
   retryable:delay!==null,...(delay!==null?{retry_at:new Date(Date.now()+delay).toISOString()}:{})}));
  process.exitCode=1;
 }finally{console.log(JSON.stringify({request_accounting:accounting.receipt()}));}
}

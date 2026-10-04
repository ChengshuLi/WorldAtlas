import {renderWorkerResult} from './worker-result.mjs';
import fs from 'node:fs';
import {githubAPI,githubPages,linkedPulls,verifyClaimForPR} from './issue-claim-contract.mjs';
import {validateIssuePRBody,validateLanePaths} from './check-handoff-scope.mjs';
import {checkPremergeEvidence} from './premerge-evidence.mjs';
import {evidenceRequirement,loadEvidencePolicy} from './evidence-policy.mjs';
import {workSpec} from './issue-claim-contract.mjs';

const event=JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH,'utf8')),input=event.inputs??{},repo=process.env.GITHUB_REPOSITORY;
if(process.env.GITHUB_REF!=='refs/heads/main'||!/^[-\w.]+\/[-\w.]+$/.test(repo??''))throw Error('Merges run only from trusted main');
const number=Number(input.pr_number),result={accepted:false,request_id:input.request_id,pr_number:number};
if(!Number.isSafeInteger(number)||number<1||!/^[a-f0-9]{40}$/.test(input.expected_head??'')||!/^[-a-zA-Z0-9]{16,100}$/.test(input.request_id??''))throw Error('Invalid merge request');
const api=githubAPI(process.env.GH_TOKEN);
try{
 const pr=await api(`/repos/${repo}/pulls/${number}`);
 if(pr.head.sha!==input.expected_head)throw Error('PR changed; verify the new head before requesting merge');
 if(pr.merged){Object.assign(result,{accepted:true,replayed:true,merge_commit:pr.merge_commit_sha});}
 else{
  if(pr.state!=='open'||pr.draft||pr.base.ref!=='main'||pr.head.repo?.full_name!==repo)throw Error('Only open non-draft repository PRs targeting main may merge');
  const {github_issue}=validateIssuePRBody(pr.body??''),issue=await api(`/repos/${repo}/issues/${github_issue}`),comments=await githubPages(api,`/repos/${repo}/issues/${github_issue}/comments`);
  const reservation=verifyClaimForPR({branch:pr.head.ref,issue,comments,prs:await linkedPulls(api,repo,github_issue)});
  const files=await githubPages(api,`/repos/${repo}/pulls/${number}/files`);
  if(files.length!==pr.changed_files)throw Error('Incomplete PR file inventory; refuse truncated ownership validation');
  validateLanePaths(pr.head.ref,files.flatMap(file=>[file.filename,...(file.previous_filename?[file.previous_filename]:[])]),{ownedPaths:reservation.owned_paths});
  const main=await api(`/repos/${repo}/git/ref/heads/main`),comparison=await api(`/repos/${repo}/compare/${main.object.sha}...${pr.head.sha}`);
  if(!['ahead','identical'].includes(comparison.status))throw Error('Update this PR with latest main and rerun checks before merge');
  const checks=await githubPages(api,`/repos/${repo}/commits/${pr.head.sha}/check-runs`);
  const scope=checks.filter(c=>c.name==='scope').sort((a,b)=>b.id-a.id)[0];
  if(!scope||scope.status!=='completed'||scope.conclusion!=='success')throw Error('Current head must pass the trusted scope check');
  // For reruns, only the latest result for each check/app name is authoritative.
  const latest=new Map();for(const check of checks){const key=`${check.app?.id}:${check.name}`;if(!latest.has(key)||latest.get(key).id<check.id)latest.set(key,check);}
  if([...latest.values()].some(c=>c.status!=='completed'||!['success','skipped','neutral'].includes(c.conclusion)))throw Error('A current check is pending or failed');
  const statuses=await api(`/repos/${repo}/commits/${pr.head.sha}/status`);
  if(statuses.statuses?.length&&statuses.state!=='success')throw Error('A commit status is pending or failed');
  const policy=loadEvidencePolicy();
  if(policy.mode==='enforce-new'&&evidenceRequirement(issue,workSpec(issue.body),policy,pr.head.ref).required){
   const evidence=checks.filter(c=>c.name==='evidence').sort((a,b)=>b.id-a.id)[0];
   if(!evidence||evidence.status!=='completed'||evidence.conclusion!=='success')throw Error('Current head must pass trusted evidence check');
  }
  result.evidence=await checkPremergeEvidence({api,repo,pr,issue,reservation,files,policy,review:true});
  // Receipt validation may take time: reread mutable authorities before the SHA-guarded merge.
  const currentPR=await api(`/repos/${repo}/pulls/${number}`),currentIssue=await api(`/repos/${repo}/issues/${github_issue}`);
  if(currentPR.head.sha!==pr.head.sha||currentPR.body!==pr.body||currentIssue.body!==issue.body)throw Error('PR head/body or issue contract changed during review; retry');
  verifyClaimForPR({branch:pr.head.ref,issue:currentIssue,comments:await githubPages(api,`/repos/${repo}/issues/${github_issue}/comments`),prs:await linkedPulls(api,repo,github_issue)});
  const freshChecks=await githubPages(api,`/repos/${repo}/commits/${pr.head.sha}/check-runs`),freshLatest=new Map();
  for(const check of freshChecks){const key=`${check.app?.id}:${check.name}`;if(!freshLatest.has(key)||freshLatest.get(key).id<check.id)freshLatest.set(key,check);}
  if([...freshLatest.values()].some(check=>check.status!=='completed'||!['success','skipped','neutral'].includes(check.conclusion)))throw Error('Checks changed during evidence review; retry');
  const freshMain=await api(`/repos/${repo}/git/ref/heads/main`);
  if(freshMain.object.sha!==main.object.sha)throw Error('Main advanced during review; update and retry');
  const merged=await api(`/repos/${repo}/pulls/${number}/merge`,'PUT',{sha:pr.head.sha,merge_method:'squash',commit_title:pr.title,commit_message:pr.body});
  if(!merged.merged)throw Error('GitHub did not merge the PR');
  Object.assign(result,{accepted:true,merge_commit:merged.sha,title:pr.title,github_issue});
 }
}catch(error){result.reason=error.message;}
// GitHub comments deliver durable confirmations without artifact-host access.
await api(`/repos/${repo}/issues/${number}/comments`,'POST',{body:renderWorkerResult('merge',result)});
fs.writeFileSync('merge-result.json',JSON.stringify(result,null,2)+'\n');
fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,`${result.accepted?'Merged':'Not merged'} PR #${number}. ${result.reason??''}\n`);console.log(JSON.stringify(result));

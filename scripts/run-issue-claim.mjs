import {renderWorkerResult} from './worker-result.mjs';
import fs from 'node:fs';
import {githubAPI,githubPages,linkedPulls,transitionClaim,renderClaim,workSpec,canonicalIssueNumber,readinessDependencyIds} from './issue-claim-contract.mjs';
import {evidenceRequirement,loadEvidencePolicy} from './evidence-policy.mjs';

const event=JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH,'utf8')),input=event.inputs??{},repo=process.env.GITHUB_REPOSITORY;
if(process.env.GITHUB_REF!=='refs/heads/main'||!/^[-\w.]+\/[-\w.]+$/.test(repo??''))throw Error('Claim mutations run only from trusted main');
const number=canonicalIssueNumber(input.issue_number);
if(!Number.isSafeInteger(number)||number<1)throw Error('Invalid issue number');
const api=githubAPI(process.env.GH_TOKEN),result={accepted:false,request_id:input.request_id,issue_number:number};
try{
 const [issue,comments,prs]=await Promise.all([api(`/repos/${repo}/issues/${number}`),githubPages(api,`/repos/${repo}/issues/${number}/comments`),linkedPulls(api,repo,number)]);
 const spec=input.action==='release'?null:workSpec(issue.body);
 if(spec&&loadEvidencePolicy().mode==='enforce-new')evidenceRequirement(issue,spec,undefined,input.branch);
 const geographyGate=spec?.mode==='content'?JSON.parse(fs.readFileSync('data/research-geography-gate.json','utf8')):null;
 const ids=readinessDependencyIds(spec,geographyGate);
 const dependencies=await Promise.all([...ids].map(id=>api(`/repos/${repo}/issues/${id}`)));
 const otherIssues=spec?.mode==='geography'?await githubPages(api,`/repos/${repo}/issues?state=open&labels=type%3Ageography`):[];
 const [freshIssue,freshComments,freshDependencies,freshPRs,freshOtherIssues]=await Promise.all([
  api(`/repos/${repo}/issues/${number}`),githubPages(api,`/repos/${repo}/issues/${number}/comments`),
  Promise.all(ids.map(id=>api(`/repos/${repo}/issues/${id}`))),linkedPulls(api,repo,number),
  spec?.mode==='geography'?githubPages(api,`/repos/${repo}/issues?state=open&labels=type%3Ageography`):[]]);
 const snapshot=value=>JSON.stringify([value.number,value.state,value.body,value.updated_at,(value.labels??[]).map(x=>x.name??x).sort()]);
 const commentSnapshot=rows=>JSON.stringify(rows.map(c=>[c.id,c.body,c.user?.login]));
 if(snapshot(freshIssue)!==snapshot(issue)||commentSnapshot(freshComments)!==commentSnapshot(comments)||
  JSON.stringify(freshDependencies.map(snapshot))!==JSON.stringify(dependencies.map(snapshot))||JSON.stringify(freshPRs)!==JSON.stringify(prs)||
  JSON.stringify(freshOtherIssues.map(snapshot))!==JSON.stringify(otherIssues.map(snapshot)))throw Error('Issue, ownership, dependencies or linked PR budget changed during claim; reread before retry');
 const next=transitionClaim({issue:freshIssue,comments:freshComments,prs:freshPRs,dependencies:freshDependencies,geographyGate,otherIssues:freshOtherIssues,request:{...input,live_work:input.live_work==='true'}}),claim=next.claim;
 // The canonical bot comment is authority; labels are a repairable display projection.
 if(claim.comment_id)await api(`/repos/${repo}/issues/comments/${claim.comment_id}`,'PATCH',{body:renderClaim(claim)});
 else claim.comment_id=(await api(`/repos/${repo}/issues/${number}/comments`,'POST',{body:renderClaim(claim)})).id;
 const hasClaimLabel=issue.labels.some(l=>l.name==='status:claimed');
 if(claim.active&&!hasClaimLabel)await api(`/repos/${repo}/issues/${number}/labels`,'POST',{labels:['status:claimed']});
 if(!claim.active&&hasClaimLabel)await api(`/repos/${repo}/issues/${number}/labels/${encodeURIComponent('status:claimed')}`,'DELETE');
 if(input.action==='recover'&&issue.labels.some(l=>l.name==='coordination:recovery-approved'))await api(`/repos/${repo}/issues/${number}/labels/${encodeURIComponent('coordination:recovery-approved')}`,'DELETE');
 if(input.action!=='renew'||next.previous?.branch!==claim.branch)await api(`/repos/${repo}/issues/${number}/comments`,'POST',{body:`Worker coordination: ${input.action} by \`${claim.worker_id}\`, branch \`${claim.branch}\`, lease ${claim.expires_at}. Request \`${input.request_id}\`.${next.previous?` Previous branch retained: \`${next.previous.branch}\`.`:''}${input.reason?` Reason: ${input.reason}`:''}`});
 Object.assign(result,{accepted:true,claim,replayed:Boolean(next.replayed)});
}catch(error){result.reason=error.message;}
// GitHub comments deliver durable confirmations without artifact-host access.
await api(`/repos/${repo}/issues/${number}/comments`,'POST',{body:renderWorkerResult('claim',result)});
fs.writeFileSync('claim-result.json',JSON.stringify(result,null,2)+'\n');
fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,`${result.accepted?'Accepted':'Not accepted'} ${input.action} for #${number}. ${result.reason??''}\n`);
console.log(JSON.stringify(result));

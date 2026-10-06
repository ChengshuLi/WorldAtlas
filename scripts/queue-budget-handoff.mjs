import fs from 'node:fs';
import {workSpec,linkedPulls} from './issue-claim-contract.mjs';
import {validateIssuePRBody} from './check-handoff-scope.mjs';
import {evidenceRequirement} from './evidence-policy.mjs';
import {readQueueDisposition,dispositionReferences} from './queue-disposition.mjs';

// Trusted queue code checks prospective last-partial-PR handoffs. Existing work
// keeps its scope; the audit surfaces its retrospective disposition separately.
export async function checkBudgetHandoff({api,repo,issue,pr,policy=JSON.parse(fs.readFileSync(new URL('../.github/queue-handoff-policy.json',import.meta.url),'utf8')),prs}) {
  const spec=workSpec(issue.body);
  if(!Number.isFinite(Date.parse(policy.handoff_activation_time)))throw Error('Invalid queue handoff activation');
  if(!(spec.queue_handoff_required || Date.parse(issue.created_at)>=Date.parse(policy.handoff_activation_time)))return {required:false};
  if(repo!==policy.repository)throw Error('Queue handoff policy repository mismatch');
  const prior=(prs ?? await linkedPulls(api,repo,issue.number)).filter(row=>row.merged_at && row.number!==pr.number);
  if(prior.length+1<spec.max_prs || validateIssuePRBody(pr.body).issue_action==='close')return {required:false};
  const comments=[{id:1,body:pr.body}];
  const ids=dispositionReferences(comments);
  if(ids.length>50)throw Error('Budget handoff exceeds bounded follow-up inventory');
  const relatedIssues=await Promise.all(ids.map(id=>api(`/repos/${repo}/issues/${id}`)));
  const result=readQueueDisposition(comments,{issue,scope:spec,prs:[...prior,{...pr,merged_at:'candidate'}],relatedIssues});
  if(!result.value)throw Error(`Last partial PR needs a reviewed acceptance-to-follow-up handoff: ${result.error ?? 'missing disposition'}`);
  if(!result.value.criteria.some(row=>row.status==='remaining'))throw Error('A partial final-budget PR needs remaining-work issues; use Closes only if all original acceptance is satisfied');
  for(const followup of relatedIssues) {
    if(followup.state==='closed')continue; // Preserve completed children and their evidence.
    const labels=(followup.labels??[]).map(label=>label.name??label);
    if(!labels.includes('kind:work-item'))throw Error('Remaining work must point to bounded children, not umbrellas');
    evidenceRequirement(followup,workSpec(followup.body));
  }
  return {required:true,disposition:result.value};
}

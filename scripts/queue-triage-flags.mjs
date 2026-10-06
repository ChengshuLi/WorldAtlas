import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {githubAPI} from './issue-claim-contract.mjs';

export const triageLabel='coordination:triage-needed';
// Informational history and legacy wording alone must not flood the work queue.
const actionable=new Set(['kind-label','type-label','umbrella-ready','invalid-scope','lane-mode',
  'invalid-evidence-contract','invalid-claim','ready-explicit-blocker','ready-blocked','expired-claim','claim-label-drift',
  'pr-budget','pr-budget-review','invalid-disposition','review-blocked','review-missing-ready','ownership-overlap']);
const digest=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
const labels=issue=>(issue.labels??[]).map(label=>label.name??label);

export async function flagOriginalIssues({api,repo,report}) {
  if(!/^[-\w.]+\/[-\w.]+$/.test(repo) || report.version!==1 || report.repository!==repo || !['complete','incomplete'].includes(report.status))throw Error('Invalid queue report identity');
  const needed=new Set(report.findings.filter(row=>actionable.has(row.code)).map(row=>row.issue));
  const result={added:[],removed:[],unchanged:[],changed_since_audit:[]};
  const snapshots=report.issue_snapshots??[];
  // A report is not an approval. Mutate only the dedicated attention label, never
  // the full label list, issue body, ready/blocked status, scope or canonical claim.
  for(const snapshot of snapshots) {
    const number=snapshot.number;
    if(!Number.isSafeInteger(number) || number<1)throw Error('Invalid snapshot issue');
    const wants=needed.has(number);
    if(!wants && report.status!=='complete')continue;
    if(wants===snapshot.triage_present){result.unchanged.push(number);continue;}
    const current=await api(`/repos/${repo}/issues/${number}`);
    if(current.state!=='open' || current.pull_request || !snapshot.updated_at || current.updated_at!==snapshot.updated_at || digest(current.body??'')!==snapshot.body_sha256 ||
      JSON.stringify(labels(current).filter(label=>label!==triageLabel).sort())!==JSON.stringify(snapshot.labels)) {
      result.changed_since_audit.push(number);continue;
    }
    const has=labels(current).includes(triageLabel);
    if(wants===has){result.unchanged.push(number);continue;}
    const route=`/repos/${repo}/issues/${number}/labels`;
    if(wants)await api(route,'POST',{labels:[triageLabel]});
    else await api(`${route}/${encodeURIComponent(triageLabel)}`,'DELETE');
    const saved=await api(`/repos/${repo}/issues/${number}`);
    if(labels(saved).includes(triageLabel)!==wants)throw Error(`Triage flag readback mismatch on #${number}`);
    result[wants?'added':'removed'].push(number);
  }
  return result;
}
if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const policy=JSON.parse(fs.readFileSync('.github/queue-handoff-policy.json','utf8'));
  if(process.env.GITHUB_REF!=='refs/heads/main' || process.env.GITHUB_REPOSITORY!==policy.repository)throw Error('Only the trusted main workflow may flag queue issues');
  const api=githubAPI(process.env.GH_TOKEN);
  // An existing label is required; setup belongs to the reviewed rollout.
  await api(`/repos/${policy.repository}/labels/${encodeURIComponent(triageLabel)}`);
  console.log(JSON.stringify(await flagOriginalIssues({api,repo:policy.repository,report:JSON.parse(fs.readFileSync(process.argv[2]??'queue-readiness-report.json','utf8'))})));
}

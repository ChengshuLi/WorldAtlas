import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {githubAPI} from './issue-claim-contract.mjs';
import {validateIssuePRBody} from './check-handoff-scope.mjs';
import {auditQueue} from './queue-readiness-audit.mjs';
import {flagOriginalIssues,triageLabel} from './queue-triage-flags.mjs';

export async function reconcileQueueEvent({api,repo,event,kind,result}) {
  let number;
  if(kind==='claim') {
    if(!result?.accepted || event.inputs?.action!=='release')return {skipped:'No accepted release'};
    number=result.issue_number;
  } else if(kind==='merge') {
    if(!result?.accepted || result.status!=='merged')return {skipped:'No accepted merge'};
    // Confirm remote outcome even for replayed receipts; never infer a merge.
    const pr=await api(`/repos/${repo}/pulls/${result.pr_number}`);
    if(!pr.merged_at || !pr.merge_commit_sha || pr.head?.sha!==event.inputs?.expected_head)throw Error('Queue event merge outcome not confirmed');
    number=validateIssuePRBody(pr.body).github_issue;
  } else if(kind==='issues' || kind==='issue_comment') {
    if(event.issue?.pull_request || event.label?.name===triageLabel)return {skipped:'PR comment or attention-label projection'};
    number=event.issue?.number;
  } else if(kind==='pull_request_target') {
    if(event.action!=='closed' || !event.pull_request?.merged)return {skipped:'No merged PR'};
    const pr=await api(`/repos/${repo}/pulls/${event.pull_request.number}`);
    if(!pr.merged_at)throw Error('Event merge not confirmed');
    number=validateIssuePRBody(pr.body).github_issue;
  } else throw Error('Unsupported queue event');
  if(!Number.isSafeInteger(number) || number<1)throw Error('Invalid affected issue');
  const report=await auditQueue({api,repo,targetIssue:number});
  const flags=await flagOriginalIssues({api,repo,report});
  return {report,flags};
}
if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const policy=JSON.parse(fs.readFileSync('.github/queue-handoff-policy.json','utf8'));
  if(process.env.GITHUB_REF!=='refs/heads/main' || process.env.GITHUB_REPOSITORY!==policy.repository)throw Error('Queue events run only from trusted main');
  const event=JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH,'utf8'));
  const kind=process.argv[2]??process.env.GITHUB_EVENT_NAME;
  const resultFile=kind==='claim'?'claim-result.json':kind==='merge'?'merge-result.json':null;
  const outcome=await reconcileQueueEvent({api:githubAPI(process.env.GH_TOKEN),repo:policy.repository,event,kind,result:resultFile?JSON.parse(fs.readFileSync(resultFile,'utf8')):undefined});
  fs.writeFileSync('queue-event-report.json',JSON.stringify(outcome,null,2)+'\n');
  if(outcome.report?.status==='incomplete')process.exitCode=1;
}

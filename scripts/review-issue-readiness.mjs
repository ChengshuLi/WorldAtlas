import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {githubAPI,canonicalIssueNumber} from './issue-claim-contract.mjs';
import {auditQueue} from './queue-readiness-audit.mjs';

// Issue creation/triage uses the same scope/evidence/lease/budget checks as the
// scanner. This read-only preflight cannot approve sources or mark work ready.
export async function reviewIssueReadiness({api,repo,number}) {
  number=canonicalIssueNumber(number);
  const current=await api(`/repos/${repo}/issues/${number}`);
  if(current.state!=='open' || current.pull_request)throw Error('Readiness preflight needs an open issue, not a PR or completed work');
  const report=await auditQueue({api,repo,targetIssue:canonicalIssueNumber(number)});
  return {issue:number,observed_at:report.observed_at,coverage:report.status,
    findings:report.findings.filter(row=>row.issue===number),
    failures:report.failures,
    decision:'Human readiness review required; recheck inputs before changing status. No labels or claims changed.'};
}
if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const [repo,rawNumber,output='issue-readiness-review.json']=process.argv.slice(2);
  const review=await reviewIssueReadiness({api:githubAPI(process.env.GH_TOKEN),repo,number:canonicalIssueNumber(rawNumber)});
  fs.writeFileSync(output,JSON.stringify(review,null,2)+'\n');
  if(review.coverage==='incomplete')process.exitCode=1;
}

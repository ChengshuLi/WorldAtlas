import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {githubAPI,githubPages,linkedPulls,canonicalIssueNumber,workSpec,readClaim,assertIssueReadiness,readinessDependencyIds} from './issue-claim-contract.mjs';

const hash=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
const labels=issue=>(issue.labels??[]).map(x=>typeof x==='string'?x:x.name).sort();
export const readinessSnapshot=issue=>({number:issue.number,state:issue.state,body:issue.body,labels:labels(issue),updated_at:issue.updated_at});

// Complete read-only preflight. Findings never mutate readiness or grant science
// approval. Re-read the issue before acting; GitHub has no atomic issue CAS.
export async function reviewIssueReadiness({api,repo,number,branch,evidencePolicy,geographyGate=null}) {
 if(!/^[-\w.]+\/[-\w.]+$/.test(repo))throw Error('Invalid repository');
 number=canonicalIssueNumber(number);const base=`/repos/${repo}`;
 const result={issue:number,coverage:'incomplete',eligible:false,findings:[],observed_at:new Date().toISOString()};
 try {
  const issue=await api(`${base}/issues/${number}`),spec=workSpec(issue.body);
  branch??=({engineering:'engineering',geography:'geography','source-only':'research',content:'research'}[spec.mode])+`/readiness-${number}`;
  if(spec.mode==='content'&&!geographyGate)geographyGate=JSON.parse(fs.readFileSync(new URL('../data/research-geography-gate.json',import.meta.url),'utf8'));
  const ids=readinessDependencyIds(spec,geographyGate);
  const [comments,prs,dependencies,otherIssues]=await Promise.all([
   githubPages(api,`${base}/issues/${number}/comments`),linkedPulls(api,repo,number),
   Promise.all(ids.map(id=>api(`${base}/issues/${id}`))),
   spec.mode==='geography'?githubPages(api,`${base}/issues?state=open&labels=type%3Ageography`):[]]);
  if(spec.mode==='content'&&!geographyGate)geographyGate=JSON.parse(fs.readFileSync(new URL('../data/research-geography-gate.json',import.meta.url),'utf8'));
  try {assertIssueReadiness({issue,branch,dependencies,prs,otherIssues,comments,geographyGate,evidencePolicy,requireReady:false});}
  catch(e){result.findings.push(e.message);}
  const claim=readClaim(comments);
  if(claim?.active)result.findings.push('Canonical claim belongs to its holder; expiry alone never authorizes takeover');
  if(claim?.live_work)result.findings.push('Preserve the existing live operation');
  if(prs.some(p=>p.state==='open'))result.findings.push('An open linked PR needs its existing owner and checkpoint reviewed');
  const [after,afterComments,afterDependencies,afterPRs,afterOtherIssues]=await Promise.all([api(`${base}/issues/${number}`),
   githubPages(api,`${base}/issues/${number}/comments`),Promise.all(ids.map(id=>api(`${base}/issues/${id}`))),linkedPulls(api,repo,number),
   spec.mode==='geography'?githubPages(api,`${base}/issues?state=open&labels=type%3Ageography`):[]]);
  if(hash(prs)!==hash(afterPRs)||hash(otherIssues.map(readinessSnapshot))!==hash(afterOtherIssues.map(readinessSnapshot)))throw Error('Linked PR budget or geography ownership changed during readiness review; reread before acting');
  if(hash(comments)!==hash(afterComments)||hash(dependencies.map(readinessSnapshot))!==hash(afterDependencies.map(readinessSnapshot)))throw Error('Ownership, issue history or dependencies changed during readiness review; reread before acting');
  if(hash(readinessSnapshot(issue))!==hash(readinessSnapshot(after)))throw Error('Issue changed during readiness review; reread before acting');
  result.snapshot=readinessSnapshot(after);result.dependencies=dependencies.map(readinessSnapshot);
  result.coverage='complete';result.eligible=!result.findings.length;
 }catch(e){result.findings.push(e.message);}
 result.decision='Mechanical eligibility only. Inspect original acceptance, waits and scientific/production evidence; reread issue, claim and dependencies immediately before a narrow mutation. No labels or claims changed.';
 return result;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const [repo,rawNumber,output='issue-readiness-review.json',branch]=process.argv.slice(2);
 const review=await reviewIssueReadiness({api:githubAPI(process.env.GH_TOKEN),repo,number:rawNumber,branch});
 fs.writeFileSync(output,JSON.stringify(review,null,2)+'\n');
 console.log(JSON.stringify(review));if(review.coverage!=='complete'||!review.eligible)process.exitCode=1;
}

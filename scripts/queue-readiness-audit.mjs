import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {workSpec, readClaim, githubPages, githubAPI, assertIssueReadiness} from './issue-claim-contract.mjs';
import {validateIssuePRBody} from './check-handoff-scope.mjs';

const types = new Set(['type:engineering', 'type:geography', 'type:history-research']);
const labelsOf = issue => (issue.labels ?? []).map(x => typeof x === 'string' ? x : x.name);
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');

// Explicit markers are authoritative for access/decision blockers. Legacy prose is
// a review warning, never machine permission to unblock an issue.
export function commentBlockers(comments) {
  const latest = new Map(), warnings = [];
  for (const c of [...comments].sort((a,b) => a.id-b.id)) {
    for (const match of (c.body ?? '').matchAll(/<!-- worldatlas-blocker:v1\s*\n([\s\S]*?)\n-->/g)) {
      try {
        const value = JSON.parse(match[1]);
        if (!value.id || typeof value.active !== 'boolean' || !value.reason) throw Error('invalid blocker');
        latest.set(value.id, {...value, comment_id:c.id});
      } catch { warnings.push({comment_id:c.id, reason:'Malformed blocker marker'}); }
    }
    if (/\b(blocked|blocker|cannot access|access denied|HTTP (401|403)|source unavailable|requires? (?:source|private|operator|user).*access)\b/i.test(c.body ?? '') && !c.body.includes('worldatlas-blocker:v1')) {
      warnings.push({comment_id:c.id, reason:'Possible unresolved source/access/decision blocker; inspect comment'});
    }
  }
  return {active:[...latest.values()].filter(x=>x.active), warnings};
}

export function assessIssue(issue, {dependencies=[], comments=[], prs=[], now=Date.now()}={}) {
  const labels=labelsOf(issue), findings=[];
  const add=(code,details)=>findings.push({issue:issue.number,code,details});
  if (issue.pull_request || issue.state!=='open') return {findings,scope:null,claim:null};
  const kinds=labels.filter(x=>x.startsWith('kind:')), lanes=labels.filter(x=>x.startsWith('type:'));
  if (kinds.length!==1 || !['kind:work-item','kind:umbrella'].includes(kinds[0])) add('kind-label','Specify exactly one known kind');
  if (lanes.length!==1 || !types.has(lanes[0])) add('type-label','Unknown/missing/ambiguous type; requires reviewed ownership policy');
  if (labels.includes('kind:umbrella')) {
    if (labels.includes('status:ready')) add('umbrella-ready','Umbrellas cannot be claimed');
    return {findings,scope:null,claim:null};
  }
  let scope=null, claim=null;
  try { scope=workSpec(issue.body); } catch (e) { add('invalid-scope',e.message); }
  if (scope && lanes.length===1 && ({engineering:'type:engineering',geography:'type:geography','source-only':'type:history-research',content:'type:history-research'}[scope.mode]!==lanes[0])) add('lane-mode','Issue type and scope mode disagree');
  try { claim=readClaim(comments); } catch(e) { add('invalid-claim',e.message); }
  const open=scope?.depends_on.filter(id=>!dependencies.some(d=>d.number===id && d.state==='closed')) ?? [];
  if (labels.includes('status:ready') && (open.length || labels.includes('status:blocked'))) add('ready-blocked',{open_dependencies:open,blocked_label:labels.includes('status:blocked')});
  const blockers=commentBlockers(comments);
  if (blockers.active.length) add('explicit-blocker',blockers.active);
  if (blockers.warnings.length) add('comment-review',blockers.warnings);
  const openPRs=prs.filter(p=>p.state==='open');
  if (openPRs.length) add('open-pr',openPRs.map(p=>({number:p.number,branch:p.head?.ref})));
  if (claim?.active) add(Date.parse(claim.expires_at)<=now?'expired-claim':'active-claim',{worker:claim.worker_id,branch:claim.branch,expires_at:claim.expires_at,live_work:Boolean(claim.live_work)});
  if (claim?.live_work) add('live-operation','Coordinate the existing holder; do not recover automatically');
  if (labels.includes('status:claimed')!==Boolean(claim?.active)) add('claim-label-drift','Canonical bot claim and convenience label differ');
  if (scope && prs.filter(p=>p.merged_at).length>=scope.max_prs) add('pr-budget','Review original acceptance: close only if complete; otherwise reuse bounded continuation or preserve an explicit wait');
  if(scope)try {assertIssueReadiness({issue,branch:({engineering:'engineering',geography:'geography','source-only':'research',content:'research'}[scope.mode])+'/readiness',dependencies,prs,comments,requireReady:false});}catch(e){add('eligibility-rejection',e.message);}
  if (scope && !open.length && !claim?.active && !openPRs.length && !blockers.active.length) {
    if (labels.includes('status:blocked')) add('review-blocked','Declared dependencies closed; inspect semantic/source/publication and comment blockers before changing status');
    else if (!labels.includes('status:ready')) add('review-missing-ready','Candidate for human triage; dependency closure alone is not approval');
  }
  if (scope?.mode==='content') add('regional-approval-review','Revalidate complete published regional certificates, exact subjects and release pins; this audit does not authorize imports');
  return {findings,scope,claim};
}

async function boundedMap(items, fn, concurrency=4) {
  const output=new Array(items.length); let next=0;
  await Promise.all(Array.from({length:Math.min(concurrency,items.length)},async()=>{
    while(next<items.length) { const index=next++; output[index]=await fn(items[index]); }
  }));
  return output;
}
export async function auditQueue({api,repo,previous=null,now=Date.now()}) {
  if (!/^[-\w.]+\/[-\w.]+$/.test(repo)) throw Error('Invalid repository');
  if (previous && (previous.version!==1 || previous.repository!==repo || previous.status!=='complete')) throw Error('Previous checkpoint must be a complete audit of this repository');
  const report={version:1,repository:repo,status:'incomplete',observed_at:new Date(now).toISOString(),last_successful_coverage:previous?.last_successful_coverage ?? null,findings:[],failures:[],new_findings:[],resolved_findings:[]};
  const base=`/repos/${repo}`;
  let issues, pulls;
  try { [issues,pulls]=await Promise.all([githubPages(api,`${base}/issues?state=open`),githubPages(api,`${base}/pulls?state=open`)]); }
  catch(e) { report.failures.push(e.message); return report; }
  const linked=new Map();
  for (const pr of pulls) {
    try { const id=validateIssuePRBody(pr.body).github_issue; linked.set(id,[...(linked.get(id)??[]),pr]); } catch { /* Invalid PR linkage is a separate handoff check. */ }
  }
  const dependencyCache=new Map();
  const getDependency=id=>{
    if (!dependencyCache.has(id)) dependencyCache.set(id,api(`${base}/issues/${id}`));
    return dependencyCache.get(id);
  };
  const candidates=issues.filter(x=>!x.pull_request);
  const assessments=await boundedMap(candidates,async issue=>{
    try {
      let scope; try {scope=workSpec(issue.body);} catch {scope=null;}
      const [comments,dependencies]=await Promise.all([githubPages(api,`${base}/issues/${issue.number}/comments`),Promise.all((scope?.depends_on??[]).map(getDependency))]);
      // Exhaust the timeline too: PR budget includes prior merged work, not just open PRs.
      const timeline=await githubPages(api,`${base}/issues/${issue.number}/timeline`);
      const ids=new Set((linked.get(issue.number)??[]).map(p=>p.number));
      for (const event of timeline) {
        const source=event.source?.issue;
        if (!source?.pull_request) continue;
        try {if(validateIssuePRBody(source.body).github_issue===issue.number)ids.add(source.number);} catch {}
      }
      const fetched=await Promise.all([...ids].map(id=>api(`${base}/pulls/${id}`)));
      const prs=fetched.filter(pr=>{try{return validateIssuePRBody(pr.body).github_issue===issue.number;}catch{return false;}});
      return {issue,...assessIssue(issue,{dependencies,comments,prs,now})};
    } catch(e) {report.failures.push({issue:issue.number,error:e.message});return null;}
  });
  for (const row of assessments.filter(Boolean)) report.findings.push(...row.findings);
  const owned=assessments.filter(x=>x?.scope?.mode==='geography');
  for(let i=0;i<owned.length;i++)for(let j=i+1;j<owned.length;j++) {
    const a=owned[i],b=owned[j];
    const overlap=a.scope.owned_paths.filter(p=>b.scope.owned_paths.some(q=>p.startsWith(q)||q.startsWith(p)));
    if(overlap.length) report.findings.push({issue:a.issue.number,code:'ownership-overlap',details:{other_issue:b.issue.number,paths:overlap,workers:[a.claim?.worker_id??null,b.claim?.worker_id??null]}});
  }
  report.findings.sort((a,b)=>a.issue-b.issue || a.code.localeCompare(b.code));
  report.findings=report.findings.map(x=>({...x,fingerprint:digest(x)}));
  report.inspected_issues=candidates.length;
  if (!report.failures.length) {
    report.status='complete'; report.last_successful_coverage=report.observed_at;
    const old=new Set((previous?.findings??[]).map(x=>x.fingerprint)),current=new Set(report.findings.map(x=>x.fingerprint));
    report.new_findings=report.findings.filter(x=>!old.has(x.fingerprint));
    report.resolved_findings=(previous?.findings??[]).filter(x=>!current.has(x.fingerprint));
  }
  return report;
}
if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const args=process.argv.slice(2), repo=args[0]??process.env.GITHUB_REPOSITORY, output=args[1]??'queue-readiness-report.json', previousFile=args[2];
  let previous=null;
  if(previousFile && fs.existsSync(previousFile)) previous=JSON.parse(fs.readFileSync(previousFile,'utf8'));
  const report=await auditQueue({api:githubAPI(process.env.GH_TOKEN),repo,previous});
  fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');
  if(process.env.GITHUB_STEP_SUMMARY) fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,`Queue audit: ${report.status}; ${report.inspected_issues??0} issues; ${report.new_findings.length} changed findings; ${report.resolved_findings.length} resolved. Inspect the report artifact; no labels or claims were changed.\n`);
  if(report.status==='incomplete')process.exitCode=1;
}

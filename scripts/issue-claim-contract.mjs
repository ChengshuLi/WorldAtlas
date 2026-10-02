import {laneForBranch,validateIssueMetadata,validateIssuePRBody} from './check-handoff-scope.mjs';

export const claimMarker='worldatlas-claim:v1';
export function canonicalIssueNumber(value){if(!/^[1-9]\d*$/.test(String(value))||!Number.isSafeInteger(Number(value)))throw Error('Use a canonical positive issue number, without leading zeros or exponent notation');return Number(value);}
export function workSpec(body){
 const matches=[...String(body??'').matchAll(/<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->/g)];
 if(matches.length!==1)throw Error('A reviewed worldatlas-work:v1 scope is required');
 const spec=JSON.parse(matches[0][1]);
 if(!Number.isInteger(spec.max_prs)||spec.max_prs<1||spec.max_prs>3||!Array.isArray(spec.depends_on)||spec.depends_on.some(n=>!Number.isSafeInteger(n)||n<1)||!spec.scope||typeof spec.scope!=='string')throw Error('Work items need bounded scope, 1–3 PRs and explicit dependency issue numbers');
 if(!['content','source-only','engineering'].includes(spec.mode))throw Error('Declare engineering, content or source-only mode');
 if(spec.mode==='content'&&(!spec.geographic_release||!spec.scope_manifest||!spec.territory_match_review))throw Error('Content issues need released geography, an entity/interval/attribute scope manifest and territory-match review');
 return spec;
}
export function readClaim(comments){
 const canonical=comments.filter(c=>c.user?.login==='github-actions[bot]'&&c.body?.startsWith('**Worker reservation:**'));
 if(canonical.length>1)throw Error('Multiple canonical claims require operator repair');
 if(!canonical.length)return null;
 const comment=canonical[0],match=/<!-- worldatlas-claim:v1\n([\s\S]*?)\n-->/.exec(comment.body);
 if(!match)throw Error('Malformed canonical claim; preserve it and request repair');
 const claim=JSON.parse(match[1]);
 if(claim.version!==1||typeof claim.active!=='boolean'||!claim.worker_id||!claim.claim_id||!claim.branch||!Number.isFinite(Date.parse(claim.expires_at)))throw Error('Invalid canonical claim');
 return {comment_id:comment.id,...claim};
}
export function renderClaim(claim){
 const state={...claim};delete state.comment_id;
 return `**Worker reservation:** ${claim.active?'claimed':'released'} · ${claim.worker_id}\n\nBranch: \`${claim.branch}\` · lease expires: ${claim.expires_at} · live work pending: ${Boolean(claim.live_work)}\n\n<!-- ${claimMarker}\n${JSON.stringify(state)}\n-->`;
}
export function transitionClaim({issue,comments,prs=[],dependencies=[],request,geographyGate=null,now=Date.now()}){
 const {action,worker_id,claim_id,branch,request_id}=request;
 if(!['claim','renew','release','recover'].includes(action)||!/^[-a-zA-Z0-9_:.]{1,100}$/.test(worker_id??'')||!/^[-a-zA-Z0-9]{16,100}$/.test(claim_id??'')||!/^[-a-zA-Z0-9]{16,100}$/.test(request_id??''))throw Error('Invalid claim action or unique worker/request IDs');
 const lane=laneForBranch(branch),current=readClaim(comments);
 if(current?.request_id===request_id)return {claim:current,replayed:true};
 const openPR=prs.find(p=>p.state==='open'&&p.head?.ref===current?.branch);
 const own=current?.worker_id===worker_id&&current?.claim_id===claim_id;
 const labels=(issue.labels??[]).map(l=>typeof l==='string'?l:l.name);
 if(action==='release'){
  if(!current?.active||!own)throw Error('Only the current claim holder may release');
  if(openPR||current.live_work)throw Error('Preserve the active PR/live operation; finish or hand over before release');
  return {claim:{...current,active:false,request_id,released_at:new Date(now).toISOString()},previous:current};
 }
 validateIssueMetadata(branch,issue);
 const spec=workSpec(issue.body);
 if(lane.lane==='engineering'&&spec.mode!=='engineering'||lane.lane==='research'&&spec.mode==='engineering')throw Error('Scope mode must agree with the issue lane');
 if(labels.includes('kind:umbrella')||!labels.includes('kind:work-item')||!labels.includes('status:ready')||labels.includes('status:blocked'))throw Error('Only reviewed ready work items may be claimed; split umbrellas or resolve blockers first');
 if(spec.depends_on.some(id=>!dependencies.some(d=>d.number===id&&d.state==='closed')))throw Error('A dependency is still open or missing');
 if(spec.mode==='content'&&(!geographyGate?.ready_for_location_attributes||!geographyGate.semantic_complete||geographyGate.approved_release?.release_id!==spec.geographic_release||!dependencies.some(d=>d.number===7&&d.state==='closed')))throw Error('Worldwide hierarchy approval is required before location-content imports');
 const merged=prs.filter(p=>p.merged_at).length;
 if(merged>=spec.max_prs&&!(action==='renew'&&branch===current?.branch))throw Error('PR budget exhausted; split remaining scope rather than monopolizing the issue');
 if(action==='renew'){
  if(!current?.active||!own)throw Error('Only the current holder may renew or change branch');
  if(branch!==current.branch&&(openPR||current.live_work))throw Error('Merge/close the previous PR and complete live work before rotating branches');
 }else if(action==='claim'&&current?.active){
  if(!own)throw Error(Date.parse(current.expires_at)<=now?'Expired reservation requires explicit recovery; do not discard existing work':'Issue already claimed by another worker');
  if(branch!==current.branch)throw Error('Renew to rotate an owned branch');
 }else if(action==='recover'){
  if(!current?.active||Date.parse(current.expires_at)>now||!labels.includes('coordination:recovery-approved')||String(request.reason??'').trim().length<10||openPR||current.live_work)throw Error('Recovery requires expired lease, explicit approval/reason and no active PR/live operation');
 }
 const expires_at=new Date(now+24*60*60*1000).toISOString();
 const claim={version:1,active:true,worker_id,claim_id,branch,request_id,issue_number:issue.number,claimed_at:own?current.claimed_at:new Date(now).toISOString(),updated_at:new Date(now).toISOString(),expires_at,live_work:action==='renew'?Boolean(request.live_work):false,mode:spec.mode,max_prs:spec.max_prs};
 return {claim,previous:current};
}
export function verifyClaimForPR({branch,issue,comments,prs=[],now=Date.now()}){
 validateIssueMetadata(branch,issue);const spec=workSpec(issue.body),claim=readClaim(comments);
 const labels=issue.labels.map(l=>typeof l==='string'?l:l.name);
 if(labels.includes('kind:umbrella')||labels.includes('status:blocked')||!labels.includes('status:ready'))throw Error('Issue is not ready for implementation');
 if(prs.filter(p=>p.merged_at).length>=spec.max_prs)throw Error('Issue PR budget exhausted; create a bounded follow-up');
 if(!claim?.active||claim.branch!==branch||Date.parse(claim.expires_at)<=now)throw Error('PR needs a current unexpired claim for this exact branch');
 return {worker_id:claim.worker_id,claim_id:claim.claim_id,mode:spec.mode};
}
export async function githubPages(api,route){
 const all=[];for(let page=1;page<=100;page++){const rows=await api(`${route}${route.includes('?')?'&':'?'}per_page=100&page=${page}`);const list=Array.isArray(rows)?rows:rows?.check_runs;if(!Array.isArray(list))throw Error('Invalid paginated GitHub response');all.push(...list);if(list.length<100)return all;}throw Error('GitHub pagination limit reached; stop rather than assume completeness');
}
export async function linkedPulls(api,repo,number){
 const timeline=await githubPages(api,`/repos/${repo}/issues/${number}/timeline`),ids=new Set();
 for(const event of timeline){const source=event.source?.issue;if(!source?.pull_request)continue;try{if(validateIssuePRBody(source.body??'').github_issue===number)ids.add(source.number);}catch{}}
 return Promise.all([...ids].map(id=>api(`/repos/${repo}/pulls/${id}`)));
}
export function githubAPI(token){
 if(!token)throw Error('Read/write GitHub token required');
 return async(route,method='GET',body)=>{
  const response=await fetch('https://api.github.com'+route,{method,headers:{Authorization:`Bearer ${token}`,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28',...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(20000)});
  if(!response.ok)throw Error(`GitHub ${method} request failed (HTTP ${response.status})`);
  return response.status===204?null:response.json();
 };
}

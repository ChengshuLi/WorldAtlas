import {quotaDelay,completeReads} from './github-quota.mjs';
import {conditionalSnapshots} from './github-snapshots.mjs';
import {evidenceRequirement} from './evidence-policy.mjs';
import {laneForBranch,validateIssueMetadata,validateGeographyOwnedPaths,validateEngineeringOwnedPaths,validateLanePaths} from './check-handoff-scope.mjs';

const HTTP_ATTEMPT_MS = 20_000;

export const claimMarker='worldatlas-claim:v1';
export function canonicalIssueNumber(value){if(!/^[1-9]\d*$/.test(String(value))||!Number.isSafeInteger(Number(value)))throw Error('Use a canonical positive issue number, without leading zeros or exponent notation');return Number(value);}
// max_prs is retained as a planning estimate for compatible v1 contracts/claims.
// Scope, ownership and acceptance bound work; merged-PR count does not.
export function workSpec(body){
 const matches=[...String(body??'').matchAll(/<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->/g)];
 if(matches.length!==1)throw Error('A reviewed worldatlas-work:v1 scope is required');
 const spec=JSON.parse(matches[0][1]);
 if(!Number.isSafeInteger(spec.max_prs)||spec.max_prs<1||!Array.isArray(spec.depends_on)||spec.depends_on.some(n=>!Number.isSafeInteger(n)||n<1)||!spec.scope||typeof spec.scope!=='string')throw Error('Work items need bounded scope, a positive PR estimate and explicit dependency issue numbers');
 if(!['content','source-only','engineering','geography'].includes(spec.mode))throw Error('Declare engineering, geography, content or source-only mode');
 if(spec.mode==='geography')validateGeographyOwnedPaths(spec.owned_paths);
 if(spec.mode==='content'&&(!spec.geographic_release||!spec.scope_manifest||!spec.territory_match_review))throw Error('Content issues need released geography, an entity/interval/attribute scope manifest and territory-match review');
 return spec;
}
function checkLaneMode(branch,spec){
 const {lane}=laneForBranch(branch);
 if(lane==='engineering'&&spec.mode!=='engineering'||lane==='geography'&&spec.mode!=='geography'||lane==='research'&&!['source-only','content'].includes(spec.mode))throw Error('Scope mode must agree with the issue lane');
 if(lane==='engineering')validateEngineeringOwnedPaths(spec.owned_paths);
}
// Ordinary authorship uses the issue's declared lane and paths. Reservations
// below are retained only for explicitly coordinated live operations.
export function verifyIssueScope({branch, issue}) {
 validateIssueMetadata(branch,issue);
 const spec=workSpec(issue.body);checkLaneMode(branch,spec);
 const evidence=spec.mode==='engineering'&&spec.evidence_quality!==undefined
  ? evidenceRequirement(issue,spec,undefined,branch):null;
 if(evidence)validateLanePaths(branch,[evidence.manifestPath],{ownedPaths:spec.owned_paths});
 return {mode:spec.mode,...(spec.owned_paths!==undefined?{owned_paths:[...spec.owned_paths]}:{}),
  ...(evidence?{evidence_manifest:evidence.manifestPath}:{})};
}
function liveOperationScope({issue,branch,dependencies=[],comments=[]}) {
 verifyIssueScope({branch,issue});
 const spec=workSpec(issue.body),labels=(issue.labels??[]).map(x=>typeof x==='string'?x:x.name);
 if(spec.mode!=='engineering')throw Error('Reservations are retained only for engineering live operations');
 if(!labels.includes('kind:work-item')||labels.includes('kind:umbrella')||!labels.includes('status:ready')||labels.includes('status:blocked'))throw Error('Live operation needs a reviewed ready work item');
 if(activeIssueBlockers(comments).length)throw Error('Unresolved live-operation blocker');
 if(spec.depends_on.some(id=>!dependencies.some(d=>d.number===id&&d.state==='closed'&&!d.pull_request)))throw Error('A live-operation dependency is still open or missing');
 return spec;
}
// Retained by live Cloudflare acceptance; ordinary authoring does not read blockers.
export function activeIssueBlockers(comments){
 const latest=new Map();
 for(const c of [...comments].sort((a,b)=>a.id-b.id))for(const match of String(c.body??'').matchAll(/<!-- worldatlas-blocker:v1\s*\n([\s\S]*?)\n-->/g)){
  const value=JSON.parse(match[1]);
  if(!value.id||typeof value.active!=='boolean'||!value.reason)throw Error('Malformed blocker marker; inspect original issue');
  latest.set(value.id,value);
 }
 return [...latest.values()].filter(x=>x.active);
}
export function readClaim(comments){
 const canonical=comments.filter(c=>c.user?.login==='github-actions[bot]'&&c.body?.startsWith('**Worker reservation:**'));
 if(canonical.length>1)throw Error('Multiple canonical claims require operator repair');
 if(!canonical.length)return null;
 const comment=canonical[0],match=/<!-- worldatlas-claim:v1\n([\s\S]*?)\n-->/.exec(comment.body);
 if(!match)throw Error('Malformed canonical claim; preserve it and request repair');
 const claim=JSON.parse(match[1]);
 if(claim.version!==1||typeof claim.active!=='boolean'||!claim.worker_id||!claim.claim_id||!claim.branch||!Number.isFinite(Date.parse(claim.expires_at)))throw Error('Invalid canonical claim');
 if(claim.mode==='geography')validateGeographyOwnedPaths(claim.owned_paths);
 return {comment_id:comment.id,...claim};
}
export function renderClaim(claim){
 const state={...claim};delete state.comment_id;
 return `**Worker reservation:** ${claim.active?'claimed':'released'} · ${claim.worker_id}\n\nBranch: \`${claim.branch}\` · lease expires: ${claim.expires_at} · live work pending: ${Boolean(claim.live_work)}\n\n<!-- ${claimMarker}\n${JSON.stringify(state)}\n-->`;
}
export function transitionClaim({issue,comments,prs=[],dependencies=[],request,now=Date.now()}){
 const {action,worker_id,claim_id,branch,request_id}=request;
 if(!['claim','renew','release','recover'].includes(action)||!/^[-a-zA-Z0-9_:.]{1,100}$/.test(worker_id??'')||!/^[-a-zA-Z0-9]{16,100}$/.test(claim_id??'')||!/^[-a-zA-Z0-9]{16,100}$/.test(request_id??''))throw Error('Invalid claim action or unique worker/request IDs');
 laneForBranch(branch);
 const current=readClaim(comments);
 if(current?.request_id===request_id)return {claim:current,replayed:true};
 const openPR=prs.find(p=>p.state==='open'&&p.head?.ref===current?.branch);
 const own=current?.worker_id===worker_id&&current?.claim_id===claim_id;
 const labels=(issue.labels??[]).map(l=>typeof l==='string'?l:l.name);
 if(['claim','recover'].includes(action)&&prs.some(p=>p.state==='open')&&!(current?.active&&own&&branch===current.branch))throw Error('Recovery or a new reservation must preserve existing open PR and checkpoint');
 if(action==='release'){
  if(!current?.active||!own)throw Error('Only the current claim holder may release');
  if(openPR||current.live_work)throw Error('Preserve the active PR/live operation; finish or hand over before release');
  return {claim:{...current,active:false,request_id,released_at:new Date(now).toISOString()},previous:current};
 }
 const spec=liveOperationScope({issue,branch,dependencies,comments});
 if(spec.production_operation&&(spec.mode!=='engineering'||!Number.isSafeInteger(spec.production_operation.source_issue)||spec.production_operation.source_issue<1||![714,spec.production_operation.source_issue].includes(spec.production_operation.queue)||spec.production_operation.publisher_worker_id!==worker_id))throw Error('Production-only child reservations belong to their designated publisher');
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
 const claim={...(current?.comment_id?{comment_id:current.comment_id}:{}),version:1,active:true,worker_id,claim_id,branch,request_id,issue_number:issue.number,claimed_at:own?current.claimed_at:new Date(now).toISOString(),updated_at:new Date(now).toISOString(),expires_at,live_work:action==='renew'?Boolean(request.live_work):false,mode:spec.mode,max_prs:spec.max_prs};
 return {claim,previous:current};
}
export async function githubPages(api,route){
 const all=[];for(let page=1;;page++){const rows=await api(`${route}${route.includes('?')?'&':'?'}per_page=100&page=${page}`);const list=Array.isArray(rows)?rows:rows?.check_runs;if(!Array.isArray(list))throw Error('Invalid paginated GitHub response');all.push(...list);if(list.length<100)return all;}
}
export async function linkedPulls(api,repo,number){
 const timeline=await githubPages(api,`/repos/${repo}/issues/${number}/timeline`),ids=new Set();
 // Live-operation release must see native cross-references even when ordinary
 // PRs have multiple links, prose punctuation or subsequently edited bodies.
 for(const event of timeline){
  const source=event.source?.issue;if(!source?.pull_request)continue;
  const id=canonicalIssueNumber(source.number),url=source.pull_request.url;
  if(typeof url!=='string'||!/^https:\/\/api\.github\.com\/repos\/[^/]+\/[^/]+\/pulls\/[1-9]\d*$/.test(url)||!url.endsWith(`/pulls/${id}`))throw Error('Incomplete cross-referenced PR identity');
  if(url===`https://api.github.com/repos/${repo}/pulls/${id}`)ids.add(id);
 }
 return completeReads([...ids].map(id=>api(`/repos/${repo}/pulls/${id}`)));
}
export function githubAPI(token, {fetchImpl = fetch, onRequest = () => {}, readWaitMs = 0, now = Date.now, sleep = ms => new Promise(resolve => setTimeout(resolve, ms)), deadlineRemaining,
 publicReadOnly = false, conditionalReads = true, snapshotBytes = 64 * 1024 * 1024, snapshotEntries = 128} = {}){
 if(publicReadOnly ? token !== undefined && token !== '' : !token)throw Error(publicReadOnly?'Public GitHub reads cannot carry credentials':'Read/write GitHub token required');
 if(deadlineRemaining!==undefined&&typeof deadlineRemaining!=='function')throw Error('Invalid job deadline');
 const remaining=()=>{const value=deadlineRemaining?deadlineRemaining():Infinity;if(deadlineRemaining&&!Number.isFinite(value))throw Error('Invalid job deadline');return value;};
 const admit=()=>{if(remaining()<=HTTP_ATTEMPT_MS)throw Object.assign(Error('Job deadline cannot admit another bounded HTTP attempt'),{jobDeadline:true});};
 const apiStarted=now();
 const snapshots=conditionalSnapshots({maxBytes:snapshotBytes,maxEntries:snapshotEntries});
 const request = async(route,method='GET',body,artifactRedirect=false,maxResponseBytes)=>{
  if(publicReadOnly&&(method!=='GET'||body!==undefined||artifactRedirect))throw Error('Public GitHub access permits metadata GET only');
  admit();
  // Immutable blobs already have independently bounded custody/transport caches.
  // Actions may retain a queued snapshot while the same job starts. Always
  // read this mutable inventory afresh; other authority routes retain ETags.
  const jobInventory=/^\/repos\/[^/]+\/[^/]+\/actions\/runs\/\d+\/attempts\/\d+\/jobs(?:\?|$)/.test(route);
  const conditional=maxResponseBytes===undefined&&!jobInventory&&!artifactRedirect&&conditionalReads&&method==='GET'&&body===undefined&&route!=='/rate_limit'&&!/\/git\/blobs\//.test(route);
  const snapshot=conditional?snapshots.get(route):undefined;
  let response;
  try {response=await fetchImpl('https://api.github.com'+route,{method,headers:{...(!publicReadOnly?{Authorization:`Bearer ${token}`} : {}),Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28',...(snapshot?{'If-None-Match':snapshot.etag}:{}),...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(HTTP_ATTEMPT_MS),redirect:artifactRedirect?'manual':'error'});}
  catch(error){onRequest({route,method,status:'transport-error'});throw error;}
  // Optional caller-owned phase admission. Cap the actual stream before JSON
  // allocation; never revalidate a larger cached representation for this read.
  if(maxResponseBytes!==undefined&&response.body){
   let bytes=0;
   const bounded=response.body.pipeThrough(new TransformStream({transform(chunk,controller){
    bytes+=chunk.length;if(bytes>maxResponseBytes)throw Error('GitHub response exceeds caller byte allowance');
    controller.enqueue(chunk);
   }}));
   response=new Response(bounded,{status:response.status,statusText:response.statusText,headers:response.headers});
  }
  const headerNumber = name => {const value=response.headers.get(name);return /^\d{1,13}$/.test(value??'')?Number(value):undefined;};
  const capacity={limit:headerNumber('x-ratelimit-limit'),remaining:headerNumber('x-ratelimit-remaining'),reset:headerNumber('x-ratelimit-reset'),resource:response.headers.get('x-ratelimit-resource')};
  onRequest({route,method,status:response.status,capacity});
  if(artifactRedirect&&response.status===302){
   if(remaining()<=0){await response.body?.cancel();throw Object.assign(Error('Job deadline exhausted during artifact redirect'),{jobDeadline:true});}
   await response.body?.cancel();
   return response;
  }
  if(response.status===304){
   if(!conditional||!snapshot)throw Error('Unrequested conditional GitHub response');
   if(remaining()<=0)throw Object.assign(Error('Job deadline exhausted during conditional revalidation'),{jobDeadline:true});
   return snapshots.revalidated(snapshot,response.headers.get('etag'));
  }
  if(!response.ok){
   snapshots.invalidate(route);
   const error=Error(`GitHub ${method} ${route} failed (HTTP ${response.status})`);
   let payload;try{payload=await response.json();}catch{/* Keep the actual HTTP rejection even without a JSON message. */}
   const numeric=name=>{const value=response.headers.get(name);return /^\d{1,13}$/.test(value??'')?value:undefined;};
   const requestId=response.headers.get('x-github-request-id');
   const message=typeof payload?.message==='string'?payload.message.split(token).join('[redacted]')
    .replace(/(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]+/g,'[redacted]')
    .replace(/Bearer\s+\S+/gi,'Bearer [redacted]').replace(/[\x00-\x1f\x7f]/g,' ').slice(0,512):undefined;
   error.github={http_status:response.status,...(message?{message}:{}),
    ...Object.fromEntries([['rate_remaining',numeric('x-ratelimit-remaining')],['rate_reset',numeric('x-ratelimit-reset')],
     ['retry_after',numeric('retry-after')],['request_id',/^[a-fA-F0-9:]{1,100}$/.test(requestId??'')?requestId:undefined]].filter(([,value])=>value!==undefined))};
   throw error;
  }
  const finish=payload=>{if(remaining()<=0)throw Object.assign(Error('Job deadline exhausted while consuming HTTP response'),{jobDeadline:true});return payload;};
  if(response.status===204)return finish(null);
  const payload=await response.json();
  if(conditional)snapshots.retain(route,response.headers.get('etag'),payload);
  if(route==='/rate_limit'){
   const numeric=name=>{const value=response.headers.get(name);return /^\d{1,13}$/.test(value??'')?Number(value):undefined;};
   const capacity_headers={limit:numeric('x-ratelimit-limit'),remaining:numeric('x-ratelimit-remaining'),reset:numeric('x-ratelimit-reset')};
   // Only numeric capacity fields are exposed. No complete response/header map
   // or authentication data crosses into pacing logs or durable receipts.
   return finish({...payload,capacity_headers});
  }
  return finish(payload);
 };
 const read = async(route, method='GET', body, {maxResponseBytes} = {}) => {
  if(maxResponseBytes!==undefined&&(!Number.isSafeInteger(maxResponseBytes)||maxResponseBytes<=0||method!=='GET'||body!==undefined))
   throw Error('Invalid caller response-byte admission');
  let lastQuota;
  for(let attempt=0;;attempt++){
   try{return await request(route,method,body,false,maxResponseBytes);}
   catch(error){
    if(error.jobDeadline&&lastQuota)error.quotaCause=lastQuota;
    const quota=quotaDelay(error,now());
    const delay=quota??([500,502,503,504].includes(error.github?.http_status)?1000*2**attempt:null);
    if(quota!==null)lastQuota=error;
    // Retry only explicit transient read responses inside the existing budget.
    // Writes, transport ambiguity and ordinary denial remain unretried.
    if(method!=='GET'||body!==undefined||delay===null||attempt>=2)throw error;
    // Include the next complete attempt, not only the sleep. Recheck admission
    // after waking too, because previous work or an oversleep may consume time.
    if(delay+HTTP_ATTEMPT_MS>=remaining()){error.jobDeadline=true;throw error;}
    if(delay>=readWaitMs-(now()-apiStarted))throw error;
    await sleep(delay);
   }
  }
 };
 // GitHub caps recursive tree responses independently of repository validity.
 // Decompose only an explicitly truncated immutable GET, discarding its rows.
 // Keep raw HTTP snapshots and each child's retries separate from this walk.
 const api = async(route,method='GET',body,options={}) => {
  const value=await read(route,method,body,options);
  const match=/^(\/repos\/[\w.-]+\/[\w.-]+\/git\/trees\/)([a-f0-9]{40})\?recursive=1$/.exec(route);
  // Bounded callers retain their original refusal; completion cannot enlarge
  // an explicit response allowance into a multi-response aggregate.
  if(method!=='GET'||body!==undefined||!match||options.maxResponseBytes!==undefined||value?.truncated!==true)return value;
  const inventories=new Map(),oid=value=>/^[a-f0-9]{40}$/.test(value??'');
  const need=(ok,message)=>{if(!ok)throw Error(message);};
  const rows=(response,sha,recursive)=>{
   need(response?.sha===sha&&typeof response.truncated==='boolean'&&Array.isArray(response.tree),
     'Invalid immutable tree response identity');
   const entries=new Map();
   for(const row of response.tree){
    const parts=typeof row.path==='string'?row.path.split('/'):[];
    need(parts.length>0&&parts.every(part=>part&&part!=='.'&&part!=='..'&&!/[\x00-\x1f\x7f\\]/.test(part))
      &&(recursive||parts.length===1)&&oid(row.sha)&&!entries.has(row.path)
      &&(row.type==='tree'&&row.mode==='040000'||row.type==='commit'&&row.mode==='160000'
        ||row.type==='blob'&&['100644','100755','120000'].includes(row.mode)
          &&Number.isSafeInteger(row.size)&&row.size>=0),'Invalid or duplicate immutable tree entry');
    entries.set(row.path,row);
   }
   if(recursive)for(const [name,row]of entries){
    if(row.type==='tree')need(row.sha!==sha,'Cyclic immutable tree inventory');
    for(let at=name.indexOf('/');at>=0;at=name.indexOf('/',at+1)){
     const parent=entries.get(name.slice(0,at));
     need(parent?.type==='tree','Incomplete immutable tree parent inventory');
     if(row.type==='tree')need(row.sha!==parent.sha,'Cyclic immutable tree inventory');
    }
   }
   return entries;
  };
  const collect=async(sha,initial,ancestors)=>{
   need(!ancestors.has(sha),'Cyclic immutable tree inventory');
   if(inventories.has(sha)){
    const cached=inventories.get(sha);
    for(const row of cached.values())if(row.type==='tree')need(!ancestors.has(row.sha),'Cyclic immutable tree inventory');
    return cached;
   }
   const response=initial??await read(match[1]+sha+'?recursive=1');
   need(response?.sha===sha&&typeof response.truncated==='boolean'&&Array.isArray(response.tree),
     'Invalid immutable tree response identity');
   let entries;
   if(response.truncated===false){
    entries=rows(response,sha,true);
    for(const row of entries.values())if(row.type==='tree')need(!ancestors.has(row.sha),'Cyclic immutable tree inventory');
   }
   else{
    const direct=await read(match[1]+sha);
    need(direct?.truncated===false,'Incomplete direct immutable tree inventory');
    entries=rows(direct,sha,false);
    const parents=new Set([...ancestors,sha]);
    for(const row of [...entries.values()])if(row.type==='tree'){
     for(const [relative,child]of await collect(row.sha,undefined,parents)){
      const name=row.path+'/'+relative;
      need(!entries.has(name),'Duplicate expanded immutable tree path');
      entries.set(name,{...child,path:name});
     }
    }
   }
   inventories.set(sha,entries);return entries;
  };
  const entries=await collect(match[2],value,new Set());
  return {...value,tree:[...entries.values()].sort((a,b)=>a.path<b.path?-1:a.path>b.path?1:0),truncated:false};
 };
 // Only fixed artifact/job-log API routes expose redirect headers. Delivery is
 // handled separately without credentials; no signed URL enters accounting.
 api.artifactRedirect=route=>{
  if(!/^\/repos\/[\w.-]+\/[\w.-]+\/actions\/artifacts\/[1-9]\d*\/zip$/.test(route??''))throw Error('Invalid artifact redirect route');
  return request(route,'GET',undefined,true);
 };
 // Retained original packages still authenticate their producer's job log.
 api.jobLogRedirect=route=>{
  if(!/^\/repos\/[\w.-]+\/[\w.-]+\/actions\/jobs\/[1-9]\d*\/logs$/.test(route??''))throw Error('Invalid job log redirect route');
  return request(route,'GET',undefined,true);
 };
 // Cleanup and result notification use one attempt, without ordinary read
 // retries. Real provider failure is left for the caller to reconcile.
 // Callers must prove exact ref ownership/SHA before deleting (cleanupCandidate).
 api.recovery=(route,method='GET',body)=>{
  const candidate=/^\/repos\/[\w.-]+\/[\w.-]+\/git\/(ref|refs)\/heads\/worldatlas-integration\/pr-[1-9]\d*-[-a-zA-Z0-9]{16,160}$/.exec(route??'');
  const notification=/^\/repos\/[\w.-]+\/[\w.-]+\/issues\/[1-9]\d*\/comments$/.test(route??'')&&method==='POST'&&
   typeof body?.body==='string'&&body.body.startsWith('**Merge result:**')&&body.body.includes('<!-- worldatlas-merge-result:v1');
  if(!(candidate&&body===undefined&&((candidate[1]==='ref'&&method==='GET')||(candidate[1]==='refs'&&method==='DELETE'))||notification))
   throw Error('Request is outside bounded merge recovery');
  return request(route,method,body);
 };
 return api;
}

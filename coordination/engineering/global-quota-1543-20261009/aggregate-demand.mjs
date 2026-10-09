import fs from 'node:fs';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const own=path.dirname(fileURLToPath(import.meta.url));
const load=name=>JSON.parse(fs.readFileSync(path.join(own,name),'utf8'));
const sum=rows=>rows.reduce((a,b)=>a+b,0);
const integer=n=>Number.isSafeInteger(n)&&n>=0;
export function aggregate(inventory,demand,evidence,claims){
 const ids=new Set();
 for(const row of inventory.runs){assert(integer(row.id)&&row.id>0&&!ids.has(row.id),'Duplicate/missing workflow identity');ids.add(row.id);}
 const check=rows=>{const seen=new Set();for(const r of rows){assert(ids.has(r.id)&&!seen.has(r.id),'Foreign/duplicate receipt identity');seen.add(r.id);}};
 check(demand.runs);check(evidence.runs);check(claims.runs);
 const attempts=row=>{
  const seen=new Set();let count=0;
  for(const a of row.accounting??[]){const key=a.job+':'+a.phase;assert(!seen.has(key),'Duplicate accounting phase');seen.add(key);
   assert(integer(a.actual_http_attempts)&&Object.values(a.counts).every(integer));
   assert.equal(sum(Object.values(a.counts)),a.actual_http_attempts,'Accounting categories disagree');count+=a.actual_http_attempts;
  }
  if(row.recorded_attempts!==undefined)assert.equal(row.recorded_attempts,count,'Run accounting disagrees');
  return count;
 };
 const merge=demand.runs.filter(r=>r.path==='.github/workflows/worker-merge.yml');
 const scheduler=demand.runs.filter(r=>r.path==='.github/workflows/merge-scheduler.yml');
 assert.equal(merge.length+scheduler.length,demand.runs.length,'Unexpected consumer');
 let evidenceFloor=0,evidenceCount=0;
 for(const r of evidence.runs){
  if(r.code_derived_blob_request_lower_bound===undefined)continue;
  const last=r.reports.at(-1);assert(integer(last.authenticated_unique_descriptor_keys));
  assert(['bytes-verified','limited'].includes(last.status),'Unverified evidence receipt cannot imply paid reads');
  assert.equal(r.code_derived_blob_request_lower_bound,last.authenticated_unique_descriptor_keys+1);
  evidenceFloor+=r.code_derived_blob_request_lower_bound;evidenceCount++;
 }
 let claimFloor=0,accepted=0;
 for(const r of claims.runs){if(r.accepted!==true)continue;assert(integer(r.code_derived_minimum_requests)&&r.derivation);assert.equal(r.code_derived_minimum_requests,8+(r.mode==='geography'&&r.action!=='release'?2:0)+(r.action!=='renew'?1:0),'Claim code-derived floor disagrees');claimFloor+=r.code_derived_minimum_requests;accepted++;}
 assert.equal(evidenceFloor,evidence.inferred_old_blob_requests_lower_bound);assert.equal(evidenceCount,evidence.successful_evidence_receipts);
 assert.equal(claimFloor,claims.inferred_request_floor);assert.equal(accepted,claims.accepted);
 const metadata=sum(merge.flatMap(r=>(r.accounting??[]).flatMap(a=>Object.entries(a.counts).filter(([k])=>k.split(':')[1]==='immutable-metadata').map(([,v])=>v))));
 const categories={GET:0,mutation:0};for(const r of demand.runs)for(const a of r.accounting??[])for(const [k,v]of Object.entries(a.counts))categories[k.startsWith('GET:')?'GET':'mutation']+=v;
 const lane=(prefix)=>{const rows=inventory.runs.filter(r=>r.event==='pull_request'&&r.head_branch.startsWith(prefix));return {runs:rows.length,pairs:new Set(rows.map(r=>r.head_branch+':'+r.head_sha)).size};};
 const geography=lane('geography/'),engineering=lane('engineering/'),history=lane('research/');
 const mergeRequests=sum(merge.map(attempts));
 return {workflow_runs:inventory.runs.length,evidence_requests_floor:evidenceFloor,merge_http_attempts:mergeRequests,scheduler_http_attempts:sum(scheduler.map(attempts)),claim_requests_floor:claimFloor,merge_immutable_metadata:metadata,merge_other_attempts:mergeRequests-metadata,get_attempts:categories.GET,mutation_attempts:categories.mutation,geography_runs:geography.runs,geography_pairs:geography.pairs,engineering_runs:engineering.runs,engineering_pairs:engineering.pairs,history_runs:history.runs,history_pairs:history.pairs};
}
const inputs=[load('day-inventory.json'),load('day-demand.json'),load('day-evidence-demand.json'),load('day-claims.json')];
const result=aggregate(...inputs);
for(const [k,v] of Object.entries({workflow_runs:1243,evidence_requests_floor:21454,merge_http_attempts:13987,scheduler_http_attempts:1873,claim_requests_floor:1515}))assert.equal(result[k],v);
fs.writeFileSync(path.join(own,'demand-summary.json'),JSON.stringify(result,null,2)+'\n');
const reject=mutate=>{const changed=structuredClone(inputs);mutate(changed);assert.throws(()=>aggregate(...changed));};
reject(x=>x[0].runs.push(x[0].runs[0]));
reject(x=>x[1].runs.push(x[1].runs[0]));
reject(x=>x[1].runs.find(r=>r.accounting?.length).accounting[0].actual_http_attempts++);
reject(x=>x[2].runs.find(r=>r.code_derived_blob_request_lower_bound!==undefined).code_derived_blob_request_lower_bound++);
reject(x=>x[3].inferred_request_floor++);
for(const kind of ['positive-control','negative-control'])fs.writeFileSync(path.join(own,kind+'.json'),JSON.stringify({method_id:'demand-aggregation',kind,outcome:'passed',checks:kind==='negative-control'?['duplicate inventory','duplicate receipt','inconsistent actual accounting','inconsistent evidence inference','inconsistent claim inference']:['complete retained inventories reproduce reported totals'],limits:['Historical log extraction remains a separate provenance step. Inferred floors are not actual request telemetry; missing traffic remains unknown.']},null,2)+'\n');
console.log(JSON.stringify(result));

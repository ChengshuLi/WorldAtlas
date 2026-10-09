import fs from 'node:fs';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const own=path.dirname(fileURLToPath(import.meta.url));
const load=name=>{const file=path.join(own,name),stat=fs.lstatSync(file);assert(stat.isFile()&&!stat.isSymbolicLink()&&stat.size<=2*1024*1024,'Bounded ordinary investigation input required');return JSON.parse(fs.readFileSync(file,'utf8'));};
const sum=rows=>rows.reduce((a,b)=>a+b,0);
const integer=n=>Number.isSafeInteger(n)&&n>=0;
export function aggregate(inventory,demand,evidence,claims){
 const ids=new Set();
 for(const row of inventory.runs){assert(integer(row.id)&&row.id>0&&!ids.has(row.id),'Duplicate/missing workflow identity');ids.add(row.id);}
 const authoritative=new Map(inventory.runs.map(r=>[r.id,r]));
 const check=(rows,expected)=>{const seen=new Set();for(const r of rows){assert(ids.has(r.id)&&!seen.has(r.id),'Foreign/duplicate receipt identity');seen.add(r.id);const original=authoritative.get(r.id);
  for(const key of ['path','name','event','created_at','head_branch','head_sha','run_attempt','conclusion'])if(Object.hasOwn(r,key))assert.equal(r[key],original[key],'Authoritative inventory join differs: '+key);
 }assert.deepEqual([...seen].sort((a,b)=>a-b),expected.map(r=>r.id).sort((a,b)=>a-b),'Incomplete selected consumer roster');};
 check(demand.runs,inventory.runs.filter(r=>['.github/workflows/worker-merge.yml','.github/workflows/merge-scheduler.yml'].includes(r.path)));
 check(evidence.runs,inventory.runs.filter(r=>r.name==='Handoff lane scope'));
 check(claims.runs,inventory.runs.filter(r=>r.path.endsWith('/issue-claims.yml')));
 for(const r of claims.runs)assert.equal(r.action,authoritative.get(r.id).name.split(' ')[0],'Claim action differs from actual workflow');
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
export function reproduce(output){
 assert(typeof output==='string'&&output,'Use --out FRESH-OWNED-RUN-DIRECTORY');
 const target=path.resolve(output),parent=path.dirname(target);
 assert(fs.realpathSync(parent)===fs.realpathSync(own)&&/^[a-z0-9][a-z0-9-]{0,63}$/.test(path.basename(target)),'Fresh run must be a direct owned packet directory');
 let exists=false;try{fs.lstatSync(target);exists=true;}catch(error){if(error.code!=='ENOENT')throw error;}
 assert(!exists,'Existing output collision; retain prior evidence');
 const inputs=[load('day-inventory.json'),load('day-demand.json'),load('day-evidence-demand.json'),load('day-claims.json')];
 const result=aggregate(...inputs);
 for(const [k,v] of Object.entries({workflow_runs:1243,evidence_requests_floor:21454,merge_http_attempts:13987,scheduler_http_attempts:1873,claim_requests_floor:1515}))assert.equal(result[k],v);
 const reject=mutate=>{const changed=structuredClone(inputs);mutate(changed);assert.throws(()=>aggregate(...changed));};
 reject(x=>x[0].runs.push(x[0].runs[0]));reject(x=>x[1].runs.push(x[1].runs[0]));
 reject(x=>x[1].runs.find(r=>r.accounting?.length).accounting[0].actual_http_attempts++);
 reject(x=>x[2].runs.find(r=>r.code_derived_blob_request_lower_bound!==undefined).code_derived_blob_request_lower_bound++);
 reject(x=>x[3].inferred_request_floor++);
 reject(x=>x[1].runs.find(r=>r.path==='.github/workflows/worker-merge.yml').path='.github/workflows/merge-scheduler.yml');
 reject(x=>x[1].runs.pop());
 const bodies={'demand-summary.json':result};
 for(const kind of ['positive-control','negative-control'])bodies[kind+'.json']={method_id:'demand-aggregation',kind,outcome:'passed',checks:kind==='negative-control'?['duplicate inventory','duplicate receipt','inconsistent actual accounting','inconsistent evidence inference','inconsistent claim inference','wrong consumer join','missing consumer receipt']:['complete retained inventories reproduce reported totals'],limits:['Historical log extraction remains a separate provenance step. Inferred floors are not actual request telemetry; missing traffic remains unknown.']};
 const encoded=Object.fromEntries(Object.entries(bodies).map(([name,body])=>[name,JSON.stringify(body,null,2)+'\n']));
 assert(Object.values(encoded).every(body=>Buffer.byteLength(body)<=1024*1024),'Complete output budget');
 // Exclusive creation occurs after all computation; no failed admission can
 // change retained files. A partial I/O failure never publishes the run receipt.
 fs.mkdirSync(target,{mode:0o700});
 for(const [name,raw]of Object.entries(encoded))fs.writeFileSync(path.join(target,name),raw,{flag:'wx',mode:0o600});
 fs.writeFileSync(path.join(target,'run-receipt.json'),JSON.stringify({status:'complete',outputs:Object.keys(encoded),controls:'passed'})+'\n',{flag:'wx',mode:0o600});
 return result;
}
if(process.argv[1]&&fs.realpathSync(process.argv[1])===fileURLToPath(import.meta.url)){
 assert(process.argv.length===4&&process.argv[2]==='--out','Use --out FRESH-OWNED-RUN-DIRECTORY');
 console.log(JSON.stringify(reproduce(process.argv[3])));
}

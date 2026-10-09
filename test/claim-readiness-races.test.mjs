import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
const runner=new URL('../scripts/run-issue-claim.mjs',import.meta.url);
const spec={mode:'engineering',scope:'bounded repair',max_prs:1,depends_on:[2]};
let caseNumber=0;
async function runCase(drift){
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'wa-claim-race-'));
 const cwd=process.cwd(),fetchBefore=globalThis.fetch,keys=['GITHUB_REF','GITHUB_REPOSITORY','GITHUB_EVENT_PATH','GITHUB_STEP_SUMMARY','GH_TOKEN'];
 const before=Object.fromEntries(keys.map(k=>[k,process.env[k]]));
 const geography=drift==='ownership';
 const caseSpec=geography?{...spec,mode:'geography',owned_paths:['data/regional-review/packet/']}:spec;
 const value={number:1,state:'open',created_at:'2026-10-01T00:00:00Z',updated_at:'same',labels:[geography?'type:geography':'type:engineering','kind:work-item','status:ready'].map(name=>({name})),body:`<!-- worldatlas-work:v1\n${JSON.stringify(caseSpec)}\n-->`};
 let commentReads=0,depReads=0,timelineReads=0,ownershipReads=0;const writes=[];
 try{
  process.chdir(dir);fs.writeFileSync('event.json',JSON.stringify({inputs:{action:'claim',issue_number:'1',worker_id:'author',claim_id:'claim-aaaaaaaaaaaaaaaa',request_id:'request-aaaaaaaaaaaaaaa',branch:geography?'geography/repair':'engineering/repair'}}));
  Object.assign(process.env,{GITHUB_REF:'refs/heads/main',GITHUB_REPOSITORY:'owner/repo',GITHUB_EVENT_PATH:path.join(dir,'event.json'),GITHUB_STEP_SUMMARY:path.join(dir,'summary'),GH_TOKEN:'synthetic-token'});
  globalThis.fetch=async(raw,options)=>{
   const url=new URL(raw),route=url.pathname,method=options.method;let payload;
   if(method!=='GET'){writes.push({route,body:JSON.parse(options.body??'{}')});payload={id:123};}
   else if(route.endsWith('/issues'))payload=ownershipReads++?[value,{...value,number:3}]:[value];
   else if(route.endsWith('/issues/1'))payload=value;
   else if(route.endsWith('/issues/2'))payload={number:2,state:drift==='dependency'&&depReads++?'open':'closed'};
   else if(route.endsWith('/comments'))payload=drift==='blocker'&&commentReads++?[{id:3,user:{login:'human'},body:'<!-- worldatlas-blocker:v1\n{"id":"input","active":true,"reason":"Missing input"}\n-->'}]:[];
   else if(route.endsWith('/timeline'))payload=drift==='budget'&&timelineReads++?[{source:{issue:{number:3,body:'Refs #1',pull_request:{url:'pr'}}}}]:[];
   else if(route.endsWith('/pulls/3'))payload={number:3,state:'closed',body:'Refs #1',merged_at:'now'};
   else throw Error('Unexpected mock route '+route);
   return new Response(JSON.stringify(payload),{status:200,headers:{'Content-Type':'application/json'}});
  };
  const {runIssueClaim}=await import(runner.href+'?race='+caseNumber++);
  const result=await runIssueClaim({event:JSON.parse(fs.readFileSync('event.json'))});
  return {result,writes};
 }finally{
  globalThis.fetch=fetchBefore;process.chdir(cwd);
  for(const k of keys)if(before[k]===undefined)delete process.env[k];else process.env[k]=before[k];
  fs.rmSync(dir,{recursive:true,force:true});
 }
}
test('actual claim runner rejects blocker, dependency, budget and ownership drift without writing a reservation',async()=>{
 for(const drift of ['blocker','dependency','budget','ownership']){
  const {result,writes}=await runCase(drift);assert.equal(result.accepted,false);assert.match(result.reason,/changed during claim/);
  assert(!writes.some(x=>x.body.body?.startsWith('**Worker reservation:**')));
  assert.equal(writes.length,1,'Only durable rejection result is written');
 }
});
test('actual claim runner still writes one accepted canonical reservation for stable eligible inputs',async()=>{
 const {result,writes}=await runCase(null);assert.equal(result.accepted,true);
 assert.equal(writes.filter(x=>x.body.body?.startsWith('**Worker reservation:**')).length,1);
});

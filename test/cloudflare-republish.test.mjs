import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {republishCurrentVersion,runRepublish} from '../scripts/cloudflare-republish.mjs';
import {renderClaim,workSpec} from '../scripts/issue-claim-contract.mjs';
import {cloudflareFixture} from './fixtures/cloudflare-publication.mjs';
import {checkedStorageV4Contract,v4MarkerIdentity} from '../hosted/storage-export-v4-contract.js';
import fsSync from 'node:fs';
const root='/repos/ChengshuLi/WorldAtlas';
function fixture(){
 const before=cloudflareFixture(),current=cloudflareFixture({id:200});
 current.op.operation_id='22222222-3333-4444-5555-666666666666';
 Object.assign(current.op,{publish_method:'republish-current-version',expected_worker_version:before.result.worker_version,reservation_issue:849,claim_id:'fixture-claim',claim_branch:'engineering/fixture'});
 const issue={number:849,state:'open',labels:['type:engineering','kind:work-item','status:ready'],body:'<!-- worldatlas-work:v1\n'+JSON.stringify({max_prs:2,depends_on:[822],mode:'engineering',scope:'Existing-version publisher acceptance'})+'\n-->'};
 current.op.reservation_scope_sha256=createHash('sha256').update(JSON.stringify(workSpec(issue.body))).digest('hex');
 const claim={version:1,issue_number:849,mode:'engineering',active:true,live_work:true,worker_id:current.op.worker_id,claim_id:current.op.claim_id,branch:current.op.claim_branch,expires_at:current.op.expires_at};
 const calls=[],requests=[],activeStatus={id:3000,state:'in_progress'};
 const providerBefore={id:'aaaaaaaa-bbbb-cccc-dddd-111111111111',versions:[{version_id:before.result.worker_version,percentage:100}]};
 const providerAfter={id:'aaaaaaaa-bbbb-cccc-dddd-222222222222',versions:[{version_id:before.result.worker_version,percentage:100}]};
 const marker=JSON.parse(fsSync.readFileSync(new URL('../coordination/engineering/cloudflare-publication-846-20261007/served-marker-before.json',import.meta.url)));checkedStorageV4Contract(marker.contract);
 for(const f of [before,current]){f.op.source_fingerprint=marker.fingerprint;f.op.catalog_sha256=marker.catalog_sha256;f.delivery.source_fingerprint=marker.fingerprint;f.delivery.catalog_sha256=marker.catalog_sha256;}
 const release={status:'published',id:current.op.release_id,hierarchy_sha256:current.op.hierarchy_sha256,footprints_sha256:current.op.footprint_sha256};
 const f={before,current,issue,claim,calls,requests,providerBefore,providerAfter,marker,release,activeStatus,providerReads:0,extra:[],registryReads:0,mutationStatus:503,postCount:0};
 f.api=async route=>{
  calls.push(route);
  if(route===root+'/deployments/200')return structuredClone(current.deployment);
  if(route===root+'/issues/849')return structuredClone(issue);
  if(route===root+'/issues/822')return f.dependency??{number:822,state:'closed'};
  if(route===root+'/issues/849/comments?per_page=100&page=1')return [{id:1,user:{login:'github-actions[bot]'},body:renderClaim(claim)},...(f.blockers??[])];
  if(route===root+'/deployments?per_page=100&page=1'){f.registryReads++;f.onRegistry?.(f.registryReads);return [before.deployment,current.deployment,...f.extra].map(row=>structuredClone(row));}
  if(route===root+'/deployments/100/statuses?per_page=100&page=1')return [before.status];
  if(route===root+'/deployments/200/statuses?per_page=100&page=1')return [f.activeStatus];
  if(route===root+'/issues/comments/99')return before.receipt();
  if(route===root+'/deployments/50/statuses?per_page=100&page=1')return [];
  throw Error('Unexpected registry route '+route);
 };
 f.fetcher=async(url,options)=>{
  requests.push({url,method:options.method??'GET',redirect:options.redirect,signal:options.signal});f.onRequest?.(requests.at(-1));
  if(url.endsWith('/deployments')){
   assert.equal(options.headers.Authorization,'Bearer fixture-secret');
   if(options.method==='POST'){f.postCount++;assert.deepEqual(JSON.parse(options.body).versions,providerBefore.versions);assert.equal(JSON.parse(options.body).force,undefined);return new Response(JSON.stringify({success:!f.ambiguousPost,result:providerAfter}));}
   f.providerReads++;f.onProviderRead?.(f.providerReads);return new Response(JSON.stringify({success:true,result:{deployments:[f.postCount?providerAfter:providerBefore]}}));
  }
  if(url.endsWith('/export-marker'))return new Response(f.largeMarker?'x'.repeat(2*1024*1024+1):JSON.stringify(marker));
  if(url.endsWith('/geography/release'))return new Response(JSON.stringify(release));
  if(url.endsWith('/records/import'))return new Response('',{status:f.mutationStatus});
  throw Error('Unexpected provider route '+url);
 };
 f.options={deployment_id:200,api:f.api,account_id:'a'.repeat(32),api_token:'fixture-secret',fetcher:f.fetcher,now:()=>Date.parse('2026-10-04T00:05:00Z')};
 return f;
}
test('real publisher entry point repeats the registry immediately before one exact-version provider deployment',async()=>{
 const f=fixture(),r=await republishCurrentVersion(f.options);assert.equal(f.postCount,1);assert.equal(f.registryReads,2);assert.equal(r.provider_after.id,f.providerAfter.id);assert.equal(r.worker_version,f.before.result.worker_version);assert.equal(r.delivery_settled,false);
 assert.deepEqual(f.requests.filter(r=>r.url.endsWith('/records/import')).map(r=>r.method),['POST','PUT','PATCH','DELETE']);
 assert.ok(f.requests.every(r=>r.redirect==='error'&&r.signal instanceof AbortSignal));assert.ok(!JSON.stringify(r).includes('fixture-secret'));
});
for(const [label,mutate] of [
 ['expired window',f=>f.options.now=()=>Date.parse(f.current.op.expires_at)],['released claim',f=>f.claim.active=false],
 ['wrong claim holder',f=>f.claim.worker_id='another'],['scope drift',f=>f.issue.body=f.issue.body.replace('publisher acceptance','other scope')],
 ['provider drift',f=>f.providerBefore.versions[0].version_id='another-version'],['marker drift',f=>f.marker.fingerprint='other'],
 ['missing marker counts',f=>delete f.marker.counts],['missing marker contract',f=>delete f.marker.contract],['changed marker counters with original fingerprint',f=>f.marker.counts.records++],['missing footprint version pin',f=>delete f.marker.footprint_versions_sha256],['mismatched release',f=>f.release.hierarchy_sha256='other'],['public writes',f=>f.mutationStatus=200],['oversize marker',f=>f.largeMarker=true],
 ['late claim release',f=>f.onRequest=()=>{f.claim.active=false;}],['late blocked issue',f=>f.onRequest=()=>{f.issue.labels=['status:blocked'];}],
 ['late registration drift',f=>f.onRequest=()=>{f.current.op.tool_commit='f'.repeat(40);}],
 ['late unset live flag',f=>f.onRequest=()=>{f.claim.live_work=false;}],
 ['wrong claim issue',f=>f.claim.issue_number=907],['wrong claim mode',f=>f.claim.mode='source-only'],
 ['source-only scope',f=>{f.issue.body=f.issue.body.replace('engineering','source-only');f.current.op.reservation_scope_sha256=createHash('sha256').update(JSON.stringify(workSpec(f.issue.body))).digest('hex');}],
 ['unready issue',f=>f.issue.labels=f.issue.labels.filter(x=>x!=='status:ready')],
 ['active blocker',f=>f.blockers=[{id:2,body:'<!-- worldatlas-blocker:v1\n'+JSON.stringify({id:'hold',active:true,reason:'Human hold'})+'\n-->'}]],
 ['late active blocker',f=>f.onRequest=()=>{f.blockers=[{id:2,body:'<!-- worldatlas-blocker:v1\n'+JSON.stringify({id:'hold',active:true,reason:'Human hold'})+'\n-->'}];}],
 ['late dependency reopening',f=>f.onRequest=()=>{f.dependency={number:822,state:'open'};}],
 ['late unready issue',f=>f.onRequest=()=>{f.issue.labels=f.issue.labels.filter(x=>x!=='status:ready');}],
 ['late provider deployment',f=>f.onProviderRead=n=>{if(n===2)f.providerBefore.id='bbbbbbbb-bbbb-cccc-dddd-111111111111';}],
 ['late provider version',f=>f.onProviderRead=n=>{if(n===2)f.providerBefore.versions[0].version_id='bbbbbbbb-bbbb-cccc-dddd-111111111111';}],
 ['lease expiration during final provider refresh',f=>{let time=f.options.now();f.options.now=()=>time;f.onProviderRead=n=>{if(n===2)time=Date.parse(f.claim.expires_at);};}],
])test('rejects '+label+' before provider deployment',async()=>{const f=fixture();mutate(f);await assert.rejects(()=>republishCurrentVersion(f.options));assert.equal(f.postCount,0);});
test('another staging operation discovered after readonly probes prevents POST',async()=>{
 const f=fixture(),older=cloudflareFixture({id:50}).deployment;older.environment='worldatlas-cloudflare-staging';older.task=older.environment;older.payload.worldatlas_cloudflare.kind='staging';older.payload.worldatlas_cloudflare.public_reads=false;
 f.onRegistry=n=>{if(n===2)f.extra.push(older);};await assert.rejects(()=>republishCurrentVersion(f.options));assert.equal(f.postCount,0);
});
test('uncertain provider POST does not automatically retry or certify delivery',async()=>{
 const f=fixture();f.ambiguousPost=true;await assert.rejects(()=>republishCurrentVersion(f.options));assert.equal(f.postCount,1);
});
test('fresh output admission protects ordinary files, directories and broken symlinks before any API access',async()=>{
 const tmp=await fs.realpath(await fs.mkdtemp(path.join(os.tmpdir(),'atlas-republish-control-')));
 try{
  for(const kind of ['file','directory','broken-symlink']){
   const output=path.join(tmp,kind);if(kind==='file')await fs.writeFile(output,'sentinel');else if(kind==='directory')await fs.mkdir(output);else await fs.symlink(path.join(tmp,'absent'),output);
   let reads=0;await assert.rejects(()=>runRepublish({output},{api:async()=>{reads++;throw Error('Must not access API');}}));assert.equal(reads,0);
   if(kind==='file')assert.equal(await fs.readFile(output,'utf8'),'sentinel');if(kind==='broken-symlink')assert.equal(await fs.readlink(output),path.join(tmp,'absent'));
  }
  const actual=path.join(tmp,'actual');await fs.mkdir(actual);await fs.symlink(actual,path.join(tmp,'linked'));let reads=0;
  await assert.rejects(()=>runRepublish({output:path.join(tmp,'linked','new')},{api:async()=>{reads++;}}));assert.equal(reads,0);assert.deepEqual(await fs.readdir(actual),[]);
 }finally{await fs.rm(tmp,{recursive:true});}
});
test('failed admitted run retains a failed receipt and no completion receipt',async()=>{
 const tmp=await fs.realpath(await fs.mkdtemp(path.join(os.tmpdir(),'atlas-republish-failure-')));
 try{const output=path.join(tmp,'fresh');await assert.rejects(()=>runRepublish({output,deployment_id:1,account_id:'a'.repeat(32),api_token:'fixture-secret'},{api:async()=>{throw Error('Synthetic provider failure');}}));assert.deepEqual(await fs.readdir(output),['failure.json']);assert.ok(!(await fs.readFile(path.join(output,'failure.json'),'utf8')).includes('fixture-secret'));}
 finally{await fs.rm(tmp,{recursive:true});}
});
test('producer executes twice into fresh outputs with identical sanitized whole-file receipts',async()=>{
 const tmp=await fs.realpath(await fs.mkdtemp(path.join(os.tmpdir(),'atlas-republish-repeat-')));
 try{
  const receipts=[];
  for(const name of ['one','two']){const f=fixture(),output=path.join(tmp,name);await runRepublish({...f.options,output},f.options);assert.equal(f.postCount,1);assert.deepEqual(await fs.readdir(output),['provider-deployment.json']);const raw=await fs.readFile(path.join(output,'provider-deployment.json'));assert.ok(!raw.includes('fixture-secret'));receipts.push(raw);}
  assert.deepEqual(receipts[0],receipts[1]);
 }finally{await fs.rm(tmp,{recursive:true});}
});
test('documented stdin CLI rejects malformed/oversize secret-bearing input without echoing it',()=>{
 const cli=new URL('../scripts/cloudflare-republish.mjs',import.meta.url);
 for(const input of ['{"api_token":"fixture-sensitive-token", INVALID', 'fixture-sensitive-token'+'x'.repeat(65536)]){
  const result=spawnSync(process.execPath,[cli.pathname],{input,encoding:'utf8'});assert.equal(result.status,1);assert.equal(result.stdout,'');assert.ok(!result.stderr.includes('fixture-sensitive-token'));assert.match(result.stderr,/Publication not completed/);
 }
});
test('documented stdin CLI executes credential-free provider fixtures into a fresh output',async()=>{
 const tmp=await fs.realpath(await fs.mkdtemp(path.join(os.tmpdir(),'atlas-republish-cli-')));
 try{
  const f=fixture();await republishCurrentVersion(f.options);
  const routes={};for(const route of new Set(f.calls))routes[route]=await f.api(route);
  const gh=path.join(tmp,'gh'),preload=path.join(tmp,'fetch-fixture.mjs'),output=path.join(tmp,'fresh');
  await fs.writeFile(gh,'#!'+process.execPath+'\nconst routes='+JSON.stringify(routes)+'; const value=routes[process.argv[3]]; if(!value)process.exit(2); process.stdout.write(JSON.stringify(value));\n',{flag:'wx',mode:0o700});
  await fs.writeFile(preload,'Date.now=()=>'+f.options.now()+'; let posted=false; globalThis.fetch=async(url,options={})=>{let value;if(url.endsWith("/deployments")){if(options.method==="POST"){posted=true;value={success:true,result:'+JSON.stringify(f.providerAfter)+'};}else value={success:true,result:{deployments:[posted?'+JSON.stringify(f.providerAfter)+':'+JSON.stringify(f.providerBefore)+']}};}else if(url.endsWith("/export-marker"))value='+JSON.stringify(f.marker)+';else if(url.endsWith("/geography/release"))value='+JSON.stringify(f.release)+';else if(url.endsWith("/records/import"))return new Response("",{status:503});else throw Error("Unexpected fixture request");return new Response(JSON.stringify(value));};\n',{flag:'wx'});
  const result=spawnSync(process.execPath,['--import',preload,new URL('../scripts/cloudflare-republish.mjs',import.meta.url).pathname],{input:JSON.stringify({deployment_id:200,account_id:'a'.repeat(32),api_token:'fixture-secret',output}),encoding:'utf8',env:{...process.env,PATH:tmp+path.delimiter+process.env.PATH}});
  assert.equal(result.status,0,result.stderr);assert.equal(result.stderr,'');assert.equal(JSON.parse(result.stdout).provider_deployment_id,f.providerAfter.id);assert.ok(!result.stdout.includes('fixture-secret'));
  const receipt=JSON.parse(await fs.readFile(path.join(output,'provider-deployment.json'),'utf8'));assert.equal(receipt.delivery_settled,false);assert.equal(receipt.worker_version,f.before.result.worker_version);
 }finally{await fs.rm(tmp,{recursive:true});}
});

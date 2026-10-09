import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {runPREvidence} from '../scripts/check-pr-evidence.mjs';
import {gitBlobTransport} from '../scripts/git-blob-transport.mjs';
import {checkPremergeEvidence} from '../scripts/premerge-evidence.mjs';
import {renderClaim} from '../scripts/issue-claim-contract.mjs';
import {sha256, subjectsHash} from '../scripts/evidence-quality.mjs';

const base = 'a'.repeat(40), head = 'b'.repeat(40), repo = 'test/repo';
const prefix = 'coordination/engineering/transport-probe/';
const manifestPath = prefix + 'evidence-quality.json';
const oid = raw => createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
const descriptor = (name, raw) => ({path:name,bytes:raw.length,sha256:sha256(raw),hash_kind:'file-bytes'});
const policy = {version:1,mode:'enforce-new',activation_time:'2026-10-03T00:00:00Z'};

function fixture(t, {corrupt = false, quota = false, stale = false} = {}) {
  const cache = path.resolve('.cache'); fs.mkdirSync(cache,{recursive:true});
  const directory = fs.mkdtempSync(path.join(cache,'pr-transport-controls-'));
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  const baseline = Buffer.from('independent original\n'), result = Buffer.from('{"value":0.5}\n');
  const contents = new Map([['baseline.txt',baseline],[prefix+'result.json',result]]);
  for(let i=0;i<300;i++)contents.set(prefix+`proof-${i}.txt`,Buffer.from(`actual complete proof ${i}\n`));
  const outputs=[...contents].filter(([name])=>name!=='baseline.txt').map(([name,raw])=>descriptor(name,raw));
  const files=outputs.map(row=>({filename:row.path,status:'added'}));files.push({filename:manifestPath,status:'added'});
  const manifest={version:1,issue:100,lane:'engineering',worker_id:'author',subject_ids:[],subject_ids_sha256:subjectsHash([]),
    baseline:{commit:base,files:[descriptor('baseline.txt',baseline)],pins:{}},sources:[],outputs,
    methods:[{id:'code',kind:'code',description:'Complete byte-transport boundary control',software:'Node 24',units:'fraction'}],
    metrics:[{id:'share',value:0.5,unit:'fraction',vintage:'current',input_sha256:sha256(baseline),evaluation_commit:base}],
    summaries:[{metric_id:'share',value:0.5,unit:'fraction'}],conclusions:[],
    stages:{research:'complete',implementation:'implemented',geographic_approval:'not-requested'},commands:['node --test'],
    change_receipts:files.map(row=>({path:row.filename,status:row.status})),
    metric_bindings:[{metric_id:'share',path:prefix+'result.json',json_pointer:'/value'}]};
  contents.set(manifestPath,Buffer.from(JSON.stringify(manifest)));
  const blobs=new Map([...contents.values()].map(raw=>[oid(raw),raw]));
  const tree=[...contents].map(([name,raw])=>({path:name,type:'blob',mode:'100644',size:raw.length,sha:oid(raw)}));
  const spec={mode:'engineering',max_prs:1,depends_on:[],scope:'Complete transport test',evidence_quality:{version:1,
    manifest_path:manifestPath,subject_ids:[],pins:{},review_kind:'code'}};
  const issue={number:100,created_at:'2026-10-04T00:00:00Z',body:`<!-- worldatlas-work:v1\n${JSON.stringify(spec)}\n-->`};
  const claim={version:1,active:true,issue_number:100,worker_id:'author',claim_id:'fixture',branch:'engineering/transport-probe',expires_at:'2099-01-01T00:00:00Z'};
  const pr={number:101,head:{sha:stale?base:head,ref:claim.branch},base:{sha:base},body:'Refs #100\n',changed_files:files.length};
  const event={repository:{full_name:repo},pull_request:{number:101,head:{sha:head}}};
  let rest=0,blobReads=0,fetches=0,closed=false;
  const apiFactory=(_, {onRequest})=>async(route,method='GET')=>{
    rest++; assert.equal(method,'GET','Candidate must not mutate GitHub');
    if(quota)throw Object.assign(Error('Explicit shared quota rejection'),{github:{http_status:403,rate_remaining:'0',rate_reset:String(Math.ceil(Date.now()/1000)+60)}});
    onRequest({route,method,status:200});
    if(route===`/repos/${repo}/pulls/101`)return pr;
    if(route===`/repos/${repo}/issues/100`)return issue;
    if(route.includes('/issues/100/comments?'))return [{id:1,user:{login:'github-actions[bot]'},body:renderClaim(claim)}];
    if(route.includes('/pulls/101/files?')){const page=Number(new URL('https://test'+route).searchParams.get('page'));return files.slice((page-1)*100,page*100);}
    if(route.includes('/git/commits/'))return {tree:{sha:'tree'}};
    if(route.includes('/git/trees/'))return {truncated:false,tree};
    if(route.includes('/compare/'))return {status:'identical'};
    if(route.includes('/git/blobs/')){blobReads++;const sha=route.split('/').pop(),raw=blobs.get(sha);return {sha,size:raw.length,encoding:'base64',content:raw.toString('base64')};}
    throw Error('Unexpected route '+route);
  };
  const transportFactory=(api,options)=>{
    const transport=gitBlobTransport(api,{...options,execute:(command,args,settings)=>{
      // Model the large protocol inventory without hundreds of child processes.
      // git-blob-transport.test uses real objects; two live PR probes additionally
      // exercise real Git fetch/cat-file. Hash/size validation remains real here.
      if(args.includes('fetch')){fetches++;return Buffer.alloc(0);}
      if(args.includes('cat-file')){
        if(args.includes('-t'))return Buffer.from('blob\n');
        return corrupt?Buffer.from('coherently truncated body'):blobs.get(args.at(-1));
      }
      return execFileSync(command,args,settings);
    }});
    return {...transport,close(){transport.close();closed=true;}};
  };
  return {run:()=>runPREvidence({event,env:{GITHUB_REPOSITORY:repo,GH_TOKEN:'private-fixture-token'},directory,apiFactory,transportFactory,
    verify:options=>checkPremergeEvidence({...options,policy})}),counts:()=>({rest,blobReads,fetches,closed}),directory,event,apiFactory};
}

test('real premerge entry authenticates 302 complete bodies with one REST manifest and one Git batch',async t=>{
  const f=fixture(t), result=await f.run();
  assert.equal(result.status,'bytes-verified',result.reason);assert.equal(result.change_files_checked,302);
  assert.equal(f.counts().blobReads,1);assert.equal(f.counts().fetches,1);assert(f.counts().rest<25);
  assert(f.counts().closed);assert.equal(fs.readdirSync(f.directory).length,0);
  assert.equal(result.immutable_transport[0].blob_count,302);
});
test('corrupt transported bytes cannot become a successful gate and temporary objects are released',async t=>{
  const f=fixture(t,{corrupt:true}),result=await f.run();assert.equal(result.status,'incomplete-or-invalid');
  assert.match(result.reason,/bytes differ/);assert(f.counts().closed);assert.equal(fs.readdirSync(f.directory).length,0);
});
test('quota refusal retains its real reset and refuses without a retry storm',async t=>{
  const f=fixture(t,{quota:true}),result=await f.run();assert.equal(result.status,'incomplete-or-invalid');
  assert.equal(result.api_error.rate_remaining,'0');assert.equal(result.retryable,true);assert(Date.parse(result.retry_at)>Date.now());
  assert.equal(f.counts().rest,1);assert(f.counts().closed);assert.equal(f.counts().fetches,0);
});
test('stale current PR head is rejected before any evidence download',async t=>{
  const f=fixture(t,{stale:true}),result=await f.run();assert.equal(result.status,'incomplete-or-invalid');
  assert.match(result.reason,/head changed/);assert.equal(f.counts().blobReads,0);assert.equal(f.counts().fetches,0);
});
test('foreign repository events cannot create a transport or contact GitHub',async t=>{
  const f=fixture(t);await assert.rejects(runPREvidence({event:f.event,env:{GITHUB_REPOSITORY:'other/repo'},
    apiFactory:()=>assert.fail('foreign API'),transportFactory:()=>assert.fail('foreign object store')}),/another repository/);
});

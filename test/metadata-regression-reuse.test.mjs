import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {metadataRegressionProgram, matchMetadataRegressionProgram, METADATA_PROGRAMS, METADATA_FRESH_TESTS} from '../scripts/metadata-regression-program.mjs';
import {originalFullRegressionJobs} from '../scripts/regression-proof-jobs.mjs';
import {reusePRRegression, readMetadataRegressionCatalogue, createMetadataRegressionProofLoader} from '../scripts/reuse-pr-regression.mjs';
import {reusePRGeography} from '../scripts/reuse-pr-geography.mjs';
import {integrationProof, PROOF_PATHS, WORKFLOW_PATH, successfulMetadataRegressionJobs} from '../scripts/integration-proof.mjs';
const actualJobs = JSON.parse(fs.readFileSync(new URL('./fixtures/metadata-regression-original-jobs.json', import.meta.url))).jobs;
const P='fe3b14d9584fe0afa6e28437a99a0b8326413376',H='b1cc388a9489385314d3282768eb9e850da37cf8',B='a7bd8a1547ecf1271ebba8919b550cbea51b431d';
const RUN=38237899123, PREFIX='coordination/engineering/example/', manifest=PREFIX+'evidence-quality.json';
const gitHash=raw=>createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
function fixture() {
  const repo='owner/repo',branch='engineering/example',blobs=new Map();
  const entry=(name,value)=>{const raw=Buffer.from(typeof value==='string'?value:JSON.stringify(value)),sha=gitHash(raw);
    blobs.set(sha,{sha,size:raw.length,encoding:'base64',content:raw.toString('base64')});
    return {path:name,type:'blob',mode:'100644',sha,size:raw.length};};
  const workflow='ref: ${{ github.event.pull_request.head.sha }}\nname: Complete regression shard\nname: Build hosted assets';
  const entries=new Map([...PROOF_PATHS,...METADATA_FRESH_TESTS,'scripts/science.mjs'].map(name=>[name,entry(name,name===WORKFLOW_PATH?workflow:'known code '+name)]));
  const definition={version:1,inputs:['.github/package-inputs.json','scripts/','src/'],optional_inputs:[],verification_paths:['test/'],generated_outputs:['dist/']};
  for(const [name,value] of [['.github/package-inputs.json',definition],[manifest,{version:1,outputs:[]}],[PREFIX+'README.md','old prose'],['data/selection.json','{}']])entries.set(name,entry(name,value));
  const source={object:{sha:P,tree:{sha:'d'.repeat(40)},parents:[{sha:B}]},entries};
  const current={object:{sha:H,tree:{sha:'e'.repeat(40)},parents:[{sha:P}]},entries:new Map(entries)};
  current.entries.set(PREFIX+'README.md',entry(PREFIX+'README.md','new prose'));
  current.entries.set(manifest,entry(manifest,{version:1,outputs:[{path:PREFIX+'README.md'}]}));
  const trusted={object:{sha:B,tree:{sha:'f'.repeat(40)},parents:[]},entries:new Map([...entries].filter(([name])=>!name.startsWith(PREFIX)))};
  const catalogue={version:1,kind:'audited-metadata-regression-programs-v1',programs:[{id:'fixture',...metadataRegressionProgram(entries,PREFIX)}]};
  trusted.entries.set(METADATA_PROGRAMS,entry(METADATA_PROGRAMS,catalogue));
  const trees=new Map([source,current,trusted].map(t=>[t.object.tree.sha,t])),commits=new Map([source,current,trusted].map(t=>[t.object.sha,t.object]));
  const pr={number:7,state:'open',body:'Refs #8',head:{sha:H,ref:branch,repo:{full_name:repo}},base:{sha:B,ref:'main',repo:{full_name:repo}}};
  const issue={number:8,state:'open',body:'<!-- worldatlas-work:v1\n'+JSON.stringify({max_prs:1,depends_on:[],scope:'fixture',mode:'engineering',evidence_quality:{manifest_path:manifest}})+'\n-->'};
  const run={id:RUN,run_attempt:1,head_sha:P,head_branch:branch,event:'pull_request',path:WORKFLOW_PATH,repository:{full_name:repo},head_repository:{full_name:repo},status:'completed',conclusion:'failure',pull_requests:[{number:7,head:{sha:H}}]};
  const origin={run_id:RUN,run_attempt:1,job_id:114773123979,head:P,tree:source.object.tree.sha,baseline:B,artifact_id:301,artifact_name:'proposed-geography-7-1',artifact_digest:'a'.repeat(64),artifact_bytes:1024,report_sha256:'b'.repeat(64),report_bytes:512};
  const report={version:1,method_id:'worldatlas-trusted-geography-check-v1',baseline_commit:B,trusted_code_commit:B,candidate_commit:P,candidate_code_executed:false,published:false,source_approval:false,gate_status:'passed',status:'not-applicable'};
  const f={repo,branch,entry,source,current,trusted,catalogue,pr,issue,run,origin,report,definition,jobs:structuredClone(actualJobs),calls:[],inspections:[]};
  f.api=async route=>{f.calls.push(route);
    if(route.endsWith('/pulls/7'))return structuredClone(f.pr);
    if(route.endsWith('/issues/8'))return structuredClone(f.issue);
    if(route.includes('/git/commits/'))return structuredClone(commits.get(route.split('/').at(-1)));
    if(route.includes('/git/trees/')){const sha=route.split('/').at(-1).split('?')[0];return {sha,truncated:false,tree:structuredClone([...trees.get(sha).entries.values()])};}
    if(route.includes('/git/blobs/'))return structuredClone(blobs.get(route.split('/').at(-1)));
    if(route.includes('/actions/workflows/'))return {workflow_runs:[structuredClone(f.run)]};
    if(route.includes('/jobs?'))return {jobs:structuredClone(f.jobs)};
    if(route.endsWith('/actions/runs/'+RUN))return structuredClone(f.run);
    throw Error('unexpected route '+route);
  };
  f.options={event:{repository:{full_name:repo},pull_request:structuredClone(pr)},repo,api:f.api,token:'fixture-token',
    loadGeography:async()=>({source:f.origin,report:f.report}),
    reuseGeography:args=>reusePRGeography({...args,acquire(){},inspect:async args=>{f.inspections.push(args);return {status:'unchanged-selected-inputs',baseline_commit:P,candidate_commit:H,trusted_reader_policy_commit:B,candidate_code_executed:false,science_reexecuted:false,...f.applicability};}})};
  f.match=()=>matchMetadataRegressionProgram({...f});
  f.reuse=()=>reusePRRegression(f.options);
  return f;
}

test('trusted program catalogue authenticates exact ordinary bounded Git blob bytes',async()=>{
  const f=fixture(),args={api:f.api,repo:f.repo,trusted:f.trusted};
  assert.deepEqual(await readMetadataRegressionCatalogue(args),f.catalogue);
  for(const change of [entry=>{entry.mode='120000';},entry=>{entry.type='tree';},entry=>{entry.size=65537;},entry=>{entry.size=0;}]){
    const g=fixture();change(g.trusted.entries.get(METADATA_PROGRAMS));
    await assert.rejects(readMetadataRegressionCatalogue({api:g.api,repo:g.repo,trusted:g.trusted}),/catalogue-unavailable/);
  }
  for(const change of [body=>{body.sha='0'.repeat(40);},body=>{body.encoding='utf8';},body=>{body.size++;},
    body=>{body.content=Buffer.from('altered catalogue').toString('base64');}]){
    const api=async route=>{const body=await f.api(route);change(body);return body;};
    await assert.rejects(readMetadataRegressionCatalogue({...args,api}),/catalogue-(?:body-unavailable|integrity)/);
  }
});

test('actual scope-failed original full jobs remain successful computation with original immutable identities',()=>{
  const pin={run:RUN,attempt:1,head:P};assert.equal(actualJobs.find(j=>j.name==='scope').conclusion,'failure');
  assert.equal(originalFullRegressionJobs(actualJobs,pin).length,5);
  for(const name of ['profile','package','regression (0)','regression (1)','regression (2)'])for(const alter of [
    j=>{j.find(x=>x.name===name).conclusion='failure';},j=>j.splice(j.findIndex(x=>x.name===name),1),j=>j.push(structuredClone(j.find(x=>x.name===name))),
    j=>{j.find(x=>x.name===name).head_sha=H;},j=>{j.find(x=>x.name===name).run_attempt=2;}
  ]){const jobs=structuredClone(actualJobs);alter(jobs);assert.equal(originalFullRegressionJobs(jobs,pin),null);}
});

test('known program retains the full test inventory, code namespaces, selectors and compressed executable images',()=>{
  for(const name of ['test/new.test.mjs','scripts/new.mjs','src/main.js','hosted/route.js','.github/workflows/new.yml','package-lock.json',
    'coordination/engineering/helper/run.py','coordination/engineering/eastern-two-gap-repair-native-20261007/prior-v1/part-003.bin.gz',
    'coordination/engineering/selected-geography-effective-prevention-20261009/supported-programs.json']){
    const f=fixture();f.source.entries.set(name,f.entry(name,'new body'));f.current.entries.set(name,f.source.entries.get(name));assert.throws(f.match,/unknown-regression-program/);
  }
  const f=fixture();assert.equal(f.match().id,'fixture');f.current.entries.set('scripts/science.mjs',f.entry('scripts/science.mjs','changed'));assert.throws(f.match,/changed-regression-program/);
});

test('receiving directory absence is required even when the two metadata filenames are absent on base',()=>{
  for(const name of [PREFIX.slice(0,-1),PREFIX+'old-file.json',manifest]){const f=fixture();f.trusted.entries.set(name,f.entry(name,'old'));assert.throws(f.match,/receiving-packet-already-on-base/);}
  const f=fixture();f.catalogue.programs.push(structuredClone(f.catalogue.programs[0]));assert.throws(f.match,/unknown-regression-program/);
});

test('actual orchestration keeps original successful jobs and science source separate from current acceptance',async()=>{
  const f=fixture(),report=JSON.stringify(f.report),result=await f.reuse();
  assert.equal(result.status,'reused-original');assert.equal(result.reviewed_head,H);assert.equal(result.original_computation.head,P);
  assert.equal(result.original_computation.run_id,RUN);assert.equal(result.original_computation.jobs.length,5);
  assert.equal(result.regression_reexecuted,false);assert.equal(result.package_rebuilt,false);assert.equal(result.transferable_geography_authority,false);
  assert.deepEqual(result.fresh_tests,METADATA_FRESH_TESTS);assert.equal(JSON.stringify(f.report),report);assert.equal(f.inspections.length,1);
});

test('unknown program refuses before fetching scientific reports or inspecting inputs',async()=>{
  const f=fixture();f.source.entries.set('test/new.test.mjs',f.entry('test/new.test.mjs','new'));f.current.entries.set('test/new.test.mjs',f.source.entries.get('test/new.test.mjs'));
  await assert.rejects(f.reuse(),/unknown-regression-program/);assert.equal(f.inspections.length,0);assert(!f.calls.some(r=>r.includes('/actions/')));
});

test('consumed metadata, changed baseline, failed source computation, current authority and source attempt all refuse',async()=>{
  for(const alter of [
    f=>{f.applicability={status:'full-check-required'};},
    f=>{f.report.baseline_commit='0'.repeat(40);},
    f=>{f.jobs.find(j=>j.name==='regression (1)').conclusion='failure';},
    f=>{f.pr.head.sha=P;},
    f=>{f.run.run_attempt=2;},
    f=>{f.definition.verification_paths.push(PREFIX);for(const t of [f.source,f.current])t.entries.set('.github/package-inputs.json',f.entry('.github/package-inputs.json',f.definition));}
  ]){const f=fixture();alter(f);await assert.rejects(f.reuse());}
});

function currentProofFixture() {
  const f=fixture(), id=202, step=(name,conclusion='success')=>({name,status:'completed',conclusion});
  const make=(name,steps,offset)=>({id:500+offset,run_id:id,run_attempt:1,head_sha:H,name,status:'completed',conclusion:'success',steps});
  const jobs=[
    make('profile',['Validate ownership and focused CI applicability','Authenticate predecessor regression inputs'].map(n=>step(n)),0),
    make('regression (0)',[step('Checkout reviewed head'),step('Checkout reviewed head','skipped'),step('Install Node dependencies'),
      step('Run current-head regression consumers'),step('Complete regression shard','skipped'),step('Build hosted assets','skipped')],1),
    make('package',[step('Use authenticated predecessor package verification')],2),
    ...['scope','evidence','geography'].map((name,i)=>make(name,[],3+i))
  ];
  const run={...f.run,id,head_sha:H,conclusion:'success',pull_requests:[{number:7,head:{sha:H}}]};
  const api=async route=>{
    if(route.includes('/actions/workflows/'))return {workflow_runs:[run]};
    if(route.includes(`/actions/runs/${id}/attempts/`))return {jobs};
    if(route.endsWith(`/actions/runs/${id}`))return run;
    return f.api(route);
  };
  const options={api,repo:f.repo,number:7,head:H,profile:'full',baseline:f.trusted,authored:f.current,candidate:structuredClone(f.current),
    metadataProofLoader:async args=>{
      assert.equal(args.head,H);assert.equal(args.baseline,f.trusted.object.sha);
      return f.reuse();
    }};
  return {...f,currentRun:run,currentJobs:jobs,proofOptions:options};
}

test('queue proof pins current successful controls separately and revalidates original jobs without geography authority',async()=>{
  const f=currentProofFixture(), proof=await integrationProof(f.proofOptions);
  assert.equal(proof.run_id,202);assert.equal(proof.tree,f.current.object.tree.sha);
  assert.equal(proof.metadata_regression.original_computation.run_id,RUN);
  assert.equal(proof.metadata_regression.original_computation.head,P);assert.equal(proof.geography_job_id,undefined);
  const final={...f.proofOptions,runId:202,runAttempt:1};assert.deepEqual(await integrationProof(final),proof);
  f.jobs.find(job=>job.name==='regression (1)').conclusion='failure';assert.equal(await integrationProof(final),null);
});

test('current controls must actually execute once; missing, failed, skipped, duplicate and relabelled jobs refuse',async()=>{
  for(const alter of [
    f=>{f.currentJobs[1].steps.find(s=>s.name==='Run current-head regression consumers').conclusion='skipped';},
    f=>{f.currentJobs[1].conclusion='failure';},f=>{f.currentJobs[1].head_sha=P;},
    f=>{f.currentJobs[1].steps.push(structuredClone(f.currentJobs[1].steps.find(s=>s.name==='Run current-head regression consumers')));},
    f=>{f.currentJobs[1].steps.find(s=>s.name==='Complete regression shard').conclusion='success';},
    f=>{f.currentJobs[1].steps.find(s=>s.name==='Checkout reviewed head'&&s.conclusion==='skipped').conclusion='success';},
    f=>{f.currentJobs.push({...f.currentJobs[1],name:'regression (1)'});},
    f=>{f.currentJobs[2].steps=[];},f=>{f.proofOptions.metadataProofLoader=undefined;},
    f=>{f.proofOptions.candidate.object.tree.sha='0'.repeat(40);},
    f=>{f.trusted.object.sha='0'.repeat(40);}
  ]){const f=currentProofFixture();alter(f);assert.equal(await integrationProof(f.proofOptions),null);}
});

test('current evidence-only failure stays narrow and source/control reruns invalidate final pins',async()=>{
  const f=currentProofFixture();f.currentRun.conclusion='failure';f.currentJobs.find(j=>j.name==='evidence').conclusion='failure';
  assert.ok(await integrationProof(f.proofOptions));
  f.currentJobs.find(j=>j.name==='scope').conclusion='failure';assert.equal(await integrationProof(f.proofOptions),null);
  const other=currentProofFixture();other.currentRun.run_attempt=2;
  assert.equal(await integrationProof({...other.proofOptions,runId:202,runAttempt:1}),null);
  assert.equal(originalFullRegressionJobs(other.currentJobs,{run:202,attempt:1,head:H}),null,'a reuse run is never an original complete producer');
});


test('queue caches only identical immutable operand equivalence while repeating all authority loading',async()=>{
  let inspections=0,loads=0;
  const loader=createMetadataRegressionProofLoader({token:'fixture',directory:'/fixture',
    inspect:async options=>{inspections++;return {status:'unchanged-selected-inputs',baseline_commit:options.baseline,
      candidate_commit:options.candidate,trusted_reader_policy_commit:options.trusted,candidate_code_executed:false,science_reexecuted:false,rows:['original']};},
    load:async options=>{loads++;return options.inspect({baseline:options.source,candidate:options.head,trusted:options.baseline,metadataPaths:options.paths});}});
  const options={api:async()=>({}),repo:'owner/repo',source:P,head:H,baseline:B,paths:[manifest]};
  const first=await loader(options);first.rows.push('caller mutation');
  assert.deepEqual((await loader(options)).rows,['original']);assert.equal(inspections,1);assert.equal(loads,2);
  for(const changed of [{...options,source:B},{...options,head:P},{...options,baseline:P},{...options,paths:[PREFIX+'README.md']}])await loader(changed);
  assert.equal(inspections,5);assert.equal(loads,6);
});


test('cold routing tree reads use the current queue admitted API and preserve recursive identity',async()=>{
  const calls=[];
  const loader=createMetadataRegressionProofLoader({directory:'/fixture',
    acquire:options=>({read:options.loadTree}),
    inspect:async options=>{await options.acquisition.read(P,true);await options.acquisition.read(B,false);return {status:'full-check-required'};},
    load:options=>options.inspect({baseline:P,candidate:H,trusted:B,metadataPaths:[manifest]})});
  const api=async route=>{calls.push(route);return {};};
  await loader({api,repo:'owner/repo'});
  assert.deepEqual(calls,[`/repos/owner/repo/git/trees/${P}?recursive=1`,`/repos/owner/repo/git/trees/${B}`]);
  await assert.rejects(loader({repo:'owner/repo'}),/metadata-proof-api-unavailable/);
  await assert.rejects(loader({repo:'owner/repo',api:async()=>{throw Error('quota-admission-refused');}}),/quota-admission-refused/);
});

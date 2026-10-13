import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {authenticateOriginalPackageOutput, requireOriginalPackageOutput,
  requirePackageAssemblyExecution, issuePackageAssemblyExecution} from '../coordination/engineering/additive-native-activation-20261009/package-selected-additive.mjs';
import {requireRetainedPackageTests, integrationTestFiles} from '../scripts/run-integration-tests.mjs';
import {admitAssemblyAtlasMetadata,createPackageAssemblyScratch,packageAssemblyInvocation,findOriginalPackage} from '../scripts/assemble-selected-package.mjs';
import {execFileSync,spawnSync} from 'node:child_process';
import {committedPackageInputs,committedPackageProducer} from '../scripts/package-output-artifact.mjs';

const sha=raw=>createHash('sha256').update(raw).digest('hex');
function original(t,{worker=false}={}){
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-original-package-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const bodies={'dist/client/atlas-geography.json':'{}','dist/client/a.bin':'invariant',
    'dist/cloudflare/index.js':'worker','dist/cloudflare/wrangler.json':'{}'};
  for(const [name,body]of Object.entries(bodies)){fs.mkdirSync(path.dirname(path.join(root,name)),{recursive:true});fs.writeFileSync(path.join(root,name),body);}
  const head='a'.repeat(40),workflowHead=worker?'c'.repeat(40):head,repo='ChengshuLi/WorldAtlas';
  const origin={run_id:17,run_attempt:2,job_id:29,artifact_id:41,head,workflow_head:workflowHead,
    artifact_name:'cloudflare-package-output-17-2',artifact_digest:'b'.repeat(64),artifact_bytes:2000};
  const output={files:Object.entries(bodies).map(([name,body])=>({path:name,bytes:Buffer.byteLength(body),sha256:sha(body)})),
    bytes:Object.values(bodies).reduce((n,body)=>n+Buffer.byteLength(body),0)};
  const workflow={path:worker?'.github/workflows/worker-merge.yml':'.github/workflows/merge-integration-checks.yml',
    type:'blob',mode:'100644',sha:'d'.repeat(40)};
  const manifest={version:1,kind:'original-cloudflare-package-output',source:{head,producer:{kind:'immediate-cloudflare-build-v1',
    workflows:[{path:workflow.path,mode:workflow.mode,oid:workflow.sha}]}},output};
  const raw=Buffer.from(JSON.stringify(manifest)+'\n');
  const run={id:17,run_attempt:2,head_sha:workflowHead,event:worker?'workflow_dispatch':'pull_request',path:workflow.path,head_branch:worker?'main':'engineering/fixture',
    status:'completed',repository:{full_name:repo},head_repository:{full_name:repo}};
  const names=worker?['Snapshot original final-worker package inputs','Build the combined application once before asset-dependent tests',
    'Inventory original final-worker package output','Read back qualified native build outputs when selected',
    'Test applicable combined-tree invariants without publishing or live imports','Retain original final-worker package output']:
    ['Snapshot original selected package inputs','Build Cloudflare package without publishing','Inventory original selected package output',
      'Verify package controls','Read back qualified native build outputs when selected','Run selected-data consumer checks','Retain original selected package output'];
  const job={id:29,run_id:17,run_attempt:2,head_sha:workflowHead,name:worker?'integration (0)':'package',status:'completed',conclusion:'success',
    steps:names.map((name,index)=>({name,number:index+1,status:'completed',conclusion:'success'}))};
  const artifact={id:41,name:origin.artifact_name,size_in_bytes:2000,digest:'sha256:'+origin.artifact_digest,
    expired:false,workflow_run:{id:17,head_sha:workflowHead}};
  const receipt={package_output_manifest_sha256:sha(raw),package_output_manifest_bytes:raw.length,original_head:head};
  const log=()=>[JSON.stringify(receipt),`SHA256 digest of uploaded artifact zip is ${origin.artifact_digest}`,
    `Artifact ${origin.artifact_name} has been successfully uploaded! Final size is 2000 bytes. Artifact ID is 41`].join('\n');
  const api=async route=>{
    if(route.endsWith('/attempts/2'))return run;
    if(route.endsWith('/jobs/29'))return job;
    if(route.endsWith('/artifacts/41'))return artifact;
    if(route.includes('/git/commits/'))return {tree:{sha:'e'.repeat(40)}};
    if(route.endsWith('/git/trees/'+'e'.repeat(40)))return {tree:[{path:'.github',type:'tree',mode:'040000',sha:'6'.repeat(40)}],truncated:false};
    if(route.endsWith('/git/trees/'+'6'.repeat(40)))return {tree:[{path:'workflows',type:'tree',mode:'040000',sha:'7'.repeat(40)}],truncated:false};
    if(route.endsWith('/git/trees/'+'7'.repeat(40)))return {tree:[{...workflow,path:path.posix.basename(workflow.path)}],truncated:false};
    if(route.includes('/git/trees/'))return {tree:[workflow],truncated:false};
    throw Error('Unexpected mocked authority route: '+route);
  };
  api.jobLogRedirect=async()=>new Response(null,{status:302,headers:{location:'https://fixture.blob.core.windows.net/job-log'}});
  return {root,repo,origin,manifestRaw:raw,api,run,job,artifact,receipt,log,workflow};
}

test('actual original-job admission mints a private token and never brands copied JSON',async t=>{
  const f=original(t),old=globalThis.fetch;
  globalThis.fetch=async(url,options)=>{assert.equal(String(url),'https://fixture.blob.core.windows.net/job-log');
    assert.equal(options.headers,undefined);return new Response(f.log());};t.after(()=>{globalThis.fetch=old;});
  const token=await authenticateOriginalPackageOutput(f);
  assert.equal(requireOriginalPackageOutput(token).manifest.source.head,f.origin.head);
  assert.throws(()=>requireOriginalPackageOutput(structuredClone(token)),/Privately authenticated/);
  assert.throws(()=>requirePackageAssemblyExecution({kind:'current-selected-package-assembly'}),/Private current/);
});

test('origin, successful actual steps, upload receipt and output mutations fail independently',async t=>{
  const old=globalThis.fetch;t.after(()=>{globalThis.fetch=old;});
  const cases=[
    f=>{f.run.head_sha='c'.repeat(40);},
    f=>{f.job.head_sha='c'.repeat(40);},
    f=>{f.artifact.workflow_run.head_sha='c'.repeat(40);},
    f=>{f.workflow.sha='f'.repeat(40);},
    f=>{f.workflow.mode='100755';},
    f=>{f.receipt.original_head='c'.repeat(40);},
    f=>{f.run.path='.github/workflows/unknown.yml';},
    f=>{f.job.run_attempt=1;},
    f=>{f.job.conclusion='failure';},
    f=>{f.job.steps.find(row=>row.name==='Build Cloudflare package without publishing').conclusion='skipped';},
    f=>{f.job.steps=f.job.steps.filter(row=>row.name!=='Run selected-data consumer checks');},
    f=>{f.artifact.expired=true;},
    f=>{f.artifact.digest='sha256:'+'d'.repeat(64);},
    f=>{f.receipt.package_output_manifest_sha256='e'.repeat(64);},
    f=>{const log=f.log;f.log=()=>log()+'\n'+log();},
    f=>{fs.writeFileSync(path.join(f.root,'dist/client/a.bin'),'invarianT');},
    f=>{fs.writeFileSync(path.join(f.root,'dist/client/extra'),'extra');},
  ];
  for(const mutate of cases){const f=original(t);mutate(f);globalThis.fetch=async()=>new Response(f.log());
    await assert.rejects(authenticateOriginalPackageOutput(f));}
});

test('retained consumer roster keeps current coverage and GPU/Canvas tests',()=>{
  const files=integrationTestFiles('full',0,'selected-output');
  assert(files.includes('test/compact-ownership.test.mjs'));
  assert(!files.includes('test/prepared-parity.test.mjs'));assert(!files.includes('test/canonical-compact-repack.test.mjs'));
  const full=integrationTestFiles('full',0,'complete');
  assert(full.includes('test/canonical-compact-repack.test.mjs'));assert(full.includes('test/prepared-parity.test.mjs'));
  assert.throws(()=>integrationTestFiles('full',1,'selected-output'));
  assert.throws(()=>requireRetainedPackageTests({expected:null}),/Trusted current/);
});

test('consumer reduction binds actual current head and trusted assembly receipt digest',t=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-current-assembly-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  execFileSync('git',['init','-q',root]);fs.writeFileSync(path.join(root,'source'),'source');
  const git=(...args)=>execFileSync('git',['-C',root,...args],{encoding:'utf8'}).trim();
  git('add','.');git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture');
  const head=git('rev-parse','HEAD'),receipt={kind:'cloudflare',preflight:{inputs:{head}},assembly:{
    kind:'retained-original-output-plus-current-additive',current_execution:{source_commit:head},
    base_restoration_invoked:false,invariant_build_invoked:false,
    base_tests_reused:['test/canonical-compact-repack.test.mjs','test/prepared-parity.test.mjs'],origin:{run_id:17}}};
  fs.mkdirSync(path.join(root,'.cache'));const file=path.join(root,'.cache/package-input-build.json');
  const write=value=>{const raw=JSON.stringify(value);fs.writeFileSync(file,raw);return sha(raw);};
  const expected=write(receipt);assert.equal(requireRetainedPackageTests({directory:root,expected}).origin.run_id,17);
  fs.appendFileSync(file,' ');assert.throws(()=>requireRetainedPackageTests({directory:root,expected}),/digest differs/);
  receipt.assembly.current_execution.source_commit='f'.repeat(40);
  assert.throws(()=>requireRetainedPackageTests({directory:root,expected:write(receipt)}),/same-head/);
});

test('actual emitted atlas admission follows observed size and shared memory rather than a control-receipt cap',()=>{
  const observed=10547753;
  assert.equal(admitAssemblyAtlasMetadata(observed,{phaseBytes:2*observed}),observed);
  assert.throws(()=>admitAssemblyAtlasMetadata(observed,{phaseBytes:2*observed-1}),/current metadata allocation/);
  for(const bytes of [0,-1,NaN,Number.MAX_SAFE_INTEGER+1])assert.throws(()=>admitAssemblyAtlasMetadata(bytes,{phaseBytes:Infinity}));
});

test('explicit hosted proof cannot silently report normal fallback success',t=>{
  const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-proof-invocation-'));
  t.after(()=>fs.rmSync(temporary,{recursive:true,force:true}));
  for(const [event,workflow,status] of [['workflow_dispatch','Selected package equivalence proof',1],
    ['pull_request','Integration queue regression',0],['workflow_dispatch','Serialize worker PR merges',0],['workflow_dispatch','Unrelated workflow',0]]){
    const result=spawnSync(process.execPath,['scripts/assemble-selected-package.mjs'],{
      env:{...process.env,GH_TOKEN:'',GITHUB_TOKEN:'',GITHUB_EVENT_NAME:event,
        GITHUB_WORKFLOW:workflow,GITHUB_OUTPUT:path.join(temporary,workflow)},encoding:'utf8'});
    assert.equal(result.status,status,result.stderr);assert.equal(JSON.parse(result.stdout).assembled,false);
    assert.match(fs.readFileSync(path.join(temporary,workflow),'utf8'),/^assembled=false\n/);
  }
});


test('fresh selected assembly creates owned ordinary scratch without depending on a previous build',async t=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-fresh-assembly-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const first=await createPackageAssemblyScratch(root),second=await createPackageAssemblyScratch(root);
  assert.ok(fs.lstatSync(path.join(root,'.cache')).isDirectory());
  for(const dir of [first,second]){
    assert.equal(path.dirname(dir),path.join(root,'.cache'));
    assert.match(path.basename(dir),/^selected-package-/);assert.ok(fs.lstatSync(dir).isDirectory());
  }
  assert.notEqual(first,second);
});
test('selected assembly rejects symlink, dangling-link and non-directory scratch without touching targets',async t=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-hostile-scratch-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const cache=path.join(root,'.cache'),outside=path.join(root,'outside');fs.mkdirSync(outside);
  fs.writeFileSync(path.join(outside,'sentinel'),'preserve');
  for(const target of [outside,path.join(root,'absent')]){
    fs.symlinkSync(target,cache);await assert.rejects(createPackageAssemblyScratch(root),/Ordinary package assembly scratch/);fs.unlinkSync(cache);
  }
  fs.writeFileSync(cache,'preserve cache');await assert.rejects(createPackageAssemblyScratch(root),/Ordinary package assembly scratch/);
  assert.equal(fs.readFileSync(cache,'utf8'),'preserve cache');assert.deepEqual(fs.readdirSync(outside),['sentinel']);
});


test('production assembly admission is independent of optional proof-reference metadata',()=>{
  const environment={GITHUB_EVENT_NAME:'workflow_dispatch',GITHUB_WORKFLOW:'Selected package equivalence proof'};
  const inputs={source_head:'a'.repeat(40),original_run_id:'17'};
  const expected={proofMode:true,expectedHead:inputs.source_head,originalRunId:17};
  assert.deepEqual(packageAssemblyInvocation({inputs},environment),expected);
  assert.deepEqual(packageAssemblyInvocation({inputs:{...inputs,readback_run_id:'not-an-authority',readback_attempt:'missing'}},environment),expected);
  for(const mutation of [{source_head:'main'},{original_run_id:'0'},{original_run_id:'9007199254740993'}])
    assert.throws(()=>packageAssemblyInvocation({inputs:{...inputs,...mutation}},environment),/Exact/);
  const source=fs.readFileSync(new URL('../scripts/assemble-selected-package.mjs',import.meta.url),'utf8');
  assert.doesNotMatch(source,/loadSelectedPackageReadback|compareSelectedPackageReadback|proofReadback/);
});


function sourceFixture(f){
  const write=(name,raw)=>{fs.mkdirSync(path.dirname(path.join(f.root,name)),{recursive:true});fs.writeFileSync(path.join(f.root,name),typeof raw==='string'?raw:JSON.stringify(raw));};
  const git=(...args)=>execFileSync('git',['-C',f.root,...args],{encoding:'utf8'}).trim();
  const commit=()=>{git('add','.');git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','source');};
  const definition={version:1,inputs:['.github/package-inputs.json','data/ownership-selection.json','scripts/builder.mjs','package-lock.json','scripts/package-output-artifact.mjs','scripts/package-node-runtime.mjs'],
    optional_inputs:[],verification_paths:[],generated_outputs:['dist/']};
  const selection={version:1,additive_release:{path:'coordination/engineering/original/release.json'}};
  write('.github/package-inputs.json',definition);write('data/ownership-selection.json',selection);
  write('.github/workflows/merge-integration-checks.yml','actual build invocation');
  write('.github/workflows/worker-merge.yml','actual final-worker build invocation');
  write('scripts/assemble-selected-package.mjs','// Synthetic current entry point for private admission controls.');
  write('scripts/builder.mjs','actual consumed builder');write('package-lock.json','{}');
  write('scripts/package-output-artifact.mjs','capture writer');write('scripts/package-node-runtime.mjs','runtime inventory');
  git('init','-q');commit();
  const snapshot=()=>({head:git('rev-parse','HEAD'),tree:git('rev-parse','HEAD^{tree}'),definition,selection,
    files:committedPackageInputs(f.root,definition),producer:committedPackageProducer(f.root)});
  return {write,git,commit,snapshot};
}

test('private assembly admission uses actual declared inputs and rejects legacy capture semantics',async t=>{
  // Exercise the actual plain-process guard instead of altering execArgv in the test.
  if(process.execArgv.length||process.env.NODE_OPTIONS?.trim()||process.env.NODE_PATH?.trim()){
    execFileSync(process.execPath,[new URL(import.meta.url).pathname],{env:{...process.env,NODE_OPTIONS:'',NODE_PATH:'',NODE_TEST_CONTEXT:undefined},encoding:'utf8'});return;
  }
  const f=original(t),s=sourceFixture(f),manifest=JSON.parse(f.manifestRaw),oldFetch=globalThis.fetch,oldEntry=process.argv[1];
  const stage=fs.mkdtempSync(path.join(f.root,'stage-'));
  t.after(()=>{globalThis.fetch=oldFetch;process.argv[1]=oldEntry;});
  manifest.source=s.snapshot();
  f.origin.head=f.origin.workflow_head=f.run.head_sha=f.job.head_sha=f.artifact.workflow_run.head_sha=f.receipt.original_head=manifest.source.head;
  f.workflow.sha=manifest.source.producer.workflows.find(row=>row.path===f.workflow.path).oid;
  const authenticate=async source=>{
    f.manifestRaw=Buffer.from(JSON.stringify({...manifest,source})+'\n');
    f.receipt.package_output_manifest_sha256=sha(f.manifestRaw);f.receipt.package_output_manifest_bytes=f.manifestRaw.length;
    return authenticateOriginalPackageOutput(f);
  };
  globalThis.fetch=async()=>new Response(f.log());
  const token=await authenticate(manifest.source);
  process.argv[1]=path.join(f.root,'scripts/assemble-selected-package.mjs');
  const issue=original=>issuePackageAssemblyExecution({original,source:f.root,stage,executingRoot:f.root,inheritedMetadata:[null,null,null,null,null]});
  assert.doesNotThrow(()=>requirePackageAssemblyExecution(issue(token)));
  for(const name of ['test/incidental.test.mjs','scripts/observer.mjs','.github/workflows/unrelated.yml']){
    s.write(name,'unconsumed observer');s.commit();assert.doesNotThrow(()=>requirePackageAssemblyExecution(issue(token)),name);
  }
  const declaration=JSON.parse(fs.readFileSync(path.join(f.root,'.github/package-inputs.json'),'utf8'));
  const childInput='coordination/engineering/child-reader/authority.json';
  declaration.inputs.push(childInput);s.write('.github/package-inputs.json',declaration);
  s.write(childInput,{authority:'read by a detached scientific reader'});s.commit();
  const admitted=issue(token);assert.equal(Object.hasOwn(admitted,'pending_selected_inputs'),false,
    'A parent-only list is not a scientific consumption inventory');
  assert.doesNotThrow(()=>requirePackageAssemblyExecution(admitted));
  for(const name of ['coordination/engineering/child-reader/helper.mjs','coordination/engineering/child-reader/absent.json']){
    const bad=structuredClone(declaration);bad.inputs.push(name);s.write('.github/package-inputs.json',bad);
    if(name.endsWith('.mjs'))s.write(name,'executable');s.commit();
    assert.throws(()=>issue(token),/Exact inert selected additions required/);
    s.write('.github/package-inputs.json',declaration);
    if(name.endsWith('.mjs'))fs.unlinkSync(path.join(f.root,name));s.commit();
  }
  for(const name of ['scripts/builder.mjs','package-lock.json','scripts/package-output-artifact.mjs','scripts/package-node-runtime.mjs','.github/workflows/merge-integration-checks.yml','.github/workflows/worker-merge.yml']){
    const old=fs.readFileSync(path.join(f.root,name),'utf8');s.write(name,'changed');s.commit();
    assert.throws(()=>issue(token),/input changed|producer workflow required/,name);
    s.write(name,old);s.commit();
  }
  const legacy={...manifest.source};delete legacy.producer;legacy.programme=[];
  await assert.rejects(authenticate(legacy),/Actual executed producer workflow/);
});

function originalDiscovery(t,{worker=false}={}){
  const f=original(t,{worker}),s=sourceFixture(f),before=s.snapshot(),repo=f.repo;
  const rows=s.git('ls-tree','-rlz','HEAD').split('\0').filter(Boolean).map(line=>{
    const [metadata,name]=line.split('\t'),[mode,type,oid,size]=metadata.trim().split(/\s+/);
    return {path:name,mode,type,sha:oid,size:Number(size)};
  });
  f.origin.head=f.receipt.original_head=before.head;
  if(!worker)f.origin.workflow_head=f.run.head_sha=f.job.head_sha=f.artifact.workflow_run.head_sha=before.head;
  f.workflow.sha=before.producer.workflows.find(row=>row.path===f.workflow.path).oid;
  const sourceHead=before.head,workflowHead=f.origin.workflow_head;
  const blob=raw=>({encoding:'base64',content:Buffer.from(raw).toString('base64')});
  const definitionRaw=JSON.stringify(before.definition),selectionRaw=JSON.stringify(before.selection);
  const originalAPI=f.api,calls=[];
  f.api=async route=>{
    calls.push(route);
    if(route.includes('/actions/workflows/'))return {workflow_runs:route.includes(worker?'worker-merge.yml':'merge-integration-checks.yml')?[f.run]:[]};
    if(route.endsWith('/actions/runs/17'))return f.run;
    if(route===`/repos/${repo}/git/commits/${sourceHead}`)return {tree:{sha:before.tree}};
    if(route===`/repos/${repo}/git/trees/${before.tree}?recursive=1`)return {tree:rows,truncated:false};
    if(route.includes('/contents/.github/package-inputs.json')){assert(route.endsWith(sourceHead));const row=rows.find(r=>r.path==='.github/package-inputs.json');return {...blob(definitionRaw),...row,type:'file'};}
    if(route.includes('/git/blobs/'))return blob(selectionRaw);
    if(route.includes('/attempts/2/jobs'))return {jobs:[f.job]};
    if(route.includes('/artifacts?'))return {total_count:1,artifacts:[f.artifact]};
    return originalAPI(route);
  };
  f.api.jobLogRedirect=originalAPI.jobLogRedirect;
  return {...f,s,before,rows,calls,sourceHead,workflowHead};
}

test('original discovery ignores observer trees but refuses changed build inputs and workflow',async t=>{
  const f=originalDiscovery(t),old=globalThis.fetch;t.after(()=>{globalThis.fetch=old;});
  globalThis.fetch=async()=>new Response(f.log());
  const discover=()=>findOriginalPackage({api:f.api,repo:f.repo,current:f.s.snapshot(),originalRunId:17});
  assert.equal((await discover()).origin.head,f.sourceHead);
  for(const name of ['test/incidental.test.mjs','scripts/observer.mjs','.github/workflows/unrelated.yml']){
    f.s.write(name,'new observer');f.s.commit();assert.equal((await discover()).origin.head,f.sourceHead,name);
  }
  for(const name of ['scripts/builder.mjs','package-lock.json','scripts/package-output-artifact.mjs','scripts/package-node-runtime.mjs','.github/workflows/merge-integration-checks.yml','.github/workflows/worker-merge.yml']){
    const old=fs.readFileSync(path.join(f.root,name),'utf8');f.s.write(name,'changed');f.s.commit();assert.equal(await discover(),null,name);
    f.s.write(name,old);f.s.commit();
  }
});

test('final-worker original binds candidate source separately from successful producer workflow SHA',async t=>{
  const old=globalThis.fetch;t.after(()=>{globalThis.fetch=old;});
  const f=original(t,{worker:true});f.run.conclusion='failure';
  assert.notEqual(f.origin.head,f.origin.workflow_head);
  globalThis.fetch=async()=>new Response(f.log());
  const token=await authenticateOriginalPackageOutput(f);
  assert.equal(requireOriginalPackageOutput(token).manifest.source.head,f.origin.head);
  assert.equal(requireOriginalPackageOutput(token).origin.workflow_head,f.run.head_sha);
  assert.throws(()=>requireOriginalPackageOutput(structuredClone(token)),/Privately authenticated/);
});

test('worker origin rejects substituted source, workflow, job, artifact and incomplete producer steps',async t=>{
  const old=globalThis.fetch;t.after(()=>{globalThis.fetch=old;});
  const cases=[
    f=>{f.origin.head=f.origin.workflow_head;},
    f=>{delete f.origin.workflow_head;},
    f=>{f.run.head_branch='engineering/fixture';},
    f=>{f.run.event='pull_request';},
    f=>{f.run.path='.github/workflows/merge-integration-checks.yml';},
    f=>{f.run.run_attempt=3;},
    f=>{f.job.head_sha=f.origin.head;},
    f=>{f.job.name='integration (1)';},
    f=>{f.job.conclusion='failure';},
    f=>{f.artifact.workflow_run.head_sha=f.origin.head;},
    f=>{f.workflow.sha='f'.repeat(40);},
    f=>{f.workflow.mode='120000';},
    f=>{f.receipt.original_head=f.origin.workflow_head;},
    f=>{f.job.steps.find(row=>row.name.startsWith('Inventory')).number=5;},
    f=>{f.job.steps.find(row=>row.name.startsWith('Retain')).number=4;},
    ...['Snapshot original final-worker package inputs','Build the combined application once before asset-dependent tests',
      'Inventory original final-worker package output','Read back qualified native build outputs when selected',
      'Test applicable combined-tree invariants without publishing or live imports','Retain original final-worker package output']
      .map(name=>f=>{f.job.steps.find(row=>row.name===name).conclusion='skipped';}),
  ];
  for(const mutate of cases){const f=original(t,{worker:true});mutate(f);globalThis.fetch=async()=>new Response(f.log());
    await assert.rejects(authenticateOriginalPackageOutput(f));}
});

test('bounded discovery checks both producer workflows and distinct runs sharing a workflow SHA',async t=>{
  const f=originalDiscovery(t,{worker:true}),old=globalThis.fetch;t.after(()=>{globalThis.fetch=old;});
  globalThis.fetch=async()=>new Response(f.log());
  f.run.conclusion='failure';
  const rejected={...f.run,id:18};
  const baseAPI=f.api,warnings=[],oldWarn=console.warn;let rejectedReads=0,workerReads=0;
  console.warn=message=>warnings.push(message);t.after(()=>{console.warn=oldWarn;});
  const api=async route=>{
    if(route.includes('/actions/workflows/worker-merge.yml/')){workerReads++;return {workflow_runs:[rejected,rejected,{...f.run,run_attempt:3},f.run]};}
    if(route.includes('/actions/runs/18/attempts/2/jobs')){rejectedReads++;throw Error('Authority unavailable https://fixture.invalid/private?signature=secret');}
    if(route.includes('/actions/runs/17/attempts/3/jobs'))return {jobs:[]};
    return baseAPI(route);
  };
  api.jobLogRedirect=baseAPI.jobLogRedirect;
  const found=await findOriginalPackage({api,repo:f.repo,current:f.s.snapshot()});
  assert.equal(found.origin.head,f.sourceHead);assert.equal(found.origin.workflow_head,f.workflowHead);
  assert.notEqual(found.origin.head,found.origin.workflow_head);assert.equal(found.origin.run_id,17);
  assert.equal(rejectedReads,1);assert.equal(workerReads,1);
  assert.deepEqual(warnings,['Skipped original package run 18/2: Authority unavailable [delivery address]']);
  assert(f.calls.some(route=>route.includes('merge-integration-checks.yml/runs?event=pull_request&per_page=20&page=1')));
  f.workflow.sha='f'.repeat(40);
  assert.equal(await findOriginalPackage({api,repo:f.repo,current:f.s.snapshot()}),null,'Changed actual workflow must be a cache miss');
});

test('worker invocation uses only trusted candidate and exact selected integration (0) context',()=>{
  const candidate='a'.repeat(40),injected='b'.repeat(40);
  const environment={GITHUB_EVENT_NAME:'workflow_dispatch',GITHUB_WORKFLOW:'Serialize worker PR merges',GITHUB_REF:'refs/heads/main',
    INTEGRATION_PROFILE:'full',INTEGRATION_SHARD:'0',INTEGRATION_TEST_SELECTION:'selected-data',SELECTED_PACKAGE_CANDIDATE:candidate};
  const event={pull_request:{head:{sha:injected}},inputs:{source_head:injected,original_run_id:'99',candidate:injected}};
  assert.deepEqual(packageAssemblyInvocation(event,environment),{proofMode:false,expectedHead:candidate,originalRunId:undefined});
  for(const mutation of [{GITHUB_REF:'refs/heads/engineering/fixture'},{GITHUB_WORKFLOW:'Unrelated workflow'},
    {INTEGRATION_PROFILE:'evidence'},{INTEGRATION_SHARD:'1'},{INTEGRATION_TEST_SELECTION:'complete'},
    {SELECTED_PACKAGE_CANDIDATE:undefined},{SELECTED_PACKAGE_CANDIDATE:'main'}])
    assert.throws(()=>packageAssemblyInvocation(event,{...environment,...mutation}));
  assert.throws(()=>packageAssemblyInvocation(event,{GITHUB_EVENT_NAME:'workflow_dispatch'}));
});

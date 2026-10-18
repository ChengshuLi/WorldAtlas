import nodeTest from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {authenticateOriginalPackageOutput, requireOriginalPackageOutput,
  requirePackageAssemblyExecution, issuePackageAssemblyExecution} from '../coordination/engineering/additive-native-activation-20261009/package-selected-additive.mjs';
import {requireCurrentPackageAssembly, integrationTestFiles} from '../scripts/run-integration-tests.mjs';
import {createPackageAssemblyScratch,packageAssemblyInvocation,findOriginalPackage,acceptedSelectedPackageInputs,readOriginalPackageGeography} from '../scripts/assemble-selected-package.mjs';
import {execFileSync,spawnSync} from 'node:child_process';
import {inspectPackageNodeRuntime,inspectPackageRuntime} from '../scripts/package-build.mjs';
import {loadPackageInputs} from '../scripts/package-inputs.mjs';
import {githubAPI} from '../scripts/issue-claim-contract.mjs';
import {admitPackageInputTransition,committedPackageInputs,committedPackageProducer} from '../scripts/package-output-artifact.mjs';

// Private execution must run in a plain child, but only its requested probe.
const probeName=process.argv[2];let probeRegistered=false;
const test=(name,...args)=>{
  if(probeName&&name!==probeName)return;
  probeRegistered=true;return nodeTest(name,...args);
};
const sha=raw=>createHash('sha256').update(raw).digest('hex');
function original(t,{worker=false,bodies:extraBodies={}}={}){
  const root=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'atlas-original-package-')));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const bodies={'dist/client/atlas-geography.json':'{}','dist/client/a.bin':'invariant',
    'dist/cloudflare/index.js':'worker','dist/cloudflare/wrangler.json':'{}',...extraBodies};
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
    'Inventory original final-worker package output',
    'Test applicable combined-tree invariants without publishing or live imports','Retain original final-worker package output']:
    ['Snapshot original selected package inputs','Build Cloudflare package without publishing','Inventory original selected package output',
      'Verify package controls','Read back qualified native build outputs when selected','Run selected-data consumer checks','Retain original selected package output'];
  const job={id:29,run_id:17,run_attempt:2,head_sha:workflowHead,name:worker?'integration (0)':'package',status:'completed',conclusion:'success',
    steps:names.map((name,index)=>({name,number:index+1,status:'completed',conclusion:'success'}))};
  const artifact={id:41,name:origin.artifact_name,size_in_bytes:2000,digest:'sha256:'+origin.artifact_digest,
    expired:false,workflow_run:{id:17,head_sha:workflowHead}};
  const receipt={package_output_manifest_sha256:sha(raw),package_output_manifest_bytes:raw.length,original_head:head,
    executed_workflow:{sha:worker?workflowHead:'9'.repeat(40),path:workflow.path,ref:worker?'refs/heads/main':'refs/pull/17/merge'}};
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
  const priorAPI=f.api;
  f.api=async route=>{if(route.includes('/git/commits/'))assert(route.endsWith(f.receipt.executed_workflow.sha));return priorAPI(route);};
  f.api.jobLogRedirect=priorAPI.jobLogRedirect;
  assert.notEqual(f.receipt.executed_workflow.sha,f.run.head_sha);
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
    f=>{delete f.receipt.executed_workflow;},
    f=>{f.receipt.executed_workflow.sha='main';},
    f=>{f.receipt.executed_workflow.path='.github/workflows/foreign.yml';},
    f=>{f.receipt.executed_workflow.ref='refs/heads/main';},
    f=>{f.run.path='.github/workflows/unknown.yml';},
    f=>{f.job.run_attempt=1;},
    f=>{f.job.conclusion='failure';},
    f=>{f.job.steps.find(row=>row.name==='Build Cloudflare package without publishing').conclusion='skipped';},
    f=>{f.job.steps.find(row=>row.name.startsWith('Inventory')).conclusion='skipped';},
    f=>{f.job.steps=f.job.steps.filter(row=>!row.name.startsWith('Snapshot'));},
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
  assert(!full.includes('test/canonical-compact-repack.test.mjs'));
  assert(!full.includes('test/context-input-stage.test.mjs'));
  assert(full.includes('test/prepared-parity.test.mjs'));
  const complete=[0,1,2].flatMap(shard=>integrationTestFiles('full',shard,'complete'));
  for(const name of ['compact-context-inputs','reference-context','runtime-ownership','compact-ownership'])
    assert(complete.includes(`test/${name}.test.mjs`));
  assert.throws(()=>integrationTestFiles('full',1,'selected-output'));
  assert.throws(()=>requireCurrentPackageAssembly({expected:null}),/Trusted current/);
});

test('consumer reduction binds actual current head and trusted assembly receipt digest',t=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-current-assembly-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  execFileSync('git',['init','-q',root]);fs.writeFileSync(path.join(root,'source'),'source');
  const git=(...args)=>execFileSync('git',['-C',root,...args],{encoding:'utf8'}).trim();
  git('add','.');git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture');
  const head=git('rev-parse','HEAD'),receipt={kind:'cloudflare',preflight:{inputs:{head}},assembly:{
    kind:'retained-original-output-plus-current-additive',current_execution:{source_commit:head},
    base_restoration_invoked:false,invariant_build_invoked:false,
    origin:{run_id:17}}};
  fs.mkdirSync(path.join(root,'.cache'));const file=path.join(root,'.cache/package-input-build.json');
  const write=value=>{const raw=JSON.stringify(value);fs.writeFileSync(file,raw);return sha(raw);};
  const expected=write(receipt),admission=requireCurrentPackageAssembly({directory:root,expected});
  assert.equal(admission.origin.run_id,17);
  assert.equal(Object.hasOwn(admission,'base_tests_reused'),false,'Assembly identity must not manufacture original test coverage');
  assert.doesNotMatch(fs.readFileSync(new URL('../scripts/assemble-selected-package.mjs',import.meta.url),'utf8'),/base_tests_reused/);
  fs.appendFileSync(file,' ');assert.throws(()=>requireCurrentPackageAssembly({directory:root,expected}),/digest differs/);
  receipt.assembly.current_execution.source_commit='f'.repeat(40);
  assert.throws(()=>requireCurrentPackageAssembly({directory:root,expected:write(receipt)}),/same-head/);
  receipt.assembly.current_execution.source_commit=head;const original=write(receipt);
  fs.renameSync(file,file+'.original');fs.symlinkSync(file+'.original',file);
  assert.throws(()=>requireCurrentPackageAssembly({directory:root,expected:original}),/Ordinary assembly receipt/);
});

test('current assembly admits its Node runtime without scientific requirements or GIS imports',t=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-assembly-node-runtime-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  fs.mkdirSync(path.join(root,'node_modules'));
  fs.writeFileSync(path.join(root,'package.json'),JSON.stringify({engines:{node:'>=24'}}));
  const lock=JSON.stringify({lockfileVersion:3,packages:{}});
  fs.writeFileSync(path.join(root,'package-lock.json'),lock);fs.writeFileSync(path.join(root,'node_modules/.package-lock.json'),lock);
  assert.deepEqual(inspectPackageNodeRuntime(root).errors,[]);
  assert(inspectPackageRuntime(root).errors.some(error=>error.kind==='python-runtime'),'Full build runtime still checks its separate Python requirements');
  const source=fs.readFileSync(new URL('../scripts/assemble-selected-package.mjs',import.meta.url),'utf8');
  assert.doesNotMatch(source,/inspectPackageRuntime|declaredPackagePythonRoots|installedPackageIdentity/);
  assert.match(source,/resolvePackagePythonExecutable\(python\.sha256\)/);
  assert.match(source,/Executing package extractor differs from current source/);
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


test('production assembly admits only the actual selected-data queue invocation',()=>{
  const environment={GITHUB_EVENT_NAME:'workflow_dispatch',GITHUB_WORKFLOW:'Serialize worker PR merges',GITHUB_REF:'refs/heads/main',
    INTEGRATION_PROFILE:'full',INTEGRATION_SHARD:'0',INTEGRATION_TEST_SELECTION:'selected-data',SELECTED_PACKAGE_CANDIDATE:'a'.repeat(40)};
  assert.deepEqual(packageAssemblyInvocation({},environment),{expectedHead:environment.SELECTED_PACKAGE_CANDIDATE});
  for(const mutation of [{GITHUB_EVENT_NAME:'pull_request'},{GITHUB_WORKFLOW:'Selected package equivalence proof'},
    {INTEGRATION_TEST_SELECTION:'complete'},{INTEGRATION_SHARD:'1'},{SELECTED_PACKAGE_CANDIDATE:'main'}])
    assert.throws(()=>packageAssemblyInvocation({},{...environment,...mutation}),/Trusted|Exact/);
  const source=fs.readFileSync(new URL('../scripts/assemble-selected-package.mjs',import.meta.url),'utf8');
  assert.doesNotMatch(source,/proofMode|loadSelectedPackageReadback|compareSelectedPackageReadback|proofReadback/);
  const body=source.slice(source.indexOf('export async function assembleSelectedPackage'));
  assert(body.indexOf('issuePackageAssemblyExecution(')<body.indexOf("await import('./package-current-additive.mjs')"));
  assert(body.indexOf('verifyPackageDependencies(')<body.indexOf("await import('./package-current-additive.mjs')"));
  assert(body.indexOf('Current additive consumption must be credential-free')<body.indexOf("await import('./package-current-additive.mjs')"));
  assert.doesNotMatch(source,/preparePackageSelectedAdditive|loadSelection|ImmutableReader/);
});


function sourceFixture(f,{author=true}={}){
  const write=(name,raw)=>{fs.mkdirSync(path.dirname(path.join(f.root,name)),{recursive:true});fs.writeFileSync(path.join(f.root,name),typeof raw==='string'?raw:JSON.stringify(raw));};
  const git=(...args)=>execFileSync('git',['-C',f.root,...args],{encoding:'utf8'}).trim();
  const commit=()=>{git('add','.');git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','source');};
  const definition={version:1,inputs:['.github/package-inputs.json','data/ownership-selection.json','scripts/builder.mjs','package-lock.json','scripts/package-output-artifact.mjs'],
    optional_inputs:[],verification_paths:[],generated_outputs:['dist/']};
  const selection={version:1,additive_release:{path:'coordination/engineering/original/release.json'}};
  write('.github/package-inputs.json',definition);write('data/ownership-selection.json',selection);
  if(author)write('.github/workflows/merge-integration-checks.yml','actual build invocation');
  write('.github/workflows/worker-merge.yml','actual final-worker build invocation');
  write('scripts/assemble-selected-package.mjs','// Synthetic current entry point for private admission controls.');
  write('scripts/builder.mjs','actual consumed builder');write('package-lock.json','{}');
  write('scripts/package-output-artifact.mjs','capture writer');
  git('init','-q');commit();
  const snapshot=()=>({head:git('rev-parse','HEAD'),tree:git('rev-parse','HEAD^{tree}'),
    definition:JSON.parse(fs.readFileSync(path.join(f.root,'.github/package-inputs.json'))),
    selection:JSON.parse(fs.readFileSync(path.join(f.root,'data/ownership-selection.json'))),
    files:committedPackageInputs(f.root,JSON.parse(fs.readFileSync(path.join(f.root,'.github/package-inputs.json')))),producer:committedPackageProducer(f.root)});
  return {write,git,commit,snapshot};
}


test('actual assembly discovers identical reference candidates only after source and head checks',async t=>{
  const f=original(t),s=sourceFixture(f,{author:false});
  // Copy the literal executing entry and its relative imports into a small real
  // repository, so currentSource authenticates actual fixture Git metadata.
  const sourceRoot=fileURLToPath(new URL('../',import.meta.url)),copied=new Set();
  const copy=name=>{
    if(copied.has(name))return;copied.add(name);
    const raw=fs.readFileSync(path.join(sourceRoot,name));s.write(name,raw.toString('utf8'));
    for(const match of raw.toString('utf8').matchAll(/(?:from\s*|import\s*(?:\(\s*)?)['"]([^'"]+)['"]/g))
      if(match[1].startsWith('.'))copy(path.posix.normalize(path.posix.join(path.posix.dirname(name),match[1])));
  };
  copy('scripts/assemble-selected-package.mjs');copy('package.json');
  const selection=s.snapshot().selection;
  s.write('data/ownership-selection.json',{...selection,reference_projection:{path:'retained-reference.json'}});s.commit();
  fs.symlinkSync(fs.realpathSync(path.join(sourceRoot,'node_modules')),path.join(f.root,'node_modules'),'dir');
  fs.appendFileSync(path.join(f.root,'.git/info/exclude'),'\nnode_modules/\n');
  const {assembleSelectedPackage}=await import(pathToFileURL(path.join(f.root,'scripts/assemble-selected-package.mjs')));
  const calls=[],api=async route=>{calls.push(route);return {workflow_runs:[]};};
  const args=()=>({api,repo:f.repo,expectedHead:s.git('rev-parse','HEAD')});
  await assert.rejects(assembleSelectedPackage({...args(),expectedHead:'f'.repeat(40)}),/Actual selected head changed/);
  const selected=path.join(f.root,'data/ownership-selection.json'),raw=fs.readFileSync(selected);
  fs.appendFileSync(selected,' ');
  await assert.rejects(assembleSelectedPackage(args()),/Current selected metadata differs from Git/);
  fs.writeFileSync(selected,raw);
  assert.deepEqual(calls,[],'Changed source/head must fail before discovering or downloading originals');
  assert.deepEqual(await assembleSelectedPackage(args()),{assembled:false,reason:'No applicable retained original output in bounded recent-result search'});
  assert.equal(calls.length,1);calls.length=0;
  assert.equal(fs.existsSync(path.join(f.root,'.cache')),false,'No original-output scratch was created');
  // Exercise the real CLI fallback with a local empty-discovery transport,
  // without sending a token or making a remote call.
  const event=path.join(f.root,'event.json');fs.writeFileSync(event,'{}');
  const entry=path.join(f.root,'scripts/assemble-selected-package.mjs');
  const probe=path.join(f.root,'cli-probe.mjs');
  fs.writeFileSync(probe,`globalThis.fetch=async()=>Response.json({workflow_runs:[]});process.argv=[process.execPath,${JSON.stringify(entry)}];await import(${JSON.stringify(pathToFileURL(entry).href)});`);
  const child=spawnSync(process.execPath,[probe],{encoding:'utf8',env:{...process.env,NODE_OPTIONS:'',NODE_PATH:'',
    GH_TOKEN:'local-fixture-only',GITHUB_TOKEN:'',GITHUB_REPOSITORY:f.repo,GITHUB_EVENT_PATH:event,
    GITHUB_EVENT_NAME:'workflow_dispatch',GITHUB_WORKFLOW:'Serialize worker PR merges',GITHUB_REF:'refs/heads/main',
    INTEGRATION_PROFILE:'full',INTEGRATION_SHARD:'0',INTEGRATION_TEST_SELECTION:'selected-data',
    SELECTED_PACKAGE_CANDIDATE:args().expectedHead,SELECTED_PACKAGE_TRUSTED_BASE:undefined,GITHUB_OUTPUT:undefined}});
  assert.equal(child.status,0,child.stderr);
  assert.deepEqual(JSON.parse(child.stdout),{assembled:false,reason:'No applicable retained original output in bounded recent-result search'});
  for(const file of [event,probe])fs.unlinkSync(file);
  s.write('data/ownership-selection.json',selection);s.commit();
  assert.deepEqual(await assembleSelectedPackage(args()),{assembled:false,reason:'No applicable retained original output in bounded recent-result search'});
  assert.equal(calls.length,1);assert.match(calls[0],/actions\/workflows\/worker-merge.yml\/runs/);
});

for(const queueOnly of [false,true])test('private assembly admission uses actual '+(queueOnly?'queue-only':'historical')+' producer and rejects drift',async t=>{
  // Exercise the actual plain-process guard instead of altering execArgv in the test.
  if(process.execArgv.length||process.env.NODE_OPTIONS?.trim()||process.env.NODE_PATH?.trim()){
    execFileSync(process.execPath,[new URL(import.meta.url).pathname,t.name],{env:{...process.env,NODE_OPTIONS:'',NODE_PATH:'',NODE_TEST_CONTEXT:undefined},encoding:'utf8'});return;
  }
  const f=original(t,{worker:queueOnly}),s=sourceFixture(f,{author:!queueOnly}),manifest=JSON.parse(f.manifestRaw),oldFetch=globalThis.fetch,oldEntry=process.argv[1];
  const stage=fs.mkdtempSync(path.join(f.root,'stage-'));
  t.after(()=>{globalThis.fetch=oldFetch;process.argv[1]=oldEntry;});
  manifest.source=s.snapshot();
  f.origin.head=f.origin.workflow_head=f.run.head_sha=f.job.head_sha=f.artifact.workflow_run.head_sha=f.receipt.original_head=manifest.source.head;
  if(queueOnly)f.receipt.executed_workflow.sha=manifest.source.head;
  f.workflow.sha=manifest.source.producer.workflows.find(row=>row.path===f.workflow.path).oid;
  const authenticate=async source=>{
    f.manifestRaw=Buffer.from(JSON.stringify({...manifest,source})+'\n');
    f.receipt.package_output_manifest_sha256=sha(f.manifestRaw);f.receipt.package_output_manifest_bytes=f.manifestRaw.length;
    return authenticateOriginalPackageOutput(f);
  };
  globalThis.fetch=async()=>new Response(f.log());
  const token=await authenticate(manifest.source);
  process.argv[1]=path.join(f.root,'scripts/assemble-selected-package.mjs');
  const issue=original=>issuePackageAssemblyExecution({original,source:f.root,stage,executingRoot:f.root});
  assert.doesNotThrow(()=>requirePackageAssemblyExecution(issue(token)));
  // Literal deferred project imports are authenticated before evaluation, even
  // when their module bodies deliberately cannot be executed during admission.
  s.write('scripts/assemble-selected-package.mjs', "export async function current(){return import('./package-current-additive.mjs');}");
  s.write('scripts/package-current-additive.mjs', "import '../src/effective-footprint.js';throw Error('must not evaluate current consumer');");
  s.write('src/effective-footprint.js', "throw Error('must not evaluate current helper');");s.commit();
  const deferred=issue(token);assert(deferred.files.some(pin=>pin.path==='scripts/package-current-additive.mjs'));
  assert(deferred.files.some(pin=>pin.path==='src/effective-footprint.js'));
  for(const name of ['scripts/package-current-additive.mjs','src/effective-footprint.js']){
    const originalBody=fs.readFileSync(path.join(f.root,name));fs.appendFileSync(path.join(f.root,name),'// substituted');
    assert.throws(()=>issue(token),/Executing assembly code differs/);
    assert.throws(()=>requirePackageAssemblyExecution(deferred),/Executing assembly code differs/);
    fs.writeFileSync(path.join(f.root,name),originalBody);
  }
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
    assert.throws(()=>issue(token),/not unchanged on trusted base|New selected declaration is absent/);
    s.write('.github/package-inputs.json',declaration);
    if(name.endsWith('.mjs'))fs.unlinkSync(path.join(f.root,name));s.commit();
  }
  for(const name of ['scripts/builder.mjs','package-lock.json','scripts/package-output-artifact.mjs',...(!queueOnly?['.github/workflows/merge-integration-checks.yml']:[]),'.github/workflows/worker-merge.yml']){
    const old=fs.readFileSync(path.join(f.root,name),'utf8');s.write(name,'changed');s.commit();
    assert.throws(()=>issue(token),/input changed|producer workflow required/,name);
    s.write(name,old);s.commit();
  }
  const legacy={...manifest.source};delete legacy.producer;legacy.programme=[];
  await assert.rejects(authenticate(legacy),/Actual executed producer workflow/);
});

function originalDiscovery(t,{worker=false,queueOnly=false}={}){
  const f=original(t,{worker}),s=sourceFixture(f,{author:!queueOnly}),before=s.snapshot(),repo=f.repo;
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

for(const worker of [false,true])test('real GitHub adapter discovers and authenticates '+(worker?'worker':'historical PR')+' original package output',async t=>{
  const f=originalDiscovery(t,{worker}),oldFetch=globalThis.fetch,oldWarn=console.warn;
  t.after(()=>{globalThis.fetch=oldFetch;console.warn=oldWarn;});console.warn=()=>{};
  const manifest=JSON.parse(f.manifestRaw);manifest.source=f.before;
  f.manifestRaw=Buffer.from(JSON.stringify(manifest)+'\n');
  f.receipt.package_output_manifest_sha256=sha(f.manifestRaw);f.receipt.package_output_manifest_bytes=f.manifestRaw.length;
  const logRoute=`/repos/${f.repo}/actions/jobs/${f.origin.job_id}/logs`,calls=[];
  let logStatus=302,logURL='https://fixture.blob.core.windows.net/job-log',downloads=0,cancelled=0;
  globalThis.fetch=async(url,options)=>{
    assert.equal(String(url),'https://fixture.blob.core.windows.net/job-log');
    assert.equal(options.headers,undefined);assert.equal(options.redirect,'error');downloads++;
    return new Response(f.log());
  };
  const api=githubAPI('fixture-token',{conditionalReads:false,fetchImpl:async(url,options)=>{
    const parsed=new URL(url);assert.equal(parsed.origin,'https://api.github.com');
    const route=parsed.pathname+parsed.search;calls.push(route);
    assert.equal(options.method,'GET');assert.equal(options.headers.Authorization,'Bearer fixture-token');
    assert.equal(options.redirect,route===logRoute?'manual':'error');
    if(route===logRoute){
      if(logStatus!==302)return Response.json({message:'Original log unavailable'},{status:logStatus});
      return new Response(new ReadableStream({cancel(){cancelled++;}}),{status:302,headers:{location:logURL}});
    }
    return Response.json(await f.api(route));
  }});
  const found=await findOriginalPackage({api,repo:f.repo,current:f.before,originalRunId:17});
  assert.equal(found?.origin.head,f.sourceHead,'The real CLI adapter must admit the original instead of forcing a rebuild');
  const admit=()=>authenticateOriginalPackageOutput({...f,api});
  const token=await admit();assert.equal(requireOriginalPackageOutput(token).manifest.source.head,f.sourceHead);
  assert.throws(()=>requireOriginalPackageOutput(structuredClone(token)),/Privately authenticated/);
  assert.equal(downloads,2);assert.equal(cancelled,2);assert.equal(calls.filter(route=>route===logRoute).length,2);
  const before=calls.length;
  for(const route of [logRoute+'?foreign=1',logRoute.replace('/29/','/0/'),logRoute.replace('/logs','/artifacts'),
    'https://api.github.com'+logRoute])assert.throws(()=>api.jobLogRedirect(route),/Invalid job log redirect route/);
  assert.equal(calls.length,before,'Invalid redirects must fail before sending authenticated requests');
  const receiptHash=f.receipt.package_output_manifest_sha256;
  f.receipt.package_output_manifest_sha256='f'.repeat(64);
  await assert.rejects(admit(),/Original package inventory differs/);f.receipt.package_output_manifest_sha256=receiptHash;
  const originalLog=f.log;f.log=()=>'';await assert.rejects(admit(),/Missing or ambiguous/);f.log=originalLog;
  logURL='https://foreign.invalid/job-log';const priorDownloads=downloads;
  await assert.rejects(admit(),/Unsupported original job-log transport/);assert.equal(downloads,priorDownloads);
  logStatus=404;const priorRequests=calls.length;
  await assert.rejects(admit(),/HTTP 404/);assert.equal(calls.length-priorRequests,4,'An ordinary denial must not be retried');
  assert.equal(downloads,priorDownloads);
});

test('original discovery ignores observer trees but refuses changed build inputs and workflow',async t=>{
  const f=originalDiscovery(t),old=globalThis.fetch;t.after(()=>{globalThis.fetch=old;});
  globalThis.fetch=async()=>new Response(f.log());
  const discover=()=>findOriginalPackage({api:f.api,repo:f.repo,current:f.s.snapshot(),originalRunId:17});
  assert.equal((await discover()).origin.head,f.sourceHead);
  for(const name of ['test/incidental.test.mjs','scripts/observer.mjs','.github/workflows/unrelated.yml']){
    f.s.write(name,'new observer');f.s.commit();assert.equal((await discover()).origin.head,f.sourceHead,name);
  }
  for(const name of ['scripts/builder.mjs','package-lock.json','scripts/package-output-artifact.mjs','.github/workflows/merge-integration-checks.yml','.github/workflows/worker-merge.yml']){
    const old=fs.readFileSync(path.join(f.root,name),'utf8');f.s.write(name,'changed');f.s.commit();assert.equal(await discover(),null,name);
    f.s.write(name,old);f.s.commit();
  }
});

test('discovery reuses only its authenticated identical base tree and retains exact commit and input checks',async t=>{
  const f=originalDiscovery(t),oldFetch=globalThis.fetch,oldWarn=console.warn;
  t.after(()=>{globalThis.fetch=oldFetch;console.warn=oldWarn;});
  globalThis.fetch=async()=>new Response(f.log());console.warn=()=>{};
  f.receipt.executed_workflow.sha=f.sourceHead;
  f.s.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','--allow-empty','-qm','same tree, distinct base');
  let trustedBase=f.s.git('rev-parse','HEAD'),truncate=false,wrongCommit=false,missingCommit=false,wrongOriginal=false;
  const calls=[],baseAPI=f.api;
  const api=async route=>{
    calls.push(route);
    const commit=/\/git\/commits\/([a-f0-9]{40})$/.exec(route);
    if(commit)return {sha:missingCommit&&commit[1]===trustedBase?undefined:(wrongCommit&&commit[1]===trustedBase||wrongOriginal&&commit[1]===f.sourceHead)?'0'.repeat(40):commit[1],tree:{sha:f.s.git('rev-parse',commit[1]+'^{tree}')}};
    const tree=/\/git\/trees\/([a-f0-9]{40})\?recursive=1$/.exec(route);
    if(tree){
      const rows=f.s.git('ls-tree','-rlz',tree[1]).split('\0').filter(Boolean).map(line=>{
        const [metadata,path]=line.split('\t'),[mode,type,sha,size]=metadata.trim().split(/\s+/);return {path,mode,type,sha,size:Number(size)};
      });return {tree:rows,truncated:truncate};
    }
    return baseAPI(route);
  };
  api.jobLogRedirect=baseAPI.jobLogRedirect;
  const discover=()=>findOriginalPackage({api,repo:f.repo,current:f.s.snapshot(),originalRunId:17,trustedBase});
  const recursive=()=>calls.filter(route=>route.includes('/git/trees/')&&route.endsWith('?recursive=1'));
  assert.notEqual(trustedBase,f.sourceHead);
  const found=await discover();
  assert.equal(found.origin.head,f.sourceHead);assert.equal(found.source.head,f.sourceHead);
  assert.equal(found.accepted_selected_inputs.commit,trustedBase);
  assert.equal(calls.filter(route=>route.endsWith('/git/commits/'+trustedBase)).length,1);
  assert.equal(calls.filter(route=>route.endsWith('/git/commits/'+f.sourceHead)).length,1);
  assert.deepEqual(recursive(),[`/repos/${f.repo}/git/trees/${f.before.tree}?recursive=1`]);
  const builder=found.accepted_selected_inputs.files.find(row=>row.path==='scripts/builder.mjs');
  assert.equal(builder.oid,f.rows.find(row=>row.path===builder.path).sha);
  calls.length=0;truncate=true;assert.equal(await discover(),null);truncate=false;
  wrongCommit=true;await assert.rejects(discover(),/Trusted selected base commit differs/);wrongCommit=false;
  missingCommit=true;await assert.rejects(discover(),/Trusted selected base commit differs/);missingCommit=false;
  wrongOriginal=true;assert.equal(await discover(),null);wrongOriginal=false;
  f.s.write('README.md','A different accepted tree with unchanged package inputs');f.s.commit();
  trustedBase=f.s.git('rev-parse','HEAD');calls.length=0;
  assert.equal((await discover()).origin.head,f.sourceHead);
  assert.deepEqual(recursive(),[`/repos/${f.repo}/git/trees/${f.before.tree}?recursive=1`,
    `/repos/${f.repo}/git/trees/${f.s.git('rev-parse',trustedBase+'^{tree}')}?recursive=1`]);
  for(const name of ['scripts/builder.mjs','.github/workflows/worker-merge.yml']){
    const original=fs.readFileSync(path.join(f.root,name),'utf8');f.s.write(name,'changed');f.s.commit();
    assert.equal(await discover(),null,'Tree reuse must not hide changed '+name);
    f.s.write(name,original);f.s.commit();
  }
});

test('failed-job retry discovers the successful original package attempt without relabeling its producer',async t=>{
  const f=originalDiscovery(t,{worker:true}),old=globalThis.fetch;t.after(()=>{globalThis.fetch=old;});
  globalThis.fetch=async()=>new Response(f.log());
  const originRun=structuredClone(f.run),baseAPI=f.api;
  originRun.conclusion='failure';f.run.run_attempt=3;f.run.conclusion='success';
  const api=async route=>{
    assert(!route.includes('/attempts/3/jobs'),'Do not use relabeled carried jobs');
    if(route.endsWith('/attempts/2'))return structuredClone(originRun);
    return baseAPI(route);
  };
  api.jobLogRedirect=baseAPI.jobLogRedirect;
  const found=await findOriginalPackage({api,repo:f.repo,current:f.s.snapshot(),originalRunId:17});
  assert.equal(found.origin.run_attempt,2);assert.equal(found.origin.job_id,29);
  assert.equal(found.origin.artifact_name,'cloudflare-package-output-17-2');
  f.job.conclusion='failure';
  assert.equal(await findOriginalPackage({api,repo:f.repo,current:f.s.snapshot(),originalRunId:17}),null);
});

test('unproved newer package cannot replace the authenticated older successful output',async t=>{
  const f=originalDiscovery(t,{worker:true}),old=globalThis.fetch,oldWarn=console.warn;
  t.after(()=>{globalThis.fetch=old;console.warn=oldWarn;});
  globalThis.fetch=async()=>new Response(f.log());
  const originRun=structuredClone(f.run),baseAPI=f.api,warnings=[];
  originRun.conclusion='failure';f.run.run_attempt=3;console.warn=message=>warnings.push(message);
  const partial={...f.artifact,id:42,name:'cloudflare-package-output-17-3'};
  const newJob={...structuredClone(f.job),id:30,run_attempt:3};
  const api=async route=>{
    if(route.includes('/artifacts?'))return {total_count:2,artifacts:[partial,f.artifact]};
    if(route.includes('/attempts/3/jobs'))return {jobs:[newJob]};
    if(route.endsWith('/attempts/3'))return structuredClone(f.run);
    if(route.endsWith('/attempts/2'))return structuredClone(originRun);
    if(route.endsWith('/jobs/30'))return newJob;
    return baseAPI(route);
  };
  api.jobLogRedirect=baseAPI.jobLogRedirect;
  const found=await findOriginalPackage({api,repo:f.repo,current:f.s.snapshot(),originalRunId:17});
  assert.equal(found.origin.run_attempt,2);assert.equal(found.origin.artifact_id,41);
  assert(warnings.some(message=>message.includes('producer 17/3')),'The newer artifact must actually fail original receipt authentication');
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

test('actual current queue step roster admits an original donor without historical readback',async t=>{
  const f=original(t,{worker:true}),old=globalThis.fetch;t.after(()=>{globalThis.fetch=old;});
  const workflow=fs.readFileSync(new URL('../.github/workflows/worker-merge.yml',import.meta.url),'utf8');
  const integration=workflow.split('\n  integration:\n')[1].split('\n  merge:\n')[0];
  const names=[...integration.matchAll(/^      - name: (.+)$/gm)].map(match=>match[1]);
  for(const name of f.job.steps.map(row=>row.name))assert(names.includes(name),'Actual current workflow must contain '+name);
  assert(!names.includes('Read back qualified native build outputs when selected'));
  f.job.steps=names.map((name,index)=>({name,number:index+1,status:'completed',conclusion:'success'}));
  globalThis.fetch=async()=>new Response(f.log());
  const token=await authenticateOriginalPackageOutput(f);assert.equal(requireOriginalPackageOutput(token).manifest.source.head,f.origin.head);
});

test('worker origin rejects substituted source, workflow, job, artifact and incomplete producer steps',async t=>{
  const old=globalThis.fetch;t.after(()=>{globalThis.fetch=old;});
  const cases=[
    f=>{f.origin.head=f.origin.workflow_head;},
    f=>{delete f.origin.workflow_head;},
    f=>{f.receipt.executed_workflow.sha=f.origin.head;},
    f=>{f.run.head_branch='engineering/fixture';},
    f=>{f.run.event='pull_request';},
    f=>{f.run.path='.github/workflows/merge-integration-checks.yml';},
    f=>{f.run.run_attempt=3;},
    f=>{f.job.head_sha=f.origin.head;},
    f=>{f.job.name='integration (1)';},
    f=>{f.job.conclusion='failure';},
    f=>{f.job.steps.find(row=>row.name.startsWith('Inventory')).conclusion='skipped';},
    f=>{f.artifact.workflow_run.head_sha=f.origin.head;},
    f=>{f.workflow.sha='f'.repeat(40);},
    f=>{f.workflow.mode='120000';},
    f=>{f.receipt.original_head=f.origin.workflow_head;},
    f=>{f.job.steps.find(row=>row.name.startsWith('Inventory')).number=5;},
    f=>{f.job.steps.find(row=>row.name.startsWith('Retain')).number=2;},
    ...['Snapshot original final-worker package inputs','Build the combined application once before asset-dependent tests',
      'Inventory original final-worker package output','Test applicable combined-tree invariants without publishing or live imports','Retain original final-worker package output']
      .map(name=>f=>{f.job.steps.find(row=>row.name===name).conclusion='skipped';}),
  ];
  for(const mutate of cases){const f=original(t,{worker:true});mutate(f);globalThis.fetch=async()=>new Response(f.log());
    await assert.rejects(authenticateOriginalPackageOutput(f));}
});

test('queue-only discovery never queries the deleted author workflow and admits its genuine original',async t=>{
  const f=originalDiscovery(t,{worker:true,queueOnly:true}),old=globalThis.fetch;t.after(()=>{globalThis.fetch=old;});
  globalThis.fetch=async()=>new Response(f.log());
  const base=f.api,calls=[];
  const api=async route=>{calls.push(route);if(route.includes('/actions/workflows/merge-integration-checks.yml/'))throw Error('GitHub GET failed (HTTP 404)');return base(route);};
  api.jobLogRedirect=base.jobLogRedirect;
  const result=await findOriginalPackage({api,repo:f.repo,current:f.s.snapshot()});
  assert.equal(result.origin.run_id,17);assert.equal(result.origin.head,f.sourceHead);
  assert.equal(calls.filter(route=>route.includes('/actions/workflows/')).length,1);
  assert(calls.some(route=>route.includes('/actions/workflows/worker-merge.yml/')));
  assert(!calls.some(route=>route.includes('/actions/workflows/merge-integration-checks.yml/')));
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
    if(route.includes('/actions/runs/18/artifacts?'))return {total_count:1,artifacts:[{...f.artifact,name:'cloudflare-package-output-18-2'}]};
    if(route.includes('/actions/runs/18/attempts/2/jobs')){rejectedReads++;throw Error('Authority unavailable https://fixture.invalid/private?signature=secret');}
    if(route.includes('/actions/runs/17/attempts/3/jobs'))return {jobs:[]};
    return baseAPI(route);
  };
  api.jobLogRedirect=baseAPI.jobLogRedirect;
  const found=await findOriginalPackage({api,repo:f.repo,current:f.s.snapshot()});
  assert.equal(found.origin.head,f.sourceHead);assert.equal(found.origin.workflow_head,f.workflowHead);
  assert.notEqual(found.origin.head,found.origin.workflow_head);assert.equal(found.origin.run_id,17);
  assert.equal(rejectedReads,1);assert.equal(workerReads,1);
  assert.deepEqual(warnings,['Skipped original package producer 18/2: Authority unavailable [delivery address]']);
  assert(f.calls.some(route=>route.includes('merge-integration-checks.yml/runs?event=pull_request&per_page=20&page=1')));
  f.workflow.sha='f'.repeat(40);
  assert.equal(await findOriginalPackage({api,repo:f.repo,current:f.s.snapshot()}),null,'Changed actual workflow must be a cache miss');
});

test('worker invocation uses only trusted candidate and exact selected integration (0) context',()=>{
  const candidate='a'.repeat(40),injected='b'.repeat(40);
  const environment={GITHUB_EVENT_NAME:'workflow_dispatch',GITHUB_WORKFLOW:'Serialize worker PR merges',GITHUB_REF:'refs/heads/main',
    INTEGRATION_PROFILE:'full',INTEGRATION_SHARD:'0',INTEGRATION_TEST_SELECTION:'selected-data',SELECTED_PACKAGE_CANDIDATE:candidate};
  const event={pull_request:{head:{sha:injected}},inputs:{source_head:injected,original_run_id:'99',candidate:injected}};
  assert.deepEqual(packageAssemblyInvocation(event,environment),{expectedHead:candidate});
  for(const mutation of [{GITHUB_REF:'refs/heads/engineering/fixture'},{GITHUB_WORKFLOW:'Unrelated workflow'},
    {INTEGRATION_PROFILE:'evidence'},{INTEGRATION_SHARD:'1'},{INTEGRATION_TEST_SELECTION:'complete'},
    {SELECTED_PACKAGE_CANDIDATE:undefined},{SELECTED_PACKAGE_CANDIDATE:'main'}])
    assert.throws(()=>packageAssemblyInvocation(event,{...environment,...mutation}));
  assert.throws(()=>packageAssemblyInvocation(event,{GITHUB_EVENT_NAME:'workflow_dispatch'}));
});

test('PR discovery checks actual merge-ref workflow bytes even when source and run heads agree',async t=>{
  const f=originalDiscovery(t),old=globalThis.fetch;t.after(()=>{globalThis.fetch=old;});
  globalThis.fetch=async()=>new Response(f.log());
  const baseAPI=f.api;
  const api=async route=>{
    const commit=/\/git\/commits\/([a-f0-9]{40})$/.exec(route);
    if(commit)return {tree:{sha:f.s.git('rev-parse',commit[1]+'^{tree}')}};
    const tree=/\/git\/trees\/([a-f0-9]{40})(\?recursive=1)?$/.exec(route);
    if(tree){
      const rows=f.s.git('ls-tree',...(tree[2]?['-r']:[]),'-lz',tree[1]).split('\0').filter(Boolean).map(line=>{
        const [meta,name]=line.split('\t'),[mode,type,sha,size]=meta.trim().split(/\s+/);return {path:name,mode,type,sha,size:Number(size)};
      });
      return {tree:rows,truncated:false};
    }
    return baseAPI(route);
  };
  api.jobLogRedirect=baseAPI.jobLogRedirect;
  f.s.write('README.md','A distinct merge-ref commit with identical workflow bytes');f.s.commit();
  f.receipt.executed_workflow.sha=f.s.git('rev-parse','HEAD');
  assert.notEqual(f.receipt.executed_workflow.sha,f.origin.workflow_head);
  const discover=()=>findOriginalPackage({api,repo:f.repo,current:f.before,originalRunId:17});
  assert.equal((await discover()).origin.head,f.sourceHead,'Commit identity alone must not invalidate identical workflow bytes');
  f.s.write(f.workflow.path,'Changed only in the actual merge-ref workflow');f.s.commit();
  f.receipt.executed_workflow.sha=f.s.git('rev-parse','HEAD');
  assert.equal(await discover(),null,'Source/run workflow bytes cannot stand in for actual executed workflow');
  delete f.receipt.executed_workflow;
  assert.equal(await discover(),null,'No inferred workflow provenance for older captures');
});


test('trusted invocation carries the existing exact selected base without receipt-derived authority',()=>{
  const base='b'.repeat(40),head='a'.repeat(40);
  const env={GITHUB_EVENT_NAME:'workflow_dispatch',GITHUB_WORKFLOW:'Serialize worker PR merges',GITHUB_REF:'refs/heads/main',
    INTEGRATION_PROFILE:'full',INTEGRATION_SHARD:'0',INTEGRATION_TEST_SELECTION:'selected-data',SELECTED_PACKAGE_CANDIDATE:head,SELECTED_PACKAGE_TRUSTED_BASE:base};
  assert.equal(packageAssemblyInvocation({pull_request:{head:{sha:head}}},env).trustedBase,base);
  assert.throws(()=>packageAssemblyInvocation({pull_request:{head:{sha:head}}},{...env,SELECTED_PACKAGE_TRUSTED_BASE:'main'}),/Exact trusted selected base/);
});

test('discovery and actual private execution admit data leaves and a later accepted typed code candidate',async t=>{
  if(process.execArgv.length||process.env.NODE_OPTIONS?.trim()||process.env.NODE_PATH?.trim()){
    execFileSync(process.execPath,[new URL(import.meta.url).pathname,t.name],{env:{...process.env,NODE_OPTIONS:'',NODE_PATH:'',NODE_TEST_CONTEXT:undefined},encoding:'utf8'});return;
  }
  const f=originalDiscovery(t),oldFetch=globalThis.fetch,oldEntry=process.argv[1];
  t.after(()=>{globalThis.fetch=oldFetch;process.argv[1]=oldEntry;});globalThis.fetch=async()=>new Response(f.log());
  const manifest=JSON.parse(f.manifestRaw);manifest.source=f.before;
  f.manifestRaw=Buffer.from(JSON.stringify(manifest)+'\n');f.receipt.package_output_manifest_sha256=sha(f.manifestRaw);
  f.receipt.package_output_manifest_bytes=f.manifestRaw.length;
  const token=await authenticateOriginalPackageOutput(f);
  const code='scripts/qualify-source-cohort.py';f.s.write(code,'accepted original SOURCE implementation');f.s.commit();
  const acceptedHead=f.s.git('rev-parse','HEAD');assert.notEqual(acceptedHead,f.sourceHead);
  const baseAPI=f.api,api=async route=>{
    if(route===`/repos/${f.repo}/git/commits/${acceptedHead}`)return {sha:acceptedHead,tree:{sha:f.s.git('rev-parse',acceptedHead+'^{tree}')}};
    if(route===`/repos/${f.repo}/git/trees/${f.s.git('rev-parse',acceptedHead+'^{tree}')}?recursive=1`){
      const tree=f.s.git('ls-tree','-rlz',acceptedHead).split('\0').filter(Boolean).map(line=>{
        const [meta,path]=line.split('\t'),[mode,type,sha,size]=meta.trim().split(/\s+/);return {path,mode,type,sha,size:Number(size)};
      });return {tree,truncated:false};
    }
    return baseAPI(route);
  };api.jobLogRedirect=baseAPI.jobLogRedirect;
  const declaration=JSON.parse(fs.readFileSync(path.join(f.root,'.github/package-inputs.json')));
  for(let i=0;i<2;i++){const name=`coordination/engineering/retained-source/operand-${i}.json`;declaration.inputs.push(name);f.s.write(name,{role:i});}
  declaration.inputs.push(code);f.s.write('.github/package-inputs.json',declaration);f.s.commit();
  const current=f.s.snapshot();current.accepted_selected_inputs=await acceptedSelectedPackageInputs({api,repo:f.repo,base:acceptedHead,current});
  assert.equal((await findOriginalPackage({api,repo:f.repo,current,originalRunId:17})).origin.head,f.sourceHead);
  const stage=fs.mkdtempSync(path.join(f.root,'stage-'));process.argv[1]=path.join(f.root,'scripts/assemble-selected-package.mjs');
  const issue=()=>issuePackageAssemblyExecution({original:token,source:f.root,stage,executingRoot:f.root,
    acceptedInputs:current.accepted_selected_inputs});
  assert.doesNotThrow(()=>requirePackageAssemblyExecution(issue()),'Preliminary execution admission grants no publication capability');
  const invariant=fs.readFileSync(path.join(f.root,'dist/client/a.bin'),'utf8');
  for(const value of ['new or changed executable code','new code with refreshed arbitrary pin metadata']){
    f.s.write(code,value);f.s.commit();assert.throws(issue,/not unchanged on trusted base/);
    assert.equal(await findOriginalPackage({api,repo:f.repo,current:{...f.s.snapshot(),accepted_selected_inputs:current.accepted_selected_inputs},originalRunId:17}),null);
    assert.equal(fs.readFileSync(path.join(f.root,'dist/client/a.bin'),'utf8'),invariant);
    assert.equal(fs.existsSync(path.join(stage,'dist')),false,'Rejected candidate never publishes output');
  }
});

// A small real current-product fixture. It exercises the same consumer after
// private original-output admission, without any scientific custody inputs.
async function currentProductFixture(t,{changeCatalog=()=>{},changeGeometry=()=>{},reference=false,sourceRevision=false,priorGzip=false}={}) {
  const {gzipSync}=await import('node:zlib');
  const {footprintHash}=await import('../scripts/check-prepared.mjs');
  const {footprintValueSha256,additiveReleaseFootprintDigest}=await import('../src/effective-footprint.js');
  const referenceRevision='7'.repeat(64);
  const properties=reference?{id:'owner',name:'Owner',parent_id:'parent',metadata:{}}:{parent_id:'parent'};
  if(reference)properties.metadata.reference_revision=referenceRevision;
  const feature={id:'owner',pixelIndex:1,properties,
    geometry:{type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}};
  const addition={type:'Polygon',coordinates:[[[1,0],[2,0],[2,1],[1,1],[1,0]]]};
  const base={id:'geography:base',footprints_sha256:footprintHash([feature]),hierarchy_sha256:'a'.repeat(64)};
  const native=reference?{...base,id:'geography:native',hierarchy_sha256:'9'.repeat(64)}:base;
  const rosterRaw=Buffer.from(JSON.stringify([{id:feature.id,index:1,province_id:reference?'old-parent':'parent',bounds:[0,0,1,1]}])),bounds=gzipSync(rosterRaw);
  const manifestRaw=Buffer.from(JSON.stringify({size:262166,geographic_release:native.id,footprints_sha256:native.footprints_sha256,
    hierarchy_sha256:native.hierarchy_sha256,original_assets:{bounds:{sha256:sha(bounds)}}}));
  const ledger={version:1,kind:'native-additive-repair-ledger-v1',rule_sha256:'b'.repeat(64),base_reference:base,
    parent_inventory:{components:1,report_sha256:'c'.repeat(64),roster_sha256:'d'.repeat(64)},scope_ids:['gap'],assigned_cells:2,
    rows:[{component_id:'gap',disposition:'assigned',target_id:'owner',pixelIndex:1,base_geometry:feature.geometry,
      base_geometry_sha256:footprintValueSha256(feature.geometry),geometry:addition,geometry_sha256:footprintValueSha256(addition),
      source_receipt_sha256:'e'.repeat(64),native_cells:2}]};
  const ledgerRaw=Buffer.from(JSON.stringify(ledger));
  const effectiveFeature={...feature,additiveFootprint:{version:1,kind:'retained-base-plus-additions',
    baseline_release_sha256:base.footprints_sha256,base_geometry_sha256:footprintValueSha256(feature.geometry),
    ledger_sha256:sha(ledgerRaw),rule_sha256:ledger.rule_sha256,additions:[{component_id:'gap',geometry:addition,
      geometry_sha256:footprintValueSha256(addition),source_receipt_sha256:'e'.repeat(64)}]}};
  const effective={...base,id:'geography:effective',footprints_sha256:additiveReleaseFootprintDigest(base,[effectiveFeature])};
  const patchRaw=Buffer.from(JSON.stringify({version:1,kind:'unassigned-native-cells-v1',base_reference:base,
    effective_reference:effective,ledger_sha256:sha(ledgerRaw),rule_sha256:ledger.rule_sha256,rows:[{y:3,runs:[[3,5,1]]}]}));
  const bodies={base_manifest:manifestRaw,owner_roster:bounds,ledger:ledgerRaw,patch:patchRaw};
  const names={base_manifest:'base.json',owner_roster:'owners.json.gz',ledger:'ledger.json',patch:'patch.json'};
  const pin=(name,raw)=>({path:name,bytes:raw.length,sha256:sha(raw)});
  const envelope={version:1,kind:'retained-native-base-plus-delta-v1',base_reference:base,effective_reference:effective,
    ...Object.fromEntries(Object.entries(bodies).map(([role,raw])=>[role,pin('additive-repairs/'+names[role],raw)]))};
  Object.assign(envelope.owner_roster,{encoding:'gzip',decoded_bytes:rosterRaw.length,decoded_sha256:sha(rosterRaw)});
  const prefix='coordination/engineering/current-fixture/',currentRoot=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'atlas-current-products-')));
  t.after(()=>fs.rmSync(currentRoot,{recursive:true,force:true}));
  const files=new Map(Object.entries(bodies).map(([role,raw])=>[prefix+names[role],raw]));
  const selection={version:1,method:'native-linear-evenodd-first-owner-v1',release_id:native.id,manifest_path:prefix+'base.json',sha256:sha(manifestRaw)};
  const envelopeRaw=Buffer.from(JSON.stringify(envelope));files.set(prefix+'envelope.json',envelopeRaw);
  const sidecar={version:2,kind:'retained-native-additive-selection-v2',base_selection:selection,
    runtime_envelope:pin(prefix+'envelope.json',envelopeRaw),logical_asset_map:Object.fromEntries(Object.entries(bodies).map(([role,raw])=>[role,
      {...pin(prefix+names[role],raw),...(role==='owner_roster'?{decoded_bytes:rosterRaw.length,decoded_sha256:sha(rosterRaw)}:{})}]))};
  const sidecarRaw=Buffer.from(JSON.stringify(sidecar));files.set(prefix+'sidecar.json',sidecarRaw);
  const currentSelection={...selection,additive_release:pin(prefix+'sidecar.json',sidecarRaw)};
  let projection,projectionRaw,referenceMetadata;
  if(reference){
    const before={...properties,parent_id:'old-parent',metadata:sourceRevision?{reference_revision:referenceRevision}:{}};
    const after={...properties,metadata:{...before.metadata,reference_corrections:[{id:'owner',action:'reparent',current_name:'Owner',
      current_parent_id:'old-parent',new_parent_id:'parent',rationale:'Synthetic sourced correction',
      evidence:[{url:'https://example.invalid/reference',title:'Fixture',inspected_fact:'Owner belongs to parent'}]}]}};
    feature.properties={...after,metadata:{...after.metadata,reference_revision:referenceRevision}};
    const originalPin=(name,digest)=>({commit:'a'.repeat(40),path:name,mode:'100644',git_blob_oid:'b'.repeat(40),bytes:1,sha256:digest});
    projection={version:1,kind:'native-reference-metadata-projection-v1',native_selection:selection,native_reference:native,reference:base,
      original_owner_roster_sha256:sha(bounds),hierarchy:{before:originalPin('before.json',native.hierarchy_sha256),after:originalPin('after.json',base.hierarchy_sha256)},
      receipts:[originalPin('receipt.json','c'.repeat(64))],source_updates:[],location_changes:[{location_id:'owner',before_properties:before,after_properties:after}],
      group_changes:[],provinces:['parent']};
    projectionRaw=Buffer.from(JSON.stringify(projection));currentSelection.reference_projection=pin(prefix+'reference.json',projectionRaw);
    files.set(currentSelection.reference_projection.path,projectionRaw);
    referenceMetadata={version:1,asset:pin('reference-metadata/current.json',projectionRaw),native_reference:native,reference:base,application_reference_revision:referenceRevision};
  }
  files.set('data/ownership-selection.json',Buffer.from(JSON.stringify(currentSelection)));
  files.set('.github/package-inputs.json',Buffer.from(JSON.stringify({version:1,inputs:['.github/package-inputs.json',...files.keys()],
    optional_inputs:[],verification_paths:[],generated_outputs:['dist/']})));
  for(const [name,raw]of files){fs.mkdirSync(path.dirname(path.join(currentRoot,name)),{recursive:true});fs.writeFileSync(path.join(currentRoot,name),raw);}
  // The retained producer really predates the selected addition. Its own valid
  // one-cell product shares only the invariant native base and owner roster.
  const priorAddition={type:'Polygon',coordinates:[[[1,0],[1.5,0],[1.5,1],[1,1],[1,0]]]};
  const priorLedger=structuredClone(ledger);priorLedger.assigned_cells=1;
  Object.assign(priorLedger.rows[0],{native_cells:1,geometry:priorAddition,geometry_sha256:footprintValueSha256(priorAddition)});
  const priorLedgerRaw=Buffer.from(JSON.stringify(priorLedger)),priorFeature=structuredClone(effectiveFeature);
  priorFeature.additiveFootprint.ledger_sha256=sha(priorLedgerRaw);
  Object.assign(priorFeature.additiveFootprint.additions[0],{geometry:priorAddition,geometry_sha256:footprintValueSha256(priorAddition)});
  const priorEffective={...base,id:'geography:prior-effective',footprints_sha256:additiveReleaseFootprintDigest(base,[priorFeature])};
  const priorPatchRaw=Buffer.from(JSON.stringify({version:1,kind:'unassigned-native-cells-v1',base_reference:base,
    effective_reference:priorEffective,ledger_sha256:sha(priorLedgerRaw),rule_sha256:ledger.rule_sha256,rows:[{y:3,runs:[[3,4,1]]}]}));
  const priorSourceBodies={...bodies,ledger:priorLedgerRaw,patch:priorPatchRaw},priorSourceEnvelope={...envelope,effective_reference:priorEffective,
    ledger:pin(envelope.ledger.path,priorLedgerRaw),patch:pin(envelope.patch.path,priorPatchRaw)};
  const priorBodies={...priorSourceBodies},priorEnvelope=structuredClone(priorSourceEnvelope);
  if(priorGzip)for(const role of ['ledger','patch']){
    const body=priorSourceBodies[role],raw=gzipSync(body);priorBodies[role]=raw;
    priorEnvelope[role]={...pin(priorSourceEnvelope[role].path+'.gz',raw),encoding:'gzip',decoded_bytes:body.length,decoded_sha256:sha(body)};
  }
  const catalog=[{...feature,geometry:null}],geometry=[{id:feature.id,geometry:feature.geometry}];changeCatalog(catalog);changeGeometry(geometry);
  const atlas={...(reference?{pixelMap:JSON.parse(manifestRaw),referenceMetadata}:{}),additiveRelease:priorEnvelope,reference_release:priorEffective,parts:['geography/catalog-0.json.gz'],geometryParts:['geography/part-0.json.gz']};
  const f=original(t,{bodies:{...(reference?{'dist/client/reference-metadata/current.json':projectionRaw}:{}),'dist/client/atlas-geography.json':JSON.stringify(atlas),
    'dist/client/geography/catalog-0.json.gz':gzipSync(JSON.stringify(catalog)),
    'dist/client/geography/part-0.json.gz':gzipSync(JSON.stringify(geometry)),
    ...Object.fromEntries(Object.entries(priorBodies).map(([role,raw])=>['dist/client/'+priorEnvelope[role].path,raw]))}});
  const prior=globalThis.fetch;globalThis.fetch=async()=>new Response(f.log());t.after(()=>{globalThis.fetch=prior;});
  const captured=JSON.parse(f.manifestRaw);captured.source.selection=currentSelection;
  f.manifestRaw=Buffer.from(JSON.stringify(captured)+'\n');
  f.receipt.package_output_manifest_sha256=sha(f.manifestRaw);f.receipt.package_output_manifest_bytes=f.manifestRaw.length;
  const originalToken=await authenticateOriginalPackageOutput(f);
  return {f,currentRoot,originalToken,files,sidecar,currentSelection,feature,bodies,envelope,priorBodies,priorEnvelope,priorSourceBodies,priorSourceEnvelope,projection,projectionRaw,referenceRevision};
}

test('shared current consumer publishes authenticated original context with historical custody entirely cold',async t=>{
  const f=await currentProductFixture(t),context=readOriginalPackageGeography(f.originalToken);
  const git=(root,...args)=>execFileSync('git',['-C',root,...args],{encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim();
  const historicalNames=['code-source.json','issued-plan.json','stderr.log','stdout.json','terminal.json'];
  const historicalDirectory='coordination/engineering/historical-custody/';
  for(const name of historicalNames){const file=path.join(f.currentRoot,historicalDirectory,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,'retained original science');}
  git(f.currentRoot,'init','-q');git(f.currentRoot,'add','.');
  const commit=()=>git(f.currentRoot,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture');
  commit();const historical=git(f.currentRoot,'rev-parse','HEAD');
  fs.rmSync(path.join(f.currentRoot,historicalDirectory),{recursive:true});git(f.currentRoot,'add','.');commit();
  const shallow=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-current-shallow-'));fs.rmdirSync(shallow);t.after(()=>fs.rmSync(shallow,{recursive:true,force:true}));
  execFileSync('git',['clone','--quiet','--depth=1','file://'+f.currentRoot,shallow]);
  assert.notEqual(spawnSync('git',['-C',shallow,'cat-file','-e',historical+'^{commit}'],{stdio:'pipe'}).status,0);
  git(shallow,'remote','set-url','origin','file:///unavailable-historical-repository');
  const head=git(shallow,'rev-parse','HEAD');
  const {prepareCurrentSelectedAdditive}=await import('../scripts/package-current-additive.mjs');
  const publication=await prepareCurrentSelectedAdditive({root:shallow,...context});
  assert.deepEqual(context.features,[f.feature]);assert.deepEqual(publication.selection,f.currentSelection);
  assert.notDeepEqual(publication.reference_release,context.atlas.reference_release,'The actual current effective reference must change');
  assert.deepEqual(publication.reference_release,f.envelope.effective_reference);
  for(const role of ['base_manifest','owner_roster'])assert.deepEqual(f.bodies[role],f.priorBodies[role],'Invariant '+role+' stays byte-exact');
  for(const role of ['ledger','patch'])assert.notEqual(sha(f.bodies[role]),sha(f.priorBodies[role]),'Current '+role+' is a genuinely different product');
  assert.equal(publication.input_inventory.length,6);
  assert.deepEqual(publication.input_inventory.map(pin=>pin.path).sort(),
    [f.currentSelection.additive_release.path,f.sidecar.runtime_envelope.path,...Object.values(f.sidecar.logical_asset_map).map(pin=>pin.path)].sort());
  for(const pin of publication.input_inventory){assert.equal(pin.whole_body_consumed,true);assert.equal(pin.sha256,sha(f.files.get(pin.path)));}
  for(const name of historicalNames)assert.equal(fs.existsSync(path.join(shallow,historicalDirectory,name)),false);
  assert.equal(git(shallow,'rev-parse','HEAD'),head);
  const out=path.join(f.currentRoot,'out');await publication.publish(out);
  for(const [role,raw]of Object.entries(f.bodies)){const actual=fs.readFileSync(path.join(out,publication.additiveRelease[role].path));assert.deepEqual(['ledger','patch'].includes(role)?gunzipSync(actual):actual,raw);}
  for(const pin of requireOriginalPackageOutput(f.originalToken).manifest.output.files)
    assert.equal(sha(fs.readFileSync(path.join(f.f.root,pin.path))),pin.sha256,'Original invariant/output remains intact: '+pin.path);
  await assert.rejects(publication.publish(out),/already exists/);
  const patch=f.sidecar.logical_asset_map.patch.path;fs.appendFileSync(path.join(shallow,patch),'x');
  await assert.rejects(prepareCurrentSelectedAdditive({root:shallow,...context}),/whole length|whole checksum/);
});

test('original emitted geometry join rejects coherent missing, duplicate, foreign and drifted bodies',async t=>{
  for(const change of [rows=>rows.length=0,rows=>rows.push(structuredClone(rows[0])),rows=>rows[0].id='foreign',
    rows=>rows[0].geometry.coordinates[0][1][0]=3]){
    const f=await currentProductFixture(t,{changeGeometry:change});
    assert.throws(()=>readOriginalPackageGeography(f.originalToken),/Nonempty|Duplicate|identity join|base geometry/);
  }
  for(const change of [rows=>rows.push(structuredClone(rows[0])),rows=>rows[0].id='foreign']){
    const f=await currentProductFixture(t,{changeCatalog:change});
    assert.throws(()=>readOriginalPackageGeography(f.originalToken),/identity join/);
  }
});

test('shared current consumer retains independent owner and base checks and refuses linked selection',async t=>{
  const f=await currentProductFixture(t),context=readOriginalPackageGeography(f.originalToken);
  const {prepareCurrentSelectedAdditive}=await import('../scripts/package-current-additive.mjs');
  await assert.rejects(prepareCurrentSelectedAdditive({root:f.currentRoot,...context,
    selectedGrid:{...context.selectedGrid,sha256:'f'.repeat(64)}}),/native selection/);
  const features=context.features.map(feature=>({...feature,properties:{parent_id:'foreign'}}));
  await assert.rejects(prepareCurrentSelectedAdditive({root:f.currentRoot,...context,features}),/owner identity or parent/);
  const selection=path.join(f.currentRoot,'data/ownership-selection.json');fs.renameSync(selection,selection+'.original');fs.symlinkSync(selection+'.original',selection);
  await assert.rejects(prepareCurrentSelectedAdditive({root:f.currentRoot,...context}),/selection must be ordinary/);
});




for(const sourceRevision of [false,true])test('identical original reference metadata retains '+(sourceRevision?'source-authored':'generated')+' revision and complete current properties',async t=>{
  const f=await currentProductFixture(t,{reference:true,sourceRevision}),context=readOriginalPackageGeography(f.originalToken);
  const {prepareCurrentSelectedAdditive}=await import('../scripts/package-current-additive.mjs');
  assert.equal(context.referenceRevision,f.referenceRevision);
  const publication=await prepareCurrentSelectedAdditive({root:f.currentRoot,...context});
  assert.deepEqual(publication.referenceMetadata,context.atlas.referenceMetadata);
  const destination=path.join(f.currentRoot,'output');await publication.publish(destination);
  assert.deepEqual(fs.readFileSync(path.join(destination,'reference-metadata/current.json')),f.projectionRaw);
  assert.equal(publication.input_inventory.length,7);
  await assert.rejects(publication.publish(destination),/already exists/);
  for(const mutation of [row=>row.properties.metadata.reference_revision='8'.repeat(64),row=>row.properties.parent_id='foreign',
    row=>row.properties.name='Changed',row=>delete row.properties.metadata.reference_corrections]){
    const features=structuredClone(context.features);mutation(features[0]);
    await assert.rejects(prepareCurrentSelectedAdditive({root:f.currentRoot,...context,features}),/reference revision|properties differ|owner identity or parent/);
  }
  const projectionFile=path.join(f.currentRoot,f.currentSelection.reference_projection.path);
  fs.appendFileSync(projectionFile,' ');
  await assert.rejects(prepareCurrentSelectedAdditive({root:f.currentRoot,...context}),/whole length|checksum/);
});

test('original reference metadata refuses coherent source, native, revision and emitted-body mismatches',async t=>{
  const f=await currentProductFixture(t,{reference:true}),base=JSON.parse(f.f.manifestRaw);
  const atlasFile=path.join(f.f.root,'dist/client/atlas-geography.json'),atlasRaw=fs.readFileSync(atlasFile);
  const projectionFile=path.join(f.f.root,'dist/client/reference-metadata/current.json'),projectionRaw=fs.readFileSync(projectionFile);
  const authenticate=async mutate=>{
    fs.writeFileSync(atlasFile,atlasRaw);fs.writeFileSync(projectionFile,projectionRaw);
    const manifest=structuredClone(base),atlas=JSON.parse(atlasRaw),projection=JSON.parse(projectionRaw);
    const rebind=mutate({manifest,atlas,projection}),raw=Buffer.from(JSON.stringify(projection));
    if(rebind===true){
      Object.assign(manifest.source.selection.reference_projection,{bytes:raw.length,sha256:sha(raw)});
      Object.assign(atlas.referenceMetadata.asset,{bytes:raw.length,sha256:sha(raw)});
    }
    fs.writeFileSync(atlasFile,JSON.stringify(atlas));fs.writeFileSync(projectionFile,raw);
    manifest.output.files=manifest.output.files.map(pin=>{const raw=fs.readFileSync(path.join(f.f.root,pin.path));return {...pin,bytes:raw.length,sha256:sha(raw)};});
    manifest.output.bytes=manifest.output.files.reduce((sum,pin)=>sum+pin.bytes,0);
    f.f.manifestRaw=Buffer.from(JSON.stringify(manifest)+'\n');
    f.f.receipt.package_output_manifest_sha256=sha(f.f.manifestRaw);f.f.receipt.package_output_manifest_bytes=f.f.manifestRaw.length;
    return authenticateOriginalPackageOutput(f.f);
  };
  for(const mutate of [
    ({manifest})=>{delete manifest.source.selection.reference_projection;},
    ({manifest})=>manifest.source.selection.reference_projection.sha256='f'.repeat(64),
    ({atlas})=>{delete atlas.referenceMetadata;},
    ({atlas})=>{delete atlas.referenceMetadata.application_reference_revision;},
    ({atlas})=>atlas.referenceMetadata.application_reference_revision='invalid',
    ({atlas})=>atlas.referenceMetadata.native_reference.id='geography:foreign',
    ({atlas})=>atlas.referenceMetadata.asset.path='a.bin',
    ({projection})=>{projection.original_owner_roster_sha256='f'.repeat(64);return true;},
    ({projection})=>{projection.native_selection.release_id='geography:foreign';return true;},
    ({projection})=>{projection.receipts=[];return true;},
  ]){const token=await authenticate(mutate);assert.throws(()=>readOriginalPackageGeography(token),/reference|Reference|native selection/);}
});


for(const [priorGzip,retirement] of [[false,false],[true,false],[true,true]])test('actual '+(priorGzip?'gzip':'plain')+(retirement?' retired-input':'')+' retained assembly preserves invariants and emits current gzip',async t=>{
  if(process.execArgv.length||process.env.NODE_OPTIONS?.trim()||process.env.NODE_PATH?.trim()){
    execFileSync(process.execPath,[new URL(import.meta.url).pathname,t.name],{env:{...process.env,NODE_OPTIONS:'',NODE_PATH:'',NODE_TEST_CONTEXT:undefined},encoding:'utf8'});return;
  }
  const oldFetch=globalThis.fetch,oldEntry=process.argv[1];
  t.after(()=>{globalThis.fetch=oldFetch;process.argv[1]=oldEntry;});
  const f=await currentProductFixture(t,{reference:true,priorGzip}),directory=f.currentRoot;
  const sourceRoot=fileURLToPath(new URL('../',import.meta.url)),copied=new Set();
  const write=(name,raw)=>{fs.mkdirSync(path.dirname(path.join(directory,name)),{recursive:true});fs.writeFileSync(path.join(directory,name),raw);};
  const copy=name=>{
    if(copied.has(name))return;copied.add(name);
    const raw=fs.readFileSync(path.join(sourceRoot,name));write(name,raw);
    if(/\.[mc]?js$/.test(name))for(const match of raw.toString('utf8').matchAll(/(?:from\s*|import\s*(?:\(\s*)?)['"]([^'"]+)['"]/g))
      if(match[1].startsWith('.'))copy(path.posix.normalize(path.posix.join(path.posix.dirname(name),match[1])));
  };
  for(const name of ['scripts/assemble-selected-package.mjs','scripts/extract-package-output.py','package.json','package-lock.json'])copy(name);
  fs.symlinkSync(fs.realpathSync(path.join(sourceRoot,'node_modules')),path.join(directory,'node_modules'),'dir');
  write('.gitignore','node_modules/\n.cache/\ndist/\n');
  for(const name of ['merge-integration-checks.yml','worker-merge.yml'])write('.github/workflows/'+name,'unchanged original producer');
  const pin=(name,raw)=>({path:name,bytes:raw.length,sha256:sha(raw),...(retirement?{mode:'100644',git_blob_oid:createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex')}:{})}),prefix='coordination/engineering/prior-fixture/';
  const priorMap={};
  for(const [role,raw]of Object.entries(f.priorSourceBodies)){
    const name=prefix+path.posix.basename(f.priorSourceEnvelope[role].path);write(name,raw);
    priorMap[role]={...pin(name,raw),...(role==='owner_roster'?{decoded_bytes:f.priorEnvelope[role].decoded_bytes,decoded_sha256:f.priorEnvelope[role].decoded_sha256}:{})};
  }
  const priorEnvelopeRaw=Buffer.from(JSON.stringify(f.priorSourceEnvelope)),priorEnvelopePin=pin(prefix+'envelope.json',priorEnvelopeRaw);write(priorEnvelopePin.path,priorEnvelopeRaw);
  const priorSidecar={...f.sidecar,runtime_envelope:priorEnvelopePin,logical_asset_map:priorMap},priorSidecarRaw=Buffer.from(JSON.stringify(priorSidecar));
  const priorPin=pin(prefix+'sidecar.json',priorSidecarRaw);write(priorPin.path,priorSidecarRaw);
  const priorSelection={...f.currentSelection,additive_release:priorPin};write('data/ownership-selection.json',JSON.stringify(priorSelection));
  const retired=[priorPin.path,priorEnvelopePin.path,priorMap.ledger.path,priorMap.patch.path];
  const definition=loadPackageInputs(directory);definition.inputs.push(...copied,...(retirement?[...Object.values(priorMap).map(pin=>pin.path),priorEnvelopePin.path,priorPin.path]:[prefix]));
  write('.github/package-inputs.json',JSON.stringify(definition));
  const git=(...args)=>execFileSync('git',['-C',directory,...args],{encoding:'utf8'}).trim();
  git('init','-q');const commit=()=>{git('add','.');git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture');};commit();
  const source={head:git('rev-parse','HEAD'),tree:git('rev-parse','HEAD^{tree}'),definition,selection:priorSelection,
    input_definition_sha256:sha(fs.readFileSync(path.join(directory,'.github/package-inputs.json'))),
    files:committedPackageInputs(directory,definition),producer:committedPackageProducer(directory)};
  const manifest=JSON.parse(f.f.manifestRaw),{packageBuildConfiguration}=await import('../scripts/package-output-artifact.mjs');
  manifest.source=source;manifest.runtime={node:process.version,platform:process.platform,arch:process.arch,dependencies:sha(fs.readFileSync(path.join(directory,'package-lock.json')))};
  manifest.configuration=packageBuildConfiguration();
  const receipt=Buffer.from(JSON.stringify({version:1,kind:'cloudflare',preflight:{passed:true}}));
  manifest.original_build_receipt=pin('.cache/package-input-build.json',receipt);
  fs.mkdirSync(path.join(f.f.root,'.cache'));
  fs.writeFileSync(path.join(f.f.root,'.cache/package-input-build.json'),receipt);
  f.f.manifestRaw=Buffer.from(JSON.stringify(manifest)+'\n');fs.writeFileSync(path.join(f.f.root,'.cache/package-output-manifest.json'),f.f.manifestRaw);
  const zip=path.join(f.f.root,'original.zip');
  execFileSync('python3',['-I','-S','-B','-c',`import pathlib,sys,zipfile
root=pathlib.Path(sys.argv[1])
with zipfile.ZipFile(sys.argv[2],'w',zipfile.ZIP_DEFLATED) as z:
 for prefix in ('dist','.cache'):
  for p in sorted((root/prefix).rglob('*')):
   if p.is_file(): z.write(p,p.relative_to(root).as_posix())`,f.f.root,zip]);
  const archive=fs.readFileSync(zip),origin=f.f.origin;
  origin.head=origin.workflow_head=f.f.run.head_sha=f.f.job.head_sha=f.f.artifact.workflow_run.head_sha=f.f.receipt.original_head=source.head;
  f.f.receipt.executed_workflow.sha=source.head;f.f.workflow.sha=source.producer.workflows.find(row=>row.path===f.f.workflow.path).oid;
  origin.artifact_bytes=f.f.artifact.size_in_bytes=archive.length;origin.artifact_digest=sha(archive);f.f.artifact.digest='sha256:'+origin.artifact_digest;
  f.f.receipt.package_output_manifest_sha256=sha(f.f.manifestRaw);f.f.receipt.package_output_manifest_bytes=f.f.manifestRaw.length;
  f.f.log=()=>[JSON.stringify(f.f.receipt),`SHA256 digest of uploaded artifact zip is ${origin.artifact_digest}`,
    `Artifact ${origin.artifact_name} has been successfully uploaded! Final size is ${archive.length} bytes. Artifact ID is ${origin.artifact_id}`].join('\n');
  const api=async route=>{
    if(route.endsWith('/actions/runs/17'))return f.f.run;
    if(route.includes('/attempts/2/jobs'))return {jobs:[f.f.job]};
    if(route.includes('/artifacts?'))return {total_count:1,artifacts:[f.f.artifact]};
    const commit=/\/git\/commits\/([a-f0-9]{40})$/.exec(route);
    if(commit)return {sha:commit[1],tree:{sha:git('rev-parse',commit[1]+'^{tree}')}};
    const tree=/\/git\/trees\/([a-f0-9]{40})(\?recursive=1)?$/.exec(route);
    if(tree)return {truncated:false,tree:git('ls-tree',...(tree[2]?['-r']:[]),'-lz',tree[1]).split('\0').filter(Boolean).map(line=>{
      const [meta,path]=line.split('\t'),[mode,type,sha,size]=meta.trim().split(/\s+/);return {path,mode,type,sha,size:Number(size)};
    })};
    const content=/\/contents\/(.+)\?ref=([a-f0-9]{40})$/.exec(route),blob=/\/git\/blobs\/([a-f0-9]{40})$/.exec(route);
    if(content||blob){const spec=blob?blob[1]:content[2]+':'+content[1],raw=execFileSync('git',['-C',directory,'cat-file','blob',spec]);
      return {type:'file',...(content?{path:content[1]}:{}),encoding:'base64',content:raw.toString('base64'),sha:git('rev-parse',spec),size:raw.length};}
    return f.f.api(route);
  };api.jobLogRedirect=f.f.api.jobLogRedirect;
  let downloads=0;api.artifactRedirect=async()=>{downloads++;return new Response(null,{status:302,headers:{location:'https://fixture.blob.core.windows.net/original.zip'}});};
  globalThis.fetch=async url=>new Response(String(url).endsWith('/original.zip')?archive:f.f.log());
  if(retirement){const next=structuredClone(definition);next.inputs=next.inputs.filter(name=>!retired.includes(name));write('.github/package-inputs.json',JSON.stringify(next));}
  write('data/ownership-selection.json',JSON.stringify(f.currentSelection));commit();
  const entry=path.join(directory,'scripts/assemble-selected-package.mjs'),{assembleSelectedPackage}=await import(pathToFileURL(entry));process.argv[1]=entry;
  const assemble=()=>assembleSelectedPackage({api,repo:f.f.repo,expectedHead:git('rev-parse','HEAD'),originalRunId:17});
  const result=await assemble();assert.equal(result.assembled,true);assert.equal(downloads,1);
  assert.equal(result.current_additive_assets,4);
  if(retirement){
    const receipt=JSON.parse(fs.readFileSync(path.join(directory,'.cache/package-input-build.json')));
    assert.deepEqual([...receipt.assembly.transition.removed_selected_inputs].sort(),[...retired].sort());
    // Discovery, private execution issuance and final output admission must use
    // the same original selector-bound bytes, never a caller's retirement flag.
    const currentDefinition=loadPackageInputs(directory),current={head:git('rev-parse','HEAD'),
      definition:currentDefinition,selection:f.currentSelection,files:committedPackageInputs(directory,currentDefinition),
      producer:committedPackageProducer(directory)};
    const found=await findOriginalPackage({api,repo:f.f.repo,current,originalRunId:17});
    assert.deepEqual(found.priorSidecarRaw,priorSidecarRaw);
    const authority=await import(pathToFileURL(path.join(directory,'coordination/engineering/additive-native-activation-20261009/package-selected-additive.mjs')));
    const original=await authority.authenticateOriginalPackageOutput({api,repo:f.f.repo,origin:found.origin,root:f.f.root,manifestRaw:f.f.manifestRaw});
    const stage=fs.mkdtempSync(path.join(directory,'.cache/proof-'));
    const issue=priorSidecarRaw=>authority.issuePackageAssemblyExecution({original,source:directory,stage,executingRoot:directory,priorSidecarRaw});
    assert.throws(()=>issue(undefined),/Authenticated prior cumulative|authenticated prior cumulative/);
    const corrupt=Buffer.from(priorSidecarRaw);corrupt[corrupt.length-1]^=1;
    assert.throws(()=>issue(corrupt),/Authenticated prior cumulative|authenticated prior cumulative/);
    assert.equal(authority.requirePackageAssemblyExecution(issue(found.priorSidecarRaw)).source_commit,current.head);
  }
  const changed=new Set(['dist/client/atlas-geography.json',...Object.values(f.priorEnvelope).filter(pin=>pin?.path).map(pin=>'dist/client/'+pin.path)]);
  for(const output of manifest.output.files)if(!changed.has(output.path)){
    const raw=fs.readFileSync(path.join(directory,output.path));assert.equal(raw.length,output.bytes);assert.equal(sha(raw),output.sha256,output.path);
  }
  const atlas=JSON.parse(fs.readFileSync(path.join(directory,'dist/client/atlas-geography.json')));
  assert.deepEqual(atlas.referenceMetadata,JSON.parse(fs.readFileSync(path.join(f.f.root,'dist/client/atlas-geography.json'))).referenceMetadata);
  assert.deepEqual(atlas.reference_release,f.envelope.effective_reference);
  for(const [role,raw]of Object.entries(f.bodies)){const actual=fs.readFileSync(path.join(directory,'dist/client',atlas.additiveRelease[role].path));assert.deepEqual(['ledger','patch'].includes(role)?gunzipSync(actual):actual,raw);}
  const published=sha(fs.readFileSync(path.join(directory,'dist/client/atlas-geography.json')));
  // A later mutable staging write is still checked against the original whole
  // output inventory. Identical metadata is never added to the mutable set.
  const writeFile=fs.promises.writeFile;
  fs.promises.writeFile=async function(file,...args){
    const result=await writeFile.call(this,file,...args);
    if(String(file).endsWith('/assembly/dist/reference-metadata/current.json'))fs.appendFileSync(file,' ');
    return result;
  };
  try{await assert.rejects(assemble(),/Invariant output changed during assembly/);}
  finally{fs.promises.writeFile=writeFile;}
  assert.equal(downloads,2);
  assert.equal(sha(fs.readFileSync(path.join(directory,'dist/client/atlas-geography.json'))),published,'Failed staging preserves the previous publication');
  // The actual assembly caller checks new static output before publication.
  fs.promises.writeFile=async function(file,...args){
    const result=await writeFile.call(this,file,...args);
    if(String(file).endsWith('/assembly/dist/reference-metadata/current.json')){
      const over=path.join(path.dirname(file),'oversize.bin'),fd=fs.openSync(over,'w');fs.ftruncateSync(fd,26214401);fs.closeSync(fd);
    }
    return result;
  };
  try{await assert.rejects(assemble(),/Cloudflare static asset exceeds 25 MiB/);}
  finally{fs.promises.writeFile=writeFile;}
  assert.equal(downloads,3);
  assert.equal(sha(fs.readFileSync(path.join(directory,'dist/client/atlas-geography.json'))),published,'Oversized staging preserves the previous publication');
  for(const mutation of [selection=>selection.reference_projection.sha256='f'.repeat(64),selection=>delete selection.reference_projection,
    selection=>selection.reference_projection=null]){
    const selection=structuredClone(f.currentSelection);mutation(selection);write('data/ownership-selection.json',JSON.stringify(selection));commit();
    assert.equal((await assemble()).assembled,false);assert.equal(downloads,3,'Changed projection must fail original compatibility before archive download');
    assert.equal(sha(fs.readFileSync(path.join(directory,'dist/client/atlas-geography.json'))),published);
  }
  write('data/ownership-selection.json',JSON.stringify(f.currentSelection));
  fs.appendFileSync(path.join(directory,f.currentSelection.reference_projection.path),' ');commit();
  assert.equal((await assemble()).assembled,false);assert.equal(downloads,3,'Changed projection body remains an invariant source refusal');
});

if(probeName&&!probeRegistered)throw Error('Unknown private assembly probe: '+probeName);

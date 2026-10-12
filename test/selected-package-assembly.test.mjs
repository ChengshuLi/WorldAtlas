import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {authenticateOriginalPackageOutput, requireOriginalPackageOutput,
  requirePackageAssemblyExecution} from '../coordination/engineering/additive-native-activation-20261009/package-selected-additive.mjs';
import {requireRetainedPackageTests, integrationTestFiles} from '../scripts/run-integration-tests.mjs';
import {admitAssemblyAtlasMetadata,createPackageAssemblyScratch} from '../scripts/assemble-selected-package.mjs';
import {execFileSync,spawnSync} from 'node:child_process';

const sha=raw=>createHash('sha256').update(raw).digest('hex');
function original(t){
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-original-package-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const bodies={'dist/client/atlas-geography.json':'{}','dist/client/a.bin':'invariant',
    'dist/cloudflare/index.js':'worker','dist/cloudflare/wrangler.json':'{}'};
  for(const [name,body]of Object.entries(bodies)){fs.mkdirSync(path.dirname(path.join(root,name)),{recursive:true});fs.writeFileSync(path.join(root,name),body);}
  const head='a'.repeat(40),repo='ChengshuLi/WorldAtlas';
  const origin={run_id:17,run_attempt:2,job_id:29,artifact_id:41,head,
    artifact_name:'cloudflare-package-output-17-2',artifact_digest:'b'.repeat(64),artifact_bytes:2000};
  const output={files:Object.entries(bodies).map(([name,body])=>({path:name,bytes:Buffer.byteLength(body),sha256:sha(body)})),
    bytes:Object.values(bodies).reduce((n,body)=>n+Buffer.byteLength(body),0)};
  const manifest={version:1,kind:'original-cloudflare-package-output',source:{head},output};
  const raw=Buffer.from(JSON.stringify(manifest)+'\n');
  const run={id:17,run_attempt:2,head_sha:head,event:'pull_request',path:'.github/workflows/merge-integration-checks.yml',
    status:'completed',repository:{full_name:repo},head_repository:{full_name:repo}};
  const names=['Snapshot original selected package inputs','Verify package controls','Build Cloudflare package without publishing',
    'Read back qualified native build outputs when selected','Run selected-data consumer checks','Inventory original selected package output',
    'Retain original selected package output'];
  const job={id:29,run_id:17,run_attempt:2,head_sha:head,name:'package',status:'completed',conclusion:'success',
    steps:names.map(name=>({name,status:'completed',conclusion:'success'}))};
  const artifact={id:41,name:origin.artifact_name,size_in_bytes:2000,digest:'sha256:'+origin.artifact_digest,
    expired:false,workflow_run:{id:17,head_sha:head}};
  const receipt={package_output_manifest_sha256:sha(raw),package_output_manifest_bytes:raw.length,original_head:head};
  const log=()=>[JSON.stringify(receipt),`SHA256 digest of uploaded artifact zip is ${origin.artifact_digest}`,
    `Artifact ${origin.artifact_name} has been successfully uploaded! Final size is 2000 bytes. Artifact ID is 41`].join('\n');
  const api=async route=>{
    if(route.endsWith('/attempts/2'))return run;
    if(route.endsWith('/jobs/29'))return job;
    if(route.endsWith('/artifacts/41'))return artifact;
    throw Error('Unexpected mocked authority route: '+route);
  };
  api.jobLogRedirect=async()=>new Response(null,{status:302,headers:{location:'https://fixture.blob.core.windows.net/job-log'}});
  return {root,repo,origin,manifestRaw:raw,api,run,job,artifact,receipt,log};
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
  for(const [event,status] of [['workflow_dispatch',1],['pull_request',0]]){
    const result=spawnSync(process.execPath,['scripts/assemble-selected-package.mjs'],{
      env:{...process.env,GH_TOKEN:'',GITHUB_TOKEN:'',GITHUB_EVENT_NAME:event,
        GITHUB_WORKFLOW:'Selected package equivalence proof',GITHUB_OUTPUT:path.join(temporary,event)},encoding:'utf8'});
    assert.equal(result.status,status,result.stderr);assert.equal(JSON.parse(result.stdout).assembled,false);
    assert.match(fs.readFileSync(path.join(temporary,event),'utf8'),/^assembled=false\n/);
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

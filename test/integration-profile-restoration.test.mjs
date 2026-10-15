import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync, execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {integrationTestFiles} from '../scripts/run-integration-tests.mjs';
import {checkoutExecutionClosure} from '../coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/artifact-checkout-execution.mjs';

const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
// Routing controls check roster eligibility separately; this fixture exercises
// the actual entry without duplicating its selected inventory.
const focused=integrationTestFiles('evidence',0).map(file=>path.basename(file,'.test.mjs'));
const helper='scripts/canonical-restoration.mjs';

test('actual checkout authority matches the selected certificate role closure and critical bytes',()=>{
  const closure=checkoutExecutionClosure(repo);
  const gitBody=name=>{
    const result=spawnSync('git',['show',`HEAD:${name}`],{cwd:repo});
    assert.equal(result.status,0,result.stderr.toString());return result.stdout;
  };
  const pinned=pin=>{
    const raw=gitBody(pin.path);assert.equal(raw.length,pin.bytes);
    assert.equal(createHash('sha256').update(raw).digest('hex'),pin.sha256);
    return JSON.parse(raw);
  };
  const selection=JSON.parse(gitBody('data/ownership-selection.json'));
  const certificate=pinned(selection.artifact_consumption.certificate);
  const code=pinned(certificate.application_consumer_code),entry='scripts/run-integration-tests.mjs';
  const critical=[...code.critical_files,...code.entry_critical_files[entry]];
  assert.deepEqual(closure,[...critical.map(pin=>pin.path),...Object.values(code.entry_roles[entry]).flat()].sort(),
    'Complete actual execution role closure required by qualified-artifact-consumer');
  for(const pin of critical){
    const raw=fs.readFileSync(path.join(repo,pin.path));assert.equal(raw.length,pin.bytes);
    assert.equal((fs.statSync(path.join(repo,pin.path)).mode&511)===493?'100755':'100644',pin.mode);
    assert.equal(createHash('sha256').update(raw).digest('hex'),pin.sha256,'Reviewed critical consumer semantics changed');
    assert.equal(createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex'),pin.git_blob);
  }
});

test('actual checkout authority refuses concatenated relative imports and missing smoke dependencies',t=>{
  const cache=path.join(repo,'.cache');fs.mkdirSync(cache,{recursive:true});
  const root=fs.mkdtempSync(path.join(cache,'checkout-closure-boundary-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  fs.mkdirSync(path.join(root,'scripts'));
  fs.writeFileSync(path.join(root,'package.json'),'{"type":"module"}\n');
  const entry=path.join(root,'scripts/run-integration-tests.mjs');
  fs.writeFileSync(entry,"const smoke = await import('../' + 'scripts/selected-delivery-smoke.mjs');\n");
  assert.throws(()=>checkoutExecutionClosure(root),{code:'ERR_ASSERTION'});
  fs.writeFileSync(entry,"const smoke = await import('./selected-delivery-smoke.mjs');\n");
  assert.throws(()=>checkoutExecutionClosure(root),{code:'ENOENT'});
});

function selectedWorkflowCommand(workflow='queue') {
  const name=workflow==='pr'?'merge-integration-checks':'worker-merge';
  const step=workflow==='pr'?'Run selected-data consumer checks':'Test applicable combined-tree invariants without publishing or live imports';
  const yaml=fs.readFileSync(path.join(repo,`.github/workflows/${name}.yml`),'utf8');
  const start=yaml.indexOf(`      - name: ${step}\n`);assert(start>=0);
  const command=yaml.slice(start).split('\n      - ')[0].split('        run: |\n')[1];assert(command);
  return command.trimEnd().split('\n').map(line=>line.slice(10)).join('\n');
}

function fixture(t,{full=false,helperBody,selectedHelperBody,omitSelectedHelper=false,skip=false,selected=false,smokeBody}={}) {
  // This is a tiny actual runner boundary fixture, not a scientific restoration.
  const sources=['scripts/run-integration-tests.mjs','scripts/integration-profile.mjs','scripts/check-handoff-scope.mjs','scripts/package-inputs.mjs','scripts/compile-hosted-migrations.mjs','scripts/ci-setup-observations.mjs'];
  const bodies=sources.map(name=>{
    const p=path.join(repo,name),s=fs.lstatSync(p);
    assert.ok(s.isFile()&&!s.isSymbolicLink());
    return fs.readFileSync(p);
  });
  const cache=path.join(repo,'.cache');fs.mkdirSync(cache,{recursive:true});
  const root=fs.mkdtempSync(path.join(cache,'integration-profile-boundary-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  function write(name,body) {const p=path.join(root,name);fs.mkdirSync(path.dirname(p),{recursive:true});fs.writeFileSync(p,body,{flag:'wx'});}
  write('package.json','{"type":"module"}\n');
  sources.forEach((name,i)=>write(name,bodies[i]));
  const names=selected?[...focused,'compact-ownership','canonical-compact-repack','prepared-parity']:full?['probe']:focused;
  for(const name of names)write(`test/${name}.test.mjs`,
    `import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
test('actual selected test',${skip?'{skip:true},':''}()=>{
  assert.equal(fs.existsSync('restored-fixture.json'),${full});
  fs.writeFileSync('tests-reached-'+${JSON.stringify(name)},'reached',{flag:'wx'});
});\n`);
  if(helperBody!==undefined)write(helper,helperBody);
  if(full&&!omitSelectedHelper)write('coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/prepare-model-reader-checkout.mjs',selectedHelperBody??`import fs from 'node:fs';import assert from 'node:assert/strict';
export function prepareModelReaderCheckout({root,profile,shard}){
 assert.equal(root,process.cwd());assert.equal(profile,'full');assert([0,1,2].includes(shard));
 assert.equal(fs.existsSync('data/ownership-selection.json'),${selected},'This tiny fixture has no selected artifact');
 fs.writeFileSync('selected-checkout-fixture-reached.json','{"fixture_only":true}',{flag:'wx'});
 return {applicable:false,fixture_only:true};
}
`);

  const expectations='coordination/engineering/fixture/selected-delivery-expectations.json';
  if(selected){
    const pin=(name,value)=>{const bytes=Buffer.from(JSON.stringify(value));write(name,bytes);return {path:name,bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')};};
    const member={component_id:'component',target_id:'target',disposition:'assigned',geometry_sha256:'a'.repeat(64)};
    const ledger=pin('coordination/engineering/fixture/ledger.json',{version:2,kind:'native-additive-repair-ledger-v2',rows:[{...member,native_cells:1}]});
    const side=pin('coordination/engineering/fixture/sidecar.json',{logical_asset_map:{ledger}});
    pin('data/ownership-selection.json',{artifact_consumption:{},additive_release:side});
    pin(expectations,{version:1,selected_ledger_sha256:ledger.sha256,cumulative_native_cells:1,cohorts:[{original_batch_id:'original',component_ids:['component'],members:[member]}]});
    write('dist/client/atlas-geography.json','{}');fs.mkdirSync(path.join(root,'.cache'));
    write('scripts/selected-delivery-smoke.mjs',smokeBody??`import fs from 'node:fs';import assert from 'node:assert/strict';
export async function runSelectedDeliverySmoke({root,expectationsPath,emittedDirectory,outputPath}){
  assert.equal(root,process.cwd());assert.equal(process.env.INTEGRATION_PROFILE,'full');assert(['selected-data','selected-output'].includes(process.env.INTEGRATION_TEST_SELECTION));
  assert(fs.existsSync(expectationsPath));assert(fs.existsSync(emittedDirectory+'/atlas-geography.json'));
  fs.writeFileSync(outputPath,'{"fixture_only":true}',{flag:'wx'});return {fixture_only:true};
}`);
  }
  return {root,expectations,run(profile=full?'full':'evidence',shard='0',workflow='queue') {
    const env={...process.env,INTEGRATION_PROFILE:profile,INTEGRATION_SHARD:shard,...(selected?{INTEGRATION_TEST_SELECTION:'selected-data',SELECTED_EXPECTATIONS_PATH:expectations}:{})};
    // Match a plain CLI launch, rather than inheriting node:test's recursion tag.
    delete env.NODE_TEST_CONTEXT;
    return spawnSync(selected?'bash':process.execPath,selected?['-e','-o','pipefail','-c',selectedWorkflowCommand(workflow)]:['scripts/run-integration-tests.mjs'],{
      cwd:root,encoding:'utf8',timeout:30000,maxBuffer:1024*1024,
      env
    });
  }};
}

test('real evidence entry runs every selected test with no canonical namespace',t=>{
  const f=fixture(t),r=f.run();assert.equal(r.status,0,r.stderr);assert.match(r.stdout,/# skipped 0/);
  assert.ok(!fs.existsSync(path.join(f.root,'coordination')));
  assert.equal(fs.readdirSync(f.root).filter(n=>n.startsWith('tests-reached-')).length,focused.length);
  assert.ok(!r.stdout.includes('canonical_checkout'));
});
test('real full entry calls canonical preparation before selected readers',t=>{
  const f=fixture(t,{full:true,helperBody:`import fs from 'node:fs';
export function prepareCanonicalCheckout(){fs.writeFileSync('restored-fixture.json','{"complete":true}',{flag:'wx'});return {fixture_only:true};}\n`});
  const r=f.run();assert.equal(r.status,0,r.stderr);assert.match(r.stdout,/canonical_checkout/);
  assert.match(r.stdout,/# skipped 0/);assert.ok(fs.existsSync(path.join(f.root,'tests-reached-probe')));
  assert.ok(fs.existsSync(path.join(f.root,'selected-checkout-fixture-reached.json')));assert.match(r.stdout,/selected_model_reader_checkout/);
});
test('real full entry refuses a missing selected checkout helper before tests',t=>{
 const f=fixture(t,{full:true,omitSelectedHelper:true,helperBody:`export function prepareCanonicalCheckout(){return {fixture_only:true};}\n`}),r=f.run();
 assert.notEqual(r.status,0);assert.match(r.stderr,/ERR_MODULE_NOT_FOUND/);assert.ok(!fs.existsSync(path.join(f.root,'tests-reached-probe')));
});
test('real full entry propagates selected checkout refusal before tests',t=>{
 const f=fixture(t,{full:true,helperBody:`export function prepareCanonicalCheckout(){return {fixture_only:true};}\n`,selectedHelperBody:`export function prepareModelReaderCheckout(){throw Error('selected artifact association rejected');}\n`}),r=f.run();
 assert.notEqual(r.status,0);assert.match(r.stderr,/selected artifact association rejected/);assert.ok(!fs.existsSync(path.join(f.root,'tests-reached-probe')));
});
test('real full entry rejects an absent canonical helper before tests',t=>{
  const f=fixture(t,{full:true}),r=f.run();assert.notEqual(r.status,0);
  assert.match(r.stderr,/ERR_MODULE_NOT_FOUND/);assert.ok(!fs.existsSync(path.join(f.root,'tests-reached-probe')));
});
test('real full entry propagates canonical input rejection before tests',t=>{
  const f=fixture(t,{full:true,helperBody:"export function prepareCanonicalCheckout(){throw Error('missing authenticated canonical input');}\n"});
  const r=f.run();assert.notEqual(r.status,0);assert.match(r.stderr,/missing authenticated canonical input/);
  assert.ok(!fs.existsSync(path.join(f.root,'tests-reached-probe')));
});
test('real evidence entry preserves the zero-skips safeguard',t=>{
  const f=fixture(t,{skip:true}),r=f.run();assert.notEqual(r.status,0);
  assert.match(r.stderr,/Regression did not establish zero skipped tests/);
});
test('invalid profile rejects before either restoration or tests',t=>{
  const f=fixture(t),r=f.run('invalid');assert.notEqual(r.status,0);
  assert.match(r.stderr,/Invalid trusted integration test profile/);
  assert.ok(!fs.readdirSync(f.root).some(n=>n.startsWith('tests-reached-')));
});

const restored=`import fs from 'node:fs';export function prepareCanonicalCheckout(){fs.writeFileSync('restored-fixture.json','{}',{flag:'wx'});return {fixture_only:true};}`;
test('actual queue selected command runs current smoke without unit tests, restoration or historical readback receipt',t=>{
  const f=fixture(t,{selected:true}),r=f.run('full');
  assert.equal(r.status,0,r.stderr);
  assert(fs.existsSync(path.join(f.root,'.cache/selected-delivery-smoke.json')));
  assert(!fs.existsSync(path.join(f.root,'.cache/native-normal-built-output.json')));
  assert(!fs.readdirSync(f.root).some(n=>n.startsWith('tests-reached-')));
  assert(!r.stdout.includes('canonical_checkout'));
  assert(!r.stdout.includes('selected_model_reader_checkout'));
});
for(const missing of ['dist/client/atlas-geography.json','scripts/selected-delivery-smoke.mjs','coordination/engineering/fixture/selected-delivery-expectations.json'])
 test('real selected-data entry refuses missing actual '+missing+' before tests',t=>{
  const f=fixture(t,{full:true,selected:true,helperBody:restored});fs.unlinkSync(path.join(f.root,missing));const r=f.run();
  assert.notEqual(r.status,0);assert(!fs.readdirSync(f.root).some(n=>n.startsWith('tests-reached-')));
});
test('real selected-data entry propagates actual smoke failure',t=>{
  const f=fixture(t,{selected:true,smokeBody:"export async function runSelectedDeliverySmoke(){throw Error('actual smoke refused');}"}),r=f.run();
  assert.notEqual(r.status,0);assert.match(r.stderr,/actual smoke refused/);
});

test('ordinary selected data cannot accidentally invoke unit regression or restore context',t=>{
  const f=fixture(t,{selected:true}),result=spawnSync(process.execPath,['scripts/run-integration-tests.mjs'],{
    cwd:f.root,env:{...process.env,INTEGRATION_PROFILE:'full',INTEGRATION_SHARD:'0',INTEGRATION_TEST_SELECTION:'selected-data'},encoding:'utf8'});
  assert.notEqual(result.status,0);assert.match(result.stderr,/Invalid trusted test selection/);
  assert(!fs.readdirSync(f.root).some(n=>n.startsWith('tests-reached-')));
});

test('actual assembled queue command runs current smoke and requires the same-head trusted receipt without restoration',t=>{
  for(const altered of [false,true]){
    const f=fixture(t,{selected:true});
    const git=(...args)=>execFileSync('git',['-C',f.root,...args],{encoding:'utf8'}).trim();
    git('init','-q');git('add','.');git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture');
    const head=git('rev-parse','HEAD'),receipt=JSON.stringify({kind:'cloudflare',preflight:{inputs:{head}},assembly:{
      kind:'retained-original-output-plus-current-additive',current_execution:{source_commit:head},
      base_restoration_invoked:false,invariant_build_invoked:false,
      origin:{run_id:17}}});
    fs.writeFileSync(path.join(f.root,'.cache/package-input-build.json'),receipt+(altered?' ':''));
    const env={...process.env,INTEGRATION_PROFILE:'full',INTEGRATION_SHARD:'0',INTEGRATION_TEST_SELECTION:'selected-output',
      SELECTED_EXPECTATIONS_PATH:f.expectations,SELECTED_PACKAGE_ASSEMBLY_SHA256:createHash('sha256').update(receipt).digest('hex')};
    delete env.NODE_TEST_CONTEXT;
    const result=spawnSync('bash',['-e','-o','pipefail','-c',selectedWorkflowCommand()],{cwd:f.root,env,encoding:'utf8',timeout:30000});
    assert.equal(result.status,altered?1:0,result.stderr);
    if(altered)assert.match(result.stderr,/receipt digest differs/);
    else assert.match(result.stdout,/package_assembly/);
    assert(fs.existsSync(path.join(f.root,'.cache/selected-delivery-smoke.json')));
    assert(!fs.existsSync(path.join(f.root,'.cache/native-normal-built-output.json')));
    assert(!fs.readdirSync(f.root).some(n=>n.startsWith('tests-reached-')));
    assert(!result.stdout.includes('canonical_checkout'));
  }
});


test('actual retained-output runner executes current tests without any model restoration helper',t=>{
  const f=fixture(t,{selected:true});
  const git=(...args)=>execFileSync('git',['-C',f.root,...args],{encoding:'utf8'}).trim();
  git('init','-q');git('add','.');git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture');
  const head=git('rev-parse','HEAD');
  const receipt=JSON.stringify({kind:'cloudflare',preflight:{inputs:{head}},assembly:{
    kind:'retained-original-output-plus-current-additive',current_execution:{source_commit:head},
    base_restoration_invoked:false,invariant_build_invoked:false,
    origin:{run_id:17}}});
  fs.writeFileSync(path.join(f.root,'.cache/package-input-build.json'),receipt);
  const env={...process.env,INTEGRATION_PROFILE:'full',INTEGRATION_SHARD:'0',INTEGRATION_TEST_SELECTION:'selected-output',
    SELECTED_PACKAGE_ASSEMBLY_SHA256:createHash('sha256').update(receipt).digest('hex')};
  delete env.NODE_TEST_CONTEXT;
  const result=spawnSync(process.execPath,['scripts/run-integration-tests.mjs'],{cwd:f.root,env,encoding:'utf8',timeout:30000});
  assert.equal(result.status,0,result.stderr);assert.match(result.stdout,/# skipped 0/);
  assert.equal(fs.readdirSync(f.root).filter(name=>name.startsWith('tests-reached-')).length,1);
  assert(fs.existsSync(path.join(f.root,'tests-reached-compact-ownership')));
  assert(!fs.existsSync(path.join(f.root,'tests-reached-canonical-compact-repack')));
  assert(!fs.existsSync(path.join(f.root,'tests-reached-prepared-parity')));
  assert(!result.stdout.includes('selected_model_reader_checkout'));assert(!result.stdout.includes('canonical_checkout'));
});

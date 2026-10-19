import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync, execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {integrationProfile} from '../scripts/integration-profile.mjs';
import {checkoutExecutionClosure} from '../coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/artifact-checkout-execution.mjs';

const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');

test('actual checkout authority covers current code independently of historical provenance',()=>{
  const closure=checkoutExecutionClosure(repo);
  assert.equal(new Set(closure).size,closure.length);
  assert(closure.includes('scripts/run-integration-tests.mjs'));
  assert(!closure.includes('coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/qualified-artifact-consumer.mjs'));
  assert(!closure.includes('scripts/canonical-restoration.mjs'));

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

function workflowCommand() {
  const step='Test applicable combined-tree invariants without publishing or live imports';
  const yaml=fs.readFileSync(path.join(repo,'.github/workflows/worker-merge.yml'),'utf8');
  const start=yaml.indexOf(`      - name: ${step}\n`);assert(start>=0);
  const command=yaml.slice(start).split('\n      - ')[0].split('        run: |\n')[1];assert(command);
  return command.trimEnd().split('\n').map(line=>line.slice(10)).join('\n');
}

function fixture(t,{selected=false,smokeBody,fail=false}={}) {
  // One marker exercises runner dispatch. Real inventory, skip and process-lifecycle
  // behavior are covered by full-regression-shards and integration-streaming.
  const sources=['src/native-grid.js','src/reference-metadata.js','scripts/run-integration-tests.mjs','scripts/integration-profile.mjs','scripts/check-handoff-scope.mjs','scripts/package-inputs.mjs','scripts/package-producer-contract.mjs','scripts/compile-hosted-migrations.mjs','scripts/ci-setup-observations.mjs'];
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
  const names=selected?['integration-fixture','compact-ownership']:['integration-fixture'];
  for(const name of names)write(`test/${name}.test.mjs`,
    `import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
test('actual runner marker',()=>{
  assert.equal(${fail},false);
  fs.writeFileSync('tests-reached-'+${JSON.stringify(name)},'reached',{flag:'wx'});
});\n`);
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
  return {root,expectations,run(profile=selected?'full':'evidence',shard='0',overrides={}) {
    const env={...process.env,INTEGRATION_PROFILE:profile,INTEGRATION_SHARD:shard,INTEGRATION_TEST_SELECTION:selected?'selected-data':'complete',...(selected?{SELECTED_EXPECTATIONS_PATH:expectations}:{}),...overrides};
    // Match a plain CLI launch, rather than inheriting node:test's recursion tag.
    delete env.NODE_TEST_CONTEXT;
    return spawnSync('bash',['-e','-o','pipefail','-c',workflowCommand()],{
      cwd:root,encoding:'utf8',timeout:30000,maxBuffer:1024*1024,
      env
    });
  }};
}

test('actual queue shell runs tests and propagates failure in both live profiles',t=>{
  for(const profile of ['evidence','full'])for(const fail of [false,true]){
    const f=fixture(t,{fail}),result=f.run(profile);
    assert.equal(result.status,fail?1:0,result.stderr);
    assert.equal(fs.existsSync(path.join(f.root,'tests-reached-integration-fixture')),!fail);
  }
  const invalid=fixture(t),result=invalid.run('invalid');
  assert.notEqual(result.status,0);
  assert(!fs.existsSync(path.join(invalid.root,'tests-reached-integration-fixture')));
});

test('actual reviewed queue shell executes only named consumers and needs no database or emitted output',t=>{
  const f=fixture(t);
  fs.writeFileSync(path.join(f.root,'test/unrelated.test.mjs'),"throw Error('Unrelated test must not execute');\n");
  const result=f.run('evidence','0',{INTEGRATION_TEST_SELECTION:'reviewed',
    INTEGRATION_TEST_FILES_BASE64:Buffer.from(JSON.stringify(['test/integration-fixture.test.mjs'])).toString('base64')});
  assert.equal(result.status,0,result.stderr);assert(fs.existsSync(path.join(f.root,'tests-reached-integration-fixture')));
  assert(!fs.existsSync(path.join(f.root,'dist')));assert(!fs.existsSync(path.join(f.root,'data')));
  assert.match(result.stdout,/'?test_selection'?:\s*'?reviewed'?|"test_selection":"reviewed"/);
});

test('actual selected queue shell runs smoke and propagates its failure without unit regression',t=>{
  for(const fail of [false,true]){
    const f=fixture(t,fail?{selected:true,smokeBody:"export async function runSelectedDeliverySmoke(){throw Error('actual smoke refused');}"}:{selected:true});
    const result=f.run();
    assert.equal(result.status,fail?1:0,result.stderr);
    assert.equal(fs.existsSync(path.join(f.root,'.cache/selected-delivery-smoke.json')),!fail);
    assert(!fs.readdirSync(f.root).some(name=>name.startsWith('tests-reached-')));
  }
});

test('actual selected queue shell keeps complete smoke details in the existing artifact',t=>{
  const scalars={version:1,kind:'actual-emitted-selected-consumer',passed:true,feature_count:49625,
    cumulative_native_cells_picked_and_sampled:1037224,stable_owner_controls:48206,expected_components_verified:1288,
    selected_ledger_sha256:'a'.repeat(64),selected_patch_sha256:'b'.repeat(64),expectations_sha256:'c'.repeat(64),
    limitation:'Fixture measurements only',optional:null};
  const report={...scalars,components:Array.from({length:1288},(_,i)=>({component_id:`component-${i}`,native_rows_sha256:'d'.repeat(64)})),
    input_inventory:{original:'complete retained input details'}};
  const bytes=JSON.stringify(report,null,2)+'\n';
  const f=fixture(t,{selected:true,smokeBody:`import fs from 'node:fs';
export async function runSelectedDeliverySmoke({outputPath}){
  fs.writeFileSync(outputPath,${JSON.stringify(bytes)},{flag:'wx'});return ${JSON.stringify(report)};
}`});
  const result=f.run();assert.equal(result.status,0,result.stderr);
  assert.equal(fs.readFileSync(path.join(f.root,'.cache/selected-delivery-smoke.json'),'utf8'),bytes);
  assert.deepEqual(JSON.parse(result.stdout.trim()),{selected_delivery_smoke:scalars});
  const yaml=fs.readFileSync(path.join(repo,'.github/workflows/worker-merge.yml'),'utf8');
  assert.match(yaml,/name: selected-delivery-smoke-\$\{\{ inputs\.request_id \}\}-\$\{\{ github\.run_attempt \}\}/);
  assert.match(yaml,/path: \.cache\/selected-delivery-smoke\.json/);
});

test('selected queue shell refuses missing consumed inputs',t=>{
  for(const missing of ['dist/client/atlas-geography.json','scripts/selected-delivery-smoke.mjs',
    'coordination/engineering/fixture/selected-delivery-expectations.json']){
    const f=fixture(t,{selected:true});fs.unlinkSync(path.join(f.root,missing));
    assert.notEqual(f.run().status,0,missing);
    assert(!fs.readdirSync(f.root).some(name=>name.startsWith('tests-reached-')));
  }
});

test('actual assembled queue shell runs smoke and rejects a changed trusted receipt',t=>{
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
    const result=spawnSync('bash',['-e','-o','pipefail','-c',workflowCommand()],{cwd:f.root,env,encoding:'utf8',timeout:30000});
    assert.equal(result.status,altered?1:0,result.stderr);
    assert.equal(result.stdout.includes('package_assembly'),!altered);
    assert(fs.existsSync(path.join(f.root,'.cache/selected-delivery-smoke.json')));
    assert(!fs.readdirSync(f.root).some(n=>n.startsWith('tests-reached-')));
  }
});


test('focused routing cannot accept a deleted helper imported by the retained real runner',t=>{
  const name='scripts/ci-setup-observations.mjs',f=fixture(t);
  assert.equal(integrationProfile('engineering/deleted-control',[{filename:name,status:'removed'}],{},new Map()),'evidence');
  fs.unlinkSync(path.join(f.root,name));
  const result=f.run();assert.notEqual(result.status,0);
  assert.match(result.stderr,/ERR_MODULE_NOT_FOUND/);
  assert(!fs.readdirSync(f.root).some(name=>name.startsWith('tests-reached-')));
});

test('deleted workflow routing retains full fallback for actual runtime inputs',()=>{
  const filename='.github/workflows/retired-isolated-stage.yml';
  assert.equal(integrationProfile('engineering/retired-stage',[{filename,status:'removed'}],{},new Map()),'evidence');
  for(const filename of ['scripts/build-static-inner.mjs','src/native-grid.js','hosted/geographic-releases.js'])
    assert.equal(integrationProfile('engineering/retired-stage',[{filename,status:'removed'}],{},new Map()),'full');
});

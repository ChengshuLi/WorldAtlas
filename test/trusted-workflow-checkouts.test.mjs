import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync, execFileSync} from 'node:child_process';
import {checkGitScope} from '../scripts/check-handoff-scope.mjs';

const root = path.resolve(import.meta.dirname, '..');
const workflows = ['issue-claims.yml', 'worker-merge.yml'];

// Reproduce each declared sparse tree, including cone-mode root files. Load
// trusted modules without executing workflow entrypoints or contacting GitHub.
function probe(directories, {geography = false, sourceRoot = root, check} = {}) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'worldatlas-checkout-'));
  try {
    fs.copyFileSync(path.join(sourceRoot, 'package.json'), path.join(directory, 'package.json'));
    for (const relative of directories) {
      const source = path.join(sourceRoot, relative);
      const destination = path.join(directory, relative);
      fs.mkdirSync(path.dirname(destination), {recursive: true});
      fs.cpSync(source, destination, {recursive: true});
    }
    if (check) return check(directory);
    return spawnSync(process.execPath, ['--input-type=module', '-e',
      "await import('./scripts/issue-claim-contract.mjs'); await import('./scripts/research-import-gate.mjs'); await import('./scripts/premerge-evidence.mjs');" +
      (geography ? "await import('./scripts/check-effective-geographic-regression.mjs'); await import('./coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs'); console.log('complete trusted geography closure imported');" : '')],
    {cwd: directory, encoding: 'utf8', env: {PATH: process.env.PATH}});
  } finally { fs.rmSync(directory, {recursive: true, force: true}); }
}

for (const workflow of ['worker-merge.yml']) {
  test(`${workflow}: actual geographic checkout imports its complete trusted closure`, () => {
    const source = fs.readFileSync(path.join(root, '.github/workflows', workflow), 'utf8');
    const match = source.match(/- name: Checkout trusted geographic checker[\s\S]*?sparse-checkout: \|\n((?:            .+\n)+)/);
    assert.ok(match, 'actual trusted geography checkout must be declared');
    const result = probe(match[1].trim().split('\n').map(row => row.trim()), {geography: true});
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /complete trusted geography closure imported/);
  });
}

test('negative control: old geographic sparse tree omits mandatory coordinator bodies', () => {
  const result = probe(['scripts', 'src', '.github'], {geography: true});
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /ERR_MODULE_NOT_FOUND/);
  assert.match(result.stderr, /selected-geography-effective-prevention-20261009/);
});

test('negative control: old scripts-only tree cannot load relocated regional gate', () => {
  const result = probe(['scripts', '.github']);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /ERR_MODULE_NOT_FOUND/);
  assert.match(result.stderr, /src\/regional-import-gate\.js/);
});


test('sparse candidate still detects changes and rename sources outside the working tree', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'worldatlas-sparse-scope-'));
  const git = args => execFileSync('git', args, {cwd: directory, encoding: 'utf8'});
  const run = (command, args, options) => execFileSync(command, args, {...options, cwd: directory});
  try {
    git(['init', '-q']); git(['config', 'user.email', 'test@example.invalid']); git(['config', 'user.name', 'test']);
    fs.mkdirSync(path.join(directory, 'src'), {recursive: true});
    fs.mkdirSync(path.join(directory, 'research/campaigns/example'), {recursive: true});
    fs.writeFileSync(path.join(directory, 'src/main.js'), 'original source\n');
    fs.writeFileSync(path.join(directory, 'research/campaigns/example/notes.txt'), 'original notes\n');
    git(['add', '.']); git(['commit', '-qm', 'baseline']); const base = git(['rev-parse', 'HEAD']).trim();
    fs.writeFileSync(path.join(directory, 'research/campaigns/example/notes.txt'), 'updated notes\n');
    git(['commit', '-qam', 'owned evidence']);
    git(['sparse-checkout', 'init', '--cone']); git(['sparse-checkout', 'set', 'src']);
    assert.equal(fs.existsSync(path.join(directory, 'research')), false);
    assert.equal(checkGitScope({branch: 'research/example', base, run}).changed_files, 1);
    git(['sparse-checkout', 'disable']);
    git(['mv', 'src/main.js', 'research/campaigns/example/copied.js']); git(['commit', '-qm', 'rename core source']);
    git(['sparse-checkout', 'set', 'src']);
    assert.equal(fs.existsSync(path.join(directory, 'research')), false);
    assert.throws(() => checkGitScope({branch: 'research/example', base, run}), /Research changes/);
  } finally { fs.rmSync(directory, {recursive: true, force: true}); }
});


// Read the actual workflow declarations and shell bodies. These bounded controls
// model the status-expression subset used here; hosted execution remains required.
function queueWorkflow() {
  const source=fs.readFileSync(path.join(root,'.github/workflows/worker-merge.yml'),'utf8');
  const job=name=>{
    const match=source.match(new RegExp('^  '+name+':\\n([\\s\\S]*?)(?=^  [a-z][a-z_-]*:|$(?![\\s\\S]))','m'));
    assert(match,'Missing job '+name);
    const header=match[1].split('    steps:\n')[0];
    const steps=match[1].split(/\n(?=      - )/).slice(1).map(text=>{
      const name=text.match(/^      - name: (.+)$/m)?.[1];
      const condition=text.match(/^        if: (.+)$/m)?.[1];
      const runLine=text.match(/^        run: (.+)$/m);
      let run=runLine?.[1];
      if(runLine?.[1]==='|'){
        const lines=text.slice(runLine.index+runLine[0].length+1).split('\n'),body=[];
        for(const line of lines){if(line&&!line.startsWith('          '))break;body.push(line.slice(10));}
        run=body.join('\n');
      }
      return {name,condition,run,text};
    });
    return {header,condition:header.match(/^    if: (.+)$/m)?.[1],steps};
  };
  return {source,integration:job('integration')};
}
function workflowCondition(expression, context, {success=true,cancelled=false}={}) {
  if(expression&&!/\b(?:always|success|failure|cancelled)\(/.test(expression)&&!success)return false;
  return expression?Boolean(new Function('needs','github','matrix','steps','always','cancelled','success','failure',
    `return (${expression});`)(context.needs,context.github,context.matrix,context.steps??{},()=>true,()=>cancelled,()=>success,()=>!success)):success;
}
function queueContext({profile='full',selection='complete'}={}){
 return {needs:{prepare:{outputs:{profile,test_selection:selection}}},matrix:{shard:0},
   steps:{assembly:{outputs:{assembled:'false'}}}};
}
function packageStep(job,name){const found=job.steps.filter(step=>step.name===name);assert.equal(found.length,1,name);return found[0];}


test('normal package workflow closes full, shard and assembly branches without historical readback', () => {
 const {source,integration}=queueWorkflow();
 assert.equal([...source.matchAll(/^        run: npm run build:cloudflare$/gm)].length,1);
 assert.doesNotMatch(source,/WORLDATLAS_PACKAGE_PROFILE|run: npm run build:hosted/);
 assert.doesNotMatch(source,/Read back qualified native build outputs|native-normal-built-output\.json|--built-output-readback/);
 const names=['Snapshot original final-worker package inputs',
  'Build the combined application once before asset-dependent tests',
  'Inventory original final-worker package output',
  'Install browser dependencies only for tests that use Playwright',
  'Test applicable combined-tree invariants without publishing or live imports'];
 const routes=names.map(name=>packageStep(integration,name));
 assert.deepEqual(integration.steps.filter(step=>names.includes(step.name)).map(step=>step.name),names);
 const original=packageStep(integration,'Retain original final-worker package output');
 const smoke=packageStep(integration,'Retain selected delivery smoke');
 assert.match(smoke.text,/name: selected-delivery-smoke-\$\{\{ inputs\.request_id \}\}-\$\{\{ github\.run_attempt \}\}/);
 assert.match(smoke.text,/path: \.cache\/selected-delivery-smoke\.json\n/);
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'worldatlas-normal-package-route-'));
 try {
  const calls=path.join(directory,'calls.jsonl');
  const recorder=`#!${process.execPath}
const fs=require('node:fs'),path=require('node:path'),args=process.argv.slice(2);
const programme=path.basename(process.argv[1]);let call;
if(programme==='npm'&&args.join(' ')==='run build:cloudflare')call='build';
else if(programme==='npx'&&args.join(' ')==='playwright install --with-deps chromium')call='browser-install';
else if(programme==='node'){
 if(args[0]==='scripts/package-output-artifact.mjs'){
  if(args.length===1)call='inventory';else if(args.length===2&&args[1]==='--snapshot')call='snapshot';
 }else if(args.length===1&&args[0]==='scripts/run-integration-tests.mjs')call='packaged-tests';
 else if(args[0]==='--input-type=module'&&args[1]==='-e'&&args.length===3){
  if(args[2].includes('integrationNeedsBrowser('))call='browser-check';
  else if(args[2].includes('await selectedDeliverySmoke(process.env.SELECTED_EXPECTATIONS_PATH)'))call='selected-smoke';
  else if(args[2].includes('package_assembly:requireCurrentPackageAssembly()'))call='assembly-admission';
 }
}
if(!call)throw Error('Unexpected normal package command: '+programme+' '+JSON.stringify(args));
fs.appendFileSync(process.env.FIXTURE_CALLS,JSON.stringify(call)+'\\n');
`;
  for(const name of ['node','npm','npx'])fs.writeFileSync(path.join(directory,name),recorder,{mode:0o755});
  const cases=[
   {selection:'complete',assembled:undefined,shard:0,expected:['snapshot','build','inventory','browser-check','browser-install','packaged-tests'],output:true},
   {selection:'selected-data',assembled:'false',shard:0,expected:['snapshot','build','inventory','selected-smoke'],output:true},
   {selection:'selected-data',assembled:'true',shard:0,expected:['selected-smoke','assembly-admission'],output:false},
   ...[1,2].map(shard=>({selection:'complete',assembled:undefined,shard,expected:['browser-check','browser-install','packaged-tests'],output:false})),
  ];
  for(const branch of cases){
   fs.rmSync(calls,{force:true});
   const context=queueContext({selection:branch.selection});context.matrix.shard=branch.shard;
   context.steps.assembly.outputs.assembled=branch.assembled;
   const effective=branch.assembled==='true'?'selected-output':branch.selection;
   for(const step of routes.filter(step=>workflowCondition(step.condition,context))){
    const result=spawnSync('/bin/bash',['-e','-o','pipefail','-c',step.run],{cwd:directory,encoding:'utf8',
     env:{PATH:directory,WORLDATLAS_PACKAGE_PROFILE:'foreign',INTEGRATION_PROFILE:'full',INTEGRATION_SHARD:String(branch.shard),
      INTEGRATION_TEST_SELECTION:effective,SELECTED_EXPECTATIONS_PATH:'current-expectations.json',FIXTURE_CALLS:calls}});
    assert.equal(result.status,0,step.name+': '+result.stderr);
   }
   const actual=fs.readFileSync(calls,'utf8').trim().split('\n').map(JSON.parse);
   assert.deepEqual(actual,branch.expected,JSON.stringify(branch));
   assert.equal(workflowCondition(original.condition,context),branch.output);
   assert.equal(workflowCondition(original.condition,context,{success:false}),false,'Failed checks cannot upload original output');
   assert.equal(workflowCondition(smoke.condition,context),branch.shard===0);
  }
 } finally {fs.rmSync(directory,{recursive:true,force:true});}
});

test('automatic author jobs are absent while final queue keeps current consumers',()=>{
 assert.equal(fs.existsSync(path.join(root,'.github/workflows/merge-integration-checks.yml')),false);
 const queue=fs.readFileSync(path.join(root,'.github/workflows/worker-merge.yml'),'utf8');
 assert.match(queue,/run: npm run build:cloudflare/);assert.match(queue,/node scripts\/run-integration-tests.mjs/);
 assert.doesNotMatch(queue,/proof_run|proof_attempt|GEOGRAPHY_PROOF|PROOF_RUN/);
 const site=fs.readFileSync(path.join(root,'.github/workflows/deployment-budget.yml'),'utf8');
 assert.match(site,/run: npm run build:hosted/);assert.match(site,/path: \.cache\/deployment-budget.json/);
});

test('final queue uses pinned stock checkout with exact candidate and transient read-only credentials',()=>{
 const {source,integration}=queueWorkflow();
 const step=packageStep(integration,'Checkout exact candidate for application regression');
 assert.match(step.text,/uses: actions\/checkout@d23441a48e516b6c34aea4fa41551a30e30af803/);
 assert.match(step.text,/ref: \$\{\{ needs\.prepare\.outputs\.candidate \}\}/);
 assert.match(step.text,/persist-credentials: false/);assert.match(step.text,/fetch-depth: 1/);
 assert.match(step.text,/sparse-checkout-cone-mode: false/);
 assert.match(step.text,/sparse-checkout: \$\{\{ needs\.prepare\.outputs\.checkout_patterns \}\}/);
 for(const line of ['lfs: false','submodules: false','GIT_CONFIG_NOSYSTEM:', 'GIT_CONFIG_GLOBAL: /dev/null',
   'GIT_CONFIG_KEY_0: core.hooksPath','GIT_CONFIG_KEY_1: credential.helper'])assert(step.text.includes(line),line);
 assert.doesNotMatch(source,/CHECKOUT_BOOTSTRAP|checkout_bootstrap|acquire-ci-checkout|WORLDATLAS_CHECKOUT_TOKEN:/);
 assert.equal(workflowCondition(step.condition,queueContext()),true);
 assert.equal(workflowCondition(step.condition,queueContext({profile:'evidence'})),false);
 assert.equal(workflowCondition(step.condition,queueContext(),{success:false}),false);
 const verification=packageStep(integration,'Checkout complete candidate for application regression');
 assert.match(verification.text,/CI_CHECKOUT_SHA: \$\{\{ needs\.prepare\.outputs\.candidate \}\}/);
 assert.match(verification.text,/CI_CHECKOUT_TREE: \$\{\{ needs\.prepare\.outputs\.candidate_tree \}\}/);
 assert.match(verification.run,/HEAD\^\{tree\}/);assert.match(verification.run,/symbolic-ref/);
 assert.match(verification.run,/extraheader/);assert.match(verification.run,/git-credentials-/);
 assert.match(verification.run,/remote.origin.promisor/);assert.match(verification.run,/partialclonefilter/);
 const permissions=source.split('  integration:')[1].split('    permissions:')[1].split('    steps:')[0];
 assert.match(permissions,/contents: read/);assert.doesNotMatch(permissions,/: write/);
});

test('full-checkout canonical verification executes against real Git and refuses mismatched identity or retained credentials',()=>{
  const bodies=['worker-merge.yml'].flatMap(workflow=>
    [...fs.readFileSync(path.join(root,'.github/workflows',workflow),'utf8').matchAll(/python3 -I -S -B - <<'CHECKOUT_VERIFY'\n([\s\S]*?)          CHECKOUT_VERIFY/g)]
      .map(match=>match[1].split('\n').map(line=>line.slice(10)).join('\n')));
  assert.equal(bodies.length,1);assert.equal(new Set(bodies).size,1);
  for(const kind of ['valid','wrong-head','wrong-tree','attached','header','credential-helper','remote-credential','inherited-token','input-token','include','temp-credential']){
    const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-checkout-verification-'));
    try{
      const git=(...args)=>execFileSync('git',args,{cwd:directory,encoding:'utf8',stdio:['pipe','pipe','pipe']}).trim();
      git('init','-q','-b','fixture');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid');
      fs.writeFileSync(path.join(directory,'input'),'bounded metadata\n');git('add','input');git('commit','-qm','fixture');
      const sha=git('rev-parse','HEAD'),tree=git('rev-parse','HEAD^{tree}');
      if(kind!=='attached')git('checkout','--detach','-q',sha);
      git('remote','add','origin','https://github.com/ChengshuLi/WorldAtlas.git');
      if(kind==='header')git('config','http.https://github.com/.extraheader','fixture-secret-never-print');
      if(kind==='credential-helper')git('config','credential.helper','fixture-secret-never-print');
      if(kind==='include')git('config','include.path','fixture-secret-never-print');
      if(kind==='temp-credential')fs.writeFileSync(path.join(directory,'git-credentials-fixture.config'),'fixture-secret-never-print');
      if(kind==='remote-credential')git('remote','set-url','origin','https://fixture-secret-never-print@github.com/ChengshuLi/WorldAtlas.git');
      const env={...process.env,RUNNER_TEMP:directory,CI_CHECKOUT_REPOSITORY:'ChengshuLi/WorldAtlas',CI_CHECKOUT_SHA:kind==='wrong-head'?'a'.repeat(40):sha,CI_CHECKOUT_TREE:kind==='wrong-tree'?'b'.repeat(40):tree};
      for(const key of ['WORLDATLAS_CHECKOUT_TOKEN','GH_TOKEN','GITHUB_TOKEN','INPUT_TOKEN'])delete env[key];
      if(kind==='inherited-token')env.WORLDATLAS_CHECKOUT_TOKEN='fixture-secret-never-print';
      if(kind==='input-token')env.INPUT_TOKEN='fixture-secret-never-print';
      const result=spawnSync('python3',['-I','-S','-B','-c',bodies[0]],{cwd:directory,env,encoding:'utf8',timeout:10000});
      assert.equal(result.status===0,kind==='valid',kind+': '+result.stderr);assert.doesNotMatch(result.stdout+result.stderr,/fixture-secret-never-print/);
    }finally{fs.rmSync(directory,{recursive:true,force:true});}
  }
});

test('queue focused candidate supports every distinct trusted sparse checkout', () => {
  const source = fs.readFileSync(path.join(root, '.github/workflows/worker-merge.yml'), 'utf8');
  const candidate = source.match(/- name: Checkout only focused-test inputs for evidence regression[\s\S]*?sparse-checkout: \|\n((?:            .+\n)+)/);
  assert.ok(candidate, 'actual focused queue checkout must be declared');
  const directories = candidate[1].trim().split('\n').map(row => row.trim());
  // Run each distinct declared module closure once, using the focused candidate
  // as its source tree. Missing nested fixtures still fail before imports.
  const check = sourceRoot => {
    const trees = new Set();
    for (const workflow of workflows) {
      const source = fs.readFileSync(path.join(sourceRoot, '.github/workflows', workflow), 'utf8');
      const blocks = [...source.matchAll(/^          sparse-checkout: \|\n((?:            .+\n)+)/gm)];
      assert.ok(blocks.length > 0, 'expected explicit sparse checkout declarations');
      for (const block of blocks) trees.add(block[1]);
    }
    for (const tree of trees) {
      const result = probe(tree.trim().split('\n').map(row => row.trim()), {sourceRoot});
      assert.equal(result.status, 0, result.stderr);
    }
  };
  assert.doesNotThrow(() => probe(directories, {check}));
  assert.throws(() => probe(directories.filter(row => !row.includes('selected-checkpoint-reuse-20261012')),
    {check}), /ENOENT.*selected-checkpoint-reuse-20261012/);
});


for (const workflow of ['worker-merge.yml']) {
  test(`${workflow}: native geography omits polygon dependencies while general regressions retain them`, () => {
    const source=fs.readFileSync(path.join(root,'.github/workflows',workflow),'utf8');
    const geography=source.match(/^  geography:\n([\s\S]*?)(?=^  [a-zA-Z_-]+:|$(?![\s\S]))/m)?.[1];
    assert(geography);
    assert.doesNotMatch(geography,/pip install|Install trusted geographic dependencies/);
    assert.match(source,/pip install[^\n]*requirements\.txt/);
  });
}


test('focused delivery tests receive their real Node/Python runtime without an atlas build', () => {
  const {source,integration}=queueWorkflow();
  for(const command of ['npm ci --no-audit --no-fund','python -m pip install -r requirements.txt']) {
    const steps=integration.steps.filter(step=>step.text.includes('run: '+command));
    assert.equal(steps.length,1,command);
    for(const profile of ['full','evidence'])assert.equal(workflowCondition(steps[0].condition,queueContext({profile})),true);
    assert.equal(workflowCondition(steps[0].condition,queueContext({profile:'unknown'})),false);
    assert.equal(workflowCondition(steps[0].condition,queueContext({profile:'evidence'}),{success:false}),false);
  }
  const build=integration.steps.find(step=>step.run==='npm run build:cloudflare');assert(build);
  assert.equal(workflowCondition(build.condition,queueContext({profile:'evidence'})),false);
  assert.equal(workflowCondition(build.condition,queueContext({profile:'full'})),true);
  const match=source.match(/- name: Checkout only focused-test inputs for evidence regression[\s\S]*?sparse-checkout: \|\n((?:            .+\n)+)/);
  assert(match);const inputs=new Set(match[1].trim().split('\n').map(line=>line.trim()));
  for(const name of ['coordination/engineering/additive-native-gap-batch-20261008/composition-v2/compose-retained.mjs',
    'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz',
    'docs/LOCAL_WORKSPACES.md'])assert(inputs.has(name),name);
  assert(!inputs.has('research'),'no blanket scientific archive checkout');
  const checker=source.match(/- name: Checkout trusted geographic checker([\s\S]*?)(?=      - uses: actions\/setup-node)/)?.[1];
  assert(checker);assert.doesNotMatch(checker,/sparse-checkout-cone-mode: false/);
  for(const name of ['coordination/engineering/additive-native-gap-batch-20261008/composition-v2/compose-retained.mjs',
    'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz',
    'docs/LOCAL_WORKSPACES.md'])assert(!checker.includes(name),'ordinary leaves must not enter trusted cone checkout');

});

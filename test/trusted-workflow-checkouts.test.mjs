import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync, execFileSync} from 'node:child_process';
import {checkGitScope} from '../scripts/check-handoff-scope.mjs';
import {containsPackagePath,loadPackageInputs,focusedCheckoutPatterns} from '../scripts/package-inputs.mjs';

const root = path.resolve(import.meta.dirname, '..');
const workflows = ['issue-claims.yml', 'worker-merge.yml'];

// Reproduce each declared sparse tree, including cone-mode root files. Load
// trusted modules without executing workflow entrypoints or contacting GitHub.
function probe(directories, {geography = false, checkoutTests = false} = {}) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'worldatlas-checkout-'));
  try {
    fs.copyFileSync(path.join(root, 'package.json'), path.join(directory, 'package.json'));
    const paths = new Set(directories.flatMap(pattern => pattern.includes('*')
      ? fs.globSync(pattern.replace(/^\//,''),{cwd:root}) : [pattern]));
    for (const relative of paths) {
      const source = path.join(root, relative);
      const destination = path.join(directory, relative);
      fs.mkdirSync(path.dirname(destination), {recursive: true});
      fs.cpSync(source, destination, {recursive: true});
    }
    return spawnSync(process.execPath, checkoutTests ? ['--test', '--test-concurrency=1', '--test-name-pattern', 'actual sparse declarations include trusted module dependencies', 'test/trusted-workflow-checkouts.test.mjs'] : ['--input-type=module', '-e',
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

for (const workflow of workflows) {
  test(`${workflow}: actual sparse declarations include trusted module dependencies`, () => {
    const source = fs.readFileSync(path.join(root, '.github/workflows', workflow), 'utf8');
    const blocks = [...source.matchAll(/^          sparse-checkout: \|\n((?:            .+\n)+)/gm)];
    assert.ok(blocks.length > 0, 'expected explicit sparse checkout declarations');
    const checkouts=blocks.map(block=>block[1].trim().split('\n').map(row=>row.trim()))
      .filter(rows=>rows.join('\n')!=='/*\n!/*/'); // Root-only bootstrap is expanded by the tested stdin step.
    if(workflow==='worker-merge.yml')checkouts.push(focusedCheckoutPatterns(loadPackageInputs(root)).map(name=>name.replace(/^\//,'')));
    for (const directories of checkouts) {
      const result = probe(directories);
      assert.equal(result.status, 0, result.stderr);
    }
  });
}

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


test('package setup and retention follow the current build and assembly branches', () => {
 const {integration}=queueWorkflow();
 const build=packageStep(integration,'Build the combined application once before asset-dependent tests');
 assert.equal(build.run,'npm run build:cloudflare');
 const setup=['Snapshot original final-worker package inputs',build.name,'Inventory original final-worker package output']
   .map(name=>packageStep(integration,name));
 const original=packageStep(integration,'Retain original final-worker package output');
 const smoke=packageStep(integration,'Retain selected delivery smoke');
 const browser=packageStep(integration,'Install browser dependencies only for tests that use Playwright');
 // The actual queue shell is exercised in integration-profile-restoration;
 // package-output-artifact verifies immediate capture and successful-only upload.
 for(const [selection,assembled,shard] of [['complete',false,0],['selected-data',false,0],
   ['selected-data',true,0],['complete',false,1],['complete',false,2]]){
   const context=queueContext({selection});context.matrix.shard=shard;
   context.steps.assembly.outputs.assembled=String(assembled);
   const builds=shard===0&&!assembled;
   for(const step of setup)assert.equal(workflowCondition(step.condition,context),builds,step.name);
   assert.equal(workflowCondition(original.condition,context),builds);
   assert.equal(workflowCondition(original.condition,context,{success:false}),false);
   assert.equal(workflowCondition(smoke.condition,context),shard===0);
   assert.equal(workflowCondition(browser.condition,context),selection!=='selected-data');
 }
});

test('final queue uses pinned stock checkout with exact candidate and transient read-only credentials',()=>{
 const {source,integration}=queueWorkflow();
 const step=packageStep(integration,'Checkout exact candidate for application regression');
 assert.match(step.text,/uses: actions\/checkout@d23441a48e516b6c34aea4fa41551a30e30af803/);
 assert.match(step.text,/ref: \$\{\{ needs\.prepare\.outputs\.candidate \}\}/);
 assert.match(step.text,/persist-credentials: false/);assert.match(step.text,/fetch-depth: 1/);
 assert.match(step.text,/sparse-checkout-cone-mode: false/);
 assert.match(step.text,/sparse-checkout: \|\n            \/\*\n            !\/\*\//);
 for(const line of ['lfs: false','submodules: false','GIT_CONFIG_NOSYSTEM:', 'GIT_CONFIG_GLOBAL: /dev/null',
   'GIT_CONFIG_KEY_0: core.hooksPath','GIT_CONFIG_KEY_1: credential.helper'])assert(step.text.includes(line),line);
 assert.doesNotMatch(source,/CHECKOUT_BOOTSTRAP|checkout_bootstrap|acquire-ci-checkout|WORLDATLAS_CHECKOUT_TOKEN:/);
 assert.equal(workflowCondition(step.condition,queueContext()),true);
 assert.equal(workflowCondition(step.condition,queueContext({profile:'evidence'})),true);
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

test('queue focused candidate includes the inputs of its nested actual-checkout probes', () => {
  const source = fs.readFileSync(path.join(root, '.github/workflows/worker-merge.yml'), 'utf8');
  assert.match(source, /- name: Materialize exact prepared checkout inputs[\s\S]*?needs\.prepare\.outputs\.checkout_patterns_base64/);
  const directories = focusedCheckoutPatterns(loadPackageInputs(root)).map(name=>name.replace(/^\//,''));
  const definition=loadPackageInputs(root),declared=[...definition.inputs,...definition.verification_paths];
  for(const name of directories.filter(row=>row.startsWith('research/')))
    assert(containsPackagePath(declared,name)||declared.includes(name+'/'),
      'Nested research fixture must be retained by the actual full checkout: '+name);
  const result = probe(directories, {checkoutTests: true});
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const missing = probe(directories.filter(row => !row.includes('selected-checkpoint-reuse-20261012')), {checkoutTests: true});
  assert.notEqual(missing.status, 0);
  assert.match(missing.stdout + missing.stderr, /ENOENT/);
  assert.match(missing.stdout + missing.stderr, /selected-checkpoint-reuse-20261012/);
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
  assert.match(source,/- name: Materialize exact prepared checkout inputs[\s\S]*?needs\.prepare\.outputs\.checkout_patterns_base64/);
  const inputs=new Set(focusedCheckoutPatterns(loadPackageInputs(root)).map(name=>name.replace(/^\//,'')));
  for(const name of ['coordination/engineering/additive-native-gap-batch-20261008/composition-v2/compose-retained.mjs',
    'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz',
    'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json',
    'docs/LOCAL_WORKSPACES.md'])assert(inputs.has(name),name);
  assert(!inputs.has('research'),'no blanket scientific archive checkout');
  const checker=source.match(/- name: Checkout trusted geographic checker([\s\S]*?)(?=      - uses: actions\/setup-node)/)?.[1];
  assert(checker);assert.doesNotMatch(checker,/sparse-checkout-cone-mode: false/);
  for(const name of ['coordination/engineering/additive-native-gap-batch-20261008/composition-v2/compose-retained.mjs',
    'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz',
    'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json',
    'docs/LOCAL_WORKSPACES.md'])assert(!checker.includes(name),'ordinary leaves must not enter trusted cone checkout');

});

// Execute the actual runner script file: the large value must never become an
// environment entry or argv item, and decoded paths must never become shell code.
function materializationFixture(patterns) {
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-checkout-inputs-'));
  const git=(...args)=>execFileSync('git',args,{cwd:directory,encoding:'utf8',stdio:['pipe','pipe','pipe']}).trim();
  git('init','-q');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid');
  fs.writeFileSync(path.join(directory,'root-file'),'root\n');
  for(const name of ['selected/input.txt','excluded/private.txt','selected/$(touch INJECTED)','selected/quote\'"; echo nope']){
    fs.mkdirSync(path.dirname(path.join(directory,name)),{recursive:true});fs.writeFileSync(path.join(directory,name),name+'\n');
  }
  git('add','.');git('commit','-qm','fixture');
  const sha=git('rev-parse','HEAD'),tree=git('rev-parse','HEAD^{tree}');
  git('checkout','--detach','-q',sha);git('remote','add','origin','https://github.com/ChengshuLi/WorldAtlas.git');
  execFileSync('git',['sparse-checkout','set','--no-cone','--stdin'],{cwd:directory,input:'/*\n!/*/\n'});
  const {integration}=queueWorkflow(),step=packageStep(integration,'Materialize exact prepared checkout inputs');
  const env={...process.env,CI_CHECKOUT_REPOSITORY:'ChengshuLi/WorldAtlas',CI_CHECKOUT_SHA:sha,CI_CHECKOUT_TREE:tree,
    GH_TOKEN:'fixture-secret-never-print',GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_TERMINAL_PROMPT:'0',
    GIT_CONFIG_COUNT:'2',GIT_CONFIG_KEY_0:'core.hooksPath',GIT_CONFIG_VALUE_0:'/dev/null',GIT_CONFIG_KEY_1:'credential.helper',GIT_CONFIG_VALUE_1:''};
  const run=({encoded=(Buffer.from(patterns).toString('base64').match(/.{1,76}/g)??[]).join('\n'),override={}}={})=>{
    // Match Actions: expressions are resolved into a file, then bash runs that file.
    const script=path.join(directory,'.git','materialize.sh');
    fs.writeFileSync(script,step.run.replace('${{ needs.prepare.outputs.checkout_patterns_base64 }}',encoded));
    return spawnSync('bash',[script],{cwd:directory,env:{...env,...override},encoding:'utf8'});
  };
  return {directory,git,sha,tree,env,run};
}

test('both queue profiles share minimal checkout, stdin materialization and exact verification',()=>{
  const {source,integration}=queueWorkflow();
  const checkout=packageStep(integration,'Checkout exact candidate for application regression');
  const materialize=packageStep(integration,'Materialize exact prepared checkout inputs');
  const verify=packageStep(integration,'Checkout complete candidate for application regression');
  assert.equal(integration.steps.filter(step=>step.text.includes('uses: actions/checkout@')).length,1);
  assert.doesNotMatch(source,/sparse-checkout: \$\{\{|checkout_patterns<<|WORLDATLAS_CHECKOUT_PATTERNS/);
  assert.match(source,/checkout_patterns_base64: \$\{\{ steps\.prepare\.outputs\.checkout_patterns_base64 \}\}/);
  assert.match(source.split('  prepare:\n')[1].split('  geography:\n')[0],/CHECKOUT_PATTERNS_FORMAT: wrapped-base64/);
  assert.match(materialize.run,/encoded = '''\$\{\{ needs\.prepare\.outputs\.checkout_patterns_base64 \}\}'''/);
  assert.match(materialize.run,/b64decode\(encoded\.replace\('\\n', ''\), validate=True\)/);
  assert.match(materialize.run,/'sparse-checkout', 'set', '--no-cone', '--stdin'\], input=patterns, env=env, check=True/);
  assert(integration.steps.indexOf(checkout)<integration.steps.indexOf(materialize));
  assert(integration.steps.indexOf(materialize)<integration.steps.indexOf(verify));
  for(const step of [checkout,materialize,verify]){
    for(const profile of ['full','evidence'])assert.equal(workflowCondition(step.condition,queueContext({profile})),true);
    assert.equal(workflowCondition(step.condition,queueContext({profile:'unknown'})),false);
    assert.equal(workflowCondition(step.condition,queueContext(),{success:false}),false);
  }
});

test('new workflow consumes legacy single-line output from an older producer',()=>{
  const patterns='/*\n!/*/\n/selected/input.txt',f=materializationFixture(patterns);
  try {
    const result=f.run({encoded:Buffer.from(patterns).toString('base64')});
    assert.equal(result.status,0,result.stderr);
    assert.equal(fs.readFileSync(path.join(f.directory,'.git/info/sparse-checkout'),'utf8'),patterns+'\n');
  } finally {fs.rmSync(f.directory,{recursive:true,force:true});}
});

test('large prepared list reaches real Git as exact stdin bytes; hostile path text remains data',()=>{
  const rows=['/*','!/*/','/selected/input.txt','/selected/$(touch INJECTED)','/selected/quote\'"; echo nope',
    ...Array.from({length:1800},(_,i)=>`/coordination/engineering/retained-literal-input-${String(i).padStart(5,'0')}/original-products/source-contact-features.geojson.gz`),
    'CHECKOUT_INPUTS','touch INJECTED'];
  const patterns=rows.join('\n');assert(Buffer.byteLength(patterns)>150987);
  const f=materializationFixture(patterns);
  try{
    const realGit=execFileSync('which',['git'],{encoding:'utf8'}).trim();
    const bin=path.join(f.directory,'.git/probe-bin');fs.mkdirSync(bin);
    fs.writeFileSync(path.join(bin,'git'),`#!/usr/bin/env python3
import json, os, subprocess, sys
args = sys.argv[1:]
if args[:1] == ['sparse-checkout']:
    data = sys.stdin.buffer.read()
    with open('.git/stdin-probe.json', 'w') as stream:
        json.dump({'args': args, 'stdin': data.decode(), 'token_environment': 'GH_TOKEN' in os.environ,
                   'config_count': os.environ.get('GIT_CONFIG_COUNT'),
                   'auth_key': os.environ.get('GIT_CONFIG_KEY_2'),
                   'has_auth': os.environ.get('GIT_CONFIG_VALUE_2', '').startswith('AUTHORIZATION: basic ')}, stream)
    sys.exit(subprocess.run([${JSON.stringify(realGit)}, *args], input=data).returncode)
os.execv(${JSON.stringify(realGit)}, [${JSON.stringify(realGit)}, *args])
`,{mode:0o755});
    const result=f.run({override:{PATH:bin+path.delimiter+process.env.PATH}});assert.equal(result.status,0,result.stderr);
    const rendered=fs.readFileSync(path.join(f.directory,'.git/materialize.sh'),'utf8');
    const encoded=rendered.match(/encoded = '''([A-Za-z0-9+/=\n]+)'''/)[1];
    assert(encoded.split('\n').length>1&&encoded.split('\n').every(line=>line.length<=76));
    assert.equal(Buffer.from(encoded.replaceAll('\n',''),'base64').toString(),patterns);
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(f.directory,'.git/stdin-probe.json'))),{
      args:['sparse-checkout','set','--no-cone','--stdin'],stdin:patterns,token_environment:false,
      config_count:'3',auth_key:'http.https://github.com/.extraheader',has_auth:true});
    assert.doesNotMatch(result.stdout+result.stderr,/fixture-secret-never-print/);
    assert.equal(fs.readFileSync(path.join(f.directory,'.git/info/sparse-checkout'),'utf8'),patterns+'\n');
    for(const name of ['selected/input.txt','selected/$(touch INJECTED)','selected/quote\'"; echo nope'])
      assert.equal(fs.readFileSync(path.join(f.directory,name),'utf8'),name+'\n');
    assert.equal(fs.existsSync(path.join(f.directory,'excluded/private.txt')),false);
    assert.equal(fs.existsSync(path.join(f.directory,'INJECTED')),false);
    assert.equal(f.git('rev-parse','HEAD'),f.sha);assert.equal(f.git('rev-parse','HEAD^{tree}'),f.tree);
    assert.doesNotMatch(f.git('config','--local','--list'),/extraheader|fixture-secret-never-print|credential\./);
  }finally{fs.rmSync(f.directory,{recursive:true,force:true});}
});

for(const kind of ['invalid-base64','truncated-base64','foreign-whitespace','wrong-head','wrong-tree','wrong-repository','wrong-remote','header','credential-helper','include','failed-git']){
  test(`prepared checkout refuses ${kind} without successful materialization`,()=>{
    const f=materializationFixture('/*\n!/*/\n/selected/input.txt');
    try{
      const override={},options={override};
      if(kind==='invalid-base64')options.encoded='not!base64';
      if(kind==='truncated-base64')options.encoded=Buffer.from('/*\n!/*/\n/selected/input.txt').toString('base64').slice(0,-1);
      if(kind==='foreign-whitespace')options.encoded='Lyo= ';
      if(kind==='wrong-head')override.CI_CHECKOUT_SHA='a'.repeat(40);
      if(kind==='wrong-tree')override.CI_CHECKOUT_TREE='b'.repeat(40);
      if(kind==='wrong-repository')override.CI_CHECKOUT_REPOSITORY='other/repo';
      if(kind==='wrong-remote')f.git('remote','set-url','origin','https://example.invalid/other/repo');
      if(kind==='header')f.git('config','http.https://github.com/.extraheader','fixture-secret-never-print');
      if(kind==='credential-helper')f.git('config','credential.helper','fixture-secret-never-print');
      if(kind==='include')f.git('config','include.path','fixture-secret-never-print');
      if(kind==='failed-git')fs.writeFileSync(path.join(f.directory,'.git/index.lock'),'occupied');
      const result=f.run(options);assert.notEqual(result.status,0,kind);
      assert.equal(fs.existsSync(path.join(f.directory,'selected/input.txt')),false);
      assert.doesNotMatch(result.stdout+result.stderr,/fixture-secret-never-print/);
    }finally{fs.rmSync(f.directory,{recursive:true,force:true});}
  });
}

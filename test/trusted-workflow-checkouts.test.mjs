import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync, execFileSync} from 'node:child_process';
import {checkGitScope} from '../scripts/check-handoff-scope.mjs';

const root = path.resolve(import.meta.dirname, '..');
const workflows = ['issue-claims.yml', 'worker-merge.yml', 'merge-integration-checks.yml', 'queue-readiness-audit.yml', 'merge-scheduler.yml'];

// Reproduce each declared sparse tree, including cone-mode root files. Load
// trusted modules without executing workflow entrypoints or contacting GitHub.
function probe(directories, {geography = false} = {}) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'worldatlas-checkout-'));
  try {
    fs.copyFileSync(path.join(root, 'package.json'), path.join(directory, 'package.json'));
    for (const relative of directories) {
      const source = path.join(root, relative);
      const destination = path.join(directory, relative);
      fs.mkdirSync(path.dirname(destination), {recursive: true});
      fs.cpSync(source, destination, {recursive: true});
    }
    return spawnSync(process.execPath, ['--input-type=module', '-e',
      "await import('./scripts/issue-claim-contract.mjs'); await import('./scripts/premerge-evidence.mjs'); await import('./scripts/queue-readiness-audit.mjs'); await import('./scripts/merge-scheduler.mjs'); await import('./scripts/check-pr-gates.mjs');" +
      (geography ? "await import('./scripts/check-effective-geographic-regression.mjs'); await import('./coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs'); console.log('complete trusted geography closure imported');" : '')],
    {cwd: directory, encoding: 'utf8', env: {PATH: process.env.PATH}});
  } finally { fs.rmSync(directory, {recursive: true, force: true}); }
}

for (const workflow of ['worker-merge.yml', 'merge-integration-checks.yml']) {
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
    for (const block of blocks) {
      const directories = block[1].trim().split('\n').map(row => row.trim());
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


for (const [workflow, expected] of [['merge-integration-checks.yml', 2], ['worker-merge.yml', 1]]) {
  test(`${workflow}: immutable normal routes build Cloudflare and retain the separate Site gate`, () => {
    const source = fs.readFileSync(path.join(root, '.github/workflows', workflow), 'utf8');
    const routes = [...source.matchAll(/^        run: (npm run build:cloudflare)$/gm)];
    assert.equal(routes.length, expected, 'all actual package/shard routes must be covered');
    assert.doesNotMatch(source, /WORLDATLAS_PACKAGE_PROFILE|run: npm run build:hosted/);
    const site = fs.readFileSync(path.join(root, '.github/workflows/deployment-budget.yml'), 'utf8');
    assert.match(site, /run: npm run build:hosted/);
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'worldatlas-package-routing-'));
    try {
      fs.writeFileSync(path.join(directory, 'npm'), '#!/bin/sh\nprintf "%s\\n" "$*"\n', {mode: 0o755});
      for (const route of routes) {
        const result = spawnSync('/bin/bash', ['-c', route[1]], {encoding: 'utf8', env: {PATH: directory, WORLDATLAS_PACKAGE_PROFILE: 'foreign'}});
        assert.equal(result.status, 0, result.stderr);assert.equal(result.stdout.trim(), 'run build:cloudflare');
      }
    } finally { fs.rmSync(directory, {recursive: true, force: true}); }
  });
}


test('actual scope candidate sparse declaration contains cold-checkout test imports', () => {
  const source = fs.readFileSync(path.join(root, '.github/workflows/merge-integration-checks.yml'), 'utf8');
  const scope = source.split('  scope:\n')[1].split('  geography:\n')[0];
  const candidate = scope.match(/path: candidate[\s\S]*?sparse-checkout: \|\n((?:            .+\n)+)/);
  assert.ok(candidate, 'actual scope candidate checkout must be declared');
  const directories = candidate[1].trim().split('\n').map(row => row.trim());
  const qualified = probe(directories, {geography: true});
  assert.equal(qualified.status, 0, qualified.stderr);
  const missing = probe(directories.filter(row => !row.startsWith('coordination/')), {geography: true});
  assert.notEqual(missing.status, 0);assert.match(missing.stderr, /selected-geography-effective-prevention-20261009/);
});

for (const [workflow, expected] of [['merge-integration-checks.yml', 2], ['worker-merge.yml', 1]]) {
  test(`${workflow}: actual post-build readback refuses missing selected helper`, () => {
    const source = fs.readFileSync(path.join(root, '.github/workflows', workflow), 'utf8');
    const blocks = [...source.matchAll(/- name: Read back qualified native build outputs when selected\n        if: .+\n        run: \|\n((?:          .+\n)+)/g)];
    assert.equal(blocks.length, expected);
    const helper = 'coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/model-reader-call-boundary-controls.mjs';
    const base = {version: 1, method: 'native-linear-evenodd-first-owner-v1', manifest_path: 'data/base.json', sha256: '1'.repeat(64), release_id: 'fixture-release'};
    const pin = {path: 'data/pin.json', mode: '100644', bytes: 1, sha256: '2'.repeat(64)};
    for (const block of blocks) {
      const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'worldatlas-built-readback-routing-'));
      try {
        fs.mkdirSync(path.join(directory, 'data'));
        const file = path.join(directory, 'data/ownership-selection.json'), calls = path.join(directory, 'calls.jsonl');
        const invoke = env => spawnSync('/bin/bash', ['-e', '-o', 'pipefail', '-c', block[1].split('\n').map(row => row.slice(10)).join('\n')], {
          cwd: directory, encoding: 'utf8', env: {PATH: path.dirname(process.execPath) + ':/usr/bin:/bin', ...env}
        });
        fs.writeFileSync(file, JSON.stringify(base));
        let result = invoke();assert.equal(result.status, 0, result.stderr);assert.equal(fs.existsSync(calls), false);assert.match(result.stdout, /no report claimed/);
        fs.writeFileSync(file, JSON.stringify({...base, artifact_consumption: {certificate: pin, review: pin}}));
        result = invoke();assert.equal(result.status, 1);assert.equal(fs.existsSync(calls), false);assert.match(result.stderr, /helper is missing/);
        fs.mkdirSync(path.dirname(path.join(directory, helper)), {recursive: true});
        fs.writeFileSync(path.join(directory, helper), `import fs from 'node:fs'; fs.appendFileSync('calls.jsonl',JSON.stringify(process.argv.slice(2))+'\n'); process.exit(Number(process.env.FIXTURE_HELPER_EXIT||0));`.replace("+'\n'", "+'\\n'"));
        result = invoke();assert.equal(result.status, 0, result.stderr);
        assert.deepEqual(JSON.parse(fs.readFileSync(calls, 'utf8')), ['--built-output-readback', '.cache/native-normal-built-output.json']);
        fs.unlinkSync(calls);result = invoke({FIXTURE_HELPER_EXIT: '23'});assert.equal(result.status, 23);fs.unlinkSync(calls);
        for (const value of ['{malformed', JSON.stringify({...base, artifact_consumption: null}), JSON.stringify({...base, artifact_consumption: {certificate: {...pin, bytes: 33554433}, review: pin}})]) {
          fs.writeFileSync(file, value);result = invoke();assert.notEqual(result.status, 0);assert.equal(fs.existsSync(calls), false);
        }
        fs.unlinkSync(file);result = invoke();assert.notEqual(result.status, 0);assert.equal(fs.existsSync(calls), false);
      } finally { fs.rmSync(directory, {recursive: true, force: true}); }
    }
    assert.match(source, /path: (?:\|\n[\s\S]*?)?[^\n]*\.cache\/native-normal-built-output\.json/);
  });
}

// Read the actual workflow declarations and shell bodies. These bounded controls
// model the status-expression subset used here; hosted execution remains required.
function packageWorkflow() {
  const source=fs.readFileSync(path.join(root,'.github/workflows/merge-integration-checks.yml'),'utf8');
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
  return {source,regression:job('regression'),package:job('package')};
}
function workflowCondition(expression, context, {success=true,cancelled=false}={}) {
  if(expression&&!/\b(?:always|success|failure|cancelled)\(/.test(expression)&&!success)return false;
  return expression?Boolean(new Function('needs','github','matrix','always','cancelled','success','failure',
    `return (${expression});`)(context.needs,context.github,context.matrix,()=>true,()=>cancelled,()=>success,()=>!success)):success;
}
function packageContext({profile='full',selection='complete',full='true',action='synchronize',result='success'}={}) {
  return {needs:{profile:{result:'success',outputs:{profile,test_selection:selection,full,blocked:'false'}},regression:{result}},
    github:{event:{action}},matrix:{shard:0}};
}
function packageStep(job,name){const found=job.steps.filter(step=>step.name===name);assert.equal(found.length,1,name);return found[0];}

test('full PR co-locates actual package work on shard zero without changing the complete inventory',()=>{
  const w=packageWorkflow(),ctx=packageContext();
  assert.match(w.package.header,/needs: \[profile, regression\]/);
  assert.match(w.regression.header,/needs: profile/);
  assert.doesNotMatch(w.regression.header,/needs:.*package/);
  const controls='node --test test/deployment-budget.test.mjs test/deployment-budget-scope.test.mjs test/package-inputs.test.mjs test/package-build.test.mjs';
  assert.equal(packageStep(w.regression,'Verify full-regression package controls').run,controls);
  assert.equal(packageStep(w.package,'Verify package controls').run,controls);
  assert.equal(packageStep(w.regression,'Build hosted assets').run,'npm run build:cloudflare');
  assert.equal(packageStep(w.regression,'Complete regression shard').run,'node scripts/run-integration-tests.mjs');
  assert.match(w.regression.steps.find(step=>step.name==='Checkout reviewed head').text,/ref: \$\{\{ github.event.pull_request.head.sha \}\}/);
  for(const full of ['true','false'])for(const shard of [0,1,2]){
    ctx.needs.profile.outputs.full=full;ctx.matrix.shard=shard;
    const producer=['Verify full-regression package controls','Build hosted assets','Read back qualified native build outputs when selected',
      'Verify full-regression package receipt','Retain full-regression package receipt'];
    for(const name of producer)assert.equal(workflowCondition(packageStep(w.regression,name).condition,ctx),shard===0,name);
    assert.equal(workflowCondition(packageStep(w.regression,'Complete regression shard').condition,ctx),true);
    assert.equal(w.package.steps.filter(step=>step.run==='npm run build:cloudflare'&&workflowCondition(step.condition,ctx)).length,0);
    for(const name of ['Checkout complete package inputs','Install package Node dependencies','Install package Python dependencies','Verify package controls'])
      assert.equal(workflowCondition(packageStep(w.package,name).condition,ctx),false,name);
    assert.equal(workflowCondition(packageStep(w.package,'Retain declared input build receipt').condition,ctx),false);
  }
  const receipt=packageStep(w.regression,'Retain full-regression package receipt');
  assert.match(receipt.text,/name: package-input-build\n/);assert.match(receipt.text,/path: \|\n            \.cache\/package-input-build.json\n/);
  assert.match(receipt.text,/if-no-files-found: error/);
  assert(w.regression.steps.indexOf(packageStep(w.regression,'Verify full-regression package controls'))<w.regression.steps.indexOf(packageStep(w.regression,'Build hosted assets')));
  assert(w.regression.steps.indexOf(packageStep(w.regression,'Read back qualified native build outputs when selected'))<w.regression.steps.indexOf(packageStep(w.regression,'Verify full-regression package receipt')));
  assert(w.regression.steps.indexOf(packageStep(w.regression,'Complete regression shard'))<w.regression.steps.indexOf(packageStep(w.regression,'Verify full-regression package receipt')),'validate the bytes actually retained after tests');
});

test('selected-data skipped regression still executes every existing real package consumer',()=>{
  const w=packageWorkflow(),ctx=packageContext({selection:'selected-data',result:'skipped'});
  assert.equal(workflowCondition(w.regression.condition,ctx),false);
  assert.equal(workflowCondition(w.package.condition,ctx,{success:false}),true,'explicit status condition permits intentional dependency skip');
  assert.equal(workflowCondition(packageStep(w.package,'Use full-regression package verification').condition,ctx),false);
  for(const name of ['Checkout complete package inputs','Install package Node dependencies','Install package Python dependencies','Verify package controls',
    'Build Cloudflare package without publishing','Read back qualified native build outputs when selected','Install selected-data browser dependencies','Run selected-data consumer checks'])
    assert.equal(workflowCondition(packageStep(w.package,name).condition,ctx),true,name);
  const consumer=packageStep(w.package,'Run selected-data consumer checks');
  assert.match(consumer.text,/INTEGRATION_TEST_SELECTION: selected-data/);
  assert.match(consumer.run,/selectedDeliverySmoke/);assert.match(consumer.run,/node scripts\/run-integration-tests.mjs/);
  assert.equal(w.package.steps.filter(step=>step.run==='npm run build:cloudflare'&&workflowCondition(step.condition,ctx)).length,1);
  assert.equal(workflowCondition(packageStep(w.package,'Retain declared input build receipt').condition,ctx),true);
});

test('evidence applicability and metadata/cancelled/failed dependency semantics stay fail-closed',()=>{
  const w=packageWorkflow();
  for(const full of ['true','false']){
    const ctx=packageContext({profile:'evidence',full});
    assert.equal(workflowCondition(w.package.condition,ctx),true);
    assert.equal(workflowCondition(packageStep(w.package,'Build Cloudflare package without publishing').condition,ctx),full==='true');
    assert.equal(workflowCondition(packageStep(w.package,'Use full-regression package verification').condition,ctx),false);
  }
  for(const action of ['edited','ready_for_review'])for(const selection of ['complete','selected-data']){
    const ctx=packageContext({action,selection});
    assert.equal(workflowCondition(w.regression.condition,ctx),false);assert.equal(workflowCondition(w.package.condition,ctx),false);
  }
  for(const profileResult of ['failure','cancelled','skipped']){
    const ctx=packageContext();ctx.needs.profile.result=profileResult;
    assert.equal(workflowCondition(w.package.condition,ctx,{success:false}),false);
  }
  assert.equal(workflowCondition(w.package.condition,packageContext(),{cancelled:true}),false);
  const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-package-gate-'));
  try{
    const gate=packageStep(w.package,'Use full-regression package verification');
    for(const result of ['success','failure','cancelled','skipped','']){
      const ctx=packageContext({result});
      assert.equal(workflowCondition(w.package.condition,ctx,{success:result==='success'}),true);
      const run=spawnSync('/bin/bash',['-e','-c',gate.run],{cwd:tmp,encoding:'utf8',env:{PATH:process.env.PATH,REGRESSION_RESULT:result,GITHUB_STEP_SUMMARY:path.join(tmp,'summary')}});
      assert.equal(run.status===0,result==='success',result);
    }
    assert.equal(fs.readFileSync(path.join(tmp,'summary'),'utf8').trim().split('\n').length,1,'only a successful dependency may report reuse');
  }finally{fs.rmSync(tmp,{recursive:true});}
});

test('actual package receipt command refuses missing, stale, failed, changed or nonordinary producer bytes',()=>{
  const w=packageWorkflow(),body=packageStep(w.regression,'Verify full-regression package receipt').run,head='a'.repeat(40);
  const cases=['valid','no-native-selection','missing-receipt','stale-head','failed-preflight','preflight-errors','wrong-kind','changed-definition','missing-native','stale-native','symlink','bad-head'];
  for(const kind of cases){
    const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-package-receipt-'));
    try{
      for(const dir of ['.cache','.github','data'])fs.mkdirSync(path.join(tmp,dir));
      const definition='{"version":1}\n';fs.writeFileSync(path.join(tmp,'.github/package-inputs.json'),definition);
      const hash=execFileSync(process.execPath,['--input-type=module','-e',"import {createHash} from 'node:crypto';process.stdout.write(createHash('sha256').update(process.argv[1]).digest('hex'));",definition],{encoding:'utf8'});
      const receipt={version:1,kind:'cloudflare',input_definition_sha256:hash,preflight:{passed:true,errors:[],inputs:{head}}};
      const native={version:1,kind:'ordinary-cloudflare-built-output-readback',head};
      if(kind==='stale-head')receipt.preflight.inputs.head='b'.repeat(40);
      if(kind==='failed-preflight')receipt.preflight.passed=false;
      if(kind==='preflight-errors')receipt.preflight.errors=['missing input'];
      if(kind==='wrong-kind')receipt.kind='hosted';
      if(kind==='changed-definition')receipt.input_definition_sha256='b'.repeat(64);
      if(kind==='stale-native')native.head='b'.repeat(40);
      const receiptPath=path.join(tmp,'.cache/package-input-build.json');
      if(kind!=='missing-receipt')fs.writeFileSync(receiptPath,JSON.stringify(receipt));
      if(kind==='symlink'){fs.renameSync(receiptPath,receiptPath+'.original');fs.symlinkSync(receiptPath+'.original',receiptPath);}
      fs.writeFileSync(path.join(tmp,'data/ownership-selection.json'),JSON.stringify(kind==='no-native-selection'?{}:{artifact_consumption:{}}));
      if(!['missing-native','no-native-selection'].includes(kind))fs.writeFileSync(path.join(tmp,'.cache/native-normal-built-output.json'),JSON.stringify(native));
      const run=spawnSync('/bin/bash',['-e','-c',body],{cwd:tmp,encoding:'utf8',env:{PATH:path.dirname(process.execPath)+':/usr/bin:/bin',PACKAGE_REVIEWED_HEAD:kind==='bad-head'?'':head}});
      assert.equal(run.status===0,['valid','no-native-selection'].includes(kind),kind+': '+run.stderr);
    }finally{fs.rmSync(tmp,{recursive:true});}
  }
});

test('Cloudflare label and artifacts do not claim the separate Sites reserve measurement',()=>{
  const w=packageWorkflow(),site=fs.readFileSync(path.join(root,'.github/workflows/deployment-budget.yml'),'utf8');
  assert.doesNotMatch(w.package.steps.map(step=>step.name).join('\n'),/enforce archive\/file reserves|Retain exact file and archive accounting/);
  assert.doesNotMatch(w.source,/path: \.cache\/deployment-budget.json/);
  assert.equal(packageStep(w.package,'Build Cloudflare package without publishing').run,'npm run build:cloudflare');
  assert.match(site,/run: npm run build:hosted/);assert.match(site,/path: \.cache\/deployment-budget.json/);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync, execFileSync} from 'node:child_process';
import {checkGitScope} from '../scripts/check-handoff-scope.mjs';
import {createHash} from 'node:crypto';

const root = path.resolve(import.meta.dirname, '..');
const workflows = ['issue-claims.yml', 'worker-merge.yml', 'merge-integration-checks.yml'];

// Reproduce each declared sparse tree, including cone-mode root files. Load
// trusted modules without executing workflow entrypoints or contacting GitHub.
function probe(directories, {geography = false, checkoutTests = false} = {}) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'worldatlas-checkout-'));
  try {
    fs.copyFileSync(path.join(root, 'package.json'), path.join(directory, 'package.json'));
    for (const relative of directories) {
      const source = path.join(root, relative);
      const destination = path.join(directory, relative);
      fs.mkdirSync(path.dirname(destination), {recursive: true});
      fs.cpSync(source, destination, {recursive: true});
    }
    return spawnSync(process.execPath, checkoutTests ? ['--test', '--test-concurrency=1', '--test-name-pattern', 'actual sparse declarations include trusted module dependencies', 'test/trusted-workflow-checkouts.test.mjs'] : ['--input-type=module', '-e',
      "await import('./scripts/issue-claim-contract.mjs'); await import('./scripts/research-import-gate.mjs'); await import('./scripts/premerge-evidence.mjs'); await import('./scripts/check-pr-gates.mjs');" +
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


for (const [workflow, expected] of [['worker-merge.yml', 1]]) {
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

test('scope candidate includes the inputs of its nested actual-checkout probes', () => {
  const source = fs.readFileSync(path.join(root, '.github/workflows/merge-integration-checks.yml'), 'utf8');
  const scope = source.split('  scope:\n')[1].split('  geography:\n')[0];
  const candidate = scope.match(/path: candidate[\s\S]*?sparse-checkout: \|\n((?:            .+\n)+)/);
  assert.ok(candidate);
  const directories = candidate[1].trim().split('\n').map(row => row.trim());
  const result = probe(directories, {checkoutTests: true});
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const missing = probe(directories.filter(row => !row.includes('selected-checkpoint-reuse-20261012')), {checkoutTests: true});
  assert.notEqual(missing.status, 0);
  assert.match(missing.stdout + missing.stderr, /ENOENT/);
  assert.match(missing.stdout + missing.stderr, /selected-checkpoint-reuse-20261012/);
});

for (const [workflow, expected] of [['worker-merge.yml', 1]]) {
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

test('automatic author compute is absent while final queue and explicit rollout keep current consumers',()=>{
 const author=fs.readFileSync(path.join(root,'.github/workflows/merge-integration-checks.yml'),'utf8');
 assert.deepEqual([...author.matchAll(/^  ([a-z]+):$/gm)].map(m=>m[1]),['profile','evidence','scope']);
 assert.doesNotMatch(author,/npm ci|pip install|playwright|build:cloudflare|native-built-output|package-input-build/);
 const queue=fs.readFileSync(path.join(root,'.github/workflows/worker-merge.yml'),'utf8');
 assert.match(queue,/run: npm run build:cloudflare/);assert.match(queue,/node scripts\/run-integration-tests.mjs/);
 assert.doesNotMatch(queue,/proof_run|proof_attempt|GEOGRAPHY_PROOF|PROOF_RUN/);
 const explicit=fs.readFileSync(path.join(root,'.github/workflows/selected-package-proof.yml'),'utf8');
 assert.match(explicit,/npx playwright install --with-deps chromium/);
 assert.match(explicit,/INTEGRATION_TEST_SELECTION: selected-output/);assert.match(explicit,/node scripts\/run-integration-tests.mjs/);
 const site=fs.readFileSync(path.join(root,'.github/workflows/deployment-budget.yml'),'utf8');
 assert.match(site,/run: npm run build:hosted/);assert.match(site,/path: \.cache\/deployment-budget.json/);
});

function checkoutBootstrapBodies() {
  return ['merge-integration-checks.yml','worker-merge.yml'].flatMap(workflow => {
    const source=fs.readFileSync(path.join(root,'.github/workflows',workflow),'utf8');
    return [...source.matchAll(/python3 -I -S -B - <<'CHECKOUT_BOOTSTRAP'\n([\s\S]*?)          CHECKOUT_BOOTSTRAP/g)]
      .map(match=>({workflow,body:match[1].split('\n').map(line=>line.slice(10)).join('\n')}));
  });
}
function checkoutBootstrapFixture({absence=false,helperMode='100644'}={}) {
  const object=(kind,raw)=>createHash('sha1').update(Buffer.from(kind+' '+raw.length+'\0')).update(raw).digest('hex');
  const raw=Buffer.from("print('authenticated baseline helper')\n"),helper=object('blob',raw),repo='ChengshuLi/WorldAtlas';
  const base='a'.repeat(40),sha='b'.repeat(40),candidateTree='c'.repeat(40),routes={};
  const entry=(path,mode,type,sha)=>({path,mode,type,sha});
  const makeTree=rows=>{
    const sorted=[...rows].sort((a,b)=>Buffer.compare(Buffer.from(a.path+(a.type==='tree'?'/':'\0')),Buffer.from(b.path+(b.type==='tree'?'/':'\0'))));
    const raw=Buffer.concat(sorted.map(row=>Buffer.concat([Buffer.from(row.mode.replace(/^0+/,'')+' '+row.path+'\0'),Buffer.from(row.sha,'hex')])));
    const hash=object('tree',raw);routes['/git/trees/'+hash]={sha:hash,truncated:false,tree:rows};return hash;
  };
  const scripts=makeTree([entry('a.py','100644','blob','1'.repeat(40)),...(absence?[]:[entry('acquire-ci-checkout.py',helperMode,'blob',helper)]),entry('é.py','100644','blob','2'.repeat(40))]);
  // Directory ordering uses a slash, and raw tree mode drops API's leading zero.
  const baseTree=makeTree([entry('scripts','040000','tree',scripts),entry('scripts.txt','100644','blob','3'.repeat(40)),entry('submodule','160000','commit','4'.repeat(40))]);
  routes['/pulls/17']={number:17,state:'open',base:{sha:base,ref:'main',repo:{full_name:repo}},head:{sha,ref:'engineering/fixture',repo:{full_name:repo}}};
  routes['/git/commits/'+base]={sha:base,tree:{sha:baseTree}};routes['/git/commits/'+sha]={sha,tree:{sha:candidateTree}};
  routes['/git/blobs/'+helper]={sha:helper,size:raw.length,encoding:'base64',content:raw.toString('base64')+'\n'};
  return {routes,raw,helper,base,sha,baseTree,scripts,candidateTree,repo};
}
function runCheckoutBootstrap(body,fixture,{queue=false,failure='',failureRoute='',rawRoute='',rawResponse='',symlinkTemp=false}={}) {
  const temporary=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'atlas-checkout-bootstrap-')));
  try {
    const runner=path.join(temporary,'runner');fs.mkdirSync(runner);
    const temp=symlinkTemp?path.join(temporary,'runner-link'):runner;if(symlinkTemp)fs.symlinkSync(runner,temp);
    const source=path.join(temporary,'bootstrap.py'),input=path.join(temporary,'fixture.json'),output=path.join(temporary,'output'),trace=path.join(temporary,'trace.json');
    fs.writeFileSync(source,body);fs.writeFileSync(input,JSON.stringify({...fixture,failure,failureRoute,rawRoute,rawResponse}));
    const wrapper=`import io,json,os,sys,urllib.request,urllib.error,signal,time,threading,http.server,socketserver
fixture=json.load(open(sys.argv[2])); calls=[]; servers=[]
real_open=urllib.request.build_opener().open
if fixture['failure']=='trickle':
 original_timer=signal.setitimer
 def bounded_timer(which,seconds):
  assert seconds in (0,60)
  return original_timer(which,0.25 if seconds else 0)
 signal.setitimer=bounded_timer
class Trickle(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_GET(self):
  self.send_response(200); self.send_header('Content-Length','100000'); self.end_headers()
  try:
   while True:
    self.wfile.write(b' '); self.wfile.flush(); calls.append('trickle-chunk'); time.sleep(0.04)
  except (BrokenPipeError,ConnectionResetError): pass
class TrickleServer(http.server.ThreadingHTTPServer):
 daemon_threads=True
 block_on_close=False
 def server_bind(self):
  socketserver.TCPServer.server_bind(self); self.server_name='fixture'; self.server_port=self.server_address[1]
class Response:
 status=200
 def __init__(self,raw): self.body=io.BytesIO(raw)
 def __enter__(self): return self
 def __exit__(self,*args): pass
 def read(self,limit): return self.body.read(limit)
class Opener:
 def open(self,request,timeout):
  assert request.full_url.startswith('https://api.github.com/repos/ChengshuLi/WorldAtlas/')
  assert request.get_header('Authorization')=='Bearer fixture-secret-never-print'
  assert 0 < timeout <= 20
  route=request.full_url.split('/WorldAtlas',1)[1]; calls.append(route)
  if route==fixture['failureRoute']:
   if fixture['failure']=='trickle':
    server=TrickleServer(('127.0.0.1',0),Trickle); servers.append(server)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    return real_open('http://127.0.0.1:'+str(server.server_port)+'/',timeout=20)
   if fixture['failure']=='timeout': raise TimeoutError('fixture-secret-never-print')
   raise urllib.error.HTTPError(request.full_url,int(fixture['failure']),'fixture-secret-never-print',None,None)
  raw=fixture['rawResponse'].encode() if route==fixture['rawRoute'] else json.dumps(fixture['routes'][route]).encode()
  return Response(raw)
urllib.request.build_opener=lambda *handlers: Opener()
try: exec(compile(open(sys.argv[1]).read(),sys.argv[1],'exec'),{'__name__':'__main__'})
finally:
 for server in servers: server.server_close()
 json.dump(calls,open(sys.argv[3],'w'))
`;
    const result=spawnSync('python3',['-I','-S','-B','-c',wrapper,source,input,trace],{encoding:'utf8',timeout:10000,
      env:{...process.env,WORLDATLAS_CHECKOUT_TOKEN:'fixture-secret-never-print',CI_CHECKOUT_REPOSITORY:fixture.repo,
        CI_CHECKOUT_BASE:fixture.base,CI_CHECKOUT_SHA:fixture.sha,CI_CHECKOUT_PR:queue?'':'17',CI_CHECKOUT_HEAD_REF:'engineering/fixture',RUNNER_TEMP:temp,GITHUB_OUTPUT:output}});
    const outputs=Object.fromEntries((fs.existsSync(output)?fs.readFileSync(output,'utf8'):'').trim().split('\n').filter(Boolean).map(row=>{const split=row.indexOf('=');return[row.slice(0,split),row.slice(split+1)];}));
    const materialized=outputs.helper?fs.readFileSync(outputs.helper):null;
    assert.doesNotMatch(result.stdout+result.stderr,/fixture-secret-never-print/,'failures must not log credentials');
    return {...result,outputs,materialized,calls:fs.existsSync(trace)?JSON.parse(fs.readFileSync(trace)):[]};
  } finally {fs.rmSync(temporary,{recursive:true,force:true});}
}

test('full-checkout inline bootstrap authenticates base trees and helper bytes before exposing immutable candidate identity',()=>{
  const bodies=checkoutBootstrapBodies();assert.equal(bodies.length,1);
  assert.equal(bodies[0].workflow,'worker-merge.yml','Only final-candidate acquisition remains');
  for(const {body,workflow} of bodies){
    const f=checkoutBootstrapFixture(),result=runCheckoutBootstrap(body,f,{queue:workflow==='worker-merge.yml'});
    assert.equal(result.status,0,result.stderr);assert.equal(result.outputs.mode,'helper');
    assert.equal(result.outputs.sha,f.sha);assert.equal(result.outputs.tree,f.candidateTree);assert.deepEqual(result.materialized,f.raw);
    assert.ok(Number(result.outputs.elapsed)>=0&&Number(result.outputs.elapsed)<60);
    assert.equal(result.calls.includes('/pulls/17'),workflow!=='worker-merge.yml');
    assert.deepEqual(result.calls.filter(route=>route.startsWith('/git/blobs/')),['/git/blobs/'+f.helper]);
    assert.match(body,/signal.setitimer\(signal.ITIMER_REAL, 60\)/);assert.match(body,/consumed <= 8 \* 1024 \* 1024/);
    assert(body.indexOf('os.fsync(output.fileno())')<body.indexOf('elapsed = time.monotonic() - started'));
  }
});

test('full-checkout inline bootstrap permits legacy only after positively verified ordinary tree absence',()=>{
  for(const {body} of checkoutBootstrapBodies()){
    const f=checkoutBootstrapFixture({absence:true}),result=runCheckoutBootstrap(body,f);
    assert.equal(result.status,0,result.stderr);assert.equal(result.outputs.mode,'legacy');assert.equal(result.materialized,null);
    assert.equal(result.calls.some(route=>route.startsWith('/git/blobs/')),false);
  }
});

test('full-checkout inline bootstrap refuses authentication, completeness, identity and transport errors without fallback',()=>{
  const body=checkoutBootstrapBodies()[0].body;
  for(const kind of ['base-ref','base-repo','head-ref','head-drift','commit-sha','candidate-tree','tree-hash','truncated','helper-mode','blob-sha','blob-size','blob-hash','malformed','oversized','404','401','timeout','symlink-temp']){
    const f=checkoutBootstrapFixture({helperMode:kind==='helper-mode'?'120000':'100644'}),options={};
    if(kind==='base-ref')f.routes['/pulls/17'].base.ref='other';
    if(kind==='base-repo')f.routes['/pulls/17'].base.repo.full_name='foreign/repo';
    if(kind==='head-ref')f.routes['/pulls/17'].head.ref='engineering/foreign';
    if(kind==='head-drift')f.routes['/pulls/17'].head.sha='d'.repeat(40);
    if(kind==='commit-sha')f.routes['/git/commits/'+f.base].sha='d'.repeat(40);
    if(kind==='candidate-tree')f.routes['/git/commits/'+f.sha].tree.sha='not-a-tree';
    if(kind==='tree-hash')f.routes['/git/trees/'+f.scripts].tree=f.routes['/git/trees/'+f.scripts].tree.filter(row=>row.path!=='acquire-ci-checkout.py');
    if(kind==='truncated')f.routes['/git/trees/'+f.scripts].truncated=true;
    if(kind==='blob-sha')f.routes['/git/blobs/'+f.helper].sha='d'.repeat(40);
    if(kind==='blob-size')f.routes['/git/blobs/'+f.helper].size++;
    if(kind==='blob-hash')f.routes['/git/blobs/'+f.helper].content=Buffer.from('x'.repeat(f.raw.length)).toString('base64');
    if(['malformed','oversized'].includes(kind)){options.rawRoute='/git/trees/'+f.scripts;options.rawResponse=kind==='malformed'?'{bad':'x'.repeat(2*1024*1024+1);}
    if(['404','401','timeout'].includes(kind)){options.failureRoute='/git/blobs/'+f.helper;options.failure=kind;}
    if(kind==='symlink-temp')options.symlinkTemp=true;
    const result=runCheckoutBootstrap(body,f,options);assert.notEqual(result.status,0,kind);assert.equal(result.outputs.mode,undefined,kind);
    assert.match(result.stderr,/no legacy fallback authorized/,kind);
  }
});

test('final queue retains one canonical verification and acquisition-only credentials',()=>{
 const job=queueWorkflow().integration;
 for(const mode of ['helper','legacy']){
  const ctx=queueContext();ctx.steps.checkout_bootstrap={outputs:{mode}};
  const canonical='Checkout complete candidate for application regression';
  assert.equal(job.steps.filter(step=>step.name===canonical&&workflowCondition(step.condition,ctx)).length,1);
  const helper=packageStep(job,'Acquire full checkout with authenticated bounded helper');
  const legacy=packageStep(job,'Legacy full checkout only for proven trusted-helper absence');
  assert.equal(workflowCondition(helper.condition,ctx),mode==='helper');assert.equal(workflowCondition(legacy.condition,ctx),mode==='legacy');
  for(const step of [helper,legacy,...job.steps.filter(step=>step.name===canonical)])assert.equal(workflowCondition(step.condition,ctx,{success:false}),false);
  const tokens=job.steps.filter(step=>/WORLDATLAS_CHECKOUT_TOKEN:/.test(step.text));assert.equal(tokens.length,2);
  for(const step of tokens)assert.ok(['Authenticate trusted full-checkout bootstrap','Acquire full checkout with authenticated bounded helper'].includes(step.name));
  const verify=packageStep(job,canonical);
  assert.match(verify.run,/HEAD\^\{tree\}/);assert.match(verify.run,/symbolic-ref/);assert.match(verify.run,/extraheader/);assert.doesNotMatch(verify.text,/WORLDATLAS_CHECKOUT_TOKEN:/);
 }
});

test('final queue keeps complete software sparse selection without importing source-only namespaces',()=>{
 const acquire=packageStep(queueWorkflow().integration,'Acquire full checkout with authenticated bounded helper');
 assert.match(acquire.text,/INTEGRATION_PROFILE: \$\{\{ needs\.prepare\.outputs\.profile \}\}/);
 assert.match(acquire.text,/INTEGRATION_TEST_SELECTION: \$\{\{ needs\.prepare\.outputs\.test_selection \}\}/);
 assert.doesNotMatch(acquire.run,/--(?:total-timeout|elapsed)-seconds/);
 assert.match(fs.readFileSync(path.join(root,'.github/workflows/worker-merge.yml'),'utf8'),/integration:[\s\S]*?timeout-minutes: 35/);
 const definition=JSON.parse(fs.readFileSync(path.join(root,'.github/package-inputs.json'),'utf8'));
 for(const name of [...definition.inputs,...definition.verification_paths])assert.ok(!['data/regional-review/','research/campaigns/'].some(prefix=>name===prefix.slice(0,-1)||name.startsWith(prefix)||prefix.startsWith(name)),name);
});

test('full-checkout bootstrap accepts live main movement while authenticating only the original frozen helper base',()=>{
  for(const {body} of checkoutBootstrapBodies()){
    const f=checkoutBootstrapFixture();f.routes['/pulls/17'].base.sha='d'.repeat(40);
    const result=runCheckoutBootstrap(body,f);
    assert.equal(result.status,0,result.stderr);assert.equal(result.outputs.mode,'helper');
    assert.deepEqual(result.materialized,f.raw);assert.ok(result.calls.includes('/git/commits/'+f.base));
    assert.equal(result.calls.includes('/git/commits/'+'d'.repeat(40)),false);
  }
});

test('full-checkout canonical verification executes against real Git and refuses mismatched identity or retained credentials',()=>{
  const bodies=['merge-integration-checks.yml','worker-merge.yml'].flatMap(workflow=>
    [...fs.readFileSync(path.join(root,'.github/workflows',workflow),'utf8').matchAll(/python3 -I -S -B - <<'CHECKOUT_VERIFY'\n([\s\S]*?)          CHECKOUT_VERIFY/g)]
      .map(match=>match[1].split('\n').map(line=>line.slice(10)).join('\n')));
  assert.equal(bodies.length,1);assert.equal(new Set(bodies).size,1);
  for(const kind of ['valid','wrong-head','wrong-tree','attached','header','credential-helper','remote-credential','inherited-token']){
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
      if(kind==='remote-credential')git('remote','set-url','origin','https://fixture-secret-never-print@github.com/ChengshuLi/WorldAtlas.git');
      const env={...process.env,CI_CHECKOUT_REPOSITORY:'ChengshuLi/WorldAtlas',CI_CHECKOUT_SHA:kind==='wrong-head'?'a'.repeat(40):sha,CI_CHECKOUT_TREE:kind==='wrong-tree'?'b'.repeat(40):tree};
      for(const key of ['WORLDATLAS_CHECKOUT_TOKEN','GH_TOKEN','GITHUB_TOKEN'])delete env[key];
      if(kind==='inherited-token')env.WORLDATLAS_CHECKOUT_TOKEN='fixture-secret-never-print';
      const result=spawnSync('python3',['-I','-S','-B','-c',bodies[0]],{cwd:directory,env,encoding:'utf8',timeout:10000});
      assert.equal(result.status===0,kind==='valid',kind+': '+result.stderr);assert.doesNotMatch(result.stdout+result.stderr,/fixture-secret-never-print/);
    }finally{fs.rmSync(directory,{recursive:true,force:true});}
  }
});

test('full-checkout bootstrap real wall alarm interrupts a continuously trickling HTTP body',()=>{
  const f=checkoutBootstrapFixture(),started=Date.now();
  const result=runCheckoutBootstrap(checkoutBootstrapBodies()[0].body,f,{failure:'trickle',failureRoute:'/git/blobs/'+f.helper});
  assert.notEqual(result.status,0);assert.match(result.stderr,/no legacy fallback authorized/);
  assert.equal(result.outputs.mode,undefined);assert.ok(result.calls.filter(value=>value==='trickle-chunk').length>=2);
  assert.ok(Date.now()-started<3000,'real SIGALRM interrupts socket read despite continuous incoming bytes');
});

test('queue focused candidate includes the inputs of its nested actual-checkout probes', () => {
  const source = fs.readFileSync(path.join(root, '.github/workflows/worker-merge.yml'), 'utf8');
  const candidate = source.match(/- name: Checkout only focused-test inputs for evidence regression[\s\S]*?sparse-checkout: \|\n((?:            .+\n)+)/);
  assert.ok(candidate, 'actual focused queue checkout must be declared');
  const directories = candidate[1].trim().split('\n').map(row => row.trim());
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

import fs from 'node:fs';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawn, spawnSync} from 'node:child_process';
import {compileHostedMigrations} from './compile-hosted-migrations.mjs';
import {observeSetupPhase,measuredGitSetup} from './ci-setup-observations.mjs';

export const PACKAGED_ASSET_TESTS = ['test/compact-ownership.test.mjs','test/prepared-parity.test.mjs'];

// Both PR CI and the trusted queue's isolated candidate checkout are shallow.
// Acquire historical inputs for the actual consuming test files, independently
// of shard placement. Unscoped/manual callers retain the complete old roster.
const NATIVE_REGRESSION_INPUTS = [
  {tests:['test/select-build-ownership.test.mjs'],commits:[
    'd55795e4c0ad01527029db0bd1d774124a12a61a',
    '548c5f89f00271050823076a84695bb41e1b8454'
  ]},
  // This context vintage is still available to unscoped historical reproducers.
  // Scheduled context tests authenticate ordinary captured snapshots instead.
  {tests:[],commits:['d70c5d86e345a225b6bc78d67451b3cbbf7a5eed']},
  {tests:['test/pinned-native-package-inputs.test.mjs'],commits:[
    '65cfcef5ffd7d8b98077b9058a374d1e27047430'
  ]},
  {tests:['test/native-latitudes.test.mjs'],commits:[
    '35d2d3ff48957d34ee8d4329824b268ecadc6d3c'
  ]},
  {tests:['test/native-materialization-gate.test.mjs'],commits:[
    '548c5f89f00271050823076a84695bb41e1b8454'
  ]},
  {tests:['test/physical-component-custody.test.mjs','test/physical-component-report-binding.test.mjs'],commits:[
    // Each executes complete original custody before its own assertions.
    // The compact evidence-controls wrapper uses synthetic predicates instead.
    '8f6dc184d1a41b634cec4759bb57b3cc04dd980a',
    '6ed6406f9fad4c7c468b06a376346b216cb50db7'
  ]}
];
export const NATIVE_REGRESSION_COMMITS = [...new Set(NATIVE_REGRESSION_INPUTS.flatMap(group=>group.commits))];
// Original body rosters already belong to these consumers' immutable metadata.
// Acquisition does not authenticate science; the unchanged readers hash each
// body when they consume it. Do not hydrate unrelated historical tree blobs.
function nativeRegressionBodies(files,readFile) {
  const has=name=>files.includes('test/'+name+'.test.mjs');
  const read=name=>JSON.parse(readFile(name));
  const pins=[];
  let candidate,raw;
  const manifest=()=>{
    if(!candidate){raw=readFile('coordination/engineering/native-grid-candidate-1010-20261005-local16/candidate-v1/manifest.json');candidate=JSON.parse(raw);}
    return candidate;
  };
  if(has('select-build-ownership'))pins.push(manifest().original_assets.bounds);
  if(has('select-build-ownership')||has('native-materialization-gate')){
    manifest();
    pins.push(read('scripts/native-ownership/verified-candidates.json').candidates[createHash('sha256').update(raw).digest('hex')]);
  }
  if(has('native-latitudes'))pins.push(manifest().native_latitudes);
  if(has('pinned-native-package-inputs')){
    const {baseline}=read('coordination/engineering/native-grid-integration-1010-20261005-local17/context-inputs-v1/evidence-quality.json');
    pins.push(...baseline.files.filter(pin=>pin.path.startsWith('data/')).map(pin=>({...pin,commit:baseline.commit})),
      {...manifest().native_latitudes,commit:baseline.commit});
  }
  if(has('physical-component-custody')||has('physical-component-report-binding')){
    const root='coordination/engineering/physical-gap-components-1005-20261005-local19/';
    for(const generation of read(root+'custody-v1/index.json').generations){
      const commit=generation.executed_code_commit,prefix=root+'executed-code/'+commit+'/';
      for(const pin of generation.code){
        if(!pin.path.startsWith(prefix))throw Error('Original custody code path differs');
        pins.push({...pin,commit,path:pin.path.slice(prefix.length)});
      }
    }
  }
  return pins;
}
export function prepareNativeRegressionInputs(profile,{files,exists=fs.existsSync,readFile=fs.readFileSync,run=spawnSync}={}) {
  if(profile!=='full'||!exists('scripts/native-ownership/validate-context-input-stage.mjs'))return {applicable:false,fetched:[]};
  if(files!==undefined&&(!Array.isArray(files)||!files.length||files.some(name=>typeof name!=='string'||!/^test\/[A-Za-z0-9_.-]+\.test\.mjs$/.test(name)||!exists(name))))
    throw Error('Actual regression file roster required');
  // Unscoped callers retain every remaining regression dependency and their
  // original whole-commit fetch behavior. Scoped runs derive only consumed pins.
  const required=files===undefined?NATIVE_REGRESSION_COMMITS:[...new Set(NATIVE_REGRESSION_INPUTS
    .filter(group=>group.tests.some(name=>files.includes(name))).flatMap(group=>group.commits))];
  const pins=files===undefined?[]:nativeRegressionBodies(files,readFile);
  const declared=new Map();
  for(const pin of pins){
    if(!pin||!required.includes(pin.commit)||typeof pin.path!=='string'||!pin.path||pin.path.includes('\\')||
      /[\0\r\n]/.test(pin.path)||path.posix.isAbsolute(pin.path)||pin.path.split('/').some(part=>!part||part==='.'||part==='..')||
      pin.bytes!==undefined&&(!Number.isSafeInteger(pin.bytes)||pin.bytes<0))throw Error('Invalid original regression input declaration');
    const key=pin.commit+'\0'+pin.path,prior=declared.get(key);
    if(prior&&['bytes','mode','git_blob_oid','sha256'].some(field=>prior[field]!==undefined&&pin[field]!==undefined&&prior[field]!==pin[field]))
      throw Error('Conflicting original regression input declarations');
    declared.set(key,{...prior,...pin});
  }
  if(files!==undefined&&required.some(commit=>!pins.some(pin=>pin.commit===commit)))throw Error('Original regression input roster is incomplete');
  const options={encoding:'utf8',maxBuffer:Infinity,env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_TERMINAL_PROMPT:'0'}};
  const git=(args,input)=>{
    const result=run('git',args,{...options,...(input===undefined?{}:{input})});
    if(result.error||result.status!==0)throw Error('Immutable native regression command failed: '+(result.error?.message??result.stderr??''));
    return result.stdout;
  };
  const present=commit=>{
    const result=run('git',['cat-file','-e',commit+'^{commit}'],options);
    if(result.error||result.status===null)throw Error('Immutable native regression commit inspection failed');
    return result.status===0;
  };
  const missing=required.filter(commit=>!present(commit));
  if(missing.length)git(['fetch','--no-tags','--depth=1',...(files===undefined?[]:['--filter=blob:none']),'origin',...missing]);
  if(required.some(commit=>!present(commit)))throw Error('Immutable native regression inputs remain unavailable');
  const objects=new Map();
  for(const pin of declared.values()){
    const row=git(['ls-tree','-z',pin.commit,'--',pin.path]);
    const match=typeof row==='string'&&/^(100644|100755) blob ([a-f0-9]{40})\t([^\0]+)\0$/.exec(row);
    if(!match||match[3]!==pin.path||pin.mode!==undefined&&pin.mode!==match[1]||pin.git_blob_oid!==undefined&&pin.git_blob_oid!==match[2])
      throw Error('Original regression tree identity differs: '+pin.path);
    const oid=match[2],previous=objects.get(oid);
    if(previous?.bytes!==undefined&&pin.bytes!==undefined&&previous.bytes!==pin.bytes)throw Error('Conflicting original regression input lengths');
    objects.set(oid,{oid,bytes:pin.bytes??previous?.bytes});
  }
  const inventory=()=>{
    if(!objects.size)return [];
    const rows=git(['cat-file','--batch-check=%(objectname) %(objecttype) %(objectsize)'],[...objects.keys()].join('\n')+'\n');
    const lines=typeof rows==='string'&&rows.endsWith('\n')?rows.slice(0,-1).split('\n'):[];
    if(lines.length!==objects.size)throw Error('Incomplete original regression body inventory');
    const absent=[];
    [...objects.values()].forEach((pin,index)=>{
      if(lines[index]===pin.oid+' missing'){absent.push(pin.oid);return;}
      const fields=lines[index].split(' '),size=Number(fields[2]);
      if(fields.length!==3||fields[0]!==pin.oid||fields[1]!=='blob'||!/^\d+$/.test(fields[2])||
        !Number.isSafeInteger(size)||pin.bytes!==undefined&&size!==pin.bytes)throw Error('Original regression body type or length differs');
    });
    return absent;
  };
  const absent=inventory();
  if(absent.length){
    git(['fetch','--no-tags','--no-write-fetch-head','--no-recurse-submodules','--no-auto-maintenance','--filter=blob:none','--stdin','origin'],absent.join('\n')+'\n');
    if(inventory().length)throw Error('Original regression bodies remain unavailable');
  }
  return {applicable:true,fetched:missing};
}

// Archived TAP profiles identify these expensive neighbors. Reserve them away
// from the packaged build/parity worker; timings are not runtime guarantees.
export const DATABASE_NEIGHBOR_TESTS = [
  'test/temporal-geography.test.mjs', 'test/postgres-runtime-role.test.mjs',
  'test/reference-hierarchy-release.test.mjs', 'test/hosted-catalog.test.mjs',
  'test/postgres-restore.test.mjs',
  'test/model-semantic-migration.test.mjs'
];
export const MIGRATION_WORKER_TESTS = [
  'test/model.test.mjs', 'test/model-hierarchy-migration.test.mjs',
  'test/model-topology-migration.test.mjs', 'test/storage-export-v2.test.mjs',
  'test/map-snapshots.test.mjs', 'test/install-reviewed-geography.test.mjs',
  'test/land-creations.test.mjs'
];
// Run 37848776291: this file dominated shard 2 (417 s of 558 s).
// Shard 1 had the shortest setup and test path (181 s of tests). Keep the
// ordinary inventory index intact so moving this file does not move neighbors.
export const COMPONENT_CONTROL_TEST = 'test/physical-component-evidence-controls.test.mjs';
export function fullRegressionShard(inventory, shard) {
  const placement = new Map([
    ...PACKAGED_ASSET_TESTS.map(name => [name, 0]),
    ...DATABASE_NEIGHBOR_TESTS.map(name => [name, 1]),
    ...MIGRATION_WORKER_TESTS.map(name => [name, 2])
  ]);
  const reserved = inventory.filter(name => placement.has(name) && placement.get(name) === shard);
  const ordinary = inventory.filter(name => !placement.has(name));
  return [...reserved, ...ordinary.filter((name, index) =>
    (name === COMPONENT_CONTROL_TEST ? 1 : index % 3) === shard)];
}

// Focused regression follows delivery-control test families. The same predicate
// routes changed tests and selects the actual discovered files, so adding or
// removing a control does not require a second inventory edit. App/rendering,
// database, prepared-output and scientific-kernel suites remain full regression.
const FOCUSED_TEST_FAMILIES = [
  'delivery-[\\w-]+', 'integration-[\\w-]+', 'ci-[\\w-]+', 'github-[\\w-]+',
  'issue-[\\w-]+', 'worker-[\\w-]+',
  'package-(?:build(?:-preflight)?|inputs|output-artifact|python-execution|python-runtime)',
  'selected-package-(?:assembly|bootstrap)',
  'source-(?:cohort|completed-staging|evidence-derivation|member-native-delivery|target-native-delivery)',
  'handoff-scope', 'regional-research-gate', 'geography-worker-lane',
  'evidence-quality', 'historical-evidence', 'premerge-evidence',
  'geographic-adjudication-api', 'geographic-report-artifact', 'trusted-workflow-checkouts',
  'merge-integration(?:-entrypoint)?', 'selected-data-profile', 'git-blob-transport',
  'immutable-git-blobs', 'local-workspace',
  // Immutable reader, original-authority, checkpoint and wrapper consumers.
  // Scientific kernels and packaged/rendered output remain full regression.
  'accepted-(?:checkpoint-qualification|joint-transport)', 'additive-gap-repair',
  'administrative-original-hashes', 'component-authority-identity', 'current-rebind-product-custody',
  'effective-geographic-regression', 'evidence-byte-bounds', 'fiji-canonical-reproduction',
  'geographic-(?:checkpoint-products|regression)', 'geography-prefetch',
  'immutable-reader-read', 'installed-runtime-identity', 'map-cell-diagnosis',
  'native-(?:additions-order|checkpoint-consumer|word-store|stream-custody|interval-stream|interval-projection)', 'canonical-value-hash', 'parallel-geography-comparison',
  'qualification-exclusion-prefilter', 'selected-checkpoint',
  'selected-joint-(?:check|entry|package-boundary)', 'selected-metadata-wiring',
  'source-target-native-diagnostic', 'supported-programs', 'trusted-geography-check',
  'unchanged-selected-geography', 'visible-gap-eligibility',
  'native-(?:authority-entry|diagnostic-entry|witness-authority|regression-inputs)',
  'physical-source-retention', 'revised-source-native', 'dated-centre-authority', 'full-regression-shards'
];
const focusedTest = new RegExp('^test/(?:' + FOCUSED_TEST_FAMILIES.join('|') + ')\\.test\\.(?:mjs|py)$');
// This shared fixture has only focused consumers; reuse their ordinary-file
// routing checks. Test execution still discovers only top-level *.test.mjs.
export const focusedIntegrationTest = name => focusedTest.test(name) || ['test/fixtures/selected-checkpoint.mjs','test/fixtures/native-word-store.mjs'].includes(name);

export function integrationTestFiles(profile, shard, testSelection = 'complete') {
  if (!['complete','selected-output'].includes(testSelection) ||
      (testSelection !== 'complete' && (profile !== 'full' || shard !== 0))) throw Error('Invalid trusted test selection');
  if (!['full','evidence'].includes(profile) || !Number.isInteger(shard) || shard < 0 || shard > 2 ||
      (profile === 'evidence' && shard !== 0)) throw Error('Invalid trusted integration test profile');
  const inventory = fs.readdirSync('test').filter(name => name.endsWith('.test.mjs')).sort().map(name=>`test/${name}`);
  const files = testSelection === 'selected-output' ? ['test/compact-ownership.test.mjs']
    : profile === 'full' ? fullRegressionShard(inventory, shard) : inventory.filter(focusedIntegrationTest);
  if (!files.length || files.some(name => !fs.existsSync(name))) throw Error('Missing integration test inventory');
  return files;
}
export function integrationNeedsBrowser(profile, shard, testSelection = 'complete') {
  return integrationTestFiles(profile, shard, testSelection).some(name => /['"](?:@playwright\/test|playwright)['"]/.test(fs.readFileSync(name, 'utf8')));
}
export function prepareIntegrationTests(files) {
  if (files.some(name=>PACKAGED_ASSET_TESTS.includes(name)) && !fs.existsSync('dist/client/atlas-geography.json')) {
    throw Error('Packaged-asset regression requires the actual hosted build; missing dist/client/atlas-geography.json');
  }
  if (files.includes('test/stage-site-migrations.test.mjs')) {
    compileHostedMigrations({input:'drizzle', output:'dist/drizzle'});
  }
}

// Stream diagnostics immediately. Cancellation also reaches the test workers
// and their Python children; the actual runner exit status determines success.
export async function streamTestProcess(args, {env = process.env,
  stdout = process.stdout, stderr = process.stderr} = {}) {
  const grouped = process.platform !== 'win32';
  const child = spawn(process.execPath, args, {env, detached: grouped, stdio: ['ignore', 'pipe', 'pipe']});
  let failure, cancelled, escalation, orphaned = false;
  let cleanup = Promise.resolve();
  const stop = signal => {
    try { grouped ? process.kill(-child.pid, signal) : child.kill(signal); }
    catch (error) { if (error.code !== 'ESRCH') failure ??= error; }
  };
  const cancel = signal => {
    if (cancelled) return;
    cancelled = signal;
    stop('SIGTERM');
    escalation = setTimeout(() => stop('SIGKILL'), 1000);
  };
  const onInt = () => cancel('SIGINT'), onTerm = () => cancel('SIGTERM');
  process.on('SIGINT', onInt); process.on('SIGTERM', onTerm);
  // Exit precedes close: descendants may inherit output pipes and prevent
  // close forever. Start cleanup as soon as the test runner itself exits.
  child.once('exit', () => {
    cleanup = (async () => {
      if (!grouped) return;
      try { process.kill(-child.pid, 0); orphaned = true; }
      catch (error) { if (error.code !== 'ESRCH') failure ??= error; return; }
      stop('SIGTERM');
      await new Promise(resolve => setTimeout(resolve, 1000));
      stop('SIGKILL');
    })();
  });
  child.stdout.pipe(stdout, {end: false}); child.stderr.pipe(stderr, {end: false});
  try {
    const result = await new Promise(resolve => {
      child.once('error', error => { failure = error; });
      child.once('close', (status, signal) => resolve({status, signal}));
    });
    await cleanup;
    if (failure) throw failure;
    if (cancelled) return cancelled === 'SIGINT' ? 130 : 143;
    if (result.status === 0 && orphaned) throw Error('Regression exited successfully with unfinished descendants');
    return result.status ?? 1;
  } finally {
    clearTimeout(escalation);
    process.off('SIGINT', onInt); process.off('SIGTERM', onTerm);
  }
}
// The digest arrives from the just-completed trusted assembly step, not from
// candidate-selected JSON. This checks actual assembly identity, not test coverage.
export function requireCurrentPackageAssembly({directory=process.cwd(),expected=process.env.SELECTED_PACKAGE_ASSEMBLY_SHA256}={}) {
  if(!/^[a-f0-9]{64}$/.test(expected??''))throw Error('Trusted current package assembly digest required');
  const file=path.join(directory,'.cache/package-input-build.json'),stat=fs.lstatSync(file);
  if(!stat.isFile()||stat.isSymbolicLink())throw Error('Ordinary assembly receipt required');
  const raw=fs.readFileSync(file);
  if(createHash('sha256').update(raw).digest('hex')!==expected)throw Error('Current assembly receipt digest differs');
  const receipt=JSON.parse(raw),assembly=receipt.assembly;
  const head=spawnSync('git',['-C',directory,'rev-parse','HEAD'],{encoding:'utf8'});
  if(head.status!==0||receipt.kind!=='cloudflare'||assembly?.kind!=='retained-original-output-plus-current-additive'||
    assembly.current_execution?.source_commit!==head.stdout.trim()||receipt.preflight?.inputs?.head!==head.stdout.trim()||
    assembly.base_restoration_invoked!==false||assembly.invariant_build_invoked!==false)
    throw Error('Actual same-head assembly required');
  return {origin:assembly.origin,
    limitation:'Authenticated current assembly identity; this receipt does not attest native, smoke, unit or browser execution.'};
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const profile = process.env.INTEGRATION_PROFILE, shard = Number(process.env.INTEGRATION_SHARD);
  const testSelection = process.env.INTEGRATION_TEST_SELECTION || 'complete';
  const files = integrationTestFiles(profile, shard, testSelection);
  const retained=testSelection==='selected-output'?requireCurrentPackageAssembly():null;
  if(retained)console.log(JSON.stringify({package_assembly:retained}));
  const git=measuredGitSetup();
  const nativeInputs=await observeSetupPhase('immutable-regression-inputs',()=>prepareNativeRegressionInputs(testSelection === 'complete' ? profile : 'evidence',{files,run:git.run}),{counters:git.snapshot});
  console.log(JSON.stringify({native_inputs:nativeInputs}));
  // Current prepared products are committed inputs. Historical restoration is
  // explicit reproduction, never a mutation of ordinary regression inputs.
  prepareIntegrationTests(files);
  console.log(JSON.stringify({profile, test_selection: testSelection, shard, files}));
  process.exitCode = await streamTestProcess(['--test','--test-reporter=tap','--test-concurrency=2', ...files], {
    env:{...process.env,...(profile==='full' && shard===0?{ATLAS_REQUIRE_STATIC:'1'}:{})}
  });
}

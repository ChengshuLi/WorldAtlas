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
export function prepareNativeRegressionInputs(profile,{files,exists=fs.existsSync,run=spawnSync}={}) {
  if(profile!=='full'||!exists('scripts/native-ownership/validate-context-input-stage.mjs'))return {applicable:false,fetched:[]};
  if(files!==undefined&&(!Array.isArray(files)||!files.length||files.some(name=>typeof name!=='string'||!/^test\/[A-Za-z0-9_.-]+\.test\.mjs$/.test(name)||!exists(name))))
    throw Error('Actual regression file roster required');
  // Unscoped callers retain every remaining regression dependency.
  const required=files===undefined?NATIVE_REGRESSION_COMMITS:[...new Set(NATIVE_REGRESSION_INPUTS
    .filter(group=>group.tests.some(name=>files.includes(name))).flatMap(group=>group.commits))];
  const present=commit=>run('git',['cat-file','-e',commit+'^{commit}'],{encoding:'utf8'}).status===0;
  const missing=required.filter(commit=>!present(commit));
  if(missing.length){
    const fetched=run('git',['fetch','--no-tags','--depth=1','origin',...missing],{encoding:'utf8',maxBuffer:4*1024*1024});
    if(fetched.status!==0)throw Error('Immutable native regression fetch failed: '+(fetched.error?.message??fetched.stderr??''));
  }
  if(required.some(commit=>!present(commit)))throw Error('Immutable native regression inputs remain unavailable');
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
  'immutable-git-blobs', 'pr-evidence-transport', 'local-workspace',
  'native-(?:authority-entry|diagnostic-entry|witness-authority|regression-inputs)',
  'physical-source-retention', 'revised-source-native', 'dated-centre-authority', 'full-regression-shards'
];
const focusedTest = new RegExp('^test/(?:' + FOCUSED_TEST_FAMILIES.join('|') + ')\\.test\\.(?:mjs|py)$');
export const focusedIntegrationTest = name => focusedTest.test(name);

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

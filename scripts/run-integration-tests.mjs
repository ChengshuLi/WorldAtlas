import fs from 'node:fs';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawn, spawnSync} from 'node:child_process';
import {isFocusedIntegrationTest, SOURCE_DATABASE_TEST_PATHS} from './integration-profile.mjs';
import {compileHostedMigrations} from './compile-hosted-migrations.mjs';
import {observeSetupPhase,measuredGitSetup} from './ci-setup-observations.mjs';

export const PACKAGED_ASSET_TESTS = ['test/compact-ownership.test.mjs','test/canonical-compact-repack.test.mjs','test/prepared-parity.test.mjs'];

// Both PR CI and the trusted queue's isolated candidate checkout are shallow.
// Keep the common native/context vintages for every full regression shard.
const COMMON_NATIVE_REGRESSION_COMMITS = [
  'd55795e4c0ad01527029db0bd1d774124a12a61a',
  '548c5f89f00271050823076a84695bb41e1b8454',
  'd70c5d86e345a225b6bc78d67451b3cbbf7a5eed',
  '65cfcef5ffd7d8b98077b9058a374d1e27047430',
  '35d2d3ff48957d34ee8d4329824b268ecadc6d3c'
];
// Only these actual tests consume the additional archived physical vintages.
// Select by the runner's file roster, so ordinary shard reassignment is harmless.
const ARCHIVED_PHYSICAL_REGRESSION_INPUTS = [
  {tests:['test/physical-component-custody.test.mjs','test/physical-component-report-binding.test.mjs'],commits:[
    // Each executes complete original custody before its own assertions.
    // The compact evidence-controls wrapper uses synthetic predicates instead.
    '8f6dc184d1a41b634cec4759bb57b3cc04dd980a',
    '6ed6406f9fad4c7c468b06a376346b216cb50db7'
  ]}
];
export const NATIVE_REGRESSION_COMMITS = [...COMMON_NATIVE_REGRESSION_COMMITS,
  ...ARCHIVED_PHYSICAL_REGRESSION_INPUTS.flatMap(group=>group.commits)];
export function prepareNativeRegressionInputs(profile,{files,exists=fs.existsSync,run=spawnSync}={}) {
  if(profile!=='full'||!exists('scripts/native-ownership/validate-context-input-stage.mjs'))return {applicable:false,fetched:[]};
  if(files!==undefined&&(!Array.isArray(files)||!files.length||files.some(name=>typeof name!=='string'||!/^test\/[A-Za-z0-9_.-]+\.test\.mjs$/.test(name)||!exists(name))))
    throw Error('Actual regression file roster required');
  // Unscoped callers retain every remaining regression dependency.
  const required=files===undefined?NATIVE_REGRESSION_COMMITS:[...COMMON_NATIVE_REGRESSION_COMMITS,
    ...ARCHIVED_PHYSICAL_REGRESSION_INPUTS.filter(group=>group.tests.some(name=>files.includes(name))).flatMap(group=>group.commits)];
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
  'test/neon-storage-migration.test.mjs', 'test/postgres-restore.test.mjs',
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

export function integrationTestFiles(profile, shard, testSelection = 'complete', focusedFiles = null) {
  if (!['complete','selected-output'].includes(testSelection) ||
      (testSelection !== 'complete' && (profile !== 'full' || shard !== 0))) throw Error('Invalid trusted test selection');
  if (!['full','evidence'].includes(profile) || !Number.isInteger(shard) || shard < 0 || shard > 2 ||
      (profile === 'evidence' && shard !== 0)) throw Error('Invalid trusted integration test profile');
  if (focusedFiles !== null) {
    if (profile !== 'evidence' || shard !== 0 || testSelection !== 'complete' || !Array.isArray(focusedFiles) ||
        !focusedFiles.length || new Set(focusedFiles).size !== focusedFiles.length ||
        !focusedFiles.some(name => SOURCE_DATABASE_TEST_PATHS.includes(name)) ||
        focusedFiles.some(name => !isFocusedIntegrationTest(name) || !fs.existsSync(name)))
      throw Error('Invalid trusted focused test files');
    return [...focusedFiles];
  }
  const focused = ['handoff-scope','issue-claims','worker-result','regional-research-gate','geography-worker-lane',
    'evidence-quality','premerge-evidence','trusted-workflow-checkouts','merge-integration','merge-integration-entrypoint','integration-proof',
    // Actual delivery entry/advance consumers, including scientific dispatch guards.
    'delivery-evidence-derivation','delivery-finalize-config','delivery-handoff-advance','delivery-handoff','delivery-registry-delta','delivery-role-staging','local-workspace','native-authority-entry','native-diagnostic-entry','native-witness-authority','physical-source-retention','source-cohort','source-completed-staging','source-evidence-derivation','source-member-native-delivery','source-publication-admission','source-target-native-delivery'];
  const inventory = fs.readdirSync('test').filter(name => name.endsWith('.test.mjs')).sort().map(name=>`test/${name}`);
  const files = testSelection === 'selected-output' ? ['test/compact-ownership.test.mjs']
    : profile === 'full' ? fullRegressionShard(inventory, shard) : focused.map(name => `test/${name}.test.mjs`);
  if (!files.length || files.some(name => !fs.existsSync(name))) throw Error('Missing integration test inventory');
  return files;
}
export function integrationNeedsBrowser(profile, shard, testSelection = 'complete', focusedFiles = null) {
  return integrationTestFiles(profile, shard, testSelection, focusedFiles).some(name => /['"](?:@playwright\/test|playwright)['"]/.test(fs.readFileSync(name, 'utf8')));
}
export function prepareIntegrationTests(files) {
  if (files.some(name=>PACKAGED_ASSET_TESTS.includes(name)) && !fs.existsSync('dist/client/atlas-geography.json')) {
    throw Error('Packaged-asset regression requires the actual hosted build; missing dist/client/atlas-geography.json');
  }
  if (files.includes('test/stage-site-migrations.test.mjs')) {
    compileHostedMigrations({input:'drizzle', output:'dist/drizzle'});
  }
}

// Stream diagnostics immediately; retain only a bounded tail for the final TAP
// summary. Cancellation also reaches the test workers and their Python children.
export async function streamTestProcess(args, {env = process.env,
  stdout = process.stdout, stderr = process.stderr, maxBytes = 64 * 1024 * 1024} = {}) {
  const grouped = process.platform !== 'win32';
  const child = spawn(process.execPath, args, {env, detached: grouped, stdio: ['ignore', 'pipe', 'pipe']});
  let tail = '', bytes = 0, failure, cancelled, escalation, orphaned = false;
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
  child.stdout.setEncoding('utf8');
  child.stdout.on('data', chunk => {
    tail = (tail + chunk).slice(-64 * 1024);
  });
  for (const stream of [child.stdout, child.stderr]) {
    stream.on('data', chunk => {
      bytes += Buffer.byteLength(chunk);
      if (bytes > maxBytes && !failure) {
        failure = Error('Regression output exceeds unchanged 64 MiB bound');
        cancel('output-limit');
      }
    });
  }
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
    if (result.status === 0 && !/^# skipped 0$/m.test(tail)) throw Error('Regression did not establish zero skipped tests');
    if (result.status === 0 && /^# skipped [1-9]/m.test(tail)) throw Error('Skipped tests cannot establish regression coverage');
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
  if(!stat.isFile()||stat.isSymbolicLink()||stat.size>8*1024*1024)throw Error('Bounded ordinary assembly receipt required');
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
  const focusedMetadata = process.env.INTEGRATION_FOCUSED_TEST_FILES;
  if (process.env.GITHUB_ACTIONS === 'true' && profile === 'evidence' &&
      (typeof focusedMetadata !== 'string' || !focusedMetadata.trim()))
    throw Error('Trusted focused test metadata is missing');
  const focusedFiles = JSON.parse(focusedMetadata || 'null');
  const files = integrationTestFiles(profile, shard, testSelection, focusedFiles);
  const retained=testSelection==='selected-output'?requireCurrentPackageAssembly():null;
  if(retained)console.log(JSON.stringify({package_assembly:retained}));
  const git=measuredGitSetup();
  const nativeInputs=await observeSetupPhase('immutable-regression-inputs',()=>prepareNativeRegressionInputs(testSelection === 'complete' ? profile : 'evidence',{files,run:git.run}),{counters:git.snapshot});
  console.log(JSON.stringify({native_inputs:nativeInputs}));
  // Only full checkout readers consume canonical products. The focused evidence
  // profile deliberately has no canonical namespace in its sparse checkout.
  if (profile === 'full' && !retained) {
    const canonicalCheckout=await observeSetupPhase('canonical-checkout',async()=>{
      const {prepareCanonicalCheckout}=await import('./canonical-restoration.mjs');
      return prepareCanonicalCheckout();
    });
    console.log(JSON.stringify({canonical_checkout:canonicalCheckout}));
    if ([0,1,2].includes(shard)) {
      const selectedCheckout=await observeSetupPhase('canonical-checkout',async()=>{
        const {prepareModelReaderCheckout}=await import('../coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/prepare-model-reader-checkout.mjs');
        return prepareModelReaderCheckout({root:process.cwd(),profile,shard});
      });
      console.log(JSON.stringify({selected_model_reader_checkout:selectedCheckout}));
    }
  }
  prepareIntegrationTests(files);
  console.log(JSON.stringify({profile, test_selection: testSelection, shard, files}));
  process.exitCode = await streamTestProcess(['--test','--test-reporter=tap','--test-concurrency=2', ...files], {
    env:{...process.env,...(profile==='full' && shard===0?{ATLAS_REQUIRE_STATIC:'1'}:{})}
  });
}

import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawn, spawnSync} from 'node:child_process';
import {compileHostedMigrations} from './compile-hosted-migrations.mjs';
import {observeSetupPhase,measuredGitSetup} from './ci-setup-observations.mjs';

export const PACKAGED_ASSET_TESTS = ['test/compact-ownership.test.mjs','test/prepared-parity.test.mjs'];

// Both PR CI and the trusted queue's isolated candidate checkout are shallow.
// Read-only regression requires these exact original source/code vintages.
export const NATIVE_REGRESSION_COMMITS = [
  'd55795e4c0ad01527029db0bd1d774124a12a61a',
  '548c5f89f00271050823076a84695bb41e1b8454',
  'd70c5d86e345a225b6bc78d67451b3cbbf7a5eed',
  '65cfcef5ffd7d8b98077b9058a374d1e27047430',
  '35d2d3ff48957d34ee8d4329824b268ecadc6d3c',
  // Original physical-water input for the before-water audit. Invalid water
  // remains diagnostic; regression only restores its immutable source bytes.
  'ff566eab31ef072084c548f67dee8ee727ab3d47',
  // Complete archived execution code is independently compared with original Git.
  'e67eeafc1aa130aa5c1a6d1222d39116625fd003',
  '8b61b9303553f2068f18ad5a000d4cba14059547',
  'b6e0d0d21cfd6dde68c3c292c9513d3a24896a11',
  '85571b6ef23f5565f08693a542fa7dad20c651b8',
  // Exact original input and both complete/incomplete execution vintages
  // for the whole-file physical component custody regression.
  'c603befd3aaf4da90d59b12378e1e0739331efba',
  '8f6dc184d1a41b634cec4759bb57b3cc04dd980a',
  '6ed6406f9fad4c7c468b06a376346b216cb50db7',
  // Exact committed input/executable for both archived global priority runs.
  'bf9e8a6580e997d82d0414235e3a0d2a81e1e24a'
];
export function prepareNativeRegressionInputs(profile,{exists=fs.existsSync,run=spawnSync}={}) {
  if(profile!=='full'||!exists('scripts/native-ownership/validate-context-input-stage.mjs'))return {applicable:false,fetched:[]};
  const present=commit=>run('git',['cat-file','-e',commit+'^{commit}'],{encoding:'utf8'}).status===0;
  const missing=NATIVE_REGRESSION_COMMITS.filter(commit=>!present(commit));
  if(missing.length){
    const fetched=run('git',['fetch','--no-tags','--depth=1','origin',...missing],{encoding:'utf8',maxBuffer:4*1024*1024});
    if(fetched.status!==0)throw Error('Immutable native regression fetch failed: '+(fetched.error?.message??fetched.stderr??''));
  }
  if(NATIVE_REGRESSION_COMMITS.some(commit=>!present(commit)))throw Error('Immutable native regression inputs remain unavailable');
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

export function integrationTestFiles(profile, shard) {
  if (!['full','evidence'].includes(profile) || !Number.isInteger(shard) || shard < 0 || shard > 2 ||
      (profile === 'evidence' && shard !== 0)) throw Error('Invalid trusted integration test profile');
  const focused = ['handoff-scope','issue-claims','worker-result','regional-research-gate','geography-worker-lane',
    'evidence-quality','premerge-evidence','trusted-workflow-checkouts','merge-integration','merge-integration-client','merge-integration-entrypoint','integration-proof'];
  const inventory = fs.readdirSync('test').filter(name => name.endsWith('.test.mjs')).sort().map(name=>`test/${name}`);
  const files = profile === 'full' ? fullRegressionShard(inventory, shard)
    : focused.map(name => `test/${name}.test.mjs`);
  if (!files.length || files.some(name => !fs.existsSync(name))) throw Error('Missing integration test inventory');
  return files;
}
export function integrationNeedsBrowser(profile, shard) {
  return integrationTestFiles(profile, shard).some(name => /['"](?:@playwright\/test|playwright)['"]/.test(fs.readFileSync(name, 'utf8')));
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
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const profile = process.env.INTEGRATION_PROFILE, shard = Number(process.env.INTEGRATION_SHARD);
  const files = integrationTestFiles(profile, shard);
  const git=measuredGitSetup();
  const nativeInputs=await observeSetupPhase('immutable-regression-inputs',()=>prepareNativeRegressionInputs(profile,{run:git.run}),{counters:git.snapshot});
  console.log(JSON.stringify({native_inputs:nativeInputs}));
  // Only full checkout readers consume canonical products. The focused evidence
  // profile deliberately has no canonical namespace in its sparse checkout.
  if (profile === 'full') {
    const canonicalCheckout=await observeSetupPhase('canonical-checkout',async()=>{
      const {prepareCanonicalCheckout}=await import('./canonical-restoration.mjs');
      return prepareCanonicalCheckout();
    });
    console.log(JSON.stringify({canonical_checkout:canonicalCheckout}));
  }
  prepareIntegrationTests(files);
  console.log(JSON.stringify({profile, shard, files}));
  process.exitCode = await streamTestProcess(['--test','--test-reporter=tap','--test-concurrency=2', ...files], {
    env:{...process.env,...(profile==='full' && shard===0?{ATLAS_REQUIRE_STATIC:'1'}:{})}
  });
}

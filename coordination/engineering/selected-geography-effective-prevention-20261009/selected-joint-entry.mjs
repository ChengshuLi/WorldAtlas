// One trusted Node invocation owns checkpoint authority and native comparison.
// Proposed commits are data, never imported code.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';

const ROOT = fileURLToPath(new URL('../../../', import.meta.url));
const P = 'coordination/engineering/selected-geography-effective-prevention-20261009/';
export const JOINT_CODE = Object.freeze([
  'scripts/run-geographic-check.py',
  'scripts/check-effective-geographic-regression.mjs', 'scripts/selected-checkpoint-native.mjs',
  'src/native-grid.js', 'src/ownership-codec.js',
  P + 'selected-neighbor-prevention.mjs', P + 'selected-checkpoint.mjs', P + 'selected-joint-entry.mjs',
  'scripts/accepted-selected-checkpoint.mjs', 'scripts/check-handoff-scope.mjs',
  'scripts/evidence-policy.mjs', 'scripts/evidence-quality.mjs', 'scripts/geographic-report-artifact.mjs',
  'scripts/github-quota.mjs', 'scripts/github-snapshots.mjs', 'scripts/integration-proof.mjs',
  'scripts/issue-claim-contract.mjs', 'scripts/research-import-gate.mjs',
  'scripts/worker-result.mjs', 'src/regional-import-gate.js', 'scripts/geographic_checkpoint_products.py',
  'scripts/selected-reference-metadata.mjs', 'src/reference-metadata.js'
]);
const sha = body => createHash('sha256').update(body).digest('hex');
const demand = (ok, message) => { if (!ok) throw Error(message); };
const commit = value => typeof value === 'string' && /^[a-f0-9]{40}$/.test(value);
function ordinaryParents(target) {
  for (let p = path.dirname(target);; p = path.dirname(p)) {
    const stat = fs.lstatSync(p);
    demand(stat.isDirectory() && !stat.isSymbolicLink(), 'Nonordinary joint output/code ancestor');
    if (p === path.dirname(p)) break;
  }
}
function fresh(destination) {
  ordinaryParents(destination);
  try { fs.lstatSync(destination); } catch (error) { if (error.code === 'ENOENT') return; throw error; }
  throw Error('Joint output already exists');
}
// Transport hints are immutable candidate data, separate from scientific routes.
// The acceptance reader authenticates their contents; these descriptors never
// mint authority and stay explicit applicability/admission dependencies.
export function checkpointTransportInput(reader, name, {consume = true} = {}) {
  demand(typeof name === 'string' && !path.posix.isAbsolute(name) && !name.includes('\\')
    && !name.includes('\0') && name.split('/').every(p => p && p !== '.' && p !== '..'),
  'Unsafe checkpoint transport path');
  const tree = reader.git('ls-tree', '-z', reader.version, '--', name).toString();
  if (!tree) return {pin:{commit:reader.version, path:name, present:false, whole_body_consumed:false}, body:null};
  demand(/^100644 blob [a-f0-9]{40}\t/.test(tree) && tree.endsWith('\t' + name + '\0'),
    'Checkpoint transport input is not an ordinary Git file');
  const key=reader.version+':'+name, previous=reader.inventory.get(key);
  try {
    const descriptor=reader.descriptor(name);
    const pin={...descriptor,present:true,whole_body_consumed:consume};
    if(!consume)return {pin,body:null};
    const body=reader.read(name);
    pin.sha256=sha(body);
    return {pin,body};
  } finally {
    // Keep transport hints in their separate explicit custody roster.
    if(!previous)reader.inventory.delete(key);
  }

}

function executionGuard(repo, trusted) {
  demand(commit(trusted) && fs.realpathSync(repo) === fs.realpathSync(ROOT), 'Joint entry requires its actual trusted checkout');
  demand(process.execArgv.length === 0
    && process.env.NODE_OPTIONS === undefined && process.env.NODE_PATH === undefined,
  'Joint entry requires its exact trusted runtime arguments');
  const git = (...args) => {
    const options={stdio:['ignore', 'pipe', 'pipe'],maxBuffer:Infinity};
    if(args[0]==='cat-file'&&args[1]==='blob') options.maxBuffer=Number(git('cat-file','-s',args[2]))+1;
    return execFileSync('git', ['-c', 'core.hooksPath=/dev/null', '-C', repo, ...args],options);
  };
  demand(git('rev-parse', 'HEAD').toString().trim() === trusted, 'Joint executing commit differs from checkout');
  const files = JOINT_CODE.map(name => {
    const file = path.join(ROOT, name); ordinaryParents(file); const stat = fs.lstatSync(file);
    demand(stat.isFile() && !stat.isSymbolicLink(), 'Nonordinary joint execution code');
    return {name, file, stat};
  });
  return files.map(({name, file, stat}) => {
    const row = git('ls-tree', '-z', trusted, '--', name).toString();
    demand(/^100(644|755) blob [a-f0-9]{40}\t/.test(row) && row.endsWith('\t' + name + '\0'), 'Unbound joint code');
    const [mode,, oid] = row.slice(0, row.indexOf('\t')).split(' ');
    demand(Number(git('cat-file', '-s', oid)) === stat.size, 'Joint code size differs');
    const local = fs.readFileSync(file), body = git('cat-file', 'blob', oid);
    demand(local.equals(body) && (stat.mode & 0o777) === (mode === '100755' ? 0o755 : 0o644), 'Joint code body/mode differs');
    return {commit:trusted, path:name, mode, git_blob_oid:oid, bytes:body.length, sha256:sha(body)};
  });
}

export async function selectedJointStage(repo, trusted, baseline, candidate, destination, parentRuntimePath) {
  demand(commit(baseline) && commit(candidate), 'Joint comparison requires immutable selected commits');
  destination = path.resolve(destination); fresh(destination);
  const code = executionGuard(repo, trusted);
  const native = await import('../../../scripts/check-effective-geographic-regression.mjs');
  const {compareSelectedCheckpointNative} = await import('../../../scripts/selected-checkpoint-native.mjs');
  const checkpoint = await import('./selected-checkpoint.mjs');
  const {valueBytes, valueSha} = await import('./selected-neighbor-prevention.mjs');
  const startup = native.selectedBootstrap(repo, baseline, candidate, {parentRuntimePath});
  const {beforeReader, afterReader} = startup;
  let state, acceptedHandle;
  const accepted = await import('../../../scripts/accepted-selected-checkpoint.mjs');
  const transportInputs = [];
  try {
    const locatorInput = checkpointTransportInput(afterReader, accepted.ACCEPTED_CHECKPOINT_LOCATOR);
    transportInputs.push(locatorInput.pin);
    let qualified;
    if (locatorInput.body) {
      const locator = accepted.validateAcceptedCheckpointLocator(JSON.parse(locatorInput.body));
      const archiveName = locator.retained_artifact?.path;
      let archiveIndex;
      if (archiveName) {
        archiveIndex = transportInputs.length;
        transportInputs.push(checkpointTransportInput(afterReader, archiveName, {consume:false}).pin);
      }
      const token = process.env.GH_TOKEN;
      if (!token) return coldDecision({cold:'baseline-and-candidate', reason:'Accepted checkpoint authenticated API access unavailable'});
      const proof = await accepted.acquireAcceptedCheckpoint({repo:process.env.GITHUB_REPOSITORY ?? 'ChengshuLi/WorldAtlas',
        locator:locator.acceptance, token,
        retainedArchive:archiveName ? () => {
          const input = checkpointTransportInput(afterReader, archiveName);
          transportInputs[archiveIndex] = input.pin;
          demand(input.body, 'Declared retained checkpoint archive is absent');
          return input.body;
        } : undefined});
      if (!proof.available) return coldDecision({cold:'baseline-and-candidate', reason:proof.reason});
      acceptedHandle = proof.handle;
      qualified = await checkpoint.qualifyAcceptedCheckpoint({reader:beforeReader, acceptedHandle});
    } else qualified = checkpoint.qualifyCheckpoint({reader:beforeReader});
    if (!qualified.available) return coldDecision(qualified);
    state = qualified.state;
    const transition = checkpoint.qualifyTransition({state, reader:afterReader});
    if (!transition.available) return coldDecision(transition);
    checkpoint.authenticateTransition({transition});
    const nativeReport = await compareSelectedCheckpointNative({transition});
    demand(nativeReport && ['native-regressions-found', 'no-new-native-loss'].includes(nativeReport.status),
      'Joint native consumer did not complete an actual comparison');
    if (nativeReport.status === 'native-regressions-found') return result(nativeReport, null);
    // Native comparison is the selected-map acceptance boundary. Do not build
    // or compare continuous polygon operands, including on no-change runs.
    const genuine = checkpoint.authenticateTransition({transition});
    const authorityPaths = [P + 'supported-programs.json',
      'coordination/engineering/selected-checkpoint-reuse-20261012/accepted-checkpoints.json'];
    const authorityPins = authorityPaths.map(name => beforeReader.inventory.get(trusted + ':' + name));
    demand(authorityPins.every(pin => pin?.whole_body_consumed && /^[a-f0-9]{64}$/.test(pin.sha256)),
      'Derived custody requires actual consumed executing authority pins');
    const executingPolicy = checkpoint.checkpointExecutingPolicy({transition});
    const inventory = reader => [...reader.inventory.values()].sort((a,b) =>
      (a.commit + ':' + a.path).localeCompare(b.commit + ':' + b.path));
    const routes = valueBytes(checkpoint.checkpointRouteCensus({transition}));
    const routePin = {path:'checkpoint-routes.json', bytes:routes.length, sha256:sha(routes)};
    const derivedFactsBase = {version:1, kind:'derived-selected-checkpoint-candidate-v1',
      validation_stage:'native-passed', accepted_checkpoint:false,
      executing_commit:trusted, execution_code:code, runtime:startup.identities,
      baseline_accepted_execution:genuine.baseline.accepted_execution,
      executing_authority_pins:authorityPins, executing_policy:executingPolicy,
      checkpoint_transport_inputs:transportInputs, checkpoint_routes:routePin,
      actual_reader_inventories:{baseline:inventory(beforeReader), candidate:inventory(afterReader)},
      baseline_commit:baseline, candidate_commit:candidate,
      baseline_selection:genuine.baseline.selection, candidate_selection:genuine.candidate.selection,
      candidate_bindings:{ledger_sha256:valueSha(genuine.candidate.ledger), registry_sha256:valueSha(genuine.candidate.registry),
        patch_sha256:valueSha(genuine.candidate.patch), manifest_sha256:valueSha(genuine.candidate.manifest)},
      native_result_sha256:valueSha(nativeReport), candidate_code_executed:false};
    const certificate = valueBytes(genuine.candidate.certificate);
    const certificateEncoded = gzipSync(certificate, {level:9, mtime:0});
    const certificatePin = {path:'derived-certificate.json.gz', bytes:certificateEncoded.length,
      sha256:sha(certificateEncoded), decoded_bytes:certificate.length, decoded_sha256:sha(certificate)};
    const derivedFacts = valueBytes({...derivedFactsBase, certificate:certificatePin});
    const derivedPublication = {version:1, complete:true, kind:'derived-selected-checkpoint-candidate-v1',
      accepted_checkpoint:false, validation_stage:'native-passed', certificate:certificatePin,
      facts:{path:'derived-facts.json', bytes:derivedFacts.length, sha256:sha(derivedFacts)}, routes:routePin};
    const derivedPublicationBody = valueBytes(derivedPublication);
    checkpoint.authenticateTransition({transition});
    executionGuard(repo, trusted); fresh(destination); fs.mkdirSync(destination);
    for (const [name, body] of [['derived-certificate.json.gz', certificateEncoded],
      ['derived-facts.json', derivedFacts], ['checkpoint-routes.json', routes], ['derived-publication.json', derivedPublicationBody]])
      fs.writeFileSync(path.join(destination, name), body, {flag:'wx', mode:0o644});
    return result(nativeReport, derivedPublication);
  } finally {
    if (state) checkpoint.releaseCheckpoint(state);
    if (acceptedHandle) accepted.releaseAcceptedCheckpoint(acceptedHandle);
  }
  function coldDecision(decision) {
    return {version:1, kind:'trusted-selected-joint-comparison-v1', mode:'legacy-cold-required',
      reuse_unavailable:{cold:decision.cold, reason:decision.reason}, candidate_code_executed:false};
  }
  function result(nativeReport, derivedCheckpoint) {
    return {version:1, kind:'trusted-selected-joint-comparison-v1', mode:'authenticated-checkpoint-append-v1',
      native:{...nativeReport, runtime:startup.runtime, caller_runtime:startup.callerRuntime,
        execution_runtimes:startup.identities, execution_code_inventory:code}, derived_checkpoint:derivedCheckpoint,
      candidate_code_executed:false};
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const result = await selectedJointStage(...process.argv.slice(2));
  const body = JSON.stringify(result) + '\n';
  process.stdout.write(body);
}

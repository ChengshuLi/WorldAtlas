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
  'scripts/issue-claim-contract.mjs', 'scripts/job-deadline.mjs', 'scripts/research-import-gate.mjs',
  'scripts/worker-result.mjs', 'src/regional-import-gate.js', 'scripts/geographic_checkpoint_products.py'
]);
const FILE = 32 * 1024 * 1024, OUTPUT = 4 * 1024 * 1024;
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
// Count canonical JSON bytes without constructing the complete serialized graph.
// Ordering changes no byte count. Only ordinary JSON products are supported.
function jsonBytes(value, limit) {
  let total = 1; // valueBytes adds one terminal newline.
  const add = bytes => { total += bytes; demand(total <= limit, 'Derived output union exceeds admitted reserve before serialization'); };
  function string(text) {
    let bytes = 2 + Buffer.byteLength(text);
    for (let i = 0; i < text.length; i++) {
      const c = text.charCodeAt(i);
      if (c === 34 || c === 92) bytes++;
      else if (c < 32) bytes += [8, 9, 10, 12, 13].includes(c) ? 1 : 5;
      else if (c >= 0xd800 && c <= 0xdbff && text.charCodeAt(i + 1) >= 0xdc00 && text.charCodeAt(i + 1) <= 0xdfff) i++;
      else if (c >= 0xd800 && c <= 0xdfff) bytes += 3;
    }
    add(bytes);
  }
  function visit(item) {
    if (item === null) return add(4);
    if (typeof item === 'string') return string(item);
    if (typeof item === 'boolean') return add(item ? 4 : 5);
    if (typeof item === 'number') { demand(Number.isFinite(item), 'Nonfinite derived JSON'); return add(String(item).length); }
    demand(item && typeof item === 'object', 'Non-JSON derived product');
    if (Array.isArray(item)) {
      add(2 + Math.max(0, item.length - 1));
      for (const child of item) visit(child);
    } else {
      const names = Object.keys(item); add(2 + Math.max(0, names.length - 1));
      for (const name of names) { string(name); add(1); visit(item[name]); }
    }
  }
  visit(value); return total;
}
export function planDerivedOutput(certificate, facts, baseBytes, limit = FILE) {
  demand(Number.isSafeInteger(baseBytes) && baseBytes >= 0 && Number.isSafeInteger(limit) && limit > baseBytes,
    'Invalid prospective derived output allowance');
  const decodedBytes = jsonBytes(certificate, limit - baseBytes);
  const placeholder = {path:'derived-certificate.json.gz', bytes:limit, sha256:'0'.repeat(64),
    decoded_bytes:decodedBytes, decoded_sha256:'0'.repeat(64)};
  const factsBytes = jsonBytes({...facts, certificate:placeholder}, limit);
  const publicationBytes = jsonBytes({version:1, complete:true, kind:'derived-selected-checkpoint-candidate-v1',
    accepted_checkpoint:false, validation_stage:'native-passed', certificate:placeholder,
    facts:{path:'derived-facts.json', bytes:limit, sha256:'0'.repeat(64)}, ...(facts.checkpoint_routes ? {routes:facts.checkpoint_routes} : {})}, limit);
  const encodedLimit = limit - baseBytes - decodedBytes - 2 * factsBytes - publicationBytes;
  demand(encodedLimit > 0, 'Derived output union exceeds admitted reserve before serialization');
  return {decodedBytes, encodedLimit};
}

// Transport hints are immutable candidate data, separate from scientific routes.
// The acceptance reader authenticates their contents; these descriptors never
// mint authority and stay explicit applicability/admission dependencies.
export function checkpointTransportInput(reader, name, maximum, admit, {consume = true} = {}) {
  demand(typeof name === 'string' && !path.posix.isAbsolute(name) && !name.includes('\\')
    && !name.includes('\0') && name.split('/').every(p => p && p !== '.' && p !== '..'),
  'Unsafe checkpoint transport path');
  demand(Number.isSafeInteger(maximum) && maximum > 0 && maximum <= FILE && typeof admit === 'function',
    'Bounded checkpoint transport admission required');
  reader.checkMemory();
  const tree = reader.git('ls-tree', '-z', reader.version, '--', name).toString();
  if (!tree) return {pin:{commit:reader.version, path:name, present:false, whole_body_consumed:false}, body:null};
  demand(/^100644 blob [a-f0-9]{40}\t/.test(tree) && tree.endsWith('\t' + name + '\0'),
    'Checkpoint transport input is not an ordinary Git file');
  const oid = tree.slice(12, 52), bytes = Number(reader.git('cat-file', '-s', oid));
  demand(Number.isSafeInteger(bytes) && bytes > 0 && bytes <= maximum, 'Checkpoint transport input exceeds ordinary cap');
  const pin = {commit:reader.version, path:name, present:true, mode:'100644', git_blob_oid:oid,
    bytes, whole_body_consumed:consume};
  if (!consume) return {pin, body:null};
  admit(bytes);
  const body = reader.git('cat-file', 'blob', oid);
  demand(body.length === bytes, 'Checkpoint transport changed after admission');
  pin.sha256 = sha(body);
  return {pin, body};
}

// This gate precedes authentication of every project import, so it cannot call
// the reader's allowance helper yet. Match its current measured admission here;
// parity controls exercise this bootstrap and the authenticated reader together.
export function jointExecutionAllowance({availableBytes = process.availableMemory(),
  concurrentReservedBytes = Number(process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES ?? 0),
  currentRssBytes = process.memoryUsage().rss} = {}) {
  demand([availableBytes, concurrentReservedBytes, currentRssBytes].every(value =>
    Number.isSafeInteger(value) && value >= 0), 'Invalid joint resource observations');
  const growthBytes = Math.floor((availableBytes - concurrentReservedBytes) / 2);
  demand(growthBytes > 0, 'Insufficient current joint memory after concurrent reservation and safety headroom');
  const limit = currentRssBytes + growthBytes;
  demand(Number.isSafeInteger(limit), 'Invalid joint resource observations');
  return Object.freeze({phaseBytes: limit, rssBytes: limit});
}

function executionGuard(repo, trusted) {
  demand(commit(trusted) && fs.realpathSync(repo) === fs.realpathSync(ROOT), 'Joint entry requires its actual trusted checkout');
  demand(process.execArgv.length === 1 && process.execArgv[0] === '--expose-gc'
    && process.env.NODE_OPTIONS === undefined && process.env.NODE_PATH === undefined,
  'Joint entry requires its exact trusted runtime arguments');
  const git = (...args) => execFileSync('git', ['-c', 'core.hooksPath=/dev/null', '-C', repo, ...args],
    {maxBuffer:FILE + 1, stdio:['ignore', 'pipe', 'pipe']});
  demand(git('rev-parse', 'HEAD').toString().trim() === trusted, 'Joint executing commit differs from checkout');
  const files = JOINT_CODE.map(name => {
    const file = path.join(ROOT, name); ordinaryParents(file); const stat = fs.lstatSync(file);
    demand(stat.isFile() && !stat.isSymbolicLink() && stat.size <= FILE, 'Nonordinary joint execution code');
    return {name, file, stat};
  });
  const allowance = jointExecutionAllowance();
  demand(files.reduce((sum, item) => sum + 2 * item.stat.size, 0)
    + fs.statSync(process.execPath).size + 8 * 1024 ** 2 + FILE < allowance.phaseBytes,
  'Joint code/runtime exceeds current allowance before body opens');
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
  // The genuine bootstrap binds installed Node/Git/Python once. Add the actual
  // joint modules to its complete execution charge before checkpoint body opens.
  beforeReader.executionBytes = afterReader.executionBytes = code.reduce((sum, item) => sum + item.bytes, 0);
  beforeReader.phase();
  const budget = {shared:beforeReader.budget, carriedBytes:7 * valueBytes({code, identities:startup.identities}).length + 7 * OUTPUT};
  let state, acceptedHandle;
  const accepted = await import('../../../scripts/accepted-selected-checkpoint.mjs');
  const transportInputs = [], originalCarry = budget.carriedBytes;
  let metadataCarry = 0, acquisitionCarry = 0;
  const admit = () => {
    const bytes = originalCarry + metadataCarry + acquisitionCarry;
    beforeReader.checkMemory();
    demand(Number.isSafeInteger(bytes) && beforeReader.used + bytes <= beforeReader.phaseLimit,
      'Complete accepted checkpoint transport exceeds current shared-reader allowance');
    budget.carriedBytes = bytes;
  };
  try {
    const locatorInput = checkpointTransportInput(afterReader, accepted.ACCEPTED_CHECKPOINT_LOCATOR, 4096,
      bytes => { metadataCarry += 8 * bytes; admit(); });
    transportInputs.push(locatorInput.pin);
    let qualified;
    if (locatorInput.body) {
      const locator = accepted.validateAcceptedCheckpointLocator(JSON.parse(locatorInput.body));
      const archiveName = locator.retained_artifact?.path;
      let archiveIndex;
      if (archiveName) {
        archiveIndex = transportInputs.length;
        transportInputs.push(checkpointTransportInput(afterReader, archiveName, FILE, () => {}, {consume:false}).pin);
      }
      const token = process.env.GH_TOKEN;
      if (!token) return coldDecision({cold:'baseline-and-candidate', reason:'Accepted checkpoint authenticated API access unavailable'});
      const proof = await accepted.acquireAcceptedCheckpoint({repo:process.env.GITHUB_REPOSITORY ?? 'ChengshuLi/WorldAtlas',
        locator:locator.acceptance, token,
        admit:bytes => { acquisitionCarry = Math.max(acquisitionCarry, bytes); admit(); },
        retainedArchive:archiveName ? maximum => {
          // The acquisition callback already admitted both complete ZIP copies.
          const input = checkpointTransportInput(afterReader, archiveName, maximum, () => admit());
          transportInputs[archiveIndex] = input.pin;
          demand(input.body, 'Declared retained checkpoint archive is absent');
          return input.body;
        } : undefined});
      if (!proof.available) return coldDecision({cold:'baseline-and-candidate', reason:proof.reason});
      acceptedHandle = proof.handle;
      qualified = await checkpoint.qualifyAcceptedCheckpoint({reader:beforeReader, acceptedHandle, budget});
    } else qualified = checkpoint.qualifyCheckpoint({reader:beforeReader, budget});
    if (!qualified.available) return coldDecision(qualified);
    state = qualified.state;
    const transition = checkpoint.qualifyTransition({state, reader:afterReader, budget});
    if (!transition.available) return coldDecision(transition);
    checkpoint.authenticateTransition({transition, budget});
    const nativeReport = await compareSelectedCheckpointNative({transition, budget});
    demand(nativeReport && ['native-regressions-found', 'no-new-native-loss'].includes(nativeReport.status),
      'Joint native consumer did not complete an actual comparison');
    demand(valueBytes(nativeReport).length <= OUTPUT, 'Joint native report exceeds original output reserve');
    if (nativeReport.status === 'native-regressions-found') return result(nativeReport, null);
    // Native comparison is the selected-map acceptance boundary. Do not build
    // or compare continuous polygon operands, including on no-change runs.
    budget.carriedBytes += 7 * FILE;
    const genuine = checkpoint.authenticateTransition({transition, budget});
    const authorityPaths = [P + 'supported-programs.json',
      'coordination/engineering/selected-checkpoint-reuse-20261012/accepted-checkpoints.json'];
    const authorityPins = authorityPaths.map(name => beforeReader.inventory.get(trusted + ':' + name));
    demand(authorityPins.every(pin => pin?.whole_body_consumed && /^[a-f0-9]{64}$/.test(pin.sha256)),
      'Derived custody requires actual consumed executing authority pins');
    const executingPolicy = checkpoint.checkpointExecutingPolicy({transition, budget});
    const inventory = reader => [...reader.inventory.values()].sort((a,b) =>
      (a.commit + ':' + a.path).localeCompare(b.commit + ':' + b.path));
    const routes = valueBytes(checkpoint.checkpointRouteCensus({transition, budget}));
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
    const baseBytes = 2 * routes.length;
    const archivePlan = planDerivedOutput(genuine.candidate.certificate, derivedFactsBase, baseBytes);
    const certificate = valueBytes(genuine.candidate.certificate);
    demand(certificate.length === archivePlan.decodedBytes, 'Derived certificate serialization size drift');
    const certificateEncoded = gzipSync(certificate, {level:9, mtime:0, maxOutputLength:archivePlan.encodedLimit});
    const certificatePin = {path:'derived-certificate.json.gz', bytes:certificateEncoded.length,
      sha256:sha(certificateEncoded), decoded_bytes:certificate.length, decoded_sha256:sha(certificate)};
    const derivedFacts = valueBytes({...derivedFactsBase, certificate:certificatePin});
    const derivedPublication = {version:1, complete:true, kind:'derived-selected-checkpoint-candidate-v1',
      accepted_checkpoint:false, validation_stage:'native-passed', certificate:certificatePin,
      facts:{path:'derived-facts.json', bytes:derivedFacts.length, sha256:sha(derivedFacts)}, routes:routePin};
    const derivedPublicationBody = valueBytes(derivedPublication);
    demand(certificate.length + certificateEncoded.length + 2 * derivedFacts.length + derivedPublicationBody.length + 2 * routes.length < FILE,
      'Derived native checkpoint complete outputs exceed original reserve');
    checkpoint.authenticateTransition({transition, budget});
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
  demand(Buffer.byteLength(body) <= FILE, 'Joint acknowledgement exceeds ordinary output cap');
  process.stdout.write(body);
}

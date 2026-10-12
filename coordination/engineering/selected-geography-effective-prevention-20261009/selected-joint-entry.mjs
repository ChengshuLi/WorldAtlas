// One trusted Node invocation owns checkpoint authority, native comparison and
// continuous operand production. Proposed commits are data, never imported code.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';

const ROOT = fileURLToPath(new URL('../../../', import.meta.url));
const P = 'coordination/engineering/selected-geography-effective-prevention-20261009/';
export const JOINT_CODE = Object.freeze([
  'scripts/run-geographic-check.py', 'scripts/check-geographic-regression.py',
  'scripts/check-effective-geographic-regression.mjs', 'src/ownership-codec.js',
  'scripts/evidence/immutable.py', 'scripts/evidence/geometry.py',
  'scripts/ellipsoidal_area.py', 'requirements.txt',
  P + 'selected-neighbor-prevention.mjs', P + 'selected-continuous-entry.mjs',
  P + 'selected-checkpoint.mjs', P + 'selected-checkpoint-continuous.mjs', P + 'selected-joint-entry.mjs'
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
  const available = process.availableMemory(), reserved = Number(process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES ?? 0);
  demand([available, reserved].every(value => Number.isSafeInteger(value) && value >= 0), 'Invalid joint resource observations');
  const phase = Math.floor((available - reserved - 2 * 1024 ** 3 - 768 * 1024 ** 2) / 2);
  demand(phase > 0 && files.reduce((sum, item) => sum + 2 * item.stat.size, 0)
    + fs.statSync(process.execPath).size + 8 * 1024 ** 2 + FILE < phase,
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
  const checkpoint = await import('./selected-checkpoint.mjs');
  const {checkpointContinuousOperands} = await import('./selected-checkpoint-continuous.mjs');
  const {valueBytes} = await import('./selected-neighbor-prevention.mjs');
  const startup = native.selectedBootstrap(repo, baseline, candidate, {parentRuntimePath});
  const {beforeReader, afterReader} = startup;
  // The genuine bootstrap binds installed Node/Git/Python once. Add the actual
  // joint modules to its complete execution charge before checkpoint body opens.
  beforeReader.executionBytes = afterReader.executionBytes = code.reduce((sum, item) => sum + item.bytes, 0);
  beforeReader.phase();
  const budget = {shared:beforeReader.budget, carriedBytes:7 * valueBytes({code, identities:startup.identities}).length + 7 * OUTPUT};
  let state;
  try {
    const qualified = checkpoint.qualifyCheckpoint({reader:beforeReader, budget});
    if (!qualified.available) return coldDecision(qualified);
    state = qualified.state;
    const transition = checkpoint.qualifyTransition({state, reader:afterReader, budget});
    if (!transition.available) return coldDecision(transition);
    checkpoint.authenticateTransition({transition, budget});
    const nativeReport = native.compareSelectedCheckpointNative({transition, budget});
    demand(nativeReport && ['native-regressions-found', 'no-new-native-loss'].includes(nativeReport.status),
      'Joint native consumer did not complete an actual comparison');
    demand(valueBytes(nativeReport).length <= OUTPUT, 'Joint native report exceeds original output reserve');
    if (nativeReport.status === 'native-regressions-found') return result(nativeReport, null);
    const product = checkpointContinuousOperands({transition, budget});
    const operands = valueBytes(product.operands);
    demand(operands.length < FILE, 'Joint continuous operand ordinary cap');
    const encoded = gzipSync(operands, {level:9, mtime:0, maxOutputLength:FILE - operands.length});
    const facts = valueBytes({version:1, kind:'trusted-selected-continuous-comparison-v1',
      executing_commit:trusted, baseline_commit:baseline, candidate_commit:candidate,
      execution_code:code, runtime:startup.identities, plan:transition.plan, inverse:product.inverse,
      checkpoint_custody:{baseline:product.baseline_execution, candidate:product.candidate_execution},
      source_custody:product.custody, validation_route:'authenticated-checkpoint-append-v1',
      candidate_code_executed:false});
    const publication = {version:1, complete:true, kind:'trusted-selected-continuous-comparison-v1',
      operands:{path:'operands.json.gz', bytes:encoded.length, sha256:sha(encoded), decoded_bytes:operands.length, decoded_sha256:sha(operands)},
      facts:{path:'facts.json', bytes:facts.length, sha256:sha(facts)}};
    const publicationBody = valueBytes(publication);
    demand(operands.length + encoded.length + 2 * facts.length + publicationBody.length < FILE,
      'Joint continuous complete output exceeds original reserve');
    checkpoint.authenticateTransition({transition, budget});
    executionGuard(repo, trusted); fresh(destination); fs.mkdirSync(destination);
    for (const [name, body] of [['operands.json.gz', encoded], ['facts.json', facts], ['publication.json', publicationBody]])
      fs.writeFileSync(path.join(destination, name), body, {flag:'wx', mode:0o644});
    return result(nativeReport, {version:1, kind:publication.kind,
      status:transition.changedIds.length ? 'selected-operands-complete' : 'no-selected-footprint-change',
      publication, changed_ids:transition.changedIds, complete_owners:product.complete_owners,
      affected_ids:transition.plan.required_ids, candidate_code_executed:false});
  } finally {
    if (state) checkpoint.releaseCheckpoint(state);
  }
  function coldDecision(decision) {
    return {version:1, kind:'trusted-selected-joint-comparison-v1', mode:'legacy-cold-required',
      reuse_unavailable:{cold:decision.cold, reason:decision.reason}, candidate_code_executed:false};
  }
  function result(nativeReport, continuous) {
    return {version:1, kind:'trusted-selected-joint-comparison-v1', mode:'authenticated-checkpoint-append-v1',
      native:{...nativeReport, runtime:startup.runtime, caller_runtime:startup.callerRuntime,
        execution_runtimes:startup.identities, execution_code_inventory:code}, continuous,
      candidate_code_executed:false};
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const result = await selectedJointStage(...process.argv.slice(2));
  const body = JSON.stringify(result) + '\n';
  demand(Buffer.byteLength(body) <= FILE, 'Joint acknowledgement exceeds ordinary output cap');
  process.stdout.write(body);
}

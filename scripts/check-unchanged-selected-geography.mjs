// Applicability only. The caller authenticates this module in its trusted checkout.
// Compare actual selected data, not the historical producers that issued it.
// Original authority/legality remains retained evidence; it is never replayed here.
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {createRoutingMetadataAcquisition} from './geography-routing-metadata.mjs';
import {ACCEPTED_CHECKPOINT_CODE} from './accepted-selected-checkpoint.mjs';

const PREFIX = 'coordination/engineering/selected-geography-effective-prevention-20261009/';
const CHECKPOINTS = 'coordination/engineering/selected-checkpoint-reuse-20261012/accepted-checkpoints.json';
const sha = body => createHash('sha256').update(body).digest('hex');
const oid = value => typeof value === 'string' && /^[a-f0-9]{40}$/.test(value);
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const safe = value => typeof value === 'string' && value && !value.includes('\\') && !value.includes('\0') && !path.posix.isAbsolute(value) && value.split('/').every(p => p && p !== '.' && p !== '..');
const demand = (value, message) => { if (!value) throw Error(message); };
const keys = (value, expected, role) => demand(value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).sort().join(',') === expected.split(',').sort().join(','), 'unsupported-' + role);
const array = (value, role, minimum = 1) => { demand(Array.isArray(value) && value.length >= minimum, 'unsupported-' + role); return value; };
const joined = async promises => {
  const rows = await Promise.allSettled(promises), failure = rows.find(row => row.status === 'rejected');
  if (failure) throw failure.reason;
  return rows.map(row => row.value);
};

// Queue classification imports these existing execution inventories. They
// select software regressions; they are not selected-data equality operands or
// a compatibility catalogue for historical producer schemas.
export const EXECUTION_CODE = Object.freeze([
  'scripts/run-geographic-check.py',
  'scripts/native-word-store.mjs', 'scripts/native-patch-store.mjs',  'scripts/check-effective-geographic-regression.mjs', 'scripts/selected-checkpoint-native.mjs', 'src/native-grid.js', 'src/ownership-codec.js',
  'package.json', 'package-lock.json',
  PREFIX + 'selected-neighbor-prevention.mjs',
  PREFIX + 'selected-checkpoint.mjs', PREFIX + 'selected-joint-entry.mjs',
  CHECKPOINTS, PREFIX + 'supported-programs.json', ...ACCEPTED_CHECKPOINT_CODE, 'scripts/geographic_checkpoint_products.py',
  'scripts/selected-reference-metadata.mjs', 'src/reference-metadata.js'
]);
// Preparation imports only this path vector. Keep it equal to the canonical
// current profile; the focused parity control catches literal maintenance drift.
export const REBIND_CODE = Object.freeze([
  'coordination/engineering/additive-native-gap-batch-20261008/composition-v2/compose-retained.mjs',
  'coordination/engineering/additive-native-gap-batch-20261008/composition-v2/current-geometry.mjs',
  'coordination/engineering/additive-native-gap-batch-20261008/composition-v2/current-rebind.mjs',
  PREFIX + 'selected-neighbor-prevention.mjs', 'src/effective-footprint.js',
  'scripts/check-effective-geographic-regression.mjs', 'src/ownership-codec.js', 'package.json',
  'src/native-runtime.js', 'scripts/native-ownership/compile-native-ownership.mjs', 'src/native-grid.js',
  ...['package.json', 'sha2.js', '_md.js', '_u64.js', 'utils.js'].map(p => 'coordination/engineering/additive-native-gap-batch-20261008/original-execution-custody/module-bodies/' + p),
  'scripts/audit-grid-intervals.mjs',
  ...['capture-current-rebind.mjs', 'run-current-rebind.mjs', 'issue-current-rebind-execution.py',
    'supervise-current-rebind.py', 'execution-contract.py', 'owned-group-original.py',
    'owned-child-termination-original.py', 'mac-execution-runtime-original.json', 'execution-code-paths.json']
    .map(p => 'coordination/engineering/additive-native-composition-20261009/' + p),
  'scripts/local-workspace.mjs', 'scripts/worker-identity.mjs',
  'scripts/selected-reference-metadata.mjs', 'src/reference-metadata.js'
]);

function createReader({repo, baseline, candidate, acquisition}) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('GIT_')));
  Object.assign(env, {GIT_NO_LAZY_FETCH: '1', GIT_NO_REPLACE_OBJECTS: '1', GIT_CONFIG_NOSYSTEM: '1',
    GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0', GIT_OPTIONAL_LOCKS: '0'});
  let gitCalls = 0;
  const runGit = (args, maxBuffer = Infinity) => {
    gitCalls++;
    try { return execFileSync('git', ['--no-replace-objects', '-c', 'core.hooksPath=/dev/null', '-c', 'credential.helper=', '-C', repo, ...args],
      {env, maxBuffer, timeout: 30000, stdio: ['ignore', 'pipe', 'pipe']}); }
    catch { throw Error('immutable-object-unavailable:' + args.slice(0, 4).join(':')); }
  };
  const git = (...args) => runGit(args);
  const descriptors = new Map(), metadata = new Map(), pending = new Map(), plan = new Map(), origins = new Map(), current = new Map();
  let metadataBytes = 0, metadataReads = 0, plannedBytes = 0;
  let currentChanges;
  function changedCurrentPaths() {
    if (!currentChanges) {
      // This exact tree delta authenticates unchanged paths, including modes and
      // absences, without inspecting unrelated paths or historical ancestry.
      const names = git('diff-tree', '--no-commit-id', '--name-only', '-r', '-z', '--no-renames', '--no-ext-diff', '--no-textconv', '--ignore-submodules=none', baseline, candidate)
        .toString().split('\0').filter(Boolean);
      demand(names.every(safe), 'invalid-changed-path-inventory');
      const ancestors = new Set();
      for (const name of names) {
        const parts = name.split('/');
        for (let i = 1; i < parts.length; i++) ancestors.add(parts.slice(0, i).join('/'));
      }
      currentChanges = {names: new Set(names), ancestors};
    }
    return currentChanges;
  }
  function unchangedCurrentPath(name) {
    const changes = changedCurrentPaths(), parts = name.split('/');
    return !changes.names.has(name) && !changes.ancestors.has(name)
      && !parts.some((_, i) => i > 0 && changes.names.has(parts.slice(0, i).join('/')));
  }
  function descriptor(commit, name, optional = false) {
    demand(oid(commit) && safe(name), 'unsafe-immutable-locator');
    const key = commit + ':' + name;
    if (!descriptors.has(key)) {
      if (commit === candidate && descriptors.has(baseline + ':' + name) && unchangedCurrentPath(name)) {
        const before = descriptors.get(baseline + ':' + name);
        descriptors.set(key, before ? {...before, commit: candidate} : null);
      } else {
        const raw = git('ls-tree', '-z', commit, '--', name).toString();
        if (!raw) descriptors.set(key, null);
        else {
          const match = raw.match(/^(100644|100755) blob ([a-f0-9]{40})\t([^\0]+)\0$/);
          demand(match && match[3] === name, 'nonordinary-immutable-input');
          descriptors.set(key, {commit, path: name, mode: match[1], git_blob_oid: match[2]});
        }
      }
    }
    const result = descriptors.get(key);
    demand(optional || result, 'missing-required-input');
    return result;
  }
  function equalCurrent(name, optional = false) {
    const before = descriptor(baseline, name, optional), after = descriptor(candidate, name, optional);
    demand((before === null && after === null) || before && after && before.mode === after.mode && before.git_blob_oid === after.git_blob_oid, 'changed-current-input:' + name);
    current.set(name, before ? {path: name, mode: before.mode, git_blob_oid: before.git_blob_oid} : {path: name, absent: true});
    return before;
  }
  async function originalDescriptor(commit, name) {
    try { return descriptor(commit, name); }
    catch (error) {
      // Only unavailable Git metadata can request transport. Missing paths,
      // nonordinary entries and identity disagreements remain refusals.
      if (!error.message.startsWith('immutable-object-unavailable:') || !acquisition.resolvePath) throw error;
      const resolved = await acquisition.resolvePath(commit, name);
      demand(resolved?.commit === commit && resolved.path === name && ['100644', '100755'].includes(resolved.mode)
        && oid(resolved.git_blob_oid), 'invalid-original-descriptor');
      const result = {commit, path: name, mode: resolved.mode, git_blob_oid: resolved.git_blob_oid};
      descriptors.set(commit + ':' + name, result);
      return result;
    }
  }
  async function body(pin, expected) {
    // Each role still authenticates its own origin/path/mode and expected hash.
    // Only the immutable raw body is shared by OID within this invocation.
    const key = pin.git_blob_oid;
    function admit(size) {
      demand(Number.isSafeInteger(size) && size > 0, 'invalid-metadata-length');
      demand(!plan.has(key) || plan.get(key) === size, 'metadata-pin-length');
      if (!plan.has(key)) {
        demand(Number.isSafeInteger(plannedBytes + size), 'invalid-metadata-total');
        plan.set(key, size); plannedBytes += size;
      }
    }
    let raw = metadata.get(key);
    if (!raw) {
      if (!pending.has(key)) pending.set(key, (async () => {
        // Existing parent-declared sizes admit pinned bodies before acquisition;
        // fixed roots without a size use the transport's exact tree-size admission.
        if (expected?.bytes !== undefined) admit(expected.bytes);
        let size;
        try { size = Number(git('cat-file', '-s', pin.git_blob_oid)); }
        catch {
          await acquisition.acquire(pin, expected);
          size = Number(git('cat-file', '-s', pin.git_blob_oid));
        }
        admit(size);
        const raw = runGit(['cat-file', 'blob', pin.git_blob_oid], size + 1);
        demand(raw.length === size, 'metadata-length-drift');
        demand(createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex') === pin.git_blob_oid, 'metadata-git-object-identity');
        metadataBytes += size; metadataReads++;
        metadata.set(key, raw);
        return raw;
      })());
      try { raw = await pending.get(key); }
      finally { pending.delete(key); }
    }
    demand(!expected || expected.bytes === undefined || expected.bytes === raw.length, 'metadata-pin-length');
    demand(!expected || !expected.sha256 || hash(expected.sha256) && expected.sha256 === sha(raw), 'metadata-pin-hash');
    return raw;
  }
  function originExists(commit) {
    demand(oid(commit), 'unsupported-historical-commit');
    if (!origins.has(commit)) {
      try { git('cat-file', '-e', commit + '^{commit}'); origins.set(commit, true); }
      catch { origins.set(commit, false); }
    }
    return origins.get(commit);
  }
  async function pinned(value) {
    demand(value && oid(value.commit) && safe(value.path) && ['100644', '100755'].includes(value.mode)
      && oid(value.git_blob_oid ?? value.blob) && Number.isSafeInteger(value.bytes) && value.bytes > 0 && hash(value.sha256), 'unsupported-historical-pin');
    // Compare candidate-visible aliases, including absence. An unavailable
    // original can use the retained current copy only at its exact pinned OID.
    // Never acquire an old producer graph to prove an unchanged output.
    const current = equalCurrent(value.path, true);
    const aliasMatches = current && current.mode === value.mode && current.git_blob_oid === (value.git_blob_oid ?? value.blob);
    const actual = originExists(value.commit) || !aliasMatches
      ? await originalDescriptor(value.commit, value.path) : current;
    demand(actual.mode === value.mode && actual.git_blob_oid === (value.git_blob_oid ?? value.blob), 'historical-pin-identity');
    return actual;
  }
  const jsonAt = async (pin, expected) => JSON.parse(await body(pin, expected));
  const currentJson = (name, expected) => jsonAt(equalCurrent(name), expected);
  function currentPin(value) {
    demand(value && safe(value.path) && Number.isSafeInteger(value.bytes) && value.bytes > 0 && hash(value.sha256), 'unsupported-current-pin');
    const p = equalCurrent(value.path);
    demand(value.mode === undefined || value.mode === p.mode, 'current-pin-mode');
    return p;
  }
  return {git, descriptor, originalDescriptor, equalCurrent, currentJson, currentPin, pinned, jsonAt, originExists,
    summary() {
      const rows = [...descriptors.values()].filter(Boolean).sort((a, b) => (a.commit + ':' + a.path).localeCompare(b.commit + ':' + b.path));
      const alternatives = [...current.values()].sort((a, b) => a.path.localeCompare(b.path));
      return {immutable_descriptors: rows, current_and_absent_alternatives: alternatives,
        identity_sha256: sha(Buffer.from(JSON.stringify({rows, alternatives}))),
        git_calls: gitCalls, metadata_bytes_read: metadataBytes, metadata_bodies_read: metadataReads,
        metadata_unique_bodies: plan.size, metadata_planned_bytes: plannedBytes,
        historical_commit_availability: [...origins].sort(([a], [b]) => a.localeCompare(b))};
    }};
}

async function collect(reader) {
  // Only actual selected inputs determine applicability. Unrelated authored
  // changes and their ancestry are not scientific operands.
  // The accepted catalogue is authority data, separate from executing software.
  reader.equalCurrent(CHECKPOINTS);
  // Optional checkpoint locators/archives choose reusable proof transport;
  // they are not scientific operands. Actual use still authenticates acquisition.
  // These roots determine the actual selected source/native operands. Their
  // immutable bindings are sufficient for an applicability decision; historical
  // authority schemas, producer inputs and rebind execution are not operands.
  const world = await reader.currentJson('data/world-index.json');
  const parts = array(world.parts, 'world-parts');
  demand(new Set(parts).size === parts.length && parts.every(safe), 'unsupported-world-parts');
  for (const name of parts) reader.equalCurrent('data/' + name);
  for (const name of ['data/hierarchy.json', 'data/canonical-grid/manifest.json', 'data/geographic-releases/index.json']) reader.equalCurrent(name);
  const pointer = await reader.currentJson('data/geographic-releases/current-manifest.json');
  demand(safe(pointer.path) && hash(pointer.sha256) && !pointer.path.startsWith('data/'), 'unsupported-release-pointer');
  reader.equalCurrent('data/geographic-releases/' + pointer.path);
  const selection = await reader.currentJson('data/ownership-selection.json');
  keys(selection, 'manifest_path,method,release_id,sha256,version' + ['selected_geography', 'additive_release', 'artifact_consumption', 'reference_projection'].filter(k => Object.hasOwn(selection, k)).map(k => ',' + k).join(''), 'selection');
  demand(selection.version === 1 && selection.method === 'native-linear-evenodd-first-owner-v1' && safe(selection.manifest_path), 'unsupported-selection');
  await joined([reader.currentJson(selection.manifest_path, {sha256: selection.sha256}),
    ...(selection.selected_geography ? [reader.currentJson(selection.selected_geography.path, selection.selected_geography)] : []),
    ...(selection.additive_release ? [reader.jsonAt(reader.currentPin(selection.additive_release), selection.additive_release)] : []),
    ...(selection.artifact_consumption ? [reader.jsonAt(reader.currentPin(selection.artifact_consumption.certificate), selection.artifact_consumption.certificate)] : [])]);
  const manifest = await reader.currentJson(selection.manifest_path, {sha256: selection.sha256});
  demand(manifest.version === 2 && manifest.method === selection.method, 'unsupported-native-manifest');
  const nativeParts = array(manifest.parts, 'native-parts');
  for (const p of nativeParts) {
    demand(safe(p.path) && ['runs', 'rows'].includes(p.kind), 'unsupported-native-part');
    reader.equalCurrent(path.posix.join(path.posix.dirname(selection.manifest_path), p.path), true);
  }
  const bounds = manifest.original_assets?.bounds;
  demand(bounds && oid(bounds.commit) && bounds.path === 'data/canonical-grid/bounds.json.gz', 'unsupported-owner-roster');
  await reader.originalDescriptor(bounds.commit, bounds.path);
  const verified = await reader.currentJson('scripts/native-ownership/verified-candidates.json');
  const receipt = verified.candidates?.[selection.sha256];
  demand(verified.version === 1 && receipt?.role === 'reviewed-exhaustive-native-rule-comparison' && oid(receipt.commit) && safe(receipt.path), 'unsupported-native-receipt');
  // This historical receipt has no declared Git OID/mode; its retained location
  // still requires exact before/after identity and its origin remains explicit.
  reader.equalCurrent(receipt.path, true);
  if (reader.originExists(receipt.commit)) await reader.originalDescriptor(receipt.commit, receipt.path);
  else reader.equalCurrent(receipt.path);
  const transport = manifest.native_asset_transport;
  keys(transport, 'index,kind,logical_assets,original_compressed_bytes,version', 'native-transport');
  demand(transport.version === 1 && transport.kind === 'ordered-exact-original-byte-fragments', 'unsupported-native-transport');
  const index = await reader.currentJson(transport.index.path, transport.index);
  demand(index.version === 1 && index.kind === transport.kind, 'unsupported-native-index');
  for (const p of array(index.parts, 'native-fragments')) {
    demand(safe(p.path), 'unsupported-native-fragment');
    reader.equalCurrent(path.posix.join(path.posix.dirname(transport.index.path), p.path));
  }
  const declared = selection.selected_geography;
  keys(declared, 'bytes,kind,path,sha256,version', 'selected-source-map');
  demand(declared.version === 1 && declared.kind === 'complete-world-index-with-exact-encoded-overrides', 'unsupported-selected-source-map');
  const bank = await reader.currentJson(declared.path, declared);
  demand(bank.version === 1 && bank.kind === declared.kind, 'unsupported-selected-source-bank');
  for (const p of [bank.world_index, ...array(bank.unchanged_files, 'unchanged-sources', 0), ...array(bank.overrides, 'source-overrides', 0)]) await reader.pinned(p);
  if (selection.reference_projection !== undefined) {
    // Reference metadata is an existing selected input. Compare its complete
    // body and every immutable operand/current alias used by the real reader;
    // unchanged applicability does not repeat the metadata qualification.
    const declared = selection.reference_projection;
    keys(declared, 'bytes,path,sha256', 'reference-projection-pin');
    const pin = reader.currentPin(declared);
    demand(pin.mode === '100644', 'nonordinary-reference-projection');
    const projection = await reader.jsonAt(pin, declared);
    demand(projection.version === 1 && projection.kind === 'native-reference-metadata-projection-v1', 'unsupported-reference-projection');
    keys(projection.hierarchy, 'before,after', 'reference-hierarchy');
    const inputs = [...Object.values(projection.hierarchy), ...array(projection.receipts, 'reference-receipts')];
    for (const update of array(projection.source_updates, 'reference-source-updates', 0)) {
      keys(update, 'after,before,logical_path', 'reference-source-update');
      demand(safe(update.logical_path), 'unsupported-reference-source-path');
      reader.equalCurrent(update.logical_path);
      inputs.push(update.before, update.after);
    }
    for (const input of inputs) {
      demand(input?.mode === '100644', 'nonordinary-reference-input');
      await reader.pinned(input);
    }
  }
  if (selection.artifact_consumption !== undefined) {
    const hook = selection.artifact_consumption;
    keys(hook, 'certificate,review', 'artifact-hook');
    reader.currentPin(hook.review);
    const certificate = await reader.jsonAt(reader.currentPin(hook.certificate), hook.certificate);
    demand(certificate.version === 1 && certificate.kind === 'qualified-arctic-immutable-product-certificate-v1', 'unsupported-artifact-certificate');
    for (const p of [certificate.application_consumer_code, certificate.qualification_inventory]) reader.currentPin(p);
    if (certificate.release_product_catalogue !== undefined) {
      reader.currentPin(certificate.release_product_catalogue);
      reader.currentPin(certificate.selected_artifact_bindings?.registry);
    }
  }
  if (selection.additive_release !== undefined) {
    const sidecar = await reader.jsonAt(reader.currentPin(selection.additive_release), selection.additive_release);
    keys(sidecar, 'authority_registry,base_selection,kind,logical_asset_map,runtime_envelope,version', 'additive-sidecar');
    demand(sidecar.version === 2 && sidecar.kind === 'retained-native-additive-selection-v2', 'unsupported-additive-sidecar');
    keys(sidecar.logical_asset_map, 'base_manifest,ledger,owner_roster,patch', 'additive-assets');
    for (const p of [sidecar.runtime_envelope, ...Object.values(sidecar.logical_asset_map)]) await reader.pinned(p);
    // Registry and ledger are actual selected outputs. Bind their complete
    // immutable bodies, without recursively interpreting the original producer
    // or rerunning its authority checks for an unchanged result.
    await reader.pinned(sidecar.authority_registry);
  }
}

export async function inspectUnchangedSelectedGeography({repo, baseline, candidate, trusted = baseline, acquisition, verifyExecutingCheckout = false}) {
  const report = {version: 1, kind: 'trusted-unchanged-selected-geography-v1', baseline_commit: baseline,
    candidate_commit: candidate, trusted_reader_policy_commit: trusted, candidate_code_executed: false,
    science_reexecuted: false, source_approval: false, published: false};
  try {
    demand(oid(baseline) && oid(candidate) && oid(trusted), 'require-immutable-commits');
    demand(baseline !== candidate, 'baseline-proof-requires-full-check');
    acquisition ??= createRoutingMetadataAcquisition({repo, baseline});
    const reader = createReader({repo, baseline, candidate, acquisition});
    if (verifyExecutingCheckout) demand(reader.git('rev-parse', 'HEAD').toString().trim() === trusted, 'executing-checkout-mismatch');
    await collect(reader);
    const result = {...report, status: 'unchanged-selected-inputs', ...reader.summary(), metadata_acquisition: acquisition.summary(),
      limits: ['Exact immutable selected-data applicability under one executing checkout only; no historical legality, fresh native, polygon, source-authority, publication or consumer validation.',
        'Changed selected data, unsupported selector/asset layouts and missing or mismatched bindings retain the original full checker.']};
    return result;
  } catch (error) {
    return {...report, status: 'full-check-required', ...(acquisition ? {metadata_acquisition: acquisition.summary()} : {}), reason: error instanceof SyntaxError ? 'invalid-routing-metadata' : String(error.message).slice(0, 512)};
  }
}

// Production callers bind policy/code identity to the actual immutable checkout.
// The lower-level collector remains available for isolated routing fixtures.
export function inspectExecutingSelectedGeography(options) {
  return inspectUnchangedSelectedGeography({...options, verifyExecutingCheckout: true});
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [repo, baseline, candidate, trusted] = process.argv.slice(2);
  process.stdout.write(JSON.stringify(await inspectExecutingSelectedGeography({repo, baseline, candidate, ...(trusted ? {trusted} : {})})) + '\n');
}

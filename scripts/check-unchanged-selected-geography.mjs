// Applicability only. The caller authenticates this module in its trusted checkout.
// These explicit roles mirror the audited readers below, including detached
// SOURCE/NATIVE readers. No candidate module or scientific body is executed.
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';

const PREFIX = 'coordination/engineering/selected-geography-effective-prevention-20261009/';
const POLICY = PREFIX + 'supported-programs.json';
const HANDOFFS = 'coordination/engineering/melanesia363-additive-delivery-20261010/accepted-administrative-handoffs.json';
const FILE = 32 * 1024 * 1024, METADATA = 64 * 1024 * 1024, ENTRIES = 4096;
const sha = body => createHash('sha256').update(body).digest('hex');
const oid = value => typeof value === 'string' && /^[a-f0-9]{40}$/.test(value);
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const safe = value => typeof value === 'string' && value && !value.includes('\\') && !value.includes('\0') && !path.posix.isAbsolute(value) && value.split('/').every(p => p && p !== '.' && p !== '..');
const demand = (value, message) => { if (!value) throw Error(message); };
const keys = (value, expected, role) => demand(value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).sort().join(',') === expected.split(',').sort().join(','), 'unsupported-' + role);
const array = (value, role, minimum = 1) => { demand(Array.isArray(value) && value.length >= minimum && value.length <= 512, 'unsupported-' + role); return value; };
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(k => [k, canonical(value[k])])) : value;
const same = (a, b) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));

// A later trusted reader may introduce another input route. Equal candidate code
// alone cannot prove this older collector complete for that new reader. Updating
// these profiles therefore requires reviewing its reads and the adverse tests.
export const AUDITED_READERS = Object.freeze({
  'src/ownership-codec.js': ['64630f340a2815d5c86706cc4456718054990083d1026e0b420dd8f9f02f593d'],
  'scripts/check-effective-geographic-regression.mjs': ['801ad9f05a8d7f34ae591ee78a09b71c87090acd4d20c92c9831152528a9c039'],
  // The second profile is reviewed stage-2 blob f8e4a88a6dbe3d3961d6b17d9b926ee4488561a8:
  // catalogue/admission/peak accounting changes; all input routes are identical.
  [PREFIX + 'selected-neighbor-prevention.mjs']: ['63745cc5d4f15bdd8c153787df07379d813ab037fc1e0734944a75568235e8aa',
    '6da5919c63822393959afc8f2499c76470aa6b51d6e29664d372e9eee79ae4b1'],
  [PREFIX + 'selected-continuous-entry.mjs']: ['84ddc84798fa371e37c0acbd6764a39ef79296f3b8a57ff09aa4ed416e7ae1b9']
});
export const EXECUTION_CODE = Object.freeze([
  'scripts/run-geographic-check.py', 'scripts/check-geographic-regression.py',
  'scripts/check-effective-geographic-regression.mjs', 'src/ownership-codec.js',
  'scripts/evidence/immutable.py', 'scripts/evidence/geometry.py',
  'scripts/ellipsoidal_area.py', 'requirements.txt', 'package.json', 'package-lock.json',
  PREFIX + 'selected-neighbor-prevention.mjs', PREFIX + 'selected-continuous-entry.mjs'
]);
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
  'scripts/local-workspace.mjs', 'scripts/worker-identity.mjs'
]);

function createReader({repo, baseline, candidate, trusted, limits}) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('GIT_')));
  Object.assign(env, {GIT_NO_LAZY_FETCH: '1', GIT_NO_REPLACE_OBJECTS: '1', GIT_CONFIG_NOSYSTEM: '1',
    GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0', GIT_OPTIONAL_LOCKS: '0'});
  const git = (...args) => {
    try { return execFileSync('git', ['--no-replace-objects', '-c', 'core.hooksPath=/dev/null', '-c', 'credential.helper=', '-C', repo, ...args],
      {env, maxBuffer: limits.member + 1024, timeout: 30000, stdio: ['ignore', 'pipe', 'pipe']}); }
    catch { throw Error('immutable-object-unavailable:' + args.slice(0, 4).join(':')); }
  };
  const descriptors = new Map(), metadata = new Map(), origins = new Map(), current = new Map();
  let metadataBytes = 0;
  function descriptor(commit, name, optional = false) {
    demand(oid(commit) && safe(name), 'unsafe-immutable-locator');
    const key = commit + ':' + name;
    if (!descriptors.has(key)) {
      demand(descriptors.size < limits.entries, 'identity-entry-limit');
      const raw = git('ls-tree', '-z', commit, '--', name).toString();
      if (!raw) descriptors.set(key, null);
      else {
        const match = raw.match(/^(100644|100755) blob ([a-f0-9]{40})\t([^\0]+)\0$/);
        demand(match && match[3] === name, 'nonordinary-immutable-input');
        descriptors.set(key, {commit, path: name, mode: match[1], git_blob_oid: match[2]});
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
  function body(pin, expected) {
    const key = pin.commit + ':' + pin.path;
    if (!metadata.has(key)) {
      const size = Number(git('cat-file', '-s', pin.git_blob_oid));
      demand(Number.isSafeInteger(size) && size > 0 && size <= limits.member && metadataBytes + size <= limits.metadata, 'metadata-byte-limit');
      metadataBytes += size;
      const raw = git('cat-file', 'blob', pin.git_blob_oid);
      demand(raw.length === size, 'metadata-length-drift');
      demand(createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex') === pin.git_blob_oid, 'metadata-git-object-identity');
      metadata.set(key, raw);
    }
    const raw = metadata.get(key);
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
  function pinned(value, {fallback = true} = {}) {
    demand(value && oid(value.commit) && safe(value.path) && ['100644', '100755'].includes(value.mode)
      && oid(value.git_blob_oid ?? value.blob) && Number.isSafeInteger(value.bytes) && value.bytes > 0 && value.bytes <= limits.member && hash(value.sha256), 'unsupported-historical-pin');
    // Protect even the currently unused retained alias, including its absence.
    // A later object hydration must not expose a candidate-only alternative.
    if (fallback) equalCurrent(value.path, true);
    const version = originExists(value.commit) ? value.commit : fallback ? baseline : null;
    demand(version, 'missing-strict-historical-commit');
    const actual = descriptor(version, value.path);
    demand(actual.mode === value.mode && actual.git_blob_oid === (value.git_blob_oid ?? value.blob), 'historical-pin-identity');
    return actual;
  }
  const jsonAt = (pin, expected) => JSON.parse(body(pin, expected));
  const currentJson = (name, expected) => jsonAt(equalCurrent(name), expected);
  const pinnedJson = (value, options) => jsonAt(pinned(value, options), value);
  function currentPin(value) {
    demand(value && safe(value.path) && Number.isSafeInteger(value.bytes) && value.bytes > 0 && value.bytes <= limits.member && hash(value.sha256), 'unsupported-current-pin');
    const p = equalCurrent(value.path);
    demand(value.mode === undefined || value.mode === p.mode, 'current-pin-mode');
    return p;
  }
  return {git, descriptor, equalCurrent, currentJson, currentPin, pinned, pinnedJson, jsonAt, body, originExists,
    trustedJson(name) { return jsonAt(descriptor(trusted, name)); },
    summary() {
      const rows = [...descriptors.values()].filter(Boolean).sort((a, b) => (a.commit + ':' + a.path).localeCompare(b.commit + ':' + b.path));
      const alternatives = [...current.values()].sort((a, b) => a.path.localeCompare(b.path));
      return {immutable_descriptors: rows, current_and_absent_alternatives: alternatives,
        identity_sha256: sha(Buffer.from(JSON.stringify({rows, alternatives}))),
        metadata_bytes_read: metadataBytes, metadata_bodies_read: metadata.size,
        historical_commit_availability: [...origins].sort(([a], [b]) => a.localeCompare(b))};
    }};
}

function originalAuthority(reader, entry) {
  keys(entry, 'authority_sha256,policy_id,policy_version,rule_preimage,rule_sha256,source_authority', 'authority-entry');
  reader.pinned(entry.rule_preimage);
  const binding = reader.pinnedJson(entry.source_authority);
  keys(binding, 'kind,native_proof,original_pins,version' + (Object.hasOwn(binding, 'source_output_aliases') ? ',source_output_aliases' : ''), 'authority-binding');
  demand(binding.version === 1 && binding.kind === 'original-issued-rule-source-custody-v1', 'unsupported-authority-binding');
  keys(binding.original_pins, 'ledger,native_facts,native_manifest,native_request,source_facts,source_request', 'original-custody');
  for (const p of Object.values(binding.original_pins)) reader.pinned(p);
  const request = reader.pinnedJson(binding.original_pins.native_request);
  const source = reader.pinnedJson(binding.original_pins.source_request);
  demand(['unactivated-additive-native-release-v1', 'unactivated-additive-native-batch-v1'].includes(request.operation)
    && source.operation === 'retained-land-source-premises-v1', 'unsupported-original-programme');
  const aliases = new Map();
  for (const alias of array(binding.source_output_aliases ?? [], 'source-aliases', 0)) {
    keys(alias, 'original,published', 'source-alias');
    demand(safe(alias.original?.path) && !aliases.has(alias.original.path), 'unsupported-source-alias');
    reader.pinned(alias.published, {fallback: false});
    aliases.set(alias.original.path, alias.published);
  }
  const spec = request.additive;
  const inputs = array(spec?.inputs, 'original-source-inputs');
  for (const role of ['publication_path', 'inventory_path', 'operating_path']) {
    demand(safe(spec[role]), 'unsupported-original-source-role');
    const matches = inputs.filter(p => p.path === spec[role]);
    demand(matches.length === 1, 'ambiguous-original-source-role');
    reader.pinned(aliases.get(matches[0].path) ?? matches[0]);
  }
  keys(binding.native_proof, 'assets,inventory,operating,publication', 'native-proof');
  for (const p of [binding.native_proof.inventory, binding.native_proof.operating,
    binding.native_proof.publication, ...array(binding.native_proof.assets, 'native-assets')]) reader.pinned(p);
  // originalAdministrativeBaseline alone opens these historical selectors/maps;
  // it never treats the original SOURCE scientific input roster as current paths.
  if (!same(source.baseline, request.baseline)) {
    demand(source.source_rule?.profile === 'retained-consumed-administrative-source'
      && request.additive.source_profile === 'retained-consumed-administrative-source', 'unsupported-baseline-split');
    for (const baseline of [source.baseline, request.baseline]) {
      keys(baseline, 'kind,pins,version', 'original-baseline');
      demand(baseline.version === 2 && baseline.kind === 'current-selected-native-baseline-v1' && baseline.pins?.length === 1
        && baseline.pins[0].path === 'data/ownership-selection.json', 'unsupported-original-baseline');
    }
    reader.pinned(source.baseline.pins[0], {fallback: false});
    const selectorPin = request.baseline.pins[0];
    const selector = reader.pinnedJson(selectorPin, {fallback: false});
    demand(selector.selected_geography?.kind === 'complete-world-index-with-exact-encoded-overrides' && safe(selector.selected_geography.path), 'unsupported-original-source-map');
    reader.descriptor(selectorPin.commit, selector.selected_geography.path);
  }
}

function currentRebind(reader, pin, sourcePaths) {
  const certificate = reader.pinnedJson(pin, {fallback: false});
  keys(certificate, 'authority_registry_sha256,base_selection,execution_commit,facts,kind,operating,publication,request,result,version', 'current-rebind');
  demand(certificate.version === 1 && certificate.kind === 'qualified-native-additive-current-bank-rebind-v1' && oid(certificate.execution_commit), 'unsupported-current-rebind');
  for (const role of ['request', 'facts', 'publication', 'operating', 'result']) reader.pinned(certificate[role], {fallback: false});
  for (const name of REBIND_CODE) { reader.equalCurrent(name); reader.descriptor(certificate.execution_commit, name); }
  const request = reader.pinnedJson(certificate.request, {fallback: false});
  const operating = reader.pinnedJson(certificate.operating, {fallback: false});
  keys(operating.execution_custody, 'code_source,terminal,stderr,stdout,issued_plan', 'external-custody');
  for (const p of Object.values(operating.execution_custody)) reader.pinned(p, {fallback: false});
  const plan = reader.pinnedJson(operating.execution_custody.issued_plan, {fallback: false});
  if (plan.original_inputs !== undefined) for (const p of array(plan.original_inputs, 'issued-original-inputs', 0)) reader.pinned(p, {fallback: false});
  demand(request.acquisition && Array.isArray(request.acquisition.target_sources), 'unsupported-rebind-acquisition');
  for (const target of request.acquisition.target_sources) {
    keys(target, 'path,target_id', 'rebind-source-target');
    demand(sourcePaths.includes(target.path), 'unsupported-rebind-source-target');
  }
  if (request.acquisition.predecessor_proof != null) reader.pinned(request.acquisition.predecessor_proof);
  // target_sources may select only members of the independently collected whole
  // selected source bank; it cannot introduce another physical input locator.
}

function collect(reader, {baseline, candidate, trusted}) {
  // This is an eligibility bound, not input equivalence. Compare the authored
  // diff from its real merge base; all consumed identities below still compare
  // the exact supplied baseline and candidate, including baseline-only changes.
  const mergeBase = reader.git('merge-base', baseline, candidate).toString().trim();
  demand(oid(mergeBase), 'source-scope-merge-base-unavailable');
  const changed = reader.git('diff-tree', '--no-commit-id', '--name-only', '-r', '-z', '--no-renames', mergeBase, candidate).toString().split('\0').filter(Boolean);
  demand(changed.length > 0 && changed.length <= 512 && changed.every(name => safe(name)
    && (name.startsWith('research/geography/') || name.startsWith('data/regional-review/'))), 'outside-source-publication-scope');
  for (const name of changed) {
    // Addition/deletion are permitted only as ordinary source-packet entries.
    reader.descriptor(mergeBase, name, true);
    reader.descriptor(candidate, name, true);
  }
  for (const name of EXECUTION_CODE) reader.equalCurrent(name);
  reader.equalCurrent('scripts/check-unchanged-selected-geography.mjs', true);
  for (const [name, allowed] of Object.entries(AUDITED_READERS)) {
    const raw = reader.body(reader.descriptor(trusted, name));
    demand(allowed.includes(sha(raw)), 'unsupported-reader-profile:' + name);
  }
  // The original reader uses executing-checkout policy for BOTH selections.
  const programme = reader.trustedJson(POLICY);
  demand(programme.version === 1 && programme.kind === 'trusted-source-native-programmes-v1', 'unsupported-programme-catalogue');
  const handoffs = reader.currentJson(HANDOFFS);
  demand(handoffs.version === 1 && handoffs.kind === 'accepted-administrative-handoffs-v1', 'unsupported-handoff-registry');
  for (const row of array(handoffs.entries, 'administrative-handoffs')) {
    reader.pinned({...row.source, commit: row.accepted_source_commit});
  }
  const world = reader.currentJson('data/world-index.json');
  const parts = array(world.parts, 'world-parts');
  demand(new Set(parts).size === parts.length && parts.every(safe), 'unsupported-world-parts');
  for (const name of parts) reader.equalCurrent('data/' + name);
  for (const name of ['data/hierarchy.json', 'data/canonical-grid/manifest.json', 'data/geographic-releases/index.json']) reader.equalCurrent(name);
  const pointer = reader.currentJson('data/geographic-releases/current-manifest.json');
  demand(safe(pointer.path) && hash(pointer.sha256) && !pointer.path.startsWith('data/'), 'unsupported-release-pointer');
  reader.equalCurrent('data/geographic-releases/' + pointer.path);
  const selection = reader.currentJson('data/ownership-selection.json');
  keys(selection, 'manifest_path,method,release_id,sha256,version' + ['selected_geography', 'additive_release', 'artifact_consumption'].filter(k => Object.hasOwn(selection, k)).map(k => ',' + k).join(''), 'selection');
  demand(selection.version === 1 && selection.method === 'native-linear-evenodd-first-owner-v1' && safe(selection.manifest_path), 'unsupported-selection');
  const manifest = reader.currentJson(selection.manifest_path, {sha256: selection.sha256});
  demand(manifest.version === 2 && manifest.method === selection.method, 'unsupported-native-manifest');
  const nativeParts = array(manifest.parts, 'native-parts');
  for (const p of nativeParts) {
    demand(safe(p.path) && ['runs', 'rows'].includes(p.kind), 'unsupported-native-part');
    reader.equalCurrent(path.posix.join(path.posix.dirname(selection.manifest_path), p.path), true);
  }
  const bounds = manifest.original_assets?.bounds;
  demand(bounds && oid(bounds.commit) && bounds.path === 'data/canonical-grid/bounds.json.gz', 'unsupported-owner-roster');
  reader.descriptor(bounds.commit, bounds.path);
  const verified = reader.currentJson('scripts/native-ownership/verified-candidates.json');
  const receipt = verified.candidates?.[selection.sha256];
  demand(verified.version === 1 && receipt?.role === 'reviewed-exhaustive-native-rule-comparison' && oid(receipt.commit) && safe(receipt.path), 'unsupported-native-receipt');
  // This historical receipt has no declared Git OID/mode; its retained location
  // still requires exact before/after identity and its origin remains explicit.
  reader.equalCurrent(receipt.path, true);
  if (reader.originExists(receipt.commit)) reader.descriptor(receipt.commit, receipt.path);
  else reader.equalCurrent(receipt.path);
  const transport = manifest.native_asset_transport;
  keys(transport, 'index,kind,logical_assets,original_compressed_bytes,version', 'native-transport');
  demand(transport.version === 1 && transport.kind === 'ordered-exact-original-byte-fragments', 'unsupported-native-transport');
  const index = reader.currentJson(transport.index.path, transport.index);
  demand(index.version === 1 && index.kind === transport.kind, 'unsupported-native-index');
  for (const p of array(index.parts, 'native-fragments')) {
    demand(safe(p.path), 'unsupported-native-fragment');
    reader.equalCurrent(path.posix.join(path.posix.dirname(transport.index.path), p.path));
  }
  const declared = selection.selected_geography;
  keys(declared, 'bytes,kind,path,sha256,version', 'selected-source-map');
  demand(declared.version === 1 && declared.kind === 'complete-world-index-with-exact-encoded-overrides', 'unsupported-selected-source-map');
  const bank = reader.currentJson(declared.path, declared);
  demand(bank.version === 1 && bank.kind === declared.kind, 'unsupported-selected-source-bank');
  for (const p of [bank.world_index, ...array(bank.unchanged_files, 'unchanged-sources', 0), ...array(bank.overrides, 'source-overrides', 0)]) reader.pinned(p);
  if (selection.artifact_consumption !== undefined) {
    const hook = selection.artifact_consumption;
    keys(hook, 'certificate,review', 'artifact-hook');
    reader.currentPin(hook.review);
    const certificate = reader.jsonAt(reader.currentPin(hook.certificate), hook.certificate);
    demand(certificate.version === 1 && certificate.kind === 'qualified-arctic-immutable-product-certificate-v1', 'unsupported-artifact-certificate');
    for (const p of [certificate.application_consumer_code, certificate.qualification_inventory]) reader.currentPin(p);
    if (certificate.release_product_catalogue !== undefined) {
      reader.currentPin(certificate.release_product_catalogue);
      reader.currentPin(certificate.selected_artifact_bindings?.registry);
    }
  }
  if (selection.additive_release !== undefined) {
    const sidecar = reader.jsonAt(reader.currentPin(selection.additive_release), selection.additive_release);
    keys(sidecar, 'authority_registry,base_selection,kind,logical_asset_map,runtime_envelope,version', 'additive-sidecar');
    demand(sidecar.version === 2 && sidecar.kind === 'retained-native-additive-selection-v2', 'unsupported-additive-sidecar');
    keys(sidecar.logical_asset_map, 'base_manifest,ledger,owner_roster,patch', 'additive-assets');
    for (const p of [sidecar.runtime_envelope, ...Object.values(sidecar.logical_asset_map)]) reader.pinned(p);
    const registry = reader.pinnedJson(sidecar.authority_registry);
    demand(registry.version === 1 && registry.kind === 'retained-rule-authority-registry-v1', 'unsupported-authority-registry');
    for (const entry of array(registry.entries, 'authorities')) originalAuthority(reader, entry);
    const ledger = reader.pinnedJson(sidecar.logical_asset_map.ledger);
    demand([1, 2].includes(ledger.version) && ledger.kind === 'native-additive-repair-ledger-v' + ledger.version, 'unsupported-selected-ledger');
    if (Object.hasOwn(ledger, 'current_rebind')) currentRebind(reader, ledger.current_rebind, parts.map(p => 'data/' + p));
  }
}

export function inspectUnchangedSelectedGeography({repo, baseline, candidate, trusted = baseline, limits = {member: FILE, metadata: METADATA, entries: ENTRIES}}) {
  const report = {version: 1, kind: 'trusted-unchanged-selected-geography-v1', baseline_commit: baseline,
    candidate_commit: candidate, trusted_reader_policy_commit: trusted, candidate_code_executed: false,
    science_reexecuted: false, source_approval: false, published: false};
  try {
    demand(oid(baseline) && oid(candidate) && oid(trusted), 'require-immutable-commits');
    demand(baseline !== candidate, 'baseline-proof-requires-full-check');
    const reader = createReader({repo, baseline, candidate, trusted, limits});
    collect(reader, {baseline, candidate, trusted});
    const result = {...report, status: 'unchanged-selected-inputs', ...reader.summary(),
      limits: ['Exact immutable input/code applicability only; no fresh native, polygon, source-authority, publication or consumer validation.',
        'Unknown reader layouts and changed or absent alternatives retain the original full checker.']};
    demand(Buffer.byteLength(JSON.stringify(result)) <= 2 * 1024 * 1024, 'identity-report-limit');
    return result;
  } catch (error) {
    return {...report, status: 'full-check-required', reason: error instanceof SyntaxError ? 'invalid-routing-metadata' : String(error.message).slice(0, 512)};
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [repo, baseline, candidate, trusted] = process.argv.slice(2);
  process.stdout.write(JSON.stringify(inspectUnchangedSelectedGeography({repo, baseline, candidate, ...(trusted ? {trusted} : {})})) + '\n');
}

// Applicability only. The caller authenticates this module in its trusted checkout.
// These explicit roles mirror the reviewed readers, including detached
// SOURCE/NATIVE readers. No data-vintage module or scientific body is executed.
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {createRoutingMetadataAcquisition} from './geography-routing-metadata.mjs';
import {ACCEPTED_CHECKPOINT_LOCATOR, ACCEPTED_CHECKPOINT_CODE, validateAcceptedCheckpointLocator} from './accepted-selected-checkpoint.mjs';

const PREFIX = 'coordination/engineering/selected-geography-effective-prevention-20261009/';
const POLICY = PREFIX + 'supported-programs.json';
const CHECKPOINTS = 'coordination/engineering/selected-checkpoint-reuse-20261012/accepted-checkpoints.json';
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
const joined = async promises => {
  const rows = await Promise.allSettled(promises), failure = rows.find(row => row.status === 'rejected');
  if (failure) throw failure.reason;
  return rows.map(row => row.value);
};

// The trusted caller authenticates this collector and its readers together from
// one reviewed checkout. Current executable identity is independent of the two
// data vintages: both operands use that same code. Typed routing schemas reject
// unknown consumed input layouts; historical code remains pinned custody data.
// A second manually maintained source-hash whitelist adds no execution authority.
export const EXECUTION_CODE = Object.freeze([
  'scripts/run-geographic-check.py',
  'scripts/check-effective-geographic-regression.mjs', 'scripts/selected-checkpoint-native.mjs', 'src/native-grid.js', 'src/ownership-codec.js',
  'package.json', 'package-lock.json',
  PREFIX + 'selected-neighbor-prevention.mjs',
  PREFIX + 'selected-checkpoint.mjs', PREFIX + 'selected-joint-entry.mjs',
  CHECKPOINTS, ...ACCEPTED_CHECKPOINT_CODE, 'scripts/geographic_checkpoint_products.py',
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

function createReader({repo, baseline, candidate, trusted, limits, acquisition}) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('GIT_')));
  Object.assign(env, {GIT_NO_LAZY_FETCH: '1', GIT_NO_REPLACE_OBJECTS: '1', GIT_CONFIG_NOSYSTEM: '1',
    GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0', GIT_OPTIONAL_LOCKS: '0'});
  const runGit = (args, ignoreShallow = false) => {
    try { return execFileSync('git', ['--no-replace-objects', '-c', 'core.hooksPath=/dev/null', '-c', 'credential.helper=', '-C', repo, ...args],
      {env: ignoreShallow ? {...env, GIT_SHALLOW_FILE: '/dev/null'} : env, maxBuffer: limits.member + 1024, timeout: 30000, stdio: ['ignore', 'pipe', 'pipe']}); }
    catch { throw Error('immutable-object-unavailable:' + args.slice(0, 4).join(':')); }
  };
  const git = (...args) => runGit(args);
  function mergeBase() {
    // A shallow baseline is already a valid common ancestor of a fresh source
    // branch. Do not traverse its intentionally absent parent in that case.
    try { return git('merge-base', baseline, candidate); }
    catch {
      // Divergent historical heads may already supply the hidden parents. This
      // read-only fallback succeeds only with the necessary objects present;
      // no ancestry fetch or shallow-file mutation is authorized here.
      return runGit(['merge-base', baseline, candidate], true);
    }
  }
  const descriptors = new Map(), metadata = new Map(), origins = new Map(), current = new Map();
  let metadataBytes = 0;
  const missingOrigins = new Set();
  function requireOrigin(commit) {
    missingOrigins.add(commit); throw Error('missing-strict-historical-commit:' + commit);
  }
  function descriptor(commit, name, optional = false) {
    demand(oid(commit) && safe(name), 'unsafe-immutable-locator');
    const key = commit + ':' + name;
    if (!descriptors.has(key)) {
      demand(descriptors.size < limits.entries, 'identity-entry-limit');
      let raw;
      try { raw = git('ls-tree', '-z', commit, '--', name).toString(); }
      catch (error) { if (!originExists(commit)) requireOrigin(commit); throw error; }
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
  async function body(pin, expected) {
    const key = pin.commit + ':' + pin.path;
    if (!metadata.has(key)) metadata.set(key, (async () => {
      let size;
      try { size = Number(git('cat-file', '-s', pin.git_blob_oid)); }
      catch {
        await acquisition.acquire(pin, expected);
        size = Number(git('cat-file', '-s', pin.git_blob_oid));
      }
      demand(Number.isSafeInteger(size) && size > 0 && size <= limits.member && metadataBytes + size <= limits.metadata, 'metadata-byte-limit');
      metadataBytes += size;
      const raw = git('cat-file', 'blob', pin.git_blob_oid);
      demand(raw.length === size, 'metadata-length-drift');
      demand(createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex') === pin.git_blob_oid, 'metadata-git-object-identity');
      return raw;
    })());
    const raw = await metadata.get(key);
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
  function pinned(value, {fallback = true, fallbackCommit = baseline, currentAlias = true} = {}) {
    demand(value && oid(value.commit) && safe(value.path) && ['100644', '100755'].includes(value.mode)
      && oid(value.git_blob_oid ?? value.blob) && Number.isSafeInteger(value.bytes) && value.bytes > 0 && value.bytes <= limits.member && hash(value.sha256), 'unsupported-historical-pin');
    // Protect even the currently unused retained alias, including its absence.
    // A later object hydration must not expose a candidate-only alternative.
    if (fallback && currentAlias) equalCurrent(value.path, true);
    const version = originExists(value.commit) ? value.commit : fallback ? fallbackCommit : null;
    if (!version) requireOrigin(value.commit);
    const actual = descriptor(version, value.path);
    demand(actual.mode === value.mode && actual.git_blob_oid === (value.git_blob_oid ?? value.blob), 'historical-pin-identity');
    return actual;
  }
  const jsonAt = async (pin, expected) => JSON.parse(await body(pin, expected));
  const currentJson = (name, expected) => jsonAt(equalCurrent(name), expected);
  const pinnedJson = (value, options) => jsonAt(pinned(value, options), value);
  function currentPin(value) {
    demand(value && safe(value.path) && Number.isSafeInteger(value.bytes) && value.bytes > 0 && value.bytes <= limits.member && hash(value.sha256), 'unsupported-current-pin');
    const p = equalCurrent(value.path);
    demand(value.mode === undefined || value.mode === p.mode, 'current-pin-mode');
    return p;
  }
  return {git, mergeBase, descriptor, equalCurrent, currentJson, currentPin, pinned, pinnedJson, jsonAt, body, originExists,
    missingOrigins,
    resetOrigins() { origins.clear(); missingOrigins.clear(); },
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

async function originalAuthority(reader, entry) {
  keys(entry, 'authority_sha256,policy_id,policy_version,rule_preimage,rule_sha256,source_authority', 'authority-entry');
  reader.pinned(entry.rule_preimage);
  const binding = await reader.pinnedJson(entry.source_authority);
  if (binding.kind === 'source-target-native-custody-v1') {
    // These are the complete file reads in evaluateSourceTargetNativeAuthority.
    // Inspect only its existing routing metadata; the scientific leaves remain
    // opaque and every historical pin retains its present/absent current alias.
    keys(binding, 'kind,native_patch,source_evidence,version', 'source-target-binding');
    demand(binding.version === 1, 'unsupported-source-target-binding');
    reader.pinned(binding.native_patch);
    const evidence = await reader.pinnedJson(binding.source_evidence);
    const dated = evidence.version === 2;
    demand([1, 2].includes(evidence.version) && evidence.kind === 'source-target-native-evidence-v' + evidence.version
      && (dated ? evidence.dated_land_support !== undefined : evidence.dated_land_support === undefined),
      'unsupported-source-target-evidence');
    // These optional roles introduce additional consumed provenance. Until this
    // collector mirrors them completely, retain the cold checker for that layout.
    demand(evidence.territorial_applicability === undefined && evidence.reference_metadata === undefined,
      'unsupported-source-target-consumed-role');
    // Like the bound scientific reader, ignore extra descriptive evidence
    // fields. Only its versioned consumed roles select further file reads.
    for (const role of ['catalogue', 'native_latitudes', 'owner_roster', 'physical_evidence', 'physical_input', 'physical_reproduction']) reader.pinned(evidence[role]);
    for (const family of array(evidence.families, 'source-target-families')) {
      demand(typeof family?.source_id === 'string', 'unsupported-source-target-family');
      for (const pin of array(family.parts, 'source-target-parts')) reader.pinned(pin);
    }
    if (evidence.source_membership !== undefined) {
      const membership = evidence.source_membership;
      keys(membership, 'index,lineage,parts', 'source-target-membership');
      for (const pin of [membership.index, membership.lineage, ...array(membership.parts, 'source-target-membership-parts')]) reader.pinned(pin);
    }
    if (dated) {
      const support = await reader.pinnedJson(evidence.dated_land_support);
      keys(support, 'kind,native_contract_sha256,provenance,records,version', 'dated-land-support');
      demand(support.version === 1 && support.kind === 'adopted-dated-native-centre-land-support-v1', 'unsupported-dated-land-support');
      for (const item of array(support.provenance, 'dated-land-provenance')) {
        demand(['adoption', 'review', 'observation', 'frame'].includes(item.role), 'unsupported-dated-land-role');
        keys(item, item.role === 'frame' ? 'block_pointer,channels,display_base,display_pointer,id,observation,pin,role' : 'id,pin,role', 'dated-land-provenance');
        reader.pinned(item.pin);
      }
    }
    return;
  }
  keys(binding, 'kind,native_proof,original_pins,version' + (Object.hasOwn(binding, 'source_output_aliases') ? ',source_output_aliases' : ''), 'authority-binding');
  demand(binding.version === 1 && binding.kind === 'original-issued-rule-source-custody-v1', 'unsupported-authority-binding');
  keys(binding.original_pins, 'ledger,native_facts,native_manifest,native_request,source_facts,source_request', 'original-custody');
  for (const p of Object.values(binding.original_pins)) reader.pinned(p);
  const [request, source] = await joined([reader.pinnedJson(binding.original_pins.native_request), reader.pinnedJson(binding.original_pins.source_request)]);
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
    const selector = await reader.pinnedJson(selectorPin, {fallback: false});
    demand(selector.selected_geography?.kind === 'complete-world-index-with-exact-encoded-overrides' && safe(selector.selected_geography.path), 'unsupported-original-source-map');
    reader.descriptor(selectorPin.commit, selector.selected_geography.path);
  }
}

async function currentRebind(reader, pin, sourcePaths) {
  const certificate = await reader.pinnedJson(pin, {fallback: false});
  keys(certificate, 'authority_registry_sha256,base_selection,execution_commit,facts,kind,operating,publication,request,result,version', 'current-rebind');
  demand(certificate.version === 1 && certificate.kind === 'qualified-native-additive-current-bank-rebind-v1' && oid(certificate.execution_commit), 'unsupported-current-rebind');
  for (const role of ['request', 'facts', 'publication', 'operating', 'result']) reader.pinned(certificate[role], {fallback: false});
  // The rebind consumed historical executable bytes as custody. Both operands
  // use the same current checker, independently of their data-vintage copies.
  const [request, operating] = await joined([reader.pinnedJson(certificate.request, {fallback: false}), reader.pinnedJson(certificate.operating, {fallback: false})]);
  // Scientific readers are materialized for actual geography, not for sparse
  // queue preparation, which only imports the exported path inventories.
  const {currentRebindCodePaths} = await import('../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs');
  for (const name of currentRebindCodePaths(request.executed_code)) reader.descriptor(certificate.execution_commit, name);
  keys(operating.execution_custody, 'code_source,terminal,stderr,stdout,issued_plan', 'external-custody');
  for (const p of Object.values(operating.execution_custody)) reader.pinned(p, {fallback: false});
  const plan = await reader.pinnedJson(operating.execution_custody.issued_plan, {fallback: false});
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

// The checkpoint reader adds retained complete-output roots and a finite route
// census beyond the selected source/native bank. A same-selector source change
// must not alter one of those aliases while the old collector silently skips it.
async function checkpointRoutes(reader, selection, trusted) {
  const catalogue = await reader.trustedJson(CHECKPOINTS);
  keys(catalogue, 'version,kind,checkpoints', 'checkpoint-catalogue');
  demand(catalogue.version === 1 && catalogue.kind === 'accepted-selected-checkpoints-v1', 'unsupported-checkpoint-catalogue');
  const roots = array(catalogue.checkpoints, 'checkpoint-roots', 0);
  demand(new Set(roots.map(p => p.id)).size === roots.length, 'duplicate-checkpoint-identity');
  const selectedHash = sha(Buffer.from(JSON.stringify(canonical(selection)) + '\n'));
  const matches = roots.filter(p => p.selection_sha256 === selectedHash);
  demand(matches.length <= 1, 'ambiguous-checkpoint-selection');
  // No registration means the genuine joint entry takes its existing cold path,
  // whose complete inputs are collected below. Do not invent checkpoint trust.
  if (!matches.length) return;
  const root = matches[0];
  const derived = root.kind === 'accepted-derived-selected-checkpoint-v1';
  const common = 'id,accepted_head,selected_commit,selection_sha256,execution_commit,execution_code_sha256,runtime_sha256,facts,certificate,publication,routes';
  keys(root, common + (derived ? ',kind,continuous_facts,operands,continuous_publication,joint_result,operating,executing_policy' : ',custody'), 'checkpoint-root');
  demand(typeof root.id === 'string' && root.id && [root.accepted_head, root.selected_commit, root.execution_commit].every(oid)
    && [root.selection_sha256, root.execution_code_sha256, root.runtime_sha256].every(hash), 'unsupported-checkpoint-root');
  const roles = ['facts', 'certificate', 'publication', 'routes', ...(derived
    ? ['continuous_facts', 'operands', 'continuous_publication', 'joint_result', 'operating', 'executing_policy'] : ['custody'])];
  for (const role of roles) reader.pinned(root[role], {fallbackCommit: trusted});
  // Scientific certificate/operand bodies stay opaque. Their original whole
  // pins bind all nested contents; this authenticated routing metadata covers
  // the module's complete present/absent inventory and source/native alternatives.
  // The qualifier also reads the archived execution's programme policy. Its
  // current alias belongs only to the trusted checkout, never the candidate.
  let policyPin;
  if (derived) policyPin = root.executing_policy;
  else {
    const custody = await reader.pinnedJson(root.custody, {fallbackCommit: trusted});
    const retained = array(custody.complete_cold_custody, 'checkpoint-custody').filter(p => p.facts?.selected_commit === root.selected_commit);
    demand(retained.length === 1, 'ambiguous-checkpoint-policy-custody');
    const policyPins = array(retained[0].inventory, 'checkpoint-inventory').filter(p => p.path === POLICY);
    demand(policyPins.length === 1, 'incomplete-checkpoint-policy-custody');
    policyPin = policyPins[0];
  }
  const priorPolicy = await reader.pinnedJson(policyPin, {fallbackCommit: trusted, currentAlias:false});
  const currentPolicy = await reader.trustedJson(POLICY);
  for (const policy of [priorPolicy, currentPolicy]) {
    keys(policy, 'version,kind,programs,current_rebind_migrations', 'checkpoint-programme-policy');
    demand(policy.version === 1 && policy.kind === 'trusted-source-native-programmes-v1', 'unsupported-checkpoint-programme-policy');
  }
  for (const role of ['programs', 'current_rebind_migrations']) {
    const current = new Set(array(currentPolicy[role], 'checkpoint-policy-records', 0).map(p => JSON.stringify(canonical(p))));
    demand(array(priorPolicy[role], 'checkpoint-policy-records', 0).every(p => current.has(JSON.stringify(canonical(p)))),
      'checkpoint-policy-eligibility-removed');
  }
  const census = await reader.pinnedJson(root.routes, {fallbackCommit: trusted});
  if (derived) {
    keys(census, 'version,kind,candidate_commit,candidate_selection,predecessor_paths,routes', 'derived-checkpoint-census');
    demand(census.version === 1 && census.kind === 'selected-checkpoint-scientific-routes-v1'
      && census.candidate_commit === root.selected_commit && same(census.candidate_selection, selection), 'unsupported-derived-checkpoint-census');
  }
  const routes = derived ? census.routes : census;
  demand(Array.isArray(routes) && routes.length > 0 && routes.length <= ENTRIES, 'unsupported-checkpoint-routes');
  let previous = '';
  for (const route of routes) {
    keys(route, 'path,tree', 'checkpoint-route');
    demand(safe(route.path) && route.path > previous && typeof route.tree === 'string', 'unsupported-checkpoint-route-order');
    previous = route.path;
    // Its original census row is preserved; current policy is independently
    // bound by trustedJson(POLICY), not selected-vintage scientific equality.
    if (route.path === POLICY || route.path === ACCEPTED_CHECKPOINT_LOCATOR) continue;
    if (EXECUTION_CODE.includes(route.path) || REBIND_CODE.includes(route.path)) reader.descriptor(trusted, route.path, true);
    else reader.equalCurrent(route.path, true);
    // A census describes its historical selected tree, including executable
    // copies. Preserve that custody identity without comparing old generation
    // code to the one current checker used by BOTH data operands.
    const archived = reader.descriptor(root.selected_commit, route.path, true);
    const tree = archived ? `${archived.mode} blob ${archived.git_blob_oid}\t${archived.path}\0` : '';
    demand(route.tree === tree, 'checkpoint-route-identity:' + route.path);
  }
}

async function collect(reader, {baseline, candidate, trusted, metadataPaths}) {
  // This is an eligibility bound, not input equivalence. Compare the authored
  // diff from its real merge base; all consumed identities below still compare
  // the exact supplied baseline and candidate, including baseline-only changes.
  // Prefer Git's real shallow boundary; consult already-present hidden ancestry
  // only if the normal query fails. Missing required history still declines.
  const mergeBase = reader.mergeBase().toString().trim();
  demand(oid(mergeBase), 'source-scope-merge-base-unavailable');
  const changed = reader.git('diff-tree', '--no-commit-id', '--name-only', '-r', '-z', '--no-renames', mergeBase, candidate).toString().split('\0').filter(Boolean);
  if (metadataPaths !== undefined) {
    // The trusted PR caller separately binds the issue-owned receiving packet,
    // complete tree delta and original successful report. This option only
    // widens scope admission: EVERY audited consumed route below still must
    // have identical ordinary immutable bytes, including fallback absences.
    demand(Array.isArray(metadataPaths) && metadataPaths.length > 0 && metadataPaths.length <= 2 &&
      new Set(metadataPaths).size === metadataPaths.length && metadataPaths.every(name =>
        /^coordination\/engineering\/[A-Za-z0-9_-]+\/(?:README\.md|evidence-quality\.json)$/.test(name)) &&
      new Set(metadataPaths.map(name => name.slice(0, name.lastIndexOf('/')))).size === 1 &&
      mergeBase === baseline && same([...changed].sort(), [...metadataPaths].sort()), 'outside-receiving-metadata-scope');
    for (const name of changed) {
      const before = reader.descriptor(baseline, name), after = reader.descriptor(candidate, name);
      demand(before.mode === '100644' && after.mode === '100644', 'nonordinary-receiving-metadata');
    }
  } else {
    demand(changed.length > 0 && changed.length <= 512 && changed.every(safe), 'invalid-changed-path-inventory');
    for (const name of changed) {
      // Unrelated ordinary changes do not alter the consumed scientific roles.
      reader.descriptor(mergeBase, name, true);
      reader.descriptor(candidate, name, true);
    }
  }
  for (const name of EXECUTION_CODE) reader.descriptor(trusted, name);
  // The accepted catalogue is authority data, separate from executing software.
  reader.equalCurrent(CHECKPOINTS);
  // Routing hints never authorize science, but any changed locator or retained
  // archive must reenter authenticated acquisition instead of inheriting a skip.
  const checkpointLocator = reader.equalCurrent(ACCEPTED_CHECKPOINT_LOCATOR, true);
  if (checkpointLocator) {
    const locator = validateAcceptedCheckpointLocator(await reader.jsonAt(checkpointLocator));
    if (locator.retained_artifact) reader.equalCurrent(locator.retained_artifact.path, true);
  }
  for (const name of ['scripts/check-unchanged-selected-geography.mjs', 'scripts/geography-routing-metadata.mjs']) reader.descriptor(trusted, name, true);
  reader.descriptor(trusted, 'scripts/geography-prefetch.mjs');
  await joined([reader.trustedJson(POLICY), reader.trustedJson(CHECKPOINTS), ...[HANDOFFS, 'data/world-index.json', 'data/geographic-releases/current-manifest.json',
      'data/ownership-selection.json', 'scripts/native-ownership/verified-candidates.json'].map(name => reader.currentJson(name))]);
  // The original reader uses executing-checkout policy for BOTH selections.
  const programme = await reader.trustedJson(POLICY);
  demand(programme.version === 1 && programme.kind === 'trusted-source-native-programmes-v1', 'unsupported-programme-catalogue');
  const handoffs = await reader.currentJson(HANDOFFS);
  demand(handoffs.version === 1 && handoffs.kind === 'accepted-administrative-handoffs-v1', 'unsupported-handoff-registry');
  for (const row of array(handoffs.entries, 'administrative-handoffs')) {
    reader.pinned({...row.source, commit: row.accepted_source_commit});
  }
  const world = await reader.currentJson('data/world-index.json');
  const parts = array(world.parts, 'world-parts');
  demand(new Set(parts).size === parts.length && parts.every(safe), 'unsupported-world-parts');
  for (const name of parts) reader.equalCurrent('data/' + name);
  for (const name of ['data/hierarchy.json', 'data/canonical-grid/manifest.json', 'data/geographic-releases/index.json']) reader.equalCurrent(name);
  const pointer = await reader.currentJson('data/geographic-releases/current-manifest.json');
  demand(safe(pointer.path) && hash(pointer.sha256) && !pointer.path.startsWith('data/'), 'unsupported-release-pointer');
  reader.equalCurrent('data/geographic-releases/' + pointer.path);
  const selection = await reader.currentJson('data/ownership-selection.json');
  keys(selection, 'manifest_path,method,release_id,sha256,version' + ['selected_geography', 'additive_release', 'artifact_consumption'].filter(k => Object.hasOwn(selection, k)).map(k => ',' + k).join(''), 'selection');
  demand(selection.version === 1 && selection.method === 'native-linear-evenodd-first-owner-v1' && safe(selection.manifest_path), 'unsupported-selection');
  await checkpointRoutes(reader, selection, trusted);
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
  reader.descriptor(bounds.commit, bounds.path);
  const verified = await reader.currentJson('scripts/native-ownership/verified-candidates.json');
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
  for (const p of [bank.world_index, ...array(bank.unchanged_files, 'unchanged-sources', 0), ...array(bank.overrides, 'source-overrides', 0)]) reader.pinned(p);
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
    for (const p of [sidecar.runtime_envelope, ...Object.values(sidecar.logical_asset_map)]) reader.pinned(p);
    const [registry, ledger] = await joined([reader.pinnedJson(sidecar.authority_registry), reader.pinnedJson(sidecar.logical_asset_map.ledger)]);
    demand(registry.version === 1 && registry.kind === 'retained-rule-authority-registry-v1', 'unsupported-authority-registry');
    await joined(array(registry.entries, 'authorities').map(entry => originalAuthority(reader, entry)));
    demand([1, 2].includes(ledger.version) && ledger.kind === 'native-additive-repair-ledger-v' + ledger.version, 'unsupported-selected-ledger');
    if (Object.hasOwn(ledger, 'current_rebind')) await currentRebind(reader, ledger.current_rebind, parts.map(p => 'data/' + p));
  }
}

export async function inspectUnchangedSelectedGeography({repo, baseline, candidate, trusted = baseline, acquisition, metadataPaths, verifyExecutingCheckout = false, limits = {member: FILE, metadata: METADATA, entries: ENTRIES}}) {
  const report = {version: 1, kind: 'trusted-unchanged-selected-geography-v1', baseline_commit: baseline,
    candidate_commit: candidate, trusted_reader_policy_commit: trusted, candidate_code_executed: false,
    science_reexecuted: false, source_approval: false, published: false};
  try {
    demand(oid(baseline) && oid(candidate) && oid(trusted), 'require-immutable-commits');
    demand(baseline !== candidate, 'baseline-proof-requires-full-check');
    acquisition ??= createRoutingMetadataAcquisition({repo, baseline, limits});
    const reader = createReader({repo, baseline, candidate, trusted, limits, acquisition});
    if (verifyExecutingCheckout) demand(reader.git('rev-parse', 'HEAD').toString().trim() === trusted, 'executing-checkout-mismatch');
    for (let round = 0; ; round++) {
      try { await collect(reader, {baseline, candidate, trusted, metadataPaths}); break; }
      catch (error) {
        if (!String(error.message).startsWith('missing-strict-historical-commit:') || round >= 8) throw error;
        acquisition.acquireOrigins([...reader.missingOrigins].sort());
        // New strict graphs may also contain fallback-eligible origins. Recheck
        // every route from its typed root rather than keeping stale absence.
        reader.resetOrigins();
      }
    }
    const result = {...report, status: 'unchanged-selected-inputs', ...reader.summary(), metadata_acquisition: acquisition.summary(),
      limits: ['Exact immutable consumed-data applicability under one executing checkout only; no fresh native, polygon, source-authority, publication or consumer validation.',
        'Unknown reader layouts and changed or absent alternatives retain the original full checker.']};
    demand(Buffer.byteLength(JSON.stringify(result)) <= 2 * 1024 * 1024, 'identity-report-limit');
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

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {inspectUnchangedSelectedGeography, EXECUTION_CODE, REBIND_CODE, AUDITED_READERS} from '../scripts/check-unchanged-selected-geography.mjs';

const ROOT = fileURLToPath(new URL('../', import.meta.url));
const P = 'research/geography/selected-fixture/';
const POLICY = 'coordination/engineering/selected-geography-effective-prevention-20261009/supported-programs.json';
const HANDOFFS = 'coordination/engineering/melanesia363-additive-delivery-20261010/accepted-administrative-handoffs.json';
const body = value => Buffer.isBuffer(value) ? value : Buffer.from(typeof value === 'string' ? value : JSON.stringify(value));
const sha = value => createHash('sha256').update(body(value)).digest('hex');

// These intentionally tiny opaque leaf bodies test immutable routing/equality,
// not scientific validity. Historical collector replay is compared separately
// with retained original full-reader logs; these leaf sentinels are not decoded.
function fixture({missingOrigin = false, splitBaseline = false, rebind = true} = {}) {
  const cache = path.join(ROOT, '.cache/unchanged-selected-fixtures');
  fs.mkdirSync(cache, {recursive: true});
  const directory = fs.mkdtempSync(path.join(cache, 'case-'));
  const env = {...Object.fromEntries(Object.entries(process.env).filter(([k]) => !k.startsWith('GIT_'))),
    GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_NO_LAZY_FETCH: '1',
    GIT_AUTHOR_NAME: 'fixture', GIT_AUTHOR_EMAIL: 'fixture@example.invalid',
    GIT_COMMITTER_NAME: 'fixture', GIT_COMMITTER_EMAIL: 'fixture@example.invalid'};
  const git = (args, input) => execFileSync('git', ['-C', directory, ...args], {env, input, maxBuffer: 4 * 1024 * 1024, stdio: ['pipe', 'pipe', 'pipe']}).toString().trim();
  git(['init', '--bare']);
  const files = {}, commits = new Map();
  const put = (name, value) => { files[name] = body(value); return name; };
  function commit(values = files, parent, modes = {}) {
    const entries = Object.entries(values).map(([name, raw]) => [name, modes[name] ?? '100644', git(['hash-object', '-w', '--stdin'], body(raw))]);
    function tree(prefix) {
      const rows = [], children = new Set();
      for (const [name, mode, oid] of entries.filter(([name]) => name.startsWith(prefix))) {
        const rest = name.slice(prefix.length), slash = rest.indexOf('/');
        if (slash < 0) rows.push(`${mode} blob ${oid}\t${rest}`);
        else children.add(rest.slice(0, slash));
      }
      for (const child of children) rows.push(`040000 tree ${tree(prefix + child + '/')}\t${child}`);
      return git(['mktree'], rows.sort().join('\n') + '\n');
    }
    const id = git(['commit-tree', tree(''), ...(parent ? ['-p', parent] : [])], 'fixture\n');
    commits.set(id, {...values}); return id;
  }
  const pin = (name, at, extra = {}) => {
    const raw = commits.get(at)[name];
    return {commit: at, path: name, mode: '100644', git_blob_oid: git(['hash-object', '--stdin'], raw), bytes: raw.length, sha256: sha(raw), ...extra};
  };
  for (const name of new Set([...EXECUTION_CODE, ...REBIND_CODE])) put(name, Object.hasOwn(AUDITED_READERS, name) ? fs.readFileSync(path.join(ROOT, name)) : 'trusted code leaf');
  put(POLICY, {version: 1, kind: 'trusted-source-native-programmes-v1'});
  const world = {parts: ['geography/source.json']};
  put('data/world-index.json', world);
  for (const name of ['data/geography/source.json', 'data/canonical-grid/bounds.json.gz', 'data/hierarchy.json', 'data/canonical-grid/manifest.json', 'data/geographic-releases/index.json', 'data/geographic-releases/current.json.gz']) put(name, 'opaque complete scientific leaf');
  for (const name of ['handoff', 'receipt', 'source-publication', 'source-inventory', 'source-operating', 'native-publication', 'native-inventory', 'native-operating', 'native-asset', 'source-facts', 'native-facts', 'original-ledger', 'original-manifest', 'rule', 'predecessor', 'code-source', 'terminal', 'stderr', 'stdout']) put(P + name + '.json', {leaf: name});
  put(P + 'original-source-map.json', {kind: 'complete-world-index-with-exact-encoded-overrides'});
  put('data/ownership-selection.json', {selected_geography: {kind: 'complete-world-index-with-exact-encoded-overrides', path: P + 'original-source-map.json'}});
  const original = commit();
  const origin = missingOrigin ? 'f'.repeat(40) : original;
  const historical = name => pin(name, original, {commit: origin});
  const ordinaryBaseline = {version: 1, pins: []};
  const oldBaseline = splitBaseline ? {version: 2, kind: 'current-selected-native-baseline-v1', pins: [pin('data/ownership-selection.json', original)]} : ordinaryBaseline;
  const newBaseline = splitBaseline ? {...oldBaseline, pins: [{...oldBaseline.pins[0], kind: 'not-consumed-shape-control'}]} : ordinaryBaseline;
  // Distinct but valid historical selector baselines exercise the strict route.
  let selectedOriginal = original;
  if (splitBaseline) {
    put(P + 'marker.json', 'second original selector commit'); selectedOriginal = commit(files, original);
    newBaseline.pins = [pin('data/ownership-selection.json', selectedOriginal)];
  }
  const aliasOriginal = {...historical(P + 'source-publication.json'), path: '.cache/native-grid-candidates/example/publication.json', kind: 'completed-inventory-body'};
  const source = {operation: 'retained-land-source-premises-v1', baseline: oldBaseline, source_rule: {profile: 'retained-consumed-administrative-source'}};
  const request = {operation: 'unactivated-additive-native-batch-v1', baseline: newBaseline,
    additive: {source_profile: 'retained-consumed-administrative-source', publication_path: aliasOriginal.path,
      inventory_path: P + 'source-inventory.json', operating_path: P + 'source-operating.json',
      inputs: [aliasOriginal, historical(P + 'source-inventory.json'), historical(P + 'source-operating.json')]}};
  put(P + 'source-request.json', source); put(P + 'native-request.json', request);
  const requests = commit(files, original);
  const originalPins = Object.fromEntries(['ledger', 'native_facts', 'native_manifest', 'source_facts'].map(role => [role, historical(P + ({ledger: 'original-ledger', native_facts: 'native-facts', native_manifest: 'original-manifest', source_facts: 'source-facts'}[role]) + '.json')]));
  originalPins.source_request = pin(P + 'source-request.json', requests);
  originalPins.native_request = pin(P + 'native-request.json', requests);
  const binding = {version: 1, kind: 'original-issued-rule-source-custody-v1', original_pins: originalPins,
    source_output_aliases: [{original: aliasOriginal, published: pin(P + 'source-publication.json', original)}],
    native_proof: {publication: historical(P + 'native-publication.json'), inventory: historical(P + 'native-inventory.json'), operating: historical(P + 'native-operating.json'), assets: [historical(P + 'native-asset.json')]}};
  put(P + 'binding.json', binding);
  const bindings = commit(files, requests);
  const entry = {authority_sha256: 'a'.repeat(64), rule_sha256: sha(files[P + 'rule.json']), policy_id: 'retained-source-literal-additions', policy_version: 1,
    rule_preimage: historical(P + 'rule.json'), source_authority: pin(P + 'binding.json', bindings)};
  put(P + 'registry.json', {version: 1, kind: 'retained-rule-authority-registry-v1', entries: [entry]});
  const ledger = {version: 2, kind: 'native-additive-repair-ledger-v2'};
  if (rebind) {
    put(P + 'rebind-request.json', {acquisition: {target_sources: [{target_id: 'one', path: 'data/geography/source.json'}], predecessor_proof: historical(P + 'predecessor.json')}});
    put(P + 'issued-plan.json', {original_inputs: [pin(P + 'native-asset.json', original)]});
    const inputs = commit(files, bindings);
    const custody = Object.fromEntries(['code_source', 'terminal', 'stderr', 'stdout'].map(role => [role, pin(P + role.replace('_', '-') + '.json', original)]));
    custody.issued_plan = pin(P + 'issued-plan.json', inputs);
    put(P + 'rebind-operating.json', {execution_custody: custody});
    const operating = commit(files, inputs);
    const certificate = {version: 1, kind: 'qualified-native-additive-current-bank-rebind-v1', authority_registry_sha256: 'a'.repeat(64), base_selection: {}, execution_commit: original,
      request: pin(P + 'rebind-request.json', inputs), operating: pin(P + 'rebind-operating.json', operating),
      facts: pin(P + 'native-facts.json', original), publication: pin(P + 'native-publication.json', original), result: pin(P + 'native-asset.json', original)};
    put(P + 'rebind-certificate.json', certificate);
    const certificates = commit(files, operating);
    ledger.current_rebind = pin(P + 'rebind-certificate.json', certificates);
  }
  put(P + 'ledger.json', ledger); put(P + 'envelope.json', {version: 2}); put(P + 'patch.json', {rows: []});
  const assets = commit(files, bindings);
  const index = {version: 1, kind: 'ordered-exact-original-byte-fragments', parts: [{path: 'fragment.gz'}]};
  put(P + 'native-bank/index.json', index); put(P + 'native-bank/fragment.gz', 'opaque native fragment');
  const manifest = {version: 2, method: 'native-linear-evenodd-first-owner-v1', parts: [{kind: 'runs', path: 'absent.bin.gz'}],
    original_assets: {bounds: {commit: original, path: 'data/canonical-grid/bounds.json.gz'}},
    native_asset_transport: {version: 1, kind: index.kind, logical_assets: 1, original_compressed_bytes: 1, index: {path: P + 'native-bank/index.json', bytes: files[P + 'native-bank/index.json'].length, sha256: sha(index)}}};
  put(P + 'native/manifest.json', manifest);
  const bank = {version: 1, kind: 'complete-world-index-with-exact-encoded-overrides', world_index: historical('data/world-index.json'), unchanged_files: [historical('data/geography/source.json')], overrides: []};
  put(P + 'source-bank.json', bank);
  const sidecar = {version: 2, kind: 'retained-native-additive-selection-v2', base_selection: {}, runtime_envelope: pin(P + 'envelope.json', assets), authority_registry: pin(P + 'registry.json', assets),
    logical_asset_map: {base_manifest: historical(P + 'original-manifest.json'), owner_roster: historical('data/canonical-grid/bounds.json.gz'), patch: pin(P + 'patch.json', assets), ledger: pin(P + 'ledger.json', assets)}};
  put(P + 'sidecar.json', sidecar);
  const currentPin = name => ({path: name, bytes: files[name].length, sha256: sha(files[name])});
  const selection = {version: 1, method: manifest.method, release_id: 'fixture', manifest_path: P + 'native/manifest.json', sha256: sha(manifest),
    selected_geography: {version: 1, kind: bank.kind, ...currentPin(P + 'source-bank.json')}, additive_release: currentPin(P + 'sidecar.json')};
  put('data/ownership-selection.json', selection);
  put('scripts/native-ownership/verified-candidates.json', {version: 1, candidates: {[selection.sha256]: {role: 'reviewed-exhaustive-native-rule-comparison', commit: original, path: P + 'receipt.json'}}});
  put(HANDOFFS, {version: 1, kind: 'accepted-administrative-handoffs-v1', entries: [{accepted_source_commit: original, source: pin(P + 'handoff.json', original)}]});
  put('data/geographic-releases/current-manifest.json', {path: 'current.json.gz', sha256: sha(files['data/geographic-releases/current.json.gz'])});
  const baseline = commit(files, assets), candidateFiles = {...files, 'research/geography/new-packet/source.json': body('unactivated source publication')};
  const candidate = commit(candidateFiles, baseline);
  const inspect = (head = candidate, base = baseline, options = {}) => inspectUnchangedSelectedGeography({repo: directory, baseline: base, candidate: head, ...options});
  return {directory, git, files, baseline, candidate, candidateFiles, inspect, commit, original,
    close() { fs.rmSync(directory, {recursive: true, force: true}); }};
}

test('complete typed closure accepts a source-only addition without scientific leaf reads', () => {
  const f = fixture(); try {
    const result = f.inspect(); assert.equal(result.status, 'unchanged-selected-inputs', result.reason);
    assert.equal(result.candidate_code_executed, false); assert.equal(result.science_reexecuted, false);
    assert.equal(result.trusted_reader_policy_commit, f.baseline);
    assert(result.current_and_absent_alternatives.some(p => p.path === P + 'native/absent.bin.gz' && p.absent));
    assert(result.immutable_descriptors.some(p => p.path === P + 'issued-plan.json'));
    assert(result.metadata_bytes_read < 1024 * 1024);
  } finally { f.close(); }
});

test('unchanged same-path fallbacks and strict administrative selector splits are covered', () => {
  for (const options of [{missingOrigin: true}, {splitBaseline: true}]) {
    const f = fixture(options); try { const result = f.inspect(); assert.equal(result.status, 'unchanged-selected-inputs', result.reason); }
    finally { f.close(); }
  }
});

test('every nested current/fallback custody family rejects changed retained aliases', () => {
  const f = fixture(); try {
    for (const name of ['binding', 'native-request', 'source-request', 'source-facts', 'native-facts', 'original-manifest', 'original-ledger',
      'source-publication', 'source-inventory', 'source-operating', 'native-publication', 'native-inventory', 'native-operating', 'native-asset', 'predecessor', 'handoff', 'rule']) {
      const target = P + name + '.json';
      const candidate = f.commit({...f.candidateFiles, [target]: body('changed retained body')}, f.baseline);
      const result = f.inspect(candidate);
      assert.equal(result.status, 'full-check-required', target);
      assert.match(result.reason, /changed-current-input|historical-pin/);
    }
  } finally { f.close(); }
});

test('native materialization absence, source map, transport and selected registry changes reject', () => {
  const f = fixture(); try {
    for (const target of ['native/absent.bin.gz', 'native-bank/fragment.gz', 'source-bank.json', 'registry.json', 'sidecar.json', 'ledger.json']) {
      const candidate = f.commit({...f.candidateFiles, [P + target]: body('changed selected input')}, f.baseline);
      assert.equal(f.inspect(candidate).status, 'full-check-required', target);
    }
  } finally { f.close(); }
});

test('baseline-only relevant code differs even when candidate authored scope is only source', () => {
  const f = fixture(); try {
    const baseline = f.commit({...f.files, 'src/effective-footprint.js': body('changed current custody code')}, f.baseline);
    const result = f.inspect(f.candidate, baseline);
    assert.equal(result.status, 'full-check-required'); assert.match(result.reason, /changed-current-input:src\/effective-footprint/);
  } finally { f.close(); }
});

test('baseline-only unused programme-copy and source support changes do not alter actual consumed code', () => {
  const f = fixture(); try {
    const baseline = f.commit({...f.files, [POLICY]: body({version: 1, kind: 'trusted-source-native-programmes-v1', changed: 'trusted-only'}),
      'scripts/additive-gap-repair.mjs': body('not executed by this reader'), 'coordination/engineering/unrelated-source-support/README.md': body('unrelated')}, f.baseline);
    const result = f.inspect(f.candidate, baseline);
    assert.equal(result.status, 'unchanged-selected-inputs', result.reason);
    assert(result.immutable_descriptors.some(p => p.path === POLICY && p.commit === baseline));
    assert(!result.immutable_descriptors.some(p => p.path === POLICY && p.commit === f.candidate));
  } finally { f.close(); }
});

test('unknown trusted reader profile, unsafe modes, limits and identical commits decline', () => {
  const f = fixture(); try {
    assert.match(f.inspect(f.baseline).reason, /baseline-proof/);
    assert.match(f.inspect(f.candidate, f.baseline, {limits: {member: 32 * 1024 * 1024, metadata: 1, entries: 4096}}).reason, /metadata-byte-limit/);
    assert.match(f.inspect(f.candidate, f.baseline, {limits: {member: 32 * 1024 * 1024, metadata: 64 * 1024 * 1024, entries: 1}}).reason, /identity-entry-limit/);
    const code = 'scripts/check-effective-geographic-regression.mjs';
    const baseline = f.commit({...f.files, [code]: body('unknown new routing reader')}, f.baseline);
    const candidate = f.commit({...f.candidateFiles, [code]: body('unknown new routing reader')}, baseline);
    assert.match(f.inspect(candidate, baseline).reason, /unsupported-reader-profile/);
    const symlink = f.commit(f.candidateFiles, f.baseline, {'research/geography/new-packet/source.json': '120000'});
    assert.match(f.inspect(symlink).reason, /nonordinary/);
  } finally { f.close(); }
});

test('CLI emits bounded explicit full fallback for invalid or engineering inputs', () => {
  const f = fixture(); try {
    const output = execFileSync(process.execPath, [path.join(ROOT, 'scripts/check-unchanged-selected-geography.mjs'), f.directory, f.baseline, f.baseline]);
    assert.equal(JSON.parse(output).status, 'full-check-required');
    const candidate = f.commit({...f.candidateFiles, 'scripts/other.mjs': body('engineering')}, f.baseline);
    assert.match(f.inspect(candidate).reason, /outside-source-publication-scope/);
  } finally { f.close(); }
});

test('receipt fallback requires an absent commit, not a missing path in an existing commit', () => {
  const f = fixture(); try {
    const registryPath = 'scripts/native-ownership/verified-candidates.json';
    const registry = JSON.parse(f.files[registryPath]);
    const receipt = Object.values(registry.candidates)[0];
    const emptyTree = f.git(['mktree'], '');
    const emptyCommit = f.git(['commit-tree', emptyTree], 'empty historical commit\n');
    for (const [commit, expected] of [[emptyCommit, 'full-check-required'], ['e'.repeat(40), 'unchanged-selected-inputs']]) {
      receipt.commit = commit;
      const files = {...f.files, [registryPath]: body(registry)};
      const baseline = f.commit(files, f.baseline);
      const candidate = f.commit({...files, 'research/geography/new-packet/source.json': body('source only')}, baseline);
      const result = f.inspect(candidate, baseline);
      assert.equal(result.status, expected, result.reason);
      if (expected === 'full-check-required') assert.match(result.reason, /missing-required-input/);
    }
  } finally { f.close(); }
});

test('unknown routing layouts decline even when their before/after blobs are equal', () => {
  const f = fixture(); try {
    const selector = JSON.parse(f.files['data/ownership-selection.json']);
    selector.new_routing_hook = {path: 'outside.json'};
    const files = {...f.files, 'data/ownership-selection.json': body(selector)};
    const baseline = f.commit(files, f.baseline);
    const candidate = f.commit({...files, 'research/geography/new-packet/source.json': body('source only')}, baseline);
    const result = f.inspect(candidate, baseline);
    assert.equal(result.status, 'full-check-required'); assert.match(result.reason, /unsupported-selection/);
  } finally { f.close(); }
});

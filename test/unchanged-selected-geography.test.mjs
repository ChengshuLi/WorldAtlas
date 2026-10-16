import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {inspectUnchangedSelectedGeography, inspectExecutingSelectedGeography} from '../scripts/check-unchanged-selected-geography.mjs';

const ROOT = fileURLToPath(new URL('../', import.meta.url));
const P = 'coordination/engineering/selected-data-fixture/';
const CHECKPOINTS = 'coordination/engineering/selected-checkpoint-reuse-20261012/accepted-checkpoints.json';
const RECEIVING = P + 'README.md';
const body = value => Buffer.isBuffer(value) ? value : Buffer.from(typeof value === 'string' ? value : JSON.stringify(value));
const sha = value => createHash('sha256').update(body(value)).digest('hex');

// Opaque scientific outputs deliberately have no historical producer schema.
// This fixture proves immutable data applicability, never scientific legality.
function fixture() {
  const cache = path.join(ROOT, '.cache/unchanged-selected-fixtures');
  fs.mkdirSync(cache, {recursive: true});
  const directory = fs.mkdtempSync(path.join(cache, 'case-'));
  const env = {...Object.fromEntries(Object.entries(process.env).filter(([k]) => !k.startsWith('GIT_'))),
    GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_NO_LAZY_FETCH: '1'};
  const git = (args, input) => execFileSync('git', ['-C', directory, ...args],
    {env, input, maxBuffer: 4 * 1024 * 1024, stdio: ['pipe', 'pipe', 'pipe']}).toString().trim();
  git(['init', '--bare']);
  const files = {}, commits = new Map();
  const put = (name, value) => { files[name] = body(value); return name; };
  function commit(values = files, parent, modes = {}) {
    const ref = 'refs/test-fixture-import';
    const stream = [Buffer.from(`commit ${ref}\nmark :1\ncommitter fixture <fixture@example.invalid> 0 +0000\ndata 8\nfixture\n`
      + (parent ? `from ${parent}\n` : '') + 'deleteall\n')];
    for (const [name, value] of Object.entries(values)) {
      const raw = body(value);
      stream.push(Buffer.from(`M ${modes[name] ?? '100644'} inline ${JSON.stringify(name)}\ndata ${raw.length}\n`), raw, Buffer.from('\n'));
    }
    stream.push(Buffer.from(`\nget-mark :1\nreset ${ref}\n\ndone\n`));
    const id = git(['fast-import', '--quiet', '--force'], Buffer.concat(stream));
    commits.set(id, {...values}); return id;
  }
  const pin = (name, at) => {
    const raw = commits.get(at)[name];
    return {commit: at, path: name, mode: '100644', git_blob_oid: git(['hash-object', '--stdin'], raw), bytes: raw.length, sha256: sha(raw)};
  };
  const currentPin = name => ({path: name, bytes: files[name].length, sha256: sha(files[name])});
  put(CHECKPOINTS, {version: 1, kind: 'accepted-selected-checkpoints-v1', checkpoints: []});
  put('data/world-index.json', {parts: ['geography/source.json']});
  for (const name of ['data/geography/source.json', 'data/canonical-grid/bounds.json.gz', 'data/hierarchy.json',
    'data/canonical-grid/manifest.json', 'data/geographic-releases/index.json', 'data/geographic-releases/current.json.gz',
    ...['source-override.json', 'ledger.json', 'registry.json', 'patch.json', 'runtime.json', 'base-manifest.json',
      'owners.json.gz', 'receipt.json', 'native/rows.bin.gz', 'native-bank/fragment.gz', 'review.json', 'code.json', 'qualification.gz'].map(p => P + p)]) {
    put(name, 'opaque selected output: ' + name);
  }
  put(RECEIVING, 'receiving metadata');
  // A huge/unknown historical graph is not part of selected-data applicability.
  put(P + 'historical-authority.json', {unrecognized_producer: true, routes: Array.from({length: 5000}, (_, i) => 'old-' + i)});
  const original = commit();
  const historical = name => pin(name, original);
  put(P + 'native-bank/index.json', {version: 1, kind: 'ordered-exact-original-byte-fragments', parts: [{path: 'fragment.gz'}]});
  put(P + 'manifest.json', {version: 2, method: 'native-linear-evenodd-first-owner-v1',
    parts: [{kind: 'rows', path: 'native/rows.bin.gz'}, {kind: 'runs', path: 'native/absent.bin.gz'}],
    original_assets: {bounds: {commit: original, path: 'data/canonical-grid/bounds.json.gz'}},
    native_asset_transport: {version: 1, kind: 'ordered-exact-original-byte-fragments', index: currentPin(P + 'native-bank/index.json'), logical_assets: 2, original_compressed_bytes: 1}});
  put(P + 'source-bank.json', {version: 1, kind: 'complete-world-index-with-exact-encoded-overrides',
    world_index: historical('data/world-index.json'), unchanged_files: [historical('data/geography/source.json')], overrides: [historical(P + 'source-override.json')]});
  put(P + 'artifact-certificate.json', {version: 1, kind: 'qualified-arctic-immutable-product-certificate-v1',
    application_consumer_code: currentPin(P + 'code.json'), qualification_inventory: currentPin(P + 'qualification.gz')});
  const selection = {version: 1, method: 'native-linear-evenodd-first-owner-v1', release_id: 'fixture-release',
    manifest_path: P + 'manifest.json', sha256: sha(files[P + 'manifest.json']),
    selected_geography: {version: 1, kind: 'complete-world-index-with-exact-encoded-overrides', ...currentPin(P + 'source-bank.json')},
    artifact_consumption: {certificate: currentPin(P + 'artifact-certificate.json'), review: currentPin(P + 'review.json')}};
  put(P + 'sidecar.json', {version: 2, kind: 'retained-native-additive-selection-v2', base_selection: selection,
    authority_registry: historical(P + 'registry.json'), runtime_envelope: historical(P + 'runtime.json'),
    logical_asset_map: {base_manifest: historical(P + 'base-manifest.json'), ledger: historical(P + 'ledger.json'),
      owner_roster: historical(P + 'owners.json.gz'), patch: historical(P + 'patch.json')}});
  put('data/ownership-selection.json', {...selection, additive_release: currentPin(P + 'sidecar.json')});
  put('data/geographic-releases/current-manifest.json', {path: 'current.json.gz', sha256: sha(files['data/geographic-releases/current.json.gz'])});
  put('scripts/native-ownership/verified-candidates.json', {version: 1, candidates: {[selection.sha256]:
    {role: 'reviewed-exhaustive-native-rule-comparison', commit: original, path: P + 'receipt.json'}}});
  const baseline = commit(files, original), candidateFiles = {...files, 'scripts/changed-reader.mjs': body('new software'),
    [P + 'new-evidence.json']: body('new evidence has no selected data binding')};
  const candidate = commit(candidateFiles, baseline);
  const calls = {acquire: 0, origins: 0};
  const acquisition = {async acquire() { calls.acquire++; throw Error('unexpected metadata acquisition'); },
    acquireOrigins() { calls.origins++; throw Error('historical replay forbidden'); }, summary() { return {...calls}; }};
  return {directory, files, candidateFiles, original, baseline, candidate, git, pin, commit, calls,
    inspect: (head = candidate, base = baseline, extra = {}) => inspectUnchangedSelectedGeography({repo: directory, baseline: base, candidate: head, acquisition, ...extra}),
    close() { fs.rmSync(directory, {recursive: true}); }};
}

test('unchanged selected outputs need no historical legality or producer-schema replay', async () => {
  const f = fixture(); try {
    const result = await f.inspect();
    assert.equal(result.status, 'unchanged-selected-inputs', result.reason);
    assert.equal(result.science_reexecuted, false); assert.equal(result.source_approval, false); assert.equal(result.published, false);
    assert(result.immutable_descriptors.some(p => p.path === P + 'patch.json' && p.commit === f.original));
    assert(result.current_and_absent_alternatives.some(p => p.path === P + 'native/absent.bin.gz' && p.absent));
    assert(!result.immutable_descriptors.some(p => p.path.includes('historical-authority')));
    assert(result.metadata_bytes_read < 10000); assert(result.git_calls < 200);
    assert.deepEqual(f.calls, {acquire: 0, origins: 0});
  } finally { f.close(); }
});

test('every directly selected data family rejects changed bytes, including baseline-only drift', async () => {
  const f = fixture(); try {
    const names = ['data/ownership-selection.json', 'data/world-index.json', 'data/geography/source.json', 'data/hierarchy.json',
      'data/canonical-grid/manifest.json', 'data/geographic-releases/index.json', 'data/geographic-releases/current-manifest.json',
      'data/geographic-releases/current.json.gz', 'scripts/native-ownership/verified-candidates.json',
      ...['manifest.json', 'source-bank.json', 'source-override.json', 'native/rows.bin.gz', 'native-bank/index.json',
        'native-bank/fragment.gz', 'sidecar.json', 'registry.json', 'ledger.json', 'patch.json', 'runtime.json', 'base-manifest.json',
        'owners.json.gz', 'receipt.json', 'artifact-certificate.json', 'review.json', 'code.json', 'qualification.gz'].map(p => P + p)];
    for (const name of names) {
      const changed = f.commit({...f.candidateFiles, [name]: body('changed selected data')}, f.baseline);
      const result = await f.inspect(changed);
      assert.equal(result.status, 'full-check-required', name); assert.match(result.reason, /changed-current-input/, name);
    }
    const baseline = f.commit({...f.files, [P + 'patch.json']: body('baseline-only changed output')}, f.baseline);
    assert.match((await f.inspect(f.candidate, baseline)).reason, /changed-current-input/);
  } finally { f.close(); }
});

test('selected modes, missing bodies, newly materialized aliases and nonordinary members fail closed', async () => {
  const f = fixture(); try {
    const target = P + 'patch.json';
    const removed = {...f.candidateFiles}; delete removed[target];
    for (const head of [f.commit(removed, f.baseline), f.commit(f.candidateFiles, f.baseline, {[target]: '100755'}),
      f.commit(f.candidateFiles, f.baseline, {[target]: '120000'}),
      f.commit({...f.candidateFiles, [P + 'native/absent.bin.gz']: body('new materialization')}, f.baseline),
      f.commit({...f.candidateFiles, [P + 'native/absent.bin.gz/child']: body('directory alias')}, f.baseline)]) {
      assert.equal((await f.inspect(head)).status, 'full-check-required');
    }
  } finally { f.close(); }
});

test('equal malformed or mismatched selected pins cannot manufacture applicability', async () => {
  const f = fixture(); try {
    const cases = [
      ['data/ownership-selection.json', value => { value.unpinned_input = {path: 'foreign.json'}; }],
      [P + 'sidecar.json', value => { delete value.logical_asset_map.patch.git_blob_oid; }],
      [P + 'sidecar.json', value => { value.authority_registry.git_blob_oid = 'f'.repeat(40); }],
      [P + 'sidecar.json', value => { value.runtime_envelope.mode = '100755'; }],
      [P + 'sidecar.json', value => { value.logical_asset_map.ledger.path = P + 'missing.json'; }],
      [P + 'source-bank.json', value => { value.world_index.git_blob_oid = 'e'.repeat(40); }],
      [P + 'source-bank.json', value => { delete value.overrides[0].sha256; }]
    ];
    for (const [name, mutate] of cases) {
      const value = JSON.parse(f.files[name]); mutate(value);
      const files = {...f.files, [name]: body(value)};
      // Keep parent selector hashes coherent so the actual nested pin is tested.
      if (name !== 'data/ownership-selection.json') {
        const selection = JSON.parse(files['data/ownership-selection.json']);
        const role = name.endsWith('sidecar.json') ? 'additive_release' : 'selected_geography';
        selection[role].bytes = files[name].length; selection[role].sha256 = sha(files[name]);
        files['data/ownership-selection.json'] = body(selection);
      }
      const baseline = f.commit(files, f.baseline), head = f.commit({...files, 'unrelated.txt': body('change')}, baseline);
      assert.equal((await f.inspect(head, baseline)).status, 'full-check-required', name);
    }
  } finally { f.close(); }
});

test('software changes bind one actual executing checkout and do not certify its science', async () => {
  const f = fixture(); try {
    const head = f.commit({...f.candidateFiles, 'scripts/check-effective-geographic-regression.mjs': body('new checker'),
      'src/native-grid.js': body('new algorithm'), 'package.json': body('new runtime')}, f.baseline);
    f.git(['update-ref', 'refs/heads/executing', head]); f.git(['symbolic-ref', 'HEAD', 'refs/heads/executing']);
    const options = {repo: f.directory, baseline: f.baseline, candidate: head, trusted: head};
    const result = await inspectExecutingSelectedGeography(options);
    assert.equal(result.status, 'unchanged-selected-inputs', result.reason); assert.equal(result.trusted_reader_policy_commit, head);
    assert.equal(result.science_reexecuted, false); assert(result.limits.some(p => p.includes('no historical legality')));
    assert.equal((await inspectExecutingSelectedGeography({...options, trusted: f.baseline})).reason, 'executing-checkout-mismatch');
  } finally { f.close(); }
});

test('receiving metadata remains exactly scoped and cannot exempt an actual selected output', async () => {
  const f = fixture(); try {
    const head = f.commit({...f.files, [RECEIVING]: body('updated metadata')}, f.baseline);
    assert.equal((await f.inspect(head, f.baseline, {metadataPaths: [RECEIVING]})).status, 'unchanged-selected-inputs');
    for (const metadataPaths of [[], [RECEIVING, RECEIVING], ['README.md'], [RECEIVING, P + 'evidence-quality.json']]) {
      assert.equal((await f.inspect(head, f.baseline, {metadataPaths})).reason, 'outside-receiving-metadata-scope');
    }
    const bank = JSON.parse(f.files[P + 'source-bank.json']); bank.overrides[0] = f.pin(RECEIVING, f.original);
    const files = {...f.files, [P + 'source-bank.json']: body(bank)}, selection = JSON.parse(files['data/ownership-selection.json']);
    selection.selected_geography.bytes = files[P + 'source-bank.json'].length; selection.selected_geography.sha256 = sha(files[P + 'source-bank.json']);
    files['data/ownership-selection.json'] = body(selection);
    const baseline = f.commit(files, f.baseline), changed = f.commit({...files, [RECEIVING]: body('changed selected output')}, baseline);
    assert.match((await f.inspect(changed, baseline, {metadataPaths: [RECEIVING]})).reason, /changed-current-input/);
  } finally { f.close(); }
});

test('invalid/self comparisons and finite identity/metadata bounds retain the full route', async () => {
  const f = fixture(); try {
    assert.match((await f.inspect(f.baseline)).reason, /baseline-proof/);
    assert.match((await f.inspect('not-a-commit')).reason, /require-immutable/);
    assert.match((await f.inspect(f.candidate, f.baseline, {limits: {member: 1024 * 1024, metadata: 1, entries: 4096}})).reason, /metadata-byte-limit/);
    assert.match((await f.inspect(f.candidate, f.baseline, {limits: {member: 1024 * 1024, metadata: 1024 * 1024, entries: 1}})).reason, /identity-entry-limit/);
  } finally { f.close(); }
});

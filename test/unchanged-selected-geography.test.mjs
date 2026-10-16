import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {pathToFileURL, fileURLToPath} from 'node:url';
import {createRoutingMetadataAcquisition} from '../scripts/geography-routing-metadata.mjs';
import {inspectUnchangedSelectedGeography, inspectExecutingSelectedGeography, EXECUTION_CODE, REBIND_CODE} from '../scripts/check-unchanged-selected-geography.mjs';

import {LEGACY_CURRENT_REBIND_CODE,CURRENT_REBIND_CODE} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const ROOT = fileURLToPath(new URL('../', import.meta.url));
const P = 'research/geography/selected-fixture/';
const POLICY = 'coordination/engineering/selected-geography-effective-prevention-20261009/supported-programs.json';
const CHECKPOINTS = 'coordination/engineering/selected-checkpoint-reuse-20261012/accepted-checkpoints.json';
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(k => [k, canonical(value[k])])) : value;
const HANDOFFS = 'coordination/engineering/melanesia363-additive-delivery-20261010/accepted-administrative-handoffs.json';
const RECEIVING = 'coordination/engineering/receiving-metadata-fixture/';
const METADATA = [RECEIVING + 'README.md', RECEIVING + 'evidence-quality.json'];
const body = value => Buffer.isBuffer(value) ? value : Buffer.from(typeof value === 'string' ? value : JSON.stringify(value));
const sha = value => createHash('sha256').update(body(value)).digest('hex');

// These intentionally tiny opaque leaf bodies test immutable routing/equality,
// not scientific validity. Historical collector replay is compared separately
// with retained original full-reader logs; these leaf sentinels are not decoded.
function fixture({missingOrigin = false, splitBaseline = false, rebind = true, missingStrictOrigin = false, checkpoint = false, sourceTarget = false, membership = false, dated = false, unknownSourceField = false, unknownSourceVersion = false, malformedDatedVersion = false, rebindCode = LEGACY_CURRENT_REBIND_CODE, historicalMetadataAbsent = false} = {}) {
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
    // Git writes the complete fixture tree in one process. The import-only ref
    // is removed before returning; ordinary fixture refs and HEAD stay untouched.
    const reference = 'refs/test-fixture-import';
    const stream = [Buffer.from(`commit ${reference}\nmark :1\n`
      + 'committer fixture <fixture@example.invalid> 0 +0000\ndata 8\nfixture\n'
      + (parent ? `from ${parent}\n` : '') + 'deleteall\n')];
    for (const [name, value] of Object.entries(values)) {
      const raw = body(value);
      stream.push(Buffer.from(`M ${modes[name] ?? '100644'} inline ${JSON.stringify(name)}\ndata ${raw.length}\n`), raw, Buffer.from('\n'));
    }
    stream.push(Buffer.from(`\nget-mark :1\nreset ${reference}\n\ndone\n`));
    const id = git(['fast-import', '--quiet', '--force'], Buffer.concat(stream));
    commits.set(id, {...values}); return id;
  }
  const pin = (name, at, extra = {}) => {
    const raw = commits.get(at)[name];
    return {commit: at, path: name, mode: '100644', git_blob_oid: git(['hash-object', '--stdin'], raw), bytes: raw.length, sha256: sha(raw), ...extra};
  };
  for (const name of new Set([...EXECUTION_CODE, ...REBIND_CODE, 'scripts/geography-prefetch.mjs'])) put(name, 'trusted code leaf');
  const catalogue = {version: 1, kind: 'accepted-selected-checkpoints-v1', checkpoints: []};
  put(CHECKPOINTS, catalogue);
  put(POLICY, fs.readFileSync(path.join(ROOT, POLICY)));
  const world = {parts: ['geography/source.json']};
  put('data/world-index.json', world);
  for (const name of ['data/geography/source.json', 'data/canonical-grid/bounds.json.gz', 'data/hierarchy.json', 'data/canonical-grid/manifest.json', 'data/geographic-releases/index.json', 'data/geographic-releases/current.json.gz']) put(name, 'opaque complete scientific leaf');
  for (const name of ['handoff', 'receipt', 'source-publication', 'source-inventory', 'source-operating', 'native-publication', 'native-inventory', 'native-operating', 'native-asset', 'source-facts', 'native-facts', 'original-ledger', 'original-manifest', 'rule', 'predecessor', 'code-source', 'terminal', 'stderr', 'stdout', 'source-catalogue', 'physical-input', 'physical-reproduction', 'physical-evidence', 'latitudes', 'source-part', 'membership-lineage', 'membership-index', 'membership-part', 'dated-adoption', 'dated-review', 'dated-observation', 'dated-frame']) put(P + name + '.json', {leaf: name});
  put(P + 'original-source-map.json', {kind: 'complete-world-index-with-exact-encoded-overrides'});
  put('data/ownership-selection.json', {selected_geography: {kind: 'complete-world-index-with-exact-encoded-overrides', path: P + 'original-source-map.json'}});
  const metadataModules=['scripts/selected-reference-metadata.mjs','src/reference-metadata.js'];
  const retainedMetadata=Object.fromEntries(metadataModules.map(name=>[name,files[name]]));
  if(historicalMetadataAbsent)for(const name of metadataModules)delete files[name];
  const original = commit();
  if(historicalMetadataAbsent)Object.assign(files,retainedMetadata);
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
  let binding = {version: 1, kind: 'original-issued-rule-source-custody-v1', original_pins: originalPins,
    source_output_aliases: [{original: aliasOriginal, published: pin(P + 'source-publication.json', original, missingStrictOrigin ? {commit: 'e'.repeat(40)} : {})}],
    native_proof: {publication: historical(P + 'native-publication.json'), inventory: historical(P + 'native-inventory.json'), operating: historical(P + 'native-operating.json'), assets: [historical(P + 'native-asset.json')]}};
  if (sourceTarget) {
    const roles = {catalogue: 'source-catalogue', physical_input: 'physical-input', physical_reproduction: 'physical-reproduction',
      physical_evidence: 'physical-evidence', native_latitudes: 'latitudes', owner_roster: 'native-asset'};
    const evidence = {version: dated ? 2 : 1, kind: 'source-target-native-evidence-v' + (dated ? 2 : 1),
      base_reference: {}, native_contract: {}, targets: [{id: 'opaque-scientific-target'}],
      families: [{source_id: 'fixture', parts: [historical(P + 'source-part.json')]}],
      ...Object.fromEntries(Object.entries(roles).map(([role, name]) => [role, historical(P + name + '.json')]))};
    if (membership) evidence.source_membership = {index: historical(P + 'membership-index.json'), lineage: historical(P + 'membership-lineage.json'), parts: [historical(P + 'membership-part.json')]};
    if (dated) {
      put(P + 'dated-support.json', {version: 1, kind: 'adopted-dated-native-centre-land-support-v1', native_contract_sha256: 'a'.repeat(64), records: [{}],
        provenance: ['adoption', 'review', 'observation', 'frame'].map(role => ({id: role, role, pin: historical(P + 'dated-' + role + '.json'),
          ...(role === 'frame' ? {observation: 'observation', block_pointer: '/block', display_pointer: '/display', channels: 'rgb', display_base: 'fixture'} : {})}))});
      const support = commit(files, requests);
      evidence.dated_land_support = pin(P + 'dated-support.json', support);
    }
    if (unknownSourceField) {
      evidence.descriptive_metadata = {not_consumed_by_current_reader: true};
      evidence.families[0].description = 'Metadata ignored by the current scientific reader';
    }
    if (unknownSourceVersion) { evidence.version = 3; evidence.kind = 'source-target-native-evidence-v3'; }
    if (malformedDatedVersion) { evidence.version = 1; evidence.kind = 'source-target-native-evidence-v1'; evidence.dated_land_support = historical(P + 'source-part.json'); }
    put(P + 'source-target-evidence.json', evidence);
    const sourceEvidence = commit(files, requests);
    binding = {version: 1, kind: 'source-target-native-custody-v1', native_patch: historical(P + 'native-asset.json'), source_evidence: pin(P + 'source-target-evidence.json', sourceEvidence)};
  }
  put(P + 'binding.json', binding);
  const bindings = commit(files, requests);
  const entry = {authority_sha256: 'a'.repeat(64), rule_sha256: sha(files[P + 'rule.json']), policy_id: 'retained-source-literal-additions', policy_version: 1,
    rule_preimage: historical(P + 'rule.json'), source_authority: pin(P + 'binding.json', bindings)};
  put(P + 'registry.json', {version: 1, kind: 'retained-rule-authority-registry-v1', entries: [entry]});
  const ledger = {version: 2, kind: 'native-additive-repair-ledger-v2'};
  if (rebind) {
    put(P + 'rebind-request.json', {executed_code:rebindCode.map(path=>({path,bytes:(files[path]??body('foreign')).length,sha256:sha(files[path]??body('foreign'))})),acquisition: {target_sources: [{target_id: 'one', path: 'data/geography/source.json'}], predecessor_proof: historical(P + 'predecessor.json')}});
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
  if (checkpoint) {
    // Opaque complete products must remain unread: only their original pins and
    // the explicitly authenticated route metadata are needed for applicability.
    for (const role of ['facts', 'certificate', 'publication', 'routed']) put(P + 'checkpoint-' + role, 'opaque checkpoint ' + role);
    put(P + 'checkpoint-custody', {complete_cold_custody:[{facts:{selected_commit:original}, inventory:[pin(POLICY, original)]}]});
    const routes = [{path: POLICY, tree: `100644 blob ${git(['hash-object', '--stdin'], files[POLICY])}\t${POLICY}\0`}, {path: P + 'checkpoint-absent', tree: ''}, {path: P + 'checkpoint-routed',
      tree: `100644 blob ${git(['hash-object', '--stdin'], files[P + 'checkpoint-routed'])}\t${P}checkpoint-routed\0`}];
    put(P + 'checkpoint-routes', routes);
    const retained = commit(files, assets);
    catalogue.checkpoints.push({id: 'ordinary-retained-root', accepted_head: retained, selected_commit: original,
      selection_sha256: sha(JSON.stringify(canonical(selection)) + '\n'), execution_commit: original,
      execution_code_sha256: 'a'.repeat(64), runtime_sha256: 'b'.repeat(64),
      ...Object.fromEntries(['facts', 'certificate', 'publication', 'custody', 'routes'].map(role => [role, pin(P + 'checkpoint-' + role, retained)]))});
    put(CHECKPOINTS, catalogue);
  }
  put(METADATA[0], 'Receiving packet description.\n');
  put(METADATA[1], {version: 1, description: 'Receiving packet metadata.'});
  const baseline = commit(files, assets), candidateFiles = {...files, 'research/geography/new-packet/source.json': body('unactivated source publication')};
  const candidate = commit(candidateFiles, baseline);
  const inspect = (head = candidate, base = baseline, options = {}) => inspectUnchangedSelectedGeography({repo: directory, baseline: base, candidate: head, ...options});
  return {directory, git, env, files, baseline, candidate, candidateFiles, inspect, commit, original,
    close() { fs.rmSync(directory, {recursive: true, force: true}); }};
}

test('complete typed closure accepts a source-only addition without scientific leaf reads', async () => {
  const f = fixture(); try {
    const result = await f.inspect(); assert.equal(result.status, 'unchanged-selected-inputs', result.reason);
    assert.equal(result.candidate_code_executed, false); assert.equal(result.science_reexecuted, false);
    assert.equal(result.trusted_reader_policy_commit, f.baseline);
    assert(result.current_and_absent_alternatives.some(p => p.path === P + 'native/absent.bin.gz' && p.absent));
    assert(result.immutable_descriptors.some(p => p.path === P + 'issued-plan.json'));
    assert(result.metadata_bytes_read < 1024 * 1024);
  } finally { f.close(); }
});

test('current source-target authority keeps every nested leaf and current fallback alias', async () => {
  const f = fixture({sourceTarget: true, membership: true, dated: true}); try {
    const result = await f.inspect();
    assert.equal(result.status, 'unchanged-selected-inputs', result.reason);
    assert.equal(result.science_reexecuted, false);
    const leaves = ['source-catalogue', 'physical-input', 'physical-reproduction', 'physical-evidence',
      'latitudes', 'native-asset', 'source-part', 'membership-index', 'membership-lineage', 'membership-part',
      'dated-adoption', 'dated-review', 'dated-observation', 'dated-frame'];
    for (const name of [...leaves, 'source-target-evidence', 'dated-support', 'binding']) {
      const target = P + name + '.json';
      assert(result.current_and_absent_alternatives.some(p => p.path === target), target);
      const changed = f.commit({...f.candidateFiles, [target]: body('changed consumed input')}, f.baseline);
      const rejected = await f.inspect(changed);
      assert.equal(rejected.status, 'full-check-required', target);
      assert.equal(rejected.reason, 'changed-current-input:' + target);
    }
    // Leaf sentinels are not valid scientific JSON inputs. The proof only reads
    // the evidence/binding/support routing bodies, never requalifying science.
    assert(result.metadata_bytes_read < 1024 * 1024);
    const target = P + 'source-part.json', baselineFiles = {...f.files};
    delete baselineFiles[target];
    const baseline = f.commit(baselineFiles, f.baseline);
    const candidate = f.commit({...baselineFiles, 'docs/delivery.md': body('ordinary delivery')}, baseline);
    const absent = await f.inspect(candidate, baseline);
    assert.equal(absent.status, 'unchanged-selected-inputs', absent.reason);
    assert(absent.current_and_absent_alternatives.some(p => p.path === target && p.absent));
    const added = f.commit({...baselineFiles, [target]: f.files[target]}, baseline);
    assert.equal((await f.inspect(added, baseline)).reason, 'changed-current-input:' + target);
  } finally { f.close(); }
});

test('current source-target authority supports retained fallback and descriptive fields but rejects unknown versions', async () => {
  for (const options of [{missingOrigin: true}, {unknownSourceField: true}, {unknownSourceVersion: true}, {malformedDatedVersion: true}]) {
    const f = fixture({sourceTarget: true, ...options}); try {
      const result = await f.inspect();
      if (!options.unknownSourceVersion && !options.malformedDatedVersion) assert.equal(result.status, 'unchanged-selected-inputs', result.reason);
      else {
        assert.equal(result.status, 'full-check-required');
        assert.equal(result.reason, 'unsupported-source-target-evidence');
      }
    } finally { f.close(); }
  }
});

test('checkpoint roots and complete present/absent route aliases are collected without scientific decoding', async () => {
  const f = fixture({checkpoint: true}); try {
    const result = await f.inspect();
    assert.equal(result.status, 'unchanged-selected-inputs', result.reason);
    for (const role of ['facts', 'certificate', 'publication', 'custody', 'routes', 'routed', 'absent']) {
      assert(result.current_and_absent_alternatives.some(p => p.path === P + 'checkpoint-' + role), role);
    }
    // These aliases were outside the old selected-bank collector. Each remains
    // source-publication scoped, so only the new dependency traversal rejects it.
    for (const role of ['facts', 'certificate', 'publication', 'custody', 'routes', 'routed', 'absent']) {
      const target = P + 'checkpoint-' + role;
      const candidate = f.commit({...f.candidateFiles, [target]: body('altered retained alias')}, f.baseline);
      const rejected = await f.inspect(candidate);
      assert.equal(rejected.status, 'full-check-required', role);
      assert.match(rejected.reason, /changed-current-input/, role);
    }
  } finally { f.close(); }
});

test('checkpoint execution policy evolves independently while its original custody remains bound', async () => {
  const f = fixture({checkpoint:true}); try {
    const files = {...f.files, [POLICY]:body({...JSON.parse(f.files[POLICY]), programs:[...JSON.parse(f.files[POLICY]).programs, {new_accepted_record:'trusted-only'}]})};
    const baseline = f.commit(files, f.baseline), candidate = f.commit({...files, 'research/geography/new-packet/source.json':body('source')}, baseline);
    const accepted = await f.inspect(candidate, baseline);
    assert.equal(accepted.status, 'unchanged-selected-inputs', accepted.reason);
    assert(accepted.immutable_descriptors.some(p => p.path === POLICY && p.commit === f.original));
    assert(accepted.immutable_descriptors.some(p => p.path === POLICY && p.commit === baseline));
    assert(!accepted.immutable_descriptors.some(p => p.path === POLICY && p.commit === candidate));
    const altered = f.commit({...files, [P + 'checkpoint-routed']:body('adjacent scientific drift')}, baseline);
    assert.match((await f.inspect(altered, baseline)).reason, /changed-current-input/);
    for (const mutate of [p => p.programs.pop(), p => p.current_rebind_migrations.pop(), p => { p.programs[0].accepted_head = 'f'.repeat(40); }]) {
      const policy = JSON.parse(f.files[POLICY]); mutate(policy);
      const changedFiles = {...f.files, [POLICY]:body(policy)}, changedBase = f.commit(changedFiles, f.baseline);
      const changedCandidate = f.commit({...changedFiles, 'research/geography/new-packet/source.json':body('source')}, changedBase);
      assert.match((await f.inspect(changedCandidate, changedBase)).reason, /checkpoint-policy-eligibility-removed/);
    }
  } finally { f.close(); }
});

test('checkpoint trust is executing catalogue authority and rejects unknown roots, vectors and route schemas', async () => {
  const f = fixture({checkpoint: true}); try {
    const unknownModule = 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
    const changedCode = f.commit({...f.files, [unknownModule]: body('changed checkpoint reader')}, f.baseline);
    assert.match((await f.inspect(f.candidate, changedCode)).reason, /changed-current-input/);
    const changedCatalogue = f.commit({...f.files, [CHECKPOINTS]: body({candidate: 'cannot supply roster'})}, f.baseline);
    assert.match((await f.inspect(f.candidate, changedCatalogue)).reason, /changed-current-input/);
    const candidateCatalogue = JSON.parse(f.files[CHECKPOINTS]); candidateCatalogue.checkpoints = [];
    const untrustedFiles = {...f.files, [CHECKPOINTS]: body(candidateCatalogue)};
    const untrustedBase = f.commit(untrustedFiles, f.baseline);
    const untrustedCandidate = f.commit({...untrustedFiles, [P + 'checkpoint-routed']: body('changed source-scoped alias')}, untrustedBase);
    assert.match((await f.inspect(untrustedCandidate, untrustedBase, {trusted:f.baseline})).reason,
      /changed-current-input/, 'candidate catalogue cannot suppress the executing trusted roster');
    for (const mutate of [c => c.checkpoints.push(c.checkpoints[0]),
      c => c.checkpoints[0].extra_route = {}, c => c.checkpoints[0].certificate.git_blob_oid = 'e'.repeat(40)]) {
      const catalogue = JSON.parse(f.files[CHECKPOINTS]); mutate(catalogue);
      const files = {...f.files, [CHECKPOINTS]: body(catalogue)};
      const baseline = f.commit(files, f.baseline), candidate = f.commit({...files, 'research/geography/new-packet/source.json': body('source')}, baseline);
      assert.equal((await f.inspect(candidate, baseline)).status, 'full-check-required');
    }
    for (const routes of [[{path: P + 'checkpoint-absent', tree: '', extra: true}],
      [{path: P + 'checkpoint-routed', tree: ''}], [{path: '../outside', tree: ''}]]) {
      const files = {...f.files, [P + 'checkpoint-routes']: body(routes)};
      const retained = f.commit(files, f.baseline), catalogue = JSON.parse(files[CHECKPOINTS]);
      const raw = files[P + 'checkpoint-routes'];
      catalogue.checkpoints[0].routes = {...catalogue.checkpoints[0].routes, commit: retained,
        git_blob_oid: f.git(['hash-object', '--stdin'], raw), bytes: raw.length, sha256: sha(raw)};
      files[CHECKPOINTS] = body(catalogue);
      const baseline = f.commit(files, retained), candidate = f.commit({...files, 'research/geography/new-packet/source.json': body('source')}, baseline);
      assert.equal((await f.inspect(candidate, baseline)).status, 'full-check-required');
    }
  } finally { f.close(); }
});

test('unchanged same-path fallbacks and strict administrative selector splits are covered', async () => {
  for (const options of [{missingOrigin: true}, {splitBaseline: true}]) {
    const f = fixture(options); try { const result = await f.inspect(); assert.equal(result.status, 'unchanged-selected-inputs', result.reason); }
    finally { f.close(); }
  }
});

test('every nested current/fallback custody family rejects changed retained aliases', async () => {
  const f = fixture(); try {
    for (const name of ['binding', 'native-request', 'source-request', 'source-facts', 'native-facts', 'original-manifest', 'original-ledger',
      'source-publication', 'source-inventory', 'source-operating', 'native-publication', 'native-inventory', 'native-operating', 'native-asset', 'predecessor', 'handoff', 'rule']) {
      const target = P + name + '.json';
      const candidate = f.commit({...f.candidateFiles, [target]: body('changed retained body')}, f.baseline);
      const result = await f.inspect(candidate);
      assert.equal(result.status, 'full-check-required', target);
      assert.match(result.reason, /changed-current-input|historical-pin/);
    }
  } finally { f.close(); }
});

test('native materialization absence, source map, transport and selected registry changes reject', async () => {
  const f = fixture(); try {
    for (const target of ['native/absent.bin.gz', 'native-bank/fragment.gz', 'source-bank.json', 'registry.json', 'sidecar.json', 'ledger.json']) {
      const candidate = f.commit({...f.candidateFiles, [P + target]: body('changed selected input')}, f.baseline);
      assert.equal((await f.inspect(candidate)).status, 'full-check-required', target);
    }
  } finally { f.close(); }
});

test('ordinary queue docs and focused tests do not change selected science while consumed code still rejects', async () => {
  const f = fixture(); try {
    const unrelated = {'scripts/run-worker-merge.mjs':body('changed delivery queue'),
      'docs/WORKER_COORDINATION.md':body('updated review instructions'),
      'test/merge-integration.test.mjs':body('updated queue control')};
    const candidate = f.commit({...f.files,...unrelated},f.baseline);
    const accepted = await f.inspect(candidate);
    assert.equal(accepted.status,'unchanged-selected-inputs',accepted.reason);
    assert.equal(accepted.science_reexecuted,false);
    assert.equal(accepted.candidate_code_executed,false);
    for (const name of ['scripts/check-effective-geographic-regression.mjs','src/native-grid.js',
      'src/ownership-codec.js','src/effective-footprint.js','scripts/selected-reference-metadata.mjs','src/reference-metadata.js','package.json','package-lock.json']) {
      const changed = f.commit({...f.files,...unrelated,[name]:body('changed consumed method or runtime')},f.baseline);
      const rejected = await f.inspect(changed);
      assert.equal(rejected.status,'full-check-required',name);
      assert.equal(rejected.reason,'changed-current-input:'+name);
    }
  } finally { f.close(); }
});

test('baseline-only relevant code differs even when candidate authored scope is only source', async () => {
  const f = fixture(); try {
    const baseline = f.commit({...f.files, 'src/effective-footprint.js': body('changed current custody code')}, f.baseline);
    const result = await f.inspect(f.candidate, baseline);
    assert.equal(result.status, 'full-check-required'); assert.match(result.reason, /changed-current-input:src\/effective-footprint/);
  } finally { f.close(); }
});

test('baseline-only unused programme-copy and source support changes do not alter actual consumed code', async () => {
  const f = fixture(); try {
    const baseline = f.commit({...f.files, [POLICY]: body({version: 1, kind: 'trusted-source-native-programmes-v1', changed: 'trusted-only'}),
      'scripts/additive-gap-repair.mjs': body('not executed by this reader'), 'coordination/engineering/unrelated-source-support/README.md': body('unrelated')}, f.baseline);
    const result = await f.inspect(f.candidate, baseline);
    assert.equal(result.status, 'unchanged-selected-inputs', result.reason);
    assert(result.immutable_descriptors.some(p => p.path === POLICY && p.commit === baseline));
    assert(!result.immutable_descriptors.some(p => p.path === POLICY && p.commit === f.candidate));
  } finally { f.close(); }
});

test('artifact transport code is equality-bound without a scientific reader hash whitelist', async () => {
  const f = fixture(); try {
    const code = 'scripts/geographic-report-artifact.mjs';
    assert(EXECUTION_CODE.includes(code));
    const upgraded = body('reviewed artifact transport update; no scientific route discovery');
    const baseline = f.commit({...f.files, [code]: upgraded}, f.baseline);
    const candidate = f.commit({...f.candidateFiles, [code]: upgraded}, baseline);
    const accepted = await f.inspect(candidate, baseline);
    assert.equal(accepted.status, 'unchanged-selected-inputs', accepted.reason);
    const changed = f.commit({...f.candidateFiles, [code]: body('different candidate transport code')}, baseline);
    const refused = await f.inspect(changed, baseline);
    assert.equal(refused.status, 'full-check-required');
    assert.equal(refused.reason, 'changed-current-input:' + code);
    const differentBaseline = await f.inspect(f.candidate, baseline);
    assert.equal(differentBaseline.status, 'full-check-required');
    assert.equal(differentBaseline.reason, 'changed-current-input:' + code);
  } finally { f.close(); }
});

test('reviewed equal readers need no hash catalogue; unsafe modes, limits and identical commits decline', async () => {
  const f = fixture(); try {
    assert.match((await f.inspect(f.baseline)).reason, /baseline-proof/);
    assert.match((await f.inspect(f.candidate, f.baseline, {limits: {member: 32 * 1024 * 1024, metadata: 1, entries: 4096}})).reason, /metadata-byte-limit/);
    assert.match((await f.inspect(f.candidate, f.baseline, {limits: {member: 32 * 1024 * 1024, metadata: 64 * 1024 * 1024, entries: 1}})).reason, /identity-entry-limit/);
    const code = 'scripts/check-effective-geographic-regression.mjs';
    const baseline = f.commit({...f.files, [code]: body('reviewed reader update with unchanged routes')}, f.baseline);
    const candidate = f.commit({...f.candidateFiles, [code]: body('reviewed reader update with unchanged routes')}, baseline);
    const accepted = await f.inspect(candidate, baseline);
    assert.equal(accepted.status, 'unchanged-selected-inputs', accepted.reason);
    assert.match((await f.inspect(f.candidate, baseline)).reason, /changed-current-input/);
    const symlink = f.commit(f.candidateFiles, f.baseline, {'research/geography/new-packet/source.json': '120000'});
    assert.match((await f.inspect(symlink)).reason, /nonordinary/);
  } finally { f.close(); }
});

test('invalid commits fail closed while unrelated engineering changes retain unchanged scientific identities', async () => {
  const f = fixture(); try {
    const output = execFileSync(process.execPath, [path.join(ROOT, 'scripts/check-unchanged-selected-geography.mjs'), f.directory, f.baseline, f.baseline]);
    assert.equal(JSON.parse(output).status, 'full-check-required');
    const candidate = f.commit({...f.candidateFiles, 'scripts/other.mjs': body('engineering')}, f.baseline);
    const result = await f.inspect(candidate);
    assert.equal(result.status, 'unchanged-selected-inputs', result.reason);
    assert.equal(result.science_reexecuted, false);
  } finally { f.close(); }
});

test('receipt fallback requires an absent commit, not a missing path in an existing commit', async () => {
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
      const result = await f.inspect(candidate, baseline);
      assert.equal(result.status, expected, result.reason);
      if (expected === 'full-check-required') assert.match(result.reason, /missing-required-input/);
    }
  } finally { f.close(); }
});

test('unknown routing layouts decline even when their before/after blobs are equal', async () => {
  const f = fixture(); try {
    const selector = JSON.parse(f.files['data/ownership-selection.json']);
    selector.new_routing_hook = {path: 'outside.json'};
    const files = {...f.files, 'data/ownership-selection.json': body(selector)};
    const baseline = f.commit(files, f.baseline);
    const candidate = f.commit({...files, 'research/geography/new-packet/source.json': body('source only')}, baseline);
    const result = await f.inspect(candidate, baseline);
    assert.equal(result.status, 'full-check-required'); assert.match(result.reason, /unsupported-selection/);
  } finally { f.close(); }
});


function coldFixture(f, options = {}) {
  const destination = path.join(f.directory, 'cold');
  f.git(['config', 'uploadpack.allowFilter', 'true']);
  f.git(['update-ref', 'refs/heads/fixture', f.candidate]);
  f.git(['symbolic-ref', 'HEAD', 'refs/heads/fixture']);
  if (options.shallowStart) {
    execFileSync('git', ['init', '--bare', destination], {env: f.env, stdio: ['ignore', 'pipe', 'pipe']});
    for (const args of [['--depth=1', f.baseline], [f.candidate]]) {
      execFileSync('git', ['-C', destination, 'fetch', '--filter=blob:none', '--no-tags', '--no-write-fetch-head',
        ...(args.length === 2 ? [args[0]] : []), pathToFileURL(f.directory).href, args.at(-1)],
        {env: f.env, stdio: ['ignore', 'pipe', 'pipe']});
    }
  } else {
    execFileSync('git', ['clone', '--bare', '--filter=blob:none', '--no-local', pathToFileURL(f.directory).href, destination],
      {env: f.env, stdio: ['ignore', 'pipe', 'pipe']});
  }
  const git = (args, input) => execFileSync('git', ['-C', destination, ...args],
    {env: f.env, input, stdio: ['pipe', 'pipe', 'pipe']}).toString().trim();
  const requests = [], batches = [], originBatches = [];
  const loadTree = async (root, recursive) => {
    requests.push({root, recursive});
    const lines = f.git(['ls-tree', '-z', '-l', ...(recursive ? ['-r'] : []), root]).split('\0').filter(Boolean);
    const tree = lines.map(line => {
      const match = line.match(/^(\d+) (\w+) ([a-f0-9]{40}) +([0-9-]+)\t(.+)$/);
      assert(match, line);
      return {mode: match[1], type: match[2], sha: match[3], ...(match[2] === 'blob' ? {size: Number(match[4])} : {}), path: match[5]};
    });
    return {sha: root, truncated: false, tree};
  };
  const execute = (command, args, callOptions) => {
    assert.equal(callOptions.env.GIT_NO_LAZY_FETCH, '1');
    if (args.includes('fetch')) {
      assert(args.includes('--stdin')); assert(args.includes('--filter=blob:none'));
      assert(args.includes('fetch.negotiationAlgorithm=noop'));
      const ids = callOptions.input.trim().split('\n');
      if (ids.every(id => { try { return f.git(['cat-file', '-t', id]) === 'commit'; } catch { return id === 'e'.repeat(40); } })) originBatches.push(ids);
      else batches.push(ids);
      args = args.map(arg => arg === 'https://github.com/ChengshuLi/WorldAtlas.git' ? pathToFileURL(f.directory).href : arg);
    }
    const result = execFileSync(command, args, callOptions);
    if (options.injectUnexpectedBlob && args.includes('fetch') && originBatches.length) {
      git(['hash-object', '-w', '--stdin'], 'unexpected scientific body');
    }
    return result;
  };
  const acquisition = createRoutingMetadataAcquisition({repo: destination, baseline: f.baseline, execute, loadTree, token: undefined, ...options});
  return {destination, git, batches, originBatches, requests, acquisition};
}

test('clean blob:none clone acquires only routing metadata in bounded discovery batches', async () => {
  const f = fixture({splitBaseline: true}); try {
    const cold = coldFixture(f);
    const before = cold.git(['cat-file', '--batch-all-objects', '--batch-check=%(objecttype)']);
    assert(!before.split('\n').includes('blob'));
    // Retain the actual shallow marker found in a depth-one baseline checkout.
    // Candidate ancestry already supplies its parents; no graph import is needed.
    fs.writeFileSync(path.join(cold.destination, 'shallow'), f.baseline + '\n');
    const result = await f.inspect(f.candidate, f.baseline, {repo: cold.destination, acquisition: cold.acquisition});
    assert.equal(result.status, 'unchanged-selected-inputs', result.reason);
    assert(cold.batches.length > 0 && cold.batches.length <= 12);
    assert(cold.batches.some(batch => batch.length >= 4));
    assert.equal(new Set(cold.batches.flat()).size, cold.batches.flat().length);
    const forbidden = ['data/geography/source.json', 'data/canonical-grid/bounds.json.gz',
      P + 'native-bank/fragment.gz', P + 'native-asset.json', P + 'source-publication.json', P + 'patch.json'];
    for (const name of forbidden) {
      const oid = f.git(['hash-object', '--stdin'], f.files[name]);
      assert(!cold.batches.flat().includes(oid), name);
      assert.equal(cold.git(['cat-file', '--batch-check'], oid + '\n'), oid + ' missing', name);
    }
    assert.equal(result.metadata_acquisition.scientific_leaf_imports, 0);
    const importedBlobs = cold.git(['cat-file', '--batch-all-objects', '--batch-check=%(objectname) %(objecttype)'])
      .split('\n').filter(line => line.endsWith(' blob')).map(line => line.split(' ')[0]).sort();
    assert.deepEqual(importedBlobs, [...new Set(cold.batches.flat())].sort());
    assert.equal(fs.readFileSync(path.join(cold.destination, 'shallow'), 'utf8'), f.baseline + '\n');
    assert(cold.originBatches.length > 0); // Detached strict producer commits are real missing objects.
    assert.deepEqual(result.metadata_acquisition.strict_origin_commits.sort(), cold.originBatches.flat().sort());
    assert.equal(result.metadata_acquisition.verified_import_objects, cold.batches.flat().length);
    assert(cold.requests.filter(row => row.recursive).length === 1);
    const count = cold.batches.length;
    const warm = await f.inspect(f.candidate, f.baseline, {repo: cold.destination, acquisition: cold.acquisition});
    assert.equal(warm.status, 'unchanged-selected-inputs', warm.reason); assert.equal(cold.batches.length, count);
  } finally { f.close(); }
});

test('shallow descendant admits its baseline without traversing an absent parent', async () => {
  const f = fixture(); try {
    const cold = coldFixture(f, {shallowStart: true});
    const parent = f.git(['rev-parse', f.baseline + '^']);
    assert.equal(cold.git(['cat-file', '--batch-check'], parent + '\n'), parent + ' missing');
    assert.equal(cold.git(['merge-base', f.baseline, f.candidate]), f.baseline);
    assert.throws(() => execFileSync('git', ['-C', cold.destination, 'merge-base', f.baseline, f.candidate],
      {env: {...f.env, GIT_SHALLOW_FILE: '/dev/null'}, stdio: ['ignore', 'pipe', 'pipe']}));
    const result = await f.inspect(f.candidate, f.baseline, {repo: cold.destination, acquisition: cold.acquisition});
    assert.equal(result.status, 'unchanged-selected-inputs', result.reason);
    assert.equal(result.metadata_acquisition.scientific_leaf_imports, 0);
    assert.equal(fs.readFileSync(path.join(cold.destination, 'shallow'), 'utf8'), f.baseline + '\n');
  } finally { f.close(); }
});

test('divergent shallow heads use present ancestry only and missing ancestry declines', async () => {
  const f = fixture(); try {
    const baseline = f.commit({...f.files, 'research/geography/baseline-only/readme': body('unrelated')}, f.baseline);
    fs.writeFileSync(path.join(f.directory, 'shallow'), baseline + '\n');
    assert.throws(() => f.git(['merge-base', baseline, f.candidate]));
    const result = await f.inspect(f.candidate, baseline);
    assert.equal(result.status, 'unchanged-selected-inputs', result.reason);
    // The fixture writes loose objects only. Remove the needed common ancestor,
    // not a real repository object; neither query may fetch missing history.
    const ancestor = path.join(f.directory, 'objects', f.baseline.slice(0, 2), f.baseline.slice(2));
    assert(fs.existsSync(ancestor)); fs.unlinkSync(ancestor);
    const missing = await f.inspect(f.candidate, baseline);
    assert.equal(missing.status, 'full-check-required');
    assert.match(missing.reason, /^immutable-object-unavailable:merge-base:/);
    assert.equal(missing.metadata_acquisition.fetch_batches, 0);
    assert.equal(fs.readFileSync(path.join(f.directory, 'shallow'), 'utf8'), baseline + '\n');
  } finally { f.close(); }
});

test('cold absent historical origins retain fallback versus strict semantics', async () => {
  for (const missingStrictOrigin of [false, true]) {
    const f = fixture({missingOrigin: true, missingStrictOrigin}); try {
      const cold = coldFixture(f);
      const result = await f.inspect(f.candidate, f.baseline, {repo: cold.destination, acquisition: cold.acquisition});
      assert.equal(result.status, missingStrictOrigin ? 'full-check-required' : 'unchanged-selected-inputs', result.reason);
      if (missingStrictOrigin) assert.match(result.reason, /routing-strict-origin-acquisition-failed/);
      assert(!cold.batches.flat().includes('e'.repeat(40)));
    } finally { f.close(); }
  }
});

test('cold remote metadata identity declines before object acquisition', async () => {
  const f = fixture(); try {
    const cold = coldFixture(f, {loadTree: async () => ({sha: '0'.repeat(40), tree: []})});
    const result = await f.inspect(f.candidate, f.baseline, {repo: cold.destination, acquisition: cold.acquisition});
    assert.equal(result.status, 'full-check-required');
    assert.equal(cold.batches.length, 0);
  } finally { f.close(); }
});


test('strict graph imports refuse unexpected blobs and aggregate metadata growth', async () => {
  for (const options of [{injectUnexpectedBlob: true},
    {limits: {member: 32 * 1024 * 1024, metadata: 64 * 1024 * 1024, entries: 4096, graphBytes: 1}}]) {
    const f = fixture(); try {
      const cold = coldFixture(f, options);
      const result = await f.inspect(f.candidate, f.baseline, {repo: cold.destination, acquisition: cold.acquisition});
      assert.equal(result.status, 'full-check-required');
      assert.match(result.reason, options.injectUnexpectedBlob ? /routing-strict-fetch-imported-blobs/ : /routing-strict-graph-growth-limit/);
    } finally { f.close(); }
  }
});

test('accepted checkpoint locator and retained whole-member custody remain applicability dependencies', async () => {
  const f=fixture();try {
    const locatorPath='data/selected-checkpoint.json', archivePath='coordination/engineering/next-batch/accepted-a/geography-artifact.zip';
    const locator={version:1,kind:'accepted-selected-checkpoint-locator-v1',acceptance:{pr_number:7,
      request_id:'01234567-abcd-4321-aaaa-123456789012',head:'a'.repeat(40)},retained_artifact:{path:archivePath}};
    const files={...f.files,[locatorPath]:body(locator),[archivePath]:body('opaque accepted artifact body')};
    const base=f.commit(files,f.baseline), candidate=f.commit({...files,'research/geography/new-packet/source.json':body('source addition')},base);
    const unchanged=await f.inspect(candidate,base);assert.equal(unchanged.status,'unchanged-selected-inputs',unchanged.reason);
    assert(unchanged.current_and_absent_alternatives.some(p=>p.path===archivePath));
    for(const target of [locatorPath,archivePath]) {
      const nextBase=f.commit({...files,[target]:body('changed acceptance or member custody')},base);
      const result=await f.inspect(candidate,nextBase);
      assert.equal(result.status,'full-check-required');assert.match(result.reason,/changed-current-input/);
    }
    const absent={...files};delete absent[archivePath];const absentBase=f.commit(absent,base);
    assert.equal((await f.inspect(candidate,absentBase)).status,'full-check-required');
  }finally{f.close();}
});
test('receiving metadata admits exact inert modifications without executing science', async () => {
  const f = fixture(); try {
    for (const metadataPaths of [[METADATA[0]], [METADATA[1]], [...METADATA].reverse()]) {
      const files = {...f.files, ...Object.fromEntries(metadataPaths.map(name => [name, body('updated inert metadata')]))};
      const candidate = f.commit(files, f.baseline);
      const result = await f.inspect(candidate, f.baseline, {metadataPaths});
      assert.equal(result.status, 'unchanged-selected-inputs', result.reason);
      assert.equal(result.candidate_code_executed, false);
      assert.equal(result.science_reexecuted, false);
      assert.equal(result.source_approval, false);
      assert.equal(result.published, false);
      assert.equal(result.trusted_reader_policy_commit, f.baseline);
      assert(result.current_and_absent_alternatives.some(p => p.path === P + 'native/absent.bin.gz' && p.absent));
      assert(result.immutable_descriptors.some(p => p.path === P + 'issued-plan.json'));
      assert(result.metadata_bytes_read < 1024 * 1024);
      for (const name of metadataPaths) {
        const pins = result.immutable_descriptors.filter(p => p.path === name);
        assert.deepEqual(pins.map(p => p.commit).sort(), [f.baseline, candidate].sort());
        assert(pins.every(p => p.mode === '100644'));
        assert.notEqual(pins[0].git_blob_oid, pins[1].git_blob_oid);
      }
      assert.equal((await f.inspect(candidate)).status, 'unchanged-selected-inputs');
    }
  } finally { f.close(); }
});

test('receiving metadata refuses malformed, foreign, mixed or incomplete changed-path scope', async () => {
  const f = fixture(); try {
    const candidate = f.commit({...f.files, [METADATA[0]]: body('updated')}, f.baseline);
    const invalid = [null, METADATA[0], [], [METADATA[0], METADATA[0]], [...METADATA, RECEIVING + 'extra.json'],
      [METADATA[1]], [METADATA[0], METADATA[1]], ['README.md'], ['research/geography/packet/README.md'],
      ['coordination/engineering/job.with.dots/README.md'], [RECEIVING + 'nested/README.md'],
      [RECEIVING + '../README.md'], [RECEIVING + 'README.md/'], [RECEIVING + 'readme.md'],
      [METADATA[0], 'coordination/engineering/another-packet/evidence-quality.json']];
    for (const metadataPaths of invalid) {
      const result = await f.inspect(candidate, f.baseline, {metadataPaths});
      assert.equal(result.status, 'full-check-required', JSON.stringify(metadataPaths));
      assert.match(result.reason, /outside-receiving-metadata-scope/);
    }
    for (const extra of ['coordination/engineering/another-packet/README.md', RECEIVING + 'extra.json',
      'research/geography/new-packet/source.json', 'scripts/run-geographic-check.py',
      'data/geography/source.json', P + 'native-bank/fragment.gz']) {
      const head = f.commit({...f.files, [METADATA[0]]: body('updated'), [extra]: body('changed extra input')}, f.baseline);
      const result = await f.inspect(head, f.baseline, {metadataPaths: [METADATA[0]]});
      assert.equal(result.status, 'full-check-required', extra);
      assert.match(result.reason, /outside-receiving-metadata-scope/);
    }
    const mixed = 'coordination/engineering/another-packet/evidence-quality.json';
    const head = f.commit({...f.files, [METADATA[0]]: body('updated'), [mixed]: body('other packet')}, f.baseline);
    assert.match((await f.inspect(head, f.baseline, {metadataPaths: [METADATA[0], mixed]})).reason,
      /outside-receiving-metadata-scope/);
  } finally { f.close(); }
});

test('receiving metadata requires modifications of ordinary non-executable files', async () => {
  const f = fixture(); try {
    for (const target of METADATA) {
      const absent = {...f.files}; delete absent[target];
      const addedBase = f.commit(absent, f.baseline);
      const added = f.commit(f.files, addedBase);
      assert.match((await f.inspect(added, addedBase, {metadataPaths: [target]})).reason, /missing-required-input/);
      const deleted = f.commit(absent, f.baseline);
      assert.match((await f.inspect(deleted, f.baseline, {metadataPaths: [target]})).reason, /missing-required-input/);
      for (const mode of ['100755', '120000']) {
        const candidate = f.commit(f.files, f.baseline, {[target]: mode});
        assert.match((await f.inspect(candidate, f.baseline, {metadataPaths: [target]})).reason, /nonordinary/);
        const baseline = f.commit(f.files, f.baseline, {[target]: mode});
        const restored = f.commit(f.files, baseline);
        assert.match((await f.inspect(restored, baseline, {metadataPaths: [target]})).reason, /nonordinary/);
      }
    }
  } finally { f.close(); }
});

test('receiving metadata requires the supplied baseline to be the actual merge base', async () => {
  const f = fixture(); try {
    const candidate = f.commit({...f.files, [METADATA[0]]: body('updated')}, f.baseline);
    const baseline = f.commit({...f.files, 'unrelated-baseline.txt': body('baseline-only change')}, f.baseline);
    assert.equal(f.git(['merge-base', baseline, candidate]), f.baseline);
    const result = await f.inspect(candidate, baseline, {metadataPaths: [METADATA[0]]});
    assert.equal(result.status, 'full-check-required');
    assert.match(result.reason, /outside-receiving-metadata-scope/);
  } finally { f.close(); }
});

test('receiving metadata cannot exempt either filename when it is a selected current or historical route', async () => {
  const f = fixture(); try {
    for (const target of METADATA) {
      for (const route of ['source-map', 'native-manifest', 'historical-source', 'fallback-source', 'historical-receipt', 'fallback-receipt']) {
        const files = {...f.files}, selection = JSON.parse(files['data/ownership-selection.json']);
        const other = METADATA.find(name => name !== target);
        if (route === 'source-map') {
          files[target] = files[selection.selected_geography.path];
          selection.selected_geography = {...selection.selected_geography, path: target};
        } else if (route === 'native-manifest') {
          files[target] = files[selection.manifest_path];
          selection.manifest_path = target;
        } else {
          files[target] = body('opaque consumed historical leaf');
          const original = f.commit(files, f.baseline);
          const commit = route.startsWith('fallback-') ? 'd'.repeat(40) : original;
          if (route.endsWith('-source')) {
            const name = selection.selected_geography.path, bank = JSON.parse(files[name]);
            bank.unchanged_files.push({commit, path: target, mode: '100644',
              git_blob_oid: f.git(['hash-object', '--stdin'], files[target]), bytes: files[target].length, sha256: sha(files[target])});
            files[name] = body(bank);
            selection.selected_geography = {...selection.selected_geography, bytes: files[name].length, sha256: sha(files[name])};
          } else {
            const name = 'scripts/native-ownership/verified-candidates.json', verified = JSON.parse(files[name]);
            verified.candidates[selection.sha256] = {...verified.candidates[selection.sha256], commit, path: target};
            files[name] = body(verified);
          }
        }
        files['data/ownership-selection.json'] = body(selection);
        const baseline = f.commit(files, f.baseline);
        // First prove this exact relocated route is supported, so malformed
        // fixture routing cannot make the changed-input rejection vacuous.
        const control = f.commit({...files, [other]: body('inert metadata control')}, baseline);
        const accepted = await f.inspect(control, baseline, {metadataPaths: [other]});
        assert.equal(accepted.status, 'unchanged-selected-inputs', `${target} ${route}: ${accepted.reason}`);
        assert(accepted.current_and_absent_alternatives.some(p => p.path === target && !p.absent));
        const candidate = f.commit({...files, [target]: body('changed consumed scientific route')}, baseline);
        const result = await f.inspect(candidate, baseline, {metadataPaths: [target]});
        assert.equal(result.status, 'full-check-required', `${target} ${route}`);
        assert.equal(result.reason, 'changed-current-input:' + target);
      }
    }
  } finally { f.close(); }
});


test('production collector rejects a moving-main policy label different from its executing checkout', async () => {
  const f = fixture(); try {
    f.git(['update-ref', 'HEAD', f.baseline]);
    const accepted = await inspectExecutingSelectedGeography({repo: f.directory, baseline: f.baseline, candidate: f.candidate});
    assert.equal(accepted.status, 'unchanged-selected-inputs', accepted.reason);
    const movedMain = f.commit({...f.files, 'reviewed-main-note': body('later main')}, f.baseline);
    const rejected = await inspectExecutingSelectedGeography({repo: f.directory, baseline: f.baseline, candidate: f.candidate, trusted: movedMain});
    assert.equal(rejected.status, 'full-check-required');
    assert.equal(rejected.reason, 'executing-checkout-mismatch');
  } finally { f.close(); }
});


test('routing distinguishes literal historical rebind profiles from the expanded current executing closure',async()=>{
 assert.strictEqual(REBIND_CODE,CURRENT_REBIND_CODE);
 for(const rebindCode of [LEGACY_CURRENT_REBIND_CODE,CURRENT_REBIND_CODE]){
  const f=fixture({rebindCode,historicalMetadataAbsent:rebindCode===LEGACY_CURRENT_REBIND_CODE});
  try{const result=await f.inspect(f.candidate,f.baseline);assert.equal(result.status,'unchanged-selected-inputs',result.reason);
   const requestPins=result.immutable_descriptors.filter(pin=>pin.path===P+'rebind-request.json');assert.ok(requestPins.length>0);
   for(const name of ['scripts/selected-reference-metadata.mjs','src/reference-metadata.js'])assert(result.current_and_absent_alternatives.some(pin=>pin.path===name),name);
  }finally{f.close();}
 }
 for(const rebindCode of [CURRENT_REBIND_CODE.slice(0,-1),[...LEGACY_CURRENT_REBIND_CODE,'foreign.mjs'],[...CURRENT_REBIND_CODE].reverse()]){
  const f=fixture({rebindCode});try{const result=await f.inspect(f.candidate,f.baseline);assert.equal(result.status,'full-check-required');assert.match(result.reason,/Foreign\/incomplete current rebind execution code profile/);}finally{f.close();}
 }
 const falseCurrent=fixture({rebindCode:CURRENT_REBIND_CODE,historicalMetadataAbsent:true});
 try{const result=await falseCurrent.inspect(falseCurrent.candidate,falseCurrent.baseline);assert.equal(result.status,'full-check-required');assert.match(result.reason,/absent|missing|unavailable/);}finally{falseCurrent.close();}
});

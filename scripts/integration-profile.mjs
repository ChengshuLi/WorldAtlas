// Only these coordination controls have an audited focused test inventory.
// Unknown docs/scripts/workflows retain full regression, including rename origins.
export const COORDINATION_PATHS = new Set([
  'docs/WORKER_COORDINATION.md', 'docs/PREMERGE_EVIDENCE_REVIEW.md',
  'scripts/issue-claim-contract.mjs', 'scripts/issue-lease.mjs', 'scripts/run-issue-claim.mjs',
  'scripts/worker-result.mjs', 'scripts/check-handoff-scope.mjs', 'scripts/check-linked-github-issue.mjs',
  'scripts/evidence-quality.mjs', 'scripts/evidence-policy.mjs', 'scripts/premerge-evidence.mjs',
  'scripts/check-pr-evidence.mjs', 'scripts/merge-integration.mjs', 'scripts/integration-proof.mjs',
  'scripts/integration-profile.mjs', 'scripts/check-integration-profile.mjs',
  'scripts/classify-deployment-budget.mjs',
  '.github/workflows/deployment-budget.yml', 'test/deployment-budget-scope.test.mjs',
  // Test-runner changes require full regression to validate the real inventory.
  'scripts/run-worker-merge.mjs', 'scripts/queue-pr-merge.mjs', 'scripts/merge-queue-client.mjs',
  '.github/workflows/handoff-scope.yml',
  '.github/workflows/merge-integration-checks.yml', '.github/workflows/worker-merge.yml',
  '.github/evidence-policy.json',
  ...['handoff-scope','issue-claims','worker-result','regional-research-gate','geography-worker-lane',
    'evidence-quality','premerge-evidence','trusted-workflow-checkouts','merge-integration',
    'merge-integration-client','merge-integration-entrypoint','integration-proof'].map(name=>`test/${name}.test.mjs`)
]);
export function integrationProfile(branch, files, reservation = {}) {
  const names = files.flatMap(file => [file.filename, ...(file.previous_filename ? [file.previous_filename] : [])]);
  if (!names.length) return 'full';
  if (branch.startsWith('geography/') && Array.isArray(reservation.owned_paths) &&
      names.every(name => reservation.owned_paths.some(prefix => name.startsWith(prefix)))) return 'evidence';
  const job = branch.split('/').slice(1).join('/');
  if (branch.startsWith('research/') && names.every(name => name.startsWith(`research/campaigns/${job}/`))) return 'evidence';
  if (branch.startsWith('engineering/')) {
    const legacy = name => COORDINATION_PATHS.has(name) || (name.startsWith('docs/') && /\.(md|txt)$/.test(name)) ||
      name.startsWith(`coordination/engineering/${job}/`) || name === `coordination/engineering/${job}.json`;
    if (names.every(legacy)) return 'evidence';
    // A verified retained scope permits new packets, not edits to its existing
    // methods. Keep the original branch-matched policy above unchanged.
    const scopes = reservation.mode === 'engineering' && Array.isArray(reservation.owned_paths)
      ? reservation.owned_paths.filter(prefix => typeof prefix === 'string' &&
        /^coordination\/engineering\/[^/]+\/(?:[^/]+\/)*$/.test(prefix) &&
        prefix.slice(0, -1).split('/').every(part => /^[a-zA-Z0-9_.-]+$/.test(part) && part !== '.' && part !== '..')) : [];
    if (!scopes.length) return 'full';
    let definition;
    try { definition = loadPackageInputs(); } catch { return 'full'; }
    const packet = name => /\.(?:md|txt|json|jsonl|jsonl\.gz|log|stdout|stderr|mjs|py|csv|tsv)$/.test(name) &&
      !/^(?:package(?:-lock)?\.json|npm-shrinkwrap\.json|(?:requirements|constraints)(?:[.-].*)?\.txt|pyproject\.toml|setup\.(?:py|cfg)|__init__\.py|(?:site|user)customize\.py|(?:js|ts)config(?:\.[^.]+)?\.json|import[-_.]?map\.json)$/i.test(name.split('/').at(-1));
    if (files.every(file => {
      if ([file.filename, ...(file.previous_filename ? [file.previous_filename] : [])].every(legacy)) return true;
      if (file.previous_filename || !safePackagePath(file.filename) || file.filename.split('/').some(part => part.startsWith('.')) ||
          file.mode !== undefined && !['100644', '100755'].includes(file.mode) || packagePathRequired(file.filename, definition)) return false;
      return scopes.some(prefix => file.filename.startsWith(prefix) &&
        (file.status === 'added' && packet(file.filename) || file.status === 'modified' && file.filename === prefix + 'evidence-quality.json'));
    })) return 'evidence';
  }
  return 'full';
}

import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual as same} from 'node:util';
import {validatePackageInputs, loadPackageInputs, packagePathRequired, safePackagePath, PACKAGE_INPUT_FILE} from './package-inputs.mjs';
const SELECTION = 'data/ownership-selection.json';
const ADMINISTRATIVE_REGISTRY = 'coordination/engineering/melanesia363-additive-delivery-20261010/accepted-administrative-handoffs.json';
const SOURCE_CORPUS = 'coordination/engineering/original-geography-source-corpus-20261006/';
export const SELECTED_SMOKE = 'scripts/selected-delivery-smoke.mjs';
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const safe = value => typeof value === 'string' && /^[A-Za-z0-9_./-]+$/.test(value) &&
  value.split('/').every(part => part && part !== '.' && part !== '..' && !part.startsWith('.'));
const ordinary = row => row?.type === 'blob' && row.mode === '100644' &&
  /^[a-f0-9]{40}$/.test(row.sha ?? '') && Number.isSafeInteger(row.size) && row.size >= 0 && row.size <= 32 * 1024 * 1024;
const needSelected = (value, message) => { if (!value) throw Error('Selected-data: ' + message); };
const keys = (value, names) => value && typeof value === 'object' && !Array.isArray(value) &&
  same(Object.keys(value).sort(), [...names].sort());
const text = value => typeof value === 'string' && value.length > 0 && value.length < 1024;

// Expectations are reviewed source-side data. Require the WHOLE selected roster,
// including zero-cell members. Held/rejected rows remain in the ledger but
// are not rendered selections; a self-consistent active subset cannot select fewer tests.
export function validateSelectedExpectations(expected, ledger, ledgerHash, previousLedger) {
  needSelected(keys(expected, ['version','selected_ledger_sha256','cumulative_native_cells','cohorts']) &&
    expected.version === 1 && expected.selected_ledger_sha256 === ledgerHash && hash(ledgerHash) &&
    Number.isSafeInteger(expected.cumulative_native_cells) && expected.cumulative_native_cells >= 0 &&
    Array.isArray(expected.cohorts) && expected.cohorts.length > 0 && expected.cohorts.length <= 1024,
    'invalid reviewed expectations');
  needSelected(ledger?.version === 2 && ledger.kind === 'native-additive-repair-ledger-v2' &&
    Array.isArray(ledger.rows) && ledger.rows.length > 0 && ledger.rows.length <= 10000, 'invalid selected ledger');
  const actual = new Map(), allRows = new Map(), members = new Map(), batches = new Set();
  let cells = 0;
  for (const row of ledger.rows) {
    needSelected(text(row.component_id) && !allRows.has(row.component_id), 'duplicate/invalid ledger member');
    allRows.set(row.component_id, row);
    if (!['assigned','zero-cell'].includes(row.disposition)) {
      needSelected(['awaiting-evidence','rejected'].includes(row.disposition) &&
        (row.native_cells === undefined || row.native_cells === 0) && hash(row.authority_sha256) && hash(row.rule_sha256),
        'unsupported inactive ledger member');
      continue;
    }
    needSelected(Number.isSafeInteger(row.native_cells) && row.native_cells >= 0, 'invalid active native cells');
    actual.set(row.component_id, row); cells += row.native_cells;
  }
  needSelected(Number.isSafeInteger(cells) && cells === expected.cumulative_native_cells, 'native cell expectation differs');
  for (const cohort of expected.cohorts) {
    needSelected(keys(cohort, ['original_batch_id','component_ids','members']) && text(cohort.original_batch_id) &&
      !batches.has(cohort.original_batch_id) && Array.isArray(cohort.component_ids) && cohort.component_ids.length > 0 &&
      Array.isArray(cohort.members) && same([...cohort.component_ids].sort(), cohort.members.map(m => m.component_id).sort()),
      'invalid complete cohort roster');
    batches.add(cohort.original_batch_id);
    for (const member of cohort.members) {
      const row = actual.get(member.component_id);
      needSelected(keys(member, ['component_id','target_id','disposition','geometry_sha256']) && row &&
        !members.has(member.component_id) && text(member.target_id) &&
        ['assigned','zero-cell'].includes(member.disposition) && hash(member.geometry_sha256) &&
        ['target_id','disposition','geometry_sha256'].every(key => row[key] === member[key]), 'member differs from selected ledger');
      members.set(member.component_id, member);
    }
  }
  needSelected(members.size === actual.size && actual.size > 0, 'expectations omit selected members');
  if (previousLedger) {
    needSelected(Array.isArray(previousLedger.rows), 'missing previous ledger roster');
    for (const old of previousLedger.rows.filter(row => ['awaiting-evidence','rejected'].includes(row.disposition)))
      needSelected(same(allRows.get(old.component_id), old), 'previous held/rejected row changed or disappeared');
  }
  return expected;
}

// Fast prefilter avoids any extra tree/blob requests for ordinary code PRs.
export function selectedDataCandidate(branch, files) {
  const owned = `coordination/engineering/${branch.slice('engineering/'.length)}/`;
  return branch.startsWith('engineering/') && files.length > 1 && files.length <= 1024 &&
    files.some(file => file.filename === SELECTION && file.status === 'modified') &&
    files.every(file => !file.previous_filename && ([SELECTION, PACKAGE_INPUT_FILE, ADMINISTRATIVE_REGISTRY].includes(file.filename)
      ? file.status === 'modified' : file.status === 'added' && file.filename.startsWith(owned) && safe(file.filename) &&
        /\.(?:json|jsonl\.gz|json\.gz|log)$/.test(file.filename) &&
        !/(?:^|\/)(?:package(?:-lock)?|tsconfig|jsconfig|binding|deno|composer)\.json$/.test(file.filename)));
}
export async function integrationTree(api, repo, commit) {
  const object = await api(`/repos/${repo}/git/commits/${commit}`);
  const result = await api(`/repos/${repo}/git/trees/${object.tree.sha}?recursive=1`);
  needSelected(!result.truncated && Array.isArray(result.tree), 'incomplete tree inventory');
  return {object, entries: new Map(result.tree.map(row => [row.path, row]))};
}

// This is structural eligibility, not another scientific validator. Walk only
// fixed reader roles, stop at unchanged authorities, and never follow arbitrary
// input/config/code pin objects. Existing package/readback/geography do the full
// source, method, decoded-body, current-neighbor and no-loss validation.
export async function selectedDataSelection({api, repo, branch, files, baseline, authored, base, head}) {
  if (!selectedDataCandidate(branch, files)) return null;
  try {
    baseline ??= await integrationTree(api, repo, base);
    authored ??= await integrationTree(api, repo, head);
    const approved = baseline.entries.get(SELECTED_SMOKE), candidate = authored.entries.get(SELECTED_SMOKE);
    needSelected(ordinary(approved) && approved.size > 0 && approved.sha === candidate?.sha && candidate.mode === approved.mode,
      'generic smoke is not accepted unchanged on baseline');
    const added = new Set(files.filter(file => file.status === 'added').map(file => file.filename));
    needSelected(files.every(file => ordinary(authored.entries.get(file.filename))) &&
      [...added].every(name => !baseline.entries.has(name)), 'nonordinary or overwritten data');
    const expectedPaths = [...added].filter(name => name.endsWith('/selected-delivery-expectations.json'));
    needSelected(expectedPaths.length === 1, 'one reviewed expectations file required');
    const cache = new Map(); let readBytes = 0;
    const read = async (name, tree = authored) => {
      const row = tree.entries.get(name);
      needSelected(ordinary(row), 'missing ordinary role ' + name);
      if (!cache.has(row.sha)) {
        needSelected(readBytes + row.size <= 16 * 1024 * 1024 && cache.size < 256, 'metadata read budget exceeded');
        readBytes += row.size;
        const blob = await api(`/repos/${repo}/git/blobs/${row.sha}`);
        needSelected(blob.encoding === 'base64' && typeof blob.content === 'string', 'missing blob bytes');
        const bytes = Buffer.from(blob.content, 'base64');
        needSelected(bytes.length === row.size && createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex') === row.sha,
          'blob identity differs');
        cache.set(row.sha, bytes);
      }
      return cache.get(row.sha);
    };
    const json = async (name, tree) => JSON.parse(await read(name, tree));
    let packageAdditions = [];
    if (files.some(file => file.filename === PACKAGE_INPUT_FILE)) {
      const {inputs: before, ...oldPolicy} = validatePackageInputs(await json(PACKAGE_INPUT_FILE, baseline));
      const {inputs: after, ...policy} = validatePackageInputs(await json(PACKAGE_INPUT_FILE));
      needSelected(same(oldPolicy, policy) && after.length >= before.length && same(before, after.slice(0, before.length)),
        'package policy is not append-only');
      packageAdditions = after.slice(before.length);
    }
    const registryChanged = files.some(file => file.filename === ADMINISTRATIVE_REGISTRY);
    const sourceExtension = registryChanged || packageAdditions.some(name => baseline.entries.has(name));
    const oldSelection = await json(SELECTION, baseline), selection = await json(SELECTION);
    const {additive_release: oldHook, ...oldBase} = oldSelection, {additive_release: hook, ...newBase} = selection;
    needSelected(selection.version === 1 && selection.method === 'native-linear-evenodd-first-owner-v1' &&
      selection.artifact_consumption && same(oldBase, newBase) && !same(oldHook, hook), 'selection changes method/base authority');
    const reachable = new Set(), identities = new Map();
    const pin = value => {
      needSelected(value && safe(value.path) && /\.(?:json|jsonl\.gz|json\.gz|log)$/.test(value.path) &&
        hash(value.sha256) && Number.isSafeInteger(value.bytes) && value.bytes >= 0, 'invalid inert role pin');
      const row = authored.entries.get(value.path);
      needSelected(ordinary(row) && row.size === value.bytes &&
        (value.mode === undefined || value.mode === row.mode) &&
        (value.git_blob_oid === undefined || value.git_blob_oid === row.sha), 'role differs from candidate tree');
      // Full pins are required for leaves whose bytes are not read here.
      needSelected((value.git_blob_oid && value.mode === '100644' && /^[a-f0-9]{40}$/.test(value.commit ?? '')) || value === hook, 'role lacks exact tree identity');
      const identity = [value.bytes, value.sha256, row.sha];
      needSelected(!identities.has(value.path) || same(identities.get(value.path), identity), 'conflicting role identities');
      identities.set(value.path, identity);
      reachable.add(value.path); return value.path;
    };
    const pinnedJSON = async value => {
      const name = pin(value), bytes = await read(name);
      needSelected(sha256(bytes) === value.sha256, 'role content hash differs');
      return JSON.parse(bytes);
    };
    // Only the two declared exceptions need this SOURCE inventory. Ordinary
    // selected deliveries keep their existing small fixed-role walk.
    const sourceDeclarations = new Set(), usedRegistrations = new Set(), acceptedTrees = new Map();
    let administrative;
    const strings = value => Array.isArray(value) && value.length > 0 && value.length <= 4096 &&
      value.every(id => typeof id === 'string' && id.length > 0) && new Set(value).size === value.length;
    const oid = value => value?.git_blob_oid ?? value?.blob;
    const content = value => [value?.path, value?.mode, oid(value), value?.bytes, value?.sha256];
    const unique = (rows, predicate, label) => {
      needSelected(Array.isArray(rows), 'missing ' + label);
      const matches = rows.filter(predicate);needSelected(matches.length === 1, 'ambiguous ' + label);return matches[0];
    };
    const registryEntries = value => {
      needSelected(keys(value, ['version','kind','entries']) && value.version === 1 &&
        value.kind === 'accepted-administrative-handoffs-v1' && Array.isArray(value.entries) && value.entries.length <= 512,
        'unsupported administrative registry');
      const ids = new Set(), paths = new Set(), components = new Set(), batches = new Set();
      for (const entry of value.entries) {
        const execution = entry.format === 'source-native-execution-cohort-v2';
        needSelected(keys(entry, ['accepted_source_commit','cohort_ids','format','id','source','target_ids',
          ...(execution ? [] : ['original_batch_id','original_component_count'])]) &&
          (execution || entry.format === 'source-native-handoff-v1') && typeof entry.id === 'string' && entry.id &&
          /^[a-f0-9]{40}$/.test(entry.accepted_source_commit ?? '') &&
          keys(entry.source, ['blob','bytes','mode','path','sha256']) && safe(entry.source.path) &&
          /^research\/geography\/[^/]+\/.+\.json$/.test(entry.source.path) && entry.source.mode === '100644' &&
          /^[a-f0-9]{40}$/.test(entry.source.blob ?? '') && hash(entry.source.sha256) &&
          Number.isSafeInteger(entry.source.bytes) && entry.source.bytes > 0 && entry.source.bytes <= 32 * 1024 * 1024 &&
          strings(entry.cohort_ids) && strings(entry.target_ids) &&
          (execution || typeof entry.original_batch_id === 'string' && entry.original_batch_id &&
            entry.original_component_count === entry.cohort_ids.length), 'unsupported administrative entry');
        needSelected(!ids.has(entry.id) && !paths.has(entry.source.path) && entry.cohort_ids.every(id => !components.has(id)) &&
          (execution || !batches.has(entry.original_batch_id)), 'duplicate administrative registration');
        ids.add(entry.id);paths.add(entry.source.path);entry.cohort_ids.forEach(id => components.add(id));
        if (!execution) batches.add(entry.original_batch_id);
      }
      return value.entries;
    };
    const acceptedSource = async value => {
      const current = authored.entries.get(value.path), previous = baseline.entries.get(value.path);
      needSelected(safe(value.path) && ordinary(current) && ordinary(previous) && current.sha === previous.sha &&
        current.size === value.bytes && previous.size === current.size && (!oid(value) || oid(value) === current.sha) &&
        (value.mode === undefined || value.mode === '100644') && hash(value.sha256), 'SOURCE data is not unchanged accepted input');
      const bytes = await read(value.path);
      needSelected(sha256(bytes) === value.sha256, 'accepted SOURCE bytes differ');
      sourceDeclarations.add(value.path);return bytes;
    };
    const sourceRoles = async authority => {
      const issued = await pinnedJSON(authority.original_pins.source_request), facts = await pinnedJSON(authority.original_pins.source_facts);
      const rule = issued.source_rule;
      needSelected(issued.version === 1 && issued.operation === 'retained-land-source-premises-v1' &&
        rule?.profile === 'retained-consumed-administrative-source' && rule.version === 1 &&
        rule.registry_path === ADMINISTRATIVE_REGISTRY && rule.geometry_scope === 'full-component' &&
        Array.isArray(rule.inputs) && rule.inputs.length <= 1024 && Array.isArray(issued.baseline?.pins) &&
        same(content(facts.request), content(authority.original_pins.source_request)) && same(facts.source_rule, rule) &&
        same(facts.input_descriptors, [issued.report, ...rule.inputs, ...issued.baseline.pins]), 'SOURCE request/facts join differs');
      administrative ??= registryEntries(await json(ADMINISTRATIVE_REGISTRY));
      const registryPin = unique(rule.inputs, row => row.path === ADMINISTRATIVE_REGISTRY, 'SOURCE registry input');
      await pinnedJSON({...registryPin, git_blob_oid: oid(registryPin)});
      const source = unique(rule.inputs, row => row.path === rule.cases_path, 'registered SOURCE input');
      const entry = unique(administrative, row => same(content(row.source), content(source)), 'registered SOURCE');
      needSelected(source.commit === entry.accepted_source_commit && rule.outcomes_path === source.path &&
        same(rule.cohort_ids, entry.cohort_ids), 'SOURCE registration scope differs');
      const baselineCommit = baseline.object?.sha ?? base;
      needSelected(/^[a-f0-9]{40}$/.test(baselineCommit ?? ''), 'missing accepted baseline identity');
      if (!acceptedTrees.has(source.commit)) {
        needSelected(acceptedTrees.size < 32, 'accepted source vintage budget exceeded');
        const comparison = await api(`/repos/${repo}/compare/${source.commit}...${baselineCommit}`);
        needSelected(['ahead','identical'].includes(comparison?.status), 'SOURCE commit is not accepted on baseline');
        acceptedTrees.set(source.commit, await integrationTree(api, repo, source.commit));
      }
      const original = acceptedTrees.get(source.commit).entries.get(source.path);
      needSelected(ordinary(original) && original.sha === oid(source) && original.size === source.bytes, 'accepted SOURCE commit pin differs');
      const handoff = JSON.parse(await acceptedSource(source)), cases = handoff.candidate_source_native_bindings;
      needSelected(Array.isArray(cases) && same(cases.map(row => row.component_id), entry.cohort_ids) &&
        same(handoff.scopeIds, entry.cohort_ids) && Array.isArray(handoff.unknowns) &&
        same([...new Set(cases.map(row => row.retained_payload?.target_stable_location_id))].sort(), [...entry.target_ids].sort()),
        'registered SOURCE subjects differ');
      if (entry.format === 'source-native-handoff-v1') {
        needSelected(handoff.original_batch_id === entry.original_batch_id &&
          handoff.original_batch_component_count === entry.original_component_count, 'original SOURCE batch differs');
      } else {
        const mapping = handoff.original_gap_membership, index = mapping?.index;
        needSelected(handoff.execution_cohort_id === entry.id && keys(mapping, ['version','index','members']) && mapping.version === 1 &&
          keys(index, ['blob','bytes','commit','mode','path','sha256']) && safe(index.path) && index.mode === '100644' &&
          /^[a-f0-9]{40}$/.test(index.commit ?? '') && /^[a-f0-9]{40}$/.test(index.blob ?? '') && hash(index.sha256) &&
          Number.isSafeInteger(index.bytes) && index.bytes > 0 && Array.isArray(mapping.members) &&
          same(mapping.members.map(row => row.component_id), entry.cohort_ids) && mapping.members.every(row =>
            keys(row, ['component_id','original_batch_id','original_family_id']) &&
            Object.values(row).every(value => typeof value === 'string' && value)), 'execution cohort original membership differs');
      }
      usedRegistrations.add(entry.id);
      needSelected(rule.source_catalogue_path === SOURCE_CORPUS + 'catalogue.json', 'unknown SOURCE catalogue');
      const cataloguePin = unique(rule.inputs, row => row.path === rule.source_catalogue_path, 'SOURCE catalogue');
      const catalogue = JSON.parse(await acceptedSource(cataloguePin));
      needSelected(Array.isArray(catalogue.products) && Array.isArray(rule.administrative_products) &&
        rule.administrative_products.length > 0 && rule.administrative_products.length <= 1024, 'missing administrative products');
      const fields = ['bytes','sha256','uncompressed_bytes','uncompressed_sha256'];
      for (const product of rule.administrative_products) {
        needSelected(safe(product.path) && product.path.startsWith(SOURCE_CORPUS + 'payloads/') && product.path.endsWith('.bin.gz'),
          'unknown administrative payload role');
        const input = unique(rule.inputs, row => row.path === product.path, 'administrative input');
        const part = unique(catalogue.products.flatMap(row => row.parts ?? []), row => row.path === product.path, 'catalogue part');
        needSelected(same(content(input), content(product)) && fields.every(key => product[key] === part[key] && product[key] === input[key]) &&
          hash(product.uncompressed_sha256) && Number.isSafeInteger(product.uncompressed_bytes) && product.uncompressed_bytes > 0,
          'administrative product identities differ');
        await acceptedSource(product);
      }
      const report = JSON.parse(await acceptedSource(issued.report));
      // The report binds a role, but cannot itself become a newly declared input.
      sourceDeclarations.delete(issued.report.path);
      needSelected(Array.isArray(rule.original_products) && rule.original_products.length > 0 && rule.original_products.length <= 1024,
        'missing original physical roles');
      const campaign = source.path.split('/').slice(0, 3).join('/') + '/';
      for (const locator of rule.original_products) {
        const name = locator.original_product_path;
        needSelected(/^(?:components|sources)-\d{3}\.jsonl\.gz$/.test(name ?? ''), 'unknown original physical role');
        const input = unique(rule.inputs, row => row.path === locator.path && row.original_product_path === name, 'original physical input');
        const product = unique(report.products, row => row.path === name, 'original report product');
        const restoration = unique(handoff.physical_restoration?.restorations, row => row.path === name, 'physical restoration');
        needSelected(input.kind === 'original-report-product' && input.report_sha256 === issued.report.sha256 &&
          fields.every(key => input[key] === product[key]) && restoration.whole_original_bytes === product.bytes &&
          restoration.whole_original_sha256 === product.sha256 && restoration.decoded_bytes === product.uncompressed_bytes &&
          restoration.decoded_sha256 === product.uncompressed_sha256, 'physical restoration identities differ');
        const retained = unique(handoff.consumed_inputs, row => safe(row.path) && row.path.startsWith(campaign) &&
          row.path.endsWith('/' + name) && row.bytes === product.bytes && row.sha256 === product.sha256, 'retained physical Git input');
        await acceptedSource(retained);
      }
    };
    const sidecar = await pinnedJSON(hook);
    needSelected(sidecar.version === 2 && sidecar.kind === 'retained-native-additive-selection-v2' &&
      keys(sidecar, ['version','kind','base_selection','runtime_envelope','authority_registry','logical_asset_map']) &&
      same(sidecar.base_selection, newBase) && keys(sidecar.logical_asset_map, ['base_manifest','ledger','owner_roster','patch']),
      'unsupported selected sidecar');
    pin(sidecar.runtime_envelope);
    for (const value of Object.values(sidecar.logical_asset_map)) pin(value);
    const ledger = await pinnedJSON(sidecar.logical_asset_map.ledger);
    const registry = await pinnedJSON(sidecar.authority_registry);
    needSelected(keys(registry, ['version','kind','entries']) && registry.version === 1 &&
      Array.isArray(registry.entries) && registry.entries.length > 0 && registry.entries.length <= 1024,
      'missing authority registry');
    needSelected(oldHook && safe(oldHook.path), 'missing preceding selected release');
    const oldSideBytes = await read(oldHook.path, baseline);
    needSelected(oldSideBytes.length === oldHook.bytes && sha256(oldSideBytes) === oldHook.sha256, 'preceding sidecar differs');
    const oldSide = JSON.parse(oldSideBytes), oldRegistryPin = oldSide.authority_registry;
    const oldLedgerPin = oldSide.logical_asset_map?.ledger, oldLedgerBytes = await read(oldLedgerPin?.path, baseline);
    needSelected(oldLedgerBytes.length === oldLedgerPin.bytes && sha256(oldLedgerBytes) === oldLedgerPin.sha256, 'preceding ledger differs');
    validateSelectedExpectations(await json(expectedPaths[0]), ledger, sidecar.logical_asset_map.ledger.sha256, JSON.parse(oldLedgerBytes));
    const oldRegistryBytes = await read(oldRegistryPin.path, baseline);
    needSelected(oldRegistryBytes.length === oldRegistryPin.bytes && sha256(oldRegistryBytes) === oldRegistryPin.sha256, 'preceding registry differs');
    const oldRegistry = JSON.parse(oldRegistryBytes);
    needSelected(Array.isArray(oldRegistry.entries) && oldRegistry.entries.every(old =>
      registry.entries.filter(entry => same(entry, old)).length === 1), 'existing authority changed or disappeared');
    const operating = async (value, current = false) => {
      pin(value);
      if (!added.has(value.path)) return;
      const object = await pinnedJSON(value);
      needSelected(keys(object.execution_custody, ['code_source','terminal','stderr','stdout','issued_plan']), 'missing operating custody');
      for (const leaf of Object.values(object.execution_custody)) pin(leaf);
      if (!current) return;
      const plan = await pinnedJSON(object.execution_custody.issued_plan);
      needSelected(Array.isArray(plan.original_inputs) && plan.original_inputs.length === 2 &&
        ['path','mode','bytes','sha256','git_blob_oid'].every(key => plan.original_inputs[0]?.[key] === sidecar.authority_registry[key]) &&
        plan.original_inputs[1].path?.endsWith('/composed-original-ledger.json'), 'unsupported original data inputs');
      pin(plan.original_inputs[1]);
    };
    for (const entry of registry.entries) {
      needSelected(keys(entry, ['authority_sha256','policy_id','policy_version','rule_preimage','rule_sha256','source_authority']), 'foreign registry fields');
      pin(entry.rule_preimage); pin(entry.source_authority);
      if (!added.has(entry.source_authority.path)) continue;
      const authority = await pinnedJSON(entry.source_authority);
      needSelected(authority.version === 1 && authority.kind === 'original-issued-rule-source-custody-v1' &&
        keys(authority.original_pins, ['ledger','native_facts','native_manifest','native_request','source_facts','source_request']),
        'unsupported source authority');
      for (const value of Object.values(authority.original_pins)) pin(value);
      const proof = authority.native_proof;
      pin(proof.publication); pin(proof.inventory); pin(proof.operating);
      needSelected(Array.isArray(proof.assets) && proof.assets.length > 0 && proof.assets.length <= 32, 'missing native asset roles');
      for (const asset of proof.assets) {
        needSelected(/\/(?:base-native-manifest|ledger[^/]*|patch[^/]*|features|owners[^/]*|release-envelope|owner-window|virtual-owner-window)\.json(?:\.gz)?$/.test(asset.path),
          'unknown native asset role');
        pin(asset);
      }
      const aliases = authority.source_output_aliases ?? [];
      needSelected(Array.isArray(aliases) && aliases.length <= 3, 'invalid source output aliases');
      for (const alias of aliases) {
        needSelected(/\/(?:facts\.json|publication\.json|inventory\.jsonl\.gz)$/.test(alias.published?.path ?? '') &&
          alias.original?.bytes === alias.published.bytes && alias.original?.sha256 === alias.published.sha256,
          'source alias rewrites original data');
        pin(alias.published);
      }
      const nativeRequest = await pinnedJSON(authority.original_pins.native_request), spec = nativeRequest.additive;
      if (sourceExtension) await sourceRoles(authority);
      needSelected(Array.isArray(spec?.inputs) && spec.inputs.length <= 1024, 'missing source role inputs');
      for (const role of ['publication_path','inventory_path','operating_path']) {
        const matches = spec.inputs.filter(value => value.path === spec[role]);
        needSelected(matches.length === 1, 'ambiguous original source role');
        const mapped = aliases.filter(alias => alias.original.path === matches[0].path);
        needSelected(mapped.length <= 1, 'duplicate source alias');
        const value = mapped[0]?.published ?? matches[0];
        pin({...value, git_blob_oid: value.git_blob_oid ?? value.blob});
      }
    }
    const certificate = await pinnedJSON(ledger.current_rebind);
    needSelected(certificate.version === 1 && certificate.kind === 'qualified-native-additive-current-bank-rebind-v1',
      'unsupported current rebind');
    for (const role of ['request','facts','publication','result']) pin(certificate[role]);
    await operating(certificate.operating, true);
    const manifest = `coordination/engineering/${branch.slice('engineering/'.length)}/evidence-quality.json`;
    for (const name of added) {
      if (reachable.has(name) || name === expectedPaths[0] || name === manifest) continue;
      // Non-consumed supporting evidence cannot become package input. It must
      // still be ordinary inert JSON/text, never a module, configuration or archive.
      if (name.endsWith('.json')) await json(name);
      else {
        needSelected(name.endsWith('.log'), 'unknown opaque evidence type');
        const bytes = await read(name);
        needSelected(bytes.length <= 128 * 1024 && !bytes.includes(0) && Buffer.from(bytes.toString('utf8')).equals(bytes), 'nontext evidence log');
      }
    }
    if (registryChanged) {
      const previous = registryEntries(await json(ADMINISTRATIVE_REGISTRY, baseline));
      needSelected(administrative && administrative.length > previous.length && same(previous, administrative.slice(0, previous.length)) &&
        administrative.slice(previous.length).every(entry => usedRegistrations.has(entry.id)), 'registry is not append-only selected SOURCE data');
    }
    needSelected(packageAdditions.every(name => added.has(name) && reachable.has(name) || sourceDeclarations.has(name)),
      'package change is not append-only exact reachable data');
    return {test_selection: 'selected-data', expectations_path: expectedPaths[0], shards: [0]};
  } catch (error) {
    if (error.planningNeeded) throw error; // Preserve the existing bounded capacity-planning retry.
    return null; // An unavailable/unknown boundary retains the full suite.
  }
}

// Bind the reviewed source-side expectations before calling the actual generic
// emitted-assets smoke. Missing selected/browser assets never become a skip.
export async function selectedDeliverySmoke(expectationsPath) {
  if (typeof expectationsPath !== 'string' || !/^coordination\/engineering\/[A-Za-z0-9_./-]+\/selected-delivery-expectations\.json$/.test(expectationsPath) ||
      expectationsPath.split('/').some(part => !part || part.startsWith('.'))) throw Error('Missing reviewed selected expectations path');
  const read = name => {
    const stat = fs.lstatSync(name);
    if (!stat.isFile() || stat.isSymbolicLink() || stat.size > 32 * 1024 * 1024) throw Error('Nonordinary selected data');
    return fs.readFileSync(name);
  };
  const pinned = pin => {
    if (!pin || typeof pin.path !== 'string' || pin.path.split('/').some(part => !part || part.startsWith('.')) || pin.path.includes('\\'))
      throw Error('Invalid selected data pin');
    const bytes = read(pin.path);
    if (bytes.length !== pin.bytes || createHash('sha256').update(bytes).digest('hex') !== pin.sha256) throw Error('Selected data bytes differ');
    return JSON.parse(bytes);
  };
  const selection = JSON.parse(read('data/ownership-selection.json'));
  if (!selection.artifact_consumption || !selection.additive_release) throw Error('Missing actual selected artifact');
  // Its successful readback was produced by the preceding mandatory build step.
  read('.cache/native-normal-built-output.json');
  const sidecar = pinned(selection.additive_release), ledgerPin = sidecar.logical_asset_map?.ledger;
  validateSelectedExpectations(JSON.parse(read(expectationsPath)), pinned(ledgerPin), ledgerPin.sha256);
  const {runSelectedDeliverySmoke} = await import('./selected-delivery-smoke.mjs');
  return runSelectedDeliverySmoke({root: process.cwd(), emittedDirectory: path.resolve('dist/client'),
    expectationsPath, outputPath: path.resolve('.cache/selected-delivery-smoke.json')});
}

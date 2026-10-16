import {FOCUSED_INTEGRATION_TESTS} from './run-integration-tests.mjs';

// Only these coordination controls have an audited focused test inventory.
// Unknown docs/scripts/workflows retain full regression, including rename origins.
export const COORDINATION_PATHS = new Set([
  // Delivery orchestration is not imported by the atlas builder. Shared native
  // operators and native-preparation-guards remain outside this exact list.
  'scripts/prepare-delivery-handoff.mjs', 'scripts/delivery-handoff-advance.mjs',
  'docs/WORKER_COORDINATION.md', 'docs/PREMERGE_EVIDENCE_REVIEW.md',
  'scripts/issue-claim-contract.mjs', 'scripts/run-issue-claim.mjs',
  'scripts/worker-result.mjs', 'scripts/check-handoff-scope.mjs', 'scripts/check-linked-github-issue.mjs',
  'scripts/evidence-quality.mjs', 'scripts/evidence-policy.mjs', 'scripts/premerge-evidence.mjs',
  'scripts/check-pr-evidence.mjs', 'scripts/merge-integration.mjs', 'scripts/integration-proof.mjs',
  'scripts/geographic-adjudication-api.mjs',
  'scripts/integration-profile.mjs',
  'scripts/classify-deployment-budget.mjs',
  '.github/workflows/deployment-budget.yml',
  // Test-runner changes require full regression to validate the real inventory.
  'scripts/run-worker-merge.mjs',
  '.github/workflows/handoff-scope.yml',
  '.github/workflows/worker-merge.yml',
  '.github/evidence-policy.json'
]);
// Only the actual focused runner inventory may accompany coordination changes.
// A provider filename/status alone cannot establish an ordinary candidate file.
const FOCUSED_TEST_PATHS = new Set(FOCUSED_INTEGRATION_TESTS);
// Callers supply the current linked issue's validated lane and declared scope.
// Candidate metadata is never an ownership source.
function engineeringOwnedScopes(reservation) {
  if (reservation.mode !== 'engineering') return [];
  try {
    // Keep the issue's literal file/directory grants; a restored read role need
    // not grant ownership of its whole original packet. Invalid scopes fail closed.
    return validateEngineeringOwnedPaths(reservation.owned_paths)
      .filter(owned => /^coordination\/engineering\/[^/]+\//.test(owned));
  } catch { return []; }
}
export function integrationProfile(branch, files, reservation = {}, authoredEntries) {
  const names = files.flatMap(file => [file.filename, ...(file.previous_filename ? [file.previous_filename] : [])]);
  if (!names.length) return 'full';
  // Validate each focused test before composing it with the existing route.
  const focused = files.filter(file => [file.filename, file.previous_filename].some(name => FOCUSED_TEST_PATHS.has(name)));
  if (focused.length && !(branch.startsWith('engineering/') && authoredEntries instanceof Map &&
      focused.every(file => FOCUSED_TEST_PATHS.has(file.filename) && file.status === 'modified' &&
        file.previous_filename === undefined && authoredEntries.get(file.filename)?.type === 'blob' &&
        authoredEntries.get(file.filename)?.mode === '100644' &&
        /^[a-f0-9]{40}$/.test(authoredEntries.get(file.filename)?.sha ?? '')))) return 'full';

  if (branch.startsWith('geography/') && Array.isArray(reservation.owned_paths) &&
      names.every(name => reservation.owned_paths.some(prefix => name.startsWith(prefix)))) return 'evidence';
  const job = branch.split('/').slice(1).join('/');
  if (branch.startsWith('research/') && names.every(name => name.startsWith(`research/campaigns/${job}/`))) return 'evidence';
  if (branch.startsWith('engineering/')) {
    const legacy = name => COORDINATION_PATHS.has(name) || FOCUSED_TEST_PATHS.has(name) || (name.startsWith('docs/') && /\.(md|txt)$/.test(name)) ||
      name.startsWith(`coordination/engineering/${job}/`) || name === `coordination/engineering/${job}.json`;
    if (names.every(legacy)) return 'evidence';
    // A verified retained scope permits new packets, not edits to its existing
    // methods. Keep the original branch-matched policy above unchanged.
    // Evidence-only packet routing keeps its existing directory-grant policy.
    // Exact restored files are considered only by the full selected-data walk.
    const scopes = engineeringOwnedScopes(reservation).filter(owned => owned.endsWith('/'));
    if (!scopes.length) return 'full';
    let definition;
    try { definition = loadPackageInputs(); } catch { return 'full'; }
    const packet = name => /\.(?:md|txt|json|jsonl|jsonl\.gz|log|stdout|stderr|mjs|py|csv|tsv)$/.test(name) &&
      !/^(?:package(?:-lock)?\.json|npm-shrinkwrap\.json|(?:requirements|constraints)(?:[.-].*)?\.txt|pyproject\.toml|setup\.(?:py|cfg)|__init__\.py|(?:site|user)customize\.py|(?:js|ts)config(?:\.[^.]+)?\.json|import[-_.]?map\.json)$/i.test(name.split('/').at(-1));
    if (files.every(file => {
      if ([file.filename, ...(file.previous_filename ? [file.previous_filename] : [])].every(legacy)) return true;
      if (file.previous_filename || !safePackagePath(file.filename) || file.filename.split('/').some(part => part.startsWith('.')) ||
          file.mode !== undefined && !['100644', '100755'].includes(file.mode) || packagePathRequired(file.filename, definition)) return false;
      return scopes.some(prefix => containsPackagePath([prefix], file.filename) &&
        (file.status === 'added' && packet(file.filename) || file.status === 'modified' && file.filename === prefix + 'evidence-quality.json'));
    })) return 'evidence';
  }
  return 'full';
}

// Route executable checker/producer changes through actual candidate science.
// This is conservative path classification, not a programme/hash exemption.
// Data-only full checks still use baseline code and authenticated adjudication.
export function candidateGeographyCode(profile, files, testSelection) {
  if (profile !== 'full' || testSelection === 'selected-data') return false;
  return files.some(file => [file.filename, file.previous_filename].filter(Boolean).some(name =>
    /^scripts\/.*\.(?:[cm]?js|[cm]?ts|py|wasm)$/.test(name) ||
    /^src\/(?:native-|effective-footprint\.|ownership-codec\.|regional-import-gate\.|reference-metadata\.)/.test(name) ||
    /^coordination\/engineering\/.*\.(?:[cm]?js|[cm]?ts|py|wasm)$/.test(name) ||
    /(?:^|\/)(?:requirements\.txt|package(?:-lock)?\.json)$/.test(name) ||
    name === 'coordination/engineering/selected-geography-effective-prevention-20261009/supported-programs.json' ||
    /^coordination\/engineering\/additive-native-composition-20261009\/(?:execution-code-paths|mac-execution-runtime-original)\.json$/.test(name)));
}

import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual as same} from 'node:util';
import {gunzipSync} from 'node:zlib';
import {isUtf8} from 'node:buffer';
import {validatePackageInputs, loadPackageInputs, packagePathRequired, safePackagePath, containsPackagePath, PACKAGE_INPUT_FILE} from './package-inputs.mjs';
import {validateEngineeringOwnedPaths} from './check-handoff-scope.mjs';
const SELECTION = 'data/ownership-selection.json';
const CHECKPOINT_LOCATOR = 'data/selected-checkpoint.json';
const ADMINISTRATIVE_REGISTRY = 'coordination/engineering/melanesia363-additive-delivery-20261010/accepted-administrative-handoffs.json';
const SOURCE_CORPUS = 'coordination/engineering/original-geography-source-corpus-20261006/';
export const SELECTED_SMOKE = 'scripts/selected-delivery-smoke.mjs';
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const safe = value => typeof value === 'string' && /^[A-Za-z0-9_./-]+$/.test(value) &&
  value.split('/').every(part => part && part !== '.' && part !== '..' && !part.startsWith('.'));
const ordinary = row => row?.type === 'blob' && row.mode === '100644' &&
  /^[a-f0-9]{40}$/.test(row.sha ?? '') && Number.isSafeInteger(row.size) && row.size >= 0;
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
    Array.isArray(expected.cohorts) && expected.cohorts.length > 0,
    'invalid reviewed expectations');
  needSelected(ledger?.version === 2 && ledger.kind === 'native-additive-repair-ledger-v2' &&
    Array.isArray(ledger.rows) && ledger.rows.length > 0, 'invalid selected ledger');
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
      const nativeOnly=row?.representation==='native-cells', representationHash=nativeOnly?'native_rows_sha256':'geometry_sha256';
      const canonical=value=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'
        ?Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonical(value[key])])):value;
      const actualHash=nativeOnly?sha256(Buffer.from(JSON.stringify(canonical(row.native_rows))+'\n')):row?.geometry_sha256;
      needSelected(keys(member, ['component_id','target_id','disposition',representationHash]) && row &&
        !members.has(member.component_id) && text(member.target_id) &&
        ['assigned','zero-cell'].includes(member.disposition) && hash(member[representationHash]) && actualHash===member[representationHash] &&
        ['target_id','disposition'].every(key => row[key] === member[key]), 'member differs from selected ledger');
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

const branchScope = branch => `coordination/engineering/${branch.slice('engineering/'.length)}/`;
const inScope = (name, scopes) => containsPackagePath(scopes, name);
function supportingText(name, branch, reservation) {
  // Names do not establish consumption. The selected-role/package checks below
  // prove new ordinary text is supporting evidence, regardless of title.
  return inScope(name, [branchScope(branch), ...engineeringOwnedScopes(reservation)]) &&
    /\.(?:md|txt)$/.test(name) &&
    !/\/(?:requirements|constraints)(?:[.-].*)?\.txt$/i.test(name);
}
// A historical source/helper copy is evidence only after the complete fixed
// reader and package exclusions below. Suffixes admit a custody check, never
// execution. Keep loader/configuration names out even in owned packet paths.
function retainedSupportingEvidence(name) {
  return /\.(?:mjs|py|jsonl|xml|lfs-pointer|geojson\.gz|f64le\.gz)$/.test(name) &&
    !/^(?:setup\.py|__init__\.py|(?:site|user)customize\.py)$/i.test(name.split('/').at(-1));
}
function nativeOperandPath(name, branch, reservation) {
  return /^(?:rows|runs)-[0-9]+\.bin\.gz$/.test(name.split('/').at(-1)) &&
    (name === branchScope(branch) + 'native-operands/' + name.split('/').at(-1) ||
      inScope(name, engineeringOwnedScopes(reservation)));
}
// Only the linked issue's validated scientific receipt can be updated metadata.
// Existing independent evidence validation remains mandatory.
function scientificManifest(branch, reservation) {
  const name = reservation.evidence_manifest;
  return reservation.mode === 'engineering' && safe(name) && name.endsWith('/evidence-quality.json') &&
    inScope(name, [branchScope(branch), ...engineeringOwnedScopes(reservation)]) ? name : null;
}
// Fast prefilter avoids any extra tree/blob requests for ordinary code PRs.
export function selectedDataCandidate(branch, files, reservation = {}) {
  const scopes = [branchScope(branch), ...engineeringOwnedScopes(reservation)], manifest = scientificManifest(branch, reservation);
  return branch.startsWith('engineering/') && files.length > 1 &&
    files.some(file => file.filename === SELECTION && file.status === 'modified') &&
    files.every(file => !file.previous_filename && (file.filename === CHECKPOINT_LOCATOR
      ? ['added', 'modified'].includes(file.status) : [SELECTION, PACKAGE_INPUT_FILE, ADMINISTRATIVE_REGISTRY].includes(file.filename)
      ? file.status === 'modified' : file.filename === manifest && file.status === 'modified' || file.status === 'added' && inScope(file.filename, scopes) && safe(file.filename) &&
        (/\.(?:json|jsonl\.gz|json\.gz|log)$/.test(file.filename) || supportingText(file.filename, branch, reservation) ||
          retainedSupportingEvidence(file.filename) || nativeOperandPath(file.filename, branch, reservation) || file.filename.endsWith('/geography-artifact.zip')) &&
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
export async function selectedDataSelection({api, repo, branch, files, baseline, authored, base, head,
  metadataDiagnostics, reservation = {}}) {
  if (!selectedDataCandidate(branch, files, reservation)) return null;
  const diagnostics = metadataDiagnostics ?? {};
  Object.assign(diagnostics, {read_count: 0, read_bytes: 0, retained_bytes: 0, retained_count: 0,
    transient_read_count: 0, transient_read_bytes: 0, decoded_bytes: 0});
  delete diagnostics.failure;
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
    needSelected(expectedPaths.length > 0, 'one reviewed expectations file required');
    let expectationsPath;
    const cache = new Map();
    const readRow = async (row, retain = true) => {
      needSelected(ordinary(row), 'missing ordinary role');
      if (!cache.has(row.sha)) {
        // All required metadata shares this read cache. Supporting evidence
        // is checked one complete member at a time and never accumulates here.
        const blob = await api(`/repos/${repo}/git/blobs/${row.sha}`, 'GET', undefined, {retainImmutableBlob: retain, expectedImmutableBytes: row.size});
        needSelected(blob.encoding === 'base64' && typeof blob.content === 'string', 'missing blob bytes');
        const bytes = Buffer.from(blob.content, 'base64');
        needSelected(bytes.length === row.size && createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex') === row.sha,
          'blob identity differs');
        diagnostics.read_count++; diagnostics.read_bytes += bytes.length;
        if (!retain) {
          diagnostics.transient_read_count++; diagnostics.transient_read_bytes += bytes.length;
          return bytes;
        }
        cache.set(row.sha, bytes);
        diagnostics.retained_bytes += bytes.length; diagnostics.retained_count = cache.size;
      }
      const bytes = cache.get(row.sha);
      needSelected(bytes.length === row.size, 'cached blob size differs from role tree');
      return bytes;
    };
    const read = (name, tree = authored, retain = true) => readRow(tree.entries.get(name), retain);
    const parseJSON = bytes => {
      // Buffer.toString()/JSON.parse(Buffer) silently replace malformed UTF-8.
      // Reject it before parsing; valid UTF-8 BOMs still follow JSON.parse's
      // existing rejection rather than a decoder silently stripping the BOM.
      needSelected(isUtf8(bytes), 'invalid UTF-8 metadata');
      return JSON.parse(bytes);
    };
    const json = async (name, tree, retain = true) => parseJSON(await read(name, tree, retain));
    const jsonLines = bytes => {
      needSelected(bytes.length > 0, 'empty supporting JSONL');
      for (let start = 0; start < bytes.length;) {
        const newline = bytes.indexOf(10, start), end = newline < 0 ? bytes.length : newline;
        parseJSON(bytes.subarray(start, end));
        start = end + 1;
      }
    };
    let packageAdditions = [];
    if (files.some(file => file.filename === PACKAGE_INPUT_FILE)) {
      const {inputs: before, ...oldPolicy} = validatePackageInputs(await json(PACKAGE_INPUT_FILE, baseline));
      const {inputs: after, ...policy} = validatePackageInputs(await json(PACKAGE_INPUT_FILE));
      needSelected(same(oldPolicy, policy) && after.length >= before.length && same(before, after.slice(0, before.length)),
        'package policy is not append-only');
      packageAdditions = after.slice(before.length);
    }
    const registryChanged = files.some(file => file.filename === ADMINISTRATIVE_REGISTRY);
    const oldSelection = await json(SELECTION, baseline), selection = await json(SELECTION);
    const {additive_release: oldHook, ...oldBase} = oldSelection, {additive_release: hook, ...newBase} = selection;
    needSelected(selection.version === 1 && selection.method === 'native-linear-evenodd-first-owner-v1' &&
      selection.artifact_consumption && same(oldBase, newBase) && !same(oldHook, hook), 'selection changes method/base authority');
    const reachable = new Set(), nativeOperands = new Set(), identities = new Map();
    const unchangedRole = name => {
      const before = baseline.entries.get(name), after = authored.entries.get(name);
      return ordinary(before) && ordinary(after) && before.sha === after.sha && before.size === after.size;
    };
    // The fixed walk may retain accepted code or binary sources. Their exact
    // unchanged tree identity, not their suffix, establishes that this PR adds
    // no executable change. New leaves keep the inert/native-operand boundary.
    const pin = value => {
      needSelected(value && safe(value.path) && (unchangedRole(value.path) || /\.(?:json|jsonl\.gz|json\.gz|log)$/.test(value.path) || nativeOperands.has(value.path)) &&
        hash(value.sha256) && Number.isSafeInteger(value.bytes) && value.bytes >= 0, 'invalid inert role pin');
      const row = authored.entries.get(value.path);
      needSelected(ordinary(row) && row.size === value.bytes &&
        (value.mode === undefined || value.mode === row.mode) &&
        (value.git_blob_oid === undefined || value.git_blob_oid === row.sha), 'role differs from candidate tree');
      // Full pins are required for leaves whose bytes are not read here.
      needSelected((value.git_blob_oid && value.mode === '100644' && /^[a-f0-9]{40}$/.test(value.commit ?? '')) || value === hook, 'role lacks exact tree identity: ' + value.path);
      const identity = [value.bytes, value.sha256, row.sha];
      needSelected(!identities.has(value.path) || same(identities.get(value.path), identity), 'conflicting role identities');
      identities.set(value.path, identity);
      reachable.add(value.path); return value.path;
    };
    const pinnedJSON = async value => {
      const name = pin(value), bytes = await read(name);
      needSelected(sha256(bytes) === value.sha256, 'role content hash differs');
      return parseJSON(bytes);
    };
    // The modern constructor whole-reads this original programme as custody;
    // it never executes or installs it. Keep the current helper unchanged and
    // authenticate the original version instead of relabelling current bytes.
    const physicalReproduction = async value => {
      const current = authored.entries.get(value?.path);
      if (ordinary(current) && current.sha === value.git_blob_oid && current.size === value.bytes) return pin(value);
      needSelected(value && safe(value.path) && unchangedRole(value.path) && value.mode === '100644'
        && /^[a-f0-9]{40}$/.test(value.commit ?? '') && /^[a-f0-9]{40}$/.test(value.git_blob_oid ?? '')
        && Number.isSafeInteger(value.bytes) && value.bytes >= 0 && hash(value.sha256),
      'historical reproduction requires unchanged current code and exact original pin');
      const vintage = await integrationTree(api, repo, value.commit);
      needSelected(vintage.object?.sha === value.commit, 'historical reproduction commit differs');
      const original = vintage.entries.get(value.path);
      needSelected(ordinary(original) && original.mode === value.mode && original.sha === value.git_blob_oid
        && original.size === value.bytes, 'historical reproduction commit/path identity differs');
      const bytes = await readRow(original, false);
      needSelected(sha256(bytes) === value.sha256, 'historical reproduction whole hash differs');
      if (value.decoded_bytes !== undefined) {
        needSelected(Number.isSafeInteger(value.decoded_bytes) && value.decoded_bytes > 0 && hash(value.decoded_sha256),
          'historical reproduction decoded identity required');
        const decoded = gunzipSync(bytes, {maxOutputLength: value.decoded_bytes});
        diagnostics.decoded_bytes += decoded.length;
        needSelected(decoded.length === value.decoded_bytes && sha256(decoded) === value.decoded_sha256,
          'historical reproduction decoded identity differs');
      }
      reachable.add(value.path);
    };
    // Only the two declared exceptions need this SOURCE inventory. Ordinary
    // selected deliveries keep their existing small fixed-role walk.
    const sourceDeclarations = new Set(), usedRegistrations = new Set(), acceptedTrees = new Map();
    let administrative;
    const strings = value => Array.isArray(value) && value.length > 0 &&
      value.every(id => typeof id === 'string' && id.length > 0) && new Set(value).size === value.length;
    const oid = value => value?.git_blob_oid ?? value?.blob;
    const content = value => [value?.path, value?.mode, oid(value), value?.bytes, value?.sha256];
    const unique = (rows, predicate, label) => {
      needSelected(Array.isArray(rows), 'missing ' + label);
      const matches = rows.filter(predicate);needSelected(matches.length === 1, 'ambiguous ' + label);return matches[0];
    };
    const registryEntries = value => {
      needSelected(keys(value, ['version','kind','entries']) && value.version === 1 &&
        value.kind === 'accepted-administrative-handoffs-v1' && Array.isArray(value.entries),
        'unsupported administrative registry');
      const ids = new Set(), paths = new Set(), components = new Set(), batches = new Set();
      for (const entry of value.entries) {
        const execution = entry.format === 'source-native-execution-cohort-v2';
        needSelected(keys(entry, ['accepted_source_commit','cohort_ids','format','id','source','target_ids',
          ...(execution ? [] : ['original_batch_id','original_component_count'])]) &&
          (execution || entry.format === 'source-native-handoff-v1') && typeof entry.id === 'string' && entry.id &&
          /^[a-f0-9]{40}$/.test(entry.accepted_source_commit ?? '') &&
          keys(entry.source, ['blob','bytes','mode','path','sha256']) && safe(entry.source.path) &&
          /^(?:research\/geography|coordination\/engineering)\/[^/]+\/.+\.json$/.test(entry.source.path) && entry.source.mode === '100644' &&
          /^[a-f0-9]{40}$/.test(entry.source.blob ?? '') && hash(entry.source.sha256) &&
          Number.isSafeInteger(entry.source.bytes) && entry.source.bytes > 0 &&
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
    const acceptedSource = async (value, opaque = false) => {
      const current = authored.entries.get(value.path), previous = baseline.entries.get(value.path);
      needSelected(safe(value.path) && ordinary(current) && ordinary(previous) && current.sha === previous.sha &&
        current.size === value.bytes && previous.size === current.size && (!oid(value) || oid(value) === current.sha) &&
        (value.mode === undefined || value.mode === '100644') && hash(value.sha256), 'SOURCE data is not unchanged accepted input');
      if (opaque && value.mode === '100644' && /^[a-f0-9]{40}$/.test(oid(value) ?? '') &&
          /^[a-f0-9]{40}$/.test(value.commit ?? '')) {
        // These unchanged leaves are already named by authenticated SOURCE
        // metadata and still undergo actual package/geography body validation.
        // Exact Git pins avoid rereading the physical world merely to select tests.
        sourceDeclarations.add(value.path);return;
      }
      const bytes = await read(value.path);
      needSelected(sha256(bytes) === value.sha256, 'accepted SOURCE bytes differ');
      sourceDeclarations.add(value.path);return bytes;
    };
    const nativeRoles = async (authority, issued) => {
      const spec = issued.additive, owners = spec.owner_parts;
      if (!Array.isArray(owners) || !owners.some(part => added.has(part.path))) return;
      needSelected(issued.version === 1 && issued.operation === 'unactivated-additive-native-batch-v1' &&
        owners.length > 0 && new Set(owners.map(part => part.path)).size === owners.length,
        'unsupported native operand roles');
      const facts = await pinnedJSON(authority.original_pins.native_facts);
      needSelected(facts.version === 1 && facts.operation === issued.operation &&
        same(content(facts.request), content(authority.original_pins.native_request)) &&
        same(facts.input_descriptors, [issued.report, ...spec.inputs, ...issued.baseline.pins]), 'native request/facts roster differs');
      const manifestPin = unique(spec.inputs, row => row.path === spec.manifest_path, 'native manifest input');
      const unchanged = value => {
        const before = baseline.entries.get(value.path), after = authored.entries.get(value.path);
        needSelected(ordinary(before) && ordinary(after) && before.sha === after.sha && before.size === after.size &&
          after.size === value.bytes && (!oid(value) || after.sha === oid(value)), 'native authority input changed');
        return after;
      };
      unchanged(manifestPin);
      const manifest = await pinnedJSON({...manifestPin, git_blob_oid: oid(manifestPin)});
      needSelected(manifest.version === 2 && manifest.method === selection.method && Array.isArray(manifest.parts) &&
        ['bytes','sha256'].every(key => authority.original_pins.native_manifest[key] === manifestPin[key]) &&
        oid(authority.original_pins.native_manifest) === oid(manifestPin), 'native manifest authority differs');
      const transport = manifest.native_asset_transport;
      needSelected(transport?.version === 1 && transport.kind === 'ordered-exact-original-byte-fragments', 'unknown native transport');
      unchanged(transport.index);
      const indexBytes = await read(transport.index.path);
      needSelected(sha256(indexBytes) === transport.index.sha256, 'native transport index differs');
      const index = parseJSON(indexBytes), manifestRoot = spec.manifest_path.slice(0, spec.manifest_path.lastIndexOf('/') + 1),
        bankRoot = transport.index.path.slice(0, transport.index.path.lastIndexOf('/') + 1);
      needSelected(index.version === 1 && index.kind === transport.kind && Array.isArray(index.files) && Array.isArray(index.parts),
        'unsupported native transport index');
      for (const part of owners.filter(part => added.has(part.path))) {
        const input = unique(spec.inputs, row => row.path === part.path, 'native operand input');
        const descriptor = unique(manifest.parts, row => row.path === part.manifest_path, 'native manifest part');
        const inverse = part.containing_inverse, member = unique(index.files, row => row.path === descriptor.path, 'native bank member');
        needSelected(['rows','runs'].includes(descriptor.kind) && descriptor.encoding === 'byte-shuffle' &&
          Number.isSafeInteger(descriptor.offset) && descriptor.offset >= 0 && Number.isSafeInteger(descriptor.words) && descriptor.words > 0 &&
          descriptor.path === `native-v1/ownership/${descriptor.kind}-${descriptor.offset}.bin.gz` &&
          nativeOperandPath(part.path, branch, reservation) && part.path.split('/').at(-1) === descriptor.path.split('/').at(-1) && input.mode === '100644' &&
          same(part.manifest_descriptor, descriptor) && same(inverse?.manifest_descriptor, descriptor) &&
          inverse.logical_path === manifestRoot + descriptor.path && same(inverse.bank_member, member) &&
          ['bytes','sha256'].every(key => input[key] === descriptor[key] && member[key] === descriptor[key]) &&
          input.uncompressed_bytes === descriptor.decoded_bytes && descriptor.decoded_bytes === descriptor.words * 4 &&
          hash(input.uncompressed_sha256) && hash(descriptor.decoded_sha256), 'native operand identities differ');
        // The request hashes shuffled bytes; the descriptor hashes canonical words.
        // Their lengths agree, but their decoded hashes intentionally need not.
        const pieces = index.parts.filter(row => Math.max(member.offset, row.offset) <
          Math.min(member.offset + member.bytes, row.offset + row.decoded_bytes));
        needSelected(pieces.length > 0 && Array.isArray(inverse.whole_containing_fragments) &&
          inverse.whole_containing_fragments.length === pieces.length &&
          same(inverse.inverse_ranges, pieces.map(row => ({physical_path: bankRoot + row.path,
            start: Math.max(member.offset, row.offset) - row.offset,
            end: Math.min(member.offset + member.bytes, row.offset + row.decoded_bytes) - row.offset}))), 'native inverse ranges differ');
        for (let i = 0; i < pieces.length; i++) {
          const row = pieces[i], fragment = inverse.whole_containing_fragments[i];
          needSelected(fragment.path === bankRoot + row.path && fragment.mode === '100644' &&
            /^[a-f0-9]{40}$/.test(fragment.commit ?? '') && /^[a-f0-9]{40}$/.test(oid(fragment) ?? '') &&
            ['offset','bytes','sha256','decoded_bytes','decoded_sha256'].every(key => fragment[key] === row[key]), 'native containing fragment differs');
          unchanged(fragment);
        }
        nativeOperands.add(part.path);
        pin({...input, git_blob_oid: oid(input)});
        needSelected(sha256(await read(part.path)) === input.sha256, 'native operand encoded hash differs');
      }
    };
    const sourceRoles = async authority => {
      const issued = await pinnedJSON(authority.original_pins.source_request), facts = await pinnedJSON(authority.original_pins.source_facts);
      const rule = issued.source_rule;
      needSelected(issued.version === 1 && issued.operation === 'retained-land-source-premises-v1' &&
        rule?.profile === 'retained-consumed-administrative-source' && rule.version === 1 &&
        rule.registry_path === ADMINISTRATIVE_REGISTRY && rule.geometry_scope === 'full-component' &&
        Array.isArray(rule.inputs) && Array.isArray(issued.baseline?.pins) &&
        same(content(facts.request), content(authority.original_pins.source_request)) && same(facts.source_rule, rule) &&
        same(facts.input_descriptors, [issued.report, ...rule.inputs, ...issued.baseline.pins]), 'SOURCE request/facts join differs');
      administrative ??= registryEntries(await json(ADMINISTRATIVE_REGISTRY));
      const registryPin = unique(rule.inputs, row => row.path === ADMINISTRATIVE_REGISTRY, 'SOURCE registry input');
      // Each qualified SOURCE request keeps its actual execution-time registry.
      // Later cohorts append entries; they must not rewrite that original pin.
      needSelected(registryPin.mode === '100644' && /^[a-f0-9]{40}$/.test(registryPin.commit ?? '') &&
        hash(registryPin.sha256), 'invalid original SOURCE registry pin');
      const registryBytes = await readRow({path: registryPin.path, mode: registryPin.mode, type: 'blob',
        sha: oid(registryPin), size: registryPin.bytes});
      needSelected(sha256(registryBytes) === registryPin.sha256, 'original SOURCE registry bytes differ');
      const originalRegistry = registryEntries(parseJSON(registryBytes));
      needSelected(originalRegistry.length > 0 && same(originalRegistry, administrative.slice(0, originalRegistry.length)),
        'original SOURCE registry history differs');
      const source = unique(rule.inputs, row => row.path === rule.cases_path, 'registered SOURCE input');
      const entry = unique(originalRegistry, row => same(content(row.source), content(source)), 'registered SOURCE');
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
      const handoff = parseJSON(await acceptedSource(source)), cases = handoff.candidate_source_native_bindings;
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
      const catalogue = parseJSON(await acceptedSource(cataloguePin));
      needSelected(Array.isArray(catalogue.products) && Array.isArray(rule.administrative_products) &&
        rule.administrative_products.length > 0, 'missing administrative products');
      const fields = ['bytes','sha256','uncompressed_bytes','uncompressed_sha256'];
      for (const product of rule.administrative_products) {
        needSelected(safe(product.path) && product.path.startsWith(SOURCE_CORPUS + 'payloads/') && product.path.endsWith('.bin.gz'),
          'unknown administrative payload role');
        const input = unique(rule.inputs, row => row.path === product.path, 'administrative input');
        const part = unique(catalogue.products.flatMap(row => row.parts ?? []), row => row.path === product.path, 'catalogue part');
        needSelected(same(content(input), content(product)) && fields.every(key => product[key] === part[key] && product[key] === input[key]) &&
          hash(product.uncompressed_sha256) && Number.isSafeInteger(product.uncompressed_bytes) && product.uncompressed_bytes > 0,
          'administrative product identities differ');
        await acceptedSource(input, true);
      }
      const report = parseJSON(await acceptedSource(issued.report));
      // The report binds a role, but cannot itself become a newly declared input.
      sourceDeclarations.delete(issued.report.path);
      // Metadata-only handoff assembly may retain a previously authenticated
      // physical inverse without claiming that assembly consumed it again.
      const reused = handoff.reused_whole_product_inputs ?? [];
      needSelected(Array.isArray(handoff.consumed_inputs) && Array.isArray(reused) &&
        new Set(reused.map(row => row.path)).size === reused.length && reused.every(row =>
          row.whole_body_consumed === false && row.mode === '100644' && safe(row.path) &&
          /^[a-f0-9]{40}$/.test(row.commit ?? '') && /^[a-f0-9]{40}$/.test(oid(row) ?? '') && hash(row.sha256) &&
          Number.isSafeInteger(row.bytes) && row.bytes > 0 && !handoff.consumed_inputs.some(old => old.path === row.path)),
        'ambiguous or unbound reused physical role');
      needSelected(Array.isArray(rule.original_products) && rule.original_products.length > 0,
        'missing original physical roles');
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
        const retained = unique([...handoff.consumed_inputs, ...reused], row => safe(row.path) && /^(?:research\/geography|coordination\/engineering)\/[^/]+\//.test(row.path) &&
          row.path.endsWith('/' + name) && row.bytes === product.bytes && row.sha256 === product.sha256, 'retained physical Git input');
        await acceptedSource(retained, true);
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
      Array.isArray(registry.entries) && registry.entries.length > 0,
      'missing authority registry');
    needSelected(oldHook && safe(oldHook.path), 'missing preceding selected release');
    const oldSideBytes = await read(oldHook.path, baseline);
    needSelected(oldSideBytes.length === oldHook.bytes && sha256(oldSideBytes) === oldHook.sha256, 'preceding sidecar differs');
    const oldSide = parseJSON(oldSideBytes), oldRegistryPin = oldSide.authority_registry;
    const oldLedgerPin = oldSide.logical_asset_map?.ledger, oldLedgerBytes = await read(oldLedgerPin?.path, baseline);
    needSelected(oldLedgerBytes.length === oldLedgerPin.bytes && sha256(oldLedgerBytes) === oldLedgerPin.sha256, 'preceding ledger differs');
    const templates = [];
    for (const name of expectedPaths) {
      const expected = await json(name);
      if (expected.selected_ledger_sha256 === null) {
        // A prospective package projection is not the authoritative smoke input.
        // Its complete roster must still agree, and its fixed preparation custody
        // is checked below against the actually consumed original/current roles.
        validateSelectedExpectations({...expected, selected_ledger_sha256: sidecar.logical_asset_map.ledger.sha256},
          ledger, sidecar.logical_asset_map.ledger.sha256, parseJSON(oldLedgerBytes));
        templates.push(name);
      } else {
        validateSelectedExpectations(expected, ledger, sidecar.logical_asset_map.ledger.sha256, parseJSON(oldLedgerBytes));
        needSelected(!expectationsPath, 'multiple authoritative expectations');
        expectationsPath = name;
      }
    }
    needSelected(expectationsPath, 'one reviewed expectations file required');
    const oldRegistryBytes = await read(oldRegistryPin.path, baseline);
    needSelected(oldRegistryBytes.length === oldRegistryPin.bytes && sha256(oldRegistryBytes) === oldRegistryPin.sha256, 'preceding registry differs');
    const oldRegistry = parseJSON(oldRegistryBytes);
    needSelected(Array.isArray(oldRegistry.entries) && oldRegistry.entries.every(old =>
      registry.entries.filter(entry => same(entry, old)).length === 1), 'existing authority changed or disappeared');
    let originalLedger;
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
      originalLedger = plan.original_inputs[1];
    };
    // Existing deliveries resolve new authority first; only unresolved native
    // operands require a bounded second pass through retained custody.
    const sourceAuthorities = [];
    const roleEntries = [...registry.entries].sort((a, b) => Number(added.has(b.source_authority?.path)) - Number(added.has(a.source_authority?.path)));
    for (const entry of roleEntries) {
      needSelected(keys(entry, ['authority_sha256','policy_id','policy_version','rule_preimage','rule_sha256','source_authority']), 'foreign registry fields');
      pin(entry.rule_preimage); pin(entry.source_authority);
      const retained = !added.has(entry.source_authority.path);
      if (retained && ![...added].some(name => nativeOperandPath(name, branch, reservation) && !nativeOperands.has(name))) continue;
      const authority = await pinnedJSON(entry.source_authority);
      let restoredRequest;
      if (retained) {
        // A previous selected delivery may retain original authority while
        // omitting another cohort's operands. Revisit only an exact original
        // request that actually names newly restored operands. This grants no
        // opaque-file exception without the full nativeRoles custody checks.
        const before = baseline.entries.get(entry.source_authority.path), after = authored.entries.get(entry.source_authority.path);
        needSelected(ordinary(before) && before.sha === after.sha && before.size === after.size,
          'retained native authority changed');
        const requestPin = authority.original_pins?.native_request;
        if (!requestPin || !authored.entries.has(requestPin.path) || requestPin.mode !== '100644' ||
            !/^[a-f0-9]{40}$/.test(requestPin.git_blob_oid ?? '') || !/^[a-f0-9]{40}$/.test(requestPin.commit ?? '')) continue;
        restoredRequest = await pinnedJSON(requestPin);
        if (!restoredRequest.additive?.owner_parts?.some(part => added.has(part.path))) continue;
      }
      if (authority.kind === 'source-target-native-custody-v1') {
        needSelected(authority.version === 1 && keys(authority,['version','kind','source_evidence','native_patch']),
          'unsupported source-target authority');
        pin(authority.source_evidence); pin(authority.native_patch);
        const rule=await pinnedJSON(entry.rule_preimage), evidence=await pinnedJSON(authority.source_evidence);
        needSelected(rule.version===1&&rule.kind==='source-target-native-rule-v1'
          &&keys(rule,['version','kind','source_evidence','native_patch'])
          &&same(rule.source_evidence,authority.source_evidence)&&same(rule.native_patch,authority.native_patch),
          'source-target rule/input join differs');
        needSelected((evidence.version===1&&evidence.kind==='source-target-native-evidence-v1'
          ||evidence.version===2&&evidence.kind==='source-target-native-evidence-v2')
          &&Array.isArray(evidence.families)&&evidence.families.length>0&&Array.isArray(evidence.targets)&&evidence.targets.length>0,
          'missing source-target evidence roles');
        for (const role of ['catalogue','physical_evidence','physical_input','owner_roster','native_latitudes']) pin(evidence[role]);
        await physicalReproduction(evidence.physical_reproduction);
        // Match the closed whole-body source-reader roles, not arbitrary JSON pins.
        for (const typed of [
          ...(evidence.version === 2 ? [{pin: evidence.dated_land_support,
            kind: 'adopted-dated-native-centre-land-support-v1', roles: ['adoption','review','observation','frame']}] : []),
          ...(evidence.territorial_applicability === undefined ? [] : [{pin: evidence.territorial_applicability,
            kind: 'adopted-native-territorial-applicability-v1', roles: ['adoption','scope','original-source']}])
        ]) {
          const name=pin(typed.pin);let raw=await read(name);
          needSelected(sha256(raw)===typed.pin.sha256,'typed source role content differs');
          if(typed.pin.decoded_bytes!==undefined){
            needSelected(Number.isSafeInteger(typed.pin.decoded_bytes)&&typed.pin.decoded_bytes>0
              &&/^[a-f0-9]{64}$/.test(typed.pin.decoded_sha256),'typed source decoded identity missing');
            raw=gunzipSync(raw,{maxOutputLength:typed.pin.decoded_bytes});
            needSelected(raw.length===typed.pin.decoded_bytes&&sha256(raw)===typed.pin.decoded_sha256,
              'typed source decoded identity differs');
          }
          const body=parseJSON(raw);
          needSelected(body.version===1&&body.kind===typed.kind&&Array.isArray(body.provenance)
            &&body.provenance.length>0,'missing typed source provenance');
          for(const item of body.provenance){
            needSelected(typed.roles.includes(item?.role),'unknown typed source provenance role');
            const multipart=typed.kind==='adopted-native-territorial-applicability-v1'
              &&item.role==='original-source'&&item.parts!==undefined;
            needSelected(!multipart||keys(item,['id','role','parts'])&&Array.isArray(item.parts)
              &&item.parts.length>0,'malformed territorial source parts');
            for(const member of multipart?item.parts:[item.pin])pin(member);
          }
        }
        if(evidence.source_membership!==undefined){
          const membership=evidence.source_membership;
          needSelected(keys(membership,['index','lineage','parts'])&&Array.isArray(membership.parts)&&membership.parts.length>0,
            'missing accepted source membership roles');
          pin(membership.index);pin(membership.lineage);for(const part of membership.parts)pin(part);
        }
        for (const family of evidence.families) {
          needSelected(text(family.source_id)&&Array.isArray(family.parts)&&family.parts.length>0,'missing complete source family roles');
          for (const part of family.parts) pin(part);
        }
        continue;
      }
      needSelected(authority.version === 1 && authority.kind === 'original-issued-rule-source-custody-v1' &&
        keys(authority.original_pins, ['ledger','native_facts','native_manifest','native_request','source_facts','source_request']),
        'unsupported source authority');
      for (const value of Object.values(authority.original_pins)) pin(value);
      const proof = authority.native_proof;
      pin(proof.publication); pin(proof.inventory); pin(proof.operating);
      needSelected(Array.isArray(proof.assets) && proof.assets.length > 0, 'missing native asset roles');
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
      const nativeRequest = restoredRequest ?? await pinnedJSON(authority.original_pins.native_request), spec = nativeRequest.additive;
      await nativeRoles(authority, nativeRequest);
      sourceAuthorities.push(authority);
      needSelected(Array.isArray(spec?.inputs), 'missing source role inputs');
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
    // Existing proof roles are already authenticated by the fixed-role walk.
    // Only declarations beyond that graph need the administrative extension.
    if (registryChanged || packageAdditions.some(name => baseline.entries.has(name) && !reachable.has(name)))
      for (const authority of sourceAuthorities) await sourceRoles(authority);
    for (const name of templates) {
      // A null template needs immutable input/output provenance, never mutable
      // runtime journal state. Legacy published intent pairs remain supported.
      const directory = name.slice(0, name.lastIndexOf('/'));
      const intentPath = directory + '.intent.json', receiptPath = directory + '/preparation.json';
      const receipt = await json(receiptPath), embedded = Object.hasOwn(receipt, 'input');
      needSelected([name, receiptPath, ...(embedded ? [] : [intentPath])].every(path => added.has(path) &&
        inScope(path, engineeringOwnedScopes(reservation)) && !reachable.has(path) && !packageAdditions.includes(path)),
        'unbound prospective expectations');
      const template = await json(name), finalized = await json(expectationsPath);
      needSelected(same({...template, selected_ledger_sha256: finalized.selected_ledger_sha256}, finalized),
        'prospective and finalized expectations differ');
      const intent = embedded ? {version: 1, stage: 'package', binding: receipt.binding, config: receipt.input} : await json(intentPath);
      if (embedded && added.has(intentPath)) needSelected(same(await json(intentPath), intent), 'Conflicting legacy package input');
      const config = intent.config;
      const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object'
        ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
      const binding = {phase: 'package', config_sha256: sha256(Buffer.from(JSON.stringify(canonical(config)) + '\n'))};
      needSelected(keys(intent, ['version','stage','binding','config']) && intent.version === 1 && intent.stage === 'package' &&
        keys(config, ['version','registry','ledger','rebind','new_prefix']) && config.version === 1 &&
        same(config.registry, sidecar.authority_registry) && same(config.ledger, originalLedger) &&
        same(config.rebind, ledger.current_rebind) && typeof config.new_prefix === 'string' &&
        config.new_prefix.endsWith('/') && safe(config.new_prefix.slice(0, -1)) &&
        inScope(config.new_prefix, engineeringOwnedScopes(reservation)) && name.startsWith(config.new_prefix) &&
        same(intent.binding, binding) && keys(receipt, ['version','binding','outputs', ...(embedded ? ['input'] : [])]) && receipt.version === 1 &&
        same(receipt.binding, binding) && keys(receipt.outputs, ['package-roles.json','selected-delivery-expectations.json']),
        'prospective expectations preparation differs');
      for (const [filename, descriptor] of Object.entries(receipt.outputs)) {
        const member = directory + '/' + filename;
        needSelected(added.has(member) && keys(descriptor, ['bytes','sha256']), 'missing prospective preparation member');
        const bytes = await read(member);
        needSelected(descriptor.bytes === bytes.length && descriptor.sha256 === sha256(bytes), 'prospective preparation bytes differ');
      }
    }
    const transport = new Set(), archives = [...added].filter(name => name.endsWith('.zip'));
    if (files.some(file => file.filename === CHECKPOINT_LOCATOR) || archives.length) {
      // This admits inert custody to the selected-data test inventory, not a
      // checkpoint capability. The unchanged real geography job still performs
      // original-job authentication and complete private scientific admission.
      const {ACCEPTED_CHECKPOINT_LOCATOR, validateAcceptedCheckpointLocator} = await import('./accepted-selected-checkpoint.mjs');
      const {githubPages} = await import('./issue-claim-contract.mjs');
      const {readWorkerResult, verifyAcceptedMergeResult} = await import('./worker-result.mjs');
      const {validateGeographyProof, readReportArchive, geographicReportProducts, checkGeographicReport} = await import('./geographic-report-artifact.mjs');
      needSelected(CHECKPOINT_LOCATOR === ACCEPTED_CHECKPOINT_LOCATOR, 'unsupported checkpoint locator route');
      const locator = validateAcceptedCheckpointLocator(await json(ACCEPTED_CHECKPOINT_LOCATOR));
      const archive = locator.retained_artifact?.path;
      needSelected(files.some(file => file.filename === ACCEPTED_CHECKPOINT_LOCATOR) &&
        archives.length === 1 && archives[0] === archive &&
        inScope(archive, [branchScope(branch), ...engineeringOwnedScopes(reservation)]), 'unbound checkpoint archive');
      const definition = validatePackageInputs(await json(PACKAGE_INPUT_FILE));
      needSelected([ACCEPTED_CHECKPOINT_LOCATOR, archive].every(name => !reachable.has(name) &&
        !sourceDeclarations.has(name) && !packagePathRequired(name, definition)), 'checkpoint custody is a consumed package role');
      // Reuse accepted receipt and actual merged-PR checks. The archive's hash
      // comes from that bot receipt, never from the locator or a local digest.
      const acceptedAPI = (...args) => api(args[0], 'GET');
      const acceptance = locator.acceptance;
      const comments = await githubPages(acceptedAPI, `/repos/${repo}/issues/${acceptance.pr_number}/comments`);
      const receipt = readWorkerResult(comments, 'merge', acceptance.request_id, acceptance.pr_number);
      const merged = await acceptedAPI(`/repos/${repo}/pulls/${acceptance.pr_number}`);
      verifyAcceptedMergeResult(receipt, merged, acceptance.head);
      needSelected(merged.number === acceptance.pr_number && merged.base?.ref === 'main' &&
        merged.base.repo?.full_name === repo && merged.head.repo?.full_name === repo &&
        receipt.reviewed_head === acceptance.head, 'foreign checkpoint acceptance');
      const source = validateGeographyProof(receipt.geography?.source);
      const candidateCommit = source.candidate_commit ?? source.head;
      needSelected(source.head === acceptance.head && receipt.geography.status === 'passed' &&
        receipt.geography.report_sha256 === source.report_sha256 &&
        receipt.geography.trusted_code_commit === source.baseline && receipt.tested_base === source.baseline &&
        receipt.geography.candidate_commit === candidateCommit, 'checkpoint receipt/source differs');
      for (const commit of [receipt.merge_commit, receipt.tested_candidate]) {
        needSelected(/^[a-f0-9]{40}$/.test(commit ?? ''), 'missing accepted checkpoint commit');
        const object = await acceptedAPI(`/repos/${repo}/git/commits/${commit}`);
        needSelected(object.sha === commit && object.tree?.sha === source.tree, 'checkpoint accepted/tested tree differs');
      }
      const raw = await read(archive, authored, false);
      needSelected(raw.length === source.artifact_bytes && sha256(raw) === source.artifact_digest,
        'checkpoint archive differs from accepted artifact digest');
      const report = readReportArchive(raw, source.report_sha256, source.report_bytes);
      checkGeographicReport(report, source.baseline, candidateCommit);
      needSelected(report.checkpoint, 'legacy report has no checkpoint custody');
      const facts = parseJSON(geographicReportProducts(report).members.get('derived-facts.json'));
      needSelected(facts.candidate_commit === candidateCommit && same(facts.candidate_selection, oldSelection),
        'checkpoint does not supply selected baseline');
      transport.add(ACCEPTED_CHECKPOINT_LOCATOR); transport.add(archive);
    }
    const updatedManifest = scientificManifest(branch, reservation);
    const manifestChanged = updatedManifest && files.some(file => file.filename === updatedManifest && file.status === 'modified');
    const supporting = new Set([...added].filter(retainedSupportingEvidence));
    if (manifestChanged) {
      needSelected(ordinary(baseline.entries.get(updatedManifest)), 'nonordinary scientific manifest');
      supporting.add(updatedManifest);
    }
    const manifest = `coordination/engineering/${branch.slice('engineering/'.length)}/evidence-quality.json`;
    for (const name of added) {
      if (retainedSupportingEvidence(name)) {
        // Authenticate and discard each whole original body. Do not execute a
        // retained module, follow XML entities/LFS pointers, or turn an archive
        // into package input. Scientific interpretation stays with its validator.
        let bytes = await read(name, authored, false);
        if (name.endsWith('.gz')) {
          bytes = gunzipSync(bytes);
          diagnostics.decoded_bytes += bytes.length;
        }
        if (name.endsWith('.geojson.gz')) parseJSON(bytes);
        else if (name.endsWith('.jsonl') && (bytes.length || !name.endsWith('.stdout.jsonl'))) jsonLines(bytes);
        else if (!name.endsWith('.f64le.gz'))
          needSelected(!bytes.includes(0) && isUtf8(bytes), 'nontext retained evidence');
        continue;
      }
      if (supportingText(name, branch, reservation)) {
        needSelected(!reachable.has(name) && !sourceDeclarations.has(name) &&
          !packagePathRequired(name, validatePackageInputs(await json(PACKAGE_INPUT_FILE))), 'supporting text is a consumed role');
        const bytes = await read(name, authored, false);
        needSelected(!bytes.includes(0) && Buffer.from(bytes.toString('utf8')).equals(bytes), 'nontext packet documentation');
        continue;
      }
      if (reachable.has(name) || transport.has(name) || name === expectationsPath || name === manifest) continue;
      // Non-consumed supporting evidence cannot become package input. It must
      // still be ordinary inert JSON/text, never a module, configuration or opaque archive.
      // Validate syntax, then discard it: arbitrary preparation records confer no
      // reader/package role and must not consume retained structural-metadata space.
      if (name.endsWith('.json')) {
        const bytes = await read(name, authored, false);
        // Original HTTP metadata may be XML despite a retained .json name.
        // Preserve that response verbatim; it earns only unconsumed custody,
        // under the same base/package exclusion as a named XML source.
        if (bytes.subarray(0, 5).equals(Buffer.from('<?xml'))) {
          needSelected(!bytes.includes(0) && isUtf8(bytes), 'nontext retained XML response');
          supporting.add(name);
        } else parseJSON(bytes);
      }
      else if (/\.jsonl?\.gz$/.test(name)) {
        const bytes = await read(name, authored, false);
        // No decoded-size pin is declared for inert supporting evidence.
        // The codec validates every complete gzip member, including concatenated
        // members, before the whole decoded JSON/JSONL body is parsed.
        const decoded=gunzipSync(bytes);
        diagnostics.decoded_bytes += decoded.length;
        if (name.endsWith('.json.gz')) parseJSON(decoded);
        else jsonLines(decoded);
      }
      else {
        needSelected(name.endsWith('.log'), 'unknown opaque evidence type');
        const bytes = await read(name, authored, false);
        needSelected(!bytes.includes(0) && Buffer.from(bytes.toString('utf8')).equals(bytes), 'nontext evidence log');
      }
    }
    if (supporting.size) {
      // Issue ownership and a historical-looking filename establish no role.
      // Reuse the fixed base-reader walk for every newly admitted retained file,
      // including helper copies. None may become current code or package input.
      const definition = validatePackageInputs(await json(PACKAGE_INPUT_FILE));
      for (const name of supporting) needSelected(!reachable.has(name) && !sourceDeclarations.has(name) &&
        ![selection.manifest_path, selection.selected_geography?.path, selection.artifact_consumption?.certificate?.path,
          selection.artifact_consumption?.review?.path].includes(name) && !packagePathRequired(name, definition),
        'supporting evidence is a consumed role');
      // Accepted base metadata can still name current reader roles outside
      // package declarations. Read only those fixed routing roots, never their
      // scientific leaves or arbitrary nested pin/config objects.
      const role = name => {
        needSelected(safe(name) && !supporting.has(name), 'supporting evidence is a consumed base role');
        return name;
      };
      const rolePin = value => {
        needSelected(value && hash(value.sha256) && Number.isSafeInteger(value.bytes) && value.bytes > 0,
          'unknown base role pin');
        return role(value.path);
      };
      const baseJSON = async (name, descriptor) => {
        role(name); needSelected(unchangedRole(name), 'base routing metadata changed or unavailable');
        const bytes = await read(name, baseline);
        needSelected(hash(descriptor.sha256) && sha256(bytes) === descriptor.sha256 &&
          (descriptor.bytes === undefined || bytes.length === descriptor.bytes), 'base routing metadata pin differs');
        return parseJSON(bytes);
      };
      const roles = rows => {
        needSelected(Array.isArray(rows), 'unknown base role roster');
        return rows;
      };
      const native = await baseJSON(selection.manifest_path, {sha256: selection.sha256});
      needSelected(native.version === 2 && native.method === selection.method && roles(native.parts).length > 0,
        'unknown base native routing');
      const nativeRoot = path.posix.dirname(selection.manifest_path);
      for (const part of native.parts) {
        needSelected(['rows', 'runs'].includes(part.kind), 'unknown base native part');
        role(path.posix.join(nativeRoot, role(part.path)));
      }
      role(path.posix.join(nativeRoot, role(native.bounds?.path)));
      role(native.original_assets?.bounds?.path);
      if (native.native_asset_transport !== undefined) {
        const transport = native.native_asset_transport;
        needSelected(transport.version === 1 && transport.kind === 'ordered-exact-original-byte-fragments',
          'unknown base native transport');
        const index = await baseJSON(rolePin(transport.index), transport.index);
        needSelected(index.version === 1 && index.kind === transport.kind, 'unknown base transport index');
        for (const part of roles(index.parts)) role(path.posix.join(path.posix.dirname(transport.index.path), role(part.path)));
      }
      const verified = await json('scripts/native-ownership/verified-candidates.json', baseline);
      needSelected(unchangedRole('scripts/native-ownership/verified-candidates.json') && verified.version === 1 &&
        verified.candidates?.[selection.sha256]?.role === 'reviewed-exhaustive-native-rule-comparison', 'unknown base comparison registry');
      role(verified.candidates[selection.sha256].path);
      if (selection.selected_geography !== undefined) {
        const declared = selection.selected_geography, bank = await baseJSON(rolePin(declared), declared);
        needSelected(declared.version === 1 && declared.kind === 'complete-world-index-with-exact-encoded-overrides' &&
          bank.version === 1 && bank.kind === declared.kind, 'unknown base source routing');
        for (const value of [bank.world_index, ...roles(bank.unchanged_files), ...roles(bank.overrides)]) rolePin(value);
      }
      const certificatePin = selection.artifact_consumption.certificate;
      const certificate = await baseJSON(rolePin(certificatePin), certificatePin);
      needSelected(certificate.version === 1 && certificate.kind === 'qualified-arctic-immutable-product-certificate-v1' &&
        roles(certificate.application_inputs).length > 0, 'unknown base consumption certificate');
      for (const value of [certificate.application_consumer_code, certificate.qualification_inventory,
        ...certificate.application_inputs]) rolePin(value);
      if (certificate.release_product_catalogue !== undefined) {
        rolePin(certificate.release_product_catalogue); rolePin(certificate.selected_artifact_bindings?.registry);
      }
      const code = await baseJSON(certificate.application_consumer_code.path, certificate.application_consumer_code);
      needSelected(code.version === 1 && code.kind === 'qualified-artifact-application-code-closure-v1' &&
        roles(code.critical_files).length > 0, 'unknown base application source routing');
      for (const value of code.critical_files) rolePin(value);
      if (code.entry_critical_files !== undefined) {
        needSelected(code.entry_critical_files && typeof code.entry_critical_files === 'object' &&
          !Array.isArray(code.entry_critical_files), 'unknown base entry source routing');
        for (const values of Object.values(code.entry_critical_files)) for (const value of roles(values)) rolePin(value);
      }
      if (manifestChanged) await json(updatedManifest, authored, false);
    }
    if (registryChanged) {
      const previous = registryEntries(await json(ADMINISTRATIVE_REGISTRY, baseline));
      needSelected(administrative && administrative.length > previous.length && same(previous, administrative.slice(0, previous.length)) &&
        administrative.slice(previous.length).every(entry => usedRegistrations.has(entry.id)), 'registry is not append-only selected SOURCE data');
    }
    // Package declarations can introduce already accepted original proof roles.
    // File creation time is not scientific authority: typed reachability plus
    // exact unchanged Git identity is required for these retained leaves.
    needSelected(packageAdditions.every(name => reachable.has(name) && (added.has(name) || unchangedRole(name)) || sourceDeclarations.has(name)),
      'package change is not append-only exact reachable data');
    return {test_selection: 'selected-data', expectations_path: expectationsPath, shards: [0]};
  } catch (error) {
    diagnostics.failure = typeof error?.message === 'string' && error.message.startsWith('Selected-data: ') ? error.message : 'Invalid or unavailable selected metadata';
    if (error?.planningNeeded) throw error; // Preserve the existing bounded capacity-planning retry.
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
    if (!stat.isFile() || stat.isSymbolicLink()) throw Error('Nonordinary selected data');
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
  const sidecar = pinned(selection.additive_release), ledgerPin = sidecar.logical_asset_map?.ledger;
  validateSelectedExpectations(JSON.parse(read(expectationsPath)), pinned(ledgerPin), ledgerPin.sha256);
  const {runSelectedDeliverySmoke} = await import('./selected-delivery-smoke.mjs');
  return runSelectedDeliverySmoke({root: process.cwd(), emittedDirectory: path.resolve('dist/client'),
    expectationsPath, outputPath: path.resolve('.cache/selected-delivery-smoke.json')});
}

import {repairComponentKey} from '../src/native-grid.js';
import {finalBankSelection,scientificNativeSelection} from '../src/reference-metadata.js';
import {focusedIntegrationTest} from './run-integration-tests.mjs';

// These delivery controls use their actual focused consumers. Unknown runtime
// implementation and rename origins retain full regression.
export const COORDINATION_PATHS = new Set([
  // Delivery orchestration is not imported by the atlas builder. Shared native
  // operators and native-preparation-guards remain outside this exact list.
  'scripts/prepare-delivery-handoff.mjs', 'scripts/delivery-handoff-advance.mjs',
  // The immutable comparison/checkpoint family has no application or builder
  // imports. Its complete focused consumers and candidate geography still run.
  'scripts/native-word-store.mjs','scripts/native-patch-store.mjs', 'scripts/check-effective-geographic-regression.mjs', 'scripts/run-geographic-check.py',
  'coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs',
  'coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs',
  'docs/WORKER_COORDINATION.md', 'docs/PREMERGE_EVIDENCE_REVIEW.md',
  'scripts/issue-claim-contract.mjs', 'scripts/run-issue-claim.mjs',
  'scripts/worker-result.mjs', 'scripts/check-handoff-scope.mjs',
  'scripts/evidence-quality.mjs', 'scripts/evidence-policy.mjs', 'scripts/premerge-evidence.mjs',
  'scripts/merge-integration.mjs', 'scripts/integration-proof.mjs',
  'scripts/geographic-adjudication-api.mjs',
  'scripts/git-blob-transport.mjs', 'scripts/immutable-git-blobs.mjs',
  'scripts/integration-profile.mjs',
  // Runner, workspace and package custody have actual focused child consumers.
  'scripts/run-integration-tests.mjs', 'scripts/ci-setup-observations.mjs',
  'scripts/local-workspace.mjs', 'scripts/worker-identity.mjs', 'scripts/github-quota.mjs',
  'scripts/package-inputs.mjs', 'scripts/package-build.mjs',
  'scripts/package-output-artifact.mjs', 'scripts/package-python-runtime.py',
  'scripts/assemble-selected-package.mjs', 'scripts/selected-package-bootstrap.py',
  '.github/package-inputs.json', 'AGENTS.md',
  'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs',
  'scripts/run-worker-merge.mjs',
  '.github/workflows/handoff-scope.yml',
  '.github/workflows/worker-merge.yml',
  '.github/evidence-policy.json'
]);
const packet = name => /\.(?:md|txt|jsonl?(?:\.gz)?|log|stdout|stderr|csv|tsv)$/.test(name) &&
  !/^(?:package(?:-lock)?\.json|npm-shrinkwrap\.json|(?:requirements|constraints)(?:[.-].*)?\.txt|pyproject\.toml|setup\.(?:py|cfg)|__init__\.py|(?:site|user)customize\.py|(?:js|ts)config(?:\.[^.]+)?\.json|import[-_.]?map\.json)$/i.test(name.split('/').at(-1));
const sourcePacketPath = name => safePackagePath(name) && /^(?:research\/(?:campaigns|geography)|data\/regional-review)\/[^/]+\//.test(name);

// Existing tests are checked as ordinary current files. Added controls run by
// the same discovery rule; removed controls need no replacement full suite.
// Routing follows actual changed files and consumed package roles, never a
// branch name or an issue-owned path declaration.
export function integrationProfile(branch, files, reservation = {}, authoredEntries) {
  const names = files.flatMap(file => [file.filename, ...(file.previous_filename ? [file.previous_filename] : [])]);
  if (!names.length) return 'full';
  // Validate each focused test before composing it with the existing route.
  const focused = files.filter(file => [file.filename, file.previous_filename].some(name => focusedIntegrationTest(name)));
  if (focused.length && !(authoredEntries instanceof Map &&
      focused.every(file => focusedIntegrationTest(file.filename) && (file.status === 'removed'
        ? !authoredEntries.has(file.filename)
        : authoredEntries.get(file.filename)?.type === 'blob' &&
          authoredEntries.get(file.filename)?.mode === '100644' &&
          /^[a-f0-9]{40}$/.test(authoredEntries.get(file.filename)?.sha ?? '') &&
          (!file.filename.endsWith('.py') || (() => {
            const wrapper = authoredEntries.get(file.filename.replace(/\.py$/, '.mjs'));
            return wrapper?.type === 'blob' && wrapper.mode === '100644' && /^[a-f0-9]{40}$/.test(wrapper.sha ?? '');
          })()))))) return 'full';

  let definition;
  try { definition = loadPackageInputs(); } catch { return 'full'; }
  // Source packets are inert unless declared as actual package inputs. Their
  // real scientific checks remain selected independently by geographyRequired.
  if (names.every(name => sourcePacketPath(name) && !packagePathRequired(name, definition))) return 'evidence';
  const removed = new Set(files.filter(file => file.status === 'removed' && !file.previous_filename &&
    /^(?:scripts\/|test\/|\.github\/workflows\/)/.test(file.filename) &&
    !packagePathRequired(file.filename, definition)).map(file => file.filename));
  const control = name => removed.has(name) || COORDINATION_PATHS.has(name) || focusedIntegrationTest(name) ||
    name.startsWith('docs/') && /\.(md|txt)$/.test(name);
  if (files.every(file => {
    if ([file.filename, ...(file.previous_filename ? [file.previous_filename] : [])].every(control)) return true;
    if (file.previous_filename || !packetPath(file.filename) ||
        file.mode !== undefined && !['100644', '100755'].includes(file.mode) ||
        packagePathRequired(file.filename, definition)) return false;
    return file.status === 'added' && packet(file.filename) ||
      file.status === 'modified' && file.filename.endsWith('/evidence-quality.json');
  })) return 'evidence';
  return 'full';
}

// The existing inert packet contract can derive the default consumer roster.
// Mixed/changed code, selected roles and nonordinary trees retain normal routing.
export function inertEvidenceAdditions(files, entries, definition) {
  return entries instanceof Map && files.length > 0 && files.every(file =>
    file.status === 'added' && !file.previous_filename &&
    (packetPath(file.filename) || sourcePacketPath(file.filename)) && packet(file.filename) &&
    !packagePathRequired(file.filename, definition) && ordinary(entries.get(file.filename)) &&
    file.filename.split('/').slice(0,-1).every((_, index, parts) => {
      const parent = entries.get(parts.slice(0,index+1).join('/'));
      return parent?.type === 'tree' && parent.mode === '040000';
    }));
}

// Exercise checker upgrades on unchanged data; proposed map edits use accepted code.
// This is conservative path classification, not a programme/hash exemption.
// Data-only full checks still use baseline code and authenticated adjudication.
export function candidateGeographyCode(profile, files, testSelection, acceptedEntries) {
  if (!['full','evidence'].includes(profile) || testSelection === 'selected-data') return false;
  // A candidate cannot certify its own map edit, even when it also changes the
  // checker. Ordinary source tests exercise that upgrade separately.
  if (acceptedEntries?.has('data/canonical-grid/current-startup/index.json') &&
    files.some(file => [file.filename,file.previous_filename].some(name =>
      name === 'data/ownership-selection.json' || name?.startsWith('data/canonical-grid/current-startup/')))) return false;
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
import {validatePackageInputs, admitSelectedPackageDeclarations, loadPackageInputs, packagePathRequired, safePackagePath, containsPackagePath, PACKAGE_INPUT_FILE, PREPARED_STARTUP_PREFIX, PREPARED_STARTUP_INDEX, preparedStartupPackageTransition} from './package-inputs.mjs';
const SELECTION = 'data/ownership-selection.json';
const ADMINISTRATIVE_REGISTRY = 'coordination/engineering/melanesia363-additive-delivery-20261010/accepted-administrative-handoffs.json';
const SOURCE_CORPUS = 'coordination/engineering/original-geography-source-corpus-20261006/';
export const SELECTED_SMOKE = 'scripts/selected-delivery-smoke.mjs';
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const safe = value => typeof value === 'string' && /^[A-Za-z0-9_./-]+$/.test(value) &&
  value.split('/').every(part => part && part !== '.' && part !== '..' && !part.startsWith('.'));
const ordinary = (row, mode = '100644') => row?.type === 'blob' && row.mode === mode &&
  /^[a-f0-9]{40}$/.test(row.sha ?? '') && Number.isSafeInteger(row.size) && row.size >= 0;
const needSelected = (value, message) => { if (!value) throw Error('Selected-data: ' + message); };
const keys = (value, names) => value && typeof value === 'object' && !Array.isArray(value) &&
  same(Object.keys(value).sort(), [...names].sort());
const text = value => typeof value === 'string' && value.length > 0 && value.length < 1024;

// Expectations are reviewed source-side data. Require the WHOLE selected roster,
// including zero-cell members. Held/rejected rows remain in the ledger but
// are not rendered selections; a self-consistent active subset cannot select fewer tests.
const packetPath = name => safe(name) && /^coordination\/engineering\/[^/]+\//.test(name);
const nativeOperandPath = name => packetPath(name) && /^(?:rows|runs)-[0-9]+\.bin\.gz$/.test(name.split('/').at(-1));
const scientificManifest = name => packetPath(name) && name.endsWith('/evidence-quality.json');
// This is only a cheap candidate filter. The complete authenticated role walk
// below decides applicability, including every added or changed supporting file.
export function selectedDataCandidate(branch, files, reservation = {}) {
  return files.length > 1 &&
    files.some(file => file.filename === SELECTION && file.status === 'modified') &&
    files.every(file => !file.previous_filename && ([SELECTION, PACKAGE_INPUT_FILE, ADMINISTRATIVE_REGISTRY].includes(file.filename)
      ? file.status === 'modified' : file.filename === PREPARED_STARTUP_INDEX ? file.status === 'modified'
      : file.filename.startsWith(PREPARED_STARTUP_PREFIX) ? ['added','removed'].includes(file.status)
      : file.status === 'modified' && scientificManifest(file.filename) ||
        file.status === 'added' && packetPath(file.filename)));
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
    // New executable originals may be supporting custody. Every consumed role
    // remains 100644; the complete role walk below must prove custody unconsumed.
    needSelected(files.every(({filename,status}) => status==='removed'&&filename.startsWith(PREPARED_STARTUP_PREFIX)
      ? ordinary(baseline.entries.get(filename)) : ordinary(authored.entries.get(filename)) ||
      added.has(filename) && ordinary(authored.entries.get(filename), '100755')) &&
      [...added].every(name => !baseline.entries.has(name)), 'nonordinary or overwritten data');
    const expectedPaths = [...added].filter(name => name.endsWith('/selected-delivery-expectations.json'));
    needSelected(expectedPaths.length > 0, 'one reviewed expectations file required');
    let expectationsPath, expectationsBytes;
    const cache = new Map();
    const readRow = async (row, retain = true) => {
      needSelected(ordinary(row), 'missing ordinary role');
      if (!cache.has(row.sha)) {
        // Required metadata shares this read cache. Explicit transient roles
        // are checked one complete member at a time without accumulating here.
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
    const registryChanged = files.some(file => file.filename === ADMINISTRATIVE_REGISTRY);
    const oldSelection = await json(SELECTION, baseline), selection = await json(SELECTION);
    let bank={changed:new Set()};
    if(baseline.entries.has(PREPARED_STARTUP_INDEX)||authored.entries.has(PREPARED_STARTUP_INDEX)||files.some(file=>file.filename.startsWith(PREPARED_STARTUP_PREFIX))){
      const source=(tree,selection)=>({selection,files:[...tree.entries].filter(([,row])=>row.type==='blob').map(([path,row])=>({path,mode:row.mode,oid:row.sha,bytes:row.size}))});
      bank=preparedStartupPackageTransition(source(baseline,oldSelection),source(authored,selection),{
        beforeIndex:await read(PREPARED_STARTUP_INDEX,baseline),afterIndex:await read(PREPARED_STARTUP_INDEX),
        beforeSelection:await read(SELECTION,baseline),afterSelection:await read(SELECTION)});
      needSelected(files.filter(file=>file.filename.startsWith(PREPARED_STARTUP_PREFIX)).every(file=>bank.changed.has(file.filename)), 'Unbound prepared-bank change');
    }
    let packageAdditions = [], packageDefinitions;
    if (files.some(file => file.filename === PACKAGE_INPUT_FILE)) {
      packageDefinitions = {before:validatePackageInputs(await json(PACKAGE_INPUT_FILE, baseline)),
        after:validatePackageInputs(await json(PACKAGE_INPUT_FILE))};
    }
    if(oldSelection.version===2||selection.version===2){
      // First adoption requires a fresh full capture. Later final banks use
      // only current files and the newly proposed authority group, never the
      // historical cumulative ledger or registry. Geography remains authority.
      needSelected(oldSelection.version===2&&selection.version===2,'First final-profile adoption requires full capture');
      finalBankSelection(oldSelection);finalBankSelection(selection);
      needSelected(same(scientificNativeSelection(oldSelection),scientificNativeSelection(selection))
        &&same(oldSelection.reference_projection,selection.reference_projection),'Final native/reference selection changed');
      const reachable=new Set([SELECTION,PACKAGE_INPUT_FILE,...bank.changed]);
      const pinned=async(value,jsonBody=false)=>{
        needSelected(value&&safe(value.path)&&hash(value.sha256)&&Number.isSafeInteger(value.bytes)&&value.bytes>0,'Invalid final role');
        const row=authored.entries.get(value.path);
        needSelected(ordinary(row)&&row.size===value.bytes&&(value.mode===undefined||value.mode===row.mode)
          &&(value.git_blob_oid===undefined||value.git_blob_oid===row.sha),'Final role tree differs');
        reachable.add(value.path);
        if(!jsonBody&&value.mode==='100644'&&value.git_blob_oid&&value.commit)return;
        const raw=await read(value.path);needSelected(sha256(raw)===value.sha256,'Final role whole identity differs');
        return jsonBody?parseJSON(raw):raw;
      };
      const full=value=>{needSelected(value?.mode==='100644'&&/^[a-f0-9]{40}$/.test(value.commit??'')
        &&/^[a-f0-9]{40}$/.test(value.git_blob_oid??''),'Complete final evidence pin required');return value;};
      if(selection.reference_projection){
        const p=selection.reference_projection,a=baseline.entries.get(p.path),b=authored.entries.get(p.path);
        needSelected(ordinary(a)&&a.sha===b?.sha&&a.size===b.size,'Final reference body changed');await pinned(p);
      }
      // A switched/restored pointer is not an append command. Only genuinely
      // changed evidence files need role discovery; current bank validation
      // independently qualifies every actual positive destination.
      if(selection.change_evidence&&files.some(file=>file.filename===selection.change_evidence.path)){
        const registry=await pinned(selection.change_evidence,true),seen=new Set();
        needSelected(registry.version===1&&registry.kind==='retained-rule-authority-registry-v1'&&Array.isArray(registry.entries)&&registry.entries.length>0,'New final registry required');
        for(const entry of registry.entries){
          needSelected(keys(entry,['authority_sha256','policy_id','policy_version','rule_preimage','rule_sha256','source_authority','completed_constructor'])
            &&hash(entry.authority_sha256)&&!seen.has(entry.authority_sha256),'Final native authority shape/identity differs');seen.add(entry.authority_sha256);
          const binding=await pinned(full(entry.source_authority),true),rule=await pinned(full(entry.rule_preimage),true);
          needSelected(binding.version===1&&binding.kind==='source-target-native-custody-v1'
            &&keys(binding,['version','kind','source_evidence','native_patch'])&&same(rule,{...binding,kind:'source-target-native-rule-v1'}),'Final native rule/binding differs');
          await pinned(full(entry.completed_constructor));await pinned(full(binding.native_patch));await pinned(full(binding.source_evidence));
        }
      }
      for(const name of expectedPaths){
        const raw=await read(name),expected=parseJSON(raw);
        if(expected.version!==2||expected.kind!=='selected-final-bank-consumer-v2'||!keys(expected,['version','kind','bank','reference'])
          ||!same(expected.bank,selection.prepared_bank)||!same(expected.reference,selection.reference))continue;
        needSelected(!expectationsBytes||expectationsBytes.equals(raw),'Multiple final expectations');expectationsBytes=raw;expectationsPath??=name;reachable.add(name);
      }
      needSelected(expectationsPath,'One exact final-bank expectations file required');
      if(packageDefinitions){const declarations=admitSelectedPackageDeclarations(packageDefinitions.before,packageDefinitions.after,{currentPaths:[...reachable]});
        needSelected(declarations.additions.every(name=>bank.changed.has(name)),'Final package declaration is not current bank data');}
      needSelected(files.every(file=>reachable.has(file.filename)),'Unbound final-profile change');
      return {test_selection:'selected-data',expectations_path:expectationsPath,shards:[0]};
    }
    needSelected(false,'Current selected-data delivery requires final-map version 2');
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
  const selection = JSON.parse(read('data/ownership-selection.json'));
  needSelected(selection.version===2,'Current selected smoke requires final-map version 2');
  const {runSelectedDeliverySmoke} = await import('./selected-delivery-smoke.mjs');
  return runSelectedDeliverySmoke({root: process.cwd(), emittedDirectory: path.resolve('dist/client'),
    expectationsPath, outputPath: path.resolve('.cache/selected-delivery-smoke.json')});
}

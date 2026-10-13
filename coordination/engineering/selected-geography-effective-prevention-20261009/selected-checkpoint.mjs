// Invocation-scoped reuse of accepted selected products. Candidate JSON is data.
// Trust enters only through the catalogue in the executing reviewed checkout.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {ImmutableReader, NativeAssetImage} from '../../../scripts/check-effective-geographic-regression.mjs';
import {unshuffleOwnershipBytes} from '../../../src/ownership-codec.js';
import {valueBytes, valueSha, coordinateBounds, nativeBaseSelection,
  normaliseRetainedRepairLedger, readRetainedRegistryAuthority, validateSupportedProgrammeCatalogue,
  compatibleCurrentRebindCode, CURRENT_REBIND_CODE, verifyCurrentRebindExecution, validateCurrentRebindLimits,
  currentRebindResult, currentRebindAcquisitionIdentity, retainedArcticNativeRows} from './selected-neighbor-prevention.mjs';

const FILE = 33554432;
const ROOT = fileURLToPath(new URL('../../../', import.meta.url));
const MODULE = 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
const CATALOGUE = 'coordination/engineering/selected-checkpoint-reuse-20261012/accepted-checkpoints.json';
const FIELDS = ['id','index','parent_id','parent_index','source','ordinal','whole_feature_sha256','geometry_sha256','effective_geometry_sha256','boxes'];
const states = new WeakMap(), projections = new WeakMap(), transitions = new WeakMap();
const LOCATOR = 'data/selected-checkpoint.json';
const ACCEPTED_CODE = ['scripts/accepted-selected-checkpoint.mjs','scripts/check-handoff-scope.mjs',
  'scripts/evidence-policy.mjs','scripts/evidence-quality.mjs','scripts/geographic-report-artifact.mjs',
  'scripts/github-quota.mjs','scripts/github-snapshots.mjs','scripts/integration-proof.mjs',
  'scripts/issue-claim-contract.mjs','scripts/job-deadline.mjs','scripts/research-import-gate.mjs',
  'scripts/worker-result.mjs','src/regional-import-gate.js'];
const JOINT_CODE = ['scripts/run-geographic-check.py','scripts/check-geographic-regression.py',
  'scripts/check-effective-geographic-regression.mjs','src/ownership-codec.js',
  'scripts/evidence/immutable.py','scripts/evidence/geometry.py','scripts/ellipsoidal_area.py','requirements.txt',
  'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs',
  'coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs',
  MODULE,'coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint-continuous.mjs',
  'coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs'];
const JOINT_NATIVE_CODE=[...JOINT_CODE.slice(0,3),'scripts/selected-checkpoint-native.mjs',...JOINT_CODE.slice(3)];
const DERIVED_CODE=[...JOINT_NATIVE_CODE,...ACCEPTED_CODE,'scripts/geographic_checkpoint_products.py'];
const demand = (ok, message) => { if (!ok) throw Error(message); };
const sha = body => createHash('sha256').update(body).digest('hex');
// Policy is rooted in the executing trusted checkout, independently of the
// selected scientific vintage. Keep its archived census entry, but do not make
// accepted programme additions look like changed source/native input bytes.
const PROGRAMME_POLICY = 'coordination/engineering/selected-geography-effective-prevention-20261009/supported-programs.json';
const sameScientificRoutes = (reader,routes) => routes.every(p => p.path === PROGRAMME_POLICY || treeRoute(reader,p.path) === p.tree);
const same = (a,b) => a === undefined || b === undefined ? a === b : valueSha(a) === valueSha(b);
const hash = x => typeof x === 'string' && /^[a-f0-9]{64}$/.test(x);
const commit = x => typeof x === 'string' && /^[a-f0-9]{40}$/.test(x);
const safe = x => typeof x === 'string' && x.length > 0 && !x.includes('\\') && !x.includes('\0') && !path.posix.isAbsolute(x) && x.split('/').every(p => p && p !== '.' && p !== '..');
const freeze = x => { if (x && typeof x === 'object' && !Object.isFrozen(x)) { Object.values(x).forEach(freeze); Object.freeze(x); } return x; };
const keys = (x, expected, message) => demand(x && same(Object.keys(x).sort(), expected.split(',').sort()), message);
const unavailable = (reason, baseline) => Object.freeze({available:false, reason, cold:baseline ? 'candidate' : 'baseline-and-candidate', ...(baseline ? {baseline} : {})});
const supported = (ok, message) => { if (!ok) { const error = Error(message); error.reuseUnavailable = true; throw error; } };

// The current complete allowance and one shared reader budget belong to this
// invocation. A historical peak is never permission for a current allocation.
function budgetCheck(reader, budget, session) {
  demand(reader instanceof ImmutableReader && budget && budget.shared === reader.budget,
    'Checkpoint requires the actual shared immutable-reader budget');
  demand(Number.isSafeInteger(budget.carriedBytes) && budget.carriedBytes >= 0,
    'Explicit complete caller-carried bytes required');
  demand(reader.runtimeBytes >= fs.statSync(process.execPath).size,
    'Checkpoint runtime undercharge');
  if (session) {
    demand(!session.closed && budget === session.budget && reader.budget === session.reader.budget
      && reader.allowance === session.reader.allowance && reader.repo === session.reader.repo,
    'Foreign, expired or independently budgeted checkpoint invocation');
    demand(reader.used >= session.floor && budget.carriedBytes >= session.callerCarry,
      'Checkpoint live-state budget was reset or undercharged');
    const additionalCarry=budget.carriedBytes-session.callerCarry;
    demand(reader.used+additionalCarry<=reader.phaseLimit,
      'External carried-state increase exceeds current allowance before projection reuse');
    reader.used+=additionalCarry;
    session.floor=Math.max(session.floor,reader.used);
    session.callerCarry=budget.carriedBytes;
  }
  reader.checkMemory();
}
function charge(session, reader, bytes) {
  demand(Number.isSafeInteger(bytes) && bytes >= 0 && reader.used + bytes <= reader.phaseLimit,
    'Complete checkpoint input/output/carry exceeds current allowance before allocation');
  reader.used += bytes;
  session.floor = Math.max(session.floor, reader.used);
}
function beginFrame(session, reader, extra = 0) {
  budgetCheck(reader, session.budget, session);
  reader.metadataBytes = session.initialMetadata + session.budget.carriedBytes + session.residentBytes;
  reader.outputBytes = session.initialOutput;
  reader.phase();
  session.floor = reader.used;
  charge(session, reader, extra);
}
function retain(session, value) {
  // A conservative seven-byte representation allowance follows the existing
  // current-rebind output frame. Pin sizes reserve this before parsing.
  const bytes = 7 * valueBytes(value).length;
  demand(Number.isSafeInteger(bytes), 'Invalid retained checkpoint size');
  session.residentBytes += bytes;
  return bytes;
}
function pin(p) {
  demand(p && commit(p.commit) && safe(p.path) && ['100644','100755'].includes(p.mode)
    && /^[a-f0-9]{40}$/.test(p.git_blob_oid) && Number.isSafeInteger(p.bytes)
    && p.bytes > 0 && p.bytes <= FILE && hash(p.sha256), 'Incomplete immutable checkpoint pin');
  if (p.decoded_bytes !== undefined) demand(Number.isSafeInteger(p.decoded_bytes)
    && p.decoded_bytes > 0 && p.decoded_bytes <= FILE && hash(p.decoded_sha256),
  'Incomplete whole decoded checkpoint pin');
}
function resolvePin(reader, p) {
  pin(p);
  let version = p.commit;
  try { reader.git('cat-file','-e',version+'^{commit}'); } catch { version = reader.version; }
  const actual = reader.descriptor(p.path, version);
  demand(actual.mode === p.mode && actual.git_blob_oid === p.git_blob_oid && actual.bytes === p.bytes,
    'Checkpoint whole mode/OID/size or historical alias changed: '+p.path);
  return {actual, version};
}
function readBody(session, reader, p, {json = true} = {}) {
  const {version} = resolvePin(reader, p), decoded = p.decoded_bytes ?? 0;
  charge(session, reader, (json ? 7 : 1) * (decoded || p.bytes));
  const encoded = reader.read(p.path, {version, expected:p.sha256, decoded});
  let body = encoded;
  if (decoded) {
    demand(encoded.length >= 18 && encoded.readUInt32LE(encoded.length-4) === decoded,
      'Checkpoint gzip declared size differs before inflate');
    body = gunzipSync(encoded, {maxOutputLength:decoded});
    demand(body.length === decoded && sha(body) === p.decoded_sha256,
      'Checkpoint whole decoded output is corrupt');
  }
  session.floor = reader.used;
  return json ? JSON.parse(body) : body;
}
function localPin(reader, name, version = reader.version, expected) {
  const actual = reader.descriptor(name, version);
  return {...actual, sha256:expected ?? sha(reader.read(name, {version}))};
}
function readNamed(session, reader, name, expected) {
  const p = reader.descriptor(name);
  charge(session,reader,7*p.bytes);
  const body = reader.read(name,{expected});
  if (name===PROGRAMME_POLICY && reader.version===session.trusted && !session.executingPolicy) {
    charge(session,reader,2*body.length);
    session.executingPolicy=freeze({pin:{...reader.inventory.get(reader.version+':'+name)},body:body.toString('utf8')});
    retain(session,session.executingPolicy);
  }
  session.floor = reader.used;
  return JSON.parse(body);
}
function rootCatalogue(session, reader, {accepted = false} = {}) {
  const trusted = reader.git('-C',ROOT,'rev-parse', '--verify', 'HEAD').toString().trim();
  // Do not derive trust from reader.version or a caller-supplied trusted SHA.
  const executing = new ImmutableReader(ROOT, trusted, {runtimeBytes:reader.runtimeBytes,
    executionBytes:reader.executionBytes, budget:reader.budget, allowance:reader.allowance,
    gitExecutable:reader.gitExecutable});
  executing.inventory=reader.inventory; // one invocation's complete archived custody survives the child
  demand(executing.git('rev-parse','HEAD').toString().trim() === trusted,
    'Checkpoint repo differs from the actual trusted execution checkout');
  const catalogue = readNamed(session, executing, CATALOGUE);
  keys(catalogue, 'version,kind,checkpoints', 'Unknown checkpoint catalogue schema');
  demand(catalogue.version === 1 && catalogue.kind === 'accepted-selected-checkpoints-v1'
    && Array.isArray(catalogue.checkpoints),
  'Unknown trusted checkpoint catalogue');
  const expectedPaths = [MODULE,
    'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs',
    'scripts/check-effective-geographic-regression.mjs','src/ownership-codec.js'];
  // HEAD owns current code identity; the catalogue records historical science.
  // Keep authenticating the actual executable bytes without a second hash ledger.
  for (const name of [...expectedPaths, ...(accepted ? ACCEPTED_CODE : [])]) {
    const actual = executing.descriptor(name), local = path.join(ROOT,name);
    demand(actual.mode === '100644', 'Checkpoint method identity differs');
    charge(session, reader, 2 * actual.bytes);
    const bytes = fs.readFileSync(local);
    demand(bytes.length === actual.bytes && bytes.equals(executing.read(name)),
      'Unrecognized/changed executing checkpoint method');
  }
  demand(new Set(catalogue.checkpoints.map(p => p.id)).size === catalogue.checkpoints.length,
    'Duplicate accepted checkpoint identity');
  return {catalogue, trusted, archiveReader:executing};
}
function treeRoute(reader, name, version = reader.version) {
  demand(safe(name), 'Unsafe checkpoint route');
  return reader.git('ls-tree','-z',version,'--',name).toString();
}
function readSelection(session, reader) {
  const selection = readNamed(session, reader, 'data/ownership-selection.json');
  supported(selection?.version === 1 && selection.method === 'native-linear-evenodd-first-owner-v1'
    && selection.additive_release && selection.selected_geography?.kind === 'complete-world-index-with-exact-encoded-overrides',
  'Unsupported selected checkpoint profile');
  const hook = selection.additive_release;
  keys(hook, 'bytes,path,sha256', 'Unknown additive selector');
  const d = reader.descriptor(hook.path);
  demand(d.bytes === hook.bytes && d.mode === '100644', 'Additive selector body differs');
  const sidecar = readNamed(session, reader, hook.path, hook.sha256);
  keys(sidecar,'version,kind,base_selection,authority_registry,logical_asset_map,runtime_envelope','Unknown additive sidecar');
  supported(sidecar.version === 2 && sidecar.kind === 'retained-native-additive-selection-v2', 'Unsupported additive sidecar version');
  demand(same(sidecar.base_selection,nativeBaseSelection(selection)), 'Stale actual native base selection');
  keys(sidecar.logical_asset_map,'base_manifest,ledger,owner_roster,patch','Incomplete additive asset map');
  const registry = readBody(session,reader,sidecar.authority_registry);
  const ledger = readBody(session,reader,sidecar.logical_asset_map.ledger);
  const patch = readBody(session,reader,sidecar.logical_asset_map.patch);
  const wrapped = readBody(session,reader,sidecar.runtime_envelope), envelope = wrapped.additiveRelease ?? wrapped;
  keys(envelope,'version,kind,base_manifest,base_reference,effective_reference,ledger,owner_roster,patch','Unknown additive envelope');
  supported(envelope.version === 2 && envelope.kind === 'retained-native-base-plus-delta-v2'
    && ledger.version === 2 && patch.version === 2, 'Unsupported non-v2 additive products');
  for (const [role,p] of Object.entries(sidecar.logical_asset_map)) {
    const q = envelope[role];
    demand(q && p.bytes === q.bytes && p.sha256 === q.sha256
      && (p.decoded_bytes ?? p.bytes) === (q.decoded_bytes ?? q.bytes)
      && (p.decoded_sha256 ?? p.sha256) === (q.decoded_sha256 ?? q.sha256), 'Runtime additive asset differs: '+role);
    resolvePin(reader,p);
  }
  const reference = r => {
    keys(r,'id,hierarchy_sha256,footprints_sha256','Unknown complete effective reference');
    demand(typeof r.id==='string' && r.id.startsWith('geography:') && hash(r.hierarchy_sha256)
      && hash(r.footprints_sha256), 'Invalid complete effective reference identity');
  };
  reference(envelope.base_reference); reference(envelope.effective_reference);
  keys(patch,'version,kind,authority_registry_sha256,base_reference,effective_reference,ledger_sha256,rows',
    'Unknown complete native patch schema');
  const normalized = normaliseRetainedRepairLedger(ledger,registry);
  demand(patch.kind === 'unassigned-native-cells-v1' && patch.authority_registry_sha256 === valueSha(registry)
    && patch.ledger_sha256 === sidecar.logical_asset_map.ledger.sha256
    && same(patch.base_reference,envelope.base_reference) && same(patch.effective_reference,envelope.effective_reference),
  'Stale native patch/ledger/registry binding');
  return {selection,sidecar,registry,ledger,patch,envelope,normalized};
}
function completeRows(rows, size, owners) {
  let previous = -1;
  demand(Array.isArray(rows), 'Missing complete native rows');
  for (const row of rows) {
    keys(row,'y,runs','Unknown native row shape');
    demand(Number.isSafeInteger(row.y) && row.y > previous && row.y < size && Array.isArray(row.runs),
      'Duplicate, unordered or foreign native row');
    previous = row.y; let end = 0;
    for (const run of row.runs) {
      demand(Array.isArray(run) && run.length === 3 && run.every(Number.isSafeInteger)
        && run[0] >= end && run[1] > run[0] && run[1] <= size && run[2] > 0 && run[2] <= owners,
      'Incomplete, overlapping or foreign native interval'); end = run[1];
    }
  }
}
function coordinateCheck(certificate, facts, additions) {
  demand(certificate.version === 2 && certificate.kind === 'selected-coordinate-neighbor-certificate-v2'
    && same(certificate.entry_fields,FIELDS) && same(certificate.binding,facts.binding)
    && certificate.entries.length === facts.complete_owners && certificate.inputs.length === facts.complete_sources,
  'Incomplete accepted coordinate product');
  const ids = new Set(), sources = new Map(certificate.inputs.map(p => [p.path,p]));
  demand(sources.size === certificate.inputs.length, 'Duplicate checkpoint source inventory');
  for (const [i,row] of certificate.entries.entries()) {
    demand(Array.isArray(row) && row.length === 10 && typeof row[0] === 'string' && !ids.has(row[0])
      && row[1] === i+1 && typeof row[2] === 'string' && Number.isSafeInteger(row[3])
      && sources.has(row[4]) && Number.isSafeInteger(row[5]) && row[5] >= 0
      && [row[6],row[7],row[8]].every(hash), 'Incomplete/duplicate checkpoint owner/index/parent identity');
    ids.add(row[0]);
    const effective = additions.filter(p => p.target_id === row[0]);
    demand(effective.every(p => p.pixelIndex === row[1] && p.base_geometry_sha256 === row[7])
      && row[8] === valueSha({base_geometry_sha256:row[7],additions:effective}), 'Checkpoint complete primitive set differs');
    demand(Array.isArray(row[9]) && row[9].length > 0 && row[9].every(b => Array.isArray(b) && b.length === 4
      && b.every(Number.isFinite) && b[0] >= -180 && b[2] <= 180 && b[1] >= -90 && b[3] <= 90
      && b[0] <= b[2] && b[1] <= b[3]), 'Invalid checkpoint exclusion bound');
  }
  for (const input of certificate.inputs) {
    demand(hash(input.whole_body_sha256) && input.bytes === (input.source.decoded_bytes ?? input.source.bytes)
      && input.whole_body_sha256 === (input.source.decoded_sha256 ?? input.source.sha256),
    'Checkpoint source whole decoded identity differs');
    supported(['ordinary-immutable-git-source','selected-exact-encoded-override'].includes(input.source.kind),
      'Unsupported retained selected source transport');
  }
}
function rebindProducts(session, reader, ledger) {
  supported(ledger.current_rebind, 'Current-base-bound producer proof is unavailable');
  const certificate = readBody(session,reader,ledger.current_rebind);
  keys(certificate,'version,kind,execution_commit,base_selection,authority_registry_sha256,request,facts,publication,operating,result','Unknown current rebind certificate');
  const bodies = {};
  for (const name of ['request','facts','publication','operating','result']) bodies[name] = readBody(session,reader,certificate[name]);
  return {certificate,...bodies};
}
function newState(session, data, privateData) {
  freeze(data); states.set(data,{session,...privateData}); session.handles.add(data); return data;
}
function getState(state, reader, budget) {
  const proof = states.get(state);
  demand(proof && !proof.session.closed, 'Missing private qualified selected checkpoint');
  budgetCheck(reader ?? proof.reader,budget ?? proof.session.budget,proof.session);
  return proof;
}

/** budget = {shared: reader.budget, carriedBytes: complete caller live bytes}.
 * Reader.version is the actual baseline, not the historical execution commit.
 * Unsupported reuse returns a cold-path decision. Corrupt custody throws. */
export function qualifyCheckpoint({reader,checkpointId,budget}) {
  budgetCheck(reader,budget);
  const session = {reader,budget,callerCarry:budget.carriedBytes,closed:false,handles:new Set(),residentBytes:0,
    initialMetadata:reader.metadataBytes,initialOutput:reader.outputBytes,floor:reader.used};
  charge(session,reader,budget.carriedBytes);
  try {
    const {catalogue,trusted,archiveReader} = rootCatalogue(session,reader);
    session.trusted=trusted;
    const selected = readSelection(session,reader);
    const matches = catalogue.checkpoints.filter(root => (!checkpointId || root.id === checkpointId)
      && root.selection_sha256 === valueSha(selected.selection));
    supported(matches.length === 1, 'No unique accepted checkpoint for the actual complete selector');
    const root = matches[0];
    if (root.kind==='accepted-derived-selected-checkpoint-v1')
      return admitTrustedDerivedSeed(session,reader,archiveReader,root,catalogue);
    keys(root,'id,accepted_head,selected_commit,selection_sha256,execution_commit,execution_code_sha256,runtime_sha256,facts,certificate,publication,custody,routes','Unknown accepted checkpoint registration');
    demand(commit(root.accepted_head) && commit(root.selected_commit) && commit(root.execution_commit), 'Incomplete original acceptance/execution identity');
    const facts = readBody(session,archiveReader,root.facts), publication = readBody(session,archiveReader,root.publication);
    const certificate = readBody(session,archiveReader,root.certificate), custody = readBody(session,archiveReader,root.custody);
    demand(facts.kind === 'trusted-selected-coordinate-stage-v1' && facts.candidate_code_executed === false
      && facts.selected_commit === root.selected_commit && facts.executing_commit === root.execution_commit
      && valueSha(facts.execution_code) === root.execution_code_sha256 && valueSha(facts.runtime) === root.runtime_sha256,
    'Accepted checkpoint execution/code/runtime binding differs');
    demand(publication.complete === true && publication.kind === facts.kind
      && publication.facts.sha256 === root.facts.sha256 && publication.facts.bytes === root.facts.bytes
      && publication.certificate.sha256 === root.certificate.sha256
      && publication.certificate.decoded_sha256 === root.certificate.decoded_sha256,
    'Accepted checkpoint output publication differs');
    const retained = custody.complete_cold_custody?.find(p => p.facts.selected_commit === root.selected_commit);
    demand(retained && same(retained.facts,facts) && same(retained.publication,publication)
      && same(facts.binding.selection,selected.selection), 'Accepted checkpoint detached custody differs');
    const rebind = rebindProducts(session,reader,selected.ledger);
    demand(same(rebind.request.base_selection,nativeBaseSelection(selected.selection))
      && rebind.request.authority_registry_sha256 === valueSha(selected.registry)
      && same(rebind.result.native.rows,selected.patch.rows), 'Accepted checkpoint rebind/native selection differs');
    const additions = [...selected.normalized.rows.values()].map(row => {
      const target = rebind.request.current_targets.find(p => p.target_id === row.target_id);
      demand(target && target.pixelIndex === row.pixelIndex, 'Accepted current target identity omitted');
      return {...row,base_geometry:target.geometry,base_geometry_sha256:target.geometry_sha256};
    });
    demand(same(additions,retained.effective_additions), 'Accepted original ledger/normalized additions differ');
    coordinateCheck(certificate,facts,additions);
    const manifest = readNamed(session,reader,selected.selection.manifest_path,selected.selection.sha256);
    completeRows(selected.patch.rows,manifest.size,certificate.entries.length);
    completeRows(rebind.request.current_rows,manifest.size,certificate.entries.length);
    demand(same(selected.ledger.current_targets,rebind.request.current_targets), 'Accepted complete target roster differs');
    // Complete old consumed paths are immutable. Include every ordinary-vs-bank
    // alternative even when absent; ls-tree equality alone reads no source body.
    const routes = readBody(session,archiveReader,root.routes);
    const paths = new Set(retained.inventory.map(p => p.path).filter(p => !/\.(mjs|py)$/.test(p) && p !== 'requirements.txt'));
    paths.delete('data/ownership-selection.json');
    for (const p of manifest.parts) paths.add(path.posix.join(path.posix.dirname(selected.selection.manifest_path),p.path));
    for (const input of certificate.inputs) { paths.add(input.path); paths.add(input.source.path); }
    demand(Array.isArray(routes) && same(routes.map(p => p.path),[...paths].sort())
      && routes.every(p => typeof p.tree === 'string'), 'Incomplete trusted present/absent route census');
    // Policy eligibility is not revoked by silently dropping its old file from
    // route equality. Authenticate the actual accepted execution's catalogue
    // and require its complete records to survive in the executing policy.
    // This is two small policy bodies, not any old source/native qualification.
    const policyPins=retained.inventory.filter(p => p.path===PROGRAMME_POLICY);
    demand(policyPins.length===1, 'Missing complete accepted programme policy custody');
    const priorPolicy=validateSupportedProgrammeCatalogue(readBody(session,archiveReader,policyPins[0]));
    const currentPolicy=validateSupportedProgrammeCatalogue(readNamed(session,archiveReader,PROGRAMME_POLICY));
    for (const key of ['programs','current_rebind_migrations']) {
      const current=new Set(currentPolicy[key].map(valueSha));
      supported(priorPolicy[key].every(row => current.has(valueSha(row))),
        'Trusted producer policy no longer preserves accepted eligibility');
    }
    supported(sameScientificRoutes(reader,routes), 'Accepted checkpoint input or routing alternative changed');
    // All genuine old complete records remain in the state, including exceptions.
    const data = {version:1,kind:'verified-selected-state-v1',selected_commit:reader.version,
      accepted_execution:{accepted_head:root.accepted_head,execution_commit:root.execution_commit,
        historical_selected_commit:root.selected_commit,checkpoint_id:root.id,trusted_catalogue_commit:trusted},
      selection:selected.selection,baseSelection:nativeBaseSelection(selected.selection),certificate,
      additions,ledger:selected.ledger,registry:selected.registry,patch:selected.patch,manifest};
    return finishCheckpoint(session,reader,{data,routes,rebind,selected,root});
  } catch (error) {
    session.closed = true;
    if (error.reuseUnavailable) return unavailable(error.message);
    throw error;
  }
}

function finishCheckpoint(session,reader,{data,routes,rebind,selected,root,carriedCertificate=false}) {
  const oldAuthorities = new Map();
  // Read only original small patch products already accepted by the checkpoint.
  // No original source/native qualification or selected acquisition is repeated.
  for (const entry of selected.registry.entries) {
    const binding = readBody(session,reader,entry.source_authority);
    const publication = readBody(session,reader,binding.native_proof.publication);
    demand(publication.assets.length === binding.native_proof.assets.length, 'Accepted native asset roster differs');
    const patches = [];
    for (let i=0;i<publication.assets.length;i++) if (publication.assets[i].path.startsWith('patch-')) {
      const p = binding.native_proof.assets[i], q = publication.assets[i];
      demand(p.path.endsWith('/'+q.path) && p.sha256 === q.sha256 && p.bytes === q.bytes,
        'Accepted original native patch alias differs');
      patches.push(readBody(session,reader,p));
    }
    demand(patches.length > 0, 'Accepted native authority has no complete patches');
    oldAuthorities.set(entry.authority_sha256,{entry,patches});
  }
  const originalPatches = [...oldAuthorities.values()].flatMap(p => p.patches);
  const nativeRows = new Map(rebind.request.current_rows.map(p => [p.y,p]));
  for (const row of rebind.request.acquisition.predecessor_rows) nativeRows.set(row.y,row);
  demand(same(originalPatches.map(valueSha),rebind.request.original_patch_sha256s), 'Accepted complete original patch denominator differs');
  if (carriedCertificate) {
    const {certificate,...newData}=data;
    retain(session,{data:newData,rebind,originalPatches});
  } else retain(session,{data,routes,rebind,originalPatches});
  const state = newState(session,data,{reader,routes,rebind,oldAuthorities,selected,root,
    nativeRows,sourceTargets:new Map(rebind.request.current_targets.map(p => [p.target_id,p]))});
  return Object.freeze({available:true,state});
}

// The accepted report is authority only after the transport module has verified
// the existing bot merge receipt, actual merged tree, trusted job and archive.
// Keep the legacy synchronous entry independent of this optional async boundary.
export async function qualifyAcceptedCheckpoint({reader,acceptedHandle,budget}) {
  budgetCheck(reader,budget);
  const session={reader,budget,callerCarry:budget.carriedBytes,closed:false,handles:new Set(),residentBytes:0,
    initialMetadata:reader.metadataBytes,initialOutput:reader.outputBytes,floor:reader.used};
  charge(session,reader,budget.carriedBytes);
  try {
    const {trusted,archiveReader}=rootCatalogue(session,reader,{accepted:true});
    session.trusted=trusted;
    const {readAcceptedCheckpoint}=await import('../../../scripts/accepted-selected-checkpoint.mjs');
    const accepted=readAcceptedCheckpoint(acceptedHandle);
    demand(Number.isSafeInteger(accepted.admitted_bytes) && accepted.admitted_bytes>0
      && budget.carriedBytes>=accepted.admitted_bytes, 'Accepted archive complete live carry is undercharged');
    return admitDerivedCheckpoint(session,reader,archiveReader,accepted);
  } catch (error) {
    session.closed=true;
    if (error.reuseUnavailable) return unavailable(error.message);
    throw error;
  }
}

// A single reviewed main-tree seed reuses the existing catalogue trust root.
// It is never relabelled as a hosted job or a cold-coordinate execution.
function admitTrustedDerivedSeed(session,reader,archiveReader,root,catalogue) {
  keys(root,'kind,id,accepted_head,selected_commit,selection_sha256,execution_commit,execution_code_sha256,runtime_sha256,facts,certificate,publication,continuous_facts,operands,continuous_publication,joint_result,operating,routes,executing_policy',
    'Unknown trusted derived checkpoint registration');
  demand(commit(root.accepted_head) && commit(root.selected_commit) && commit(root.execution_commit)
    && hash(root.selection_sha256) && hash(root.execution_code_sha256) && hash(root.runtime_sha256),
  'Incomplete trusted derived acceptance/execution identity');
  const roles={facts:'derived-facts.json',certificate:'derived-certificate.json.gz',publication:'derived-publication.json',
    continuous_facts:'facts.json',operands:'operands.json.gz',continuous_publication:'publication.json',routes:'checkpoint-routes.json'};
  const products={},members=[];
  for (const [role,name] of Object.entries(roles)) {
    const p=root[role]; products[name]=readBody(session,archiveReader,p);
    // Repository evidence may gzip an originally plain canonical JSON product.
    // Keep its original logical publication identity without relabelling bytes.
    members.push(name.endsWith('.gz')?{name,bytes:p.bytes,sha256:p.sha256,
      decoded_bytes:p.decoded_bytes,decoded_sha256:p.decoded_sha256}
      :{name,bytes:p.decoded_bytes??p.bytes,sha256:p.decoded_sha256??p.sha256});
  }
  const facts=products['derived-facts.json'], joint=readBody(session,archiveReader,root.joint_result);
  const predecessor=catalogue.checkpoints.find(p=>p.id===facts.baseline_accepted_execution?.checkpoint_id);
  demand(predecessor && !predecessor.kind && predecessor.id!==root.id
    && predecessor.accepted_head===facts.baseline_accepted_execution.accepted_head
    && predecessor.execution_commit===facts.baseline_accepted_execution.execution_commit
    && predecessor.selected_commit===facts.baseline_accepted_execution.historical_selected_commit,
  'Trusted seed predecessor acceptance differs');
  const inherited=readBody(session,archiveReader,predecessor.routes);
  demand(Array.isArray(inherited) && inherited.every(validRoute)
    && same(products['checkpoint-routes.json'].predecessor_paths,inherited.map(p=>p.path)),
  'Trusted seed omitted its complete inherited route census');
  const operating=readBody(session,archiveReader,root.operating);
  demand(facts.executing_commit===root.execution_commit && facts.candidate_commit===root.selected_commit
    && valueSha(facts.candidate_selection)===root.selection_sha256
    && valueSha(facts.execution_code)===root.execution_code_sha256 && valueSha(facts.runtime)===root.runtime_sha256,
  'Trusted derived original execution/code/runtime differs');
  demand(joint.version===1 && joint.kind==='trusted-selected-joint-comparison-v1'
    && joint.mode==='authenticated-checkpoint-append-v1' && joint.candidate_code_executed===false,
  'Trusted seed lacks its original joint completion');
  demand(operating.complete===true && operating.returncode===0 && operating.failure===null
    && same(operating.errors,[]) && same(operating.terminal_group_scan?.members,[])
    && same(operating.cleanup_group_scan?.members,[]), 'Trusted seed lacks measured successful terminal custody');
  // This internal view is not a fabricated geographic report or acceptance
  // receipt. The only authority is the already authenticated trusted catalogue.
  const report={gate_status:'passed',selected_native_report:joint.native,selected_continuous_report:joint.continuous_result};
  retain(session,{certificate:products['derived-certificate.json.gz'],routes:products['checkpoint-routes.json'].routes});
  return admitDerivedCheckpoint(session,reader,archiveReader,{seedRoot:root,products,member_pins:members,report,
    source:{executing_commit:root.execution_commit,baseline:facts.baseline_commit,candidate_commit:root.selected_commit}});
}

function admitDerivedCheckpoint(session,reader,archiveReader,accepted) {
  const {source,receipt,report,products,member_pins,seedRoot}=accepted;
  const trusted=session.trusted;
  const facts=products['derived-facts.json'], certificate=products['derived-certificate.json.gz'];
  const publication=products['derived-publication.json'], continuousFacts=products['facts.json'];
  const continuousPublication=products['publication.json'], operands=products['operands.json.gz'];
  const census=products['checkpoint-routes.json'];
  const members=new Map(member_pins.map(p=>[p.name,p]));
  const published=(name,p)=>{
    const actual=members.get(name);
    demand(actual && p?.path===name && p.bytes===actual.bytes && p.sha256===actual.sha256
      && p.decoded_bytes===actual.decoded_bytes && p.decoded_sha256===actual.decoded_sha256
      && valueSha(products[name])===(actual.decoded_sha256??actual.sha256),
    'Accepted whole checkpoint publication/member differs: '+name);
  };
  const factKeys='version,kind,validation_stage,accepted_checkpoint,executing_commit,execution_code,runtime,baseline_accepted_execution,executing_authority_pins,actual_reader_inventories,baseline_commit,candidate_commit,baseline_selection,candidate_selection,candidate_bindings,transition_plan,native_result_sha256,continuous_publication,candidate_code_executed,certificate,checkpoint_routes,executing_policy';
  const expectedFactKeys=seedRoot?factKeys.split(',').filter(key=>!['checkpoint_routes','executing_policy'].includes(key) || Object.hasOwn(facts??{},key)).join(','):factKeys;
  keys(facts, expectedFactKeys+(Object.hasOwn(facts??{},'checkpoint_transport_inputs')?',checkpoint_transport_inputs':''),
    'Unknown accepted derived checkpoint facts');
  demand(facts.version===1 && facts.kind==='derived-selected-checkpoint-candidate-v1'
    && facts.validation_stage==='native-passed-continuous-pending' && facts.accepted_checkpoint===false
    && facts.candidate_code_executed===false && facts.executing_commit===(source.executing_commit??source.baseline)
    && facts.baseline_commit===source.baseline && facts.candidate_commit===source.candidate_commit,
  'Accepted derived execution/selected vintage differs');
  keys(publication,'version,complete,kind,accepted_checkpoint,validation_stage,certificate,facts'+(!seedRoot || Object.hasOwn(publication??{},'routes')?',routes':''),
    'Unknown accepted derived publication');
  demand(publication.version===1 && publication.complete===true && publication.kind===facts.kind
    && publication.accepted_checkpoint===false && publication.validation_stage===facts.validation_stage,
  'Accepted derived publication completion differs');
  published('derived-facts.json',publication.facts); published('derived-certificate.json.gz',publication.certificate);
  if (!seedRoot || publication.routes) {
    published('checkpoint-routes.json',publication.routes);
    demand(same(facts.checkpoint_routes,publication.routes), 'Accepted complete route publication differs');
  }
  demand(same(facts.certificate,publication.certificate), 'Accepted candidate certificate pin differs');
  published('facts.json',continuousPublication?.facts); published('operands.json.gz',continuousPublication?.operands);
  demand(continuousPublication.version===1 && continuousPublication.complete===true
    && continuousPublication.kind==='trusted-selected-continuous-comparison-v1'
    && same(facts.continuous_publication,continuousPublication), 'Accepted continuous publication differs');
  const native=report.selected_native_report, continuous=report.selected_continuous_report;
  const {runtime:outerRuntime,caller_runtime:outerCaller,execution_runtimes:outerRuntimes,
    execution_code_inventory:outerCode,...nativeInverse}=native??{};
  demand(report.gate_status==='passed' && native?.status==='no-new-native-loss'
    && native.method==='selected-native-owner-conservation-v1' && native.candidate_code_executed===false
    && native.lost_or_reassigned_cells===0 && same(native.intervals,[])
    && valueSha(nativeInverse)===facts.native_result_sha256
    && same(native.baseline_selection,facts.baseline_selection) && same(native.candidate_selection,facts.candidate_selection),
  'Accepted checkpoint lacks its complete successful native result');
  const outer=[outerRuntime,outerCaller,outerRuntimes,outerCode];
  demand(outer.every(p=>p===undefined) || outer.every(p=>p!==undefined)
    && same(outerRuntime,facts.runtime[0]) && same(outerCaller,facts.runtime[1])
    && same(outerRuntimes,facts.runtime) && same(outerCode,facts.execution_code),
  'Accepted native wrapper execution/runtime differs');
  const strict=continuous?.original_strict_polygon_result;
  demand(continuous?.kind===continuousPublication.kind && continuous.candidate_code_executed===false
    && ['no-new-regression','no-footprint-change'].includes(continuous.status)
    && (continuous.regressions===0 || continuous.status==='no-footprint-change' && continuous.regressions===null)
    && strict && strict.status===continuous.status && strict.regressions===continuous.regressions
    && same(strict.findings,{type:'FeatureCollection',features:[]}) && same(strict.geometry_errors,[])
    && same(continuous.issued_publication,continuousPublication),
  'Accepted checkpoint lacks its original successful strict polygon result');
  const codePaths=facts.execution_code?.map(p=>p.path);
  supported(seedRoot && same(codePaths,JOINT_NATIVE_CODE) || same(codePaths,DERIVED_CODE),
    'Unsupported accepted joint method closure');
  for (const p of facts.execution_code) {
    pin(p); demand(p.commit===facts.executing_commit, 'Accepted executing code was rebound');
    // The original trusted accepted execution already authenticated these exact
    // complete code bodies. Preserve its pins; do not reacquire that old method.
  }
  demand(Array.isArray(facts.runtime) && facts.runtime.length===3
    && new Set(facts.runtime.map(p=>p.path)).size===3 && facts.runtime.every(p=>typeof p.path==='string'
      && Number.isSafeInteger(p.bytes) && p.bytes>0 && Number.isSafeInteger(p.mode) && hash(p.sha256)),
  'Incomplete accepted execution runtime identities');
  keys(continuousFacts,'version,kind,baseline_commit,candidate_commit,executing_commit,execution_code,runtime,plan,inverse,checkpoint_custody,source_custody,validation_route,candidate_code_executed',
    'Unknown complete accepted continuous facts');
  demand(commit(facts.baseline_accepted_execution?.accepted_head)
    && commit(facts.baseline_accepted_execution?.execution_commit)
    && commit(facts.baseline_accepted_execution?.historical_selected_commit)
    && same(continuousFacts.checkpoint_custody?.baseline,facts.baseline_accepted_execution)
    && same(continuousFacts.checkpoint_custody?.candidate,facts.baseline_accepted_execution),
  'Accepted complete predecessor checkpoint custody differs');
  demand(same(continuousFacts.execution_code,facts.execution_code) && same(continuousFacts.runtime,facts.runtime)
    && continuousFacts.kind===continuousPublication.kind && continuousFacts.executing_commit===facts.executing_commit
    && continuousFacts.baseline_commit===facts.baseline_commit && continuousFacts.candidate_commit===facts.candidate_commit
    && continuousFacts.candidate_code_executed===false && continuousFacts.validation_route==='authenticated-checkpoint-append-v1',
  'Accepted continuous execution/custody differs');
  const selected=readSelection(session,reader);
  supported(same(selected.selection,facts.candidate_selection), 'Accepted checkpoint does not cover the actual complete selector');
  const manifest=readNamed(session,reader,selected.selection.manifest_path,selected.selection.sha256);
  demand(same(facts.candidate_bindings,{ledger_sha256:valueSha(selected.ledger),registry_sha256:valueSha(selected.registry),
    patch_sha256:valueSha(selected.patch),manifest_sha256:valueSha(manifest)}),
  'Accepted checkpoint changed the complete ledger/registry/patch/manifest');
  const rebind=rebindProducts(session,reader,selected.ledger);
  demand(same(rebind.request.base_selection,nativeBaseSelection(selected.selection))
    && rebind.request.authority_registry_sha256===valueSha(selected.registry)
    && same(rebind.result.native.rows,selected.patch.rows)
    && same(selected.ledger.current_targets,rebind.request.current_targets),
  'Accepted checkpoint current-base/native/target roster differs');
  const additions=[...selected.normalized.rows.values()].map(row=>{
    const target=rebind.request.current_targets.find(p=>p.target_id===row.target_id);
    demand(target && target.pixelIndex===row.pixelIndex, 'Accepted current target identity omitted');
    return {...row,base_geometry:target.geometry,base_geometry_sha256:target.geometry_sha256};
  });
  demand(same(operands.effective_additions?.candidate,additions), 'Accepted complete current primitives differ');
  coordinateCheck(certificate,{binding:certificate.binding,complete_owners:continuous.complete_owners,
    complete_sources:certificate.binding.sources.length},additions);
  demand(same(certificate.inputs.map(p=>p.source),certificate.binding.sources), 'Accepted complete source binding inventory differs');
  demand(same(certificate.binding.selection,selected.selection), 'Accepted certificate selected binding differs');
  completeRows(selected.patch.rows,manifest.size,certificate.entries.length);
  completeRows(rebind.request.current_rows,manifest.size,certificate.entries.length);
  completeRows(rebind.request.acquisition.predecessor_rows,manifest.size,certificate.entries.length);
  const plan=facts.transition_plan, ids=plan?.required_ids;
  demand(plan?.kind==='complete-selected-continuous-plan-v1' && plan.version===1
    && Array.isArray(ids) && same(ids,[...new Set(ids)].sort())
    && same(plan,continuousFacts.plan) && same(plan,operands.plan)
    && same(plan.source_bindings,continuous.source_binding) && same(ids,continuous.required_ids)
    && same(plan.changed_ids,strict.changed_location_ids)
    && same(plan.source_bindings.candidate,certificate.binding)
    && same(plan.source_bindings.baseline.selection,facts.baseline_selection),
  'Accepted complete two-vintage continuous scope differs');
  demand(operands.version===1 && operands.kind==='complete-selected-continuous-operands-v1'
    && same(Object.keys(operands.baseline).sort(),ids) && same(Object.keys(operands.candidate).sort(),ids),
  'Accepted whole source operand scope differs');
  const sourceCustody=continuousFacts.source_custody;
  keys(sourceCustody,'baseline,candidate,source_features_reused','Incomplete accepted whole-source custody');
  demand(sourceCustody.source_features_reused===true, 'Unsupported accepted source projection method');
  for (const vintage of ['baseline','candidate']) {
    const side=sourceCustody[vintage], planned=plan.source_paths[vintage];
    // Plans sort path sets; whole projections preserve certificate source order.
    // Join the complete unique roster, not these unrelated iteration orders.
    demand(Array.isArray(planned) && same(planned,[...new Set(planned)].sort())
      && same(side?.state_binding,plan.source_bindings[vintage]) && Array.isArray(side.inputs)
      && same(side.inputs.map(p=>p.path).sort(),planned) && Array.isArray(side.actual_inputs)
      && side.actual_inputs.length===side.inputs.length, 'Accepted complete source input custody differs');
    for (const input of side.inputs) {
      const actual=side.actual_inputs.filter(p=>p.path===input.source.path);
      demand(same(input,certificate.inputs.find(p=>p.path===input.path)) && actual.length===1
        && actual[0].whole_body_consumed===true && actual[0].mode===input.source.mode
        && actual[0].git_blob_oid===input.source.git_blob_oid && actual[0].bytes===input.source.bytes
        && actual[0].sha256===input.source.sha256, 'Accepted source body mode/OID/hash differs');
    }
  }
  const entries=new Map(certificate.entries.map(row=>[row[0],row]));
  const inverse=continuousFacts.inverse;
  demand(Array.isArray(inverse) && inverse.length===2*ids.length, 'Accepted complete source inverse omitted rows');
  for (const vintage of ['baseline','candidate']) {
    const rows=inverse.filter(row=>row.vintage===vintage);
    demand(same(rows.map(row=>row.id).sort(),ids), 'Accepted source inverse repeats/omits an owner');
    for (const row of rows) {
      const expected=entries.get(row.id), feature=operands[vintage][row.id];
      demand(expected && row.source===expected[4] && row.ordinal===expected[5]
        && row.whole_feature_sha256===expected[6] && row.geometry_sha256===expected[7]
        && row.whole_source_sha256===certificate.inputs.find(p=>p.path===row.source)?.whole_body_sha256
        && valueSha(feature)===row.whole_feature_sha256 && valueSha(feature.geometry)===row.geometry_sha256,
      'Accepted whole original feature/geometry inverse differs');
    }
  }
  const inventories=facts.actual_reader_inventories;
  keys(inventories,'baseline,candidate','Missing complete accepted reader inventories');
  for (const inventory of Object.values(inventories)) {
    demand(Array.isArray(inventory) && new Set(inventory.map(p=>p.commit+':'+p.path)).size===inventory.length,
      'Duplicate accepted reader inventory identity');
    for (const p of inventory) {
      demand(commit(p.commit) && safe(p.path) && ['100644','100755'].includes(p.mode)
        && /^[a-f0-9]{40}$/.test(p.git_blob_oid) && Number.isSafeInteger(p.bytes) && p.bytes>=0 && p.bytes<=FILE,
      'Incomplete accepted reader descriptor');
      if (p.whole_body_consumed) demand(p.whole_body_consumed===true && hash(p.sha256)
        && (p.decoded_bytes===undefined || Number.isSafeInteger(p.decoded_bytes) && p.decoded_bytes>=0
          && p.decoded_bytes<=FILE && hash(p.decoded_sha256)), 'Incomplete accepted consumed-body identity');
      else demand(p.whole_body_consumed===undefined && (p.sha256===undefined || hash(p.sha256)),
        'Ambiguous accepted body-consumption identity');
    }
  }
  keys(census,'version,kind,candidate_commit,candidate_selection,predecessor_paths,routes',
    'Unknown complete accepted scientific route census');
  demand(census.version===1 && census.kind==='selected-checkpoint-scientific-routes-v1'
    && census.candidate_commit===facts.candidate_commit && same(census.candidate_selection,selected.selection)
    && Array.isArray(census.predecessor_paths)
    && same(census.predecessor_paths,[...new Set(census.predecessor_paths)].sort())
    && census.predecessor_paths.every(safe), 'Accepted route predecessor/selection identity differs');
  const expectedPaths=scientificRoutePaths(census.predecessor_paths,inventories.candidate,manifest,certificate,selected.selection);
  demand(Array.isArray(census.routes) && same(census.routes.map(p=>p.path),expectedPaths)
    && census.routes.every(validRoute), 'Incomplete accepted present/absent route census');
  const policyPins=facts.executing_authority_pins;
  demand(Array.isArray(policyPins) && same(policyPins.map(p=>p.path),[PROGRAMME_POLICY,CATALOGUE])
    && policyPins.every(p=>p.commit===facts.executing_commit && p.whole_body_consumed===true),
  'Incomplete accepted executing policy custody');
  for (const p of policyPins) {
    pin(p);
    demand(same(p,inventories.baseline.find(q=>q.commit===p.commit && q.path===p.path)),
      'Accepted executing policy/catalogue pin differs from complete consumed inventory');
  }
  let priorPolicy;
  if (seedRoot) {
    const p=seedRoot.executing_policy;
    demand((p.decoded_bytes??p.bytes)===policyPins[0].bytes
      && (p.decoded_sha256??p.sha256)===policyPins[0].sha256,
    'Trusted seed policy alias differs from original executing policy');
    priorPolicy=validateSupportedProgrammeCatalogue(readBody(session,archiveReader,p));
  } else {
    const policy=facts.executing_policy;
    keys(policy,'pin,body','Missing exact accepted programme policy body');
    demand(same(policy.pin,policyPins[0]) && typeof policy.body==='string'
      && Buffer.byteLength(policy.body)===policy.pin.bytes, 'Accepted programme policy identity differs');
    charge(session,reader,8*policy.pin.bytes);
    demand(sha(Buffer.from(policy.body))===policy.pin.sha256, 'Accepted original programme policy body differs');
    priorPolicy=validateSupportedProgrammeCatalogue(JSON.parse(policy.body));
  }
  const currentPolicy=validateSupportedProgrammeCatalogue(readNamed(session,archiveReader,PROGRAMME_POLICY));
  for (const key of ['programs','current_rebind_migrations']) {
    const current=new Set(currentPolicy[key].map(valueSha));
    supported(priorPolicy[key].every(row=>current.has(valueSha(row))),
      'Trusted producer policy no longer preserves accepted eligibility');
  }
  supported(sameScientificRoutes(reader,census.routes), 'Accepted checkpoint input or routing alternative changed');
  const data={version:1,kind:'verified-selected-state-v1',selected_commit:reader.version,
    accepted_execution:seedRoot?{kind:'trusted-main-derived-selected-checkpoint-v1',checkpoint_id:seedRoot.id,
      accepted_head:seedRoot.accepted_head,execution_commit:facts.executing_commit,
      historical_selected_commit:facts.candidate_commit,trusted_catalogue_commit:trusted}
      :{kind:'accepted-selected-checkpoint-artifact-v1',accepted_head:receipt.merge_commit,
      reviewed_head:receipt.reviewed_head,request_id:receipt.request_id,pr_number:receipt.pr_number,
      execution_commit:facts.executing_commit,historical_selected_commit:facts.candidate_commit,
      source,report_sha256:source.report_sha256,trusted_catalogue_commit:trusted},
    selection:selected.selection,baseSelection:nativeBaseSelection(selected.selection),certificate,
    additions,ledger:selected.ledger,registry:selected.registry,patch:selected.patch,manifest};
  // accepted products already belong to the explicitly carried transport
  // allowance. Retain only newly acquired state/patch products, not a resolver.
  return finishCheckpoint(session,reader,{data,routes:census.routes,rebind,selected,root:null,carriedCertificate:true});
}

/** Exact already-consumed executing policy, for durable successor custody. */
export function checkpointExecutingPolicy({transition,budget}) {
  authenticateTransition({transition,budget});
  const session=transitions.get(transition);
  demand(session.executingPolicy, 'Missing consumed executing programme policy');
  return session.executingPolicy;
}

const scientificPath=name=>safe(name) && !/\.(mjs|py)$/.test(name)
  && !['requirements.txt','data/ownership-selection.json',LOCATOR].includes(name);
function scientificRoutePaths(predecessor,inventory,manifest,certificate,selection) {
  const paths=new Set(predecessor.filter(name=>name!==LOCATOR));
  for (const p of inventory) if (scientificPath(p.path)) paths.add(p.path);
  for (const p of manifest.parts) paths.add(path.posix.join(path.posix.dirname(selection.manifest_path),p.path));
  for (const input of certificate.inputs) { paths.add(input.path); paths.add(input.source.path); }
  return [...paths].sort();
}
function validRoute(p) {
  if (!p || !safe(p.path) || typeof p.tree!=='string') return false;
  return p.tree==='' || /^100(644|755) blob [a-f0-9]{40}\t/.test(p.tree)
    && p.tree.endsWith('\t'+p.path+'\0') && p.tree.split('\0').length===2;
}
/** Complete candidate routing, including inherited unchanged bodies/absences.
 * Caller arrays, changed-owner lists and locator JSON cannot restrict the scope. */
export function checkpointRouteCensus({transition,budget}) {
  const genuine=authenticateTransition({transition,budget});
  const before=states.get(genuine.baseline), after=states.get(genuine.candidate), {session,reader}=after;
  const predecessor=before.routes.map(p=>p.path);
  const names=scientificRoutePaths(predecessor,[...reader.inventory.values()],genuine.candidate.manifest,
    genuine.candidate.certificate,genuine.candidate.selection);
  // Every new ls-tree row is either absent or one ordinary file; reserve its
  // path, full identity, both route-name arrays and canonical output copies.
  const reserve=7*(names.reduce((n,name)=>n+2*Buffer.byteLength(name)+192,0)
    +valueBytes(genuine.candidate.selection).length+1024);
  beginFrame(session,reader,reserve);
  const old=new Map(before.routes.map(p=>[p.path,p.tree]));
  const routes=names.map(name=>({path:name,tree:old.has(name) && name!==PROGRAMME_POLICY
    ? old.get(name) : treeRoute(reader,name)}));
  demand(routes.every(validRoute), 'Unsupported scientific route entry');
  const result=freeze({version:1,kind:'selected-checkpoint-scientific-routes-v1',candidate_commit:reader.version,
    candidate_selection:genuine.candidate.selection,predecessor_paths:[...predecessor].sort(),routes});
  demand(7*valueBytes(result).length<=reserve, 'Complete route output exceeded prospective admission');
  retain(session,result); beginFrame(session,reader); return result;
}

function planFor(before,after) {
  const old = new Map(before.entries.map(row => [row[0],row])), next = new Map(after.entries.map(row => [row[0],row]));
  demand(old.size === next.size && [...old].every(([id,row]) => next.has(id) && same(row.slice(0,4),next.get(id).slice(0,4))),
    'Complete owner/index/parent roster changed');
  const changed = [...old].filter(([id,row]) => row[8] !== next.get(id)[8]).map(([id]) => id).sort();
  const needed = new Set(changed), pairs = new Set();
  const hits = (a,b) => a[0] <= b[2] && b[0] <= a[2] && a[1] <= b[3] && b[1] <= a[3];
  for (const id of changed) for (const certificate of [before,after]) for (const row of certificate.entries)
    if (row[0] !== id && row[9].some(a => [...old.get(id)[9],...next.get(id)[9]].some(b => hits(a,b)))) {
      needed.add(row[0]); pairs.add([id,row[0]].sort().join('\0'));
    }
  return freeze({version:1,kind:'complete-selected-continuous-plan-v1',changed_ids:changed,
    required_ids:[...needed].sort(),pairs:[...pairs].sort().map(p => p.split('\0')),
    source_paths:{baseline:[...new Set([...needed].map(id => old.get(id)[4]))].sort(),
      candidate:[...new Set([...needed].map(id => next.get(id)[4]))].sort()},
    source_bindings:{baseline:before.binding,candidate:after.binding},
    limits:['Coordinate exclusion only. All required full original polygons and unchanged strict coverage/overlap predicates remain mandatory.']});
}

/** Projects exact whole original features, never certificate boxes. Pass a prior
 * projection explicitly as reuse to share identical pointsets across vintages. */
export function projectSourceFeatures({state,ids,budget,reuse}) {
  const proof = getState(state,undefined,budget), {session,reader} = proof;
  demand(Array.isArray(ids) && new Set(ids).size === ids.length && ids.every(id => typeof id === 'string'), 'Incomplete source projection scope');
  const byId = new Map(state.certificate.entries.map(row => [row[0],row]));
  demand(ids.every(id => byId.has(id)), 'Foreign source projection owner');
  if (reuse) {
    const old = projections.get(reuse);
    demand(old?.session === session && old.kind === 'source' && same(old.ids,ids)
      && same(old.sourceIdentity,state.certificate.binding.sources), 'Foreign/incomplete source projection reuse');
    const result=freeze({...reuse,state_binding:state.certificate.binding});
    projections.set(result,old); return result;
  }
  const features = [], inverse = [], inputs = [], actualInputs = [], wanted = new Set(ids);
  const names = state.certificate.inputs.filter(input => ids.some(id => byId.get(id)[4] === input.path));
  for (const input of names) {
    beginFrame(session,reader);
    const collection = readBody(session,reader,input.source);
    demand(collection.type === 'FeatureCollection' && Array.isArray(collection.features), 'Missing whole source collection');
    const rows = state.certificate.entries.filter(row => row[4] === input.path);
    demand(rows.length === collection.features.length, 'Whole source/certificate denominator differs');
    for (const row of rows) if (wanted.has(row[0])) {
      const f = collection.features[row[5]];
      demand(f?.type === 'Feature' && (f.id ?? f.properties?.id) === row[0]
        && f.properties?.parent_id === row[2] && valueSha(f) === row[6] && valueSha(f.geometry) === row[7],
      'Complete source ordinal/owner/parent/feature/geometry differs');
      features.push(f); inverse.push({id:row[0],source:row[4],ordinal:row[5],whole_source_sha256:input.whole_body_sha256,
        whole_feature_sha256:row[6],geometry_sha256:row[7]});
      retain(session,f);
    }
    inputs.push(input);
    const {version}=resolvePin(reader,input.source); actualInputs.push({...reader.inventory.get(version+':'+input.source.path)});
  }
  demand(features.length === ids.length, 'Source projection omitted requested features');
  const result = freeze({features,inverse,inputs,custody:{actual_inputs:actualInputs},state_binding:state.certificate.binding,complete_phase_bytes:reader.used});
  projections.set(result,{session,kind:'source',ids:Object.freeze([...ids]),sourceIdentity:state.certificate.binding.sources});
  retain(session,{inverse,inputs,actualInputs}); beginFrame(session,reader);
  return result;
}

function nativeContext(proof) {
  const {session,reader} = proof, state = proof.state;
  if (proof.nativeContext) return proof.nativeContext;
  supported(state.manifest.native_asset_transport, 'Unsupported legacy native transport');
  beginFrame(session,reader);
  const image = new NativeAssetImage(reader,state.manifest,state.selection.manifest_path);
  retain(session,{index:image.index});
  proof.nativeContext = {image,table:null,inputInventory:new Map()}; return proof.nativeContext;
}
function nativeAsset(proof, pin, context) {
  const {session,reader} = proof, state = proof.state;
  const name = path.posix.join(path.posix.dirname(state.selection.manifest_path),pin.path);
  const ordinary = treeRoute(reader,name).length > 0;
  charge(session,reader,(ordinary ? 3 : 4)*pin.decoded_bytes+pin.bytes);
  const encoded = ordinary ? reader.read(name,{expected:pin.sha256,decoded:pin.decoded_bytes}) : context.image.logical(name,pin);
  demand(encoded.length === pin.bytes && sha(encoded) === pin.sha256, 'Whole native encoded body differs');
  const raw = gunzipSync(encoded,{maxOutputLength:pin.decoded_bytes});
  demand(raw.length === pin.decoded_bytes, 'Whole native decoded length differs');
  const words = unshuffleOwnershipBytes(raw,pin.words), canonical = Buffer.alloc(words.byteLength);
  for (let i=0;i<words.length;i++) canonical.writeUInt32LE(words[i],i*4);
  demand(sha(canonical) === pin.decoded_sha256, 'Whole native canonical words differ');
  for (const key of reader.charged.keys()) {
    const p=reader.inventory.get(key); if (p?.whole_body_consumed) context.inputInventory.set(key,{...p});
  }
  session.floor = reader.used; return words;
}
/** Complete native intervals. Genuine accepted whole rows are reused only under
 * identical manifest/domain/owner and all present/absent native routes. */
export function projectNativeRows({state,rows,budget}) {
  const proof = getState(state,undefined,budget), {session,reader} = proof;
  proof.state = state;
  demand(Array.isArray(rows) && rows.every((y,i) => Number.isSafeInteger(y) && y >= 0 && y < state.manifest.size && (!i || rows[i-1] < y)),
    'Duplicate, incomplete or foreign native row scope');
  const missing = rows.filter(y => !proof.nativeRows.has(y)), inputs = [];
  if (missing.length) {
    const context = nativeContext(proof), manifest = state.manifest;
    if (!context.table) {
      const pins = manifest.parts.filter(p => p.kind === 'rows');
      supported(pins.length === 1, 'Unsupported split native row table');
      beginFrame(session,reader); context.table = nativeAsset(proof,pins[0],context);
      demand(context.table.length === manifest.size*2, 'Incomplete whole native row table');
      let offset = 0;
      for (let y=0;y<manifest.size;y++) { demand(context.table[y*2] === offset, 'Native row partition omitted a range'); offset += context.table[y*2+1]; }
      demand(offset*2 === manifest.runWords, 'Native row partition omits complete runs');
      session.residentBytes += context.table.byteLength; inputs.push(pins[0]);
    }
    const table = context.table, groups = new Map();
    for (const y of missing) {
      const start = table[y*2]*2, end = start+table[y*2+1]*2;
      const parts = manifest.parts.filter(p => p.kind === 'runs' && start < p.offset+p.words && p.offset < end), key = valueSha(parts);
      if (!groups.has(key)) groups.set(key,{parts,rows:[]}); groups.get(key).rows.push({y,start,end});
    }
    for (const group of groups.values()) {
      beginFrame(session,reader,group.rows.reduce((n,r) => n+table[r.y*2+1]*48+128,0));
      const bodies = new Map(group.parts.map(p => [p.path,nativeAsset(proof,p,context)]));
      for (const {y,start,end} of group.rows) {
        const runs = [];
        for (const part of group.parts) for (let i=Math.max(start,part.offset);i<Math.min(end,part.offset+part.words);i+=2) {
          const words = bodies.get(part.path), a = words[i-part.offset], b = words[i-part.offset+1], bits = manifest.coordinateBits, mask = 2**bits-1;
          runs.push([a&mask,(b&mask)+1,(a>>>bits)+(b>>>bits)*2**(32-bits)]);
        }
        demand(runs.length === table[y*2+1], 'Incomplete containing native interval range');
        const row = freeze({y,runs}); completeRows([row],manifest.size,state.certificate.entries.length);
        proof.nativeRows.set(y,row); retain(session,row);
      }
      inputs.push(...group.parts);
    }
  }
  const result = freeze({rows:rows.map(y => proof.nativeRows.get(y)),requested_rows:rows,
    native_binding:{base_selection:state.baseSelection,manifest_sha256:state.selection.sha256,
      owners_sha256:state.certificate.binding.owners_sha256},inputs,
    custody:{accepted_checkpoint:state.accepted_execution,new_whole_inputs:[...(proof.nativeContext?.inputInventory.values()??[])],
      retained_native_inputs:proof.rebind.request.acquisition.native_inputs},
    reused_rows:rows.filter(y => !missing.includes(y)),acquired_rows:missing,complete_phase_bytes:reader.used});
  projections.set(result,{session,kind:'native',rows}); retain(session,{requested_rows:rows,inputs});
  beginFrame(session,reader); return result;
}

export function releaseCheckpoint(state) {
  const proof = states.get(state); demand(proof && !proof.session.closed, 'Checkpoint already released or foreign');
  const session = proof.session; session.closed = true;
  for (const handle of session.handles) states.delete(handle);
  session.handles.clear(); session.executingPolicy=null;
}

function mergePatchRows(patches, size, ownerCount) {
  const byRow = new Map();
  for (const patch of patches) {
    completeRows(patch.rows,size,ownerCount);
    for (const row of patch.rows) { const runs = byRow.get(row.y) ?? []; runs.push(...row.runs); byRow.set(row.y,runs); }
  }
  return [...byRow].sort((a,b) => a[0]-b[0]).map(([y,runs]) => {
    const merged = [];
    for (const r of [...runs].sort((a,b) => a[0]-b[0] || a[1]-b[1] || a[2]-b[2])) {
      const last = merged.at(-1);
      demand(!last || r[0] >= last[1] || r[2] === last[2], 'Native delta reassigns an existing owner');
      if (last && r[2] === last[2] && r[0] <= last[1]) last[1] = Math.max(last[1],r[1]);
      else merged.push([...r]);
    }
    return {y,runs:merged};
  });
}
function appendAuthority(session, reader, entry) {
  // The original helper owns its own sequential temporary frames. Its metadata
  // includes the entire joint caller state, never a fresh independent budget.
  const child = new ImmutableReader(reader.repo,reader.version,{runtimeBytes:reader.runtimeBytes,
    executionBytes:reader.executionBytes,metadataBytes:session.initialMetadata+session.budget.carriedBytes+session.residentBytes,
    outputBytes:session.initialOutput,gitExecutable:reader.gitExecutable,budget:reader.budget,allowance:reader.allowance});
  child.inventory=reader.inventory; // retain actual appended-producer inputs without reopening them
  const proof = readRetainedRegistryAuthority(child,entry);
  session.floor = reader.used;
  return {entry,patches:proof.native_proof.native_patches,ledger:proof.original_ledger,
    contract:proof.native_proof.native_contract,source_scope_ids:proof.source_scope_ids};
}
function expectedNativeAcquisition(proof, neededRows) {
  const {session,reader,state} = proof, prior = proof.rebind.request.acquisition;
  const oldNeeded = [...new Set(proof.rebind.request.current_rows.map(p => p.y).concat(prior.predecessor_rows.map(p => p.y)))].sort((a,b) => a-b);
  if (same(neededRows,oldNeeded)) return {inputs:prior.native_inputs,
    scopes:proof.rebind.facts.acquisition_phases.filter(p => p.kind.startsWith('complete-current-native')).map(({complete_phase_bytes,descriptors,...scope}) => scope)};
  const context = nativeContext(proof), table = context.table;
  demand(table, 'New native row projection omitted the whole row table');
  const groups = new Map(), manifest = state.manifest;
  for (const y of neededRows) {
    const start=table[y*2]*2,end=start+table[y*2+1]*2;
    const parts=manifest.parts.filter(p => p.kind==='runs' && start<p.offset+p.words && p.offset<end), key=valueSha(parts);
    if (!groups.has(key)) groups.set(key,{parts,rows:[]}); groups.get(key).rows.push(y);
  }
  const pins = new Map(manifest.parts.filter(p => p.kind==='rows').map(p => [p.path,p]));
  for (const group of groups.values()) for (const p of group.parts) pins.set(p.path,p);
  const bodyIdentity = p => { const {commit,...identity}=p; return identity; };
  const inputs=[...pins.values()].map(asset => {
    const name=path.posix.join(path.posix.dirname(state.selection.manifest_path),asset.path);
    let custody;
    if (treeRoute(reader,name)) {
      const p=reader.descriptor(name);
      custody={kind:'ordinary-native-body',pin:{path:p.path,mode:p.mode,git_blob_oid:p.git_blob_oid,bytes:p.bytes,sha256:asset.sha256}};
    } else {
      const member=context.image.index.files.find(p => p.path===asset.path);
      demand(member,'Missing complete native containing member');
      custody={kind:'selected-native-transport',index:manifest.native_asset_transport.index,member,
        fragments:context.image.index.parts.filter(p => p.offset<member.offset+member.bytes && member.offset<p.offset+p.decoded_bytes)
          .map(p => ({...p,pin:bodyIdentity(reader.descriptor(context.image.directory+'/'+p.path))}))};
    }
    return {logical_path:name,asset,custody};
  });
  session.floor=reader.used;
  return {inputs,scopes:[{kind:'complete-current-native-row-table'},...[...groups.values()].map(g => ({kind:'complete-current-native-window-group',rows:g.rows,parts:g.parts.map(p => p.path)}))]};
}
function authenticateProducerExecution(session,reader,products,bodyPins) {
  const {certificate,request,facts,publication,operating}=products;
  const code=CURRENT_REBIND_CODE.map(name => { const p=reader.descriptor(name,session.trusted); return {path:name,bytes:p.bytes,sha256:sha(reader.read(name,{version:session.trusted}))}; });
  const historical=CURRENT_REBIND_CODE.map(name => { const p=reader.descriptor(name,certificate.execution_commit); return {path:name,bytes:p.bytes,sha256:sha(reader.read(name,{version:certificate.execution_commit}))}; });
  const expectedCode=compatibleCurrentRebindCode(certificate.execution_commit,code,historical,reader);
  demand(same(request.executed_code,expectedCode),'Unknown complete current producer programme');
  // Reuse the accepted producer's exact required/optional bounded contract.
  // Its complete limits remain bound to the authenticated original issued plan.
  validateCurrentRebindLimits(request.limits);
  demand(request.limits.output_bytes<=FILE, 'Invalid original producer resource contract');
  keys(facts,'version,kind,execution_commit,request_sha256,result_sha256,complete_phase_bytes,descriptors,acquisition_sha256,acquisition_phases','Unknown producer facts');
  keys(publication,'version,kind,execution_commit,request_sha256,outputs','Unknown producer publication');
  keys(operating,'version,kind,execution_commit,request_sha256,publication_sha256,exit_code,signal,owned_processes_remaining,lifetime_rss_bytes,elapsed_seconds,execution_custody','Unknown producer operating proof');
  const custody={};
  for (const name of ['code_source','terminal','stderr','stdout','issued_plan'])
    custody[name]=readBody(session,reader,operating.execution_custody[name],{json:false});
  verifyCurrentRebindExecution({request,operating,expectedCode,custody:{...custody,result_sha256:bodyPins.result.sha256}});
}
function qualifyProjectedRebind(proof, selected, authorities, products) {
  const {session,reader,state}=proof, {certificate,request,facts,publication,operating,result}=products;
  const base=state.baseSelection, originalRows=[...selected.normalized.rows.values()];
  const originalPatches=selected.registry.entries.flatMap(entry => authorities.get(entry.authority_sha256).patches);
  const bodyPins=Object.fromEntries(['request','facts','publication','operating','result'].map(name => [name,certificate[name]]));
  for (const [name,body] of Object.entries({request,facts,publication,operating,result}))
    demand(valueSha(body)===bodyPins[name].sha256 && valueBytes(body).length===bodyPins[name].bytes,'Whole canonical producer output differs');
  keys(request,'version,kind,execution_commit,executed_code,base_selection,authority_registry_sha256,original_rows,original_patch_sha256s,current_targets,current_rows,acquisition,execution,size,limits','Unknown current producer request');
  demand(certificate.version===1 && certificate.kind==='qualified-native-additive-current-bank-rebind-v1'
    && request.version===1 && request.kind==='issued-native-additive-current-bank-rebind-v1'
    && certificate.execution_commit===request.execution_commit && same(certificate.base_selection,base)
    && certificate.authority_registry_sha256===valueSha(selected.registry)
    && same(request.base_selection,base) && request.authority_registry_sha256===valueSha(selected.registry)
    && request.size===state.manifest.size && same(request.original_rows,originalRows)
    && same(request.original_patch_sha256s,originalPatches.map(valueSha)), 'Producer rebind has stale base, omitted original scope or different authority');
  authenticateProducerExecution(session,reader,products,bodyPins);
  keys(request.acquisition,'version,kind,target_sources,source_inputs,native_inputs,predecessor_proof,predecessor_rows,manifest_sha256','Unknown producer acquisition schema');
  demand(same(request.acquisition.predecessor_proof,proof.rebind.request.acquisition.predecessor_proof)
    && same(request.acquisition.predecessor_rows,proof.rebind.request.acquisition.predecessor_rows), 'Changed original predecessor custody/rows');
  const owners=new Map(state.certificate.entries.map(row => [row[0],row]));
  const targets=[...new Set(originalRows.map(row => row.target_id))].sort();
  const newTargets=targets.filter(id => !proof.sourceTargets.has(id));
  const projected=projectSourceFeatures({state,ids:newTargets,budget:session.budget});
  for (const feature of projected.features) {
    const id=feature.id??feature.properties.id,row=owners.get(id);
    proof.sourceTargets.set(id,freeze({target_id:id,pixelIndex:row[1],geometry:feature.geometry,geometry_sha256:row[7]}));
  }
  const currentTargets=targets.map(id => proof.sourceTargets.get(id));
  const targetSources=targets.map(id => ({target_id:id,path:owners.get(id)[4]}));
  // The issued target roster follows original first-appearance order, so compare
  // it as a complete unique map; preserve its genuine original order in custody.
  demand(Array.isArray(request.acquisition.target_sources) && request.acquisition.target_sources.length===targets.length
    && new Set(request.acquisition.target_sources.map(p => p.target_id)).size===targets.length
    && request.acquisition.target_sources.every(p => same(p,targetSources.find(q => q.target_id===p.target_id))),
  'Producer omitted or rebound complete target source roster');
  const sourceInputs=state.certificate.inputs.filter(p => targetSources.some(t => t.path===p.path));
  const candidateRows=[...new Set(originalPatches.flatMap(p => p.rows.map(row => row.y)))].sort((a,b) => a-b);
  const needed=[...new Set(candidateRows.concat(request.acquisition.predecessor_rows.map(row => row.y)))].sort((a,b) => a-b);
  const native=projectNativeRows({state,rows:needed,budget:session.budget});
  const currentRows=native.rows.filter(row => candidateRows.includes(row.y));
  const nativeAcquisition=expectedNativeAcquisition(proof,needed);
  const acquisition={version:1,kind:'complete-selected-rebind-inputs-v1',target_sources:request.acquisition.target_sources,
    source_inputs:sourceInputs,native_inputs:nativeAcquisition.inputs,predecessor_proof:request.acquisition.predecessor_proof,
    predecessor_rows:request.acquisition.predecessor_rows,manifest_sha256:valueSha(state.manifest)};
  demand(same(currentRebindAcquisitionIdentity(acquisition),currentRebindAcquisitionIdentity(request.acquisition))
    && same(currentTargets,request.current_targets) && same(currentRows,request.current_rows),
  'Producer operands differ from complete retained/projected original sources or native intervals');
  const expected=currentRebindResult({baseSelection:base,registry:selected.registry,originalRows,originalPatches,
    currentTargets,currentRows,size:state.manifest.size});
  demand(same(result,expected),'Producer result differs from actual complete delta operands');
  const scopes=sourceInputs.map(p => ({kind:'complete-current-target-source',path:p.path}));
  if (request.acquisition.predecessor_proof) scopes.push({kind:'complete-qualified-arctic-predecessor',
    path:request.acquisition.predecessor_proof.path,sha256:request.acquisition.predecessor_proof.sha256});
  scopes.push(...nativeAcquisition.scopes);
  demand(Array.isArray(facts.acquisition_phases) && facts.acquisition_phases.length===scopes.length
    && facts.acquisition_phases.every((p,i) => { const {complete_phase_bytes,descriptors,...scope}=p;
      return same(scope,scopes[i]) && Number.isSafeInteger(complete_phase_bytes) && complete_phase_bytes>0
        && complete_phase_bytes<=request.limits.complete_phase_bytes && Number.isSafeInteger(descriptors)
        && descriptors>0 && descriptors<=request.limits.descriptors; }), 'Original producer complete acquisition scope or admission differs');
  demand(facts.version===1 && facts.kind==='native-additive-current-bank-rebind-facts-v1'
    && facts.execution_commit===request.execution_commit && facts.request_sha256===bodyPins.request.sha256
    && facts.result_sha256===bodyPins.result.sha256 && facts.acquisition_sha256===valueSha(request.acquisition)
    && Number.isSafeInteger(facts.complete_phase_bytes) && facts.complete_phase_bytes>0
    && facts.complete_phase_bytes<=request.limits.complete_phase_bytes && Number.isSafeInteger(facts.descriptors)
    && facts.descriptors>0 && facts.descriptors<=request.limits.descriptors,
  'Original producer facts are not bound to actual complete products');
  demand(publication.version===1 && publication.kind==='native-additive-current-bank-rebind-publication-v1'
    && publication.execution_commit===request.execution_commit && publication.request_sha256===bodyPins.request.sha256
    && same(publication.outputs,{facts:{path:'facts.json',bytes:bodyPins.facts.bytes,sha256:bodyPins.facts.sha256},
      result:{path:'result.json',bytes:bodyPins.result.bytes,sha256:bodyPins.result.sha256}}), 'Producer whole output publication differs');
  demand(operating.version===1 && operating.kind==='native-additive-current-bank-rebind-operating-v1'
    && operating.execution_commit===request.execution_commit && operating.exit_code===0 && operating.signal===null
    && Array.isArray(operating.owned_processes_remaining) && operating.owned_processes_remaining.length===0
    && operating.request_sha256===bodyPins.request.sha256 && operating.publication_sha256===bodyPins.publication.sha256
    && bodyPins.result.bytes<=request.limits.output_bytes, 'Producer external operating/output binding differs');
  return {currentTargets,originalRows,native};
}

/** Exhaustive actual append-only transition. Never reacquires a full selection.
 * A valid baseline remains usable when an unsupported candidate needs cold work. */
export function qualifyTransition({state,reader,budget}) {
  const baseProof=getState(state,reader,budget), {session}=baseProof;
  try {
    beginFrame(session,reader);
    const selected=readSelection(session,reader);
    supported(same(nativeBaseSelection(selected.selection),state.baseSelection), 'Selected native/source/domain/owner base changed');
    supported(sameScientificRoutes(reader,baseProof.routes), 'Selected input or present/absent route changed');
    for (const role of ['base_manifest','owner_roster'])
      supported(same(selected.sidecar.logical_asset_map[role],baseProof.selected.sidecar.logical_asset_map[role]), 'Selected original manifest/owner alias changed');
    demand(same(selected.ledger.parent_inventory,state.ledger.parent_inventory), 'Complete original source/scope denominator changed');
    const oldRows=new Map(state.ledger.rows.map(row => [row.component_id,row]));
    for (const row of state.ledger.rows) demand(same(row,selected.ledger.rows.find(p => p.component_id===row.component_id)),
      'Old complete ledger primitive, exception or native assignment removed/rebound');
    const authorities=new Map(baseProof.oldAuthorities);
    for (const entry of state.registry.entries) demand(same(entry,selected.registry.entries.find(p => p.authority_sha256===entry.authority_sha256)),
      'Old original authority removed/rebound');
    const addedEntries=selected.registry.entries.filter(entry => !authorities.has(entry.authority_sha256));
    retain(session,selected);
    const expectedAdded=new Map();
    for (const entry of addedEntries) {
      demand(entry.policy_id==='retained-source-literal-additions' && entry.policy_version===1, 'Unsupported appended source policy');
      const proof=appendAuthority(session,reader,entry); retain(session,proof); authorities.set(entry.authority_sha256,proof);
      const contract=Object.fromEntries(['size','coordinateBits','method','native_latitudes','hierarchy_sha256','original_assets'].map(k => [k,state.manifest[k]]));
      demand(same(proof.contract,contract) && same(proof.ledger.parent_inventory,state.ledger.parent_inventory),
        'Appended producer changed native contract or complete original source denominator');
      for (const original of proof.ledger.rows) {
        demand(!oldRows.has(original.component_id) && !expectedAdded.has(original.component_id), 'Appended producer repeats original component');
        expectedAdded.set(original.component_id,{original,entry});
      }
    }
    const addedRows=selected.ledger.rows.filter(row => !oldRows.has(row.component_id));
    demand(addedRows.length===expectedAdded.size,'Candidate omitted/invented complete appended ledger scope');
    for (const row of addedRows) {
      const expected=expectedAdded.get(row.component_id), {authority_sha256,rule_sha256,...literal}=row;
      demand(expected && authority_sha256===expected.entry.authority_sha256
        && (rule_sha256===undefined || rule_sha256===expected.entry.rule_sha256) && same(literal,expected.original),
      'Candidate changed original appended primitive or exception');
    }
    const patches=selected.registry.entries.flatMap(entry => authorities.get(entry.authority_sha256).patches);
    const expectedPatch=mergePatchRows(patches,state.manifest.size,state.certificate.entries.length);
    demand(same(selected.patch.rows,expectedPatch),'Candidate patch omitted, invented or reassigned original native intervals');
    for (const entry of addedEntries) for (const row of authorities.get(entry.authority_sha256).patches.flatMap(p => p.rows))
      for (const run of row.runs) for (const old of state.patch.rows.find(p => p.y===row.y)?.runs??[])
        demand(run[1]<=old[0] || run[0]>=old[1], 'New native assignment overlaps a previously selected owner');
    const proof={...baseProof,reader,state,nativeRows:new Map(baseProof.nativeRows),sourceTargets:new Map(baseProof.sourceTargets),nativeContext:null};
    // Projection authority is still the genuine baseline, while its operands
    // use this candidate's identical base routes. No SelectedSnapshot is forged.
    const operandState=newState(session,{...state,selected_commit:reader.version},{...proof});
    const operandProof=states.get(operandState); operandProof.state=operandState;
    let currentTargets;
    if (addedEntries.length===0 && same(selected.registry,state.registry)
      && same(selected.ledger.current_rebind,state.ledger.current_rebind)) currentTargets=baseProof.rebind.request.current_targets;
    else {
      const products=rebindProducts(session,reader,selected.ledger); retain(session,products);
      currentTargets=qualifyProjectedRebind(operandProof,selected,authorities,products).currentTargets;
      operandProof.rebind=products;
    }
    demand(same(selected.ledger.current_targets,currentTargets), 'Ledger complete current target roster differs from qualified operands');
    const additions=[...selected.normalized.rows.values()].map(row => {
      const target=currentTargets.find(p => p.target_id===row.target_id);
      demand(target && target.pixelIndex===row.pixelIndex,'Appended owner identity or actual base geometry missing');
      return {...row,base_geometry:target.geometry,base_geometry_sha256:target.geometry_sha256};
    });
    demand(selected.envelope.effective_reference.footprints_sha256===valueSha({domain:'worldatlas-effective-native-footprints:v2',
      base_reference:selected.envelope.base_reference,authority_registry_sha256:valueSha(selected.registry),
      ledger_sha256:selected.sidecar.logical_asset_map.ledger.sha256,components:[...selected.normalized.rows.values()]}),
    'Candidate effective release does not bind the complete ledger/authority set');
    demand(same(selected.envelope.base_reference,baseProof.selected.envelope.base_reference)
      && selected.envelope.effective_reference.hierarchy_sha256===selected.envelope.base_reference.hierarchy_sha256,
    'Candidate silently changes complete base release or hierarchy');
    const {certificate,plan}=deriveCoordinateDelta({certificate:state.certificate,oldAdditions:state.additions,additions,selection:selected.selection});
    const candidate=newState(session,{...state,selected_commit:reader.version,selection:selected.selection,certificate,
      additions,ledger:selected.ledger,registry:selected.registry,patch:selected.patch},
      {...operandProof,selected,oldAuthorities:authorities});
    const changedIds=new Set(plan.changed_ids);
    const oldNative=new Map(state.patch.rows.map(row => [row.y,row.runs])), newNative=new Map(selected.patch.rows.map(row => [row.y,row.runs]));
    const changedNativeRows=[...new Set([...oldNative.keys(),...newNative.keys()])].sort((a,b) => a-b)
      .filter(y => !same(oldNative.get(y)??[],newNative.get(y)??[]));
    retain(session,{entries:certificate.entries.filter(row => changedIds.has(row[0])),additions,plan,changedNativeRows});
    const transition=freeze({available:true,baseline:state,candidate,changedIds:plan.changed_ids,changedNativeRows,plan});
    transitions.set(transition,session); return transition;
  } catch (error) {
    if (error.reuseUnavailable) return unavailable(error.message,state);
    throw error;
  }
}

/** Consumer admission of the complete internally derived two-vintage scope.
 * Genuine state handles inside a caller-created wrapper do not authenticate its
 * changed-owner/neighbor plan. This is constant-time, not a repeated scan. */
export function authenticateTransition({transition,budget}) {
  const session=transitions.get(transition);
  demand(session && !session.closed, 'Missing private qualified selected transition');
  demand(getState(transition.baseline,undefined,budget).session===session
    && getState(transition.candidate,undefined,budget).session===session,
  'Foreign transition state or invocation');
  return transition;
}

// Pure arithmetic only. This function cannot mint a checkpoint, projector or
// selected certificate capability; callers must still qualify all operands.
export function deriveCoordinateDelta({certificate,oldAdditions,additions,selection}) {
  const oldById=new Map(oldAdditions.map(row => [row.component_id,row]));
  demand(oldById.size===oldAdditions.length && new Set(additions.map(row => row.component_id)).size===additions.length,
    'Duplicate complete primitive identity');
  for (const row of oldAdditions) demand(same(row,additions.find(p => p.component_id===row.component_id)),
    'Old effective primitive/base geometry changed');
  const rows=new Map(certificate.entries.map(row => [row[0],row]));
  for (const row of additions) demand(rows.has(row.target_id) && row.pixelIndex===rows.get(row.target_id)[1]
    && row.base_geometry_sha256===rows.get(row.target_id)[7] && row.geometry_sha256===valueSha(row.geometry),
  'Appended primitive targets a stale base, changed geometry or different owner');
  const changedIds=new Set(additions.filter(row => !oldById.has(row.component_id)).map(row => row.target_id));
  const entries=certificate.entries.map(row => {
    if (!changedIds.has(row[0])) return row;
    const all=additions.filter(p => p.target_id===row[0]), added=all.filter(p => !oldById.has(p.component_id));
    const boxes=[...row[9],...added.flatMap(p => coordinateBounds(p.geometry))];
    const next=[...row]; next[8]=valueSha({base_geometry_sha256:row[7],additions:all});
    next[9]=[boxes.reduce((a,b) => [Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.max(a[2],b[2]),Math.max(a[3],b[3])])];
    return next;
  });
  const result={...certificate,binding:{...certificate.binding,selection},entries};
  return freeze({certificate:result,plan:planFor(certificate,result)});
}

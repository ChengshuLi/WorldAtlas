// Invocation-scoped reuse of accepted selected products. Candidate JSON is data.
// Trust enters only through the catalogue in the executing reviewed checkout.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import os from 'node:os';
import {admitNativePatchStore,admitNativeLedgerStore,admitNativeEnvelopeStore,admitNativeMetadataStore,decodedNativeChunks,authenticatedDecodedNativeChunks} from '../../../scripts/native-patch-store.mjs';
import {nativeSequence,isNativeSequence,nativeRowAt} from '../../../src/native-grid.js';
import {openNativeWordStore} from '../../../scripts/native-word-store.mjs';
import {ImmutableReader, NativeAssetImage, decodeVisibilityLatitudes,
  loadBaseSelection, selectedGeometrySourceAlias, selectedReferenceOwners} from '../../../scripts/check-effective-geographic-regression.mjs';
import {repairComponentKey, nativeOnlyComponent} from '../../../src/native-grid.js';
import {unshuffleOwnershipBytes} from '../../../src/ownership-codec.js';
import {valueBytes, valueSha, coordinateBounds, nativeBaseSelection,
  normaliseRetainedRepairLedger, repairRowsIndex, repairIndexValues, readRetainedRegistryAuthority, readRegistryAuthorityInputs, verifyCompletedSourceTargetNativeAuthority, validateSupportedProgrammeCatalogue,
  CURRENT_REBIND_CODE, verifyCurrentRebindExecution,
  currentRebindResult, currentRebindAcquisitionIdentity, retainedArcticNativeRows} from './selected-neighbor-prevention.mjs';

const ROOT = fileURLToPath(new URL('../../../', import.meta.url));
const MODULE = 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
const CATALOGUE = 'coordination/engineering/selected-checkpoint-reuse-20261012/accepted-checkpoints.json';
const FIELDS = ['id','index','parent_id','parent_index','source','ordinal','whole_feature_sha256','geometry_sha256','effective_geometry_sha256','boxes'];
const states = new WeakMap(), projections = new WeakMap(), transitions = new WeakMap();
const LOCATOR = 'data/selected-checkpoint.json';
const ACCEPTED_CODE = ['scripts/accepted-selected-checkpoint.mjs','scripts/check-handoff-scope.mjs',
  'scripts/evidence-policy.mjs','scripts/evidence-quality.mjs','scripts/geographic-report-artifact.mjs',
  'scripts/github-quota.mjs','scripts/github-snapshots.mjs','scripts/integration-proof.mjs',
  'scripts/issue-claim-contract.mjs','scripts/research-import-gate.mjs',
  'scripts/worker-result.mjs','src/regional-import-gate.js'];
const demand = (ok, message) => { if (!ok) throw Error(message); };
const sha = body => createHash('sha256').update(body).digest('hex');
// Policy is rooted in the executing trusted checkout, independently of the
// selected scientific vintage. Keep its archived census entry, but do not make
// accepted programme additions look like changed source/native input bytes.
const PROGRAMME_POLICY = 'coordination/engineering/selected-geography-effective-prevention-20261009/supported-programs.json';
// A certificate names both the logical source and the physical body it consumed.
// An exact encoded override does not read the shadowed ordinary logical file.
// Keep its archived census row, but do not replay accepted science for that inert
// route. Any actual physical use, including by another authority, keeps it bound.
function maskedLogicalSources(certificate,physicalPaths) {
  const physical = new Set([...physicalPaths,...certificate.inputs.map(input => input.source.path)]);
  return new Set(certificate.inputs.filter(input => input.source.kind === 'selected-exact-encoded-override'
    && input.source.logical_path === input.path && input.source.path !== input.path
    && !physical.has(input.path)).map(input => input.path));
}
function bindPhysicalLogicalSources(reader,certificate,inventory) {
  const logical = new Set(certificate.inputs.filter(input => input.source.kind === 'selected-exact-encoded-override'
    && input.source.logical_path === input.path && input.source.path !== input.path).map(input => input.path));
  // An inherited physical use must remain visible in the successor's existing
  // actual descriptor inventory, even though its accepted body is not reread.
  // Otherwise a later derived checkpoint could mistake that path for inert.
  for (const p of inventory) if (logical.has(p.path)) {
    let version = p.commit;
    try { reader.git('--no-lazy-fetch','cat-file','-e',version+'^{commit}'); } catch { version = reader.version; }
    const actual = reader.descriptor(p.path,version);
    demand(actual.mode === p.mode && actual.git_blob_oid === p.git_blob_oid && actual.bytes === p.bytes,
      'Accepted physical logical-source identity changed');
  }
  return new Set(inventory.map(p => p.path));
}
const sameScientificRoutes = (reader,routes,executablePaths,masked = new Set()) => routes.every(p => p.path === PROGRAMME_POLICY
  || executablePaths.has(p.path) || masked.has(p.path) || reader.treeRoute(p.path) === p.tree);
const currentMaskedRoutes = (reader,routes,masked) => {
  const current=new Map(routes.map(p=>[p.path,p]));
  for (const name of masked) current.set(name,{path:name,tree:reader.treeRoute(name)});
  return [...current.values()].sort((a,b)=>a.path.localeCompare(b.path));
};
// Older route censuses excluded .mjs/.py but also retained executable .js.
// Keep the complete archived census. Identify code by its authenticated executed
// role and whole bytes, never by an extension, changed-file list or new hashes.
function acceptedExecutablePaths(session,reader,routes,inventory,facts,policy,rebind) {
  const roles=[...facts.execution_code,...policy.programs.flatMap(p=>[...p.source_executed_code,...p.native_executed_code]),
    ...policy.current_rebind_migrations.flatMap(p=>[...p.historical_code,...p.current_code])];
  const identity=p=>valueSha([p.path,p.bytes,p.sha256]);
  const bodies=new Set(roles.map(identity));
  const paths=new Set(inventory.filter(p=>hash(p.sha256)&&bodies.has(identity(p))).map(p=>p.path));
  // Derived inventories omit historical code bodies that the accepted parent
  // reused. Recover only the exact archived route at an existing policy origin;
  // reading it records truthful historical custody, never a fresh execution.
  const recorded=new Set(inventory.map(p=>p.path));
  const inherited=new Map(routes.filter(p=>!recorded.has(p.path)).map(p=>[p.path,p.tree]));
  for (const p of rebind.request.executed_code??[]) {
    if (!inherited.has(p.path) || !bodies.has(identity(p))) continue;
    const version=rebind.certificate.execution_commit;
    demand(rebind.request.execution_commit===version,'Accepted rebind execution identity differs');
    const actual=reader.descriptor(p.path,version);
    demand(`${actual.mode} blob ${actual.git_blob_oid}\t${p.path}\0`===inherited.get(p.path)
      && actual.bytes===p.bytes,'Accepted inherited code route differs');
    reader.read(p.path,{version,expected:p.sha256});
    paths.add(p.path);
  }
  return paths;
}
const same = (a,b) => a === undefined || b === undefined ? a === b : valueSha(a) === valueSha(b);
const hash = x => typeof x === 'string' && /^[a-f0-9]{64}$/.test(x);
const commit = x => typeof x === 'string' && /^[a-f0-9]{40}$/.test(x);
const safe = x => typeof x === 'string' && x.length > 0 && !x.includes('\\') && !x.includes('\0') && !path.posix.isAbsolute(x) && x.split('/').every(p => p && p !== '.' && p !== '..');
const freeze = x => { if (x && typeof x === 'object' && !Object.isFrozen(x)) { Object.values(x).forEach(freeze); Object.freeze(x); } return x; };
const keys = (x, expected, message) => demand(x && same(Object.keys(x).sort(), expected.split(',').sort()), message);
const unavailable = (reason, baseline) => Object.freeze({available:false, reason, cold:baseline ? 'candidate' : 'baseline-and-candidate', ...(baseline ? {baseline} : {})});
const supported = (ok, message) => { if (!ok) { const error = Error(message); error.reuseUnavailable = true; throw error; } };

// Qualified handles and projections belong to one live immutable-reader invocation.
function sessionCheck(reader, session) {
  demand(reader instanceof ImmutableReader, 'Checkpoint requires an immutable reader');
  if (session) demand(!session.closed && reader.invocation === session.invocation
    && reader.repo === session.repo, 'Foreign or expired checkpoint invocation');
}
function pin(p) {
  demand(p && commit(p.commit) && safe(p.path) && ['100644','100755'].includes(p.mode)
    && /^[a-f0-9]{40}$/.test(p.git_blob_oid) && Number.isSafeInteger(p.bytes)
    && p.bytes >= 0 && hash(p.sha256), 'Incomplete immutable checkpoint pin');
  if (p.decoded_bytes !== undefined) demand(Number.isSafeInteger(p.decoded_bytes)
    && p.decoded_bytes > 0 && hash(p.decoded_sha256),
  'Incomplete whole decoded checkpoint pin');
}
function resolvePin(reader, p) {
  pin(p);
  let version = p.commit;
  try { reader.git('--no-lazy-fetch','cat-file','-e',version+'^{commit}'); } catch { version = reader.version; }
  const actual = reader.descriptor(p.path, version);
  demand(actual.mode === p.mode && actual.git_blob_oid === p.git_blob_oid && actual.bytes === p.bytes,
    'Checkpoint whole mode/OID/size or historical alias changed: '+p.path);
  return {actual, version};
}
function readBody(session, reader, p, {json = true} = {}) {
  const {version} = resolvePin(reader, p);

  const encoded = reader.read(p.path, {version, expected:p.sha256});
  return decodeBody(p,encoded,{json});
}
function readBodies(session,reader,pins) {
  pins.forEach(pin);
  const values=[];
  for(let start=0;start<pins.length;){
    let end=start,bytes=0;
    // Byte-sized transport batches, not a limit on admitted files or scope.
    do{bytes+=pins[end++].bytes;}while(end<pins.length&&bytes+pins[end].bytes<=1024*1024);
    const group=pins.slice(start,end),bodies=reader.readPinned(group);
    for(let i=0;i<group.length;i++){values.push(decodeBody(group[i],bodies[i]));bodies[i]=null;}
    start=end;
  }
  return values;
}
function decodeBody(p,encoded,{json = true} = {}) {
  const decoded=p.decoded_bytes??0;
  let body = encoded;
  if (decoded) {
    demand(encoded.length >= 18 && encoded.readUInt32LE(encoded.length-4) === decoded,
      'Checkpoint gzip declared size differs before inflate');
    body = gunzipSync(encoded, {maxOutputLength:decoded});
    demand(body.length === decoded && sha(body) === p.decoded_sha256,
      'Checkpoint whole decoded output is corrupt');
  }

  return json ? JSON.parse(body) : body;
}
function localPin(reader, name, version = reader.version, expected) {
  const actual = reader.descriptor(name, version);
  return {...actual, sha256:expected ?? sha(reader.read(name, {version}))};
}
function readNamed(session, reader, name, expected) {
  const body = reader.read(name,{expected});
  if (name===PROGRAMME_POLICY && reader.version===session.trusted && !session.executingPolicy) {

    session.executingPolicy=freeze({pin:{...reader.inventory.get(reader.version+':'+name)},body:body.toString('utf8')});

  }

  return JSON.parse(body);
}
function rootCatalogue(session, reader, {accepted = false} = {}) {
  const trusted = reader.git('-C',ROOT,'rev-parse', '--verify', 'HEAD').toString().trim();
  // Do not derive trust from reader.version or a caller-supplied trusted SHA.
  const executing = new ImmutableReader(ROOT, trusted, {invocation:reader.invocation, gitExecutable:reader.gitExecutable});
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
    'scripts/check-effective-geographic-regression.mjs','scripts/native-patch-store.mjs',
    'scripts/native-word-store.mjs','src/native-grid.js','src/ownership-codec.js'];
  // HEAD owns current code identity; the catalogue records historical science.
  // Keep authenticating the actual executable bytes without a second hash ledger.
  for (const name of [...expectedPaths, ...(accepted ? ACCEPTED_CODE : [])]) {
    const actual = executing.descriptor(name), local = path.join(ROOT,name);
    demand(actual.mode === '100644', 'Checkpoint method identity differs');

    const bytes = fs.readFileSync(local);
    demand(bytes.length === actual.bytes && bytes.equals(executing.read(name)),
      'Unrecognized/changed executing checkpoint method');
  }
  demand(new Set(catalogue.checkpoints.map(p => p.id)).size === catalogue.checkpoints.length,
    'Duplicate accepted checkpoint identity');
  return {catalogue, trusted, archiveReader:executing};
}
function closeStores(session,keep=new Set()) {
  let failure;
  for(const store of session.stores??[])if(!keep.has(store)){
    try{store.close();}catch(error){failure??=error;}session.stores.delete(store);
  }
  if(failure)throw failure;
}
const decodedChunks=decodedNativeChunks;
const custodyChunks=(chunks,p)=>authenticatedDecodedNativeChunks(chunks,p,{directory:os.tmpdir(),footer:true});
async function storedProduct(session,reader,p,domain,ledger) {
  const {version}=resolvePin(reader,p);
  let chunks=reader.stream(p.path,{version,expected:p.sha256});
  if(ledger==='custody')chunks=custodyChunks(chunks,p);else if(p.decoded_bytes)chunks=decodedChunks(chunks);
  let store;try{store=await (ledger==='custody'?admitNativeMetadataStore:ledger==='envelope'?admitNativeEnvelopeStore:ledger?admitNativeLedgerStore:admitNativePatchStore)({chunks,
    expected:{bytes:p.decoded_bytes??p.bytes,sha256:p.decoded_sha256??p.sha256},
    directory:os.tmpdir(),...domain,...(ledger==='custody'?{metadataArrays:['complete_cold_custody','effective_additions','inventory']}:{}),...(ledger==='constructor'?{rowField:'ledger_rows'}:{})});
  }catch(error){if(ledger==='custody'&&p.decoded_bytes&&error?.message==='Complete native JSON identity differs')throw Error('Checkpoint whole decoded output is corrupt');throw error;}
  (session.stores??=new Set()).add(store);
  if(ledger==='envelope'||ledger==='custody')return store.metadata;
  const wrap=row=>Object.freeze({y:row.y,runs:nativeSequence(row.count,()=>store.intervals(row))});
  if(!ledger)return {...store.metadata,rows:nativeSequence(store.rowCount,
    function*(){for(const row of store.rowEntries())yield wrap(row);},
    {rowAt:y=>{const row=store.rowAt(y);return row?wrap(row):undefined;}})};
  const componentView=component=>Object.freeze({...store.componentMetadata(component),
    ...(component.hasNativeRows?{native_rows:nativeSequence(component.rowCount,
      function*(){for(const row of store.componentRows(component))yield wrap(row);})}:{})});
  return {...store.metadata,[ledger==='constructor'?'ledger_rows':'rows']:nativeSequence(store.componentCount,
    function*(){for(const component of store.componentEntries())yield componentView(component);},
    {entryAt:ordinal=>componentView(store.componentAt(ordinal))})};
}
async function readSelectionProducts(session, reader) {
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
  const [registry,wrapped,manifest] = readBodies(session,reader,[sidecar.authority_registry,
    sidecar.runtime_envelope,sidecar.logical_asset_map.base_manifest]);
  const ownerPin=sidecar.logical_asset_map.owner_roster;
  let ownerBody=readBody(session,reader,ownerPin,{json:false});
  if(!ownerPin.decoded_bytes&&ownerPin.path.endsWith('.gz')){
    demand(ownerBody.length>=18,'Invalid complete compressed owner roster');
    const decoded=ownerBody.readUInt32LE(ownerBody.length-4);
    ownerBody=gunzipSync(ownerBody,{maxOutputLength:decoded});
    demand(ownerBody.length===decoded,'Complete owner roster declared size differs');
  }
  const owners=JSON.parse(ownerBody);
  demand(Array.isArray(owners)&&owners.length>0,'Missing complete selected owner roster');
  const domain={size:manifest.size,ownerCount:owners.length};
  const ledger=await storedProduct(session,reader,sidecar.logical_asset_map.ledger,domain,true);
  const patch=await storedProduct(session,reader,sidecar.logical_asset_map.patch,domain,false);
  const envelope = wrapped.additiveRelease ?? wrapped;
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
  demand(patch.kind === 'unassigned-native-cells-v1' && patch.authority_registry_sha256 === valueSha(registry)
    && patch.ledger_sha256 === sidecar.logical_asset_map.ledger.sha256
    && same(patch.base_reference,envelope.base_reference) && same(patch.effective_reference,envelope.effective_reference),
  'Stale native patch/ledger/registry binding');
  return {selection,sidecar,registry,ledger,patch,envelope};
}
async function readSelection(session, reader) {
  const selected=await readSelectionProducts(session,reader);
  return {...selected,normalized:normaliseRetainedRepairLedger(selected.ledger,selected.registry)};
}
// Only qualifyTransition calls this with a genuine live baseline and products
// parsed into its own immutable stores. Exact old rows inherit intrinsic row
// semantics; new/changed rows still use the complete public validator. Preserve
// original products and defer append-only rejection until after cold eligibility.
function normaliseTransitionSelection(state, selected) {
  const {ledger,registry}=selected;
  demand(isNativeSequence(ledger.scope_ids)&&isNativeSequence(ledger.rows)
    && ledger.scope_ids.length===ledger.rows.length,'Incomplete complete ledger scope');
  const oldRows=repairRowsIndex(state.ledger.rows),candidateRows=repairRowsIndex(ledger.rows);
  let ordinal=0;
  for(const row of ledger.rows){
    demand(typeof row.component_id==='string'&&row.component_id
      &&row.component_id===ledger.scope_ids.at(ordinal++),'Foreign/duplicate/unordered component');
    demand(['assigned','zero-cell','already-resolved','rejected','awaiting-evidence'].includes(row.disposition),
      'Unknown original ledger disposition');
  }
  demand(Array.isArray(registry?.entries),'Missing explicit retained authority registry');
  const entries=new Map(registry.entries.map(entry=>[entry?.authority_sha256,entry]));
  const unchangedAuthorities=new Set(state.registry.entries.filter(entry=>same(entry,entries.get(entry.authority_sha256)))
    .map(entry=>entry.authority_sha256));
  const unchangedRows=new Set();
  for(const row of state.ledger.rows){const key=repairComponentKey(row);
    if(same(row,candidateRows.get(key)))unchangedRows.add(key);}
  const residual=repairRowsIndex(ledger.rows,{include:row=>!unchangedRows.has(repairComponentKey(row))
    ||!unchangedAuthorities.has(row.authority_sha256)});
  // Only selected residual ordinals are read; index.values() would rescan all
  // old metadata on each pass. This is private input, not a published ledger.
  const rows=nativeSequence(residual.size,function*(){for(let at=0;at<residual.size;at++)yield residual.at(at);},
    {entryAt:at=>residual.at(at)});
  // Keep direct ordinal scope lookup; a mapped lazy iterator replays prefixes.
  const {authorities,registry_sha256}=normaliseRetainedRepairLedger({...ledger,rows,
    scope_ids:nativeSequence(residual.size,function*(){for(const row of rows)yield row.component_id;},
      {entryAt:at=>residual.at(at).component_id})},registry);
  selected.normalized={authorities,registry_sha256,rows:repairRowsIndex(ledger.rows,{
    include:row=>['assigned','zero-cell'].includes(row.disposition),
    project:row=>{const entry=authorities.get(row.authority_sha256);
      return entry?{...row,rule_sha256:entry.rule_sha256,authority_sha256:entry.authority_sha256}:row;}
  })};
  return {oldRows,rowsPreserved:unchangedRows.size===oldRows.size,
    authoritiesPreserved:unchangedAuthorities.size===state.registry.entries.length};
}
function completeRows(rows, size, owners) {
  let previous = -1;
  demand(isNativeSequence(rows), 'Missing complete native rows');
  for (const row of rows) {
    keys(row,'y,runs','Unknown native row shape');
    demand(Number.isSafeInteger(row.y) && row.y > previous && row.y < size && isNativeSequence(row.runs),
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
    supported(['ordinary-immutable-git-source','selected-exact-encoded-override','metadata-projected-selected-source'].includes(input.source.kind),
      'Unsupported retained selected source transport');
  }
}
async function rebindOperands(session, reader, ledger, domain) {
  supported(ledger.current_rebind, 'Current-base-bound producer proof is unavailable');
  const certificate = readBody(session,reader,ledger.current_rebind);
  keys(certificate,'version,kind,execution_commit,base_selection,authority_registry_sha256,request,facts,publication,operating,result','Unknown current rebind certificate');
  const request=await storedProduct(session,reader,certificate.request,domain,'envelope');
  return {certificate,request,facts:readBody(session,reader,certificate.facts)};
}
async function rebindProducts(session, reader, ledger, domain) {
  const operands=await rebindOperands(session,reader,ledger,domain),{certificate}=operands;
  return {...operands,publication:readBody(session,reader,certificate.publication),
    operating:readBody(session,reader,certificate.operating),
    result:await storedProduct(session,reader,certificate.result,domain,'envelope')};
}
function newState(session, data, privateData) {
  freeze(data); states.set(data,{session,...privateData}); session.handles.add(data); return data;
}
function getState(state, reader) {
  const proof = states.get(state);
  demand(proof && !proof.session.closed, 'Missing private qualified selected checkpoint');
  sessionCheck(reader ?? proof.reader,proof.session);
  return proof;
}

/** Reader.version is the actual baseline, not the historical execution commit.
 * Unsupported reuse returns a cold-path decision. Corrupt custody throws. */
export async function qualifyCheckpoint({reader,checkpointId}) {
  sessionCheck(reader);
  const session = {reader,invocation:reader.invocation,repo:reader.repo,closed:false,handles:new Set()};

  try {
    const {catalogue,trusted,archiveReader} = rootCatalogue(session,reader);
    session.trusted=trusted;
    const selected = await readSelection(session,reader);
    const matches = catalogue.checkpoints.filter(root => (!checkpointId || root.id === checkpointId)
      && root.selection_sha256 === valueSha(selected.selection));
    supported(matches.length === 1, 'No unique accepted checkpoint for the actual complete selector');
    const root = matches[0];
    if (root.kind==='accepted-derived-selected-checkpoint-v1')
      return await admitTrustedDerivedSeed(session,reader,archiveReader,root,catalogue,selected);
    keys(root,'id,accepted_head,selected_commit,selection_sha256,execution_commit,execution_code_sha256,runtime_sha256,facts,certificate,publication,custody,routes','Unknown accepted checkpoint registration');
    demand(commit(root.accepted_head) && commit(root.selected_commit) && commit(root.execution_commit), 'Incomplete original acceptance/execution identity');
    const facts = readBody(session,archiveReader,root.facts), publication = readBody(session,archiveReader,root.publication);
    const certificate = readBody(session,archiveReader,root.certificate), custody = await storedProduct(session,archiveReader,root.custody,undefined,'custody');
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
    const manifest = readNamed(session,reader,selected.selection.manifest_path,selected.selection.sha256);
    const rebind = await rebindProducts(session,reader,selected.ledger,{size:manifest.size,ownerCount:certificate.entries.length});
    const oldAuthorities=await acceptedAuthorities(session,reader,selected,{size:manifest.size,ownerCount:certificate.entries.length});
    acceptedRebindCheck(selected,rebind,oldAuthorities,manifest.size,certificate.entries.length);
    const additions=checkpointAdditions(selected,rebind.request.current_targets);
    demand(same(additions,retained.effective_additions), 'Accepted original ledger/normalized additions differ');
    coordinateCheck(certificate,facts,additions);
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
    const priorPolicy=validateSupportedProgrammeCatalogue(readBody(session,archiveReader,policyPins.at(0)));
    const currentPolicy=validateSupportedProgrammeCatalogue(readNamed(session,archiveReader,PROGRAMME_POLICY));
    for (const key of ['programs','current_rebind_migrations']) {
      const current=new Set(currentPolicy[key].map(valueSha));
      supported(priorPolicy[key].every(row => current.has(valueSha(row))),
        'Trusted producer policy no longer preserves accepted eligibility');
    }
    session.executablePaths=acceptedExecutablePaths(session,reader,routes,retained.inventory,facts,priorPolicy,rebind);
    const physicalPaths = bindPhysicalLogicalSources(reader,certificate,retained.inventory);
    const masked = maskedLogicalSources(certificate,physicalPaths);
    supported(sameScientificRoutes(reader,routes,session.executablePaths,masked), 'Accepted checkpoint input or routing alternative changed');
    // All genuine old complete records remain in the state, including exceptions.
    const data = {version:1,kind:'verified-selected-state-v1',selected_commit:reader.version,
      accepted_execution:{accepted_head:root.accepted_head,execution_commit:root.execution_commit,
        historical_selected_commit:root.selected_commit,checkpoint_id:root.id,trusted_catalogue_commit:trusted},
      selection:selected.selection,baseSelection:nativeBaseSelection(selected.selection),certificate,
      additions,ledger:selected.ledger,registry:selected.registry,patch:selected.patch,manifest};
    return finishCheckpoint(session,reader,{data,routes:currentMaskedRoutes(reader,routes,masked),physicalPaths,rebind,selected,root,oldAuthorities});
  } catch (error) {
    closeStores(session);session.closed = true;
    if (error.reuseUnavailable) return unavailable(error.message);
    throw error;
  }
}

async function acceptedAuthorities(session,reader,selected,{metadataOnly=false,...domain}={}) {
  const oldAuthorities = new Map();
  // Read only original small patch products already accepted by the checkpoint.
  // No original source/native qualification or selected acquisition is repeated.
  const entries=selected.registry.entries;
  const bindings=readBodies(session,reader,entries.map(entry=>entry.source_authority));
  if(metadataOnly){
    for(let i=0;i<entries.length;i++){
      const binding=bindings[i],nativeOnly=binding.kind==='source-target-native-custody-v1';
      if(nativeOnly){keys(binding,'version,kind,source_evidence,native_patch','Unknown accepted native source custody');demand(binding.version===1,'Unknown accepted native source custody version');}
      oldAuthorities.set(entries[i].authority_sha256,{entry:entries[i],nativeOnly});
    }
    return oldAuthorities;
  }
  const productPins=bindings.map(binding=>{
    if (binding.kind === 'source-target-native-custody-v1') {
      keys(binding,'version,kind,source_evidence,native_patch','Unknown accepted native source custody');
      demand(binding.version===1,'Unknown accepted native source custody version');
      return binding.native_patch;
    }
    return binding.native_proof.publication;
  });
  const products=[];for(let i=0;i<productPins.length;i++)products.push(bindings[i].kind==='source-target-native-custody-v1'
    ?await storedProduct(session,reader,productPins[i],domain,false):readBody(session,reader,productPins[i]));
  const patchPins=[],patchesByEntry=new Map();
  for (let e=0;e<entries.length;e++) {
    const entry=entries[e],binding=bindings[e];
    if (binding.kind === 'source-target-native-custody-v1') {
      oldAuthorities.set(entry.authority_sha256,{entry,nativeOnly:true,patches:[products[e]]});
      continue;
    }
    const publication = products[e];
    demand(publication.assets.length === binding.native_proof.assets.length, 'Accepted native asset roster differs');
    const patches = [];
    for (let i=0;i<publication.assets.length;i++) if (publication.assets[i].path.startsWith('patch-')) {
      const p = binding.native_proof.assets[i], q = publication.assets[i];
      demand(p.path.endsWith('/'+q.path) && p.sha256 === q.sha256 && p.bytes === q.bytes,
        'Accepted original native patch alias differs');
      patches.push(patchPins.length);patchPins.push(p);
    }
    demand(patches.length > 0, 'Accepted native authority has no complete patches');
    oldAuthorities.set(entry.authority_sha256,{entry,patches:[]});
    patchesByEntry.set(entry,patches);
  }
  const patches=[];for(const p of patchPins)patches.push(await storedProduct(session,reader,p,domain,false));
  for(const [entry,indices]of patchesByEntry)oldAuthorities.set(entry.authority_sha256,
    {entry,patches:indices.map(index=>patches[index])});
  return oldAuthorities;
}
function legacyRegistry(registry,authorities) {
  return {...registry,entries:registry.entries.filter(entry=>!authorities.get(entry.authority_sha256).nativeOnly)};
}
function checkpointAdditions(selected,currentTargets) {
  const index=selected.normalized.rows,project=row=>{
    // Cold/seed readSelection validates every normalized component; private
    // transitions reuse only exact rows under unchanged qualified authorities.
    // Hosted admission inherits that invariant only after authenticating the
    // producer's exact accepted bytes, policy and routes. This private projection
    // dispatches that validated representation; rereading the store preserves
    // session lifetime checks without replaying validation on each traversal.
    if (row.representation === 'native-cells') return row;
    const target=currentTargets.find(p=>p.target_id===row.target_id);
    demand(target && target.pixelIndex===row.pixelIndex,'Accepted current target identity omitted');
    return {...row,base_geometry:target.geometry,base_geometry_sha256:target.geometry_sha256};
  };
  return nativeSequence(index.size,function*(){for(const row of index.values())yield project(row);},
    {entryAt:ordinal=>project(index.at(ordinal))});
}
function acceptedRebindCheck(selected,rebind,authorities,size,owners) {
  const legacy=[...authorities.values()].filter(proof=>!proof.nativeOnly).flatMap(proof=>proof.patches);
  demand(same(rebind.request.base_selection,nativeBaseSelection(selected.selection))
    && rebind.request.authority_registry_sha256===valueSha(legacyRegistry(selected.registry,authorities))
    && equalMergedPatchRows(rebind.result.native.rows,legacy,size,owners)
    && equalMergedPatchRows(selected.patch.rows,[...authorities.values()].flatMap(proof=>proof.patches),size,owners),
  'Accepted checkpoint rebind/native selection differs');
}
// Cursor-backed accepted operands plus only newly projected values. Forking a
// transition shares immutable admitted storage, never copies its geometry/runs.
function operandIndex(sources,key,lookup,overrides=new Map()) {
 const index={
  get(id){if(overrides.has(id))return overrides.get(id);
   for(let i=sources.length-1;i>=0;i--){const value=lookup(sources[i],id);if(value!==undefined)return value;}},
  has(id){return index.get(id)!==undefined;},
  set(id,value){overrides.set(id,value);return index;},
  delete(id){return overrides.delete(id);},
  *keys(){const seen=new Set();for(const source of sources)for(const row of source){const id=key(row);if(!seen.has(id)){seen.add(id);yield id;}}
   for(const id of overrides.keys())if(!seen.has(id))yield id;},
  *[Symbol.iterator](){for(const id of index.keys())yield [id,index.get(id)];},
  fork(){return operandIndex(sources,key,lookup,new Map(overrides));}
 };return index;
}
function finishCheckpoint(session,reader,{data,routes,physicalPaths,rebind,selected,root,oldAuthorities,acceptedAggregate=false}) {
  // Derived accepted artifacts bind the entire cumulative patch directly.
  // Legacy seeds still establish their original complete patch denominator.
  if(!acceptedAggregate){
    const hashes=[...oldAuthorities.values()].filter(p=>!p.nativeOnly).flatMap(p=>p.patches.map(valueSha));
    demand(same(hashes,rebind.request.original_patch_sha256s),'Accepted complete original patch denominator differs');
  }
  oldAuthorities=new Map([...oldAuthorities].map(([key,p])=>[key,{entry:p.entry,nativeOnly:!!p.nativeOnly}]));
  const nativeRows=operandIndex([rebind.request.current_rows,rebind.request.acquisition.predecessor_rows],row=>row.y,nativeRowAt);
  const state = newState(session,data,{reader,routes,physicalPaths,rebind,oldAuthorities,selected,root,
    nativeRows,sourceTargets:operandIndex([rebind.request.current_targets],row=>row.target_id,(rows,id)=>rows.find(row=>row.target_id===id))});
  return Object.freeze({available:true,state});
}

// The accepted report is authority only after the transport module has verified
// the existing bot merge receipt, actual merged tree, trusted job and archive.
// Keep the legacy synchronous entry independent of this optional async boundary.
export async function qualifyAcceptedCheckpoint({reader,acceptedHandle}) {
  sessionCheck(reader);
  const session = {reader,invocation:reader.invocation,repo:reader.repo,closed:false,handles:new Set()};

  try {
    const {trusted,archiveReader}=rootCatalogue(session,reader,{accepted:true});
    session.trusted=trusted;
    const {readAcceptedCheckpoint}=await import('../../../scripts/accepted-selected-checkpoint.mjs');
    const accepted=readAcceptedCheckpoint(acceptedHandle);
    // An accepted selector may precede the actual baseline by ordinary additive
    // deliveries. Admit the genuine historical tree, then qualify the existing
    // append-only transition; never relabel its certificate as today's selector.
    const currentSelection=readNamed(session,reader,'data/ownership-selection.json');
    if (same(currentSelection,accepted.products['derived-facts.json'].candidate_selection))
      return await admitDerivedCheckpoint(session,reader,archiveReader,accepted);
    const origin=accepted.receipt.merge_commit;
    try { reader.git('rev-parse','--verify',origin+'^{commit}'); }
    catch {
      try { reader.git('fetch','--quiet','--no-tags','--no-write-fetch-head','--depth=1','--filter=blob:none','origin',origin); }
      catch { closeStores(session);session.closed=true; return unavailable('Accepted historical checkpoint commit unavailable'); }
    }
    demand(reader.git('rev-parse',origin+'^{tree}').toString().trim()===accepted.source.tree,
      'Accepted historical checkpoint tree differs from authenticated merge');
    const historical=new ImmutableReader(reader.repo,origin,{invocation:reader.invocation,gitExecutable:reader.gitExecutable});
    historical.inventory=reader.inventory;
    const qualified=await admitDerivedCheckpoint(session,historical,archiveReader,accepted);
    const transition=await qualifyTransition({state:qualified.state,reader});
    if (!transition.available) { closeStores(session);session.closed=true; return unavailable(transition.reason); }
    // Every newly consumed baseline route must survive the NEXT transition too.
    // The existing census includes complete inherited present/absent routes.
    states.get(transition.candidate).routes=checkpointRouteCensus({transition}).routes;
    return Object.freeze({available:true,state:transition.candidate});
  } catch (error) {
    closeStores(session);session.closed=true;
    if (error.reuseUnavailable) return unavailable(error.message);
    throw error;
  }
}

// A single reviewed main-tree seed reuses the existing catalogue trust root.
// It is never relabelled as a hosted job or a cold-coordinate execution.
async function admitTrustedDerivedSeed(session,reader,archiveReader,root,catalogue,selected) {
  keys(root,'kind,id,accepted_head,selected_commit,selection_sha256,execution_commit,execution_code_sha256,runtime_sha256,facts,certificate,publication,continuous_facts,operands,continuous_publication,joint_result,operating,routes,executing_policy',
    'Unknown trusted derived checkpoint registration');
  demand(commit(root.accepted_head) && commit(root.selected_commit) && commit(root.execution_commit)
    && hash(root.selection_sha256) && hash(root.execution_code_sha256) && hash(root.runtime_sha256),
  'Incomplete trusted derived acceptance/execution identity');
  const roles={facts:'derived-facts.json',certificate:'derived-certificate.json.gz',publication:'derived-publication.json',
    routes:'checkpoint-routes.json'};
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
  const report={gate_status:'passed',selected_native_report:joint.native};

  return admitDerivedCheckpoint(session,reader,archiveReader,{seedRoot:root,products,member_pins:members,report,
    source:{executing_commit:root.execution_commit,baseline:facts.baseline_commit,candidate_commit:root.selected_commit}},selected);
}

async function admitDerivedCheckpoint(session,reader,archiveReader,accepted,selectedInput) {
  const {source,receipt,report,products,member_pins,seedRoot}=accepted;
  const trusted=session.trusted;
  const facts=products['derived-facts.json'], certificate=products['derived-certificate.json.gz'];
  const publication=products['derived-publication.json'];
  const census=products['checkpoint-routes.json'];
  const members=new Map(member_pins.map(p=>[p.name,p]));
  const published=(name,p)=>{
    const actual=members.get(name);
    demand(actual && p?.path===name && p.bytes===actual.bytes && p.sha256===actual.sha256
      && p.decoded_bytes===actual.decoded_bytes && p.decoded_sha256===actual.decoded_sha256
      && valueSha(products[name])===(actual.decoded_sha256??actual.sha256),
    'Accepted whole checkpoint publication/member differs: '+name);
  };
  demand(facts.version===1 && facts.kind==='derived-selected-checkpoint-candidate-v1'
    && facts.accepted_checkpoint===false
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
  demand(certificate.version===2 && certificate.kind==='selected-coordinate-neighbor-certificate-v2'
    && same(certificate.entry_fields,FIELDS) && Array.isArray(certificate.entries)
    && Array.isArray(certificate.inputs) && Array.isArray(certificate.binding?.sources),
  'Unsupported accepted coordinate product schema');
  const native=report.selected_native_report;
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
  // Original accepted execution is provenance. Preserve its pins without
  // reacquiring obsolete polygon methods or requiring their output roster.
  demand(Array.isArray(facts.execution_code) && new Set(facts.execution_code.map(p=>p.path)).size===facts.execution_code.length
    && facts.execution_code.some(p=>p.path==='scripts/selected-checkpoint-native.mjs'),
  'Accepted checkpoint lacks original native execution identity');
  for (const p of facts.execution_code) {
    pin(p); demand(p.commit===facts.executing_commit, 'Accepted executing code was rebound');
    // The original trusted accepted execution already authenticated these exact
    // complete code bodies. Preserve its pins; do not reacquire that old method.
  }
  demand(Array.isArray(facts.runtime) && facts.runtime.length===3
    && new Set(facts.runtime.map(p=>p.path)).size===3 && facts.runtime.every(p=>typeof p.path==='string'
      && Number.isSafeInteger(p.bytes) && p.bytes>0 && Number.isSafeInteger(p.mode) && hash(p.sha256)),
  'Incomplete accepted execution runtime identities');
  demand(commit(facts.baseline_accepted_execution?.accepted_head)
    && commit(facts.baseline_accepted_execution?.execution_commit)
    && commit(facts.baseline_accepted_execution?.historical_selected_commit),
  'Accepted predecessor checkpoint custody differs');
  const selected=selectedInput??await readSelectionProducts(session,reader);
  supported(same(selected.selection,facts.candidate_selection), 'Accepted checkpoint does not cover the actual complete selector');
  const manifest=readNamed(session,reader,selected.selection.manifest_path,selected.selection.sha256);
  demand(same(facts.candidate_bindings,{ledger_sha256:valueSha(selected.ledger),registry_sha256:valueSha(selected.registry),
    patch_sha256:valueSha(selected.patch),manifest_sha256:valueSha(manifest)}),
  'Accepted checkpoint changed the complete ledger/registry/patch/manifest');
  // Accepted aggregate consumers use request/facts only. Keep the other original
  // product pins in the certificate and route census; cold seeds and changed
  // rebinds still acquire their complete proof bodies.
  const rebind=await (seedRoot?rebindProducts:rebindOperands)(session,reader,selected.ledger,
    {size:manifest.size,ownerCount:certificate.entries.length});
  // The trusted accepted execution already proved this exact aggregate.
  // Keep authority identities and full route custody, not historical patch copies.
  const oldAuthorities=await acceptedAuthorities(session,reader,selected,{metadataOnly:true});
  demand(same(rebind.request.base_selection,nativeBaseSelection(selected.selection))
    &&rebind.request.authority_registry_sha256===valueSha(legacyRegistry(selected.registry,oldAuthorities)),
    'Accepted checkpoint rebind/native selection differs');
  demand(same(selected.ledger.current_targets,rebind.request.current_targets), 'Accepted complete target roster differs');
  demand(same(certificate.inputs.map(p=>p.source),certificate.binding.sources), 'Accepted complete source binding inventory differs');
  demand(same(certificate.binding.selection,selected.selection), 'Accepted certificate selected binding differs');
  const inventories=facts.actual_reader_inventories;
  keys(inventories,'baseline,candidate','Missing complete accepted reader inventories');
  for (const inventory of Object.values(inventories)) {
    demand(Array.isArray(inventory) && new Set(inventory.map(p=>p.commit+':'+p.path)).size===inventory.length,
      'Duplicate accepted reader inventory identity');
    for (const p of inventory) {
      demand(commit(p.commit) && safe(p.path) && ['100644','100755'].includes(p.mode)
        && /^[a-f0-9]{40}$/.test(p.git_blob_oid) && Number.isSafeInteger(p.bytes) && p.bytes>=0,
      'Incomplete accepted reader descriptor');
      if (p.whole_body_consumed) demand(p.whole_body_consumed===true && hash(p.sha256)
        && (p.decoded_bytes===undefined || Number.isSafeInteger(p.decoded_bytes) && p.decoded_bytes>=0
          && hash(p.decoded_sha256)), 'Incomplete accepted consumed-body identity');
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

    demand(sha(Buffer.from(policy.body))===policy.pin.sha256, 'Accepted original programme policy body differs');
    priorPolicy=validateSupportedProgrammeCatalogue(JSON.parse(policy.body));
  }
  const currentPolicy=validateSupportedProgrammeCatalogue(readNamed(session,archiveReader,PROGRAMME_POLICY));
  for (const key of ['programs','current_rebind_migrations']) {
    const current=new Set(currentPolicy[key].map(valueSha));
    supported(priorPolicy[key].every(row=>current.has(valueSha(row))),
      'Trusted producer policy no longer preserves accepted eligibility');
  }
  session.executablePaths=acceptedExecutablePaths(session,reader,census.routes,Object.values(inventories).flat(),facts,priorPolicy,rebind);
  const physicalPaths = bindPhysicalLogicalSources(reader,certificate,Object.values(inventories).flat());
  const masked = maskedLogicalSources(certificate,physicalPaths);
  supported(sameScientificRoutes(reader,census.routes,session.executablePaths,masked), 'Accepted checkpoint input or routing alternative changed');
  if (!seedRoot) {
    // This private path is reached only with the transport's genuine accepted
    // handle and the original producer's successful native result. Its complete
    // ledger/registry/patch hashes, selector, policy and routes match above.
    // The producer established every candidate row's semantics before minting
    // its private transition. Reconstruct that view without replaying accepted
    // polygon/interval semantics. Parsing and whole-body authentication remain.
    selected.normalized={rows:repairRowsIndex(selected.ledger.rows,{
      include:row=>['assigned','zero-cell'].includes(row.disposition),
      project:row=>{const entry=oldAuthorities.get(row.authority_sha256)?.entry;
        return entry?{...row,rule_sha256:entry.rule_sha256,authority_sha256:entry.authority_sha256}:row;}
    })};
  }
  const additions=checkpointAdditions(selected,rebind.request.current_targets);
  // A catalogue seed has no hosted acceptance; preserve its full semantic check.
  if (seedRoot) {
    coordinateCheck(certificate,{binding:certificate.binding,complete_owners:certificate.entries.length,
      complete_sources:certificate.binding.sources.length},additions);
    completeRows(selected.patch.rows,manifest.size,certificate.entries.length);
    completeRows(rebind.request.current_rows,manifest.size,certificate.entries.length);
    completeRows(rebind.request.acquisition.predecessor_rows,manifest.size,certificate.entries.length);
  }
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
  // Retain newly acquired state/patch products without duplicating a resolver.
  return finishCheckpoint(session,reader,{data,routes:currentMaskedRoutes(reader,census.routes,masked),physicalPaths,rebind,selected,root:null,oldAuthorities,acceptedAggregate:true});
}

/** Exact already-consumed executing policy, for durable successor custody. */
export function checkpointExecutingPolicy({transition}) {
  authenticateTransition({transition});
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
export function checkpointRouteCensus({transition}) {
  const genuine=authenticateTransition({transition});
  const before=states.get(genuine.baseline), after=states.get(genuine.candidate), {session,reader}=after;
  const predecessor=before.routes.map(p=>p.path);
  const names=scientificRoutePaths(predecessor,[...reader.inventory.values()],genuine.candidate.manifest,
    genuine.candidate.certificate,genuine.candidate.selection);

  // The admitted candidate already refreshed any unconsumed masked logical
  // routes. Preserve those current bindings if a new authority now reads them.
  const old=new Map(after.routes.map(p=>[p.path,p.tree]));
  const routes=names.map(name=>({path:name,tree:old.has(name) && name!==PROGRAMME_POLICY
    ? old.get(name) : reader.treeRoute(name)}));
  demand(routes.every(validRoute), 'Unsupported scientific route entry');
  const result=freeze({version:1,kind:'selected-checkpoint-scientific-routes-v1',candidate_commit:reader.version,
    candidate_selection:genuine.candidate.selection,predecessor_paths:[...predecessor].sort(),routes});

  return result;
}

/** Read the selected normative latitude bytes for the actual native consumer.
 * Historical checkpoint traversal does not apply new-repair eligibility. */
export function projectVisibilityLatitudes({state}) {
  const {session,reader}=getState(state), p=state.manifest.native_latitudes;
  demand(p?.root==='repository'&&p.decoded_bytes===state.manifest.size*8,'Missing normative visibility latitude input');

  let version=p.commit;try{reader.git('--no-lazy-fetch','cat-file','-e',version+'^{commit}');}catch{version=reader.version;}
  const encoded=reader.read(p.path,{version,expected:p.sha256,decoded:p.decoded_bytes});
  const latitudes=decodeVisibilityLatitudes(encoded,p,state.manifest.size);

  return latitudes;
}

/** Projects exact whole original features, never certificate boxes. Pass a prior
 * projection explicitly as reuse to share identical pointsets across vintages. */
export function projectSourceFeatures({state,ids,reuse}) {
  const proof = getState(state), {session,reader} = proof;
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

    }
    inputs.push(input);
    const {version}=resolvePin(reader,input.source); actualInputs.push({...reader.inventory.get(version+':'+input.source.path)});
  }
  demand(features.length === ids.length, 'Source projection omitted requested features');
  const result = freeze({features,inverse,inputs,custody:{actual_inputs:actualInputs},state_binding:state.certificate.binding});
  projections.set(result,{session,kind:'source',ids:Object.freeze([...ids]),sourceIdentity:state.certificate.binding.sources});

  return result;
}

function nativeContext(proof) {
  const {session,reader} = proof, state = proof.state;
  if (proof.nativeContext) return proof.nativeContext;
  supported(state.manifest.native_asset_transport, 'Unsupported legacy native transport');

  const image = new NativeAssetImage(reader,state.manifest,state.selection.manifest_path);

  proof.nativeContext = {image,table:null,inputInventory:new Map()}; return proof.nativeContext;
}
function nativeAsset(proof, pin, context) {
  const {session,reader} = proof, state = proof.state;
  if (context.visitingWords?.has(pin.path)) return context.visitingWords.get(pin.path);
  const name = path.posix.join(path.posix.dirname(state.selection.manifest_path),pin.path);
  const ordinary = reader.treeRoute(name).length > 0;

  const encoded = ordinary ? reader.read(name,{expected:pin.sha256,decoded:pin.decoded_bytes}) : context.image.logical(name,pin);
  demand(encoded.length === pin.bytes && sha(encoded) === pin.sha256, 'Whole native encoded body differs');
  const raw = gunzipSync(encoded,{maxOutputLength:pin.decoded_bytes});
  demand(raw.length === pin.decoded_bytes, 'Whole native decoded length differs');
  const words = unshuffleOwnershipBytes(raw,pin.words), canonical = Buffer.alloc(words.byteLength);
  for (let i=0;i<words.length;i++) canonical.writeUInt32LE(words[i],i*4);
  demand(sha(canonical) === pin.decoded_sha256, 'Whole native canonical words differ');
  for (const key of reader.inventory.keys()) {
    const p=reader.inventory.get(key); if (p?.whole_body_consumed) context.inputInventory.set(key,{...p});
  }

  context.visitingWords?.set(pin.path,words);
  return words;
}
/** Complete native intervals. Genuine accepted whole rows are reused only under
 * identical manifest/domain/owner and all present/absent native routes. */
export function projectNativeRows({state,rows}) {
  const proof = getState(state), {session,reader} = proof;
  proof.state = state;
  demand(Array.isArray(rows) && rows.every((y,i) => Number.isSafeInteger(y) && y >= 0 && y < state.manifest.size && (!i || rows[i-1] < y)),
    'Duplicate, incomplete or foreign native row scope');
  const missing = rows.filter(y => !proof.nativeRows.has(y)), inputs = [];
  if (missing.length) {
    const context = nativeContext(proof), manifest = state.manifest;
    if (!context.table) {
      const pins = manifest.parts.filter(p => p.kind === 'rows');
      supported(pins.length === 1, 'Unsupported split native row table');
      context.table = nativeAsset(proof,pins[0],context);
      demand(context.table.length === manifest.size*2, 'Incomplete whole native row table');
      let offset = 0;
      for (let y=0;y<manifest.size;y++) { demand(context.table[y*2] === offset, 'Native row partition omitted a range'); offset += context.table[y*2+1]; }
      demand(offset*2 === manifest.runWords, 'Native row partition omits complete runs');

inputs.push(pins[0]);
    }
    const table = context.table, groups = new Map();
    for (const y of missing) {
      const start = table[y*2]*2, end = start+table[y*2+1]*2;
      const parts = manifest.parts.filter(p => p.kind === 'runs' && start < p.offset+p.words && p.offset < end), key = valueSha(parts);
      if (!groups.has(key)) groups.set(key,{parts,rows:[]}); groups.get(key).rows.push({y,start,end});
    }
    for (const group of groups.values()) {

      const bodies = new Map(group.parts.map(p => [p.path,nativeAsset(proof,p,context)]));
      for (const {y,start,end} of group.rows) {
        const runs = [];
        for (const part of group.parts) for (let i=Math.max(start,part.offset);i<Math.min(end,part.offset+part.words);i+=2) {
          const words = bodies.get(part.path), a = words[i-part.offset], b = words[i-part.offset+1], bits = manifest.coordinateBits, mask = 2**bits-1;
          runs.push([a&mask,(b&mask)+1,(a>>>bits)+(b>>>bits)*2**(32-bits)]);
        }
        demand(runs.length === table[y*2+1], 'Incomplete containing native interval range');
        const row = freeze({y,runs}); completeRows([row],manifest.size,state.certificate.entries.length);
        proof.nativeRows.set(y,row);
      }
      inputs.push(...group.parts);
    }
  }
  const result = freeze({rows:rows.map(y => proof.nativeRows.get(y)),requested_rows:rows,
    native_binding:{base_selection:state.baseSelection,manifest_sha256:state.selection.sha256,
      owners_sha256:state.certificate.binding.owners_sha256},inputs,
    custody:{accepted_checkpoint:state.accepted_execution,new_whole_inputs:[...(proof.nativeContext?.inputInventory.values()??[])],
      retained_native_inputs:Array.from(proof.rebind.request.acquisition.native_inputs)},
    reused_rows:rows.filter(y => !missing.includes(y)),acquired_rows:missing});
  projections.set(result,{session,kind:'native',rows});
  return result;
}

export function releaseCheckpoint(state) {
  const proof = states.get(state); demand(proof && !proof.session.closed, 'Checkpoint already released or foreign');
  const session = proof.session; session.closed = true;
  try{closeStores(session);}finally{
    for (const handle of session.handles) states.delete(handle);
    session.handles.clear(); session.executingPolicy=null;
  }
}

// Compare the canonical union directly. One cursor per authority and one
// pending interval replace a complete duplicate expected-patch graph, including
// the dense-row case. Inputs have already been authenticated; validate every row.
export function equalMergedPatchRows(actual,patches,size,ownerCount) {
  completeRows(actual,size,ownerCount);
  for(const patch of patches)completeRows(patch.rows,size,ownerCount);
  const cursors=patches.map(patch=>{const rows=patch.rows[Symbol.iterator]();return {rows,row:rows.next()};});
  const actualRows=actual[Symbol.iterator]();let actualRow=actualRows.next();
  try {while(true){
    let y=Infinity;for(const cursor of cursors)if(!cursor.row.done)y=Math.min(y,cursor.row.value.y);
    if(y===Infinity)return actualRow.done;
    if(actualRow.done||actualRow.value.y!==y)return false;
    const group=cursors.filter(cursor=>!cursor.row.done&&cursor.row.value.y===y)
      .map(cursor=>{const runs=cursor.row.value.runs[Symbol.iterator]();return {cursor,runs,run:runs.next()};});
    const expected=actualRow.value.runs[Symbol.iterator]();let pending=null;
    const matches=run=>{const next=expected.next();return !next.done&&run.every((n,i)=>n===next.value[i]);};
    try {while(true){
      let selected=null,run=null;
      for(const cursor of group){
        const next=cursor.run.done?null:cursor.run.value;
        if(next&&(!run||next[0]<run[0]||next[0]===run[0]&&(next[1]<run[1]||next[1]===run[1]&&next[2]<run[2]))){selected=cursor;run=next;}
      }
      if(!selected)break;selected.run=selected.runs.next();
      demand(!pending||run[0]>=pending[1]||run[2]===pending[2],'Native delta reassigns an existing owner');
      if(pending&&run[2]===pending[2]&&run[0]<=pending[1])pending[1]=Math.max(pending[1],run[1]);
      else{if(pending&&!matches(pending))return false;pending=[...run];}
    }
    if(pending&&!matches(pending)||!expected.next().done)return false;
    }finally{expected.return?.();for(const cursor of group)cursor.runs.return?.();}
    for(const cursor of group)cursor.cursor.row=cursor.cursor.rows.next();
    actualRow=actualRows.next();
  }}finally{actualRows.return?.();for(const cursor of cursors)cursor.rows.return?.();}
}
function changedPatchRows(before,after) {
  const left=before[Symbol.iterator](),right=after[Symbol.iterator](),changed=[];
  let a=left.next(),b=right.next();
  try{while(!a.done||!b.done){
    if(b.done||!a.done&&a.value.y<b.value.y){changed.push(a.value.y);a=left.next();}
    else if(a.done||b.value.y<a.value.y){changed.push(b.value.y);b=right.next();}
    else {if(!same(a.value.runs,b.value.runs))changed.push(a.value.y);a=left.next();b=right.next();}
  }}finally{left.return?.();right.return?.();}
  return changed;
}
function disjointPatchRows(before,patches) {
  for(const patch of patches)for(const row of patch.rows){
    const old=nativeRowAt(before,row.y)?.runs??[],iterator=old[Symbol.iterator]();let current=iterator.next();
    try{for(const run of row.runs){
      while(!current.done&&current.value[1]<=run[0])current=iterator.next();
      demand(current.done||current.value[0]>=run[1],'New native assignment overlaps a previously selected owner');
    }}finally{iterator.return?.();}
  }
}

async function appendAuthority(session, reader, entry, domain) {
  const child = new ImmutableReader(reader.repo,reader.version,{invocation:reader.invocation,gitExecutable:reader.gitExecutable});
  child.inventory=reader.inventory; // retain actual appended-producer inputs without reopening them
  let proof;
  if(entry.completed_constructor!==undefined){
    const {preimage,binding}=readRegistryAuthorityInputs(child,entry);
    if(binding?.kind==='source-target-native-custody-v1'){
      const constructed=await storedProduct(session,child,entry.completed_constructor,domain,'constructor');
      const evidence=await storedProduct(session,child,binding.source_evidence,domain,'envelope');
      const candidate=await storedProduct(session,child,binding.native_patch,domain,false);
      proof=verifyCompletedSourceTargetNativeAuthority({constructed,preimage,binding,evidence,candidate});
    }
  }
  proof??=readRetainedRegistryAuthority(child,entry);

  return {entry,nativeOnly:proof.original_pins.source_evidence!==undefined,patches:proof.native_proof.native_patches,ledger:proof.original_ledger,
    contract:proof.native_proof.native_contract,source_scope_ids:proof.source_scope_ids};
}
function expectedNativeAcquisition(proof, neededRows) {
  const {session,reader,state} = proof, prior = proof.rebind.request.acquisition;
  const oldNeeded = [...new Set(Array.from(proof.rebind.request.current_rows,p => p.y).concat(Array.from(prior.predecessor_rows,p => p.y)))].sort((a,b) => a-b);
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
    if (reader.treeRoute(name)) {
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

  return {inputs,scopes:[{kind:'complete-current-native-row-table'},...[...groups.values()].map(g => ({kind:'complete-current-native-window-group',rows:g.rows,parts:g.parts.map(p => p.path)}))]};
}
function authenticateProducerExecution(session,reader,products,bodyPins) {
  const {certificate,request,facts,publication,operating}=products;
  const expectedCode=CURRENT_REBIND_CODE.map(name => { const p=reader.descriptor(name,certificate.execution_commit); return {path:name,bytes:p.bytes,sha256:sha(reader.read(name,{version:certificate.execution_commit}))}; });
  demand(same(request.executed_code,expectedCode),'Original producer execution vector differs');
  keys(facts,'version,kind,execution_commit,request_sha256,result_sha256,acquisition_sha256,acquisition_phases'+['complete_phase_bytes','descriptors'].filter(k=>Object.hasOwn(facts,k)).map(k=>','+k).join(''),'Unknown producer facts');
  keys(publication,'version,kind,execution_commit,request_sha256,outputs','Unknown producer publication');
  keys(operating,'version,kind,execution_commit,request_sha256,publication_sha256,exit_code,signal,owned_processes_remaining,elapsed_seconds,execution_custody'+(Object.hasOwn(operating,'lifetime_rss_bytes')?',lifetime_rss_bytes':''),'Unknown producer operating proof');
  const custody={};
  for (const name of ['code_source','terminal','stderr','stdout','issued_plan'])
    custody[name]=readBody(session,reader,operating.execution_custody[name],{json:false});
  verifyCurrentRebindExecution({request,operating,expectedCode,custody:{...custody,result_sha256:bodyPins.result.sha256}});
}
function qualifyProjectedRebind(proof, selected, authorities, products) {
  const {session,reader,state}=proof, {certificate,request,facts,publication,operating,result}=products;
  const base=state.baseSelection, registry=legacyRegistry(selected.registry,authorities);
  const originalRows=[...selected.normalized.rows.values()].filter(row=>!nativeOnlyComponent(row,valueSha));
  const originalPatches=registry.entries.flatMap(entry => authorities.get(entry.authority_sha256).patches);
  const bodyPins=Object.fromEntries(['request','facts','publication','operating','result'].map(name => [name,certificate[name]]));
  for (const [name,body] of Object.entries({request,facts,publication,operating,result}))
    demand(valueSha(body)===bodyPins[name].sha256 && valueBytes(body).length===bodyPins[name].bytes,'Whole canonical producer output differs');
  keys(request,'version,kind,execution_commit,executed_code,base_selection,authority_registry_sha256,original_rows,original_patch_sha256s,current_targets,current_rows,acquisition,execution,size'+(Object.hasOwn(request,'limits')?',limits':''),'Unknown current producer request');
  demand(certificate.version===1 && certificate.kind==='qualified-native-additive-current-bank-rebind-v1'
    && request.version===1 && request.kind==='issued-native-additive-current-bank-rebind-v1'
    && certificate.execution_commit===request.execution_commit && same(certificate.base_selection,base)
    && certificate.authority_registry_sha256===valueSha(registry)
    && same(request.base_selection,base) && request.authority_registry_sha256===valueSha(registry)
    && request.size===state.manifest.size && same(request.original_rows,originalRows)
    && same(request.original_patch_sha256s,originalPatches.map(valueSha)), 'Producer rebind has stale base, omitted original scope or different authority');
  authenticateProducerExecution(session,reader,products,bodyPins);
  keys(request.acquisition,'version,kind,target_sources,source_inputs,native_inputs,predecessor_proof,predecessor_rows,manifest_sha256','Unknown producer acquisition schema');
  demand(same(request.acquisition.predecessor_proof,proof.rebind.request.acquisition.predecessor_proof)
    && same(request.acquisition.predecessor_rows,proof.rebind.request.acquisition.predecessor_rows), 'Changed original predecessor custody/rows');
  const owners=new Map(state.certificate.entries.map(row => [row[0],row]));
  const targets=[...new Set(originalRows.map(row => row.target_id))].sort();
  const newTargets=targets.filter(id => !proof.sourceTargets.has(id));
  const projected=projectSourceFeatures({state,ids:newTargets});
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
  const candidateRows=[...new Set(originalPatches.flatMap(p => Array.from(p.rows,row => row.y)))].sort((a,b) => a-b);
  const needed=[...new Set(candidateRows.concat(request.acquisition.predecessor_rows.map(row => row.y)))].sort((a,b) => a-b);
  const native=projectNativeRows({state,rows:needed});
  const currentRows=native.rows.filter(row => candidateRows.includes(row.y));
  const nativeAcquisition=expectedNativeAcquisition(proof,needed);
  const acquisition={version:1,kind:'complete-selected-rebind-inputs-v1',target_sources:request.acquisition.target_sources,
    source_inputs:sourceInputs,native_inputs:nativeAcquisition.inputs,predecessor_proof:request.acquisition.predecessor_proof,
    predecessor_rows:request.acquisition.predecessor_rows,manifest_sha256:valueSha(state.manifest)};
  demand(same(currentRebindAcquisitionIdentity(acquisition),currentRebindAcquisitionIdentity(request.acquisition))
    && same(currentTargets,request.current_targets) && same(currentRows,request.current_rows),
  'Producer operands differ from complete retained/projected original sources or native intervals');
  const expected=currentRebindResult({baseSelection:base,registry,originalRows,originalPatches,
    currentTargets,currentRows,size:state.manifest.size});
  demand(same(result,expected),'Producer result differs from actual complete delta operands');
  const scopes=sourceInputs.map(p => ({kind:'complete-current-target-source',path:p.path}));
  if (request.acquisition.predecessor_proof) scopes.push({kind:'complete-qualified-arctic-predecessor',
    path:request.acquisition.predecessor_proof.path,sha256:request.acquisition.predecessor_proof.sha256});
  scopes.push(...nativeAcquisition.scopes);
  demand(Array.isArray(facts.acquisition_phases) && facts.acquisition_phases.length===scopes.length
    && facts.acquisition_phases.every((p,i) => { const {complete_phase_bytes,descriptors,...scope}=p;
      return same(scope,scopes[i]); }), 'Original producer complete acquisition scope or admission differs');
  demand(facts.version===1 && facts.kind==='native-additive-current-bank-rebind-facts-v1'
    && facts.execution_commit===request.execution_commit && facts.request_sha256===bodyPins.request.sha256
    && facts.result_sha256===bodyPins.result.sha256 && facts.acquisition_sha256===valueSha(request.acquisition),
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

// Full proof wrappers and expectedAdded's original-row aliases are temporary.
// Retain original per-authority patches, exactly as for accepted seed entries.
async function qualifyAppendedAuthorities(session,reader,state,selected,prior,addedEntries,oldRows) {
  const authorities=new Map(prior);
  const expectedAdded=new Map();
  for (const entry of addedEntries) {
    demand(entry.policy_id==='retained-source-literal-additions' && entry.policy_version===1, 'Unsupported appended source policy');
    const proof=await appendAuthority(session,reader,entry,{size:state.manifest.size,ownerCount:state.certificate.entries.length}); authorities.set(entry.authority_sha256,proof);
    const contract=Object.fromEntries(['size','coordinateBits','method','native_latitudes','hierarchy_sha256','original_assets'].map(k => [k,state.manifest[k]]));
    demand(same(proof.contract,contract) && (same(proof.ledger.parent_inventory,state.ledger.parent_inventory) || proof.nativeOnly && proof.ledger.parent_inventory===undefined),
      'Appended producer changed native contract or complete original source denominator');
    if (proof.nativeOnly) demand(proof.patches.every(p=>same(p.base_reference,selected.envelope.base_reference)
      || selected.selection.reference_projection && same(p.base_reference,{id:state.manifest.geographic_release,
        hierarchy_sha256:state.manifest.hierarchy_sha256,footprints_sha256:state.manifest.footprints_sha256})),
      'Native source-target authority belongs to a different selected base');
    let ordinal=0;for (const original of proof.ledger.rows) {
      demand(!oldRows.has(repairComponentKey({...original,authority_sha256:entry.authority_sha256})) && !expectedAdded.has(repairComponentKey({...original,authority_sha256:entry.authority_sha256})), 'Appended producer repeats original component');
      expectedAdded.set(repairComponentKey({...original,authority_sha256:entry.authority_sha256}),{ordinal:ordinal++,ledger:proof.ledger,entry});
    }
  }
  const addedRows=selected.ledger.rows.filter(row => !oldRows.has(repairComponentKey(row)));
  demand(addedRows.length===expectedAdded.size,'Candidate omitted/invented complete appended ledger scope');
  for (const row of addedRows) {
    const expected=expectedAdded.get(repairComponentKey(row)), {authority_sha256,rule_sha256,...literal}=row;
    demand(expected && authority_sha256===expected.entry.authority_sha256
      && (rule_sha256===undefined || rule_sha256===expected.entry.rule_sha256) && same(literal,expected.ledger.rows.at(expected.ordinal)),
    'Candidate changed original appended primitive or exception');
  }
  for (const entry of addedEntries) {
    const {nativeOnly,patches}=authorities.get(entry.authority_sha256);
    authorities.set(entry.authority_sha256,{entry,nativeOnly,patches});
  }
  return authorities;
}

// Apply the existing complete reference-metadata proof to a retained coordinate
// product. This reads the small base/metadata context, never additive authorities
// or native rows. Only the proof's actual current aliases may refresh old routes.
function projectCheckpointMetadata(state,reader,selection) {
  if (same(state.selection.reference_projection,selection.reference_projection))
    return {certificate:state.certificate,paths:new Set()};
  supported(selection.reference_projection, 'Removing a selected reference metadata application requires cold comparison');
  const snapshot=loadBaseSelection(reader), resolver=selectedGeometrySourceAlias(snapshot);
  demand(same(snapshot.selection,selection) && same(snapshot.manifest,state.manifest),
    'Checkpoint metadata application changes the selected native manifest');
  const projection=resolver.metadataProjection, owners=selectedReferenceOwners(snapshot);
  demand(projection && owners.length===state.certificate.entries.length
    && same(resolver.paths,state.certificate.inputs.map(input=>input.path)),
    'Checkpoint metadata application changes the complete source/owner roster');
  // Historical encoded aliases do not change the original scientific source.
  const identity=p=>Object.fromEntries(['commit','path','mode','git_blob_oid','bytes','sha256',
    'encoding','decoded_bytes','decoded_sha256'].filter(k=>Object.hasOwn(p,k)).map(k=>[k,p[k]]));
  const entries=state.certificate.entries.map(row=>[...row]);
  const inputs=state.certificate.inputs.map((input,i)=>{
    const source=resolver.sources[i], original=source.original_source??source;
    const priorOriginal=input.source.original_source??input.source;
    demand(same(identity(priorOriginal),identity(original)),
      'Checkpoint metadata application changes an original scientific source');
    if (same(identity(input.source),identity(source))) return input;
    const actual=resolver.read(input.path), rows=entries.filter(row=>row[4]===input.path);
    demand(rows.length===actual.collection.features.length,
      'Checkpoint metadata application changes complete source membership');
    for (const row of rows) {
      const feature=actual.collection.features[row[5]], owner=owners[row[1]-1];
      demand(feature?.type==='Feature' && (feature.id??feature.properties?.id)===row[0]
        && owner?.id===row[0] && owner.index===row[1]
        && feature.properties?.parent_id===owner.province_id && valueSha(feature.geometry)===row[7],
        'Checkpoint metadata application changes original geometry/ordinal/owner');
      row[6]=valueSha(feature);
    }
    return {path:input.path,source:actual.source,whole_body_sha256:actual.whole_sha256,bytes:actual.body.length};
  });
  for (const row of entries) {
    const owner=owners[row[1]-1];
    demand(owner?.id===row[0] && owner.index===row[1], 'Checkpoint metadata application rebinds stable owner/index');
    row[2]=owner.province_id; row[3]=owner.province_index;
  }
  const certificate={...state.certificate,inputs,entries,binding:{...state.certificate.binding,
    selection,release:resolver.release,sources:inputs.map(input=>input.source),owners_sha256:valueSha(owners)}};
  // These are validated roles, not arbitrary changed paths: current full source,
  // hierarchy, release pointer/body and the selected metadata application.
  const pointer=reader.json('data/geographic-releases/current-manifest.json');
  const paths=new Set([selection.reference_projection.path,projection.hierarchy.after.path,
    'data/geographic-releases/current-manifest.json',path.posix.join('data/geographic-releases',pointer.path),
    ...projection.source_updates.map(update=>update.logical_path)]);
  return {certificate:freeze(certificate),paths,reference:projection.reference,nativeReference:projection.native_reference};
}

/** Visit complete authenticated row batches without retaining newly expanded
 * triples. Whole decoded native containers are reused only within this visit;
 * existing qualified rows and the ordinary projector API remain unchanged. */
export function visitNativeRows({state,rows,visit}) {
  const proof=getState(state); proof.state=state;
  demand(typeof visit==='function','Native row visitor required');
  demand(Array.isArray(rows)&&rows.every((y,i)=>Number.isSafeInteger(y)&&y>=0&&y<state.manifest.size&&(!i||y>rows[i-1])),
    'Duplicate, incomplete or foreign native row scope');
  if(!rows.length){const projected=projectNativeRows({state,rows});visit(projected.rows);return projected;}
  const retained=new Set(proof.nativeRows.keys()),reused=[],acquired=[];
  const context=nativeContext(proof);
  demand(!context.visitingWords,'Nested native row visit');
  context.visitingWords=new Map();
  let last;
  try {
    // Even an empty scope goes through the genuine projection boundary.
    for(let start=0;start<rows.length||start===0;start+=128){
      const batch=rows.slice(start,start+128);
      try {
        last=projectNativeRows({state,rows:batch});
        reused.push(...last.reused_rows); acquired.push(...last.acquired_rows);
        visit(last.rows);
      } finally {
        for(const y of batch)if(!retained.has(y))proof.nativeRows.delete(y);
      }
    }
    return {reused_rows:reused,acquired_rows:acquired,custody:last.custody};
  } finally {
    delete context.visitingWords;
  }
}


// Stream complete row intervals from bounded authenticated word windows. This
// path never enters the expanded-row or decoded-container caches. The caller
// must consume each complete row; only the finished visit returns custody.
export async function visitNativeIntervals({state,rows,visit}) {
  const proof=getState(state);proof.state=state;
  demand(typeof visit==='function'&&Array.isArray(rows)&&rows.every((y,i)=>Number.isSafeInteger(y)&&y>=0&&y<state.manifest.size&&(!i||y>rows[i-1])),
    'Duplicate, incomplete or foreign native row scope');
  if(!rows.length){const result=projectNativeRows({state,rows});return {reused_rows:[],acquired_rows:[],custody:result.custody};}
  const context=nativeContext(proof),manifest=state.manifest;
  demand(!context.intervalVisit,'Nested native interval visit');context.intervalVisit=true;
  let table,body,bodyPin,partIndex=0,failed=false;const reused=[],acquired=[];
  async function open(pin){
    const name=path.posix.join(path.posix.dirname(state.selection.manifest_path),pin.path);
    const chunks=proof.reader.treeRoute(name).length?proof.reader.stream(name,{expected:pin.sha256}):context.image.logicalStream(name,pin);
    const store=await openNativeWordStore(chunks,pin);
    for(const [key,p]of proof.reader.inventory)if(p.whole_body_consumed)context.inputInventory.set(key,{...p});
    return store;
  }
  try {
    const parts=manifest.parts.filter(p=>p.kind==='runs').sort((a,b)=>a.offset-b.offset);
    for(const y of rows){
      let complete=false;
      async function* intervals(){
        let end=0,count=0;
        const retained=proof.nativeRows.get(y);
        if(retained){reused.push(y);for(const run of retained.runs)yield run;complete=true;return;}
        if(!table){
          const pins=manifest.parts.filter(p=>p.kind==='rows');supported(pins.length===1,'Unsupported split native row table');
          table=await open(pins[0]);demand(table.length===manifest.size*2,'Incomplete whole native row table');
          let offset=0;for(let row=0;row<manifest.size;row++){
            demand(table.get(row*2)===offset,'Native row partition omitted a range');offset+=table.get(row*2+1);
          }demand(offset*2===manifest.runWords,'Native row partition omits complete runs');
        }
        const start=table.get(y*2)*2,stop=start+table.get(y*2+1)*2;
        let at=start;
        while(partIndex<parts.length&&parts[partIndex].offset+parts[partIndex].words<=start)partIndex++;
        for(let index=partIndex;index<parts.length&&parts[index].offset<stop;index++){
          const pin=parts[index];partIndex=index;
          demand(pin.offset<=at&&pin.offset+pin.words>at,'Incomplete containing native interval range');
          if(bodyPin!==pin){body?.close();body=null;body=await open(pin);bodyPin=pin;}
          const limit=Math.min(stop,pin.offset+pin.words);
          demand(at%2===0&&limit%2===0,'Split native interval words');
          for(;at<limit;at+=2){
            const a=body.get(at-pin.offset),b=body.get(at-pin.offset+1),bits=manifest.coordinateBits,mask=2**bits-1;
            const run=[a&mask,(b&mask)+1,(a>>>bits)+(b>>>bits)*2**(32-bits)];
            demand(run[0]>=end&&run[1]>run[0]&&run[1]<=manifest.size&&run[2]>0&&run[2]<=state.certificate.entries.length,
              'Invalid complete effective native interval/owner');
            end=run[1];count++;yield run;
          }
        }
        demand(at===stop&&count===table.get(y*2+1),'Incomplete containing native interval range');
        acquired.push(y);complete=true;
      }
      const iterator=intervals();
      try{await visit({y,runs:iterator});demand(complete,'Native interval visitor omitted complete row');}
      finally{await iterator.return();}
    }
    return {reused_rows:reused,acquired_rows:acquired,custody:{accepted_checkpoint:state.accepted_execution,
      new_whole_inputs:[...context.inputInventory.values()],retained_native_inputs:Array.from(proof.rebind.request.acquisition.native_inputs)}};
  }catch(error){failed=true;throw error;}
  finally{
    const errors=[];
    try{body?.close();}catch(error){errors.push(error);}
    try{table?.close();}catch(error){errors.push(error);}
    delete context.intervalVisit;
    if(!failed&&errors.length)throw errors[0];
  }
}

/** Exhaustive actual append-only transition. Never reacquires a full selection.
 * A valid baseline remains usable when an unsupported candidate needs cold work. */
export async function qualifyTransition({state,reader}) {
  const baseProof=getState(state,reader), {session}=baseProof,priorStores=new Set(session.stores);
  try {

    const selected=await readSelectionProducts(session,reader);
    const {oldRows,rowsPreserved,authoritiesPreserved}=normaliseTransitionSelection(state,selected);
    supported(same(nativeBaseSelection(selected.selection),state.baseSelection), 'Selected native/source/domain/owner base changed');
    const metadata=projectCheckpointMetadata(state,reader,selected.selection);
    const masked = new Set([...maskedLogicalSources(state.certificate,baseProof.physicalPaths),...metadata.paths]);
    supported(sameScientificRoutes(reader,baseProof.routes,session.executablePaths,masked), 'Selected input or present/absent route changed');
    for (const role of ['base_manifest','owner_roster'])
      supported(same(selected.sidecar.logical_asset_map[role],baseProof.selected.sidecar.logical_asset_map[role]), 'Selected original manifest/owner alias changed');
    demand(same(selected.ledger.parent_inventory,state.ledger.parent_inventory), 'Complete original source/scope denominator changed');
    demand(rowsPreserved,'Old complete ledger primitive, exception or native assignment removed/rebound');
    let authorities=new Map(baseProof.oldAuthorities);
    demand(authoritiesPreserved,'Old original authority removed/rebound');
    const addedEntries=selected.registry.entries.filter(entry => !authorities.has(entry.authority_sha256));

    authorities=await qualifyAppendedAuthorities(session,reader,state,selected,authorities,addedEntries,oldRows);
    const patches=[state.patch,...addedEntries.flatMap(entry=>authorities.get(entry.authority_sha256).patches)];

    demand(equalMergedPatchRows(selected.patch.rows,patches,state.manifest.size,state.certificate.entries.length),'Candidate patch omitted, invented or reassigned original native intervals');
    disjointPatchRows(state.patch.rows,addedEntries.flatMap(entry=>authorities.get(entry.authority_sha256).patches));
    // Rebase only genuinely inert logical rows. Newly qualified authorities may
    // consume that ordinary file; retain their physical paths so the exemption
    // cannot survive into another transition. No archived census is rewritten.
    const physicalPaths = new Set([...baseProof.physicalPaths,...[...reader.inventory.values()].map(p => p.path)]);
    const proof={...baseProof,reader,state,routes:currentMaskedRoutes(reader,baseProof.routes,masked),physicalPaths,
      nativeRows:baseProof.nativeRows.fork(),sourceTargets:baseProof.sourceTargets.fork(),nativeContext:null};
    // Projection authority is still the genuine baseline, while its operands
    // use this candidate's identical base routes. No SelectedSnapshot is forged.
    const operandState=newState(session,{...state,certificate:metadata.certificate,selected_commit:reader.version},{...proof});
    const operandProof=states.get(operandState); operandProof.state=operandState;
    let currentTargets;
    if (same(legacyRegistry(selected.registry,authorities),legacyRegistry(state.registry,baseProof.oldAuthorities))
      && same(selected.ledger.current_rebind,state.ledger.current_rebind)) currentTargets=baseProof.rebind.request.current_targets;
    else {
      const products=await rebindProducts(session,reader,selected.ledger,{size:state.manifest.size,ownerCount:state.certificate.entries.length});
      const missing=legacyRegistry(selected.registry,authorities).entries.filter(entry=>!authorities.get(entry.authority_sha256).patches);
      if(missing.length){
        const hydrated=await acceptedAuthorities(session,reader,{registry:{entries:missing}},{size:state.manifest.size,ownerCount:state.certificate.entries.length});
        for(const [key,value]of hydrated)authorities.set(key,value);
      }
      currentTargets=qualifyProjectedRebind(operandProof,selected,authorities,products).currentTargets;
      operandProof.rebind=products;
    }
    demand(same(selected.ledger.current_targets,currentTargets), 'Ledger complete current target roster differs from qualified operands');
    const additions=checkpointAdditions(selected,currentTargets);
    demand(selected.envelope.effective_reference.footprints_sha256===valueSha({domain:'worldatlas-effective-native-footprints:v2',
      base_reference:selected.envelope.base_reference,authority_registry_sha256:valueSha(selected.registry),
      ledger_sha256:selected.sidecar.logical_asset_map.ledger.sha256,components:repairIndexValues(selected.normalized.rows)}),
    'Candidate effective release does not bind the complete ledger/authority set');
    const priorReference=Object.fromEntries(['id','hierarchy_sha256','footprints_sha256'].map(k=>[k,state.certificate.binding.release[k]]));
    demand((same(selected.envelope.base_reference,baseProof.selected.envelope.base_reference)
      || metadata.reference && same(selected.envelope.base_reference,metadata.reference)
        && same(baseProof.selected.envelope.base_reference,priorReference)
        && priorReference.footprints_sha256===metadata.nativeReference.footprints_sha256)
      && selected.envelope.effective_reference.hierarchy_sha256===selected.envelope.base_reference.hierarchy_sha256,
    'Candidate silently changes complete base release or hierarchy');
    const {certificate,changedIds}=deriveQualifiedCoordinateDelta({certificate:metadata.certificate,oldAdditions:state.additions,additions,selection:selected.selection});
    const candidate=newState(session,{...state,selected_commit:reader.version,selection:selected.selection,certificate,
      additions,ledger:selected.ledger,registry:selected.registry,patch:selected.patch},
      {...operandProof,selected,oldAuthorities:new Map([...authorities].map(([key,p])=>[key,{entry:p.entry,nativeOnly:!!p.nativeOnly}])),
        physicalPaths:new Set([...physicalPaths,...[...reader.inventory.values()].map(p => p.path)])});
    const changed=new Set(changedIds);
    const changedNativeRows=changedPatchRows(state.patch.rows,selected.patch.rows);

    const transition=freeze({available:true,baseline:state,candidate,changedIds,changedNativeRows});
    transitions.set(transition,session); return transition;
  } catch (error) {
    closeStores(session,priorStores);
    if (error.reuseUnavailable) return unavailable(error.message,state);
    throw error;
  }
}

/** Consumer admission of the complete internally derived two-vintage scope.
 * Genuine state handles inside a caller-created wrapper do not authenticate its
 * changed-owner/neighbor plan. This is constant-time, not a repeated scan. */
export function authenticateTransition({transition}) {
  const session=transitions.get(transition);
  demand(session && !session.closed, 'Missing private qualified selected transition');
  demand(getState(transition.baseline).session===session
    && getState(transition.candidate).session===session,
  'Foreign transition state or invocation');
  return transition;
}

// Pure arithmetic only. This function cannot mint a checkpoint, projector or
// selected certificate capability; callers must still qualify all operands.
export function deriveCoordinateDelta({certificate,oldAdditions,additions,selection}) {
  // Public sequences provide storage, not an iterator/index consistency proof.
  // Bind every later lookup to the outer rows actually iterated here. Nested
  // stored geometry/intervals remain borrowed and retain their lifetime guards.
  const snapshot=source=>{
    demand(isNativeSequence(source),'Missing complete primitive sequence');
    const rows=[];
    for(const row of source){
      demand(rows.length<source.length,'Duplicate complete primitive identity');rows.push(row);
    }
    demand(rows.length===source.length,'Duplicate complete primitive identity');return rows;
  };
  return coordinateDelta({certificate,oldAdditions:snapshot(oldAdditions),additions:snapshot(additions),selection},
    row=>nativeOnlyComponent(row,valueSha));
}

// The only caller is qualifyTransition, after private ledger admission proves
// every candidate row and old projected operands belong to a genuine live state.
// checkpointAdditions borrows immutable admitted storage: its iterator and index
// are the same rows, and all native semantics were already checked. Keep the
// common target/owner/base, duplicate and old projected-equality guards below;
// in particular raw old-row equality does not authorize a changed legacy rebind.
function deriveQualifiedCoordinateDelta(operands) {
  return coordinateDelta(operands,row=>row.representation==='native-cells');
}
function coordinateDelta({certificate,oldAdditions,additions,selection},nativeComponent) {
  const oldById=new Set(oldAdditions.map(repairComponentKey)),ordinals=new Map();let ordinal=0;
  for(const row of additions)ordinals.set(repairComponentKey(row),ordinal++);
  demand(oldById.size===oldAdditions.length && ordinals.size===additions.length,
    'Duplicate complete primitive identity');
  for (const row of oldAdditions) {
    const at=ordinals.get(repairComponentKey(row));
    demand(same(row,at===undefined?undefined:additions.at(at)),'Old effective primitive/base geometry changed');
  }
  const rows=new Map(certificate.entries.map(row => [row[0],row])),byTarget=new Map(),changedIds=new Set();
  ordinal=0;
  for (const row of additions) {
    demand(rows.has(row.target_id) && row.pixelIndex===rows.get(row.target_id)[1]
      && row.base_geometry_sha256===rows.get(row.target_id)[7] && (nativeComponent(row) || row.geometry_sha256===valueSha(row.geometry)),
    'Appended primitive targets a stale base, changed geometry or different owner');
    let group=byTarget.get(row.target_id);if(!group){group={all:[],added:[]};byTarget.set(row.target_id,group);}
    group.all.push(ordinal);
    if(!oldById.has(repairComponentKey(row))){group.added.push(ordinal);changedIds.add(row.target_id);}
    ordinal++;
  }
  const entries=certificate.entries.map(row => {
    if (!changedIds.has(row[0])) return row;
    const group=byTarget.get(row[0]),all=nativeSequence(group.all.length,
      function*(){for(const at of group.all)yield additions.at(at);});
    const bounds=(a,b)=>[Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.max(a[2],b[2]),Math.max(a[3],b[3])];
    let box=row[9].reduce(bounds);
    for(const at of group.added){const p=additions.at(at);
      for(const next of nativeComponent(p)?[p.native_bounds]:coordinateBounds(p.geometry))box=bounds(box,next);}
    const next=[...row]; next[8]=valueSha({base_geometry_sha256:row[7],additions:all});
    next[9]=[box];
    return next;
  });
  const result={...certificate,binding:{...certificate.binding,selection},entries};
  return freeze({certificate:result,changedIds:[...changedIds].sort()});
}

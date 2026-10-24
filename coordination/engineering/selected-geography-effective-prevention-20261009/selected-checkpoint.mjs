// Current final-bank comparison and complete new-positive source qualification.
// Historical cumulative reconstruction remains in Git history, not this runtime.

import path from 'node:path';

import {createHash} from 'node:crypto';

import {gunzipSync} from 'node:zlib';

import os from 'node:os';

import {admitNativePatchStore, admitNativeLedgerStore, admitNativeEnvelopeStore, admitNativeMetadataStore, decodedNativeChunks, authenticatedDecodedNativeChunks, canonicalNativeJsonChunks} from '../../../scripts/native-patch-store.mjs';

import {nativeSequence, isNativeSequence} from '../../../src/native-grid.js';

import {ImmutableReader, decodeVisibilityLatitudes, readSelectedGeometryBank, compareIntervals} from '../../../scripts/check-effective-geographic-regression.mjs';

import {nativeOnlyComponent} from '../../../src/native-grid.js';

import {finalBankSelection, scientificNativeSelection, validateReferenceMetadataHeader} from '../../../src/reference-metadata.js';

import {readPreparedFinalOwnership} from '../../../scripts/package-startup-ownership.mjs';

import {validateReferenceMetadataProjection} from '../../../scripts/selected-reference-metadata.mjs';

import {valueSha, nativeBaseSelection, authorityRegistry, readRegistryAuthorityInputs, verifyCompletedSourceTargetNativeAuthority, projectCompletedGeometryBody, restoreCompletedGeometryBody, completedGeometryCustody} from './selected-neighbor-prevention.mjs';

const demand = (ok, message) => { if (!ok) throw Error(message); };

const sha = body => createHash('sha256').update(body).digest('hex');

const same = (a,b) => a === undefined || b === undefined ? a === b : valueSha(a) === valueSha(b);

const hash = x => typeof x === 'string' && /^[a-f0-9]{64}$/.test(x);

const commit = x => typeof x === 'string' && /^[a-f0-9]{40}$/.test(x);

const safe = x => typeof x === 'string' && x.length > 0 && !x.includes('\\') && !x.includes('\0') && !path.posix.isAbsolute(x) && x.split('/').every(p => p && p !== '.' && p !== '..');

const freeze = x => { if (x && typeof x === 'object' && !Object.isFrozen(x)) { Object.values(x).forEach(freeze); Object.freeze(x); } return x; };

const keys = (x, expected, message) => demand(x && same(Object.keys(x).sort(), expected.split(',').sort()), message);

const supported = (ok, message) => { if (!ok) { const error = Error(message); error.reuseUnavailable = true; throw error; } };

function sessionCheck(reader, session) {
  demand(reader instanceof ImmutableReader, 'Checkpoint requires an immutable reader');
  if (session) demand(!session.closed && reader.invocation === session.invocation
    && reader.repo === session.repo, 'Foreign or expired checkpoint invocation');
}

// Some original body descriptors predate explicit Git custody fields. Their
// declared byte/hash identities remain mandatory; only absent mode/OID may be
// obtained from the exact original Git path, never from a current alias.
const missingMetadata = p => !Object.hasOwn(p, 'mode') || !Object.hasOwn(p, 'git_blob_oid');
function pin(p) {
  demand(p && commit(p.commit) && safe(p.path)
    && (!Object.hasOwn(p,'mode') || ['100644','100755'].includes(p.mode))
    && (!Object.hasOwn(p,'git_blob_oid') || /^[a-f0-9]{40}$/.test(p.git_blob_oid))
    && Number.isSafeInteger(p.bytes) && p.bytes >= 0 && hash(p.sha256), 'Incomplete immutable checkpoint pin');
  if (Object.hasOwn(p,'decoded_bytes') || Object.hasOwn(p,'decoded_sha256')) demand(Number.isSafeInteger(p.decoded_bytes)
    && p.decoded_bytes > 0 && hash(p.decoded_sha256),
  'Incomplete whole decoded checkpoint pin');
}
function metadataPin(p, actual) {
  demand(['100644','100755'].includes(actual.mode) && commit(actual.git_blob_oid)
    && (!Object.hasOwn(p,'mode') || p.mode===actual.mode)
    && (!Object.hasOwn(p,'git_blob_oid') || p.git_blob_oid===actual.git_blob_oid),
    'Checkpoint original mode/OID differs: '+p.path);
  return {...p,mode:actual.mode,git_blob_oid:actual.git_blob_oid};
}
async function acquireInputs(session, reader, pins) {
  pins.forEach(pin);
  const complete=[];
  for(const p of pins) {
    if(!missingMetadata(p)){complete.push(p);continue;}
    let known=true;try{reader.git('--no-lazy-fetch','cat-file','-e',p.commit+'^{commit}');}catch{known=false;}
    if(known){
      const row=reader.git('ls-tree','-z',p.commit,'--',p.path).toString();
      const match=/^(100644|100755) blob ([a-f0-9]{40})\t([^\0]+)\0$/.exec(row);
      demand(match&&match[3]===p.path,'Missing ordinary original checkpoint path: '+p.path);
      complete.push(metadataPin(p,{mode:match[1],git_blob_oid:match[2]}));
    }else{
      await reader.acquireOriginalPaths([p]);
      const actual=reader.descriptor(p.path,p.commit);
      metadataPin(p,actual);
      demand(actual.bytes===p.bytes,'Checkpoint original whole size differs: '+p.path);
    }
  }
  if (complete.length) await session.acquireAuthorityInputs?.(reader, complete);
}

function resolvePin(reader, p) {
  pin(p);
  let version = p.commit;
  // A descriptor without custody fields has no authenticated current alias.
  if(!missingMetadata(p))try { reader.git('--no-lazy-fetch','cat-file','-e',version+'^{commit}'); } catch { version = reader.version; }
  const actual = reader.descriptor(p.path, version);
  metadataPin(p,actual);
  demand(actual.bytes === p.bytes,
    'Checkpoint whole mode/OID/size or historical alias changed: '+p.path);
  return {actual, version};
}

function readBody(session, reader, p, {json = true} = {}) {
  const {version} = resolvePin(reader, p);

  const encoded = reader.read(p.path, {version, expected:p.sha256});
  return decodeBody(p,encoded,{json});
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

function closeStores(session,keep=new Set()) {
  let failure;
  for(const store of session.stores??[])if(!keep.has(store)){
    try{store.close();}catch(error){failure??=error;}session.stores.delete(store);
  }
  if(failure)throw failure;
}

const decodedChunks=decodedNativeChunks;

const custodyChunks=(chunks,p)=>authenticatedDecodedNativeChunks(chunks,p,{directory:os.tmpdir(),footer:true});

async function storedProduct(session,reader,p,domain,ledger,restored) {
  let chunks;
  if(restored!==undefined)chunks=(function*(){for(const chunk of canonicalNativeJsonChunks(restored))yield Buffer.from(chunk);})();
  else {const {version}=resolvePin(reader,p);chunks=reader.stream(p.path,{version,expected:p.sha256});}
  if(ledger==='custody')chunks=custodyChunks(chunks,p);else if(p.decoded_bytes)chunks=decodedChunks(chunks);
  let store;try{store=await (ledger==='custody'?admitNativeMetadataStore:ledger==='envelope'?admitNativeEnvelopeStore:ledger?admitNativeLedgerStore:admitNativePatchStore)({chunks,
    expected:{bytes:p.decoded_bytes??p.bytes,sha256:p.decoded_sha256??p.sha256},
    directory:os.tmpdir(),...domain,...(ledger==='custody'?{metadataArrays:['complete_cold_custody','effective_additions','inventory']}:{}),...(ledger==='constructor'?{rowField:'ledger_rows'}:{})});
  }catch(error){if(ledger==='custody'&&p.decoded_bytes&&error?.message==='Complete native JSON identity differs')throw Error('Checkpoint whole decoded output is corrupt');throw error;}
  (session.stores??=new Set()).add(store);
  if(ledger==='envelope'||ledger==='custody')return store.metadata;
  const wrap=row=>Object.freeze({y:row.y,runs:nativeSequence(row.count,()=>store.intervals(row))});
  const componentView=component=>{
    const view=Object.freeze({...store.componentMetadata(component),
      ...(component.hasNativeRows?{native_rows:nativeSequence(component.rowCount,
        function*(){for(const row of store.componentRows(component))yield wrap(row);})}:{})});
    // The parser authenticated every byte and computed this exact canonical
    // component identity. Only this invocation-owned immutable view may use it.
    (session.componentIdentities??=new WeakMap()).set(view,{store,sha256:component.canonical_sha256});
    return view;
  };
  const product=Object.freeze(ledger?{...store.metadata,[ledger==='constructor'?'ledger_rows':'rows']:nativeSequence(store.componentCount,
    function*(){for(const component of store.componentEntries())yield componentView(component);},
    {entryAt:ordinal=>componentView(store.componentAt(ordinal))})}:
    {...store.metadata,rows:nativeSequence(store.rowCount,
      function*(){for(const row of store.rowEntries())yield wrap(row);},
      {rowAt:y=>{const row=store.rowAt(y);return row?wrap(row):undefined;}})});
  // This exact frozen view only reads its invocation-owned immutable store.
  // Admission already hashed its complete canonical value, not its wire bytes.
  (session.productStores??=new WeakMap()).set(product,store);
  return product;
}

async function readSelectedPreparedBank(session,reader,{selection,manifest,ownerCount,indexPath,indexRaw,selected}) {
  const index=JSON.parse(indexRaw);
  const root=path.posix.dirname(indexPath),proof=index.preparedOwnership;
  demand(Array.isArray(index.files)&&Array.isArray(proof?.context_parts)&&Array.isArray(index.pixelMap?.parts),
    'Missing complete selected final bank');
  // Every declared current URL has its actual ordinary committed tree identity.
  // There is no body/descriptor borrowed from a historical repair selector.
  const roster=new Map(index.files.map(p=>[root+'/'+p.path,p]));
  demand(roster.size===index.files.length,'Duplicate selected final bank member');
  const tree=reader.git('--literal-pathspecs','ls-tree','-r','-z',reader.version,'--',root).toString('utf8').split('\0').filter(Boolean);
  demand(tree.length===roster.size+1,'Selected final bank whole tree roster differs');
  for(const entry of tree){const match=/^(100644) blob ([a-f0-9]{40})\t(.+)$/.exec(entry);
    demand(match&&(match[3]===indexPath||roster.has(match[3])),'Unknown/nonordinary selected final bank path');}
  const routes=new Map(tree.map(line=>{const [meta,name]=line.split('\t');return [name,meta.split(' ')];}));
  const consumed=[...index.pixelMap.parts,...proof.context_parts].map(p=>{
    const name=root+'/'+p.path,member=roster.get(name),actual=routes.get(name);
    demand(member&&actual?.[0]==='100644'&&(p.bytes===undefined||member.bytes===p.bytes)&&member.sha256===p.sha256,
      'Selected final bank physical body differs');
    return {commit:reader.version,path:name,mode:actual[0],git_blob_oid:actual[2],bytes:member.bytes,sha256:p.sha256};
  });
  await acquireInputs(session,reader,consumed);
  const bank=await readPreparedFinalOwnership({indexRaw,manifest,manifestSha:scientificNativeSelection(selection).sha256,selected,ownerCount,
    read:p=>reader.read(root+'/'+p.path,{expected:p.sha256})});
  return {...bank,indexIdentity:{path:indexPath,bytes:indexRaw.length,sha256:sha(indexRaw)}};
}

function selectedRuntimeReferenceMetadata(reader,selection,manifest) {
  const pin=selection.reference_projection;if(pin===undefined)return undefined;
  const raw=reader.read(pin.path,{expected:pin.sha256});
  demand(raw.length===pin.bytes,'Selected projection whole length differs');
  const {native,reference}=validateReferenceMetadataHeader(JSON.parse(raw),{selection,manifest});
  return {version:1,asset:{path:'reference-metadata/current.json',bytes:raw.length,sha256:sha(raw)},
    native_reference:native,reference};
}

async function readFinalSelectionProducts(session,reader,selection,ownerCount) {
  const hook=finalBankSelection(selection),native=scientificNativeSelection(selection);
  const manifestRaw=reader.read(native.manifest_path,{expected:native.sha256}),manifest=JSON.parse(manifestRaw);
  const indexRaw=reader.read(hook.path,{expected:hook.sha256}),index=JSON.parse(indexRaw),proof=index.preparedOwnership;
  demand(indexRaw.length===hook.bytes&&index.version===3,'Final selection index identity/profile differs');
  const referenceMetadata=selectedRuntimeReferenceMetadata(reader,selection,manifest);
  demand(same(index.referenceMetadata,referenceMetadata)&&(!referenceMetadata||same(proof.base_reference,referenceMetadata.reference)),
    'Final index reference metadata differs from its actual selected projection');
  const selected={finalBank:hook,base:proof.base_reference,reference_release:selection.reference,referenceMetadata};
  const bank=await readSelectedPreparedBank(session,reader,{selection,manifest,ownerCount:ownerCount??proof.owners,indexPath:hook.path,indexRaw,selected});
  return {profile:2,selection,manifest,index,indexRaw,bank,reference:proof.base_reference,
    binding:{index:{path:hook.path,bytes:hook.bytes,sha256:hook.sha256},manifest_sha256:native.sha256,
      effective_reference:selection.reference}};
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

function acceptedAuthorityIdentities(values) {
  demand(Array.isArray(values),'Missing accepted authority identities');
  let prior='';
  for(const pair of values){
    demand(Array.isArray(pair)&&pair.length===2&&pair.every(hash)&&pair[0]>prior,
      'Duplicate, unordered or rebound accepted authority identity');prior=pair[0];
  }
  return values;
}

// Resolve geometry only from the accepted original N roster, even when the
// accepted current context already materializes that owner. Candidate paths are
// locating hints; their pins/geometry never establish the original authority.
async function completedOriginalGeometry(session,reader,state,sourcePaths) {
  const selection=state.selection,source=scientificNativeSelection(selection).selected_geography;
  demand(source&&Array.isArray(sourcePaths)&&sourcePaths.length>0&&new Set(sourcePaths).size===sourcePaths.length,
    'Completed geometry needs an original containing-source roster');
  const route=reader.treeRoute(source.path),match=/^(100644) blob ([a-f0-9]{40})\t/.exec(route);
  demand(match,'Completed geometry original index is not ordinary');
  await acquireInputs(session,reader,[{commit:reader.version,path:source.path,mode:match[1],git_blob_oid:match[2],bytes:source.bytes,sha256:source.sha256}]);
  const bank=readSelectedGeometryBank(reader,selection);
  demand(bank.locations===state.bank.features.length&&bank.footprints_sha256===state.manifest.footprints_sha256,
    'Completed geometry original owner/source scope differs');
  await acquireInputs(session,reader,[bank.world_index]);
  const world=readBody(session,reader,bank.world_index),paths=world.parts.map(p=>'data/'+p),roster=new Map();
  demand(new Set(paths).size===paths.length,'Duplicate original geometry containing route');
  for(const p of [...bank.unchanged_files,...bank.overrides]){
    const name=p.logical_path??p.path;pin(p);
    demand(paths.includes(name)&&!roster.has(name),'Foreign original geometry containing route');roster.set(name,p);
  }
  demand(roster.size===paths.length,'Incomplete original geometry containing roster');
  const found=new Map();
  for(const name of sourcePaths){
    const p=roster.get(name);demand(p,'Completed geometry source is outside accepted original N');
    await acquireInputs(session,reader,[p]);const collection=readBody(session,reader,p);
    demand(collection.type==='FeatureCollection'&&Array.isArray(collection.features),'Incomplete original geometry containing body');
    for(const feature of collection.features){
      demand(typeof feature.id==='string'&&!found.has(feature.id),'Duplicate original geometry target');found.set(feature.id,feature.geometry);
    }
  }
  return slot=>{
    const owner=state.bank.features[slot.pixelIndex-1],geometry=found.get(slot.target_id);
    demand(owner?.id===slot.target_id&&owner.pixelIndex===slot.pixelIndex&&geometry
      &&(owner.geometry===null||same(owner.geometry,geometry)),'Missing or changed accepted original geometry/owner');
    return geometry;
  };
}
function completedAcceptedLattice(session,reader,state) {
 let acquired;
 return ()=>acquired??=(async()=>{
  demand(state.manifest.size===262166&&state.manifest.method==='native-linear-evenodd-first-owner-v1',
    'Completed bounds require the accepted fixed native contract');
  const p=state.manifest.native_latitudes;
  await acquireInputs(session,reader,[p]);
  const latitudes=decodeVisibilityLatitudes(reader.read(p.path,{version:resolvePin(reader,p).version,expected:p.sha256}),p,state.manifest.size);
  return {size:state.manifest.size,latitudes};
 })();
}
function knownProjectionOrigin(reader,p) {
  let known=true;try{reader.git('--no-lazy-fetch','cat-file','-e',p.commit+'^{commit}');}catch{known=false;}
  if(known){const row=reader.git('--literal-pathspecs','ls-tree','-z',p.commit,'--',p.path).toString();
    demand(row===`${p.mode} blob ${p.git_blob_oid}\t${p.path}\0`,'Known completed geometry origin differs');}
}
// Authoring only: caller establishes accepted commit provenance. Original
// qualification artifacts are read, not regenerated; publication remains a new
// honest registry hook. Full local originals remain the finalizer's inputs.
export async function projectCompletedAuthorityRegistry({beforeReader,registry,readOriginal}) {
  sessionCheck(beforeReader);
  const session={invocation:beforeReader.invocation,repo:beforeReader.repo,closed:false,stores:new Set()};
  try {
    demand(registry.completed_geometry_custody===undefined,'Completed geometry registry is already projected');
    const selection=beforeReader.json('data/ownership-selection.json');demand(finalBankSelection(selection),'Accepted final bank required for geometry custody');
    const state=await readFinalSelectionProducts(session,beforeReader,selection);
    const rows=[],lattice=completedAcceptedLattice(session,beforeReader,state);
    for(const entry of authorityRegistry(registry).values()){
      demand(entry.completed_constructor,'Completed geometry custody cannot qualify unfinished authority');
      const binding=JSON.parse(await readOriginal(entry.source_authority));
      demand(binding.kind==='source-target-native-custody-v1','Completed source-target binding required');
      const record={authority_sha256:entry.authority_sha256};
      for(const role of ['completed_constructor','source_evidence']){
        const original=role==='completed_constructor'?entry.completed_constructor:binding.source_evidence;
        record[role]=projectCompletedGeometryBody(await readOriginal(original),original,role,{omitNativeBounds:role==='completed_constructor'});
      }
      const geometry=await completedOriginalGeometry(session,beforeReader,state,record.source_evidence.body.source_membership?.parts?.map(p=>p.path));
      for(const role of ['completed_constructor','source_evidence'])
        await restoreCompletedGeometryBody(record[role],role,record[role].original,geometry,lattice);
      rows.push(record);
    }
    return {...registry,completed_geometry_custody:rows};
  }finally{session.closed=true;closeStores(session);}
}

async function appendAuthority(session, reader, entry, domain, custody) {
  const child = new ImmutableReader(reader.repo,reader.version,{invocation:reader.invocation,gitExecutable:reader.gitExecutable});
  child.inventory=reader.inventory; // retain actual appended-producer inputs without reopening them
  let proof, evidence;
  if(entry.completed_constructor!==undefined){
    await acquireInputs(session,child,[entry.rule_preimage,entry.source_authority]);
    const {preimage,binding}=readRegistryAuthorityInputs(child,entry);
    if(binding?.kind==='source-target-native-custody-v1'){
      let restored;
      if(custody){
        demand(same(custody.source_evidence?.original,binding.source_evidence),'Completed geometry source pin differs');
        knownProjectionOrigin(child,entry.completed_constructor);knownProjectionOrigin(child,binding.source_evidence);
        const geometry=await completedOriginalGeometry(session,session.beforeReader,session.beforeState,
          custody.source_evidence.body?.source_membership?.parts?.map(p=>p.path));
        const lattice=completedAcceptedLattice(session,session.beforeReader,session.beforeState);
        restored={};
        for(const role of ['completed_constructor','source_evidence'])
          restored[role]=await restoreCompletedGeometryBody(custody[role],role,
            role==='completed_constructor'?entry.completed_constructor:binding.source_evidence,geometry,lattice);
        (session.completedGeometryCustody??=[]).push({authority_sha256:entry.authority_sha256,
          kind:'original-n-reconstructed-completed-bodies-v1',originals:[entry.completed_constructor,binding.source_evidence],
          geometry_slots:custody.source_evidence.slots});
      }
      await acquireInputs(session,child,[...(custody?[]:[entry.completed_constructor,binding.source_evidence]),binding.native_patch]);
      const constructed=await storedProduct(session,child,entry.completed_constructor,domain,'constructor',restored?.completed_constructor);
      evidence=await storedProduct(session,child,binding.source_evidence,domain,'envelope',restored?.source_evidence);
      const candidate=await storedProduct(session,child,binding.native_patch,domain,false);
      proof=verifyCompletedSourceTargetNativeAuthority({constructed,preimage,binding,evidence,candidate});
    }
  }
  if(!proof){
    throw Error('Final-bank positive changes require completed native source-target authority');
  }

  return {entry,nativeOnly:proof.original_pins.source_evidence!==undefined,patches:proof.native_proof.native_patches,ledger:proof.original_ledger,
    contract:proof.native_proof.native_contract,source_scope_ids:proof.source_scope_ids,
    referenceSources:evidence?.source_membership?.parts?.map(p=>p.path)??[]};
}

async function qualifyFinalPositiveEvidence(session,reader,state,selected,priorIdentities,ownerCount=state.certificate?.entries.length) {
  const hook=selected.selection.change_evidence;
  if(!hook)return {identities:priorIdentities,components:[],patches:[],referenceSources:[]};
  demand(state.version===2,'Representation migration cannot add scientific cells');
  await acquireInputs(session,reader,[hook]);
  const registry=readBody(session,reader,hook);
  const custody=completedGeometryCustody(registry);
  const entries=[...authorityRegistry(registry).values()],seen=new Set(priorIdentities.map(pair=>pair[0]));
  const components=[],patches=[],referenceSources=new Set(),identities=priorIdentities.map(pair=>[...pair]);
  const contract=Object.fromEntries(['size','coordinateBits','method','native_latitudes','hierarchy_sha256','original_assets'].map(k=>[k,state.manifest[k]]));
  const native={id:state.manifest.geographic_release,footprints_sha256:state.manifest.footprints_sha256,hierarchy_sha256:state.manifest.hierarchy_sha256};
  for(const entry of entries){
    demand(!seen.has(entry.authority_sha256),'Candidate repeats an already accepted authority identity');seen.add(entry.authority_sha256);
    demand(entry.policy_id==='retained-source-literal-additions'&&entry.policy_version===1,'Unsupported appended source policy');
    const qualified=await appendAuthority(session,reader,entry,{size:state.manifest.size,ownerCount},custody.get(entry.authority_sha256));
    supported(qualified.nativeOnly,'Final-bank positive changes require original native source-target authority');
    demand(same(qualified.contract,contract)&&qualified.ledger.parent_inventory===undefined,
      'New native authority changed the original physical/source contract');
    demand(qualified.patches.every(p=>same(p.base_reference,selected.reference)
      ||selected.selection.reference_projection&&same(p.base_reference,native)),
      'New native authority belongs to a different reference');
    for(const row of qualified.ledger.rows){
      if(row.disposition==='assigned'){
        const component={...row,authority_sha256:entry.authority_sha256,rule_sha256:entry.rule_sha256};
        demand(nativeOnlyComponent(component,valueSha),'New positive component is not an admitted native cell set');components.push(component);
      }
      // Nonpositive/held dispositions remain in the complete authenticated new
      // proof. They grant no context or word mutation and are not replay inputs.
    }
    for(const name of qualified.referenceSources)referenceSources.add(name);
    patches.push(...qualified.patches);identities.push([entry.authority_sha256,valueSha(entry)]);
  }
  identities.sort((a,b)=>a[0].localeCompare(b[0]));acceptedAuthorityIdentities(identities);
  return {identities,components,patches,referenceSources:[...referenceSources]};
}

function finalPatchRows(patches,size,ownerCount) {
  const groups=new Map();
  for(const patch of patches){completeRows(patch.rows,size,ownerCount);
    for(const row of patch.rows){const runs=groups.get(row.y)??[];runs.push(...Array.from(row.runs,run=>[...run]));groups.set(row.y,runs);}}
  const rows=[...groups].sort((a,b)=>a[0]-b[0]).map(([y,runs])=>({y,runs:runs.sort((a,b)=>a[0]-b[0]||a[1]-b[1]||a[2]-b[2])}));
  // Even equal-owner overlap is not a new disjoint scientific addition.
  completeRows(rows,size,ownerCount);
  return rows.map(({y,runs})=>{const joined=[];for(const run of runs){const last=joined.at(-1);
    if(last&&last[1]===run[0]&&last[2]===run[2])last[1]=run[1];else joined.push([...run]);}return {y,runs:joined};});
}

function sameWords(a,b){return a.length===b.length&&a.every((word,i)=>word===b[i]);}

function finalRowChanges(before,after,y,owners) {
  const values=[...compareIntervals(before,after,{row:y,ownersBefore:owners,ownersAfter:owners}),
    ...compareIntervals(after,before,{row:y,ownersBefore:owners,ownersAfter:owners})
      .filter(p=>p.candidate_owner===null).map(p=>({...p,previous_owner:null,candidate_owner:p.previous_owner}))]
    .sort((a,b)=>a.start-b.start);
  const result=[];
  for(const value of values){const prior=result.at(-1);
    if(prior&&prior.end===value.start&&prior.previous_owner===value.previous_owner&&prior.candidate_owner===value.candidate_owner)prior.end=value.end;
    else result.push(value);
  }
  return result;
}

function finalWordChanges(before,after,owners) {
  demand(before.size===after.size&&before.coordinateBits===after.coordinateBits,'Final map numerical domain changed');
  const changes=[],bits=before.coordinateBits,mask=2**bits-1;
  const decode=(bank,y)=>{const result=[],start=bank.rows[y*2],stop=start+bank.rows[y*2+1];
    for(let i=start;i<stop;i++){const a=bank.runs[i*2],b=bank.runs[i*2+1];
      result.push([a&mask,(b&mask)+1,(a>>>bits)+(b>>>bits)*2**(32-bits)]);}
    return result;};
  for(let y=0;y<before.size;y++){
    const a=before.rows[y*2]*2,b=after.rows[y*2]*2,length=before.rows[y*2+1]*2;
    if(length===after.rows[y*2+1]*2&&sameWords(before.runs.subarray(a,a+length),after.runs.subarray(b,b+length)))continue;
    changes.push(...finalRowChanges(decode(before,y),decode(after,y),y,owners));
  }
  return changes;
}

function finalContextRows(features) {
  const rows=new Map();
  for(const feature of features)for(const row of feature.finishedFootprint?.native_rows??[]){
    const runs=rows.get(row.y)??[];runs.push(...row.runs.map(([start,end])=>[start,end,feature.pixelIndex]));rows.set(row.y,runs);
  }
  for(const runs of rows.values())runs.sort((a,b)=>a[0]-b[0]||a[1]-b[1]||a[2]-b[2]);
  return rows;
}

export async function compareAcceptedFinalBank({beforeReader,afterReader,acquireAuthorityInputs,acquireMetadataInputs}) {
  sessionCheck(beforeReader);
  const session={invocation:beforeReader.invocation,repo:beforeReader.repo,closed:false,stores:new Set(),acquireAuthorityInputs};
  sessionCheck(afterReader,session);
  try {
    const beforeSelection=beforeReader.json('data/ownership-selection.json');
    const afterSelection=afterReader.json('data/ownership-selection.json');
    demand(finalBankSelection(beforeSelection)&&finalBankSelection(afterSelection),
      'Direct final-map comparison requires accepted and proposed final banks');
    demand(same(nativeBaseSelection(beforeSelection),nativeBaseSelection(afterSelection)),
      'Final bank changed original native/source/domain contract');
    const before=await readFinalSelectionProducts(session,beforeReader,beforeSelection);
    session.beforeReader=beforeReader;session.beforeState=before;
    const count=before.bank.features.length;
    const after=await readFinalSelectionProducts(session,afterReader,afterSelection,count);
    demand(same(before.index.compatibility_files,after.index.compatibility_files),
      'Final bank changed the accepted fixed compatibility roster');
    for(const member of before.index.compatibility_files){
      const old=beforeReader.treeRoute(path.posix.dirname(before.bank.indexIdentity.path)+'/'+member.path);
      const current=afterReader.treeRoute(path.posix.dirname(after.bank.indexIdentity.path)+'/'+member.path);
      // Compare object identity, not path spelling or missing local body size.
      demand(old.split('\t')[0]===current.split('\t')[0], 'Final bank rebound an accepted compatibility body');
    }
    let sources;
    const originalSources=async()=>{
      if(sources)return sources;
      const source=scientificNativeSelection(beforeSelection).selected_geography;
      const route=beforeReader.treeRoute(source.path),match=/^(100644) blob ([a-f0-9]{40})\t/.exec(route);
      demand(match,'Original source index is not an ordinary accepted file');
      await acquireInputs(session,beforeReader,[{commit:beforeReader.version,path:source.path,mode:match[1],
        git_blob_oid:match[2],bytes:source.bytes,sha256:source.sha256}]);
      const bank=readSelectedGeometryBank(beforeReader,beforeSelection);
      demand(bank.locations===count&&bank.footprints_sha256===before.manifest.footprints_sha256,
        'Original source index differs from accepted owner scope');
      await acquireInputs(session,beforeReader,[bank.world_index]);
      const world=readBody(session,beforeReader,bank.world_index);
      const paths=world.parts.map(p=>'data/'+p);
      demand(new Set(paths).size===paths.length,'Duplicate original source containing route');
      sources=new Map();
      for(const p of [...bank.unchanged_files,...bank.overrides]){
        pin(p);const name=p.logical_path??p.path;
        demand(paths.includes(name)&&!sources.has(name),'Foreign or duplicate original source route');sources.set(name,p);
      }
      demand(sources.size===paths.length,'Incomplete original source containing roster');
      return sources;
    };
    let reference=before.reference,properties=new Map();
    if(!same(beforeSelection.reference_projection,afterSelection.reference_projection)){
      demand(afterSelection.reference_projection,'Removing a selected metadata application is unsupported');
      const projection=afterReader.json(afterSelection.reference_projection.path,{expected:afterSelection.reference_projection.sha256});
      const previous=beforeSelection.reference_projection
        ?beforeReader.json(beforeSelection.reference_projection.path,{expected:beforeSelection.reference_projection.sha256}):null;
      const originalProperties=new Map((previous?.location_changes??[]).map(row=>[row.location_id,row.before_properties]));
      const owners=before.bank.features.map(f=>({id:f.id,index:f.pixelIndex,
        province_id:(originalProperties.get(f.id)??f.properties).parent_id}));
      const roster=await originalSources();
      const inputs=[projection.hierarchy.before,projection.hierarchy.after,...projection.receipts,
        ...projection.source_updates.flatMap(update=>[update.before,update.after])];
      await acquireInputs(session,afterReader,inputs);
      const applied=validateReferenceMetadataProjection({projection,selection:afterSelection,manifest:before.manifest,
        owners,originalSources:roster,read:p=>afterReader.read(p.path,{version:resolvePin(afterReader,p).version,expected:p.sha256})});
      // Keep the existing receipt/release/current-tree joins without reopening
      // original native transports, artifact receipts or all source bodies.
      const readMetadata=async(name,expected)=>{
        await acquireMetadataInputs?.(afterReader,[{path:name,...(expected?{sha256:expected}:{})}]);
        return afterReader.read(name,{...(expected?{expected}:{})});
      };
      const pointer=JSON.parse(await readMetadata('data/geographic-releases/current-manifest.json'));
      demand(safe(pointer.path)&&hash(pointer.sha256),'Unbound selected geographic release');
      const encoded=await readMetadata('data/geographic-releases/'+pointer.path,pointer.sha256);
      demand(encoded.length>=18&&encoded[0]===31&&encoded[1]===139,'Invalid whole reference release gzip');
      const decodedBytes=encoded.readUInt32LE(encoded.length-4),decoded=gunzipSync(encoded,{maxOutputLength:decodedBytes});
      demand(decoded.length===decodedBytes,'Whole reference release decoded size differs');
      const releases=JSON.parse(decoded).releases;
      demand(Array.isArray(releases)&&releases.length>0&&new Set(releases.map(r=>r.id)).size===releases.length,'Incomplete selected release roster');
      const native=releases.find(r=>r.id===scientificNativeSelection(beforeSelection).release_id),current=releases.at(-1);
      const identity=row=>Object.fromEntries(['id','footprints_sha256','hierarchy_sha256'].map(k=>[k,row?.[k]]));
      demand(same(identity(native),applied.nativeReference)&&same(identity(current),applied.reference),
        'Current reference metadata differs from the actual selected releases');
      const receipts=new Set(Object.values(current.metadata?.metadata_migration_sha256??{}));
      demand(applied.releaseReceipts.every(p=>receipts.has(p.sha256)),'Current reference release does not bind every applied metadata receipt');
      const matches=(name,p)=>afterReader.treeRoute(name)===p.mode+' blob '+p.git_blob_oid+'\t'+name+'\0';
      demand(projection.hierarchy.after.path==='data/hierarchy.json'&&projection.hierarchy.after.encoding===undefined
        &&matches('data/hierarchy.json',projection.hierarchy.after),'Current hierarchy differs from the metadata application');
      const source=readSelectedGeometryBank(beforeReader,beforeSelection);
      demand(matches('data/world-index.json',source.world_index),'Source bank original index differs from current complete index');
      for(const [name,p] of roster){
        const update=applied.sourceUpdates.get(name);
        if(update)demand(update.after.path===name&&update.after.encoding===undefined&&matches(name,update.after),
          'Current complete source differs from the metadata application');
        else if(!p.logical_path)demand(matches(name,p),'Current original containing body differs without a complete metadata application');
      }
      demand(applied.owners.every((owner,i)=>owner.id===after.bank.features[i].id&&owner.index===after.bank.features[i].pixelIndex
        &&owner.province_id===after.bank.features[i].properties.parent_id),'Final context differs from projected owner identities');
      reference=applied.reference;
      properties=new Map(projection.location_changes.map(p=>[p.location_id,p.after_properties]));
    }
    demand(same(after.reference,reference),'Final bank silently changed content reference');
    const ownerRecords=before.bank.features.map((f,i)=>{
      demand(f.id===after.bank.features[i].id&&f.pixelIndex===after.bank.features[i].pixelIndex&&f.pixelIndex===i+1,
        'Final map changed stable owner identity/order');return {id:f.id,index:f.pixelIndex};});
    const changes=finalWordChanges(before.bank.ownership,after.bank.ownership,ownerRecords);
    const positive=changes.filter(p=>p.candidate_owner!==null),ownerIndex=new Map(ownerRecords.map(p=>[p.id,p.index]));
    // Only actual new destinations require new positive source/target evidence.
    // An old hook restored during withdrawal is provenance, not an append command.
    const added=positive.length?await qualifyFinalPositiveEvidence(session,afterReader,
      {version:2,selection:beforeSelection,manifest:before.manifest},after,[],count):{components:[],patches:[],referenceSources:[]};
    const positiveRows=new Map();
    for(const p of positive){const runs=positiveRows.get(p.row)??[];runs.push([p.start,p.end,ownerIndex.get(p.candidate_owner)]);positiveRows.set(p.row,runs);}
    const expectedPositive=finalPatchRows([{rows:[...positiveRows].map(([y,runs])=>({y,runs}))}],before.manifest.size,count);
    const qualified=finalPatchRows(added.patches,before.manifest.size,count);
    demand(same(qualified,finalPatchRows(added.components.map(c=>({rows:c.native_rows})),before.manifest.size,count)),
      'New proposal includes cells outside its assigned dispositions');
    demand(same(expectedPositive,qualified),'Final map positive destinations differ from complete qualified source scope');
    for(const component of added.components)
      demand(ownerIndex.get(component.target_id)===component.pixelIndex,'Positive source target differs from the accepted owner identity');
    const lazy=new Set(before.bank.features.filter((f,i)=>f.geometry===null&&after.bank.features[i].geometry!==null).map(f=>f.id)),originals=new Map();
    if(lazy.size){
      // Proposed containing paths locate accepted N, never redefine its bytes.
      const sources=await originalSources();
      for(const name of added.referenceSources){
        const pin=sources.get(name);demand(pin,'New target source is outside the accepted original source roster');
        await acquireInputs(session,beforeReader,[pin]);
        const collection=readBody(session,beforeReader,pin);
        demand(collection.type==='FeatureCollection'&&Array.isArray(collection.features),'Incomplete original target containing source');
        for(const feature of collection.features)if(lazy.has(feature.id)){
          demand(!originals.has(feature.id),'Duplicate original target identity');originals.set(feature.id,feature.geometry);
        }
      }
      demand(originals.size===lazy.size,'New lazy target lacks its accepted original containing source');
    }
    const changedIds=[],oldContexts=[],newContexts=[];
    let latitudes;
    const checkBounds=async footprint=>{
      if(!footprint?.native_rows.length)return;
      if(!latitudes){const pin=before.manifest.native_latitudes;
        await acquireInputs(session,beforeReader,[pin]);
        latitudes=decodeVisibilityLatitudes(beforeReader.read(pin.path,{version:resolvePin(beforeReader,pin).version,expected:pin.sha256}),pin,before.manifest.size);
      }
      const box=footprint.native_bounds,size=before.manifest.size;
      for(const row of footprint.native_rows)for(const [start,end] of row.runs)
        demand(box[0]<=(start+.5)/size*360-180&&box[2]>=(end-.5)/size*360-180
          &&box[1]<=latitudes[row.y]&&box[3]>=latitudes[row.y], 'Final native bounds omit declared cells');
    };
    for(let i=0;i<count;i++){
      const feature=before.bank.features[i],current=after.bank.features[i];
      const {geometry:oldGeometry,finishedFootprint:oldFootprint,...oldRest}=feature;
      const {geometry:newGeometry,finishedFootprint:newFootprint,...newRest}=current;
      demand(same({...oldRest,properties:properties.get(feature.id)??feature.properties},newRest),
        'Final context changed unrelated owner/reference properties');
      const original=originals.get(feature.id)??oldGeometry;
      demand(newGeometry===null?!newFootprint:same(newGeometry,original), 'Final context changed original reference geometry');
      for(const component of added.components.filter(c=>c.target_id===feature.id))
        demand(component.pixelIndex===feature.pixelIndex&&same(component.base_geometry,original)
          &&component.base_geometry_sha256===valueSha(original),'New source evidence changed original target identity/geometry');
      const parts=geometry=>geometry.type==='MultiPolygon'?geometry.coordinates:[geometry.coordinates];
      const oldPolygons=oldFootprint?.geometry??(original?{type:'MultiPolygon',coordinates:parts(original)}:null);
      const newPolygons=newFootprint?.geometry??(original?{type:'MultiPolygon',coordinates:parts(original)}:null);
      demand(same(oldPolygons,newPolygons),'Final native-cell edit changed polygon coverage/order');
      const oldRows=oldFootprint?.native_rows??[],newRows=newFootprint?.native_rows??[];
      if(!same(oldRows,newRows)){await checkBounds(newFootprint);oldContexts.push(feature);newContexts.push(current);}
      else demand(same(oldFootprint,newFootprint)&&same(oldGeometry,newGeometry),
        'Final context changed without a native-cell or reference-metadata edit');
      if(!same(feature,current))changedIds.push(feature.id);
    }
    const oldRows=finalContextRows(oldContexts),newRows=finalContextRows(newContexts),contextChanges=[];
    for(const y of [...new Set([...oldRows.keys(),...newRows.keys()])].sort((a,b)=>a-b))
      contextChanges.push(...finalRowChanges(oldRows.get(y)??[],newRows.get(y)??[],y,ownerRecords));
    demand(same(changes,contextChanges),'Final words and exact finished-context changes differ; unrelated cells changed');
    const addedCells=changes.filter(p=>p.previous_owner===null).reduce((n,p)=>n+p.end-p.start,0);
    const removedCells=changes.filter(p=>p.candidate_owner===null).reduce((n,p)=>n+p.end-p.start,0);
    const reassignedCells=changes.filter(p=>p.previous_owner!==null&&p.candidate_owner!==null).reduce((n,p)=>n+p.end-p.start,0);
    const loss=removedCells+reassignedCells,rows=[...new Set(changes.map(p=>p.row))];
    return {version:1,method:'selected-native-owner-conservation-v1',status:loss?'validated-native-map-transition':'no-new-native-loss',
      baseline_selection:beforeSelection,candidate_selection:afterSelection,
      affected_rows:rows.length,lost_or_reassigned_cells:loss,intervals:changes.filter(p=>p.previous_owner!==null),
      changes,added_cells:addedCells,removed_cells:removedCells,reassigned_cells:reassignedCells,
      repair_visibility:{new_components:added.components.length,witnesses:added.components.map(c=>{
        const row=c.native_rows.at(0),run=Array.from(row.runs)[0];
        return {component_id:c.component_id,authority_sha256:c.authority_sha256,native_rows_sha256:valueSha(c.native_rows),
          x:run[0],y:row.y,previous_owner:ownerIndex.get(changes.find(p=>p.row===row.y&&p.start<=run[0]&&p.end>run[0])?.previous_owner)??0,candidate_owner:run[2]};})},
      native_row_scope:{proof:'complete-accepted-final-bank-and-qualified-new-intervals',
        compared_rows:before.manifest.size,changed_rows:rows,representation_migration:false,added_cells:addedCells},
      checkpoint_custody:{baseline_commit:beforeReader.version,accepted_bank:before.bank.indexIdentity,candidate_bank:after.bank.indexIdentity},
      changed_ids:changedIds,input_inventory:[...beforeReader.inventory.values(),...afterReader.inventory.values()],
      candidate_code_executed:false,
      ...(session.completedGeometryCustody?{completed_geometry_custody:session.completedGeometryCustody}:{}),
      limits:['Accepted main and proposed final files are the map authorities. Complete native words and finished context are compared; old repair hooks are not replayed.',
        'New positive destinations retain original source/target/method qualification. Withdrawals and scientific source fitness require substantive exact-head review; this result is not source approval.']};
  } finally {session.closed=true;closeStores(session);}
}

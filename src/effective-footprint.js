import {canonicalValue,mergeUnassignedNativeIntervals,finishedPrimitiveGeometries as finishedPrimitiveGeometriesPure,finishEffectiveFootprint as finishEffectiveFootprintPure,extendFinishedNativeFootprint as extendFinishedNativeFootprintPure,finishedReleaseFootprintDigest as finishedReleaseFootprintDigestPure,effectivePrimitiveGeometries as effectivePrimitiveGeometriesPure,effectiveFootprintValue as effectiveFootprintValuePure,versionedPrimitiveGeometries as versionedPrimitiveGeometriesPure,additiveReleaseFootprintDigest as additiveReleaseFootprintDigestPure,versionedReleaseFootprintDigest as versionedReleaseFootprintDigestPure} from './native-grid.js';
import {finalBankReference as finalBankReferencePure,additiveBaseReference as additiveBaseReferencePure,nativeReferenceForData as nativeReferenceForDataPure,bindPreparedNativeFeatures as bindPreparedNativeFeaturesPure} from './reference-metadata.js';
import {EFFECTIVE_FOOTPRINT_KIND,FINISHED_FOOTPRINT_KIND} from './native-grid.js';
export {EFFECTIVE_FOOTPRINT_KIND,FINISHED_FOOTPRINT_KIND};
import {compileNativeRuntime} from './native-runtime.js';
import {repairComponentKey,compareRepairComponents,nativeRuntimeIndex,polygonParts,nativeOnlyComponent as validateNativeOnlyComponent} from './native-grid.js';
export {polygonParts} from './native-grid.js';
import {compileNativeOwnership} from '../scripts/native-ownership/compile-native-ownership.mjs';
import {sha256} from '@noble/hashes/sha2.js';
import {originalNativeReference,validateReferenceMetadataHeader,projectReferenceOwners,assertAppliedReferenceProperties} from './reference-metadata.js';

const hex = /^[a-f0-9]{64}$/;
function require(value, message) { if (!value) throw Error(message); }
function exactKeys(value, keys, name) {
  require(value && typeof value === 'object' && !Array.isArray(value), name + ' must be an object');
  require(Object.keys(value).sort().join('\0') === [...keys].sort().join('\0'), name + ' has missing/foreign fields');
}

export function footprintValueSha256(value) {
  const raw = new TextEncoder().encode(JSON.stringify(canonicalValue(value)) + '\n');
  return Array.from(sha256(raw), byte => byte.toString(16).padStart(2, '0')).join('');
}

// The final profile carries complete current geometry and native-only coverage,
// not a list of old repairs. The reference geometry is retained solely to bind
// historical boundary replacement; a different dated geometry cannot inherit it.




// Used only for the one-time representation migration. It is deterministic
// preparation, not authority: the existing joint consumer independently proves
// exact accepted-main polygon/ring, interval, context and word conservation.


// Deterministic context preparation for ONLY newly supplied native components.
// This does not grant authority or allow overlaps: the private transition first
// proves the same proposed intervals change owner-zero in the accepted E bank.




// Polygon validity/source fitness is a producer admission, not inferred here
// from ring closure. This browser reader authenticates complete representation.


// Legacy digest bytes remain [id, geometry]. Additive releases have an explicit
// different value domain; old OGC-only readers must not ignore the new field.

export function effectiveFootprintBounds(feature) {
  const bounds = [Infinity, Infinity, -Infinity, -Infinity];
  for (const geometry of effectivePrimitiveGeometries(feature)) for (const polygon of polygonParts(geometry))
    for (const ring of polygon) for (const [x, y] of ring) {
      bounds[0] = Math.min(bounds[0], x); bounds[1] = Math.min(bounds[1], y);
      bounds[2] = Math.max(bounds[2], x); bounds[3] = Math.max(bounds[3], y);
    }
  for (const row of feature.additiveFootprint?.components ?? []) if (nativeOnlyComponent(row)) {
    bounds[0] = Math.min(bounds[0], row.native_bounds[0]); bounds[1] = Math.min(bounds[1], row.native_bounds[1]);
    bounds[2] = Math.max(bounds[2], row.native_bounds[2]); bounds[3] = Math.max(bounds[3], row.native_bounds[3]);
  }
  if (feature.finishedFootprint?.native_bounds) {
    const native = feature.finishedFootprint.native_bounds;
    for (let i = 0; i < 2; i++) {bounds[i] = Math.min(bounds[i], native[i]); bounds[i + 2] = Math.max(bounds[i + 2], native[i + 2]);}
  }
  return bounds;
}
export function assertLegacyFootprint(feature) {
  require(!Object.hasOwn(feature, 'additiveFootprint') && !Object.hasOwn(feature, 'finishedFootprint'),
    'Selected final/additive ownership requires an effective-footprint consumer');
  return feature.geometry;
}


// The historical adapter and exact native operator remain literal. Each valid
// primitive is admitted separately; their interval inputs aggregate one owner.
export function effectiveNativeRuntimeIndex(features) {
  const base=nativeRuntimeIndex(features),byOwner=new Map(features.map(feature=>[feature.pixelIndex,feature]));
  return base.map(item=>{
    const feature=byOwner.get(item.index);
    const primitives=effectivePrimitiveGeometries(feature);
    const polygons=primitives.flatMap(geometry=>nativeRuntimeIndex([{...feature,geometry}])[0].polygons);
    return {...item,polygons};
  });
}
export async function compileEffectiveNativeRuntime(features, options={}) {
  require(!features.some(feature=>feature.finishedFootprint?.native_rows?.length
    ||(feature.additiveFootprint?.components??[]).some(row=>row.representation==='native-cells')),
    'Native-only selections require the retained base plus authenticated native patch, not polygon recompilation');
  if(!features.some(feature=>Object.hasOwn(feature,'additiveFootprint')||Object.hasOwn(feature,'finishedFootprint')))return compileNativeRuntime(features,options);
  const {size,latitudes,rowBlock=4096,partWords=1048576,onBlock}=options;
  require(size===262166 && latitudes instanceof Float64Array && latitudes.length===size,
    'Canonical effective runtime requires the exact supplied latitude table');
  const raw=new Uint8Array(size*8),view=new DataView(raw.buffer);
  for(let y=0;y<size;y++)view.setFloat64(y*8,latitudes[y],true);
  require(Array.from(sha256(raw),byte=>byte.toString(16).padStart(2,'0')).join('')
    ==='66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23', 'Canonical native latitude bytes differ');
  const pieces=[],rows=new Uint32Array(size*2);
  const result=await compileNativeOwnership(effectiveNativeRuntimeIndex(features),{size,latitudes:new Float64Array(latitudes),rowBlock,partWords,onBlock,
    writePart:async(part,words)=>{if(part.kind==='rows')rows.set(words,part.offset);else pieces.push({offset:part.offset,words});return part;}});
  const runs=new Uint32Array(result.runWords);
  for(const piece of pieces)runs.set(piece.words,piece.offset);
  return {version:result.version,coordinateBits:result.coordinateBits,size,method:result.method,rows,runs};
}

// Release overlays change only previously unassigned native cells. The complete
// immutable base assets remain the inverse; no floating polygon union is used.
export const ADDITIVE_NATIVE_PATCH_KIND='unassigned-native-cells-v1';
const installedPatches=new WeakMap();
const wordDigest=words=>Array.from(sha256(new Uint8Array(words.buffer,words.byteOffset,words.byteLength)),byte=>byte.toString(16).padStart(2,'0')).join('');
// One current transport-shape contract for packaging and browser application.
export function validateAdditivePatchFormat(patch,size) {
  const versioned=patch?.version===2;
  exactKeys(patch,['version','kind','base_reference','effective_reference','ledger_sha256',versioned?'authority_registry_sha256':'rule_sha256','rows'],'Native additive patch');
  require((patch.version===1||versioned)&&patch.kind===ADDITIVE_NATIVE_PATCH_KIND,'Unsupported native additive patch');
  require(Array.isArray(patch.rows),'Missing current additive rows');let previous=-1;
  for(const row of patch.rows){
    exactKeys(row,['y','runs'],'Native patch row');
    require(Number.isSafeInteger(row.y)&&row.y>previous&&row.y>=0&&row.y<size&&Array.isArray(row.runs)&&row.runs.length>0,'Duplicate/unordered/outside native patch row');previous=row.y;let end=0;
    for(const run of row.runs){require(Array.isArray(run)&&run.length===3&&run.every(Number.isSafeInteger)&&run[0]>=end&&run[1]>run[0]&&run[1]<=size&&run[2]>0&&run[2]<2**26,'Conflicting or foreign current additive run');end=run[1];}
  }
}

// The existing interval merge arithmetic is independent of N's provenance.
// Preparation may apply a proposed new delta to an accepted final bank; only
// the ordinary conservation gate grants scientific authority to that delta.


export function applyAdditiveNativePatch(base,patch,{baseReference,effectiveReference,features}={}) {
  const versioned=patch?.version===2;
  exactKeys(patch,['version','kind','base_reference','effective_reference','ledger_sha256',versioned?'authority_registry_sha256':'rule_sha256','rows'], 'Native additive patch');
  require((patch.version===1||versioned)&&patch.kind===ADDITIVE_NATIVE_PATCH_KIND,'Unsupported native additive patch');
  const same=(a,b)=>JSON.stringify(canonicalValue(a))===JSON.stringify(canonicalValue(b));
  for(const reference of [baseReference,effectiveReference,patch.base_reference,patch.effective_reference]) {
    exactKeys(reference,['id','footprints_sha256','hierarchy_sha256'],'Additive reference');
    require(typeof reference.id==='string'&&reference.id.startsWith('geography:')&&hex.test(reference.footprints_sha256)&&hex.test(reference.hierarchy_sha256),'Incomplete additive reference');
  }
  require(same(baseReference,patch.base_reference)&&same(effectiveReference,patch.effective_reference),'Stale/foreign additive release');
  require(baseReference.hierarchy_sha256===effectiveReference.hierarchy_sha256,'Additive release cannot change hierarchy');
  require(hex.test(patch.ledger_sha256)&&hex.test(versioned?patch.authority_registry_sha256:patch.rule_sha256),'Missing additive rule/ledger binding');
  require(base?.version===2&&base.method==='native-linear-evenodd-first-owner-v1'&&base.size===262166&&base.coordinateBits===19
    &&base.rows instanceof Uint32Array&&base.rows.length===base.size*2&&base.runs instanceof Uint32Array&&base.runs.length%2===0,'Additive patch requires complete prepared native ownership');
  validateAdditivePatchFormat(patch,base.size);
  const digest=footprintValueSha256(patch);
  if(base.additive_patch_sha256===undefined)require(base.geographic_release===baseReference.id&&base.footprints_sha256===baseReference.footprints_sha256&&base.hierarchy_sha256===baseReference.hierarchy_sha256,'Native additive base differs from selected bank');
  require(Array.isArray(features)&&features.length>0,'Additive patch requires complete effective feature roster');
  const owners=new Set(),allowed=new Set();
  for(const feature of features) {
    require(Number.isInteger(feature.pixelIndex)&&feature.pixelIndex>0&&feature.pixelIndex<2**26&&!owners.has(feature.pixelIndex),'Duplicate/missing stable additive owner');
    owners.add(feature.pixelIndex);
    if(feature.geometry||Object.hasOwn(feature,'additiveFootprint'))effectivePrimitiveGeometries(feature);
    if(Object.hasOwn(feature,'additiveFootprint')) {
      const value=feature.additiveFootprint;
      require(value.baseline_release_sha256===baseReference.footprints_sha256&&value.ledger_sha256===patch.ledger_sha256
        &&(versioned?value.version===2&&value.authority_registry_sha256===patch.authority_registry_sha256:value.version===1&&value.rule_sha256===patch.rule_sha256),'Effective primitive differs from patch rule/ledger/base');
      allowed.add(feature.pixelIndex);
    }
  }
  const mapping=features.map(feature=>[feature.pixelIndex,feature.id]).sort((a,b)=>a[0]-b[0]);
  const ownerDigest=Array.from(sha256(new TextEncoder().encode(JSON.stringify(mapping))),byte=>byte.toString(16).padStart(2,'0')).join('');
  require(base.reference_owner_sha256===ownerDigest,'Native additive owner roster differs from selected base');
  require(allowed.size>0&&Array.isArray(patch.rows),'Missing additive primitives / native rows');
  if(base.additive_patch_sha256!==undefined) {
    const proof=installedPatches.get(base);
    require(proof&&proof.patch===digest&&proof.rows===wordDigest(base.rows)&&proof.runs===wordDigest(base.runs)&&base.additive_patch_sha256===digest&&base.footprints_sha256===effectiveReference.footprints_sha256,'Foreign/drifted repeated additive patch');
    return base;
  }

  const {rows,runs,addedCells}=mergeUnassignedNativeIntervals(base,patch.rows,{owners,allowed});
  const output={...base,rows,runs,runWords:runs.length,geographic_release:effectiveReference.id,footprints_sha256:effectiveReference.footprints_sha256,
    effective_footprint_sha256:effectiveReference.footprints_sha256,effective_footprint_domain:versioned?'worldatlas-effective-native-footprints:v2':'worldatlas-effective-native-footprints:v1',additive_base_reference:{...baseReference},additive_patch_sha256:digest,additive_ledger_sha256:patch.ledger_sha256,
    ...(versioned?{additive_authority_registry_sha256:patch.authority_registry_sha256}:{additive_rule_sha256:patch.rule_sha256}),additive_added_cells:addedCells};
  installedPatches.set(output,{patch:digest,rows:wordDigest(rows),runs:wordDigest(runs)});
  return output;
}

// Ledger/patch science is bound to the complete decoded JSON bytes. Transport
// compression must not rewrite that identity or the effective-footprint digest.
export function decodedAdditiveAssetIdentity(asset) {
  return asset.encoding==='gzip'?{bytes:asset.decoded_bytes,sha256:asset.decoded_sha256}:{bytes:asset.bytes,sha256:asset.sha256};
}

// Current E identifies the finished context and the complete actual word bank,
// not the historical patch sequence. Neither selector nor index hashes appear
// here, so the selector can whole-pin the index without a self-reference cycle.




// A current metadata projection does not reselect immutable ownership words,
// latitude inputs or physical coverage. Validate its transport descriptor and
// original reference before any native loader uses the selection.


export function verifyAdditiveLedgerSelection(ledger,features,patch) {
  if(ledger?.version===2)return verifyVersionedLedgerSelection(ledger,features,patch);
  require(ledger?.version===1&&ledger.kind==='native-additive-repair-ledger-v1'&&hex.test(ledger.rule_sha256),'Unsupported additive selection ledger');
  require(JSON.stringify(canonicalValue(ledger.base_reference))===JSON.stringify(canonicalValue(patch.base_reference))&&ledger.rule_sha256===patch.rule_sha256,'Selected ledger source/rule differs from patch');
  require(Number.isSafeInteger(ledger.parent_inventory?.components)&&ledger.parent_inventory.components>=ledger.rows?.filter(row=>row.representation!=='native-cells').length
    &&hex.test(ledger.parent_inventory?.report_sha256)&&hex.test(ledger.parent_inventory?.roster_sha256),'Missing complete inventory denominator');
  require(Array.isArray(ledger.scope_ids)&&Array.isArray(ledger.rows)&&ledger.scope_ids.length===ledger.rows.length
    &&new Set(ledger.scope_ids).size===ledger.scope_ids.length,'Missing/duplicate declared ledger scope');
  const wanted=new Map();let previous='';
  for(let i=0;i<ledger.rows.length;i++) {
    const row=ledger.rows[i];require(row.component_id===ledger.scope_ids[i]&&row.component_id>previous,'Foreign/unordered ledger component');previous=row.component_id;
    require(['assigned','zero-cell','already-resolved','rejected','awaiting-evidence'].includes(row.disposition),'Unknown additive ledger disposition');
    if(!['assigned','zero-cell'].includes(row.disposition))continue;
    require(typeof row.target_id==='string'&&Number.isInteger(row.pixelIndex)&&row.pixelIndex>0&&hex.test(row.base_geometry_sha256)
      &&hex.test(row.geometry_sha256)&&hex.test(row.source_receipt_sha256)&&Number.isSafeInteger(row.native_cells)&&row.native_cells>=0
      &&(row.disposition==='assigned'?row.native_cells>0:row.native_cells===0),'Incomplete native ledger contribution');
    polygonParts(row.geometry);require(footprintValueSha256(row.geometry)===row.geometry_sha256,'Ledger whole primitive changed');
    wanted.set(row.component_id,row);
  }
  const seen=new Set();
  for(const feature of features)if(Object.hasOwn(feature,'additiveFootprint')) {
    effectivePrimitiveGeometries(feature);
    for(const addition of feature.additiveFootprint.additions) {
      const row=wanted.get(addition.component_id);require(row&&!seen.has(addition.component_id)&&row.target_id===feature.id&&row.pixelIndex===feature.pixelIndex
        &&row.base_geometry_sha256===feature.additiveFootprint.base_geometry_sha256&&row.geometry_sha256===addition.geometry_sha256
        &&row.source_receipt_sha256===addition.source_receipt_sha256&&JSON.stringify(canonicalValue(row.geometry))===JSON.stringify(canonicalValue(addition.geometry)),'Foreign/duplicate/changed selected primitive');
      seen.add(addition.component_id);
    }
  }
  require(seen.size===wanted.size,'Selected effective footprint omitted a declared primitive');
  const allowed=new Set([...wanted.values()].filter(row=>row.disposition==='assigned').map(row=>row.pixelIndex));
  require(patch.rows.every(row=>row.runs.every(run=>allowed.has(run[2]))),'Native cells assigned to zero-cell/unselected ledger owner');
  const cells=patch.rows.reduce((n,row)=>n+row.runs.reduce((sum,run)=>sum+run[1]-run[0],0),0);
  require(cells===ledger.assigned_cells,'Native assigned-cell total differs from complete ledger');
  return {selected_components:wanted.size,assigned_cells:cells};
}

async function readWholeAdditiveAsset(asset,fetcher,label) {
  const response=await fetcher('./'+asset.path);require(response.ok&&response.body,label+' could not load');
  const reader=response.body.getReader(),chunks=[];let length=0;
  try{while(true){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;require(length<=asset.bytes,label+' exceeds declared whole bytes');chunks.push(value);}}
  catch(error){await reader.cancel().catch(()=>{});throw error;}finally{reader.releaseLock();}
  require(length===asset.bytes,'Incomplete '+label);const raw=new Uint8Array(length);let offset=0;
  for(const chunk of chunks){raw.set(chunk,offset);offset+=chunk.length;}
  require(Array.from(sha256(raw),byte=>byte.toString(16).padStart(2,'0')).join('')===asset.sha256,label+' whole checksum mismatch');
  let decoded=raw;
  if(asset.encoding==='gzip'){
    const stream=new Response(raw).body.pipeThrough(new DecompressionStream('gzip')),reader=stream.getReader(),parts=[];let bytes=0;
    try{while(true){const {done,value}=await reader.read();if(done)break;bytes+=value.length;require(bytes<=asset.decoded_bytes,label+' exceeds declared whole decoded bytes');parts.push(value);}}
    catch(error){await reader.cancel().catch(()=>{});throw error;}finally{reader.releaseLock();}
    require(bytes===asset.decoded_bytes,'Incomplete decoded '+label);decoded=new Uint8Array(bytes);let at=0;for(const part of parts){decoded.set(part,at);at+=part.length;}
    require(Array.from(sha256(decoded),byte=>byte.toString(16).padStart(2,'0')).join('')===asset.decoded_sha256,label+' whole decoded checksum mismatch');
  }
  return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(decoded));
}

// Fixed accepted repairs are already present in the served word bank. This
// reader installs only its whole-pinned feature context; it never fetches or
// replays a ledger/patch and has no fallback to original ownership words.


export async function loadPreparedNativeContext(data,features,ownership,{fetcher=fetch}={}) {
  const final=data.preparedOwnership?.version===3;
  if(data.additiveRelease===undefined&&!final){require(data.preparedOwnership===undefined,'Unexpected prepared ownership context');return ownership;}
  const proof=data.preparedOwnership,base=additiveBaseReference(data),effective=data.reference_release;
  require(final||proof?.version===2,'Selected ownership requires a corrected prepared bank');
  const same=(a,b)=>JSON.stringify(canonicalValue(a))===JSON.stringify(canonicalValue(b));
  require(same(proof.base_reference,base)&&same(proof.effective_reference,effective)
    &&(final||hex.test(proof.selection_sha256)&&proof.native_manifest_sha256===data.additiveRelease.base_manifest.sha256),
    'Prepared ownership selection or reference differs');
  const native=nativeReferenceForData(data);
  require(proof.native_pixel_map?.canonical_grid_sha256===proof.native_manifest_sha256
    &&same(originalNativeReference(proof.native_pixel_map),native),'Prepared original native identity differs');
  require(ownership?.geographic_release===effective.id&&ownership.footprints_sha256===effective.footprints_sha256
    &&ownership.hierarchy_sha256===effective.hierarchy_sha256&&ownership.rows instanceof Uint32Array
    &&ownership.runs instanceof Uint32Array,'Prepared final ownership differs from selected effective reference');
  require(Array.isArray(features)&&features.length===proof.owners&&Array.isArray(proof.context_parts)
    &&proof.context_parts.length>0,'Incomplete prepared effective context');
  let offset=0;const paths=new Set();
  for(const pin of proof.context_parts){
    require(/^geography\/effective-context-[a-f0-9]{64}\.json\.gz$/.test(pin.path)&&!paths.has(pin.path)
      &&pin.offset===offset&&Number.isSafeInteger(pin.features)&&pin.features>0&&pin.features<=1500
      &&pin.encoding==='gzip'&&Number.isSafeInteger(pin.bytes)&&pin.bytes>0&&pin.bytes<=8*1024*1024
      &&Number.isSafeInteger(pin.decoded_bytes)&&pin.decoded_bytes>0&&pin.decoded_bytes<=32*1024*1024
      &&hex.test(pin.sha256)&&hex.test(pin.decoded_sha256),'Invalid prepared effective context part');
    paths.add(pin.path);offset+=pin.features;
  }
  require(offset===features.length,'Incomplete prepared effective context roster');
  const parts=await Promise.all(proof.context_parts.map(pin=>readWholeAdditiveAsset(pin,fetcher,'Prepared effective context')));
  require(ownership.reference_owner_sha256===proof.reference_owner_sha256,'Prepared final owner mapping differs');
  const prepared=bindPreparedNativeFeatures(data,features,parts);
  if(final){
    for(let i=0;i<features.length;i++)features[i]=prepared[i];
    return {...ownership,effective_footprint_sha256:effective.footprints_sha256,
      effective_footprint_domain:proof.effective_footprint_domain,additive_base_reference:{...base}};
  }
  require(proof.effective_footprint_domain===`worldatlas-effective-native-footprints:v${data.additiveRelease.version}`
    &&hex.test(proof.additive_patch_sha256)
    &&proof.additive_ledger_sha256===decodedAdditiveAssetIdentity(data.additiveRelease.ledger).sha256
    &&Number.isSafeInteger(proof.additive_added_cells)&&proof.additive_added_cells>=0,'Incomplete prepared effective provenance');
  for(let i=0;i<features.length;i++)features[i]=prepared[i];
  return {...ownership,effective_footprint_sha256:effective.footprints_sha256,
    effective_footprint_domain:proof.effective_footprint_domain,additive_base_reference:{...base},
    additive_patch_sha256:proof.additive_patch_sha256,additive_ledger_sha256:proof.additive_ledger_sha256,
    additive_added_cells:proof.additive_added_cells,reference_owner_source_sha256:data.additiveRelease.owner_roster.sha256,
    ...(proof.additive_authority_registry_sha256?{additive_authority_registry_sha256:proof.additive_authority_registry_sha256}:{}),
    ...(proof.additive_rule_sha256?{additive_rule_sha256:proof.additive_rule_sha256}:{})};
}

export function loadedBaseFootprintSha256(features) {
  require(Array.isArray(features)&&features.length>0,'Missing complete loaded base features');
  const ids=new Set(),ordered=[...features].sort((a,b)=>a.id.localeCompare(b.id)),hash=sha256.create(),encoder=new TextEncoder();
  try{hash.update(encoder.encode('['));for(let i=0;i<ordered.length;i++){
    const feature=ordered[i];require(typeof feature.id==='string'&&feature.id&&!ids.has(feature.id),'Duplicate/missing loaded base identity');ids.add(feature.id);
    if(i)hash.update(encoder.encode(','));hash.update(encoder.encode(JSON.stringify([feature.id,feature.geometry])));
  }hash.update(encoder.encode(']'));return Array.from(hash.digest(),byte=>byte.toString(16).padStart(2,'0')).join('');}
  finally{hash.destroy();}
}

// Shared current-product binding. Preparation owns source qualification; both
// packaging and browser consumption verify the accepted ledger against actual
// current target identities, geometry and the selected base reference.
export function bindAdditiveLedgerFeatures(features,ledger,release,baseReference) {
  const hasAdditions=features.some(feature=>Object.hasOwn(feature,'additiveFootprint'));
  features=[...features];
  if(!hasAdditions&&ledger.version===2){
    const targets=versionedCurrentTargets(ledger),groups=new Map();
    for(const row of ledger.rows??[])if(['assigned','zero-cell'].includes(row.disposition)){
      if(!groups.has(row.target_id))groups.set(row.target_id,[]);groups.get(row.target_id).push(row);
    }
    require(groups.size===targets.size&&groups.size>0,'Incomplete current target/primitive scope');
    for(const [id,components]of groups){
      const index=features.findIndex(feature=>feature.id===id),target=targets.get(id);
      require(index>=0&&target&&features[index].pixelIndex===target.pixelIndex,'Foreign current additive target');
      const geometry=features[index].geometry??target.geometry;
      require(footprintValueSha256(geometry)===target.geometry_sha256,'Current target differs from authenticated rebind');
      features[index]={...features[index],geometry,additiveFootprint:{version:2,kind:EFFECTIVE_FOOTPRINT_KIND,
        baseline_release_sha256:baseReference.footprints_sha256,base_geometry_sha256:target.geometry_sha256,
        ledger_sha256:decodedAdditiveAssetIdentity(release.ledger).sha256,authority_registry_sha256:ledger.authority_registry_sha256,components}};
    }
  }else if(!hasAdditions){
    const groups=new Map();
    for(const row of ledger.rows??[])if(['assigned','zero-cell'].includes(row.disposition)){
      if(!groups.has(row.target_id))groups.set(row.target_id,[]);groups.get(row.target_id).push(row);
    }
    require(groups.size>0,'Selected additive ledger has no effective primitives');
    for(const [id,rows]of groups){
      const index=features.findIndex(feature=>feature.id===id);require(index>=0,'Selected primitive target absent from complete base');
      const original=features[index],geometry=original.geometry??rows[0].base_geometry;
      polygonParts(geometry);
      const feature={...original,geometry};
      require(rows.every(row=>row.pixelIndex===feature.pixelIndex&&row.base_geometry_sha256===footprintValueSha256(feature.geometry)
        &&(row.base_geometry===undefined||footprintValueSha256(row.base_geometry)===row.base_geometry_sha256)),'Selected primitive has foreign base owner/geometry');
      features[index]={...feature,additiveFootprint:{version:1,kind:EFFECTIVE_FOOTPRINT_KIND,baseline_release_sha256:baseReference.footprints_sha256,
        base_geometry_sha256:footprintValueSha256(feature.geometry),ledger_sha256:decodedAdditiveAssetIdentity(release.ledger).sha256,rule_sha256:ledger.rule_sha256,
        additions:rows.map(row=>({component_id:row.component_id,geometry:row.geometry,geometry_sha256:row.geometry_sha256,source_receipt_sha256:row.source_receipt_sha256}))}};
    }
  }
  return features;
}

export async function loadAdditiveNativePatch(data,features,base,{fetcher=fetch,effectiveDigest}={}) {
  const hasAdditions=features.some(feature=>Object.hasOwn(feature,'additiveFootprint'));
  const nativeReference=nativeReferenceForData(data);
  if(data.additiveRelease===undefined){
    require(!hasAdditions,'Effective footprint requires an explicit selected additive release');
    return base;
  }
  const originalFeatures=features;features=[...features];
  const baseReference=additiveBaseReference(data),release=data.additiveRelease;
  require(effectiveDigest===undefined||effectiveDigest===data.reference_release.footprints_sha256,'Selected effective footprint digest mismatch');
  if(features.every(feature=>feature.geometry))require(loadedBaseFootprintSha256(features)===baseReference.footprints_sha256,'Complete loaded original base footprint differs from selected additive bank');
  require(hex.test(data.pixelMap?.canonical_grid_sha256)&&release.base_manifest.sha256===data.pixelMap.canonical_grid_sha256,'Additive original native manifest is not independently selected');
  const originalManifest=await readWholeAdditiveAsset(release.base_manifest,fetcher,'Original native manifest');
  require(originalManifest.geographic_release===nativeReference.id&&originalManifest.footprints_sha256===nativeReference.footprints_sha256
    &&originalManifest.hierarchy_sha256===nativeReference.hierarchy_sha256&&originalManifest.method===base.method
    &&originalManifest.size===base.size&&originalManifest.coordinateBits===base.coordinateBits
    &&originalManifest.original_assets?.bounds?.sha256===release.owner_roster.sha256,'Selected owner roster differs from original native manifest');
  require(base.geographic_release===nativeReference.id&&base.footprints_sha256===nativeReference.footprints_sha256
    &&base.hierarchy_sha256===nativeReference.hierarchy_sha256,'Decoded native ownership differs from original selected reference');
  require(Array.isArray(originalManifest.parts)&&originalManifest.parts.length>0,'Missing original native asset closure');
  for(const kind of ['rows','runs']){
    const words=base[kind];require(words instanceof Uint32Array,'Missing actual decoded native asset');let offset=0;
    for(const part of originalManifest.parts.filter(part=>part.kind===kind).sort((a,b)=>a.offset-b.offset)){
      require(part.offset===offset&&Number.isSafeInteger(part.words)&&part.words>0
        &&part.words<=words.length-offset&&hex.test(part.decoded_sha256),'Incomplete original native asset closure');
      const raw=new Uint8Array(words.buffer,words.byteOffset+offset*4,part.words*4);
      require(Array.from(sha256(raw),byte=>byte.toString(16).padStart(2,'0')).join('')===part.decoded_sha256,'Decoded native ownership differs from original selected manifest');offset+=part.words;
    }
    require(offset===words.length,'Original manifest omitted decoded native ownership');
  }
  require(originalManifest.parts.every(part=>['rows','runs'].includes(part.kind)),'Foreign original native asset');
  const ledger=await readWholeAdditiveAsset(release.ledger,fetcher,'Native ledger'),patch=await readWholeAdditiveAsset(release.patch,fetcher,'Native patch');
  require(patch.ledger_sha256===decodedAdditiveAssetIdentity(release.ledger).sha256,'Native patch differs from selected whole ledger');
  features=bindAdditiveLedgerFeatures(features,ledger,release,baseReference);
  const actualEffectiveDigest=additiveReleaseFootprintDigest(baseReference,features);
  require(actualEffectiveDigest===data.reference_release.footprints_sha256,'Explicit additive footprint domain differs from selected release');
  verifyAdditiveLedgerSelection(ledger,features,patch);
  // The immutable native manifest predates the explicit leaf-owner binding.
  // Authenticate the WHOLE selected original bounds roster, never a target-only
  // assertion or an inferred nearest owner, before adding metadata to its view.
  const roster=await readWholeAdditiveAsset(release.owner_roster,fetcher,'Native owner roster');
  require(Array.isArray(roster)&&roster.length===features.length,'Incomplete selected native owner roster');
  let currentRoster=roster;
  if(data.referenceMetadata!==undefined){
    const metadata=data.referenceMetadata,projection=await readWholeAdditiveAsset(metadata.asset,fetcher,'Reference metadata projection');
    const references=validateReferenceMetadataHeader(projection,{selection:projection.native_selection,manifest:originalManifest});
    const same=(a,b)=>JSON.stringify(canonicalValue(a))===JSON.stringify(canonicalValue(b));
    require(projection.native_selection.sha256===data.pixelMap.canonical_grid_sha256
      &&same(references.native,nativeReference)&&same(references.reference,baseReference),
    'Reference metadata projection differs from the selected native manifest or current reference');
    currentRoster=projectReferenceOwners(roster,projection.location_changes,projection.provinces);
    const byId=new Map(features.map(feature=>[feature.id,feature]));
    for(const change of projection.location_changes)assertAppliedReferenceProperties(byId.get(change.location_id)?.properties,change.after_properties,{referenceRevision:metadata.application_reference_revision});

  }
  const byId=new Map(features.map(feature=>[feature.id,feature])),positions=new Map(features.map((feature,index)=>[feature.id,index])),indices=new Set(),ids=new Set();
  for(const row of currentRoster){
    const feature=byId.get(row.id);
    require(feature&&!ids.has(row.id)&&Number.isInteger(row.index)&&row.index>0&&!indices.has(row.index)
      &&feature.pixelIndex===row.index&&feature.properties?.parent_id===row.province_id,'Foreign/duplicate/changed selected native owner or parent');
    require(Array.isArray(row.bounds)&&row.bounds.length===4&&row.bounds.every(Number.isFinite),'Missing whole original native viewport bounds');
    const index=positions.get(row.id);features[index]={...feature,gridBounds:[...row.bounds]};
    ids.add(row.id);indices.add(row.index);
  }
  const mapping=roster.map(row=>[row.index,row.id]).sort((a,b)=>a[0]-b[0]);
  const ownerDigest=Array.from(sha256(new TextEncoder().encode(JSON.stringify(mapping))),byte=>byte.toString(16).padStart(2,'0')).join('');
  require(base.reference_owner_sha256===undefined||base.reference_owner_sha256===ownerDigest,'Existing native owner binding differs from selected whole roster');
  // Bind only a fresh metadata view after authenticating N and every M parent.
  // The additive application still requires the same M/E hierarchy.
  const boundBase={...base,geographic_release:baseReference.id,hierarchy_sha256:baseReference.hierarchy_sha256,
    reference_owner_sha256:ownerDigest,reference_owner_source_sha256:release.owner_roster.sha256};
  const installed=applyAdditiveNativePatch(boundBase,patch,{baseReference,effectiveReference:data.reference_release,features});
  for(let i=0;i<features.length;i++)originalFeatures[i]=features[i];
  return installed;
}

// Explicit release domain: producer authenticates immutable whole base custody;
// geometry consumers separately rehash ALL loaded base identities/geometries. This
// digest does not assert that the producer reread the entire world geometry.


// Native additions retain exact intervals, never synthetic polygons. These
// intervals also survive historical context remapping and supply camera bounds.
export function nativeOnlyComponent(row) { return validateNativeOnlyComponent(row,footprintValueSha256); }
export function effectiveNativeAdditionRows(feature) {
  if (Object.hasOwn(feature ?? {}, 'finishedFootprint')) {finishedPrimitiveGeometries(feature); return feature.finishedFootprint.native_rows;}
  if (!feature?.additiveFootprint) return [];
  effectivePrimitiveGeometries(feature);
  return (feature.additiveFootprint.components ?? []).filter(nativeOnlyComponent).flatMap(row => row.native_rows);
}

// V2 keeps each complete original component and its issued policy authority.
// The current base is a separate binding, authenticated by current-bank rebind;
// original component base geometry is never relabelled as that current base.




function versionedCurrentTargets(ledger) {
  const targets=new Map();
  if(ledger.current_rebind===undefined){
    require(ledger.current_targets===undefined,'Current targets require actual rebind custody');
    for(const row of ledger.rows??[])if(['assigned','zero-cell'].includes(row.disposition)){
      const target={target_id:row.target_id,pixelIndex:row.pixelIndex,geometry:row.base_geometry,geometry_sha256:row.base_geometry_sha256};
      const old=targets.get(row.target_id);require(old===undefined||footprintValueSha256(old)===footprintValueSha256(target),'Original component bases disagree');targets.set(row.target_id,target);
    }
    return targets;
  }
  const pin=ledger.current_rebind;
  exactKeys(pin,['commit','path','mode','git_blob_oid','bytes','sha256'],'Current rebind ordinary pin');
  require(/^[a-f0-9]{40}$/.test(pin.commit)&&/^[a-f0-9]{40}$/.test(pin.git_blob_oid)&&pin.mode==='100644'
    &&typeof pin.path==='string'&&!pin.path.includes('\\')&&pin.path.split('/').every(p=>p&&p!=='.'&&p!=='..')
    &&Number.isSafeInteger(pin.bytes)&&pin.bytes>0&&hex.test(pin.sha256),'Incomplete current rebind custody');
  // This pin is independently authenticated by the selected authority reader.
  // Browser consumption relies on the selected whole ledger, never infers a
  // source approval or qualification from the shape of this pin.
  require(Array.isArray(ledger.current_targets)&&ledger.current_targets.length>0,'Missing complete current rebind targets');let previous='';
  for(const row of ledger.current_targets){
    exactKeys(row,['target_id','pixelIndex','geometry','geometry_sha256'],'Current target binding');
    require(typeof row.target_id==='string'&&row.target_id>previous&&Number.isSafeInteger(row.pixelIndex)&&row.pixelIndex>0,'Foreign/duplicate/unordered current target');previous=row.target_id;
    polygonParts(row.geometry);require(hex.test(row.geometry_sha256)&&footprintValueSha256(row.geometry)===row.geometry_sha256,'Current target pointset changed');targets.set(row.target_id,row);
  }
  for (const row of ledger.rows ?? []) if (nativeOnlyComponent(row)) {
    const target = {target_id:row.target_id,pixelIndex:row.pixelIndex,geometry:row.base_geometry,geometry_sha256:row.base_geometry_sha256};
    const old = targets.get(row.target_id);
    require(!old || footprintValueSha256(old) === footprintValueSha256(target), 'Native target base conflicts with prior target');
    targets.set(row.target_id, target);
  }
  return targets;
}

function verifyVersionedLedgerSelection(ledger,features,patch) {
  require(ledger.kind==='native-additive-repair-ledger-v2'&&hex.test(ledger.authority_registry_sha256)&&patch.version===2
    &&ledger.authority_registry_sha256===patch.authority_registry_sha256,'Foreign versioned ledger/patch authority registry');
  // The normative V2 ledger stores component authorities and optional current
  // rebind custody. Its selected base and delta count live in the separately
  // authenticated envelope/patch; retain strict checks for explicit summaries.
  if(Object.hasOwn(ledger,'base_reference'))require(footprintValueSha256(ledger.base_reference)===footprintValueSha256(patch.base_reference),'Versioned ledger current bank differs from patch');
  require(Number.isSafeInteger(ledger.parent_inventory?.components)&&ledger.parent_inventory.components>=ledger.rows?.filter(row=>row.representation!=='native-cells').length
    &&hex.test(ledger.parent_inventory?.report_sha256)&&hex.test(ledger.parent_inventory?.roster_sha256),'Missing original complete inventory denominator');
  require(Array.isArray(ledger.scope_ids)&&Array.isArray(ledger.rows)&&ledger.scope_ids.length===ledger.rows.length,'Missing complete original versioned scope');
  const targets=versionedCurrentTargets(ledger),wanted=new Map();let previous;
  for(let i=0;i<ledger.rows.length;i++){
    const row=ledger.rows[i];require(typeof row.component_id==='string'&&row.component_id&&row.component_id===ledger.scope_ids[i]&&(!previous||compareRepairComponents(previous,row)<0),'Foreign/duplicate/unordered original component');previous=row;
    require(['assigned','zero-cell','already-resolved','rejected','awaiting-evidence'].includes(row.disposition),'Unknown original component disposition');
    if(['assigned','zero-cell'].includes(row.disposition))wanted.set(repairComponentKey(row),row);
  }
  const seen=new Set(),targetIds=new Set();
  for(const feature of features)if(Object.hasOwn(feature,'additiveFootprint')){
    require(feature.additiveFootprint.version===2,'Mixed versioned selected footprint');versionedPrimitiveGeometries(feature);
    const value=feature.additiveFootprint,target=targets.get(feature.id);
    require(target&&target.pixelIndex===feature.pixelIndex&&target.geometry_sha256===value.base_geometry_sha256
      &&value.authority_registry_sha256===ledger.authority_registry_sha256&&value.ledger_sha256===patch.ledger_sha256
      &&value.baseline_release_sha256===patch.base_reference.footprints_sha256,'Foreign current target/registry/ledger/base binding');targetIds.add(feature.id);
    for(const component of value.components){const original=wanted.get(repairComponentKey(component));
      require(original&&!seen.has(repairComponentKey(component))&&footprintValueSha256(original)===footprintValueSha256(component),'Original component authority removed/rebound');seen.add(repairComponentKey(component));}
  }
  require(seen.size===wanted.size&&targetIds.size===targets.size,'Incomplete selected original components/current target scope');
  const patchRows=new Map(patch.rows.map(row=>[row.y,row.runs]));
  for (const component of wanted.values()) if (nativeOnlyComponent(component))
    for (const row of component.native_rows) for (const run of row.runs)
      require((patchRows.get(row.y)??[]).some(actual=>actual[2]===run[2]&&actual[0]<=run[0]&&actual[1]>=run[1]),
        'Selected native component intervals omitted or reassigned by patch');
  const allowed=new Set([...wanted.values()].filter(row=>row.disposition==='assigned').map(row=>row.pixelIndex));
  require(Array.isArray(patch.rows)&&patch.rows.every(row=>row.runs.every(run=>allowed.has(run[2]))),'Native cells assigned to zero-cell/unselected owner');
  const cells=patch.rows.reduce((n,row)=>n+row.runs.reduce((sum,run)=>sum+run[1]-run[0],0),0);
  require(Number.isSafeInteger(cells)&&cells>=0,'Invalid complete current native cell total');
  if(Object.hasOwn(ledger,'assigned_cells'))require(Number.isSafeInteger(ledger.assigned_cells)&&cells===ledger.assigned_cells,'Complete current native cell total differs');
  return {selected_components:wanted.size,assigned_cells:cells};
}

// Shared source-target route. Geometry is evidence for native membership, not an
// invented continuous addition. The caller authenticates complete source-family
// products, the reviewed coverage/exclusion masks and the current owner rows.
// Physical water is deliberately not a territorial exclusion: callers pass only
// independently supported territorial exclusions (for example retained holes).

export {canonicalValue,mergeUnassignedNativeIntervals};
export function finishedPrimitiveGeometries(...args){return finishedPrimitiveGeometriesPure(...args,footprintValueSha256);}
export function finishEffectiveFootprint(...args){return finishEffectiveFootprintPure(...args,footprintValueSha256);}
export function extendFinishedNativeFootprint(...args){return extendFinishedNativeFootprintPure(...args,footprintValueSha256);}
export function finishedReleaseFootprintDigest(...args){return finishedReleaseFootprintDigestPure(...args,footprintValueSha256);}
export function effectivePrimitiveGeometries(...args){return effectivePrimitiveGeometriesPure(...args,footprintValueSha256);}
export function effectiveFootprintValue(...args){return effectiveFootprintValuePure(...args,footprintValueSha256);}
export function versionedPrimitiveGeometries(...args){return versionedPrimitiveGeometriesPure(...args,footprintValueSha256);}
export function additiveReleaseFootprintDigest(...args){return additiveReleaseFootprintDigestPure(...args,footprintValueSha256);}
export function versionedReleaseFootprintDigest(...args){return versionedReleaseFootprintDigestPure(...args,footprintValueSha256);}
export function finalBankReference(...args){return finalBankReferencePure(...args,footprintValueSha256);}
export function additiveBaseReference(...args){return additiveBaseReferencePure(...args,footprintValueSha256);}
export function nativeReferenceForData(...args){return nativeReferenceForDataPure(...args,footprintValueSha256);}
export function bindPreparedNativeFeatures(...args){return bindPreparedNativeFeaturesPure(...args,footprintValueSha256,bytes=>Array.from(sha256(bytes),b=>b.toString(16).padStart(2,'0')).join(''));}

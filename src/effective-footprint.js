import {nativeRuntimeIndex, compileNativeRuntime} from './native-runtime.js';
import {compileNativeOwnership} from '../scripts/native-ownership/compile-native-ownership.mjs';
import {sha256} from '@noble/hashes/sha2.js';

export const EFFECTIVE_FOOTPRINT_KIND = 'retained-base-plus-additions';
const hex = /^[a-f0-9]{64}$/;
function require(value, message) { if (!value) throw Error(message); }
function exactKeys(value, keys, name) {
  require(value && typeof value === 'object' && !Array.isArray(value), name + ' must be an object');
  require(Object.keys(value).sort().join('\0') === [...keys].sort().join('\0'), name + ' has missing/foreign fields');
}
export function canonicalValue(value) {
  if (Array.isArray(value)) return value.map(canonicalValue);
  if (value && typeof value === 'object') {
    const out = Object.create(null);
    for (const key of Object.keys(value).sort()) out[key] = canonicalValue(value[key]);
    return out;
  }
  require(value !== undefined && (typeof value !== 'number' || Number.isFinite(value)), 'Nonfinite or missing footprint value');
  return value;
}
export function footprintValueSha256(value) {
  const raw = new TextEncoder().encode(JSON.stringify(canonicalValue(value)) + '\n');
  return Array.from(sha256(raw), byte => byte.toString(16).padStart(2, '0')).join('');
}

// Polygon validity/source fitness is a producer admission, not inferred here
// from ring closure. This browser reader authenticates complete representation.
export function polygonParts(geometry) {
  require(geometry && ['Polygon', 'MultiPolygon'].includes(geometry.type), 'Unsupported original native geometry / footprint primitive');
  exactKeys(geometry, ['type', 'coordinates'], 'Primitive geometry');
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  require(Array.isArray(polygons) && polygons.length > 0, 'Missing footprint polygons');
  for (const polygon of polygons) {
    require(Array.isArray(polygon) && polygon.length > 0, 'Missing footprint rings');
    for (const ring of polygon) {
      require(Array.isArray(ring) && ring.length >= 4, 'Incomplete footprint ring');
      for (const point of ring) require(Array.isArray(point) && point.length === 2 && point.every(Number.isFinite)
        && Math.abs(point[0]) <= 180 && Math.abs(point[1]) <= 90, 'Invalid native footprint coordinate');
      require(ring[0][0] === ring.at(-1)[0] && ring[0][1] === ring.at(-1)[1], 'Unclosed footprint ring');
    }
  }
  return polygons;
}
export function effectivePrimitiveGeometries(feature) {
  if (feature?.additiveFootprint?.version === 2) return versionedPrimitiveGeometries(feature);
  require(feature && typeof feature.id === 'string' && feature.id, 'Missing effective footprint identity');
  polygonParts(feature.geometry);
  if (!Object.hasOwn(feature, 'additiveFootprint')) return [feature.geometry];
  const value = feature.additiveFootprint;
  exactKeys(value, ['version', 'kind', 'baseline_release_sha256', 'base_geometry_sha256', 'ledger_sha256', 'rule_sha256', 'additions'], 'Additive footprint');
  require(value.version === 1 && value.kind === EFFECTIVE_FOOTPRINT_KIND, 'Unsupported effective footprint version');
  for (const key of ['baseline_release_sha256', 'base_geometry_sha256', 'ledger_sha256', 'rule_sha256'])
    require(hex.test(value[key] ?? ''), 'Missing complete effective footprint binding: ' + key);
  require(value.base_geometry_sha256 === footprintValueSha256(feature.geometry), 'Retained base geometry changed');
  require(Array.isArray(value.additions) && value.additions.length > 0, 'Empty additive footprint');
  const ids = new Set(), output = [feature.geometry];
  let previous = '';
  for (const addition of value.additions) {
    exactKeys(addition, ['component_id', 'geometry', 'geometry_sha256', 'source_receipt_sha256'], 'Footprint addition');
    require(typeof addition.component_id === 'string' && addition.component_id && !ids.has(addition.component_id)
      && addition.component_id > previous, 'Duplicate/unordered addition identity');
    ids.add(addition.component_id); previous = addition.component_id;
    require(hex.test(addition.geometry_sha256 ?? '') && hex.test(addition.source_receipt_sha256 ?? ''), 'Missing whole addition/source binding');
    polygonParts(addition.geometry);
    require(footprintValueSha256(addition.geometry) === addition.geometry_sha256, 'Complete addition pointset changed');
    output.push(addition.geometry);
  }
  return output;
}

// Legacy digest bytes remain [id, geometry]. Additive releases have an explicit
// different value domain; old OGC-only readers must not ignore the new field.
export function effectiveFootprintValue(feature) {
  if (feature?.additiveFootprint?.version === 2) {
    versionedPrimitiveGeometries(feature);
    return {version: 2, kind: EFFECTIVE_FOOTPRINT_KIND, base: feature.geometry, additive: feature.additiveFootprint};
  }
  effectivePrimitiveGeometries(feature);
  return Object.hasOwn(feature, 'additiveFootprint')
    ? {version: 1, kind: EFFECTIVE_FOOTPRINT_KIND, base: feature.geometry, additive: feature.additiveFootprint}
    : feature.geometry;
}
export function effectiveFootprintBounds(feature) {
  const bounds = [Infinity, Infinity, -Infinity, -Infinity];
  for (const geometry of effectivePrimitiveGeometries(feature)) for (const polygon of polygonParts(geometry))
    for (const ring of polygon) for (const [x, y] of ring) {
      bounds[0] = Math.min(bounds[0], x); bounds[1] = Math.min(bounds[1], y);
      bounds[2] = Math.max(bounds[2], x); bounds[3] = Math.max(bounds[3], y);
    }
  return bounds;
}
export function assertLegacyFootprint(feature) {
  require(!Object.hasOwn(feature, 'additiveFootprint'), 'Additive release requires an effective-footprint consumer');
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
  if(!features.some(feature=>Object.hasOwn(feature,'additiveFootprint')))return compileNativeRuntime(features,options);
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

  const replacements=new Map();let previousY=-1,addedCells=0;
  const bits=19,mask=2**bits-1,ownerBase=2**(32-bits);
  const decode=k=>{const a=base.runs[k*2],b=base.runs[k*2+1];return[a&mask,(b&mask)+1,(a>>>bits)+(b>>>bits)*ownerBase];};
  for(const row of patch.rows) {
    exactKeys(row,['y','runs'],'Native patch row');
    require(Number.isInteger(row.y)&&row.y>previousY&&row.y<base.size&&Array.isArray(row.runs)&&row.runs.length>0,'Duplicate/unordered/outside native patch row');previousY=row.y;
    const start=base.rows[row.y*2],count=base.rows[row.y*2+1];
    require(start+count<=base.runs.length/2,'Incomplete base native row');
    const old=Array.from({length:count},(_,i)=>decode(start+i));let previousEnd=0;
    for(const run of old){require(run[0]>=previousEnd&&run[1]>run[0]&&run[1]<=base.size&&owners.has(run[2]),'Invalid/foreign base ownership run');previousEnd=run[1];}
    previousEnd=0;
    for(const run of row.runs) {
      require(Array.isArray(run)&&run.length===3&&run.every(Number.isInteger)&&run[0]>=previousEnd&&run[1]>run[0]&&run[1]<=base.size&&allowed.has(run[2]),'Conflicting/unordered/foreign native addition');previousEnd=run[1];
      require(!old.some(before=>before[0]<run[1]&&run[0]<before[1]),'Native additive patch would replace an assigned cell');
      addedCells+=run[1]-run[0];
    }
    const combined=[...old,...row.runs].sort((a,b)=>a[0]-b[0]),merged=[];
    for(const run of combined){const last=merged.at(-1);if(last&&last[1]===run[0]&&last[2]===run[2])last[1]=run[1];else merged.push([...run]);}
    replacements.set(row.y,merged);
  }
  const count=base.runs.length/2+[...replacements].reduce((n,[y,runs])=>n+runs.length-base.rows[y*2+1],0);
  require(Number.isSafeInteger(count)&&count>=0,'Invalid native additive output count');
  const rows=new Uint32Array(base.rows.length),runs=new Uint32Array(count*2);let cursor=0;
  for(let y=0;y<base.size;y++) {
    const offset=base.rows[y*2],length=base.rows[y*2+1];
    require(offset===(y?base.rows[(y-1)*2]+base.rows[(y-1)*2+1]:0)&&offset+length<=base.runs.length/2,'Incomplete/unreferenced base ownership');
    rows[y*2]=cursor;
    if(replacements.has(y)) {
      const replacement=replacements.get(y);rows[y*2+1]=replacement.length;
      for(const [start,end,owner] of replacement){runs[cursor*2]=owner%ownerBase*2**bits+start;runs[cursor*2+1]=Math.floor(owner/ownerBase)*2**bits+end-1;cursor++;}
    }else{rows[y*2+1]=length;runs.set(base.runs.subarray(offset*2,(offset+length)*2),cursor*2);cursor+=length;}
  }
  require(base.rows.at(-2)+base.rows.at(-1)===base.runs.length/2&&cursor===count,'Unreferenced native base/output runs');
  const output={...base,rows,runs,runWords:runs.length,geographic_release:effectiveReference.id,footprints_sha256:effectiveReference.footprints_sha256,
    effective_footprint_sha256:effectiveReference.footprints_sha256,effective_footprint_domain:versioned?'worldatlas-effective-native-footprints:v2':'worldatlas-effective-native-footprints:v1',additive_base_reference:{...baseReference},additive_patch_sha256:digest,additive_ledger_sha256:patch.ledger_sha256,
    ...(versioned?{additive_authority_registry_sha256:patch.authority_registry_sha256}:{additive_rule_sha256:patch.rule_sha256}),additive_added_cells:addedCells};
  installedPatches.set(output,{patch:digest,rows:wordDigest(rows),runs:wordDigest(runs)});
  return output;
}

export function additiveBaseReference(data) {
  if(data.additiveRelease===undefined)return data.reference_release;
  const release=data.additiveRelease;
  exactKeys(release,['version','kind','base_reference','effective_reference','patch','ledger','owner_roster','base_manifest'],'Additive release');
  require((release.version===1&&release.kind==='retained-native-base-plus-delta-v1')
    ||(release.version===2&&release.kind==='retained-native-base-plus-delta-v2'),'Unsupported additive release');
  require(JSON.stringify(canonicalValue(release.effective_reference))===JSON.stringify(canonicalValue(data.reference_release)),'Selected additive reference mismatch');
  for(const asset of [release.patch,release.ledger,release.owner_roster,release.base_manifest]){
    exactKeys(asset,asset===release.owner_roster?['path','bytes','sha256','encoding','decoded_bytes','decoded_sha256']:['path','bytes','sha256'],'Native additive asset');
    require(/^additive-repairs\/[a-zA-Z0-9_-]+\.json(?:\.gz)?$/.test(asset.path)&&Number.isSafeInteger(asset.bytes)
      &&asset.bytes>0&&asset.bytes<=32*1024*1024&&hex.test(asset.sha256),'Unsafe/oversized native additive asset');
  }
  require(release.owner_roster.encoding==='gzip'&&Number.isSafeInteger(release.owner_roster.decoded_bytes)&&release.owner_roster.decoded_bytes>0&&release.owner_roster.decoded_bytes<=32*1024*1024&&hex.test(release.owner_roster.decoded_sha256),'Incomplete whole decoded native owner roster');
  require(new Set([release.patch.path,release.ledger.path,release.owner_roster.path,release.base_manifest.path]).size===4,'Duplicate native additive assets');
  return release.base_reference;
}

export function verifyAdditiveLedgerSelection(ledger,features,patch) {
  if(ledger?.version===2)return verifyVersionedLedgerSelection(ledger,features,patch);
  require(ledger?.version===1&&ledger.kind==='native-additive-repair-ledger-v1'&&hex.test(ledger.rule_sha256),'Unsupported additive selection ledger');
  require(JSON.stringify(canonicalValue(ledger.base_reference))===JSON.stringify(canonicalValue(patch.base_reference))&&ledger.rule_sha256===patch.rule_sha256,'Selected ledger source/rule differs from patch');
  require(Number.isSafeInteger(ledger.parent_inventory?.components)&&ledger.parent_inventory.components>=ledger.rows?.length
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

export function loadedBaseFootprintSha256(features) {
  require(Array.isArray(features)&&features.length>0,'Missing complete loaded base features');
  const ids=new Set(),ordered=[...features].sort((a,b)=>a.id.localeCompare(b.id)),hash=sha256.create(),encoder=new TextEncoder();
  try{hash.update(encoder.encode('['));for(let i=0;i<ordered.length;i++){
    const feature=ordered[i];require(typeof feature.id==='string'&&feature.id&&!ids.has(feature.id),'Duplicate/missing loaded base identity');ids.add(feature.id);
    if(i)hash.update(encoder.encode(','));hash.update(encoder.encode(JSON.stringify([feature.id,feature.geometry])));
  }hash.update(encoder.encode(']'));return Array.from(hash.digest(),byte=>byte.toString(16).padStart(2,'0')).join('');}
  finally{hash.destroy();}
}

export async function loadAdditiveNativePatch(data,features,base,{fetcher=fetch,effectiveDigest}={}) {
  const hasAdditions=features.some(feature=>Object.hasOwn(feature,'additiveFootprint'));
  if(data.additiveRelease===undefined){require(!hasAdditions,'Effective footprint requires an explicit selected additive release');return base;}
  const originalFeatures=features;features=[...features];
  const baseReference=additiveBaseReference(data),release=data.additiveRelease;
  require(effectiveDigest===undefined||effectiveDigest===data.reference_release.footprints_sha256,'Selected effective footprint digest mismatch');
  if(features.every(feature=>feature.geometry))require(loadedBaseFootprintSha256(features)===baseReference.footprints_sha256,'Complete loaded original base footprint differs from selected additive bank');
  require(hex.test(data.pixelMap?.canonical_grid_sha256)&&release.base_manifest.sha256===data.pixelMap.canonical_grid_sha256,'Additive original native manifest is not independently selected');
  const originalManifest=await readWholeAdditiveAsset(release.base_manifest,fetcher,'Original native manifest');
  require(originalManifest.geographic_release===baseReference.id&&originalManifest.footprints_sha256===baseReference.footprints_sha256
    &&originalManifest.hierarchy_sha256===baseReference.hierarchy_sha256&&originalManifest.method===base.method
    &&originalManifest.size===base.size&&originalManifest.coordinateBits===base.coordinateBits
    &&originalManifest.original_assets?.bounds?.sha256===release.owner_roster.sha256,'Selected owner roster differs from original native manifest');
  require(Array.isArray(originalManifest.parts)&&originalManifest.parts.length>0,'Missing original native asset closure');
  for(const kind of ['rows','runs']){
    const words=base[kind];require(words instanceof Uint32Array,'Missing actual decoded native asset');let offset=0;
    for(const part of originalManifest.parts.filter(part=>part.kind===kind).sort((a,b)=>a.offset-b.offset)){
      require(part.offset===offset&&Number.isSafeInteger(part.words)&&part.words>0&&part.words*4<=32*1024*1024
        &&offset+part.words<=words.length&&hex.test(part.decoded_sha256),'Incomplete original native asset closure');
      const raw=new Uint8Array(words.buffer,words.byteOffset+offset*4,part.words*4);
      require(Array.from(sha256(raw),byte=>byte.toString(16).padStart(2,'0')).join('')===part.decoded_sha256,'Decoded native ownership differs from original selected manifest');offset+=part.words;
    }
    require(offset===words.length,'Original manifest omitted decoded native ownership');
  }
  require(originalManifest.parts.every(part=>['rows','runs'].includes(part.kind)),'Foreign original native asset');
  const ledger=await readWholeAdditiveAsset(release.ledger,fetcher,'Native ledger'),patch=await readWholeAdditiveAsset(release.patch,fetcher,'Native patch');
  require(patch.ledger_sha256===release.ledger.sha256,'Native patch differs from selected whole ledger');
  // Existing whole base catalog parts stay literal. The explicit selected
  // ledger supplies every new primitive to a cloned effective feature view.
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
        ledger_sha256:release.ledger.sha256,authority_registry_sha256:ledger.authority_registry_sha256,components}};
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
        base_geometry_sha256:footprintValueSha256(feature.geometry),ledger_sha256:release.ledger.sha256,rule_sha256:ledger.rule_sha256,
        additions:rows.map(row=>({component_id:row.component_id,geometry:row.geometry,geometry_sha256:row.geometry_sha256,source_receipt_sha256:row.source_receipt_sha256}))}};
    }
  }
  const actualEffectiveDigest=additiveReleaseFootprintDigest(baseReference,features);
  require(actualEffectiveDigest===data.reference_release.footprints_sha256,'Explicit additive footprint domain differs from selected release');
  verifyAdditiveLedgerSelection(ledger,features,patch);
  // The immutable native manifest predates the explicit leaf-owner binding.
  // Authenticate the WHOLE selected original bounds roster, never a target-only
  // assertion or an inferred nearest owner, before adding metadata to its view.
  const roster=await readWholeAdditiveAsset(release.owner_roster,fetcher,'Native owner roster');
  require(Array.isArray(roster)&&roster.length===features.length,'Incomplete selected native owner roster');
  const byId=new Map(features.map(feature=>[feature.id,feature])),positions=new Map(features.map((feature,index)=>[feature.id,index])),indices=new Set(),ids=new Set();
  for(const row of roster){
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
  const boundBase={...base,reference_owner_sha256:ownerDigest,reference_owner_source_sha256:release.owner_roster.sha256};
  const installed=applyAdditiveNativePatch(boundBase,patch,{baseReference,effectiveReference:data.reference_release,features});
  for(let i=0;i<features.length;i++)originalFeatures[i]=features[i];
  return installed;
}

// Explicit release domain: producer authenticates immutable whole base custody;
// geometry consumers separately rehash ALL loaded base identities/geometries. This
// digest does not assert that the producer reread the entire world geometry.
export function additiveReleaseFootprintDigest(baseReference,features) {
  if (features.some(feature => feature?.additiveFootprint?.version === 2)) return versionedReleaseFootprintDigest(baseReference,features);
  exactKeys(baseReference,['id','footprints_sha256','hierarchy_sha256'],'Additive base reference');
  require(hex.test(baseReference.footprints_sha256)&&hex.test(baseReference.hierarchy_sha256)&&baseReference.id.startsWith('geography:'),'Incomplete additive digest base');
  const additions=features.filter(feature=>Object.hasOwn(feature,'additiveFootprint')).sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0);
  require(additions.length>0,'Explicit additive digest requires complete additions');
  const ids=new Set(),owners=new Set();let ledger,rule;
  for(const feature of additions) {
    effectivePrimitiveGeometries(feature);
    require(!ids.has(feature.id)&&Number.isInteger(feature.pixelIndex)&&feature.pixelIndex>0&&feature.pixelIndex<2**26&&!owners.has(feature.pixelIndex),'Duplicate/missing additive digest owner/identity');
    ids.add(feature.id);owners.add(feature.pixelIndex);
    const value=feature.additiveFootprint;
    require(value.baseline_release_sha256===baseReference.footprints_sha256,'Stale additive digest baseline');
    if(ledger===undefined){ledger=value.ledger_sha256;rule=value.rule_sha256;}
    require(value.ledger_sha256===ledger&&value.rule_sha256===rule,'Incomplete mixed-rule/ledger additive digest');
  }
  return footprintValueSha256({domain:'worldatlas-effective-native-footprints:v1',base_reference:baseReference,
    additions:additions.map(feature=>({id:feature.id,pixelIndex:feature.pixelIndex,footprint:feature.additiveFootprint}))});
}

// V2 keeps each complete original component and its issued policy authority.
// The current base is a separate binding, authenticated by current-bank rebind;
// original component base geometry is never relabelled as that current base.
function versionedPrimitiveGeometries(feature) {
  require(feature && typeof feature.id === 'string' && feature.id && Number.isSafeInteger(feature.pixelIndex) && feature.pixelIndex > 0,
    'Missing versioned effective owner identity');
  polygonParts(feature.geometry);
  const value=feature.additiveFootprint;
  exactKeys(value,['version','kind','baseline_release_sha256','base_geometry_sha256','ledger_sha256','authority_registry_sha256','components'],'Versioned additive footprint');
  require(value.version===2 && value.kind===EFFECTIVE_FOOTPRINT_KIND,'Unsupported versioned footprint');
  for(const key of ['baseline_release_sha256','base_geometry_sha256','ledger_sha256','authority_registry_sha256'])
    require(hex.test(value[key]??''),'Missing versioned footprint binding: '+key);
  require(value.base_geometry_sha256===footprintValueSha256(feature.geometry),'Current retained base changed');
  require(Array.isArray(value.components)&&value.components.length>0,'Missing complete original components');
  let previous='';const output=[feature.geometry];
  for(const row of value.components){
    exactKeys(row,['base_geometry','base_geometry_sha256','component_id','disposition','geometry','geometry_sha256','native_cells','pixelIndex','source_receipt_sha256','target_id','authority_sha256','rule_sha256'],'Original authority component');
    require(typeof row.component_id==='string'&&row.component_id>previous&&row.target_id===feature.id&&row.pixelIndex===feature.pixelIndex,'Foreign/duplicate/unordered component owner');
    previous=row.component_id;
    for(const key of ['base_geometry_sha256','geometry_sha256','source_receipt_sha256','authority_sha256','rule_sha256'])
      require(hex.test(row[key]??''),'Incomplete original component authority: '+key);
    require(Number.isSafeInteger(row.native_cells)&&(['assigned','zero-cell'].includes(row.disposition))
      &&(row.disposition==='assigned'?row.native_cells>0:row.native_cells===0),'False original native contribution');
    polygonParts(row.base_geometry);polygonParts(row.geometry);
    require(footprintValueSha256(row.base_geometry)===row.base_geometry_sha256&&footprintValueSha256(row.geometry)===row.geometry_sha256,'Original complete component pointsets changed');
    output.push(row.geometry);
  }
  return output;
}

function versionedReleaseFootprintDigest(baseReference,features) {
  exactKeys(baseReference,['id','footprints_sha256','hierarchy_sha256'],'Versioned base reference');
  require(typeof baseReference.id==='string'&&baseReference.id.startsWith('geography:')&&hex.test(baseReference.footprints_sha256)&&hex.test(baseReference.hierarchy_sha256),'Incomplete versioned base reference');
  const selected=features.filter(feature=>Object.hasOwn(feature,'additiveFootprint'));
  require(selected.length>0,'Missing versioned components');
  const owners=new Set(),ids=new Set(),components=new Map();let ledger,registry;
  for(const feature of selected){
    require(feature.additiveFootprint.version===2,'Mixed original/versioned effective footprint domain');
    versionedPrimitiveGeometries(feature);
    require(!ids.has(feature.id)&&!owners.has(feature.pixelIndex),'Duplicate effective target/owner');ids.add(feature.id);owners.add(feature.pixelIndex);
    const value=feature.additiveFootprint;
    require(value.baseline_release_sha256===baseReference.footprints_sha256,'Stale versioned base');
    if(ledger===undefined){ledger=value.ledger_sha256;registry=value.authority_registry_sha256;}
    require(value.ledger_sha256===ledger&&value.authority_registry_sha256===registry,'Mixed complete ledger/authority registry');
    for(const row of value.components){require(!components.has(row.component_id),'Duplicate component across owners');components.set(row.component_id,row);}
  }
  return footprintValueSha256({domain:'worldatlas-effective-native-footprints:v2',base_reference:baseReference,
    authority_registry_sha256:registry,ledger_sha256:ledger,
    components:[...components.values()].sort((a,b)=>a.component_id<b.component_id?-1:a.component_id>b.component_id?1:0)});
}

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
    &&Number.isSafeInteger(pin.bytes)&&pin.bytes>0&&pin.bytes<=32*1024*1024&&hex.test(pin.sha256),'Incomplete current rebind custody');
  // This pin is independently authenticated by the selected authority reader.
  // Browser consumption relies on the selected whole ledger, never infers a
  // source approval or qualification from the shape of this pin.
  require(Array.isArray(ledger.current_targets)&&ledger.current_targets.length>0,'Missing complete current rebind targets');let previous='';
  for(const row of ledger.current_targets){
    exactKeys(row,['target_id','pixelIndex','geometry','geometry_sha256'],'Current target binding');
    require(typeof row.target_id==='string'&&row.target_id>previous&&Number.isSafeInteger(row.pixelIndex)&&row.pixelIndex>0,'Foreign/duplicate/unordered current target');previous=row.target_id;
    polygonParts(row.geometry);require(hex.test(row.geometry_sha256)&&footprintValueSha256(row.geometry)===row.geometry_sha256,'Current target pointset changed');targets.set(row.target_id,row);
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
  require(Number.isSafeInteger(ledger.parent_inventory?.components)&&ledger.parent_inventory.components>=ledger.rows?.length
    &&hex.test(ledger.parent_inventory?.report_sha256)&&hex.test(ledger.parent_inventory?.roster_sha256),'Missing original complete inventory denominator');
  require(Array.isArray(ledger.scope_ids)&&Array.isArray(ledger.rows)&&ledger.scope_ids.length===ledger.rows.length,'Missing complete original versioned scope');
  const targets=versionedCurrentTargets(ledger),wanted=new Map();let previous='';
  for(let i=0;i<ledger.rows.length;i++){
    const row=ledger.rows[i];require(row.component_id===ledger.scope_ids[i]&&row.component_id>previous,'Foreign/duplicate/unordered original component');previous=row.component_id;
    require(['assigned','zero-cell','already-resolved','rejected','awaiting-evidence'].includes(row.disposition),'Unknown original component disposition');
    if(['assigned','zero-cell'].includes(row.disposition))wanted.set(row.component_id,row);
  }
  const seen=new Set(),targetIds=new Set();
  for(const feature of features)if(Object.hasOwn(feature,'additiveFootprint')){
    require(feature.additiveFootprint.version===2,'Mixed versioned selected footprint');versionedPrimitiveGeometries(feature);
    const value=feature.additiveFootprint,target=targets.get(feature.id);
    require(target&&target.pixelIndex===feature.pixelIndex&&target.geometry_sha256===value.base_geometry_sha256
      &&value.authority_registry_sha256===ledger.authority_registry_sha256&&value.ledger_sha256===patch.ledger_sha256
      &&value.baseline_release_sha256===patch.base_reference.footprints_sha256,'Foreign current target/registry/ledger/base binding');targetIds.add(feature.id);
    for(const component of value.components){const original=wanted.get(component.component_id);
      require(original&&!seen.has(component.component_id)&&footprintValueSha256(original)===footprintValueSha256(component),'Original component authority removed/rebound');seen.add(component.component_id);}
  }
  require(seen.size===wanted.size&&targetIds.size===targets.size,'Incomplete selected original components/current target scope');
  const allowed=new Set([...wanted.values()].filter(row=>row.disposition==='assigned').map(row=>row.pixelIndex));
  require(Array.isArray(patch.rows)&&patch.rows.every(row=>row.runs.every(run=>allowed.has(run[2]))),'Native cells assigned to zero-cell/unselected owner');
  const cells=patch.rows.reduce((n,row)=>n+row.runs.reduce((sum,run)=>sum+run[1]-run[0],0),0);
  require(Number.isSafeInteger(cells)&&cells>=0,'Invalid complete current native cell total');
  if(Object.hasOwn(ledger,'assigned_cells'))require(Number.isSafeInteger(ledger.assigned_cells)&&cells===ledger.assigned_cells,'Complete current native cell total differs');
  return {selected_components:wanted.size,assigned_cells:cells};
}

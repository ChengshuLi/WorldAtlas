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
  exactKeys(patch,['version','kind','base_reference','effective_reference','ledger_sha256','rule_sha256','rows'], 'Native additive patch');
  require(patch.version===1&&patch.kind===ADDITIVE_NATIVE_PATCH_KIND,'Unsupported native additive patch');
  const same=(a,b)=>JSON.stringify(canonicalValue(a))===JSON.stringify(canonicalValue(b));
  for(const reference of [baseReference,effectiveReference,patch.base_reference,patch.effective_reference]) {
    exactKeys(reference,['id','footprints_sha256','hierarchy_sha256'],'Additive reference');
    require(typeof reference.id==='string'&&reference.id.startsWith('geography:')&&hex.test(reference.footprints_sha256)&&hex.test(reference.hierarchy_sha256),'Incomplete additive reference');
  }
  require(same(baseReference,patch.base_reference)&&same(effectiveReference,patch.effective_reference),'Stale/foreign additive release');
  require(baseReference.hierarchy_sha256===effectiveReference.hierarchy_sha256,'Additive release cannot change hierarchy');
  require(hex.test(patch.ledger_sha256)&&hex.test(patch.rule_sha256),'Missing additive rule/ledger binding');
  require(base?.version===2&&base.method==='native-linear-evenodd-first-owner-v1'&&base.size===262166&&base.coordinateBits===19
    &&base.rows instanceof Uint32Array&&base.rows.length===base.size*2&&base.runs instanceof Uint32Array&&base.runs.length%2===0,'Additive patch requires complete prepared native ownership');
  const digest=footprintValueSha256(patch);
  if(base.additive_patch_sha256===undefined)require(base.geographic_release===baseReference.id&&base.footprints_sha256===baseReference.footprints_sha256&&base.hierarchy_sha256===baseReference.hierarchy_sha256,'Native additive base differs from selected bank');
  require(Array.isArray(features)&&features.length>0,'Additive patch requires complete effective feature roster');
  const owners=new Set(),allowed=new Set();
  for(const feature of features) {
    require(Number.isInteger(feature.pixelIndex)&&feature.pixelIndex>0&&feature.pixelIndex<2**26&&!owners.has(feature.pixelIndex),'Duplicate/missing stable additive owner');
    owners.add(feature.pixelIndex);effectivePrimitiveGeometries(feature);
    if(Object.hasOwn(feature,'additiveFootprint')) {
      const value=feature.additiveFootprint;
      require(value.baseline_release_sha256===baseReference.footprints_sha256&&value.ledger_sha256===patch.ledger_sha256&&value.rule_sha256===patch.rule_sha256,'Effective primitive differs from patch rule/ledger/base');
      allowed.add(feature.pixelIndex);
    }
  }
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
    effective_footprint_sha256:effectiveReference.footprints_sha256,additive_patch_sha256:digest,additive_ledger_sha256:patch.ledger_sha256,additive_rule_sha256:patch.rule_sha256,additive_added_cells:addedCells};
  installedPatches.set(output,{patch:digest,rows:wordDigest(rows),runs:wordDigest(runs)});
  return output;
}

export function additiveBaseReference(data) {
  if(data.additiveRelease===undefined)return data.reference_release;
  const release=data.additiveRelease;
  exactKeys(release,['version','kind','base_reference','effective_reference','patch'],'Additive release');
  require(release.version===1&&release.kind==='retained-native-base-plus-delta-v1','Unsupported additive release');
  require(JSON.stringify(canonicalValue(release.effective_reference))===JSON.stringify(canonicalValue(data.reference_release)),'Selected additive reference mismatch');
  exactKeys(release.patch,['path','bytes','sha256'],'Native patch asset');
  require(/^additive-repairs\/[a-zA-Z0-9_-]+\.json$/.test(release.patch.path)&&Number.isSafeInteger(release.patch.bytes)
    &&release.patch.bytes>0&&release.patch.bytes<=32*1024*1024&&hex.test(release.patch.sha256),'Unsafe/oversized native patch asset');
  return release.base_reference;
}

export async function loadAdditiveNativePatch(data,features,base,{fetcher=fetch,effectiveDigest}={}) {
  const hasAdditions=features.some(feature=>Object.hasOwn(feature,'additiveFootprint'));
  if(data.additiveRelease===undefined){require(!hasAdditions,'Effective footprint requires an explicit selected additive release');return base;}
  const baseReference=additiveBaseReference(data),release=data.additiveRelease;
  require(hasAdditions&&effectiveDigest===data.reference_release.footprints_sha256,'Selected effective footprint digest mismatch');
  const response=await fetcher('./'+release.patch.path);
  require(response.ok&&response.body,'Native additive patch could not load');
  const reader=response.body.getReader(),chunks=[];let length=0;
  try {
    while(true){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;
      require(length<=release.patch.bytes,'Native patch exceeds declared whole bytes');chunks.push(value);}
  }catch(error){await reader.cancel().catch(()=>{});throw error;}finally{reader.releaseLock();}
  require(length===release.patch.bytes,'Incomplete native patch asset');
  const raw=new Uint8Array(length);let offset=0;for(const chunk of chunks){raw.set(chunk,offset);offset+=chunk.length;}
  require(Array.from(sha256(raw),byte=>byte.toString(16).padStart(2,'0')).join('')===release.patch.sha256,'Native patch whole checksum mismatch');
  const patch=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw));
  return applyAdditiveNativePatch(base,patch,{baseReference,effectiveReference:data.reference_release,features});
}

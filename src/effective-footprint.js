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

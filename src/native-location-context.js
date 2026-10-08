import {effectiveFootprintValue, effectiveNativeRuntimeIndex} from './effective-footprint.js';
import {nativePolygonIntervals, NATIVE_GRID_METHOD} from './native-grid.js';
import {coverageRow} from '../scripts/audit-grid-intervals.mjs';
import {LATITUDE_DIGEST} from './ownership-method.js';
import {nativeSourceDigest} from './native-source-digest.js';

const digest = async bytes => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)),
  byte => byte.toString(16).padStart(2, '0')).join('');
const geometryKey = feature => JSON.stringify(effectiveFootprintValue(feature));
const sameFootprint = (a,b) => a && b && (a.geometry === b.geometry && a.additiveFootprint === b.additiveFootprint
  || geometryKey(a) === geometryKey(b));
const yieldTask = () => new Promise(resolve => setTimeout(resolve, 0));

// Display owners are local dense indices, explicitly mapped to immutable IDs.
// Retained reference owners keep relative precedence; new IDs follow them in
// deterministic code-point order. No name, parent or political field sets order.
export function nativeDisplayContext(referenceFeatures, features) {
  const reference = new Map(), current = new Map();
  for (const feature of referenceFeatures) {
    if (!feature?.id || reference.has(feature.id) || !Number.isInteger(feature.pixelIndex) || feature.pixelIndex < 1)
      throw Error('Invalid original native reference identity');
    reference.set(feature.id, feature);
  }
  if (new Set(referenceFeatures.map(f => f.pixelIndex)).size !== referenceFeatures.length)
    throw Error('Duplicate original native owner index');
  for (const feature of features) {
    if (!feature?.id || current.has(feature.id)) throw Error('Invalid dated native location identity');
    current.set(feature.id, feature);
  }
  const ordered = [...current.values()].sort((a, b) => {
    const ai = reference.get(a.id)?.pixelIndex ?? Infinity, bi = reference.get(b.id)?.pixelIndex ?? Infinity;
    return ai === bi ? (a.id < b.id ? -1 : a.id > b.id ? 1 : 0) : ai < bi ? -1 : 1;
  });
  const owners = ordered.map((feature, i) => ({index: i + 1, id: feature.id,
    referenceIndex: reference.get(feature.id)?.pixelIndex ?? null}));
  return {features: ordered, owners, byId: new Map(owners.map(owner => [owner.id, owner.index]))};
}

function latitudeBounds(item) {
  let min = Infinity, max = -Infinity;
  for (const polygon of item.polygons) for (const ring of polygon)
    for (let k = 1; k < ring.length; k += 2) {min = Math.min(min, ring[k]); max = Math.max(max, ring[k]);}
  return {min, max};
}

// Recompute all native neighbors on every row touched by any removed, added or
// changed original polygon. Other rows reuse the independently verified native
// reference grid with an explicit identity mapping. No proximity/area filling.
export async function compileNativeLocationContext({referenceFeatures, features, base, latitudes,
  signal, onProgress = () => {}, rowBlock = 4096}) {
  if (base?.method !== NATIVE_GRID_METHOD || base.version !== 2 || base.size !== 262166 ||
    base.coordinateBits !== 19 || !(latitudes instanceof Float64Array) || latitudes.length !== base.size ||
    !Number.isInteger(rowBlock) || rowBlock < 1 || rowBlock > 4096) throw Error('Require pinned canonical native context');
  signal?.throwIfAborted();
  const raw = new Uint8Array(latitudes.length * 8), tableView = new DataView(raw.buffer);
  latitudes.forEach((value, y) => tableView.setFloat64(y * 8, value, true));
  if (await digest(raw) !== LATITUDE_DIGEST) throw Error('Native context latitude rule changed');
  const sourceDigest = await nativeSourceDigest(referenceFeatures, {signal, onProgress});
  if (sourceDigest.sha256 !== base.footprints_sha256)
    throw Error('Native context reference source bytes changed');
  const referenceOwners = referenceFeatures.map(f => [f.pixelIndex, f.id]).sort((a, b) => a[0] - b[0]);
  if (await digest(new TextEncoder().encode(JSON.stringify(referenceOwners))) !== base.reference_owner_sha256)
    throw Error('Native context reference owner identity mapping changed');
  const context = nativeDisplayContext(referenceFeatures, features);
  if (context.features.length > 67108863) throw Error('Native display owner capacity exceeded');
  const original = effectiveNativeRuntimeIndex(referenceFeatures), originalById = new Map(referenceFeatures.map(f => [f.id, f]));
  const originalInput = new Map(original.map(item => [item.index, item]));
  const originalBounds = new Map(original.map(item => [item.index, latitudeBounds(item)]));
  const changedInputs=[];
  const contextual=context.features.map((feature,i)=>{
    const old=originalById.get(feature.id);
    if(sameFootprint(old,feature))return {...originalInput.get(old.pixelIndex),index:i+1};
    const input=effectiveNativeRuntimeIndex([{...feature,pixelIndex:i+1}])[0];
    changedInputs.push(input);return input;
  });
  const contextualBounds = contextual.map(item => ({...item, ...latitudeBounds(item)}));
  // This validates every ring, including rings outside the affected latitude band.
  nativePolygonIntervals(original, {size: base.size, rowStart: 0, rowEnd: 1, latitudes});
  if(changedInputs.length)nativePolygonIntervals(changedInputs, {size: base.size, rowStart: 0, rowEnd: 1, latitudes});
  const changedRanges = [];
  const currentById = new Map(features.map(f => [f.id, f]));
  for (const old of referenceFeatures) {
    const next = currentById.get(old.id);
    if (!sameFootprint(old,next))
      changedRanges.push(originalBounds.get(old.pixelIndex));
  }
  for (const item of contextualBounds) {
    const next = context.features[item.index - 1], old = originalById.get(next.id);
    if (!sameFootprint(old,next)) changedRanges.push(item);
  }
  const affected = new Uint8Array(base.size), changedRows = new Map();
  for (const {min, max} of changedRanges) for (let y = 0; y < base.size; y++)
    if (latitudes[y] >= min && latitudes[y] <= max) affected[y] = 1;
  const ownerMap = new Map(referenceFeatures.map(f => [f.pixelIndex, context.byId.get(f.id) ?? 0]));
  let recomputedRows = 0;
  for (let first = 0; first < base.size;) {
    signal?.throwIfAborted();
    if (!affected[first]) {first++; continue;}
    let end = first + 1;
    while (end < base.size && end - first < rowBlock && affected[end]) end++;
    const selected = contextualBounds.filter(item => item.min <= latitudes[first] && item.max >= latitudes[end - 1]);
    const native = nativePolygonIntervals(selected, {size: base.size, rowStart: first, rowEnd: end, latitudes});
    for (let y = first; y < end; y++) if (affected[y]) {
      const segments = [];
      for (const segment of coverageRow(native.rows.get(y) ?? [], base.size)) {
        const id = segment.owners[0];
        if (!id) continue;
        const previous = segments.at(-1);
        if (previous?.id === id && previous.end === segment.start) previous.end = segment.end;
        else segments.push({start: segment.start, end: segment.end, id});
      }
      changedRows.set(y, segments); recomputedRows++;
    }
    onProgress({phase: 'native-rows', recomputedRows});
    await yieldTask();
    first = end;
  }
  const factor = 2 ** 19, ownerBase = 2 ** 13;
  // Stream reference runs rather than allocating tens of millions of temporary
  // segment objects twice. Preserve exactly the same adjacency coalescing rule.
  const visitRow = (y, visit) => {
    if (changedRows.has(y)) {
      for (const {start, end, id} of changedRows.get(y)) visit(start, end, id);
      return;
    }
    const first = base.rows[y * 2], end = first + base.rows[y * 2 + 1];
    let pendingStart = 0, pendingEnd = 0, pendingId = 0;
    for (let n = first; n < end; n++) {
      const wordOne = base.runs[n * 2], wordTwo = base.runs[n * 2 + 1];
      const start = wordOne % factor, runEnd = wordTwo % factor + 1;
      const originalOwner = Math.floor(wordOne / factor) + Math.floor(wordTwo / factor) * ownerBase;
      const id = ownerMap.get(originalOwner);
      if (id === undefined) throw Error('Reference grid owner lacks a stable identity');
      if (!id) throw Error('Removed reference owner appeared outside its native affected rows');
      if (pendingId === id && pendingEnd === start) pendingEnd = runEnd;
      else {
        if (pendingId) visit(pendingStart, pendingEnd, pendingId);
        pendingStart = start; pendingEnd = runEnd; pendingId = id;
      }
    }
    if (pendingId) visit(pendingStart, pendingEnd, pendingId);
  };
  const rows = new Uint32Array(base.size * 2);
  let count = 0;
  for (let y = 0; y < base.size; y++) {
    signal?.throwIfAborted(); rows[y * 2] = count;
    let n = 0; visitRow(y, () => n++); rows[y * 2 + 1] = n; count += n;
    if (y % 4096 === 0) await yieldTask();
  }
  if (count > 2 ** 32 - 1) throw Error('Native context exceeds row-offset capacity');
  const runs = new Uint32Array(count * 2);
  let offset = 0;
  for (let y = 0; y < base.size; y++) {
    signal?.throwIfAborted();
    visitRow(y, (start, end, id) => {
      runs[offset++] = id % ownerBase * factor + start;
      runs[offset++] = Math.floor(id / ownerBase) * factor + end - 1;
    });
    if (y % 4096 === 0) await yieldTask();
  }
  return {grid: {version: 2, coordinateBits: 19, size: base.size, method: NATIVE_GRID_METHOD, rows, runs},
    context, accounting: {rows: base.size, recomputedRows, reusedRows: base.size - recomputedRows,
      sourceDigest, ownerMapping: context.owners, rule: 'exact-native-affected-rows-and-stable-reference-reuse-v1'}};
}

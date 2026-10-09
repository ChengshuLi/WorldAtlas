// Lossless native-runtime operand custody, not a geography transformation.
import {createHash} from 'node:crypto';
import {nativeRuntimeIndex} from '../../../src/native-runtime.js';
const MAX = 32 * 1024 * 1024;
const sha = bytes => createHash('sha256').update(bytes).digest('hex');

export function encodeOperandChunk(features) {
  const index = nativeRuntimeIndex(features);
  const names = new Map(features.map(feature => [feature.pixelIndex, feature.id]));
  let bytes = 0;
  const owners = index.map(item => ({id: names.get(item.index), index: item.index,
    polygons: item.polygons.map(polygon => polygon.map(ring => {
      bytes += ring.byteLength;
      return ring.length;
    }))}));
  if (!Number.isSafeInteger(bytes) || bytes > MAX) throw Error('Operand chunk exceeds whole-body bound');
  const coordinates = Buffer.alloc(bytes);
  let offset = 0;
  for (const item of index) for (const polygon of item.polygons) for (const ring of polygon)
    for (const coordinate of ring) {
      coordinates.writeDoubleLE(coordinate, offset); offset += 8;
    }
  const descriptor = {version: 1, kind: 'complete-native-binary64-operand-chunk',
    encoding: 'ieee754-binary64-le', owners, coordinate_bytes: bytes,
    coordinate_sha256: sha(coordinates)};
  // Exercise the inverse before the chunk may be published.
  const restored = decodeOperandChunk(descriptor, coordinates);
  for (let i = 0; i < index.length; i++) {
    if (index[i].index !== restored[i].index) throw Error('Operand owner inverse mismatch');
    for (let p = 0; p < index[i].polygons.length; p++)
      for (let r = 0; r < index[i].polygons[p].length; r++) {
        const original = index[i].polygons[p][r], inverse = restored[i].polygons[p][r];
        if (original.length !== inverse.length ||
            original.some((coordinate, n) => !Object.is(coordinate, inverse[n])))
          throw Error('Operand binary64 inverse mismatch');
      }
  }
  return {descriptor, coordinates};
}

export function decodeOperandChunk(descriptor, coordinates) {
  if (descriptor?.version !== 1 || descriptor.kind !== 'complete-native-binary64-operand-chunk' ||
      descriptor.encoding !== 'ieee754-binary64-le' || !Buffer.isBuffer(coordinates) ||
      !Number.isSafeInteger(descriptor.coordinate_bytes) || descriptor.coordinate_bytes < 0 ||
      descriptor.coordinate_bytes > MAX || coordinates.length !== descriptor.coordinate_bytes ||
      !Array.isArray(descriptor.owners) || !descriptor.owners.length)
    throw Error('Require complete bounded ordinary operand chunk');
  const names = new Set(); let previous = 0, expected = 0;
  for (const owner of descriptor.owners) {
    if (typeof owner.id !== 'string' || !owner.id || names.has(owner.id) ||
        !Number.isSafeInteger(owner.index) || owner.index <= previous ||
        !Array.isArray(owner.polygons) || !owner.polygons.length)
      throw Error('Invalid original operand owner identity/order');
    names.add(owner.id); previous = owner.index;
    for (const polygon of owner.polygons) {
      if (!Array.isArray(polygon) || !polygon.length) throw Error('Missing complete operand polygon');
      for (const count of polygon) {
        if (!Number.isSafeInteger(count) || count < 8 || count % 2)
          throw Error('Invalid complete operand ring length');
        expected += count * 8;
        if (!Number.isSafeInteger(expected) || expected > MAX) throw Error('Operand allocation exceeds cap');
      }
    }
  }
  if (expected !== coordinates.length || sha(coordinates) !== descriptor.coordinate_sha256)
    throw Error('Incomplete or changed original operand bytes');
  let offset = 0;
  return descriptor.owners.map(owner => ({index: owner.index,
    polygons: owner.polygons.map(polygon => polygon.map(count => {
      const ring = new Float64Array(count);
      for (let i = 0; i < count; i++) { ring[i] = coordinates.readDoubleLE(offset); offset += 8; }
      if (ring[0] !== ring.at(-2) || ring[1] !== ring.at(-1)) throw Error('Unclosed original operand ring');
      for (let i = 0; i < count; i += 2)
        if (!Number.isFinite(ring[i]) || !Number.isFinite(ring[i + 1]) ||
            Math.abs(ring[i]) > 180 || Math.abs(ring[i + 1]) > 90)
          throw Error('Invalid original operand coordinates');
      return ring;
    }))}));
}

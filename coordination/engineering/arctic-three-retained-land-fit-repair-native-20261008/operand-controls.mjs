import assert from 'node:assert/strict';
import {nativeRuntimeIndex} from '../../../src/native-runtime.js';
import {encodeOperandChunk, decodeOperandChunk} from './operand-codec.mjs';
const features = [
  {id: 'original:one', pixelIndex: 1, geometry: {type: 'Polygon', coordinates:
    [[[-0, 0], [1, 0], [1, 1], [-0, 0]]]}},
  {id: 'original:two', pixelIndex: 2, geometry: {type: 'MultiPolygon', coordinates:
    [[[[2, 2], [3, 2], [3, 3], [2, 2]]],
      [[[4, 4], [5, 4], [5, 5], [4, 4]]]]}},
];
const encoded = encodeOperandChunk(features);
assert.deepEqual(decodeOperandChunk(encoded.descriptor, encoded.coordinates), nativeRuntimeIndex(features));
assert(Object.is(decodeOperandChunk(encoded.descriptor, encoded.coordinates)[0].polygons[0][0][0], -0));
const copy = () => structuredClone(encoded.descriptor);
const changed = Buffer.from(encoded.coordinates); changed[0] ^= 1;
assert.throws(() => decodeOperandChunk(encoded.descriptor, changed));
assert.throws(() => decodeOperandChunk(encoded.descriptor, encoded.coordinates.subarray(8)));
let adverse = copy(); adverse.owners.reverse();
assert.throws(() => decodeOperandChunk(adverse, encoded.coordinates));
adverse = copy(); adverse.owners[1].id = adverse.owners[0].id;
assert.throws(() => decodeOperandChunk(adverse, encoded.coordinates));
adverse = copy(); adverse.owners[0].polygons[0][0] = 2 ** 31;
assert.throws(() => decodeOperandChunk(adverse, encoded.coordinates));
adverse = copy(); adverse.encoding = 'native-platform';
assert.throws(() => decodeOperandChunk(adverse, encoded.coordinates));
console.log(JSON.stringify({kind: 'complete operand binary64 tiny controls', positive: 2, negative: 6,
  full_world_executed: false, qualified_science: false}));

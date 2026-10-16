import test from 'node:test';
import assert from 'node:assert/strict';
import {geometryBounds, inclusiveColumnBounds} from './observe-current-fine365.mjs';

test('exact inclusive bounds retain native-centre endpoints and reject outside columns', () => {
  assert.deepEqual(inclusiveColumnBounds(-135, -45, 4), [0, 1]);
  assert.deepEqual(inclusiveColumnBounds(-134, -46, 4), [1, 0]);
  assert.deepEqual(inclusiveColumnBounds(-180, 180, 4), [0, 3]);
  assert.deepEqual(inclusiveColumnBounds(0, 0, 4), [2, 1]);
  assert.deepEqual(inclusiveColumnBounds(-45, -45, 4), [1, 1]);
});

test('complete ring bounds include holes and seam endpoints without a wrap shortcut', () => {
  assert.deepEqual(geometryBounds({type: 'Polygon', coordinates: [
    [[-179, -10], [179, -10], [179, 10], [-179, -10]],
    [[-2, -2], [2, -2], [2, 2], [-2, -2]],
  ]}), {bounds: [-179, -10, 179, 10], vertices: 8});
  assert.throws(() => geometryBounds({type: 'Polygon', coordinates: [[[0, 0], [1, 0], [1, 1], [0, 1]]]}), /Unclosed/);
  assert.throws(() => geometryBounds({type: 'Polygon', coordinates: [[[0, 0], [181, 0], [1, 1], [0, 0]]]}), /Invalid/);
  assert.throws(() => geometryBounds({type: 'Point', coordinates: [0, 0]}), /Unsupported/);
});

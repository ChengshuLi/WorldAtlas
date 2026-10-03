import test from 'node:test';
import assert from 'node:assert/strict';
import {packOwnership} from '../src/pixel-ownership.js';
import {rasterColorNeighbors} from '../scripts/map-color-neighbors.mjs';
const packed = rows => packOwnership({size: rows.length, rows: rows.map(row => Uint32Array.from(row))});
test('raster presentation graph includes true horizontal and vertical shared cells', () => {
  const grid = packed([[0,2,1,2,4,2], [1,3,3], [], []]);
  assert.deepEqual(rasterColorNeighbors(grid), {adjacent: [[1,2],[1,3],[2,3]], nearby: []});
});
test('ocean gaps and diagonal corners do not become territorial adjacency', () => {
  assert.deepEqual(rasterColorNeighbors(packed([[0,1,1],[1,2,2],[],[]])).adjacent, []);
  const grid = packed([[0,1,1,2,3,2],[],[],[]]);
  assert.deepEqual(rasterColorNeighbors(grid), {adjacent: [], nearby: []});
  assert.deepEqual(rasterColorNeighbors(grid, {maxHorizontalGap: 1}), {adjacent: [], nearby: [[1,2]]});
});
test('date-line screen wrap is included and same-owner contact is ignored', () => {
  assert.deepEqual(rasterColorNeighbors(packed([[0,1,1,3,4,2],[],[],[]])).adjacent, [[1,2]]);
  assert.deepEqual(rasterColorNeighbors(packed([[0,1,1,3,4,1],[],[],[]])), {adjacent: [], nearby: []});
});
test('malformed packed rows fail closed instead of emitting an incomplete graph', () => {
  const grid = packed([[0,1,1],[],[],[]]);
  grid.rows[2] = 0;
  assert.throws(() => rasterColorNeighbors(grid), /row bounds/);
  assert.throws(() => rasterColorNeighbors({...grid,version:1}), /Invalid raster/);
  assert.throws(() => rasterColorNeighbors(grid,{maxHorizontalGap:-1}), /Invalid raster/);
});

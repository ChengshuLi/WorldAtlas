import assert from 'node:assert/strict';
import {proveCompletePolygonAppend, affectedRows} from './append-scope.mjs';
const exterior = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]];
const hole = [[2, 2], [3, 2], [3, 3], [2, 2]];
const added = [[20, 20], [21, 20], [21, 21], [20, 20]];
const before = {type: 'Polygon', coordinates: [exterior, hole]};
const rotated = [[10, 10], [10, 0], [0, 0], [0, 10], [10, 10]];
const after = {type: 'MultiPolygon', coordinates: [[rotated, [...hole].reverse()], [added]]};
const proof = proveCompletePolygonAppend(before, after);
assert.equal(proof.preserved_polygons, 1); assert.equal(proof.latitude_min, 20);
assert.equal(proof.latitude_max, 21);
assert.throws(() => proveCompletePolygonAppend(before, {type: 'MultiPolygon', coordinates: [[exterior], [hole], [added]]}));
assert.throws(() => proveCompletePolygonAppend(before, before));
assert.throws(() => proveCompletePolygonAppend(before, {type: 'MultiPolygon', coordinates: [[exterior, hole], [added], [added]]}));
const changed = structuredClone(after); changed.coordinates[0][0][0][0] += 1;
assert.throws(() => proveCompletePolygonAppend(before, changed));
assert.throws(() => affectedRows(proof, Buffer.alloc(262166 * 8)));
console.log(JSON.stringify({positive: 1, negative: 5, full_world_executed: false,
  independently_qualified_scope: false}));

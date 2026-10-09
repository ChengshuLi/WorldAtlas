import assert from 'node:assert/strict';
import {proveRowPreservation} from './selected-native-proof.mjs';
const words = runs => Uint32Array.from(runs.flatMap(([a,b,id]) => [id * 8 + a, b - 1]));
const options = {size: 8, ownerCount: 3, addedOwners: [2]};
assert.deepEqual(proveRowPreservation(words([[1,3,1]]), words([[1,3,1],[4,6,2]]), options),
  {added_cells: 2, removed_cells: 0, reassigned_cells: 0});
assert.deepEqual(proveRowPreservation(words([[1,3,1]]), words([[1,3,1]]), options),
  {added_cells: 0, removed_cells: 0, reassigned_cells: 0});
for (const value of [words([[2,3,1]]),words([[1,3,2]]),words([[1,3,1],[4,6,3]]),
  words([[1,3,1],[2,6,2]]),words([[1,3,1],[6,9,2]])])
  assert.throws(() => proveRowPreservation(words([[1,3,1]]), value, options));
console.log(JSON.stringify({positive: 2, negative: 5, actual_row_preservation_entry: true,
  full_native_rows_computed: 0, fixture_only: true}));

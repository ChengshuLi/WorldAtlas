// Exact selected-row counterparty proof; uses the unchanged native compiler.
import assert from 'node:assert/strict';
import {compileRowBlock} from './compile-row-block.mjs';

export function decodeRowWords(words, size, ownerCount) {
  assert(words instanceof Uint32Array && words.length % 2 === 0);
  const factor = 2 ** Math.ceil(Math.log2(size)), ownerBase = 2 ** (32 - Math.ceil(Math.log2(size)));
  const result = []; let previousEnd = 0;
  for (let i = 0; i < words.length; i += 2) {
    const start = words[i] % factor, end = words[i + 1] % factor + 1;
    const owner = Math.floor(words[i] / factor) + Math.floor(words[i + 1] / factor) * ownerBase;
    assert(start >= previousEnd && end > start && end <= size && owner >= 1 && owner <= ownerCount,
      'Invalid complete original native row words');
    result.push({start, end, owner}); previousEnd = end;
  }
  return result;
}

export function proveRowPreservation(beforeWords, afterWords, {size, ownerCount, addedOwners}) {
  const before = decodeRowWords(beforeWords, size, ownerCount), after = decodeRowWords(afterWords, size, ownerCount);
  const allowed = new Set(addedOwners); let added = 0;
  for (const old of before) {
    let cursor = old.start;
    for (const current of after) {
      if (current.end <= cursor || current.start >= old.end) continue;
      assert(current.start <= cursor && current.owner === old.owner, 'Original owned cell removed or reassigned');
      cursor = Math.min(current.end, old.end);
      if (cursor === old.end) break;
    }
    assert.equal(cursor, old.end, 'Original owned cells missing');
  }
  for (const current of after) {
    let cursor = current.start;
    for (const old of before) {
      if (old.end <= cursor || old.start >= current.end) continue;
      if (old.start > cursor) {
        assert(allowed.has(current.owner), 'Unapproved owner gained previously unowned cells');
        added += old.start - cursor;
      }
      cursor = Math.min(current.end, old.end);
      if (cursor === current.end) break;
    }
    if (cursor < current.end) {
      assert(allowed.has(current.owner), 'Unapproved owner gained previously unowned cells');
      added += current.end - cursor;
    }
  }
  const count = rows => rows.reduce((sum, run) => sum + run.end - run.start, 0);
  assert.equal(count(after) - count(before), added);
  return {added_cells: added, removed_cells: 0, reassigned_cells: 0};
}

export function compileSelectedNativeProof(before, after, {size, latitudes, spans, installedRows,
  changedOwners, ownerCount = 49625}) {
  assert.equal(size, 262166); assert.equal(before.length, ownerCount); assert.equal(after.length, ownerCount);
  assert.equal(ownerCount, 49625); assert.equal(changedOwners.length, 2);
  const changed = new Set(changedOwners); assert.equal(changed.size, 2);
  for (let i = 0; i < ownerCount; i++) {
    assert.equal(before[i].index, i + 1); assert.equal(after[i].index, i + 1);
    if (!changed.has(i + 1)) assert.equal(after[i], before[i], 'Unchanged full owner operand must be shared exactly');
  }
  assert.deepEqual(spans, [[48715, 48774], [62146, 62147]]);
  assert.equal(installedRows.length, 60);
  const originalByRow = new Map(installedRows.map(row => [row.row, row.words]));
  assert.equal(originalByRow.size, 60);
  const windows = []; let addedCells = 0;
  const originals = spans.map(([rowStart, rowEnd]) => {
    const old = compileRowBlock(before, {size, latitudes, rowStart, rowEnd});
    // No successor calculation until every old row in this window reproduces
    // the actual whole-source-authenticated installed native word content.
    for (let y = rowStart; y < rowEnd; y++) {
      const at = (y - rowStart) * 2, offset = old.rows[at], count = old.rows[at + 1];
      assert.deepEqual(old.runs.subarray(offset * 2, (offset + count) * 2), originalByRow.get(y),
        'Original scientific row differs from installed native bank');
    }
    return old;
  });
  for (let window = 0; window < spans.length; window++) {
    const [rowStart, rowEnd] = spans[window], old = originals[window];
    const current = compileRowBlock(after, {size, latitudes, rowStart, rowEnd});
    const conservation = [];
    for (let y = rowStart; y < rowEnd; y++) {
      const at = (y - rowStart) * 2;
      const a = old.rows[at], b = current.rows[at];
      const proof = proveRowPreservation(old.runs.subarray(a * 2, (a + old.rows[at + 1]) * 2),
        current.runs.subarray(b * 2, (b + current.rows[at + 1]) * 2),
        {size, ownerCount, addedOwners: changedOwners});
      addedCells += proof.added_cells; conservation.push({row: y, ...proof});
    }
    windows.push({row_start: rowStart, row_end: rowEnd, before: old, after: current, conservation});
  }
  return {version: 1, kind: 'exact-selected-native-old-new-counterparty-proof', windows,
    full_owner_count: ownerCount, checked_rows: 60, unchanged_rows: size - 60,
    checked_cells: 60 * size, added_cells: addedCells, removed_cells: 0, reassigned_cells: 0,
    source_approval: false, installation_ready: false};
}

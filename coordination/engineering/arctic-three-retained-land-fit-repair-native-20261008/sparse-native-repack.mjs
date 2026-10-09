// Exact word custody after a qualified selected-row proof, no geometry operator.
import assert from 'node:assert/strict';

export function selectedWordPatches(originalRows, windows) {
  assert(originalRows instanceof Uint32Array && originalRows.length % 2 === 0);
  const size = originalRows.length / 2, patches = [];
  let priorRow = -1;
  for (const window of windows) {
    assert(Number.isInteger(window.row_start) && Number.isInteger(window.row_end) &&
      window.row_start > priorRow && window.row_end > window.row_start && window.row_end <= size);
    for (const side of ['before', 'after']) {
      assert(window[side].rows instanceof Uint32Array && window[side].runs instanceof Uint32Array);
      assert.equal(window[side].rows.length, (window.row_end - window.row_start) * 2);
    }
    for (let row = window.row_start; row < window.row_end; row++) {
      const at = (row - window.row_start) * 2, old = window.before, current = window.after;
      assert.equal(old.rows[at + 1], originalRows[row * 2 + 1]);
      const before = old.runs.slice(old.rows[at] * 2, (old.rows[at] + old.rows[at + 1]) * 2);
      const after = current.runs.slice(current.rows[at] * 2, (current.rows[at] + current.rows[at + 1]) * 2);
      assert.equal(before.length, originalRows[row * 2 + 1] * 2);
      assert.equal(after.length, current.rows[at + 1] * 2);
      patches.push({row, offset: originalRows[row * 2] * 2, before, after});
    }
    priorRow = window.row_end - 1;
  }
  return patches;
}

export function patchCompleteRunPart(original, offset, patches, maxBytes = 32 * 1024 * 1024) {
  assert(original instanceof Uint32Array && original.length % 2 === 0);
  assert(Number.isSafeInteger(offset) && offset >= 0 && offset % 2 === 0);
  assert(Number.isSafeInteger(maxBytes) && maxBytes >= 0 && maxBytes <= 32 * 1024 * 1024);
  let previous = offset, length = original.length;
  for (const patch of patches) {
    assert(patch.before instanceof Uint32Array && patch.after instanceof Uint32Array);
    assert(patch.before.length % 2 === 0 && patch.after.length % 2 === 0);
    assert(patch.offset >= previous && patch.offset + patch.before.length <= offset + original.length);
    assert.deepEqual(original.subarray(patch.offset - offset, patch.offset - offset + patch.before.length), patch.before,
      'Sparse replacement must match complete original word content');
    previous = patch.offset + patch.before.length;
    length += patch.after.length - patch.before.length;
  }
  assert(Number.isSafeInteger(length) && length >= 0 && length * 4 <= maxBytes);
  const current = new Uint32Array(length); let read = 0, write = 0;
  for (const patch of patches) {
    const at = patch.offset - offset;
    current.set(original.subarray(read, at), write); write += at - read;
    current.set(patch.after, write); write += patch.after.length; read = at + patch.before.length;
  }
  current.set(original.subarray(read), write); write += original.length - read;
  assert.equal(write, current.length);
  // Build the inverse from exact new offsets, then compare every original word.
  const inverse = new Uint32Array(original.length); read = 0; write = 0; let delta = 0;
  for (const patch of patches) {
    const at = patch.offset - offset + delta;
    inverse.set(current.subarray(read, at), write); write += at - read;
    assert.deepEqual(current.subarray(at, at + patch.after.length), patch.after);
    inverse.set(patch.before, write); write += patch.before.length;
    read = at + patch.after.length; delta += patch.after.length - patch.before.length;
  }
  inverse.set(current.subarray(read), write);
  assert.deepEqual(inverse, original, 'Complete original native part inverse failed');
  return current;
}

export function reindexCompleteRows(originalRows, patches) {
  assert(originalRows instanceof Uint32Array && originalRows.length % 2 === 0);
  const changes = new Map(); let previousRow = -1;
  for (const patch of patches) {
    assert(Number.isInteger(patch.row) && patch.row > previousRow && patch.row < originalRows.length / 2);
    assert.equal(patch.offset, originalRows[patch.row * 2] * 2);
    assert.equal(patch.before.length, originalRows[patch.row * 2 + 1] * 2);
    assert(patch.after.length % 2 === 0);
    changes.set(patch.row, patch); previousRow = patch.row;
  }
  const rows = new Uint32Array(originalRows.length); let oldOffset = 0, newOffset = 0;
  for (let row = 0; row < originalRows.length / 2; row++) {
    assert.equal(originalRows[row * 2], oldOffset, 'Complete original row offsets must be contiguous');
    const oldCount = originalRows[row * 2 + 1], patch = changes.get(row);
    const newCount = patch ? patch.after.length / 2 : oldCount;
    assert(Number.isSafeInteger(newOffset) && newOffset <= 0xffffffff);
    rows[row * 2] = newOffset; rows[row * 2 + 1] = newCount;
    oldOffset += oldCount; newOffset += newCount;
  }
  return {rows, old_run_words: oldOffset * 2, new_run_words: newOffset * 2,
    changed_rows: changes.size, unchanged_row_counts: originalRows.length / 2 - changes.size};
}

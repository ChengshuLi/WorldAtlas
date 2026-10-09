// A completed whole-part byte phase after the qualified selected native pair.
// No geometry crossing/coverage calculation is invoked by this entry.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {readAdmittedBody} from './phase-admission.mjs';
import {decodeInstalledWords} from './selected-native-inputs.mjs';
import {shuffleOwnershipBytes, unshuffleOwnershipBytes} from '../../../src/ownership-codec.js';
import {selectedWordPatches, patchCompleteRunPart, reindexCompleteRows} from './sparse-native-repack.mjs';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
export function repackNativePart(admission, plan) {
  assert.equal(plan.kind, 'qualified-selected-native-whole-part-repack');
  assert.equal(plan.scientific.sha256, 'd8af3b2eaf77f4fa948c01937ccb107f3d7eaa833ea4bac1d4480c633d509794');
  const proof = JSON.parse(readAdmittedBody(admission, plan.scientific.path));
  assert.equal(proof.kind, 'exact-selected-native-old-new-counterparty-proof');
  assert.equal(proof.checked_rows, 60); assert.equal(proof.full_owner_count, 49625);
  assert.equal(proof.added_cells, 141); assert.equal(proof.removed_cells, 0); assert.equal(proof.reassigned_cells, 0);
  const windows = proof.windows.map(window => ({...window,
    before: {...window.before, rows: Uint32Array.from(window.before.rows), runs: Uint32Array.from(window.before.runs)},
    after: {...window.after, rows: Uint32Array.from(window.after.rows), runs: Uint32Array.from(window.after.runs)}}));
  assert.deepEqual(windows.map(window => [window.row_start, window.row_end]), [[48715,48774],[62146,62147]]);
  const rows = decodeInstalledWords(admission, plan.rows);
  const patches = selectedWordPatches(rows, windows);
  assert.equal(patches.length, 60);
  const reindexed = reindexCompleteRows(rows, patches);
  // Actual qualified output proves no run-count change, so every original
  // global row/part offset remains exact. No new row table is manufactured.
  assert.deepEqual(reindexed.rows, rows);
  assert.equal(reindexed.old_run_words, 57617774);
  assert.equal(reindexed.new_run_words, 57617774);
  const manifest = JSON.parse(readAdmittedBody(admission, plan.manifest.path));
  assert.equal(manifest.runWords, 57617774); assert.equal(manifest.size, 262166);
  const declared = manifest.parts.find(part => part.path === plan.part.original_path);
  assert(declared);
  for (const key of ['kind','offset','words','bytes','sha256','decoded_bytes','decoded_sha256','encoding'])
    assert.equal(declared[key], plan.part[key]);
  const original = decodeInstalledWords(admission, plan.part);
  const selected = patches.filter(patch => patch.offset >= plan.part.offset &&
    patch.offset + patch.before.length <= plan.part.offset + plan.part.words);
  assert.equal(selected.length, plan.part.offset === 1048576 ? 59 : 1);
  assert([1048576,3145728].includes(plan.part.offset));
  const current = patchCompleteRunPart(original, plan.part.offset, selected);
  assert.equal(current.length, original.length);
  const canonical = Buffer.alloc(current.length * 4);
  for (let i = 0; i < current.length; i++) canonical.writeUInt32LE(current[i], i * 4);
  const shuffled = shuffleOwnershipBytes(current);
  assert.deepEqual(unshuffleOwnershipBytes(shuffled, current.length), current);
  const encoded = gzipSync(shuffled, {level: 9, mtime: 0});
  assert(encoded.length <= 32 * 1024 * 1024);
  assert(encoded.length + canonical.length * 2 <= plan.output_reserve,
    'Complete encoded/shuffled/canonical part output exceeds admitted reserve');
  const report = {version: 1, kind: 'qualified-selected-native-whole-part-byte-inverse',
    original_part: declared, current_part: {...declared, bytes: encoded.length, sha256: sha(encoded),
      decoded_sha256: sha(canonical)}, unchanged_complete_row_table: true,
    unchanged_global_run_words: true, full_original_word_inverse: true,
    scientific_output_sha256: plan.scientific.sha256, selected_rows: selected.map(patch => patch.row),
    owner_reassignment: 0, removed_cells: 0, activation: false};
  return {encoded, report};
}

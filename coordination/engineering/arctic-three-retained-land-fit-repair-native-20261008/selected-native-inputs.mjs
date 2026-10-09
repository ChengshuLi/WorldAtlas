// Complete authenticated operands and installed rows for the focused comparison.
// The independently pinned launcher must admit this module before import.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {readAdmittedBody} from './phase-admission.mjs';
import {decodeOperandChunk} from './operand-codec.mjs';
import {unshuffleOwnershipBytes} from '../../../src/ownership-codec.js';
import {proveCompletePolygonAppend, affectedRows} from './append-scope.mjs';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const SPANS = [[48715, 48774], [62146, 62147]];
const TARGETS = ['atlas:physical:CAN-15:NWT', 'atlas:physical:CAN-25:NUN'];

export function decodePinnedGzip(admission, pin) {
  const encoded = readAdmittedBody(admission, pin.path);
  assert(Number.isSafeInteger(pin.decoded_bytes) && pin.decoded_bytes > 0);
  const decoded = gunzipSync(encoded, {maxOutputLength: pin.decoded_bytes});
  assert.equal(decoded.length, pin.decoded_bytes);
  assert.equal(sha(decoded), pin.decoded_sha256);
  return decoded;
}

export function decodeInstalledWords(admission, pin) {
  assert.equal(pin.encoding, 'byte-shuffle');
  assert(Number.isSafeInteger(pin.words) && pin.words > 0);
  // This pin authenticates canonical words, not the shuffled gzip payload.
  assert.equal(pin.decoded_bytes, pin.words * 4);
  const shuffled = gunzipSync(readAdmittedBody(admission, pin.path),
    {maxOutputLength: pin.decoded_bytes});
  assert.equal(shuffled.length, pin.decoded_bytes);
  const words = unshuffleOwnershipBytes(shuffled, pin.words);
  const canonical = Buffer.alloc(words.length * 4);
  for (let i = 0; i < words.length; i++) canonical.writeUInt32LE(words[i], i * 4);
  assert.equal(sha(canonical), pin.decoded_sha256);
  return words;
}

function geometry(owner) {
  // The native operand already preserves full polygon and exterior/hole roles.
  return {type: 'MultiPolygon', coordinates: owner.polygons.map(polygon => polygon.map(ring => {
    const points = []; for (let i = 0; i < ring.length; i += 2) points.push([ring[i], ring[i + 1]]);
    return points;
  }))};
}

export function loadSelectedNativeInputs(admission, plan) {
  assert.equal(plan.kind, 'complete-selected-native-input-plan');
  assert.equal(plan.original_manifest_sha256,
    'a71edb65cbd7986e245f626e8a34b70e12c12d081ca24fc936bdd84e1bb07885');
  assert.equal(plan.manifest.sha256, plan.original_manifest_sha256);
  const manifest = JSON.parse(readAdmittedBody(admission, plan.manifest.path));
  assert.equal(manifest.size, 262166);
  for (const pin of [plan.installed_rows, ...plan.installed_runs]) {
    const original = manifest.parts.find(part => part.path === pin.original_path);
    assert(original, 'Whole native member absent from original manifest');
    for (const key of ['kind', 'offset', 'words', 'bytes', 'sha256', 'decoded_bytes', 'decoded_sha256', 'encoding'])
      assert.equal(pin[key], original[key], 'Installed native member differs from original manifest');
  }
  assert.equal(plan.chunks.length, 34);
  assert.equal(plan.context_index.sha256, '2a1ba93fcdfc81da3247e6abacb49a5df6284d6c1ffd2b2a73f4e84c3b760716');
  const originalIndex = JSON.parse(readAdmittedBody(admission, plan.context_index.path));
  assert.equal(originalIndex.parts.length, 34);
  const before = [], names = [], seen = new Set();
  for (let ordinal = 0; ordinal < 34; ordinal++) {
    const chunk = plan.chunks[ordinal]; assert.equal(chunk.ordinal, ordinal);
    const publication = JSON.parse(readAdmittedBody(admission, chunk.publication.path));
    assert.equal(publication.head, plan.operand_head); assert.equal(publication.ordinal, ordinal);
    assert.equal(publication.original_commit, plan.original_commit);
    assert.deepEqual(publication.original_context_pin, originalIndex.parts[ordinal]);
    for (const pin of [chunk.structure, chunk.coordinates]) {
      const published = publication.outputs.find(row => row.path === pin.original_path);
      assert(published);
      for (const key of ['bytes', 'sha256', 'decoded_bytes', 'decoded_sha256'])
        assert.equal(pin[key], published[key], 'Operand differs from actual predecessor output');
    }
    const descriptor = JSON.parse(readAdmittedBody(admission, chunk.structure.path));
    const owners = decodeOperandChunk(descriptor, decodePinnedGzip(admission, chunk.coordinates));
    assert.equal(owners.length, originalIndex.parts[ordinal].owners);
    assert.equal(owners[0].index, originalIndex.parts[ordinal].first_owner);
    for (let i = 0; i < owners.length; i++) {
      const name = descriptor.owners[i].id;
      assert(!seen.has(name), 'Duplicate full original owner ID'); seen.add(name);
      assert.equal(owners[i].index, before.length + 1);
      before.push(owners[i]); names.push(name);
    }
  }
  assert.equal(before.length, 49625); assert.equal(seen.size, 49625);
  const changedPublication = JSON.parse(readAdmittedBody(admission, plan.chunks[4].publication.path));
  for (const pin of [plan.changed.structure, plan.changed.coordinates, plan.changed.complete_rows]) {
    const published = changedPublication.outputs.find(row => row.path === pin.original_path);
    assert(published);
    for (const key of ['bytes', 'sha256', 'decoded_bytes', 'decoded_sha256'])
      assert.equal(pin[key], published[key], 'Changed operand differs from complete predecessor output');
  }
  // Retain the complete source feature rows as admitted custody, while the
  // numerical operator consumes their previously proved binary64 operands.
  const complete = JSON.parse(readAdmittedBody(admission, plan.changed.complete_rows.path));
  assert.equal(complete.length, 2);
  const variant = JSON.parse(readAdmittedBody(admission, plan.changed.structure.path));
  assert.deepEqual(variant.owners.map(owner => owner.id), TARGETS);
  const changed = decodeOperandChunk(variant, decodePinnedGzip(admission, plan.changed.coordinates));
  const replacements = new Map();
  const latitudeBytes = decodePinnedGzip(admission, plan.latitudes);
  const appendProofs = changed.map((owner, i) => {
    assert.equal(names[owner.index - 1], TARGETS[i]);
    replacements.set(owner.index, owner);
    const proof = proveCompletePolygonAppend(geometry(before[owner.index - 1]), geometry(owner));
    const span = affectedRows(proof, latitudeBytes);
    assert.deepEqual([span.row_start, span.row_end], SPANS[i]);
    return {id: TARGETS[i], owner: owner.index, ...proof, ...span};
  });
  assert.equal(replacements.size, 2);
  const after = before.map(owner => replacements.get(owner.index) ?? owner);
  const latitudes = new Float64Array(262166);
  for (let i = 0; i < latitudes.length; i++) latitudes[i] = latitudeBytes.readDoubleLE(i * 8);
  const rows = decodeInstalledWords(admission, plan.installed_rows);
  assert.equal(rows.length, 262166 * 2);
  assert.equal(plan.installed_runs.length, 2);
  const parts = plan.installed_runs.map(pin => ({pin, words: decodeInstalledWords(admission, pin)}));
  const installedRows = [];
  for (const [start, end] of SPANS) for (let row = start; row < end; row++) {
    const offset = rows[row * 2] * 2, count = rows[row * 2 + 1] * 2;
    const part = parts.find(({pin}) => offset >= pin.offset && offset + count <= pin.offset + pin.words);
    assert(part, 'Complete installed row must be contained in admitted whole run part');
    installedRows.push({row, words: part.words.slice(offset - part.pin.offset, offset - part.pin.offset + count)});
  }
  return {before, after, names, appendProofs, options: {size: 262166, latitudes, spans: SPANS,
    installedRows, changedOwners: changed.map(owner => owner.index), ownerCount: 49625}};
}

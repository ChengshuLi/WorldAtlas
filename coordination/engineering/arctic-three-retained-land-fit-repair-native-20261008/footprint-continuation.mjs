import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

// Preserve the exact stock footprint JSON byte sequence while retaining only
// one serialized geometry per original owner, rather than two world graphs.
export function footprintContinuation(expectedCount, changedRows) {
  assert(Number.isSafeInteger(expectedCount) && expectedCount > 0);
  assert(Array.isArray(changedRows) && changedRows.length === 2);
  const expected = ['atlas:physical:CAN-15:NWT', 'atlas:physical:CAN-25:NUN'];
  assert.deepEqual(changedRows.map(row => row.id).sort(), expected);
  const changes = new Map(changedRows.map(row => [row.id, row]));
  const rows = new Map(), owners = new Set();
  return {
    add(features, firstOwner, count) {
      assert(Array.isArray(features) && features.length === count);
      for (let i = 0; i < features.length; i++) {
        const row = features[i];
        assert.equal(row.pixelIndex, firstOwner + i);
        assert.equal(typeof row.id, 'string');
        assert(!rows.has(row.id) && !owners.has(row.pixelIndex), 'Duplicate original owner');
        assert(row.geometry && ['Polygon', 'MultiPolygon'].includes(row.geometry.type));
        const next = changes.get(row.id);
        if (next) {
          assert.equal(next.pixelIndex, row.pixelIndex);
          assert.deepEqual(next.properties, row.properties, 'Original complete context metadata must stay exact');
          assert.notDeepEqual(next.geometry, row.geometry, 'Expected genuine changed geometry');
        }
        rows.set(row.id, {old: JSON.stringify([row.id, row.geometry]),
          current: next ? JSON.stringify([next.id, next.geometry]) : null});
        owners.add(row.pixelIndex);
      }
    },
    finish() {
      assert.equal(rows.size, expectedCount); assert.equal(owners.size, expectedCount);
      for (let owner = 1; owner <= expectedCount; owner++) assert(owners.has(owner));
      for (const id of expected) assert(rows.has(id), 'Complete changed owner presence');
      const old = createHash('sha256').update('['), current = createHash('sha256').update('[');
      const ids = [...rows.keys()].sort((a, b) => a.localeCompare(b));
      for (let i = 0; i < ids.length; i++) {
        if (i) { old.update(','); current.update(','); }
        const row = rows.get(ids[i]); old.update(row.old); current.update(row.current ?? row.old);
      }
      return {original_footprints_sha256: old.update(']').digest('hex'),
        current_footprints_sha256: current.update(']').digest('hex'),
        owners: expectedCount, changed_ids: expected, unchanged_owners: expectedCount - 2,
        serialization: 'Exact stock JSON.stringify(sorted [id,geometry]) byte sequence'};
    },
  };
}

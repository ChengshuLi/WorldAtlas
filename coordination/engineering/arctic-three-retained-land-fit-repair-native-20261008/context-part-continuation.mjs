import assert from 'node:assert/strict';

// The entire original owner chunk remains present and ordered. Only the two
// independently qualified complete geometry fields are substituted.
export function continueContextPart(before, changedRows, {firstOwner, owners}) {
  assert(Array.isArray(before) && before.length === owners);
  assert(Array.isArray(changedRows) && changedRows.length === 2);
  const ids = ['atlas:physical:CAN-15:NWT', 'atlas:physical:CAN-25:NUN'];
  assert.deepEqual(changedRows.map(row => row.id).sort(), ids);
  const changes = new Map(changedRows.map(row => [row.id, row]));
  const seen = new Set(), changed = [];
  const after = before.map((row, i) => {
    assert.equal(row.pixelIndex, firstOwner + i);
    assert(typeof row.id === 'string' && !seen.has(row.id)); seen.add(row.id);
    const next = changes.get(row.id);
    if (!next) return row;
    assert.deepEqual(Object.keys(next), Object.keys(row));
    for (const key of Object.keys(row)) if (key !== 'geometry') assert.deepEqual(next[key], row[key]);
    assert.notDeepEqual(next.geometry, row.geometry);
    changed.push(row.id);
    return {...row, geometry: next.geometry};
  });
  assert.deepEqual(changed.sort(), ids, 'Both qualified targets required in complete chunk');
  assert.equal(after.length, before.length);
  return {after, changed_ids: changed, unchanged_full_rows: owners - 2,
    complete_owner_order_preserved: true};
}

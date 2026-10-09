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

export function continueContextIndex(index, currentPart, footprints) {
  assert.equal(index.version, 1); assert.equal(index.locations, 49625);
  assert.equal(index.owner_sha256, '90facdfa2c74a935e7e64fe2b2467de3b09f3b816eb96ba350f4f5bacb2227c2');
  assert.equal(index.footprints_sha256, footprints.original_footprints_sha256);
  assert.equal(footprints.original_footprints_sha256, 'b9a3c8bf375217dba3a50d1a022ec7e4ac6c6f1cdedff22845da953c805b7433');
  assert.equal(footprints.current_footprints_sha256, '2deeff1457ff9238cb3dbe599e9a858dcce29d8ba88e2a66abe2785ddec0aed9');
  assert.equal(index.parts.length, 34);
  assert.equal(currentPart.path, index.parts[4].path);
  assert.equal(currentPart.first_owner, index.parts[4].first_owner);
  assert.equal(currentPart.owners, index.parts[4].owners);
  let nextOwner = 1;
  for (const part of index.parts) { assert.equal(part.first_owner, nextOwner); nextOwner += part.owners; }
  assert.equal(nextOwner, index.locations + 1);
  const after = {...index, footprints_sha256: footprints.current_footprints_sha256,
    parts: index.parts.map((part, ordinal) => ordinal === 4 ? currentPart : part)};
  assert.equal(after.locations, index.locations); assert.equal(after.owner_sha256, index.owner_sha256);
  for (let ordinal = 0; ordinal < 34; ordinal++) if (ordinal !== 4) assert.equal(after.parts[ordinal], index.parts[ordinal]);
  return after;
}

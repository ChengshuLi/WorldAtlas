import assert from 'node:assert/strict';

// Application representation only. Qualified coordinate values are never
// recomputed. Retain every unchanged source record's literal JSON bytes so the
// stock JSON.stringify footprint remains associated with prepared products.
export function serializeQualifiedGeometryChanges(originalRaw, qualifiedRaw, changedIds) {
  assert(Buffer.isBuffer(originalRaw) && Buffer.isBuffer(qualifiedRaw));
  assert(Array.isArray(changedIds) && changedIds.length > 0);
  assert.equal(new Set(changedIds).size, changedIds.length);
  const original = JSON.parse(originalRaw), qualified = JSON.parse(qualifiedRaw);
  assert(Array.isArray(original.features) && Array.isArray(qualified.features));
  assert.deepEqual({...original, features: null}, {...qualified, features: null});
  assert.equal(original.features.length, qualified.features.length);
  const expected = new Set(changedIds), actual = [], seen = new Set();
  const replacements = new Map();
  for (let i = 0; i < original.features.length; i++) {
    const before = original.features[i], after = qualified.features[i];
    assert.equal(before.id, after.id, 'Complete feature order must be preserved');
    assert(typeof before.id === 'string' && !seen.has(before.id)); seen.add(before.id);
    assert.deepEqual({...before, geometry: null}, {...after, geometry: null});
    if (expected.has(before.id)) {
      assert.notDeepEqual(before.geometry, after.geometry, 'Declared change must be consequential');
      actual.push(before.id);
      replacements.set(i, JSON.stringify({...before, geometry: after.geometry}));
    } else assert.deepEqual(before, after, 'Undeclared source change');
  }
  assert.deepEqual(actual.slice().sort(), changedIds.slice().sort(), 'Missing qualified target');
  const text = originalRaw.toString('utf8');
  assert(Buffer.from(text).equals(originalRaw), 'Original must be exact UTF-8');
  // Locate the top-level features array using JSON lexical depth, not a
  // substring which could occur in a name/property value.
  let depth = 0, arrayStart = -1;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') {
      const start = i++;
      for (; i < text.length; i++) { if (text[i] === '\\') i++; else if (text[i] === '"') break; }
      if (depth === 1 && JSON.parse(text.slice(start, i + 1)) === 'features') {
        let j = i + 1; while (/\s/.test(text[j])) j++;
        if (text[j] === ':') { j++; while (/\s/.test(text[j])) j++; assert.equal(text[j], '['); assert.equal(arrayStart, -1); arrayStart = j; }
      }
    } else if (c === '{' || c === '[') depth++;
    else if (c === '}' || c === ']') depth--;
  }
  assert(arrayStart >= 0);
  const spans = []; let start = -1; depth = 0;
  for (let i = arrayStart + 1; i < text.length; i++) {
    const c = text[i];
    if (c === '"') { for (i++; i < text.length; i++) { if (text[i] === '\\') i++; else if (text[i] === '"') break; } }
    else if (c === '{' || c === '[') { if (depth === 0) { assert.equal(c, '{'); start = i; } depth++; }
    else if (c === '}' || c === ']') {
      if (depth === 0) { assert.equal(c, ']'); break; }
      if (--depth === 0) spans.push([start, i + 1]);
    } else if (depth === 0) assert(c === ',' || /\s/.test(c));
  }
  assert.equal(spans.length, original.features.length);
  const pieces = [], inverse = []; let cursor = 0;
  for (const [ordinal, replacement] of replacements) {
    const [start, end] = spans[ordinal];
    assert.deepEqual(JSON.parse(text.slice(start, end)), original.features[ordinal]);
    pieces.push(text.slice(cursor, start), replacement); cursor = end;
    inverse.push({ordinal, id: original.features[ordinal].id, original_record: text.slice(start, end), replacement_record: replacement});
  }
  pieces.push(text.slice(cursor));
  const output = Buffer.from(pieces.join(''));
  assert.deepEqual(JSON.parse(output), qualified);
  return {output, inverse, changed_ids: actual, unchanged_full_records: spans.length - actual.length};
}

export function restoreOriginalGeometrySerialization(output, inverse) {
  assert(Buffer.isBuffer(output) && Array.isArray(inverse) && inverse.length > 0);
  let text = output.toString('utf8');
  const seen = new Set();
  for (const entry of inverse) {
    assert(typeof entry.id === 'string' && !seen.has(entry.id)); seen.add(entry.id);
    assert.equal(JSON.parse(entry.original_record).id, entry.id);
    assert.equal(JSON.parse(entry.replacement_record).id, entry.id);
    const start = text.indexOf(entry.replacement_record);
    assert(start >= 0 && text.indexOf(entry.replacement_record, start + 1) === -1);
    text = text.slice(0, start) + entry.original_record + text.slice(start + entry.replacement_record.length);
  }
  JSON.parse(text);
  return Buffer.from(text);
}

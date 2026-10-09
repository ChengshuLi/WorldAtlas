import assert from 'node:assert/strict';

// Application representation only. Qualified coordinate values are never
// recomputed. Retain every unchanged source record's literal JSON bytes so the
// stock JSON.stringify footprint remains associated with prepared products.
function featureLayout(raw) {
  assert(Buffer.isBuffer(raw));
  const text = raw.toString('utf8');
  assert(Buffer.from(text).equals(raw), 'Source must be exact UTF-8');
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
  const spans = []; let start = -1, arrayEnd = -1, needRecord = true; depth = 0;
  for (let i = arrayStart + 1; i < text.length; i++) {
    const c = text[i];
    if (c === '"') { assert(depth > 0); for (i++; i < text.length; i++) { if (text[i] === '\\') i++; else if (text[i] === '"') break; } }
    else if (c === '{' || c === '[') { if (depth === 0) { assert(needRecord); assert.equal(c, '{'); start = i; } depth++; }
    else if (c === '}' || c === ']') {
      if (depth === 0) { assert.equal(c, ']'); assert(!needRecord || spans.length === 0); arrayEnd = i; break; }
      if (--depth === 0) { spans.push([start, i + 1]); needRecord = false; }
    } else if (depth === 0) {
      if (c === ',') { assert(!needRecord); needRecord = true; }
      else assert(/\s/.test(c));
    }
  }
  assert(arrayEnd >= 0);
  const header = JSON.parse(text.slice(0, arrayStart) + '[]' + text.slice(arrayEnd + 1));
  assert(Array.isArray(header.features));
  return {text, spans, header};
}

export function serializeQualifiedGeometryChanges(originalRaw, qualifiedRaw, changedIds) {
  assert(Array.isArray(changedIds) && changedIds.length > 0);
  assert.equal(new Set(changedIds).size, changedIds.length);
  const original = featureLayout(originalRaw), qualified = featureLayout(qualifiedRaw);
  assert.deepEqual(original.header, qualified.header);
  assert.equal(original.spans.length, qualified.spans.length);
  const expected = new Set(changedIds), actual = [], seen = new Set(), geometryJSON = [];
  const replacements = new Map();
  // Only one complete before/after record pair is parsed at a time. No full
  // third/fourth geometry graph is created merely to prove serialization.
  for (let i = 0; i < original.spans.length; i++) {
    const before = JSON.parse(original.text.slice(...original.spans[i]));
    const after = JSON.parse(qualified.text.slice(...qualified.spans[i]));
    assert.equal(before.id, after.id, 'Complete feature order must be preserved');
    assert(typeof before.id === 'string' && !seen.has(before.id)); seen.add(before.id);
    assert.deepEqual({...before, geometry: null}, {...after, geometry: null});
    if (expected.has(before.id)) {
      assert.notDeepEqual(before.geometry, after.geometry, 'Declared change must be consequential');
      actual.push(before.id);
      geometryJSON.push({id: before.id, geometry_json: JSON.stringify(after.geometry)});
      replacements.set(i, JSON.stringify({...before, geometry: after.geometry}));
    } else assert.deepEqual(before, after, 'Undeclared source change');
  }
  assert.deepEqual(actual.slice().sort(), changedIds.slice().sort(), 'Missing qualified target');
  const {text, spans} = original;
  const pieces = [], inverse = []; let cursor = 0;
  for (const [ordinal, replacement] of replacements) {
    const [start, end] = spans[ordinal];
    pieces.push(text.slice(cursor, start), replacement); cursor = end;
    inverse.push({ordinal, id: JSON.parse(replacement).id, original_record: text.slice(start, end), replacement_record: replacement});
  }
  pieces.push(text.slice(cursor));
  const output = Buffer.from(pieces.join(''));
  return {output, inverse, changed_ids: actual, qualified_geometry_json: geometryJSON,
    unchanged_full_records: spans.length - actual.length};
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
  const restored = featureLayout(Buffer.from(text));
  for (const span of restored.spans) JSON.parse(restored.text.slice(...span));
  return Buffer.from(text);
}

import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const sha = body => createHash('sha256').update(body).digest('hex');

function ringKey(ring) {
  assert(Array.isArray(ring) && ring.length >= 4);
  const points = ring.map(point => {
    assert(Array.isArray(point) && point.length === 2 && point.every(Number.isFinite));
    const bytes = Buffer.alloc(16); bytes.writeDoubleBE(point[0]); bytes.writeDoubleBE(point[1], 8);
    return bytes.toString('hex');
  });
  assert.equal(points[0], points.at(-1), 'Exact closed source ring required');
  points.pop();
  const candidates = [];
  for (const direction of [points, [...points].reverse()]) {
    const smallest = direction.reduce((a, b) => a < b ? a : b);
    for (let i = 0; i < direction.length; i++) if (direction[i] === smallest)
      candidates.push(direction.slice(i).concat(direction.slice(0, i)).join(''));
  }
  return candidates.sort()[0];
}

function polygons(geometry) {
  assert(['Polygon', 'MultiPolygon'].includes(geometry?.type));
  const list = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  assert(Array.isArray(list) && list.length);
  return list.map(polygon => {
    assert(Array.isArray(polygon) && polygon.length);
    const rings = polygon.map(ringKey);
    // Exterior and holes are different roles, even when their edge sets agree.
    return {polygon, key: JSON.stringify([rings[0], rings.slice(1).sort()])};
  });
}

export function proveCompletePolygonAppend(before, after) {
  const old = polygons(before), current = polygons(after), remaining = [...current];
  for (const original of old) {
    const i = remaining.findIndex(row => row.key === original.key);
    assert(i >= 0, 'Complete original polygon/exterior/hole grouping changed');
    remaining.splice(i, 1);
  }
  assert.equal(remaining.length, 1, 'Require exactly one separately added complete polygon');
  const points = remaining[0].polygon.flat();
  assert(points.every(point => Math.abs(point[0]) <= 180 && Math.abs(point[1]) <= 90));
  return {preserved_polygons: old.length, added_polygons: 1,
    original_complete_polygon_sha256: sha(JSON.stringify(old.map(row => row.key).sort())),
    added_complete_polygon_sha256: sha(remaining[0].key),
    latitude_min: Math.min(...points.map(point => point[1])),
    latitude_max: Math.max(...points.map(point => point[1]))};
}

export function affectedRows(proof, latitudeBytes) {
  assert(Buffer.isBuffer(latitudeBytes) && latitudeBytes.length === 262166 * 8);
  assert.equal(sha(latitudeBytes), '66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23');
  assert(Number.isFinite(proof.latitude_min) && Number.isFinite(proof.latitude_max) &&
    proof.latitude_min <= proof.latitude_max);
  let first = null, end = null, previous = 90;
  for (let y = 0; y < 262166; y++) {
    const latitude = latitudeBytes.readDoubleLE(y * 8);
    assert(Number.isFinite(latitude) && latitude < previous && latitude > -90);
    previous = latitude;
    // Inclusive exact endpoints retain horizontal-boundary and vertex ties.
    if (latitude >= proof.latitude_min && latitude <= proof.latitude_max) {
      first ??= y; end = y + 1;
    }
  }
  return {row_start: first, row_end: end, checked_rows: first === null ? 0 : end - first};
}

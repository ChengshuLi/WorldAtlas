import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeOriginalRequestRows} from '../scripts/native-ownership/original-request-rows.mjs';

const columns = ['category', 'y', 'start', 'end', 'owners', 'source_feature_indices', 'physical'];
const packet = rows => ({columns: [...columns], rows});
const options = {owner: 7, size: 12};
const row = (start, end, physical = 'land', category = 'repair', y = 2) =>
  [category, y, start, end, [7], [101, 103], physical];
const normalize = rows => normalizeOriginalRequestRows(packet(rows), options);

test('mixed classes preserve exact intervals/SIDs, separately holding relative and unknown', () => {
  const input = packet([
    row(5, 7, 'inland-water'), row(1, 3), row(3, 5),
    row(8, 10, 'source-relative', 'physical'), row(0, 1, 'unknown', 'physical'),
  ]);
  const before = structuredClone(input);
  const result = normalizeOriginalRequestRows(input, options);
  assert.deepEqual(result.patch, {rows: [{y: 2, runs: [[1, 3, 7], [3, 5, 7], [5, 7, 7]]}]});
  assert.deepEqual(result.coverage_rows, [{y: 2, runs: [
    [1, 3, 'mapped_land_support'], [3, 5, 'mapped_land_support'], [5, 7, 'mapped_inland_water_support'],
  ]}]);
  assert.deepEqual(result.coverage_classes, ['mapped_land_support', 'mapped_inland_water_support']);
  assert.deepEqual(result.requested.rows, before.rows.slice(0, 3));
  assert.deepEqual(result.held.rows, before.rows.slice(3));
  assert.deepEqual(result.counts, {cells: 9, requested_cells: 6, held_cells: 3,
    by_category: {repair: 6, physical: 3}, by_class: {'inland-water': 2, land: 4, 'source-relative': 2, unknown: 1}});
  assert.deepEqual(input, before);
  result.requested.rows[0][5].push(999);
  result.held.rows[0][4][0] = 999;
  assert.deepEqual(input, before, 'result provenance must not alias the original arrays');
});

test('all-held input stays held; explicit unknown under repair does not become land', () => {
  const result = normalize([row(1, 3, 'unknown'), row(4, 6, 'source-relative', 'physical')]);
  assert.deepEqual(result.patch, {rows: []});
  assert.deepEqual(result.coverage_rows, []);
  assert.deepEqual(result.coverage_classes, []);
  assert.equal(result.counts.requested_cells, 0);
  assert.equal(result.counts.held_cells, 4);
});

test('duplicates/overlaps are rejected across requested and held classes, even unsorted', () => {
  for (const rows of [
    [row(1, 3), row(1, 3)],
    [row(3, 6), row(1, 4, 'inland-water')],
    [row(1, 5), row(4, 6, 'source-relative', 'physical')],
    [row(1, 3, 'unknown'), row(2, 4, 'unknown', 'physical')],
  ]) assert.throws(() => normalize(rows), /Duplicate or overlapping/);
});

test('wrong/ambiguous owner, invalid SID, foreign category and unsupported class fail closed', () => {
  const wrongOwner = row(1, 2); wrongOwner[4] = [8];
  const ambiguousOwner = row(1, 2); ambiguousOwner[4] = [7, 8];
  const badSID = row(1, 2); badSID[5] = [101, 101];
  const noSID = row(1, 2); noSID[5] = [];
  const missingSID = row(1, 2); missingSID[5] = Array(1);
  for (const value of [wrongOwner, ambiguousOwner]) assert.throws(() => normalize([value]), /owner/);
  for (const value of [badSID, noSID, missingSID]) assert.throws(() => normalize([value]), /source SID/);
  assert.throws(() => normalize([row(1, 2, 'probably-land')]), /Unsupported original physical class/);
  assert.throws(() => normalize([row(1, 2, 'land', 'conflict')]), /Unsupported original request category/);
  assert.throws(() => normalize([row(1, 2, 'land', 'physical')]), /category and physical class disagree/);
  assert.throws(() => normalize([row(1, 2, 'source-relative')]), /category and physical class disagree/);
});

test('exact schema, native bounds and explicit owner/size are required', () => {
  assert.throws(() => normalizeOriginalRequestRows(packet([row(1, 2)])), /owner and native size/);
  assert.throws(() => normalize([]), /Nonempty/);
  assert.throws(() => normalizeOriginalRequestRows({columns: Array(7), rows: [row(1, 2)]}, options), /columns/);
  assert.throws(() => normalizeOriginalRequestRows({columns: columns.toReversed(), rows: [row(1, 2)]}, options), /columns/);
  for (const value of [row(-1, 2), row(2, 2), row(1, 13), row(1.5, 2), row(1, 2, 'land', 'repair', 12)])
    assert.throws(() => normalize([value]), /native interval/);
});

test('real public Aru slice preserves water instead of calling every repair cell land', () => {
  // 3996a7a34dc8894ccd4b5229036cc9e52f168db1:
  // coordination/engineering/indonesia-kepulauan-aru-20261015/whole-physical-input-001/
  // original-requested-intervals.json, original row ordinals 0, 1646, 2433.
  // Whole body SHA256 6d77f2fc77b6ee6d7c79ec780f9b904984721ad71fdfeece52023e232cc63863.
  const original = packet([
    ['repair', 134972, 229056, 229058, [22734], [36413], 'land'],
    ['repair', 135717, 228894, 228897, [22734], [36249, 36413], 'inland-water'],
    ['physical', 134967, 229081, 229084, [22734], [36413], 'source-relative'],
  ]);
  const result = normalizeOriginalRequestRows(original, {owner: 22734, size: 262166});
  assert.deepEqual(result.patch.rows, [
    {y: 134972, runs: [[229056, 229058, 22734]]},
    {y: 135717, runs: [[228894, 228897, 22734]]},
  ]);
  assert.deepEqual(result.coverage_rows, [
    {y: 134972, runs: [[229056, 229058, 'mapped_land_support']]},
    {y: 135717, runs: [[228894, 228897, 'mapped_inland_water_support']]},
  ]);
  assert.deepEqual(result.counts.by_class, {land: 2, 'inland-water': 3, 'source-relative': 3});
  assert.equal(result.counts.requested_cells, 5);
  assert.deepEqual(result.held.rows, [original.rows[2]]);
});

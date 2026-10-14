import test from 'node:test';
import assert from 'node:assert/strict';
import {diagnoseMapCell} from '../src/map-cell-diagnosis.js';
import {measureCellFeatures, sourceFeatureId} from '../scripts/diagnose-map-cell.mjs';
import {nativeRowLatitudes} from '../src/native-grid.js';

const blank = () => ({effectiveOwner: {index: 0, id: null}, physicalEvidence: [],
  lineage: {original: [], consumed: [], selected: {first_owner: 0, holes: []}, native: {first_owner: 0}},
  intendedLocations: [], transitions: []});
const water = {kind: 'water', covers: true, explicit_feature: true, source: 'mapped lake', date: '2024', coverage: 'mapped water'};
const dry = {kind: 'land', covers: true, explicit_feature: true, excludes_water: true, source: 'physical L1–L4', date: '2017', coverage: 'mapped water excluded'};
const location = {id: 'location:district', index: 7, name: 'District'};

test('explicit mapped water resolves water; a hole and administrative membership cannot', () => {
  const input = blank(); input.lineage.selected.holes.push({id: location.id}); input.intendedLocations.push(location);
  assert.equal(diagnoseMapCell(input).decision, 'unresolved');
  input.physicalEvidence.push(water);
  assert.equal(diagnoseMapCell(input).decision, 'water');
  assert.equal(diagnoseMapCell(input).kind, 'intentional-mapped-water');
  input.physicalEvidence = [{...dry, excludes_water: false}];
  assert.equal(diagnoseMapCell(input).decision, 'unresolved');
});

test('source-relative physical land plus one joined location supports an actionable assignment', () => {
  const input = blank(); input.physicalEvidence.push(dry); input.intendedLocations.push(location);
  const result = diagnoseMapCell(input);
  assert.equal(result.decision, 'land-with-location'); assert.deepEqual(result.intended_location, location);
  assert.deepEqual(result.blockers, []); assert.match(result.next_action, /additive native-cell repair/);
  assert.deepEqual(input.lineage.selected, {first_owner: 0, holes: []});
});

test('conflicting water, competing owners, exact boundary and semantic exclusions withhold assignment', () => {
  for (const change of [
    input => input.physicalEvidence.push(water),
    input => input.intendedLocations.push({...location, id: 'location:other', index: 8}),
    input => input.lineage.selected.holes.push({id: location.id}),
    input => input.lineage.consumed.push({boundary_ties: [{x: 1}]}),
  ]) {
    const input = blank(); input.physicalEvidence.push(dry); input.intendedLocations.push(location); change(input);
    assert.equal(diagnoseMapCell(input).decision, 'unresolved'); assert.ok(diagnoseMapCell(input).blockers.length);
  }
});

test('same-vintage joined loss differs from vintage disagreement and unjoined coincidence', () => {
  const input = blank(), transition = {joined: true, before: true, after: false, same_vintage: true};
  input.transitions.push(transition);
  assert.equal(diagnoseMapCell(input).kind, 'downstream-geometry-loss');
  transition.same_vintage = false;
  assert.equal(diagnoseMapCell(input).kind, 'source-vintage-disagreement');
  transition.same_vintage = null;
  assert.equal(diagnoseMapCell(input).kind, 'mixed-or-unknown');
  transition.joined = false; transition.same_vintage = true;
  assert.equal(diagnoseMapCell(input).kind, 'mixed-or-unknown');
});

test('native versus selected mismatch is visible even under mapped water', () => {
  const input = blank(); input.lineage.selected.first_owner = 7; input.physicalEvidence.push(water);
  assert.equal(diagnoseMapCell(input).kind, 'native-grid-selection-mismatch');
  assert.equal(diagnoseMapCell(input).decision, 'unresolved');
  input.lineage.native.first_owner = 7; input.effectiveOwner = location;
  assert.equal(diagnoseMapCell(input).decision, 'currently-assigned');
  assert.deepEqual(diagnoseMapCell(input).current_owner, location);
  assert.equal(diagnoseMapCell(input).intended_location, null);
  input.lineage.selected.first_owner = 8;
  assert.equal(diagnoseMapCell(input).decision, 'unresolved');
});

const size = 360, latitudes = nativeRowLatitudes(size), context = {size, latitudes};
const rectangle = (west, east, south = -10, north = 10) => [[west, south], [east, south], [east, north], [west, north], [west, south]];
const feature = (id, geometry, pixelIndex = 7) => ({type: 'Feature', id, pixelIndex, properties: {name: id}, geometry});

test('native measurement preserves holes and first-owner semantics independently of feature order', () => {
  const geometry = {type: 'Polygon', coordinates: [rectangle(-10, 10), rectangle(-2, 2, -2, 2)]};
  const hole = measureCellFeatures([feature('donut', geometry)], {x: 180, y: 180}, context);
  assert.equal(hole.matches.length, 0); assert.equal(hole.holes[0].id, 'donut');
  const overlap = measureCellFeatures([feature('later', geometry, 8), feature('earlier', geometry, 3)], {x: 185, y: 180}, context);
  assert.equal(overlap.first_owner, 3); assert.equal(overlap.matches.length, 2);
});

test('split dateline islands do not fill Greenwich and raw over-range longitude is rejected', () => {
  const island = feature('dateline-island', {type: 'MultiPolygon', coordinates: [[rectangle(179, 180)], [rectangle(-180, -179)]]});
  for (const x of [0, 359]) assert.equal(measureCellFeatures([island], {x, y: 180}, context).first_owner, 7);
  assert.equal(measureCellFeatures([island], {x: 180, y: 180}, context).first_owner, 0);
  island.geometry.coordinates[0][0][1][0] = 180.0000000000001;
  assert.throws(() => measureCellFeatures([island], {x: 359, y: 180}, context), /no clamping or longitude wrapping/);
});

test('source joins use stable source identifiers, never a nearby name', () => {
  const raw = {properties: {shapeID: 'ABC', shapeGroup: 'XYZ', shapeType: 'ADM2', shapeName: 'District'}};
  assert.equal(sourceFeatureId(raw, 0), 'gb:XYZ:ADM2:ABC');
  assert.equal(sourceFeatureId({...raw, id: 'atlas:group:ABC'}, 0), 'atlas:group:ABC');
  assert.notEqual(sourceFeatureId({properties: {name: 'District'}}, 0), 'gb:XYZ:ADM2:ABC');
});

test('held-out boundary river observation is not painted as land by a coarser physical mask', () => {
  // Independently checked original JRC February 2024 10W_40N pixel (682,12209)
  // is water at this canonical center. GSHHG 2.3.7 maps surrounding land here.
  // Keep the actual observations; no country/coordinate exception is in code.
  const input = blank(); input.cell = {x: 126023, y: 99412}; input.intendedLocations.push(location);
  input.physicalEvidence = [
    {...dry, source: 'GSHHG 2.3.7 full L1–L4', date: '2017-06-15', coverage: 'Mapped inland waters excluded; narrow rivers may be absent'},
    {...water, source: 'JRC monthly 10W_40N', date: '2024-02', coverage: 'Observed water at the cell center; not permanent-water inference'},
  ];
  const result = diagnoseMapCell(input);
  assert.equal(result.decision, 'unresolved'); assert.equal(result.physical_support, 'conflicting');
  assert.equal(result.intended_location, null); assert.equal(result.kind, 'source-vintage-disagreement');
});

test('anonymous or numeric ordinal features cannot establish an upstream identity join', () => {
  const geometry = {type: 'Polygon', coordinates: [rectangle(-2, 2)]};
  for (const id of [undefined, 0]) {
    const measured = measureCellFeatures([{id, properties: {}, geometry}], {x: 180, y: 180}, context);
    assert.equal(measured.matches.length, 1); assert.equal(measured.matches[0].joinable_id, false);
  }
});

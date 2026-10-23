import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {diagnoseMapCell} from '../src/map-cell-diagnosis.js';
import {diagnoseCells, measureCellFeatures, sourceFeatureId, sourceTransitions} from '../scripts/diagnose-map-cell.mjs';
import {mapCellSelectionFixture} from './fixtures/map-cell-selection.mjs';
import {nativeRowLatitudes} from '../src/native-grid.js';

const blank = () => ({effectiveOwner: {index: 0, id: null}, physicalEvidence: [],
  lineage: {original: [], consumed: [], selected: {first_owner: 0, holes: []}, native: {first_owner: 0}},
  intendedLocations: [], transitions: []});
const water = {kind: 'water', covers: true, explicit_feature: true, source: 'mapped lake', date: '2024', coverage: 'mapped water'};
const dry = {kind: 'land', covers: true, explicit_feature: true, excludes_water: true, source: 'physical L1–L4', date: '2017', coverage: 'mapped water excluded'};
const location = {id: 'location:district', index: 7, name: 'District'};

test('explicit mapped water resolves water; a hole and administrative membership cannot', () => {
  const input = blank(); input.lineage.selected.holes.push({id: location.id}); input.intendedLocations.push(location);
  assert.equal(diagnoseMapCell(input).location_status, 'unresolved');
  input.physicalEvidence.push(water);
  assert.equal(diagnoseMapCell(input).physical_status, 'water-supported');
  assert.equal(diagnoseMapCell(input).location_status, 'unresolved');
  input.physicalEvidence = [{...dry, excludes_water: false}];
  assert.equal(diagnoseMapCell(input).location_status, 'unresolved');
});

test('source-relative physical land plus one joined location supports an actionable assignment', () => {
  const input = blank(); input.physicalEvidence.push(dry); input.intendedLocations.push(location);
  const result = diagnoseMapCell(input);
  assert.equal(result.location_status, 'source-supported'); assert.equal(result.physical_status, 'land-supported'); assert.deepEqual(result.intended_location, location);
  assert.deepEqual(result.blockers, []); assert.match(result.next_action, /source-supported native-cell assignment/);
  assert.deepEqual(input.lineage.selected, {first_owner: 0, holes: []});
});

test('competing owners and unexplained territorial exclusions withhold assignment', () => {
  for (const change of [
    input => input.intendedLocations.push({...location, id: 'location:other', index: 8}),
    input => input.lineage.selected.holes.push({id: location.id}),
  ]) {
    const input = blank(); input.physicalEvidence.push(dry); input.intendedLocations.push(location); change(input);
    assert.equal(diagnoseMapCell(input).location_status, 'unresolved'); assert.ok(diagnoseMapCell(input).blockers.length);
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
  assert.equal(diagnoseMapCell(input).location_status, 'unresolved');
  input.lineage.native.first_owner = 7; input.effectiveOwner = location;
  assert.equal(diagnoseMapCell(input).location_status, 'currently-assigned');
  assert.equal(diagnoseMapCell(input).physical_status, 'water-supported');
  assert.doesNotMatch(diagnoseMapCell(input).next_action, /Preserve.*exclusion/);
  assert.deepEqual(diagnoseMapCell(input).current_owner, location);
  assert.equal(diagnoseMapCell(input).intended_location, null);
  input.lineage.selected.first_owner = 8;
  assert.equal(diagnoseMapCell(input).location_status, 'unresolved');
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
  const input = blank(); input.cell = {x: 126023, y: 99412};
  input.physicalEvidence = [
    {...dry, source: 'GSHHG 2.3.7 full L1–L4', date: '2017-06-15', coverage: 'Mapped inland waters excluded; narrow rivers may be absent'},
    {...water, source: 'JRC monthly 10W_40N', date: '2024-02', coverage: 'Observed water at the cell center; not permanent-water inference'},
  ];
  const result = diagnoseMapCell(input);
  assert.equal(result.physical_status, 'water-supported'); assert.equal(result.physical_source_disagreement, true);
  assert.equal(result.location_status, 'unresolved'); assert.equal(result.intended_location, null);
});

test('anonymous or numeric ordinal features cannot establish an upstream identity join', () => {
  const geometry = {type: 'Polygon', coordinates: [rectangle(-2, 2)]};
  for (const id of [undefined, 0]) {
    const measured = measureCellFeatures([{id, properties: {}, geometry}], {x: 180, y: 180}, context);
    assert.equal(measured.matches.length, 1); assert.equal(measured.matches[0].joinable_id, false);
  }
});

test('coordinate CLI rejects out-of-domain latitude before opening any repository input', () => {
  const command = fileURLToPath(new URL('../scripts/diagnose-map-cell.mjs', import.meta.url));
  const result = spawnSync(process.execPath, [command, '--repo', '/not/a/repository', '--coordinate', '0,90'], {encoding: 'utf8'});
  assert.notEqual(result.status, 0); assert.match(result.stderr, /Coordinate outside the canonical Mercator domain; no clamping/);
  assert.doesNotMatch(result.stderr, /not a git repository/);
});


test('water overlays can coexist with a separately source-supported location', () => {
  const input = blank(); input.physicalEvidence = [water, dry]; input.intendedLocations = [location];
  const result = diagnoseMapCell(input);
  assert.equal(result.physical_status, 'water-supported'); assert.equal(result.physical_source_disagreement, true);
  assert.equal(result.location_status, 'source-supported'); assert.deepEqual(result.intended_location, location);
  assert.doesNotMatch(result.next_action, /owner.?zero|water exclusion/);
});

test('source transitions retain a lost overlapping ID and compare its own feature dates', () => {
  const a = {id: 'A', date: '2001', joinable_id: true}, b = {id: 'B', date: '2001', joinable_id: true};
  const original = [{path: 'original', date: '2020', matches: [a, b]}];
  const consumed = [{path: 'consumed', date: '2020', matches: [b], available_features: [{...a, date: '2002'}, b]}];
  const transitions = sourceTransitions(original, consumed, {matches: [b]}, new Map([['B', b]]));
  assert.deepEqual(transitions[0], {from: 'original', to: 'consumed', ids: ['A'], joined: true, before: true, after: false, same_vintage: false});
  assert.equal(transitions[1].after, true); assert.equal(transitions[1].same_vintage, true);
  assert.deepEqual(transitions[2].ids, ['B']);
});


test('a source-defined native boundary tie does not create an unassigned-cell rule', () => {
  const input = blank(); input.physicalEvidence = [water]; input.intendedLocations = [location];
  input.lineage.consumed = [{boundary_ties: [{kind: 'native-intersection-on-cell-centre', x: 1}]}];
  const result = diagnoseMapCell(input);
  assert.equal(result.boundary_incidence, true); assert.equal(result.location_status, 'source-supported');
  assert.deepEqual(result.intended_location, location); assert.match(result.reasons.join(' '), /declared native sampling rule/);
  input.intendedLocations.push({...location, id: 'location:other', index: 8});
  assert.equal(diagnoseMapCell(input).location_status, 'unresolved');
});


test('actual diagnostic retains native indices while applying authenticated current source and owner parents', async t => {
  const f = mapCellSelectionFixture(t);
  const original = await diagnoseCells({repo: f.repo, commit: f.base, cells: f.cells});
  const current = await diagnoseCells({repo: f.repo, commit: f.current, cells: f.cells});
  for (const [i, report] of current.reports.entries()) {
    assert.equal(report.effectiveOwner.id, 'A'); assert.equal(report.effectiveOwner.index, 1);
    assert.equal(report.effectiveOwner.province_id, 'Q'); assert.equal(report.effectiveOwner.province_index, 2);
    assert.deepEqual(report.diagnosis.current_owner, {id: 'A', index: 1, name: 'Source A'});
    assert.equal(original.reports[i].effectiveOwner.province_id, 'P');
    assert.deepEqual(report.effectiveOwner.bounds, f.owners[0].bounds);
    assert.equal(report.lineage.native.first_owner, original.reports[i].lineage.native.first_owner);
    assert.equal(report.lineage.selected.first_owner, 1); assert.equal(report.effectiveOwner.name, 'Source A');
  }
  const source = current.reports[0].lineage.selected.matches.find(row => row.id === 'A');
  assert.equal(source.tags.parent_id, 'Q');
  assert.deepEqual(source.tags.metadata.reference_corrections, f.currentFeatures[0].properties.metadata.reference_corrections);
  assert.deepEqual(f.currentFeatures.map(row => row.geometry), f.features.map(row => row.geometry));
  assert.equal(f.git('status', '--porcelain'), '');
  f.git('reset', '--hard', f.base);
  const nativeOnly = JSON.parse(f.git('show', f.base + ':data/ownership-selection.json'));
  delete nativeOnly.additive_release; f.write('data/ownership-selection.json', nativeOnly);
  const withoutAdditions = await diagnoseCells({repo: f.repo, commit: f.commit(), cells: f.cells});
  assert.equal(withoutAdditions.reports[0].effectiveOwner.province_id, 'P');
  assert.equal(withoutAdditions.reports[1].effectiveOwner.index, 0);
});

test('actual diagnostic rejects foreign native sidecars and unauthenticated or materially changed projections', async t => {
  const f = mapCellSelectionFixture(t), run = commit => diagnoseCells({repo: f.repo, commit, cells: f.cells});
  const foreignSidecar = structuredClone(f.sidecar); foreignSidecar.base_selection.release_id = 'geography:foreign';
  f.write('data/ownership-selection.json', {...f.selection, additive_release: f.plain('inputs/sidecar.json', foreignSidecar)});
  await assert.rejects(run(f.commit()), /Additive selection belongs to a different base/);
  f.git('reset', '--hard', f.current);
  f.write('inputs/projection.json', {...f.projection, reference: {...f.projection.reference, id: f.projection.reference.id.replace('current', 'changed')}});
  await assert.rejects(run(f.commit()), /Whole immutable input differs/);
  f.git('reset', '--hard', f.current);
  const foreignProjection = {...f.projection, reference: {...f.projection.reference, id: 'geography:foreign'}};
  f.write('data/ownership-selection.json', {...f.selection, reference_projection: f.plain('inputs/projection.json', foreignProjection)});
  await assert.rejects(run(f.commit()), /Current reference metadata differs from the actual latest release/);
  f.git('reset', '--hard', f.current);
  const {reference_projection, ...unprojected} = f.selection; f.write('data/ownership-selection.json', unprojected);
  await assert.rejects(run(f.commit()), /Native source differs from current selected geographic release/);
  f.git('reset', '--hard', f.current);
  const drift = structuredClone(f.currentFeatures); drift[0].geometry.coordinates[0][1][0] += 0.1;
  f.write('data/geography/fixture.json', {type: 'FeatureCollection', features: drift}); const altered = f.commit();
  f.projection.source_updates[0].after = f.pin('data/geography/fixture.json', altered);
  await assert.rejects(run(f.project()), /geometry|Geometry/);
});

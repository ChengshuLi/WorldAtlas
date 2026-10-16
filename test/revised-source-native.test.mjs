import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {nativeRowLatitudes} from '../src/native-grid.js';
import {qualifySourceTargetNativeAuthority, valueSha} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const version = 'a'.repeat(40), size = 262166, y = size / 2, x = size / 2;
const rectangle = (left, right) => ({type: 'Polygon', coordinates: [[[left, -.02], [right, -.02], [right, .02], [left, .02], [left, -.02]]]});
const digest = body => createHash('sha256').update(body).digest('hex');
const blob = body => createHash('sha1').update(`blob ${body.length}\0`).update(body).digest('hex');
const latitudeBody = Buffer.alloc(size * 8);
nativeRowLatitudes(size).forEach((value, index) => latitudeBody.writeDoubleLE(value, index * 8));
const snapshot = '2026-10-16T00:19:04Z', timestamp = '2026-10-13T04:45:39Z';
const sourceId = 'osm:relation:17', targetId = 'stable-existing-owner', family = 'osm:bounded-whole-snapshot';
const prefix = 'coordination/engineering/revised-source-control/';

function fixture(change = () => {}) {
  const bodies = new Map(), reads = [];
  const put = (name, value) => {
    const body = Buffer.isBuffer(value) ? value : Buffer.from(JSON.stringify(value));
    const pin = {commit: version, path: name, mode: '100644', git_blob_oid: blob(body), bytes: body.length, sha256: digest(body)};
    bodies.set(name, {pin, body}); return pin;
  };
  const state = {geometry: rectangle(-.03, .03), base: rectangle(10, 11),
    originalKeys: [{owner: 2, y, x}, {owner: 2, y, x: x + 1}], requestedX: x,
    relationVersion: 2, stageVersion: 2, memberVersion: 2, reviewVersion: 2,
    geometryMutation: false, license: 'ODbL', omitOriginal: false, duplicateMember: false,
    currentGeometryChanged: false, currentAdoptionChanged: false, omitCurrentPart: false,
    otherRelationOverlaps: false, version: 3};
  change(state);
  const rawGeometry = rectangle(-.03, .03);
  const relation = (id, geometry, relationVersion) => ({type: 'relation', id, version: relationVersion, timestamp,
    members: [{type: 'way', ref: id + 100, role: 'outer', geometry: geometry.coordinates[0].map(([lon, lat]) => ({lon, lat}))}]});
  const raw = put(prefix + 'raw.json', {osm3s: {timestamp_osm_base: snapshot}, elements: [relation(17, rawGeometry, state.relationVersion),
    relation(18, state.otherRelationOverlaps ? rawGeometry : rectangle(30, 31), 1)]});
  if (state.geometryMutation) state.geometry = rectangle(-.04, .03);
  const stage = [{target: sourceId, consumed: {type: 'Feature', id: sourceId, geometry: state.geometry, properties: {
    source_provenance: {raw_source_body: {sha256: raw.sha256, bytes: raw.bytes}, relation_version: state.stageVersion,
      relation_timestamp: timestamp, source_snapshot: snapshot, old_atlas_identity: targetId, old_stable_owner: 1}}},
  selected: {type: 'Feature', id: targetId, geometry: state.base, properties: {id: targetId}}}];
  const stagePin = put(prefix + 'stage.json', stage);
  const assessment = put(prefix + 'assessment.json', {source_assessments: [{source_id: sourceId, target_id: targetId,
    stable_owner: 1, relation_version: state.reviewVersion, relation_edit_timestamp: timestamp, snapshot,
    literal_segments_equal_raw_multiset: true, valid_geometry: true, source_identity_and_administrative_role_supported: true}]});
  const scopeRecords = state.originalKeys.map((original_key, index) => ({original_key, new_source_identity: sourceId,
    target_id: targetId, target_owner: 1, source_choice_disposition: index === 0 ? 'supported_for_parent_display_source_choice' : 'blocked_for_proposed_CHN_target'}));
  const scope = put(prefix + 'scope.json', {records: scopeRecords, supported_source_choice_keys: [state.originalKeys[0]]});
  const parent = put(prefix + 'parent.json', {kind: 'bounded-parent-display-source-choice-adoption-v1', decision: 'Accept only the first original key.',
    whole_original_scope: 2, adopted_display_source_choice_keys: 1, blocked_proposed_CHN_keys: 1, native_qualification: false, accepted_map_cells: 0,
    exact_roster: {path: 'scope.json', bytes: scope.bytes, sha256: scope.sha256},
    distinct_scientific_assessment: {path: 'assessment.json', bytes: assessment.bytes, sha256: assessment.sha256}});
  const attribution = put(prefix + 'attribution.json', {provider: 'OpenStreetMap contributors', license: state.license,
    license_url: 'https://opendatacommons.org/licenses/odbl/1-0/', notice: '© OpenStreetMap contributors, ODbL1.0.',
    source_snapshot: snapshot, stage_sha256: stagePin.sha256});
  const index = put('data/world-index.json', {parts: ['geography/part-0.json']});
  const part = put('data/geography/part-0.json', {type: 'FeatureCollection', features: [stage[0].selected,
    {type: 'Feature', id: 'old-question-owner', properties: {id: 'old-question-owner'}, geometry: rectangle(20, 21)}]});
  const latitudes = {...put(prefix + 'latitudes.gz', gzipSync(latitudeBody)),
    decoded_bytes: latitudeBody.length, decoded_sha256: digest(latitudeBody)};
  const fine = put(prefix + 'fine.json', {kind: 'bounded-complete-current-fine-geography-exact-native365-observation-v1',
    feature_inventory: {index_parts: 1, features: 2}, native_rule: {size, latitude_sha256: latitudes.decoded_sha256},
    input_pins: state.omitCurrentPart ? [index] : [index, part],
    records: scopeRecords.map(row => ({original_key: row.original_key, proposed_source_id: sourceId, target_id: targetId,
      target_owner: 1, current_fine_contacts: [], current_fine_boundary_ties: []}))});
  const member = {source_id: sourceId, target_id: targetId, pixelIndex: 1, relation_id: 17, relation_version: state.memberVersion,
    relation_timestamp: timestamp, snapshot_timestamp: snapshot, geometry_sha256: valueSha(state.geometry), base_geometry_sha256: valueSha(state.base)};
  let records = state.originalKeys.map((original_key, index) => ({original_key, source_id: sourceId, target_id: targetId,
    pixelIndex: 1, adopted_display_choice: index === 0}));
  if (state.omitOriginal) records.pop();
  const adoption = put(prefix + 'adoption.json', {version: 1, kind: 'adopted-osm-revised-source-native-v1', source_id: family,
    raw_source: raw, source_stage: stagePin, assessment, scope, parent_decision: parent, current_geography: fine, attribution,
    members: state.duplicateMember ? [member, member] : [member], records});
  const owners = put(prefix + 'owners.json', [{id: targetId, index: 1}, {id: 'old-question-owner', index: 2}]);
  const physical = put(prefix + 'physical.json', {results: [{target: sourceId, issues: [], support: {mapped_land_support: state.geometry}}]});
  const catalogue = put('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json', {products: []});
  const evidence = put(prefix + 'source-evidence.json', {version: state.version, kind: 'source-target-native-evidence-v' + state.version,
    revised_source_adoption: adoption, catalogue, physical_input: stagePin, physical_evidence: physical,
    physical_reproduction: put(prefix + 'physical.py', Buffer.from('# genuine fixture operand')),
    native_latitudes: latitudes, native_contract: {size, native_latitudes: latitudes, original_assets: {bounds: {sha256: owners.sha256}}},
    owner_roster: owners, base_reference: {id: 'unchanged-selected-base'}, families: [{source_id: family, parts: [stagePin]}],
    targets: [{id: sourceId, target_id: targetId, pixelIndex: 1, source_family: family, base_geometry: state.base,
      coverage_classes: ['mapped_land_support'], source_receipt_sha256: physical.sha256}]});
  const patch = put(prefix + 'patch.json', {rows: [{y, runs: [[state.requestedX, state.requestedX + 1, 1]]}]});
  const reader = {version, gitExecutable: 'git', reads,
    git: () => Buffer.alloc(0),
    descriptor(name, selectedVersion = version) {
      assert.ok(bodies.has(name), name);
      const pin = {...bodies.get(name).pin};
      if (name === part.path && state.currentGeometryChanged && selectedVersion === version) pin.git_blob_oid = 'f'.repeat(40);
      if (name === adoption.path && state.currentAdoptionChanged && selectedVersion !== version) pin.git_blob_oid = 'f'.repeat(40);
      return pin;
    },
    read(name, {expected}) { const {body} = bodies.get(name); assert.equal(digest(body), expected); reads.push(name); return body; }};
  const binding = {version: 1, kind: 'source-target-native-custody-v1', source_evidence: evidence, native_patch: patch};
  return {bodies, reader, state, run: () => qualifySourceTargetNativeAuthority(reader, {...binding, kind: 'source-target-native-rule-v1'}, binding)};
}

test('v3 qualifies only the adopted exact native key while retaining distinct source and canonical base', () => {
  const f = fixture(), before = [...f.bodies].map(([name, row]) => [name, Buffer.from(row.body)]);
  const result = f.run();
  assert.equal(result.source_rows.length, 1);
  assert.equal(result.source_rows[0].target_id, targetId);
  assert.equal(result.source_rows[0].native_cells, 1);
  assert.deepEqual(result.source_rows[0].base_geometry, f.state.base);
  assert.deepEqual(result.source_rows[0].native_rows, [{y, runs: [[x, x + 1, 1]]}]);
  assert.ok(f.reader.reads.some(name => name.endsWith('/raw.json')));
  for (const [name, body] of before) assert.deepEqual(f.bodies.get(name).body, body);
});

test('v3 rejects wrong original scope, raw version, geometry, license, competing relation and trusted-tree drift', async t => {
  const mutations = {
    'blocked original key': s => { s.requestedX = x + 1; },
    'omitted adverse original': s => { s.omitOriginal = true; },
    'duplicate whole member': s => { s.duplicateMember = true; },
    'raw relation version': s => { s.relationVersion++; },
    'physical stage version': s => { s.stageVersion++; },
    'substantive review version': s => { s.reviewVersion++; },
    'new geometry with refreshed derived hashes': s => { s.geometryMutation = true; },
    'old target license substituted': s => { s.license = 'PDDL'; },
    'unselected raw relation may compete': s => { s.otherRelationOverlaps = true; },
    'current geometry changed': s => { s.currentGeometryChanged = true; },
    'adoption absent from executing tree': s => { s.currentAdoptionChanged = true; },
    'current indexed part omitted': s => { s.omitCurrentPart = true; },
    'new-source adoption smuggled into v1': s => { s.version = 1; },
  };
  for (const [name, change] of Object.entries(mutations)) await t.test(name, () => assert.throws(() => fixture(change).run()));
});

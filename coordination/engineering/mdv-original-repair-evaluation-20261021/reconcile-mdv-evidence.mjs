// Reproducible exact-interval join for the MDV ADM1 original package.
// This is a retained-input accounting join, not a geometry or qualification test.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const DATA_COMMIT = '7fc7fae5d0caa4153dad87537097591249193117';
const ROOT = fileURLToPath(new URL('../../../', import.meta.url));
const SCRIPT = 'coordination/engineering/mdv-original-repair-evaluation-20261021/reconcile-mdv-evidence.mjs';
const OBSERVATION = 'coordination/engineering/mdv-original-repair-evaluation-20261021/selected-owner-observation.json';
const OUT = 'coordination/engineering/mdv-original-repair-evaluation-20261021/proposed-disposition.json';
const QUEUE_DIR = 'coordination/engineering/global-current-cell-work-queue-20261014';
const CORPUS_DIR = 'coordination/engineering/original-geography-source-corpus-20261006';
const GIT = process.env.MDV_GIT ?? 'git';
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const git = (...args) => execFileSync(GIT, ['-C', ROOT, ...args], {encoding: 'utf8', env: {
  ...process.env, GIT_NO_LAZY_FETCH: '1', GIT_NO_REPLACE_OBJECTS: '1'
}}).trim();

const pins = {
  [`${QUEUE_DIR}/source-package-queue.json`]: '9c9a9bc83627afd3e8435ff4009e39530543bf54',
  [`${QUEUE_DIR}/source-feature-roster.json.gz`]: 'e6e380ec13cd4bcc1d24399a76bfa85ca5805b26',
  [`${QUEUE_DIR}/source-census-summary.json`]: null,
  [`${QUEUE_DIR}/source-raster-summary.json`]: null,
  [`${QUEUE_DIR}/physical-unassigned-summary.json`]: null,
  [`${QUEUE_DIR}/normalized-source-seams.json`]: null,
  [`${QUEUE_DIR}/source-candidates-block-030.json.gz`]: 'bcb16439246dfebc52708996ca21897070c8bc46',
  [`${QUEUE_DIR}/source-candidates-block-031.json.gz`]: '8c513fafe3d2754547cba8c3e8a4c812e8cc520d',
  [`${QUEUE_DIR}/source-candidates-block-032.json.gz`]: '5c56cb06a4879060a4ad933395cd643cdaaa5565',
  [`${QUEUE_DIR}/physical-support-block-030.json.gz`]: 'e87d23b077e9a0b47bcdc38cdf6126f9ca8e3b48',
  [`${QUEUE_DIR}/physical-support-block-031.json.gz`]: 'ea10ba7f8cacba0d3ac4c4967d6f0f501afa1dbb',
  [`${QUEUE_DIR}/physical-support-block-032.json.gz`]: '5f8f1e8aa032abc85e931930eb4eb9b0dbc0ebdb',
  [`${QUEUE_DIR}/inland-water-support-block-030.json.gz`]: '126ed25c39ecf26af8188d20f6f3a0e90bdcbf09',
  [`${QUEUE_DIR}/inland-water-support-block-031.json.gz`]: '15ddbafb578c0b664651bce93956080257e482ef',
  [`${QUEUE_DIR}/inland-water-support-block-032.json.gz`]: '9bee5462a2f4a8bf1e54816c4a3bd61d9227e221',
  [`${QUEUE_DIR}/physical-unknown-envelope-block-030.json.gz`]: '95890a0fc5a9cb9fb6bbd8f48425a8887b043a6e',
  [`${QUEUE_DIR}/physical-unknown-envelope-block-031.json.gz`]: '95890a0fc5a9cb9fb6bbd8f48425a8887b043a6e',
  [`${QUEUE_DIR}/physical-unknown-envelope-block-032.json.gz`]: '95890a0fc5a9cb9fb6bbd8f48425a8887b043a6e',
  [`${QUEUE_DIR}/physical-unknown-residual-block-030.json.gz`]: '95890a0fc5a9cb9fb6bbd8f48425a8887b043a6e',
  [`${QUEUE_DIR}/physical-unknown-residual-block-031.json.gz`]: '95890a0fc5a9cb9fb6bbd8f48425a8887b043a6e',
  [`${QUEUE_DIR}/physical-unknown-residual-block-032.json.gz`]: '95890a0fc5a9cb9fb6bbd8f48425a8887b043a6e',
  [`${QUEUE_DIR}/lineage.json.gz`]: '4ef0728e74e11e069bd7bb11e287c6fbb59946fa',
  [`${QUEUE_DIR}/retained-source-catalogue.json`]: '09afab19371f0814da61e79e5f310c5fb2405b6d',
  [`${QUEUE_DIR}/ownership-binding.json`]: 'b9d81d18aab6d03dc701ff1337b35e53be81d0af',
  [`${CORPUS_DIR}/catalogue.json`]: null,
  [`${CORPUS_DIR}/payloads/gb-MDV-ADM1-000.bin.gz`]: null,
  'data/administrative-sources.json': null
};

const input = name => {
  const full = path.join(ROOT, name);
  const body = fs.readFileSync(full);
  const treeOid = git('rev-parse', `${DATA_COMMIT}:${name}`);
  const worktreeOid = git('hash-object', '--no-filters', full);
  assert.equal(worktreeOid, treeOid, `Worktree input differs from pinned tree: ${name}`);
  if (pins[name]) assert.equal(treeOid, pins[name], `Unexpected input OID: ${name}`);
  const row = {path: name, commit: DATA_COMMIT, blob_oid: treeOid, bytes: body.length, sha256: sha256(body)};
  let decoded = body;
  if (name.endsWith('.gz')) {
    decoded = zlib.gunzipSync(body);
    row.decoded_bytes = decoded.length;
    row.decoded_sha256 = sha256(decoded);
  }
  return {body, decoded, row};
};
const json = name => JSON.parse(input(name).decoded);
const dataPath = name => `${QUEUE_DIR}/${name}`;
const featuresFile = input(`${QUEUE_DIR}/source-feature-roster.json.gz`);
const roster = JSON.parse(featuresFile.decoded);
const featureByIndex = new Map(roster.map(f => [f.source_index, f]));
const queue = json(dataPath('source-package-queue.json'));
assert.equal(queue.current_commit, 'a61b6f9e7f88b1da380e3a834f89d7509132ed71');
const queuePackage = queue.packages.find(p => p.package_id === 'gb-MDV-ADM1--repair-evaluation');
assert.ok(queuePackage);
assert.deepEqual([queuePackage.land_cells, queuePackage.inland_water_cells, queuePackage.interval_segments,
  queuePackage.source_family_index, queuePackage.native_blocks], [850, 0, 228, 207, [30,31,32]]);
assert.deepEqual(queuePackage.source_features, [42130,42131,42133,42136,42138,42148]);
assert.deepEqual(queuePackage.owners, [27463,27464,27465,27472,27476,27478]);
const ids = [42130, 42131, 42133, 42136, 42138, 42148];
const expectedOwners = new Map([[42130, 27478], [42131, 27463], [42133, 27472], [42136, 27476], [42138, 27465], [42148, 27464]]);
const featureRows = ids.map(i => {
  const r = featureByIndex.get(i);
  assert.ok(r, `Missing source roster row ${i}`);
  assert.equal(r.family_index, 207);
  assert.deepEqual(r.owners, [expectedOwners.get(i)]);
  return {source_index: r.source_index, family_index: r.family_index, source_id: r.source_id,
    name: r.name, owner_id: r.owners[0], ordinal: r.ordinal, geometry_status: r.geometry_status};
});

const candidate = {}, physical = {}, water = {}, unknownEnvelope = {}, unknownResidual = {};
for (const block of [30, 31, 32]) {
  const n = String(block).padStart(3, '0');
  candidate[block] = json(dataPath(`source-candidates-block-${n}.json.gz`));
  physical[block] = json(dataPath(`physical-support-block-${n}.json.gz`));
  water[block] = json(dataPath(`inland-water-support-block-${n}.json.gz`));
  unknownEnvelope[block] = json(dataPath(`physical-unknown-envelope-block-${n}.json.gz`));
  unknownResidual[block] = json(dataPath(`physical-unknown-residual-block-${n}.json.gz`));
}
const intervalContains = (rows, y, x, startIndex, endIndex) => {
  const row = rows.find(r => r.y === y);
  return row ? row.runs.filter(run => run[startIndex] <= x && x < run[endIndex]) : [];
};
const reportPath = path.join(ROOT, OBSERVATION);
const observationBytes = fs.readFileSync(reportPath);
const observation = JSON.parse(observationBytes);
assert.equal(observation.kind, 'literal-selected-owner-observation-v1');
assert.equal(observation.commit, DATA_COMMIT);
assert.equal(observation.code_commit, DATA_COMMIT);
assert.equal(observation.original_package.package_id, 'gb-MDV-ADM1--repair-evaluation');
assert.equal(observation.query_count, 850);
assert.equal(observation.keys.length, 850);
assert.equal(observation.keys.every(k => k.base_owner === 0 && k.accepted_additive_owner === 0 &&
  k.effective_selected_owner === 0 && k.owner_id === null && k.existing_product_overlap === false), true);
const observedByKey = new Map(observation.keys.map(k => [`${k.y}:${k.x}`, k]));
assert.equal(observedByKey.size, 850, 'Observation contains duplicate keys');
const blocks = observation.original_intervals;
const sourceCoverage = new Map(), ownerCoverage = new Map(), physicalCoverage = new Map(), waterCoverage = new Map();
const unknownEnvelopeCoverage = new Map(), unknownResidualCoverage = new Map();
const increment = (map, key) => map.set(key, (map.get(key) ?? 0) + 1);
const intervalRows = [];
for (const b of blocks) for (const [y, start, end, ownerIds, sourceIndexes, className] of b.rows) {
  assert.equal(b.block, Math.floor(y / 4096));
  assert.ok(end > start && ownerIds.length === 1 && sourceIndexes.length === 1);
  const sourceIndex = sourceIndexes[0], ownerId = ownerIds[0], feature = featureByIndex.get(sourceIndex);
  assert.ok(feature && feature.owners.includes(ownerId), 'Source roster and interval owner disagree');
  let sourceHits = 0, landHits = 0, waterHits = 0, unknownEnvelopeHits = 0, unknownResidualHits = 0;
  let baseOwners = new Set(), additiveOwners = new Set(), effectiveOwners = new Set(), overlaps = 0;
  for (let x = start; x < end; x++) {
    const keyId = `${y}:${x}`, observed = observedByKey.get(keyId);
    assert.ok(observed, `Original interval key absent from observation: ${keyId}`);
    const cs = intervalContains(candidate[b.block], y, x, 0, 1);
    assert.equal(cs.length, 1, `Candidate contact count for ${keyId}`);
    const candidateOwners = cs[0][2], candidateFeatures = cs[0][3];
    assert.deepEqual(candidateOwners, ownerIds, `Candidate owner differs at ${keyId}`);
    assert.deepEqual(candidateFeatures, sourceIndexes, `Candidate feature differs at ${keyId}`);
    sourceHits++;
    const ps = intervalContains(physical[b.block], y, x, 0, 1);
    const ws = intervalContains(water[b.block], y, x, 0, 1);
    const es = intervalContains(unknownEnvelope[b.block], y, x, 0, 1);
    const rs = intervalContains(unknownResidual[b.block], y, x, 0, 1);
    assert.equal(ps.length, 1, `Physical support count for ${keyId}`);
    assert.equal(ws.length, 0, `Water support unexpectedly overlaps ${keyId}`);
    assert.equal(es.length, 0, `Physical unknown envelope unexpectedly overlaps ${keyId}`);
    assert.equal(rs.length, 0, `Physical unknown residual unexpectedly overlaps ${keyId}`);
    landHits += ps.length; waterHits += ws.length; unknownEnvelopeHits += es.length; unknownResidualHits += rs.length;
    baseOwners.add(observed.base_owner); additiveOwners.add(observed.accepted_additive_owner);
    effectiveOwners.add(observed.effective_selected_owner); if (observed.existing_product_overlap) overlaps++;
    increment(sourceCoverage, sourceIndex); increment(physicalCoverage, keyId);
    for (const _ of ws) increment(waterCoverage, keyId);
    for (const _ of es) increment(unknownEnvelopeCoverage, keyId);
    for (const _ of rs) increment(unknownResidualCoverage, keyId);
  }
  assert.equal(sourceHits, end - start);
  assert.equal(landHits, end - start);
  assert.equal(waterHits + unknownEnvelopeHits + unknownResidualHits, 0);
  assert.deepEqual([...baseOwners], [0]); assert.deepEqual([...additiveOwners], [0]);
  assert.deepEqual([...effectiveOwners], [0]); assert.equal(overlaps, 0);
  const line = {owner_id: ownerId, source_feature_index: sourceIndex,
    source_feature_id: feature.source_id, source_name: feature.name, family_index: feature.family_index,
    block: b.block, interval: [y, start, end], width: end - start,
    queue_physical_class: className,
    retained_candidate_join: {candidate_rows: sourceHits, candidate_owner_ids: ownerIds, source_feature_indices: sourceIndexes},
    retained_physical_join: {land_support_cells: landHits, inland_water_support_cells: waterHits,
      unknown_envelope_cells: unknownEnvelopeHits, unknown_residual_cells: unknownResidualHits},
    selected_owner_observation: {base_owner_ids: [...baseOwners], additive_owner_ids: [...additiveOwners],
      effective_owner_ids: [...effectiveOwners], overlap_keys: overlaps},
    proposal: {status: 'proposed-unresolved', held: true, accepted: false, repair_qualified: false,
      documented_unresolved_exception_accepted: false,
      question: `Does the retained 2017 ${feature.name} source record establish a uniquely applicable current location for this exact interval, given the unverified current vintage, other-source competitor set, and authority/rights evidence?`}};
  intervalRows.push(line);
  const own = ownerCoverage.get(ownerId) ?? {cells: 0, intervals: 0};
  own.cells += end - start; own.intervals++; ownerCoverage.set(ownerId, own);
}
const width = intervalRows.reduce((n, r) => n + r.width, 0);
assert.equal(intervalRows.length, 228);
assert.equal(width, 850);
assert.equal(physicalCoverage.size, 850);
assert.equal([...physicalCoverage.values()].every(n => n === 1), true);
assert.equal(waterCoverage.size, 0);
assert.equal(unknownEnvelopeCoverage.size, 0);
assert.equal(unknownResidualCoverage.size, 0);
assert.equal(sourceCoverage.size, 6);
assert.deepEqual([...sourceCoverage.keys()].sort((a,b)=>a-b), ids);
assert.equal(ownerCoverage.size, 6);
assert.deepEqual([...ownerCoverage.keys()].sort((a,b)=>a-b), [27463,27464,27465,27472,27476,27478]);
const featureCounts = Object.fromEntries([...sourceCoverage].sort((a,b)=>a[0]-b[0]).map(([i,n]) => [String(i), n]));
assert.equal(Object.values(featureCounts).reduce((a,b)=>a+b,0), 850);

const sourceCatalog = json(dataPath('retained-source-catalogue.json'));
const sourceProduct = sourceCatalog.products.find(p => p.key === 'gb:MDV:ADM1');
assert.ok(sourceProduct);
assert.equal(sourceProduct.feature_count, 21);
assert.equal(sourceProduct.source_represented_year_claim, '2017');
const corpusCatalog = json(`${CORPUS_DIR}/catalogue.json`);
const corpusProduct = corpusCatalog.products.find(p => p.key === 'gb:MDV:ADM1');
assert.ok(corpusProduct);
const archive = input(`${CORPUS_DIR}/payloads/gb-MDV-ADM1-000.bin.gz`);
assert.equal(archive.row.bytes, sourceProduct.parts[0].bytes);
assert.equal(archive.row.sha256, sourceProduct.parts[0].sha256);
assert.equal(sha256(archive.decoded), sourceProduct.original_sha256);
const admin = json('data/administrative-sources.json');
const adminSource = admin['gb:MDV:ADM1'];
assert.ok(adminSource);
assert.equal(adminSource.boundaryYearRepresented, '2017');
assert.equal(adminSource.boundaryCanonical, 'Unknown');
assert.equal(adminSource.boundaryLicense, sourceProduct.recorded_license);
const lineage = json(dataPath('lineage.json.gz'));
const lineageRows = ids.map(i => {
  const f = featureByIndex.get(i), loc = lineage.locations.find(r => r.index === expectedOwners.get(i));
  assert.ok(loc && loc.id === f.source_id && loc.name === f.name && loc.source_atoms.includes(f.source_id));
  return {source_index: i, owner_id: loc.index, source_id: loc.id, name: loc.name,
    province_id: loc.province_id, bounds: loc.bounds};
});
const joinedInputs = Object.keys(pins).map(name => input(name).row);
const observationRow = {path: OBSERVATION, commit: DATA_COMMIT, bytes: observationBytes.length, sha256: sha256(observationBytes)};
const scriptBlob = git('rev-parse', `HEAD:${SCRIPT}`);
assert.equal(git('hash-object', '--no-filters', path.join(ROOT, SCRIPT)), scriptBlob, 'Join driver must be committed before result generation');
const out = path.join(ROOT, OUT);
assert.equal(fs.existsSync(out), false, 'Refusing to overwrite proposal output');
const result = {
  version: 1,
  kind: 'mdv-original-package-evidence-disposition-proposal-v1',
  status: 'proposed-unaccepted',
  package: {id: 'gb-MDV-ADM1--repair-evaluation', queue_commit: DATA_COMMIT,
    frozen_queue_source_commit: queue.current_commit,
    original_cells: 850, original_intervals: 228, land_cells: 850, inland_water_cells: 0,
    owners: [27463,27464,27465,27472,27476,27478], source_family_index: 207,
    native_blocks: [30,31,32], source_feature_indices: ids},
  generation: {code_commit: git('rev-parse','HEAD'), code_path: SCRIPT, code_blob_oid: scriptBlob,
    code_sha256: sha256(fs.readFileSync(path.join(ROOT,SCRIPT))), runtime: process.version,
    command: 'node reconcile-mdv-evidence.mjs', purpose: 'join retained original package, source-candidate, physical, water, lineage and stock observation rows; no geometry run'},
  source_identity: {retained_source_key: 'gb:MDV:ADM1', represented_year_claim: sourceProduct.source_represented_year_claim,
    recorded_feature_count: sourceProduct.feature_count, original_geometry_payload_sha256: sourceProduct.original_sha256,
    original_geometry_payload_bytes: sourceProduct.original_bytes, compressed_payload_sha256: sourceProduct.parts[0].sha256,
    compressed_payload_bytes: sourceProduct.parts[0].bytes, recorded_url: sourceProduct.recorded_consumed_url,
    recorded_source: adminSource.boundarySource, recorded_canonical: adminSource.boundaryCanonical,
    recorded_license: sourceProduct.recorded_license, rights_compliance_assessment: 'not performed',
    package_feature_rows: featureRows, lineage_identity_rows: lineageRows,
    per_feature_contact_key_counts: featureCounts},
  observation: {path: OBSERVATION, bytes: observationRow.bytes, sha256: observationRow.sha256,
    data_commit: DATA_COMMIT, code_commit: observation.code_commit, full_package_keys: observation.query_count,
    base_nonzero_keys: observation.keys.filter(k => k.base_owner !== 0).length,
    additive_nonzero_keys: observation.keys.filter(k => k.accepted_additive_owner !== 0).length,
    effective_nonzero_keys: observation.keys.filter(k => k.effective_selected_owner !== 0).length,
    overlap_keys: observation.keys.filter(k => k.existing_product_overlap).length,
    historical_accepted_exact_key_overlap: 'not determined by this observation'},
  joins: {interval_count: intervalRows.length, key_count: width, unique_key_count: observedByKey.size,
    candidate_contact_key_count: 850, all_candidate_contacts_match_queue_feature_and_owner: true,
    physical_support_key_count: physicalCoverage.size, queue_land_key_count: 850, water_support_key_count: 0,
    unknown_envelope_key_count: 0, unknown_residual_key_count: 0,
    target_key_candidate_features: featureRows.map(f=>f.source_index),
    candidate_features_outside_package_set: 0,
    per_owner_cell_and_interval_counts: Object.fromEntries([...ownerCoverage].sort((a,b)=>a[0]-b[0]).map(([owner,c])=>[String(owner),c])),
    foreign_competitor_completeness: 'not established; the retained candidate blocks show the contacts listed per key but do not prove a complete set of current alternative sources'},
  input_pins: joinedInputs,
  intervals: intervalRows,
  limits: [
    'All interval outcomes are proposed and unaccepted. This packet adds zero repair, exception, or historical accepted-key credit.',
    'The selected-owner observation is a literal current selected-product result for the exact data/code commit; it does not qualify source applicability or establish historical accepted-key credit.',
    'The retained feature roster, source-candidate blocks, lineage, physical support, inland-water support, and empty physical unknown-envelope/residual blocks are the tested evidence scope. No separate current territorial-exclusion or complete competitor inventory was demonstrated for this package.',
    'The retained source catalogue records a 2017 source-year claim and ODbL 1.0 metadata. This does not establish current boundary applicability, authority, legal status, sovereignty, rights compliance, or complete competitor coverage.',
    'Physical support is an archived raster support classification at the exact keys; it is not a current legal land/water boundary finding.',
    'Issue #131 remains a separate 50-location source/semantic review and is not evidence of repair or qualification for these native keys.'
  ]
};
fs.writeFileSync(out, JSON.stringify(result, null, 2) + '\n', {flag: 'wx'});
process.stdout.write(JSON.stringify({output: OUT, intervals: intervalRows.length, keys: width,
  sourceFeatures: featureCounts, baseNonzero: result.observation.base_nonzero_keys,
  additiveNonzero: result.observation.additive_nonzero_keys, effectiveNonzero: result.observation.effective_nonzero_keys,
  water: result.joins.water_support_key_count}) + '\n');

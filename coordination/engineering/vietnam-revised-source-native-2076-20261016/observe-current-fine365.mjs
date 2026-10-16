import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';

const BASE = 'cd68e89523901acf477d0365470410b8b970bb48';
const PREFIX = 'coordination/engineering/vietnam-revised-source-native-2076-20261016/';
const sha = body => createHash('sha256').update(body).digest('hex');
const require = (condition, message) => { if (!condition) throw Error(message); };
const key = record => `${record.owner}:${record.y}:${record.x}`;

function git(...args) {
  return execFileSync('git', ['--no-lazy-fetch', '--no-replace-objects', ...args], {
    maxBuffer: 16 * 1024 ** 2, timeout: 15000,
    env: {...process.env, GIT_NO_LAZY_FETCH: '1', GIT_NO_REPLACE_OBJECTS: '1'},
  });
}

function treeDescriptor(commit, name) {
  require(/^[a-f0-9]{40}$/.test(commit) && /^[a-zA-Z0-9_./-]+$/.test(name)
    && !name.split('/').includes('..'), 'Unsafe immutable locator');
  const raw = git('ls-tree', '-lz', commit, '--', name).toString();
  const match = /^(100644|100755) blob ([a-f0-9]{40})\s+(\d+)\t([^\0]+)\0$/.exec(raw);
  require(match && match[4] === name, 'Missing ordinary exact-tree body: ' + name);
  const bytes = Number(match[3]);
  require(Number.isSafeInteger(bytes) && bytes >= 0 && bytes < 16 * 1024 ** 2, 'Unplanned body size');
  return {commit, path: name, mode: match[1], git_blob_oid: match[2], bytes};
}

function readDescriptor(descriptor, expectedSha) {
  const actual = treeDescriptor(descriptor.commit, descriptor.path);
  for (const field of ['mode', 'git_blob_oid', 'bytes']) require(actual[field] === descriptor[field], 'Tree descriptor mismatch');
  const body = git('cat-file', 'blob', descriptor.git_blob_oid);
  require(body.length === descriptor.bytes, 'Whole body length mismatch');
  const gitOid = createHash('sha1').update(`blob ${body.length}\0`).update(body).digest('hex');
  require(gitOid === descriptor.git_blob_oid, 'Whole Git body identity mismatch');
  const hash = sha(body);
  if (expectedSha) require(hash === expectedSha, 'Whole body SHA256 mismatch: ' + descriptor.path);
  return {body, pin: {...descriptor, sha256: hash}};
}

function readPinned(commit, name, expectedSha) {
  return readDescriptor(treeDescriptor(commit, name), expectedSha);
}

// Exact binary64/rational conversion. Bounds cannot discard a native centre on
// an endpoint merely because its displayed longitude rounded to the other side.
function fraction(value) {
  require(Number.isFinite(value), 'Nonfinite bound');
  if (value === 0) return [0n, 1n];
  const view = new DataView(new ArrayBuffer(8)); view.setFloat64(0, value, false);
  const word = view.getBigUint64(0, false), power = Number((word >> 52n) & 2047n);
  let numerator = (word & ((1n << 52n) - 1n)) + (power ? 1n << 52n : 0n);
  const exponent = power ? power - 1075 : -1074;
  if (word >> 63n) numerator = -numerator;
  return exponent >= 0 ? [numerator << BigInt(exponent), 1n] : [numerator, 1n << BigInt(-exponent)];
}
const floor = (n, d) => n / d - (n % d < 0n ? 1n : 0n);
const ceil = (n, d) => n / d + (n % d > 0n ? 1n : 0n);
export function inclusiveColumnBounds(minimum, maximum, size) {
  require(Number.isSafeInteger(size) && size >= 2 && minimum <= maximum, 'Invalid bound/grid');
  const convert = longitude => {
    const [n, d] = fraction(longitude), width = BigInt(size);
    return [width * n + (180n * width - 180n) * d, 360n * d];
  };
  const [ln, ld] = convert(minimum), [rn, rd] = convert(maximum);
  return [Math.max(0, Number(ceil(ln, ld))), Math.min(size - 1, Number(floor(rn, rd)))];
}

export function geometryBounds(geometry) {
  require(geometry && ['Polygon', 'MultiPolygon'].includes(geometry.type), 'Unsupported current geometry');
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  require(Array.isArray(polygons) && polygons.length > 0, 'Missing polygons');
  let west = Infinity, south = Infinity, east = -Infinity, north = -Infinity, vertices = 0;
  for (const polygon of polygons) {
    require(Array.isArray(polygon) && polygon.length > 0, 'Missing rings');
    for (const ring of polygon) {
      require(Array.isArray(ring) && ring.length >= 4, 'Missing ring vertices');
      for (const point of ring) {
        require(Array.isArray(point) && point.length === 2 && point.every(Number.isFinite)
          && Math.abs(point[0]) <= 180 && Math.abs(point[1]) <= 90, 'Invalid current longitude/latitude');
        west = Math.min(west, point[0]); east = Math.max(east, point[0]);
        south = Math.min(south, point[1]); north = Math.max(north, point[1]); vertices++;
      }
      require(ring[0][0] === ring.at(-1)[0] && ring[0][1] === ring.at(-1)[1], 'Unclosed current ring');
    }
  }
  // A seam-spanning ring only widens these bounds; no antimeridian shortcut is
  // used. Exact stock predicates decide all surviving candidate contacts.
  return {bounds: [west, south, east, north], vertices};
}

export async function observe(codeCommit, outputPath) {
  const started = performance.now(), inputs = [];
  const load = (commit, name, expected) => {
    const result = readPinned(commit, name, expected); inputs.push(result.pin); return result.body;
  };
  const planBytes = load(codeCommit, PREFIX + 'current-fine-input-plan.json');
  const plan = JSON.parse(planBytes);
  require(plan.commit === BASE && plan.parts.length === 37, 'Wrong complete current tree plan');
  const indexRow = plan.parts[0]; require(indexRow.path === 'data/world-index.json', 'Wrong index');
  const indexRead = readDescriptor(indexRow); inputs.push(indexRead.pin);
  const index = JSON.parse(indexRead.body);
  const paths = ['data/world-index.json', ...index.parts.map(name => 'data/' + name)];
  require(index.parts.length === 36 && new Set(paths).size === 37
    && JSON.stringify(paths) === JSON.stringify(plan.parts.map(row => row.path))
    && plan.parts.every(row => row.commit === BASE), 'Incomplete/changed world-index closure');
  const sourceChoice = JSON.parse(load(codeCommit, PREFIX + 'distinct-source-assessment/source-choice348-supported17-blocked.json',
    '15f0a3368358a6696888cd82a4402c4f97a47683274482a66074ddd723c838f2'));
  const records = sourceChoice.records.map(record => ({original_key: record.original_key,
    proposed_source_id: record.new_source_identity, target_id: record.target_id,
    target_owner: record.target_owner, supported_display_source_choice: record.proposed_CHN_display_choice_supported,
    retained_original_contacts: record.retained_original_contacts,
    country_hits: record.country_hits, current_fine_contacts: [], current_fine_boundary_ties: []}));
  require(records.length === 365 && new Set(records.map(row => key(row.original_key))).size === 365
    && records.filter(row => row.supported_display_source_choice).length === 348, 'Original365 /348/17 scope mismatch');
  const latitudeBytes = load(BASE,
    'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz',
    'ab0becdda100da3473d7bb5d34ccda6510aa1c0490c407082072c7201ad1e147');
  const latitudeRaw = gunzipSync(latitudeBytes, {maxOutputLength: 2097328});
  require(latitudeRaw.length === 2097328 && sha(latitudeRaw) === '66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23', 'Wrong normative latitudes');
  const size = 262166, latitudes = Float64Array.from({length: size}, (_, y) => latitudeRaw.readDoubleLE(y * 8));
  const ownersBytes = load('7e423077552651d6ec1d6bf6b879c34e956f985a',
    'coordination/engineering/melanesia363-additive-delivery-20261010/release-next-eighteen/owners.json.gz',
    'b33f44b882b4a0c9b89c79fb079b766505a18f2ba0089fe2945ac9b5120fb78f');
  const ownersRaw = gunzipSync(ownersBytes, {maxOutputLength: 11096191});
  require(ownersRaw.length === 11096191 && sha(ownersRaw) === 'a8086008b7a072dd86483720a2a166785229753422769dbbe0749497d870f428', 'Wrong stable owner roster');
  const roster = JSON.parse(ownersRaw), byId = new Map(roster.map(row => [row.id, row]));
  require(roster.length === 49625 && byId.size === roster.length, 'Incomplete stable owner roster');
  const nativeCode = load(BASE, 'src/native-grid.js', '3ef6bc5ec66e3184c254ea66404add0824e3ee18e39c8658f234d2e236d840ad');
  require(!/\bimport\s/.test(nativeCode.toString()), 'Unexpected unbound native import');
  const {nativeRuntimeIndex, nativePolygonIntervals} = await import('data:text/javascript;base64,' + nativeCode.toString('base64'));
  const rowStart = Math.min(...records.map(row => row.original_key.y));
  const rowEnd = Math.max(...records.map(row => row.original_key.y)) + 1;
  const ids = new Set(), partInventory = [], potentialFeatures = [], inventoryHash = createHash('sha256');
  let featureCount = 0, totalVertices = 0, boundedExclusions = 0;
  for (const descriptor of plan.parts.slice(1)) {
    const read = readDescriptor(descriptor); inputs.push(read.pin);
    const collection = JSON.parse(read.body);
    require(collection.type === 'FeatureCollection' && Array.isArray(collection.features), 'Wrong current geography part');
    let possible = 0, excluded = 0;
    for (const feature of collection.features) {
      require(feature.type === 'Feature' && typeof feature.id === 'string' && feature.id
        && feature.properties?.id === feature.id && !ids.has(feature.id), 'Missing/duplicate current stable identity');
      ids.add(feature.id); featureCount++;
      const {bounds, vertices} = geometryBounds(feature.geometry); totalVertices += vertices;
      const [first, last] = inclusiveColumnBounds(bounds[0], bounds[2], size);
      const potential = records.filter(({original_key: point}) => point.x >= first && point.x <= last
        && latitudes[point.y] >= bounds[1] && latitudes[point.y] <= bounds[3]);
      inventoryHash.update(JSON.stringify([descriptor.path, feature.id, bounds, vertices]) + '\n');
      if (!potential.length) { excluded++; boundedExclusions++; continue; }
      possible++;
      const scan = nativePolygonIntervals(nativeRuntimeIndex([{id: feature.id, pixelIndex: 1, geometry: feature.geometry}]),
        {size, latitudes, rowStart, rowEnd});
      let contacts = 0, boundaryKeys = 0;
      for (const record of potential) {
        const {y, x} = record.original_key;
        const ties = scan.ties.filter(tie => tie.y === y && (tie.start ?? tie.x) <= x && x < (tie.end ?? tie.x + 1));
        const interior = (scan.rows.get(y) ?? []).some(run => run.start <= x && x < run.end) && !ties.length;
        const reference = {id: feature.id, stable_owner: byId.get(feature.id)?.index ?? null,
          reference_owner: feature.properties.reference_owner ?? null,
          parent_id: feature.properties.parent_id ?? null,
          source_id: feature.properties.metadata?.source_id ?? null,
          current_part: descriptor.path, geometry_sha256: sha(JSON.stringify(feature.geometry))};
        if (interior) { record.current_fine_contacts.push(reference); contacts++; }
        if (ties.length) {
          record.current_fine_boundary_ties.push({...reference, ties}); boundaryKeys++;
        }
      }
      potentialFeatures.push({id: feature.id, stable_owner: byId.get(feature.id)?.index ?? null,
        part: descriptor.path, geometry_sha256: sha(JSON.stringify(feature.geometry)), bounds, vertices,
        bounded_candidate_keys: potential.length, actual_interior_keys: contacts, boundary_keys: boundaryKeys});
    }
    partInventory.push({path: descriptor.path, features: collection.features.length,
      exact_bounds_excluded_features: excluded, stock_scanned_features: possible});
  }
  require(featureCount === 49625 && ids.size === roster.length && roster.every(row => ids.has(row.id)), 'Current complete feature/owner roster mismatch');
  const result = {kind: 'bounded-complete-current-fine-geography-exact-native365-observation-v1',
    code_commit: codeCommit, geography_commit: BASE, input_pins: inputs,
    source_choice_scope_sha256: '15f0a3368358a6696888cd82a4402c4f97a47683274482a66074ddd723c838f2',
    feature_inventory: {index_parts: 36, features: featureCount, validated_vertices: totalVertices,
      exact_bounds_excluded_features: boundedExclusions, stock_scanned_features: potentialFeatures.length,
      traversal_sha256: inventoryHash.digest('hex'), parts: partInventory},
    native_rule: {size, rowStart, rowEnd, latitude_sha256: sha(latitudeRaw), method: 'native-linear-evenodd-first-owner-v1'},
    original_keys: records.length, supported_display_source_choices: 348, blocked_proposed_CHN_keys: 17,
    keys_with_current_fine_interior_contacts: records.filter(row => row.current_fine_contacts.length).length,
    keys_with_current_fine_boundary_ties: records.filter(row => row.current_fine_boundary_ties.length).length,
    potential_features: potentialFeatures, records, elapsed_seconds: (performance.now() - started) / 1000,
    limitations: ['This is a complete current canonical fine-geography contact/tie proof, not a replay of the original 368-product source bank.',
      'The existing independent country-reference and VNM raw shared-interior observations are reused and all original contrary contacts remain recorded.',
      'Source-choice adoption covers exactly348 original keys;17 Chinese proposals remain blocked.',
      'No current native ownership, source/physical/native qualification, conservation, selected-map delivery or accepted credit is established by this observation.']};
  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2) + '\n', {flag: 'wx'});
  console.log(JSON.stringify({features: featureCount, scanned: potentialFeatures.length,
    interior_keys: result.keys_with_current_fine_interior_contacts, boundary_keys: result.keys_with_current_fine_boundary_ties,
    elapsed_seconds: result.elapsed_seconds, output_bytes: fs.statSync(outputPath).size, rss_bytes: process.memoryUsage().rss}));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  require(process.argv.length === 4 && /^[a-f0-9]{40}$/.test(process.argv[2]), 'Usage: node observe-current-fine365.mjs EXACT_CODE_COMMIT NEW_OUTPUT');
  await observe(process.argv[2], process.argv[3]);
}

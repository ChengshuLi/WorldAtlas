/* Scope adapter for the unchanged accepted whole-original bounds method.
 * Usage: NODE24 THIS_FILE REPO IMMUTABLE_INPUT_CONFIG FRESH_OUTPUT
 * No GIS/normalization/native producer runs. Full originals remain immutable.
 */
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL, fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';

const need = (value, message) => { if (!value) throw Error(message); };
const sha = body => createHash('sha256').update(body).digest('hex');
const bytes = value => Buffer.from(JSON.stringify(value) + '\n');
const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);
const hex = (value, length) => typeof value === 'string' && new RegExp(`^[a-f0-9]{${length}}$`).test(value);
const safe = name => typeof name === 'string' && /^[A-Za-z0-9_./-]+$/.test(name)
  && !path.isAbsolute(name) && name.split('/').every(p => p && p !== '.' && p !== '..');
const ordinary = name => {
  for (let current = path.resolve(name);; current = path.dirname(current)) {
    need(!fs.lstatSync(current, {throwIfNoEntry: false})?.isSymbolicLink(), 'Symlink path: ' + current);
    if (current === path.dirname(current)) break;
  }
};
// Exactly the inclusive conservative rectangle predicate in the retained scanner.
const intersection = (a, b) => a[0] <= b[2] && b[0] <= a[2] && a[1] <= b[3] && b[1] <= a[3];
const EXPECTED_ISOS = ['MEX', 'ECU', 'BOL', 'PER', 'COL'];
const FIJI_IDS = ['gb:FJI:ADM1:53030831B91072554514863',
  'gb:FJI:ADM2:14151628B95966095088914', 'gb:FJI:ADM2:14151628B42533076410957'];
const HELPER = 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const [repoArgument, configArgument, outputArgument] = process.argv.slice(2);
need(process.argv.length === 5, 'Usage: NODE24 DRIVER REPO CONFIG FRESH_OUTPUT');
const repo = path.resolve(repoArgument), output = path.resolve(outputArgument);
ordinary(repo); ordinary(configArgument); ordinary(output);
need(fs.statSync(repo).isDirectory() && fs.statSync(configArgument).isFile(), 'Repository/config required');
need(!fs.lstatSync(output, {throwIfNoEntry: false}) && fs.statSync(path.dirname(output)).isDirectory(), 'Fresh ordinary output required');
const configRaw = fs.readFileSync(configArgument), config = JSON.parse(configRaw);
need(config.version === 1 && config.kind === 'five-country-whole-original-bounds-adapter-v1'
  && hex(config.method_commit, 40) && same(config.countries.map(c => c.iso), EXPECTED_ISOS), 'Exact five-country adapter contract required');
need(same(config.expected, {catalogue_families: 368, source_features: 73567, targets: 389}), 'Exact intended complete scope required');
const environment = {...process.env, GIT_NO_LAZY_FETCH: '1', GIT_NO_REPLACE_OBJECTS: '1',
  GIT_OPTIONAL_LOCKS: '0', GIT_TERMINAL_PROMPT: '0', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null'};
const git = (...args) => execFileSync('git', ['-c', 'protocol.allow=never', '-C', repo, ...args],
  {env: environment, maxBuffer: 64 * 1024 * 1024});
const consumed = new Map(), admitted = new Map();
function admit(pin) {
  need(pin && hex(pin.commit, 40) && safe(pin.path) && pin.mode === '100644'
    && hex(pin.git_blob_oid, 40) && Number.isSafeInteger(pin.bytes) && pin.bytes > 0 && hex(pin.sha256, 64), 'Ordinary immutable input pin required');
  const key = pin.commit + ':' + pin.path;
  if (admitted.has(key)) { need(same(admitted.get(key), pin), 'Conflicting admitted pin'); return; }
  need(git('cat-file', '-t', pin.commit).toString().trim() === 'commit', 'Actual immutable commit required');
  const tree = git('ls-tree', '-z', pin.commit, '--', pin.path).toString();
  need(tree === `100644 blob ${pin.git_blob_oid}\t${pin.path}\0`, 'Exact ordinary input tree differs: ' + pin.path);
  need(Number(git('cat-file', '-s', pin.git_blob_oid).toString()) === pin.bytes, 'Input size differs');
  admitted.set(key, pin);
}
function read(pin) {
  admit(pin);
  const body = git('cat-file', 'blob', pin.git_blob_oid);
  need(body.length === pin.bytes && sha(body) === pin.sha256, 'Whole input body differs: ' + pin.path);
  need(createHash('sha1').update(Buffer.concat([Buffer.from(`blob ${body.length}\0`), body])).digest('hex') === pin.git_blob_oid,
    'Whole Git object differs');
  const key = pin.commit + ':' + pin.path;
  need(!consumed.has(key) || same(consumed.get(key), pin), 'Conflicting pin for same input');
  consumed.set(key, pin); return body;
}
function decoded(pin) {
  const raw = read(pin);
  if (!pin.path.endsWith('.gz')) return raw;
  need(Number.isSafeInteger(pin.decoded_bytes) && pin.decoded_bytes > 0 && hex(pin.decoded_sha256, 64), 'Complete decoded pin required');
  const body = gunzipSync(raw, {maxOutputLength: pin.decoded_bytes + 1});
  need(body.length === pin.decoded_bytes && sha(body) === pin.decoded_sha256, 'Decoded input differs'); return body;
}
const json = pin => JSON.parse(decoded(pin));
function mapUnique(rows, key, label) {
  need(Array.isArray(rows) && rows.length, 'Nonempty ' + label + ' required');
  const result = new Map();
  for (const row of rows) { need(!result.has(row[key]), 'Duplicate ' + label); result.set(row[key], row); }
  return result;
}

// Authenticate the complete ordinary static import closure before importing it.
const closure = mapUnique(config.code_closure, 'path', 'code closure');
const visited = new Set();
function verifyCode(name) {
  if (visited.has(name)) return;
  const pin = closure.get(name);
  need(pin && pin.commit === config.method_commit, 'Missing accepted code import: ' + name);
  const body = read(pin), local = path.join(repo, name); ordinary(local);
  need(fs.statSync(local).isFile() && fs.readFileSync(local).equals(body), 'Materialized accepted code differs: ' + name);
  visited.add(name);
  for (const match of body.toString().matchAll(/(?:from\s+|import\(\s*)['"]([.][^'"]+)['"]/g)) {
    const imported = path.posix.normalize(path.posix.join(path.posix.dirname(name), match[1]));
    if (/\.(mjs|js|cjs)$/.test(imported)) verifyCode(imported);
  }
}
verifyCode(HELPER);
need(visited.size === closure.size, 'Unused or missing accepted code closure record');
const {coordinateBounds} = await import(pathToFileURL(path.join(repo, HELPER)));
need(typeof coordinateBounds === 'function', 'Accepted coordinateBounds export required');
const started = performance.now();
const catalogueRaw = read(config.inputs.catalogue), catalogue = JSON.parse(catalogueRaw);
const products = mapUnique(catalogue.products, 'key', 'catalogue families');
const roster = json(config.inputs.roster), bySource = mapUnique(roster, 'source_id', 'global source roster');
const byIndex = mapUnique(roster, 'source_index', 'source indexes');
need(catalogue.version === 1 && products.size === 368 && bySource.size === 73567 && byIndex.size === 73567, 'Complete original catalogue/roster required');
const seams = json(config.inputs.seams), seamMap = mapUnique(seams, 'source_id', 'retained seam records');
const periodicReview = json(config.inputs.periodic_review), reviewMap = mapUnique(periodicReview.features, 'source_id', 'periodic review');
read(config.inputs.periodic_review_method); read(config.inputs.periodic_documentation);
need(same([...seamMap.keys()].sort(), [...FIJI_IDS].sort()) && same([...reviewMap.keys()].sort(), [...FIJI_IDS].sort()), 'Exact retained three Fiji exceptions required');
const nativeSelection = json(config.inputs.native_selection), nativeManifest = json(config.inputs.native_manifest);
need(config.inputs.native_manifest.commit === config.inputs.native_selection.commit
  && config.inputs.native_manifest.path === nativeSelection.manifest_path
  && config.inputs.native_manifest.sha256 === nativeSelection.sha256
  && Number.isSafeInteger(nativeManifest.size) && nativeManifest.size === 262166
  && nativeManifest.method === nativeSelection.method, 'Authenticated normative native size/selection required');
const nativeSize = nativeManifest.size;

const stageCache = new Map(), allStageIds = new Set(), allTargets = new Map();
const membershipCache = new Map();
// Exact normative cell-centre longitude in authenticated src/native-grid.js:
// (360*x + 180 - 180*size) / size. No endpoint-frame substitution.
const denominator = BigInt(nativeSize);
const floorDiv = (n, d) => n >= 0n ? n / d : -((-n + d - 1n) / d);
const ceilDiv = (n, d) => -floorDiv(-n, d);
const countries = config.countries.map(country => {
  need(country.positive_family === `gb:${country.iso}:ADM2` && products.has(country.positive_family), 'Exact positive family required');
  const sk = country.stage.commit + ':' + country.stage.path;
  if (!stageCache.has(sk)) {
    const stages = json(country.stage), stageMap = mapUnique(stages, 'target', 'whole stages');
    for (const id of stageMap.keys()) allStageIds.add(id);
    stageCache.set(sk, stageMap);
  }
  const mk = country.membership.commit + ':' + country.membership.path;
  if (!membershipCache.has(mk)) membershipCache.set(mk, mapUnique(json(country.membership), 'source_id', 'whole membership'));
  const stages = stageCache.get(sk), membership = membershipCache.get(mk), pkg = json(country.package);
  need(pkg.package_id === `gb-${country.iso}-ADM2--repair-evaluation` && Array.isArray(country.target_ids)
    && country.target_ids.length === pkg.owners.length && new Set(country.target_ids).size === country.target_ids.length, 'Exact original target scope required');
  const targetOwners = new Set(), targets = country.target_ids.map(id => {
    const stage = stages.get(id), member = membership.get(id), source = bySource.get(id);
    need(id.startsWith(country.positive_family + ':') && stage && member && source && !allTargets.has(id), 'Unique exact country source target required');
    need(member.source_id === id && member.target_id === id && Number.isSafeInteger(member.pixelIndex)
      && source.owners.length === 1 && source.owners[0] === member.pixelIndex
      && source.source_index === member.source_index && source.ordinal === member.source_ordinal
      && stage.selected?.id === id && stage.consumed?.properties?.shapeID === id.slice(country.positive_family.length + 1), 'Original target/member/source join differs');
    const target = {source_id: id, pixelIndex: member.pixelIndex, source_index: source.source_index,
      country_iso: country.iso, bounds: coordinateBounds(stage.consumed.geometry), stage_geometry: stage.consumed.geometry};
    need(!targetOwners.has(member.pixelIndex), 'Duplicate country target owner'); targetOwners.add(member.pixelIndex);
    allTargets.set(id, target); return target;
  });
  need(same([...targetOwners].sort((a,b)=>a-b), [...pkg.owners].sort((a,b)=>a-b)), 'Original package owner scope differs');
  need(country.intervals.length === pkg.native_blocks.length, 'Complete original native block pins required');
  let cells = 0, intervals = 0, minColumn = Infinity, maxColumn = -Infinity;
  const physical = {land: 0, 'inland-water': 0}, sourceIndexes = new Set(), owners = new Set();
  for (const [ordinal, pin] of country.intervals.entries()) {
    need(pin.path.endsWith(`/block-${String(pkg.native_blocks[ordinal]).padStart(3, '0')}.json.gz`), 'Original block order differs');
    for (const row of json(pin)) {
      const [y, start, end, oi, si, kind] = row;
      need(Number.isSafeInteger(y) && y >= 0 && y < nativeSize && Number.isSafeInteger(start)
        && Number.isSafeInteger(end) && start >= 0 && end <= nativeSize && end > start
        && Object.hasOwn(physical, kind) && Array.isArray(oi) && Array.isArray(si), 'Original exact native interval required');
      cells += end - start; physical[kind] += end - start; intervals++;
      minColumn = Math.min(minColumn, start); maxColumn = Math.max(maxColumn, end - 1);
      for (const value of oi) owners.add(value); for (const value of si) sourceIndexes.add(value);
    }
  }
  need(cells === pkg.native_cells && intervals === pkg.interval_segments
    && physical.land === pkg.land_cells && physical['inland-water'] === pkg.inland_water_cells
    && same([...owners].sort((a,b)=>a-b), [...pkg.owners].sort((a,b)=>a-b))
    && same([...sourceIndexes].sort((a,b)=>a-b), [...pkg.source_features].sort((a,b)=>a-b)), 'Complete original interval scope differs');
  const westNumerator = 360n * BigInt(minColumn) + 180n - 180n * denominator;
  const eastNumerator = 360n * BigInt(maxColumn) + 180n - 180n * denominator;
  return {iso: country.iso, positive_family: country.positive_family,
    parent_context_families: [`gb:${country.iso}:ADM1`], targets,
    original_scope: {package_id: pkg.package_id, cells, intervals, physical_classes: physical,
      min_column: minColumn, max_inclusive_column: maxColumn,
      longitude_enclosure: [Number(floorDiv(westNumerator, denominator)), Number(ceilDiv(eastNumerator, denominator))],
      exact_longitude_numerators: [String(westNumerator), String(eastNumerator)], longitude_denominator: String(denominator),
      native_size: nativeSize, longitude_formula: '(360*x + 180 - 180*size) / size',
      native_manifest: config.inputs.native_manifest, normative_code: closure.get('src/native-grid.js')},
    feature_counts: {domestic: 0, foreign: 0, foreign_raw_disjoint: 0, foreign_raw_candidates: 0,
      foreign_periodic_disjoint: 0, foreign_unresolved: 0}, candidate_families: new Set(), unresolved_families: new Set(),
    contextual_contact_families: new Set([...sourceIndexes].map(i => byIndex.get(i)?.source_id.split(':').slice(0,3).join(':')))};
});
need(allTargets.size === 389 && allStageIds.size === 389 && [...allStageIds].every(id => allTargets.has(id)), 'Complete five-country 389 stage union required');

// Admit every original transport descriptor before creating any destination.
// Whole encoded/decoded byte authentication remains at the actual read below.
const sourcePartMap = mapUnique(config.source_parts, 'path', 'source part pins');
let admittedParts = 0;
for (const record of catalogue.products) {
  let offset = 0;
  for (const [ordinal, part] of record.parts.entries()) {
    const pin = sourcePartMap.get(part.path);
    need(part.ordinal === ordinal && part.offset === offset && pin
      && pin.commit === config.inputs.catalogue.commit && pin.bytes === part.bytes && pin.sha256 === part.sha256
      && pin.decoded_bytes === part.uncompressed_bytes && pin.decoded_sha256 === part.uncompressed_sha256,
    'Complete original transport admission differs');
    admit(pin); offset += part.uncompressed_bytes; admittedParts++;
  }
  need(offset === record.original_bytes, 'Complete original body admission differs');
}
need(admittedParts === 370 && sourcePartMap.size === admittedParts, 'Complete exact original transport inventory required');

// Only bounded, sequential provenance shards are retained; raw originals stay in
// their immutable whole-body/contiguous transport pins, never reserialized.
fs.mkdirSync(output);
const emitted = [], MAX_SHARD = 8 * 1024 * 1024;
let shard = null, shardOrdinal = 0;
function finishShard() {
  if (!shard) return;
  fs.closeSync(shard.fd); emitted.push({path: shard.name, bytes: shard.length, sha256: shard.hash.digest('hex'), records: shard.records}); shard = null;
}
function emit(record) {
  const body = bytes(record); need(body.length <= MAX_SHARD, 'One bounds record exceeds ordinary shard allowance');
  if (!shard || shard.length + body.length > MAX_SHARD) {
    finishShard(); const name = `whole-source-bounds-${String(shardOrdinal++).padStart(3, '0')}.jsonl`;
    shard = {name, fd: fs.openSync(path.join(output, name), 'wx'), hash: createHash('sha256'), length: 0, records: 0};
  }
  fs.writeFileSync(shard.fd, body); shard.hash.update(body); shard.length += body.length; shard.records++;
}
function write(name, value, raw = false) {
  const body = raw ? value : bytes(value); need(body.length <= 32 * 1024 * 1024, 'Ordinary metadata output too large');
  fs.writeFileSync(path.join(output, name), body, {flag: 'wx'});
  emitted.push({path: name, bytes: body.length, sha256: sha(body)});
}
const allSeen = new Set(), periodicOutcomes = [], familyInventories = [];
let encodedSourceBytes = 0, decodedSourceBytes = 0;
for (const record of catalogue.products) {
  let offset = 0; const partPins = [], pieces = [];
  for (const [ordinal, part] of record.parts.entries()) {
    need(part.ordinal === ordinal && part.offset === offset, 'Complete contiguous original parts required');
    const pin = sourcePartMap.get(part.path);
    need(pin && pin.commit === config.inputs.catalogue.commit && pin.bytes === part.bytes && pin.sha256 === part.sha256
      && pin.decoded_bytes === part.uncompressed_bytes && pin.decoded_sha256 === part.uncompressed_sha256, 'Original catalogue part pin differs');
    const body = decoded(pin); pieces.push(body); partPins.push(pin); offset += body.length;
    encodedSourceBytes += pin.bytes; decodedSourceBytes += body.length;
  }
  const raw = Buffer.concat(pieces);
  need(raw.length === record.original_bytes && sha(raw) === record.original_sha256, 'Complete original product differs');
  const product = JSON.parse(raw), familySeen = new Set();
  need(product.type === 'FeatureCollection' && product.features.length === record.feature_count, 'Complete original feature roster required');
  for (const [ordinal, feature] of product.features.entries()) {
    const id = record.key + ':' + feature.properties?.shapeID, source = bySource.get(id);
    need(source && source.ordinal === ordinal && !familySeen.has(id) && !allSeen.has(id), 'Exact complete original source identity required');
    familySeen.add(id); allSeen.add(id);
    const geometryHash = sha(bytes(feature.geometry)), target = allTargets.get(id);
    if (target) need(same(target.stage_geometry, feature.geometry), 'Whole target original geometry differs from source corpus');
    let bounds = null, rawError = null, frame = 'strict-complete-original-coordinate-bounds';
    try { bounds = coordinateBounds(feature.geometry); } catch (error) { rawError = error.message; }
    let seam = null, proof = null;
    if (rawError && seamMap.has(id)) {
      seam = seamMap.get(id); proof = reviewMap.get(id);
      need(rawError === 'Invalid/nonfinite coordinate' && seam.source_product_sha256 === record.original_sha256
        && seam.source_id === id && seam.ordinal === ordinal && seam.source_index === source.source_index
        && same(seam.owners, source.owners) && same(seam.original_geometry, feature.geometry)
        && seam.normalization === 'retained-majority-canonical-periodic-unwrap-make-valid-v1'
        && seam.original_shapely_valid === true && seam.canonical_shapely_valid === true
        && proof.exact_output_match === true && Number.isSafeInteger(proof.row_start)
        && Number.isSafeInteger(proof.row_end) && proof.row_end > proof.row_start,
      'Exact retained Fiji original and independent native-equality proof required');
      bounds = coordinateBounds(seam.geometry); frame = 'retained-periodic-native-equality-view';
    }
    need(!seamMap.has(id) || (rawError && seam), 'Retained exception changed raw-coordinate behavior');
    const perCountry = [];
    for (const country of countries) {
      const domestic = record.key.startsWith(`gb:${country.iso}:`), role = domestic
        ? (record.key === country.positive_family ? 'positive-complete-source-family' : 'own-country-parent-context') : 'foreign-original';
      country.feature_counts[domestic ? 'domestic' : 'foreign']++;
      const matched = bounds ? country.targets.filter(t => bounds.some(a => t.bounds.some(b => intersection(a,b)))).map(t => t.source_id) : [];
      let status;
      if (!bounds) status = 'unresolved-raw-coordinate-failure';
      else if (!seam) status = matched.length ? 'whole-bounds-candidate' : 'whole-bounds-disjoint';
      else {
        const [west, east] = country.original_scope.longitude_enclosure;
        const keysDisjoint = bounds.every(box => box[2] < west || box[0] > east);
        status = matched.length === 0 && keysDisjoint ? 'retained-periodic-bounds-and-native-key-enclosure-disjoint' : 'unresolved-retained-periodic-contact';
        periodicOutcomes.push({country_iso: country.iso, source_id: id, source_index: source.source_index,
          original_geometry_sha256: geometryHash, retained_canonical_geometry_sha256: sha(bytes(seam.geometry)),
          original_requested_key_longitude_enclosure: [west, east], whole_target_bounds_disjoint: matched.length === 0,
          exact_requested_key_enclosure_disjoint: keysDisjoint, status, retained_independent_full_native_comparison: proof});
      }
      if (!domestic) {
        if (status.startsWith('unresolved')) { country.feature_counts.foreign_unresolved++; country.unresolved_families.add(record.key); }
        else if (seam) country.feature_counts.foreign_periodic_disjoint++;
        else if (matched.length) country.feature_counts.foreign_raw_candidates++;
        else country.feature_counts.foreign_raw_disjoint++;
        if (matched.length || status.startsWith('unresolved')) country.candidate_families.add(record.key);
      }
      perCountry.push({country_iso: country.iso, role, status, target_ids: matched});
    }
    emit({source_family: record.key, source_id: id, source_index: source.source_index, feature_ordinal: ordinal,
      owners: source.owners, original_properties: feature.properties, original_geometry_sha256: geometryHash,
      whole_original_sha256: record.original_sha256, bounds_frame: frame, raw_coordinate_error: rawError,
      complete_part_bounds: bounds, ...(seam ? {retained_canonical_geometry_sha256: sha(bytes(seam.geometry)),
        retained_periodic_evidence: config.inputs.seams, retained_independent_native_equality: config.inputs.periodic_review} : {}),
      country_outcomes: perCountry});
  }
  const expected = roster.filter(row => row.source_id.startsWith(record.key + ':'));
  need(familySeen.size === expected.length && expected.every(row => familySeen.has(row.source_id)), 'Complete source-family identity coverage differs');
  familyInventories.push({...record, authenticated_parts: partPins, complete_observed_features: familySeen.size});
  console.log(JSON.stringify({family: record.key, complete_features: familySeen.size}));
}
finishShard();
need(allSeen.size === 73567 && roster.every(row => allSeen.has(row.source_id)) && familyInventories.length === 368,
  'Complete whole original source universe required');
need(config.source_parts.length === familyInventories.reduce((n,f)=>n+f.parts.length,0)
  && new Set(config.source_parts.map(p=>p.path)).size === config.source_parts.length, 'Unused/duplicate source payload pin');
need(periodicOutcomes.length === 15 && countries.every(c => c.feature_counts.domestic + c.feature_counts.foreign === 73567
  && c.feature_counts.foreign_raw_disjoint + c.feature_counts.foreign_raw_candidates
  + c.feature_counts.foreign_periodic_disjoint + c.feature_counts.foreign_unresolved === c.feature_counts.foreign), 'Complete country/exception conservation required');
write('original-catalogue.json', catalogueRaw, true);
write('whole-family-custody.json', {catalogue: config.inputs.catalogue, families: familyInventories});
write('retained-periodic-outcomes.json', {seams: config.inputs.seams, independent_review: config.inputs.periodic_review,
  rows: periodicOutcomes, limits: ['Exact prior periodic interpretation/native-equality evidence reused; no unwrap, MakeValid or raster rerun.',
    'Raw errors remain explicit; disjointness is specific to complete target bounds and ideal-rational requested-key enclosure.']});
const summaries = countries.map(country => {
  const candidate = [...country.candidate_families].sort(), unresolved = [...country.unresolved_families].sort();
  const domestic = [...products.keys()].filter(f => f.startsWith(`gb:${country.iso}:`));
  need(domestic.length === 2, 'Complete same-country parent/positive scope required');
  return {country_iso: country.iso, positive_family: country.positive_family, parent_context_families: country.parent_context_families,
    complete_foreign_families: products.size - domestic.length, target_count: country.targets.length,
    targets: country.targets.map(({stage_geometry, ...rest})=>rest), original_scope: country.original_scope,
    feature_counts: country.feature_counts, whole_bounds_candidate_families: candidate, unresolved_families: unresolved,
    stock_scope_ready: unresolved.length === 0, stock_territorial_exclusion_families: unresolved.length ? null : candidate,
    original_contact_families: [...country.contextual_contact_families].sort(),
    limits: ['Country source identity is role context, not sovereignty or geographic applicability by itself.',
      'Own parent context is not an automatic negative operand; other positive countries remain foreign here.',
      'Bounds select conservative whole-source operands only; physical/native/source-semantic qualification remains required.']};
});
write('country-foreign-applicability.json', {version: 1, countries: summaries});
const complete = summaries.every(country => country.stock_scope_ready);
write('completion.json', {version: 1, kind: 'complete-five-country-whole-original-bounds-inventory',
  inventory_complete: true, country_applicability_complete: complete, driver_sha256: sha(fs.readFileSync(fileURLToPath(import.meta.url))),
  config_sha256: sha(configRaw), method_commit: config.method_commit, complete_families: 368, complete_source_features: 73567,
  complete_target_members: 389, original_raw_coordinate_exceptions: FIJI_IDS,
  encoded_source_bytes: encodedSourceBytes, decoded_source_bytes: decodedSourceBytes,
  inputs: [...consumed.values()], outputs: emitted, seconds: (performance.now() - started) / 1000,
  process_max_rss_platform_units: process.resourceUsage().maxRSS, platform: process.platform,
  limits: ['Input/bounds preparation only; no physical, native, source approval or accepted credit.',
    'Cumulative encoded/decoded bytes are not peak memory; platform maxRSS is an observation, not an enforced process-tree limit.',
    'Original geometry/properties remain in authenticated complete immutable original bodies; bounds outputs do not replace source bytes.',
    'Current owning state, mixed source rights/vintages and all scientific/semantic gates remain independently applicable.']});
console.log(JSON.stringify({inventory_complete: true, country_applicability_complete: complete,
  complete_features: allSeen.size, countries: summaries.map(c=>({iso:c.country_iso, candidates:c.whole_bounds_candidate_families,
    unresolved:c.unresolved_families})), output}));
if (!complete) process.exitCode = 2;

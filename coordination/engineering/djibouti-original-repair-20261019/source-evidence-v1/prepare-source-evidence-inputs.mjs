/* Prepare factual DJI source-evidence inputs from immutable package and source pins.
 * This adapter preserves the full package denominator and does not qualify applicability.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {fileURLToPath, pathToFileURL} from 'node:url';

const root = process.cwd();
const base = '261e709ac9e1837b3399537f9f53cfa6550e3a01';
const stageCommit = 'f086c1b4dfbaf6e3095785dcae03368090e5415b';
const intervalCommit = 'dd155faf933cc44511d7023930a8aab369897a60';
const physicalCommit = '908b1a5e70f69151173ea823c760009277a25297';
const prefix = 'coordination/engineering/djibouti-original-repair-20261019/';
const evidenceVersion = process.argv[2] ?? 'v1';
const need = (value, message) => { if (!value) throw new Error(message); };
need(['v1', 'v2'].includes(evidenceVersion), 'Use an explicit supported evidence vintage');
const evidenceDir = prefix + `source-evidence-${evidenceVersion}`;
const contextDir = prefix + 'source-context-v1';
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
need(!fs.existsSync(path.join(root, evidenceDir, 'source-evidence-config.json'))
  && !fs.existsSync(path.join(root, evidenceDir, 'native-requested-patch.json')),
  'Fresh DJI source evidence products required');

const {pinReader} = await import(pathToFileURL(path.join(root, 'scripts/prepare-delivery-handoff.mjs')));
const {coordinateBounds} = await import(pathToFileURL(path.join(root,
  'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs')));
const reader = pinReader(root);
const pins = new Map();
function pin(commit, file) {
  const result = reader.pin(commit, file);
  pins.set(`${commit}:${file}`, result);
  return result;
}
function read(commit, file) { const p = pin(commit, file); return reader.read(p); }
function json(commit, file, decoded = false) {
  const raw = read(commit, file);
  return JSON.parse(decoded ? gunzipSync(raw) : raw);
}
function sourceFamily(catalogue, key) {
  const product = catalogue.products.find(record => record.key === key);
  need(product, `Missing exact original family ${key}`);
  const chunks = [], parts = [];
  for (const [ordinal, part] of product.parts.entries()) {
    const encoded = read(base, part.path);
    need(encoded.length === part.bytes && digest(encoded) === part.sha256, `Encoded source part mismatch ${key}`);
    const body = gunzipSync(encoded, {maxOutputLength: part.uncompressed_bytes + 1});
    need(body.length === part.uncompressed_bytes && digest(body) === part.uncompressed_sha256,
      `Decoded source part mismatch ${key}`);
    need(part.ordinal === ordinal && part.offset === chunks.reduce((total, chunk) => total + chunk.length, 0),
      `Source part ordering mismatch ${key}`);
    chunks.push(body);
    parts.push({...pin(base, part.path), decoded_bytes: body.length, decoded_sha256: digest(body)});
  }
  const body = Buffer.concat(chunks);
  need(body.length === product.original_bytes && digest(body) === product.original_sha256,
    `Whole original family mismatch ${key}`);
  const collection = JSON.parse(body);
  need(collection.type === 'FeatureCollection' && collection.features.length === product.feature_count,
    `Incomplete original feature family ${key}`);
  return {product, collection, parts};
}

const stagePath = prefix + 'source-stage-v1/original-stage-inputs.json';
const stageRows = json(stageCommit, stagePath);
const stagePin = pin(stageCommit, stagePath);
const identityPath = prefix + 'source-identity-v1/source-identity-joins.json';
const identity = json(intervalCommit, identityPath);
const ownerByTarget = new Map(identity.targets.map(row => [row.target_location.id, row.target_owner_index]));
need(stageRows.length === 9 && ownerByTarget.size === 9, 'Exact nine-target DJI stage required');

const intervalBase = prefix + 'source-batch-intervals-v1/';
const packageInfo = json(intervalCommit, intervalBase + 'package.json');
need(packageInfo.package_id === 'gb-DJI-ADM2--repair-evaluation'
  && packageInfo.land_cells === 683 && packageInfo.interval_segments === 394
  && packageInfo.source_families.join(',') === '87,88', 'Pinned DJI package denominator differs');
const intervals = ['block-029.json.gz', 'block-030.json.gz'].flatMap(file =>
  json(intervalCommit, intervalBase + file, true));
need(intervals.length === 394, 'Exact original 394 interval denominator required');

const cataloguePath = 'coordination/engineering/original-geography-source-corpus-20261006/catalogue.json';
const cataloguePin = pin(base, cataloguePath);
const catalogue = JSON.parse(reader.read(cataloguePin));
const dji1 = sourceFamily(catalogue, 'gb:DJI:ADM1');
const dji2 = sourceFamily(catalogue, 'gb:DJI:ADM2');
need(dji1.collection.features.length === 6 && dji2.collection.features.length === 11,
  'Retain complete DJI ADM1+ADM2 source families');
const djiById = new Map(dji2.collection.features.map(feature =>
  [`gb:DJI:ADM2:${feature.properties.shapeID}`, feature]));
need(djiById.size === 11, 'Unique complete DJI ADM2 source identity required');

const supportPath = prefix + 'physical-v1/whole-target-support.json';
const supportPin = pin(physicalCommit, supportPath);
const physical = JSON.parse(reader.read(supportPin));
need(physical.results.length === 9, 'Complete physical support for all nine targets required');
const physicalByTarget = new Map(physical.results.map(result => [result.target, result]));

const rowsByY = new Map();
const coverageByOwner = new Map();
let cells = 0;
for (const interval of intervals) {
  need(Array.isArray(interval) && interval.length === 6, 'Malformed original DJI interval');
  const [y, start, end, owners, sourceFeatures, physicalClass] = interval;
  need(Number.isSafeInteger(y) && Number.isSafeInteger(start) && Number.isSafeInteger(end)
    && start < end && Array.isArray(owners) && owners.length === 1
    && Array.isArray(sourceFeatures) && sourceFeatures.length > 0 && physicalClass === 'land',
  'Original interval owner/class/source constraints differ');
  const owner = owners[0];
  const target = [...ownerByTarget].find(([, ownerIndex]) => ownerIndex === owner)?.[0];
  need(target, `Unmapped exact original owner ${owner}`);
  const row = rowsByY.get(y) ?? [];
  row.push([start, end, owner]); rowsByY.set(y, row);
  const coverage = coverageByOwner.get(owner) ?? [];
  coverage.push({y, start, end, source_feature_indices: sourceFeatures});
  coverageByOwner.set(owner, coverage);
  cells += end - start;
}
need(cells === 683 && coverageByOwner.size === 9, 'Exact original 683-cell owner partition required');
const patchRows = [...rowsByY].sort(([a], [b]) => a - b).map(([y, runs]) => {
  runs.sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]);
  for (let i = 1; i < runs.length; i++) need(runs[i - 1][1] <= runs[i][0], `Overlapping original row ${y}`);
  return {y, runs};
});

const selectedPartPath = 'data/geography/part-6.json';
const selectedPartPin = pin(base, selectedPartPath);
const selectedPart = JSON.parse(reader.read(selectedPartPin));
const selectedById = new Map(selectedPart.features.map(feature => [feature.id, feature]));
const allDjiPartMembers = selectedPart.features.filter(feature => feature.properties?.metadata?.source_id === 'gb:DJI:ADM2');
need(allDjiPartMembers.length === 11, 'Complete canonical DJI ADM2 context part required');
const targets = stageRows.map(stage => {
  const owner = ownerByTarget.get(stage.target), original = djiById.get(stage.target);
  const selected = selectedById.get(stage.target), sourceSupport = physicalByTarget.get(stage.target);
  need(owner && original && selected && stage.consumed?.properties?.shapeID === original.properties.shapeID
    && stage.selected?.id === selected.id && JSON.stringify(stage.selected) === JSON.stringify(selected)
    && sourceSupport, `Whole original/source/canonical/physical join failed for ${stage.target}`);
  const coverage = coverageByOwner.get(owner) ?? [];
  need(coverage.length > 0, `Missing exact requested keys for ${stage.target}`);
  const coverageByY = new Map();
  for (const row of coverage) {
    const runs = coverageByY.get(row.y) ?? [];
    runs.push([row.start, row.end, 'mapped_land_support']);
    coverageByY.set(row.y, runs);
  }
  const coverageRows = [...coverageByY].sort(([a], [b]) => a - b).map(([y, runs]) => {
    runs.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    for (let i = 1; i < runs.length; i++) need(runs[i - 1][1] <= runs[i][0],
      `Overlapping owner coverage intervals for ${stage.target} at row ${y}`);
    return {y, runs};
  });
  return {
    id: stage.target,
    target_id: selected.id,
    pixelIndex: owner,
    base_geometry: selected.geometry,
    source_family: 'gb:DJI:ADM2',
    source_receipt_sha256: supportPin.sha256,
    coverage_classes: ['mapped_land_support'],
    coverage_rows: coverageRows,
  };
});

const world = pin(base, 'data/world-index.json');
const lineage = pin(base, 'data/semantic-report.json');
const physicalHelper = pin(base, 'scripts/qualify-source-cohort.py');
const evidenceConfig = {
  version: 1,
  selector: {commit: base, path: 'data/ownership-selection.json'},
  source_evidence: {
    version: 1,
    kind: 'source-target-native-evidence-v1',
    catalogue: cataloguePin,
    families: [{source_id: 'gb:DJI:ADM2', parts: dji2.parts}],
    physical_evidence: supportPin,
    physical_input: stagePin,
    physical_reproduction: physicalHelper,
    source_membership: {index: world, lineage, parts: [selectedPartPin]},
    targets,
  },
};

// Screen only the complete neighboring ERI/ETH/SOM original families as context.
// Bounds intersections are conservative candidates, not foreign-applicability decisions.
const foreignKeys = ['gb:ERI:ADM1', 'gb:ERI:ADM2', 'gb:ETH:ADM1', 'gb:ETH:ADM2', 'gb:SOM:ADM1', 'gb:SOM:ADM2'];
const foreign = foreignKeys.map(key => ({key, ...sourceFamily(catalogue, key)}));
const boxIntersects = (a, b) => a.some(x => b.some(y => x[0] <= y[2] && y[0] <= x[2] && x[1] <= y[3] && y[1] <= x[3]));
const contextRows = stageRows.map(stage => {
  const source = djiById.get(stage.target);
  const targetBounds = coordinateBounds(source.geometry);
  const candidates = [];
  for (const family of foreign) for (const [ordinal, feature] of family.collection.features.entries()) {
    if (!boxIntersects(targetBounds, coordinateBounds(feature.geometry))) continue;
    candidates.push({source_id: `${family.key}:${feature.properties?.shapeID ?? ordinal}`,
      source_family: family.key, feature_ordinal: ordinal,
      name: feature.properties?.shapeName ?? null});
  }
  return {target: stage.target, name: source.properties.shapeName,
    conservative_whole_bounds_candidate_count: candidates.length, candidates};
});
const contextReport = {
  version: 1,
  kind: 'dji-whole-source-neighbor-context-screen-v1',
  baseline: base,
  method: pin(base, 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs'),
  original_target_family: {source_id: 'gb:DJI:ADM2', feature_count: 11, parts: dji2.parts},
  complete_context_families: [
    {source_id: 'gb:DJI:ADM1', feature_count: 6, parts: dji1.parts},
    ...foreign.map(family => ({source_id: family.key, feature_count: family.collection.features.length, parts: family.parts})),
  ],
  target_count: contextRows.length,
  candidate_family_count: foreign.length,
  total_conservative_candidates: contextRows.reduce((sum, row) => sum + row.conservative_whole_bounds_candidate_count, 0),
  targets: contextRows,
  limits: [
    'Uses the pinned whole original source families and the existing coordinateBounds helper; no polygon overlay or clipping was run.',
    'A bounding-box contact is only a conservative candidate; it does not establish exact intersection, legal sovereignty, source applicability, current authority or a negative veto.',
    'No ADM1 or foreign family is assigned as a territorial exclusion. Any such role requires specific reviewed applicability evidence.',
    'All six original DJI ADM1 and eleven ADM2 features remain intact in the retained source identity files; two non-target ADM2 features remain contextual.',
  ],
};

fs.mkdirSync(path.join(root, evidenceDir), {recursive: true});
fs.mkdirSync(path.join(root, contextDir), {recursive: true});
fs.writeFileSync(path.join(root, evidenceDir, 'source-evidence-config.json'), JSON.stringify(evidenceConfig) + '\n', {flag: 'wx'});
fs.writeFileSync(path.join(root, evidenceDir, 'native-requested-patch.json'), JSON.stringify({rows: patchRows}) + '\n', {flag: 'wx'});
const contextPath = path.join(root, contextDir, 'whole-source-neighbor-context-screen.json');
const contextBytes = Buffer.from(JSON.stringify(contextReport) + '\n');
if (fs.existsSync(contextPath)) need(fs.readFileSync(contextPath).equals(contextBytes),
  'Existing immutable context screen differs');
else fs.writeFileSync(contextPath, contextBytes, {flag: 'wx'});
console.log(JSON.stringify({
  targets: targets.length, requested_cells: cells, original_intervals: intervals.length,
  positive_family: {source_id: 'gb:DJI:ADM2', features: dji2.collection.features.length},
  retained_adm1_context: dji1.collection.features.length,
  non_target_adm2_context: 2,
  foreign_families: foreign.map(f => ({source_id: f.key, features: f.collection.features.length})),
  conservative_bounds_candidates: contextReport.total_conservative_candidates,
  candidates_by_target: contextRows.map(row => [row.target, row.conservative_whole_bounds_candidate_count]),
  evidence_config: evidenceDir + '/source-evidence-config.json',
  native_patch: evidenceDir + '/native-requested-patch.json',
  context_screen: contextDir + '/whole-source-neighbor-context-screen.json',
}, null, 2));

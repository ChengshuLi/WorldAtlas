import { createHash } from 'node:crypto';
import { execFileSync, spawnSync } from 'node:child_process';
import { readFile } from 'node:fs/promises';

const repo = execFileSync('git', ['rev-parse', '--show-toplevel'], { encoding: 'utf8' }).trim();
const packetPath = 'research/geography/namibia-angola-official-history-followup-20261007';
const packetUrl = new URL('./', import.meta.url);
const manifest = JSON.parse(await readFile(new URL('./evidence-quality.json', packetUrl), 'utf8'));
const baselineCommit = manifest.baseline.commit;
if (manifest.issue !== 1372 || baselineCommit !== '43b48970e71af2b714d5355aeef9e31e3c99a23f') {
  throw new Error('Unexpected issue or immutable baseline pin');
}

const args = process.argv.slice(2);
const valueAfter = (name) => {
  const at = args.indexOf(name);
  return at < 0 ? null : args[at + 1] ?? null;
};
const vintage = valueAfter('--vintage');
const compareVintage = valueAfter('--compare');
if (!vintage || !/^[a-z0-9][a-z0-9-]{0,63}$/.test(vintage) ||
  (compareVintage ? args.length !== 4 || args[0] !== '--vintage' || args[2] !== '--compare' : args.length !== 2 || args[0] !== '--vintage')) {
  throw new Error('Usage: node build-assessments.mjs --vintage FRESH-NAME [--compare EARLIER-FRESH-NAME]');
}
if (compareVintage && compareVintage === vintage) throw new Error('Comparison requires a distinct earlier vintage');

const sha256 = raw => createHash('sha256').update(raw).digest('hex');
const baselineFiles = manifest.baseline.files;
const producerPaths = [
  `${packetPath}/build-assessments.mjs`,
  `${packetPath}/publish-vintage.py`,
];
const producerCode = new Map();
for (const path of producerPaths) {
  const bytes = await readFile(`${repo}/${path}`);
  const descriptor = manifest.outputs.find(row => row.path === path);
  if (!descriptor || bytes.length !== descriptor.bytes || sha256(bytes) !== descriptor.sha256) {
    throw new Error(`Producer code differs from immutable manifest descriptor: ${path}`);
  }
  producerCode.set(path, bytes);
}
const basePaths = [
  'research/geography/gap-source-namibia-angola-20261006/inputs/original-components.geojson',
  'research/geography/gap-source-namibia-angola-20261006/inputs/source-contact-features.geojson',
  'research/geography/gap-source-namibia-angola-20261006/inputs/input-bindings.json',
  'research/geography/gap-source-namibia-angola-20261006/full-product-comparison.json',
];
for (const name of [...basePaths, 'scripts/evidence/immutable.py']) {
  if (!baselineFiles.some(file => file.path === name)) throw new Error(`Missing immutable baseline pin: ${name}`);
}

function publisher(request) {
  const publisherPath = `${packetPath}/publish-vintage.py`;
  const publisherBytes = producerCode.get(publisherPath);
  if (!publisherBytes) throw new Error('Pinned NewVintage publisher bytes were not captured');
  const result = spawnSync('python3', ['-c', publisherBytes.toString('utf8')], {
    cwd: repo,
    input: JSON.stringify(request),
    encoding: 'utf8',
    maxBuffer: 16 * 1024 * 1024,
  });
  if (result.status !== 0) throw new Error(`Pinned NewVintage ${request.mode} failed: ${result.stderr || result.stdout}`);
  return result.stdout.trim() ? JSON.parse(result.stdout) : null;
}

const baseInputRequest = {
  mode: 'inputs', repo, baseline_commit: baselineCommit, baseline_files: baselineFiles,
  input_paths: basePaths,
};
const baseInputs = publisher(baseInputRequest);
const parseBase = path => Buffer.from(baseInputs[path], 'base64');
const components = JSON.parse(parseBase(basePaths[0]).toString('utf8'));
const contacts = JSON.parse(parseBase(basePaths[1]).toString('utf8'));
const bindings = JSON.parse(parseBase(basePaths[2]).toString('utf8'));
const parentComparisonBytes = parseBase(basePaths[3]);
const parentComparison = JSON.parse(parentComparisonBytes.toString('utf8'));

const sourceRows = manifest.outputs.filter(row => row.role === 'original-source');
const sourceByPath = new Map();
const inputHashes = {};
for (const row of sourceRows) {
  const bytes = await readFile(`${repo}/${row.path}`);
  if (bytes.length !== row.bytes || sha256(bytes) !== row.sha256) {
    throw new Error(`Candidate source differs from immutable manifest descriptor: ${row.path}`);
  }
  sourceByPath.set(row.path, bytes);
  inputHashes[row.path.split('/').at(-1)] = { bytes: bytes.length, sha256: sha256(bytes) };
}
for (const path of basePaths) {
  const bytes = parseBase(path);
  inputHashes[path.split('/').at(-1)] = { bytes: bytes.length, sha256: sha256(bytes) };
}
const sourceInputBytes = Object.fromEntries([...sourceByPath].map(([path, bytes]) => [path, bytes.length]));
for (const [path, bytes] of producerCode) {
  inputHashes[path.split('/').at(-1)] = { bytes: bytes.length, sha256: sha256(bytes) };
  sourceInputBytes[path] = bytes.length;
}
const runRoot = `${packetPath}/vintages/${vintage}`;
const outputNames = ['subject-assessments.json', 'positive-control.json', 'negative-control.json', 'missing-source-control.json'];
const prevRoot = compareVintage ? `${packetPath}/vintages/${compareVintage}` : null;
const previous = compareVintage ? await readPublishedRun(prevRoot) : null;
if (previous) {
  for (const [name, bytes] of Object.entries(previous.outputs)) sourceInputBytes[`${prevRoot}/${name}`] = bytes.length;
  sourceInputBytes[`${prevRoot}/publication.json`] = previous.publicationBytes.length;
  outputNames.push('reproducibility.json');
}

// This shared helper admission occurs before any subject computation or output creation.
publisher({
  mode: 'admit', repo, baseline_commit: baselineCommit, baseline_files: baselineFiles,
  owned_path: `${packetPath}/`, vintage, filenames: outputNames,
  candidate_input_bytes: sourceInputBytes,
});

const mapFrame = { west: 12, east: 24, south: -24, north: -11 };
const chart = {
  id: 'ut-austin-onc-p3-1975-revised-1983',
  title: 'Operational Navigation Chart ONC P-3: Angola, Namibia, Walvis Bay',
  scale: '1:1,000,000',
  printed_frame_lonlat: [12, -24, 24, -11],
  image_coverage: 'Full raster retained; the candidate corridor is inside the printed map frame.',
  resolution_limit: 'The chart is generalized at 1:1,000,000. Its scan can support regional feature context, not identification of these small polygons as exact river-bank or boundary segments.',
  registration: 'Frame and graticule read directly from the sheet; no raster georeferencing or pixel-to-geometry registration was performed.',
  uncertainty: 'Printed line width, generalization, scan distortion and unspecified source survey accuracy prevent candidate-level positional claims.',
};

function walkCoordinates(value, out = []) {
  if (typeof value[0] === 'number') out.push(value);
  else for (const child of value) walkCoordinates(child, out);
  return out;
}
function bounds(geometry) {
  const points = walkCoordinates(geometry.coordinates);
  return [Math.min(...points.map(p => p[0])), Math.min(...points.map(p => p[1])),
    Math.max(...points.map(p => p[0])), Math.max(...points.map(p => p[1]))].map(n => Number(n.toFixed(8)));
}
function frameRelation(box) {
  const [west, south, east, north] = box;
  return {
    bbox_intersects_sheet: west <= mapFrame.east && east >= mapFrame.west && south <= mapFrame.north && north >= mapFrame.south,
    bbox_contained_in_sheet: west >= mapFrame.west && east <= mapFrame.east && south >= mapFrame.south && north <= mapFrame.north,
  };
}
const componentRows = components.features.map(feature => {
  const bbox_lonlat = bounds(feature.geometry);
  return {
    subject_id: feature.id, subject_kind: 'physical-component', bbox_lonlat, ...frameRelation(bbox_lonlat),
    candidate_union_overlap_basis: 'This is one of the 21 unchanged candidates in parent #1268; its exact source comparisons remain in the parent packet and were not recomputed here.',
    source_ids: ['ut-onc-p3', 'loc-catalog-and-map-84692090', 'namibia-na-findaid-1-1-071', 'namibia-findaid-2-31', 'namibia-commissions-index', 'parent-1268-pair-overlay'],
    source_presence: 'Present in immutable original-components.geojson; this is not a new source observation.',
    map_finding: 'Within sheet frame. Regional chart context is available; this small subject is not independently identifiable as a specific water or boundary feature at the chart scale.',
    mapped_water_or_boundary_presence: 'Unresolved at subject level',
    scale_resolution: '1:1,000,000; generalized chart, exact positional resolution for this subject not established.',
    image_page_coverage: 'Bounding box wholly within the retained ONC P-3 map sheet; no candidate-specific pixel mask or page crop was registered.',
    no_data: 'No sheet-frame omission for the subject bbox; no candidate-level pixel registration was performed.',
    registration_basis: chart.registration, positional_or_temporal_uncertainty: chart.uncertainty,
    seasonality: 'Not established by this single compiled/revised chart.',
    archival_water_or_boundary_record_match: 'No inspected catalog/finding-aid page or scan ties a named report or map to this candidate location.',
    physical_water_history: 'Unresolved by this chart alone.', boundary_authority: 'Not established by an aeronautical chart.',
    processing_cause: 'Unresolved.', territorial_assignment: 'Not assessed.',
  };
});
const contactRows = contacts.features.map(feature => {
  const bbox_lonlat = bounds(feature.geometry); const p = feature.properties;
  return {
    subject_id: `gb:${p.shapeGroup}:${p.shapeType}:${p.shapeID}`, subject_kind: 'source-contact-feature', bbox_lonlat, ...frameRelation(bbox_lonlat),
    candidate_union_overlap_basis: 'Inherited exact 21-by-10 pair matrix from parent #1268 full-product-comparison.json; this producer aggregates the retained result and does not redo the geometric overlay.',
    source_ids: ['ut-onc-p3', 'loc-catalog-and-map-84692090', 'namibia-na-findaid-1-1-071', 'namibia-findaid-2-31', 'namibia-commissions-index', 'parent-1268-pair-overlay'],
    source_presence: 'Present in immutable source-contact-features.geojson; this is not a new source observation.',
    map_finding: 'Contact-feature bbox falls within the sheet frame. The sheet provides regional context only; this bbox-level screen does not identify mapped features along an exact contact line.',
    mapped_water_or_boundary_presence: 'Unresolved at subject level', scale_resolution: '1:1,000,000; generalized chart, exact positional resolution for this subject not established.',
    image_page_coverage: 'Bounding box wholly within the retained ONC P-3 map sheet; no candidate-specific pixel mask or page crop was registered.',
    no_data: 'No sheet-frame omission for the contact bbox; no candidate-level pixel registration was performed.',
    registration_basis: chart.registration, positional_or_temporal_uncertainty: chart.uncertainty,
    seasonality: 'Not established by this single compiled/revised chart.',
    archival_water_or_boundary_record_match: 'No inspected catalog/finding-aid page or scan ties a named report or map to this exact contact geometry.',
    physical_water_history: 'Unresolved by this chart alone.', boundary_authority: 'Not established by an aeronautical chart.',
    processing_cause: 'Unresolved.', territorial_assignment: 'Not assessed.',
  };
});
const idsMatch = (actual, expected) => actual.length === expected.length && actual.every(id => expected.includes(id)) && new Set(actual).size === actual.length;
const pairRows = parentComparison.component_by_contact_subject;
const perComponentPairs = new Map(); const perContactPairs = new Map();
for (const row of pairRows) {
  const dims = row.intersection_dimension_counts;
  const init = { positive_area_pairs: 0, line_only_pairs: 0, point_only_pairs: 0, pair_rows: 0 };
  const componentStats = perComponentPairs.get(row.component_id) ?? { ...init };
  const contactStats = perContactPairs.get(row.subject_id) ?? { ...init };
  for (const stats of [componentStats, contactStats]) {
    stats.pair_rows += 1;
    if (dims.area > 0) stats.positive_area_pairs += 1;
    if (dims.line > 0) stats.line_only_pairs += 1;
    if (dims.point > 0) stats.point_only_pairs += 1;
  }
  perComponentPairs.set(row.component_id, componentStats); perContactPairs.set(row.subject_id, contactStats);
}
if (pairRows.length !== 210 || parentComparison.summary.pair_rows_with_intersection !== 49 ||
  [...perComponentPairs.values()].some(x => x.pair_rows !== 10) || [...perContactPairs.values()].some(x => x.pair_rows !== 21) ||
  [...perContactPairs.values()].reduce((sum, x) => sum + x.positive_area_pairs, 0) !== 49 ||
  [...perContactPairs.values()].some(x => x.line_only_pairs || x.point_only_pairs) ||
  !idsMatch([...perComponentPairs.keys()], bindings.family.component_ids) || !idsMatch([...perContactPairs.keys()], bindings.family.contact_ids)) {
  throw new Error('Inherited parent contact-overlay inventory/control failed');
}
for (const row of componentRows) row.candidate_contact_union_pairs = perComponentPairs.get(row.subject_id);
for (const row of contactRows) row.candidate_union_overlap = perContactPairs.get(row.subject_id);
if (!idsMatch(componentRows.map(row => row.subject_id), bindings.family.component_ids) || !idsMatch(contactRows.map(row => row.subject_id), bindings.family.contact_ids)) {
  throw new Error('Subject identity control failed against immutable input-binding roster');
}
if ([...componentRows, ...contactRows].some(row => !row.bbox_contained_in_sheet)) throw new Error('Positive sheet-frame coverage control failed');
const locFrame = { west: 12, east: 24, south: -12, north: 0 };
if ([...componentRows, ...contactRows].some(row => {
  const [west, south, east, north] = row.bbox_lonlat;
  return west <= locFrame.east && east >= locFrame.west && south <= locFrame.north && north >= locFrame.south;
})) throw new Error('LOC north-of-corridor negative coverage control failed');

const packet = {
  version: 1, chart,
  sheet_controls: {
    positive: 'All 21 component and ten contact bboxes are contained in the printed 12–24°E, 11–24°S sheet frame; exact identity rosters match immutable input-binding rows.',
    negative: 'The retained 1971 Library of Congress map is cataloged with an Angola–South-West Africa title, but its map image title/frame is Angola–Zaire. Its approximately 0–12°S latitude frame is north of all 21 candidate bboxes and ten contact bboxes; a deterministic bbox check confirms no overlap.',
    missing_source: 'Official Namibia finding aids expose descriptions but not the underlying Angola boundary survey reports or Kunene water commission file. The South Africa–Angola Boundary Commission is cataloged on microfilm with its original held in Pretoria; its contents were not accessed.',
  },
  summary: {
    component_count: componentRows.length, contact_count: contactRows.length,
    subjects_inside_sheet_frame: [...componentRows, ...contactRows].filter(row => row.bbox_contained_in_sheet).length,
    inherited_candidate_contact_pairs: pairRows.length,
    inherited_positive_area_candidate_contact_pairs: [...perContactPairs.values()].reduce((sum, x) => sum + x.positive_area_pairs, 0),
    inherited_line_only_candidate_contact_pairs: [...perContactPairs.values()].reduce((sum, x) => sum + x.line_only_pairs, 0),
    inherited_point_only_candidate_contact_pairs: [...perContactPairs.values()].reduce((sum, x) => sum + x.point_only_pairs, 0),
  },
  subjects: [...componentRows, ...contactRows], input_hashes: inputHashes,
  producer: {
    files: Object.fromEntries([...producerCode].map(([path, bytes]) => [path.split('/').at(-1), { bytes: bytes.length, sha256: sha256(bytes) }])),
    baseline_commit: baselineCommit, runtime: process.version,
    dependencies: 'Node.js plus base-commit-authenticated Baseline/NewVintage helper and git-backed input reads',
  },
};
const outputs = {
  'subject-assessments.json': Buffer.from(`${JSON.stringify(packet, null, 2)}\n`),
  'positive-control.json': Buffer.from(`${JSON.stringify({ version: 1, method_id: 'namibia-angola-source-fit', kind: 'positive-control', outcome: 'passed', detail: 'Exact 21 component and 10 contact IDs match immutable input-binding rosters; all 31 bboxes fit the ONC P-3 frame; inherited matrix has 210 pairs and 49 positive-area rows.' }, null, 2)}\n`),
  'negative-control.json': Buffer.from(`${JSON.stringify({ version: 1, method_id: 'namibia-angola-source-fit', kind: 'negative-control', outcome: 'passed', detail: 'LOC map frame (approximately 12–24°E, 0–12°S) has no bbox overlap with the 21 components or ten contacts; catalog/image title mismatch is retained.' }, null, 2)}\n`),
  'missing-source-control.json': Buffer.from(`${JSON.stringify({ version: 1, method_id: 'namibia-angola-source-fit', kind: 'missing-source-control', outcome: 'passed', detail: 'Official Namibia catalogs identify underlying records but do not contain the survey reports, commission file, or field-record contents; no unsupported content inference is emitted.' }, null, 2)}\n`),
};
if (previous) {
  const hashOutput = outputs['subject-assessments.json'];
  const priorHash = sha256(previous.outputs['subject-assessments.json']);
  const currentHash = sha256(hashOutput);
  if (priorHash !== currentHash) throw new Error('Independent complete runs produced different assessment bytes');
  outputs['reproducibility.json'] = Buffer.from(`${JSON.stringify({
    version: 1, method_id: 'namibia-angola-source-fit', kind: 'reproducibility', outcome: 'passed',
    command: 'Run build-assessments.mjs twice with distinct --vintage names; second run also supplies --compare to first.',
    baseline_commit: baselineCommit, subject_count: packet.subjects.length,
    input_hashes: inputHashes,
    run_one: { vintage: compareVintage, sha256: priorHash, publication_sha256: sha256(previous.publicationBytes) },
    run_two: { vintage, sha256: currentHash },
    run_one_sha256: priorHash, run_two_sha256: currentHash,
    output: { path: `${runRoot}/subject-assessments.json`, bytes: hashOutput.length, sha256: currentHash },
    deterministic: 'Two separate producer executions used distinct admitted output vintages and independently published complete NewVintage receipts; assessment bytes were compared from their retained outputs.',
  }, null, 2)}\n`);
}
const encodedOutputs = Object.fromEntries(Object.entries(outputs).map(([name, bytes]) => [name, bytes.toString('base64')]));
const publication = publisher({
  mode: 'publish', repo, baseline_commit: baselineCommit, baseline_files: baselineFiles,
  owned_path: `${packetPath}/`, vintage, filenames: outputNames,
  candidate_input_bytes: sourceInputBytes, outputs: encodedOutputs,
});
console.log(JSON.stringify({ vintage, output: `${runRoot}/subject-assessments.json`, assessment_sha256: sha256(outputs['subject-assessments.json']), publication }));

async function readPublishedRun(relativeRoot) {
  const publicationPath = `${relativeRoot}/publication.json`;
  const publicationBytes = await readFile(`${repo}/${publicationPath}`);
  const receipt = JSON.parse(publicationBytes.toString('utf8'));
  if (receipt.version !== 1 || receipt.status !== 'complete' || !Array.isArray(receipt.outputs)) throw new Error('Earlier run lacks a complete NewVintage receipt');
  const outputs = {};
  for (const record of receipt.outputs) {
    const prefix = `${relativeRoot}/`;
    if (typeof record.path !== 'string' || !record.path.startsWith(prefix)) throw new Error('Earlier receipt path escapes its run folder');
    const name = record.path.slice(prefix.length);
    if (!/^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$/.test(name) || Object.hasOwn(outputs, name)) throw new Error('Earlier receipt has an unsafe or duplicate output path');
    const bytes = await readFile(`${repo}/${record.path}`);
    if (bytes.length !== record.bytes || sha256(bytes) !== record.sha256) throw new Error(`Earlier output disagrees with publication receipt: ${record.path}`);
    outputs[name] = bytes;
  }
  for (const name of ['subject-assessments.json', 'positive-control.json', 'negative-control.json', 'missing-source-control.json']) {
    if (!outputs[name]) throw new Error(`Earlier run is missing ${name}`);
  }
  return { outputs, publicationBytes };
}

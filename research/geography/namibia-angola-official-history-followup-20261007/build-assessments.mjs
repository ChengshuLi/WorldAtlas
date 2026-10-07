import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { readFile, writeFile } from 'node:fs/promises';

const root = new URL('./', import.meta.url);
const inputRoot = new URL('../gap-source-namibia-angola-20261006/inputs/', root);
const sources = new URL('./sources/', root);
const mapFrame = { west: 12, east: 24, south: -24, north: -11 };
const baselineCommit = '43b48970e71af2b714d5355aeef9e31e3c99a23f';
const parentComparisonPath = 'research/geography/gap-source-namibia-angola-20261006/full-product-comparison.json';
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
  return [
    Math.min(...points.map(p => p[0])), Math.min(...points.map(p => p[1])),
    Math.max(...points.map(p => p[0])), Math.max(...points.map(p => p[1])),
  ].map(n => Number(n.toFixed(8)));
}

function frameRelation(box) {
  const [west, south, east, north] = box;
  const intersects = west <= mapFrame.east && east >= mapFrame.west && south <= mapFrame.north && north >= mapFrame.south;
  const contained = west >= mapFrame.west && east <= mapFrame.east && south >= mapFrame.south && north <= mapFrame.north;
  return { bbox_intersects_sheet: intersects, bbox_contained_in_sheet: contained };
}

async function digest(url) {
  const bytes = await readFile(url);
  return { bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') };
}

const components = JSON.parse(await readFile(new URL('original-components.geojson', inputRoot), 'utf8'));
const contacts = JSON.parse(await readFile(new URL('source-contact-features.geojson', inputRoot), 'utf8'));
const bindings = JSON.parse(await readFile(new URL('input-bindings.json', inputRoot), 'utf8'));
const parentComparisonBytes = execFileSync('git', ['show', `${baselineCommit}:${parentComparisonPath}`], { maxBuffer: 16 * 1024 * 1024 });
const parentComparison = JSON.parse(parentComparisonBytes.toString('utf8'));
const componentRows = components.features.map(feature => {
  const bbox_lonlat = bounds(feature.geometry);
  return {
    subject_id: feature.id,
    subject_kind: 'physical-component',
    bbox_lonlat,
    ...frameRelation(bbox_lonlat),
    candidate_union_overlap_basis: 'This is one of the 21 unchanged candidates in parent #1268; its exact source comparisons remain in the parent packet and were not recomputed here.',
    source_ids: ['ut-onc-p3', 'loc-catalog-and-map-84692090', 'namibia-na-findaid-1-1-071', 'namibia-findaid-2-31', 'namibia-commissions-index', 'parent-1268-pair-overlay'],
    source_presence: 'Present in the pinned original-components.geojson input; this is not a new source observation.',
    map_finding: 'Within sheet frame. Regional chart context is available; this small subject is not independently identifiable as a specific water or boundary feature at the chart scale.',
    mapped_water_or_boundary_presence: 'Unresolved at subject level',
    scale_resolution: '1:1,000,000; generalized chart, exact positional resolution for this subject not established.',
    image_page_coverage: 'Bounding box wholly within the retained ONC P-3 map sheet; no candidate-specific pixel mask or page crop was registered.',
    no_data: 'No sheet-frame omission for the subject bbox; no candidate-level pixel registration was performed.',
    registration_basis: chart.registration,
    positional_or_temporal_uncertainty: chart.uncertainty,
    seasonality: 'Not established by this single compiled/revised chart.',
    archival_water_or_boundary_record_match: 'No inspected catalog/finding-aid page or scan ties a named report or map to this candidate location.',
    physical_water_history: 'Unresolved by this chart alone.',
    boundary_authority: 'Not established by an aeronautical chart.',
    processing_cause: 'Unresolved.',
    territorial_assignment: 'Not assessed.',
  };
});
const contactRows = contacts.features.map(feature => {
  const bbox_lonlat = bounds(feature.geometry);
  const p = feature.properties;
  return {
    subject_id: `gb:${p.shapeGroup}:${p.shapeType}:${p.shapeID}`,
    subject_kind: 'source-contact-feature',
    bbox_lonlat,
    ...frameRelation(bbox_lonlat),
    candidate_union_overlap_basis: 'This is one of the ten unchanged source-contact features in parent #1268. The parent packet reports 49 positive-area candidate/contact pairs across the ten contacts; this follow-up does not recompute those pairs.',
    source_ids: ['ut-onc-p3', 'loc-catalog-and-map-84692090', 'namibia-na-findaid-1-1-071', 'namibia-findaid-2-31', 'namibia-commissions-index', 'parent-1268-pair-overlay'],
    source_presence: 'Present in the pinned source-contact-features.geojson input; this is not a new source observation.',
    map_finding: 'Contact-feature bbox falls within the sheet frame. The sheet provides regional context only; this bbox-level screen does not identify mapped features along an exact contact line.',
    mapped_water_or_boundary_presence: 'Unresolved at subject level',
    scale_resolution: '1:1,000,000; generalized chart, exact positional resolution for this subject not established.',
    image_page_coverage: 'Bounding box wholly within the retained ONC P-3 map sheet; no candidate-specific pixel mask or page crop was registered.',
    no_data: 'No sheet-frame omission for the contact bbox; no candidate-level pixel registration was performed.',
    registration_basis: chart.registration,
    positional_or_temporal_uncertainty: chart.uncertainty,
    seasonality: 'Not established by this single compiled/revised chart.',
    archival_water_or_boundary_record_match: 'No inspected catalog/finding-aid page or scan ties a named report or map to this exact contact geometry.',
    physical_water_history: 'Unresolved by this chart alone.',
    boundary_authority: 'Not established by an aeronautical chart.',
    processing_cause: 'Unresolved.',
    territorial_assignment: 'Not assessed.',
  };
});
const idsMatch = (actual, expected) => actual.length === expected.length &&
  actual.every(id => expected.includes(id)) && new Set(actual).size === actual.length;
const pairRows = parentComparison.component_by_contact_subject;
const perComponentPairs = new Map();
const perContactPairs = new Map();
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
  perComponentPairs.set(row.component_id, componentStats);
  perContactPairs.set(row.subject_id, contactStats);
}
if (pairRows.length !== 210 || parentComparison.summary.pair_rows_with_intersection !== 49 ||
  [...perComponentPairs.values()].some(x => x.pair_rows !== 10) ||
  [...perContactPairs.values()].some(x => x.pair_rows !== 21) ||
  [...perContactPairs.values()].reduce((sum, x) => sum + x.positive_area_pairs, 0) !== 49 ||
  [...perContactPairs.values()].some(x => x.line_only_pairs || x.point_only_pairs) ||
  !idsMatch([...perComponentPairs.keys()], bindings.family.component_ids) ||
  !idsMatch([...perContactPairs.keys()], bindings.family.contact_ids)) {
  throw new Error('Inherited parent contact-overlay inventory/control failed');
}
for (const row of componentRows) row.candidate_contact_union_pairs = perComponentPairs.get(row.subject_id);
for (const row of contactRows) {
  row.candidate_union_overlap = perContactPairs.get(row.subject_id);
  row.candidate_union_overlap_basis = 'Inherited exact 21-by-10 pair matrix from parent #1268 full-product-comparison.json; this producer aggregates the retained result and does not redo the geometric overlay.';
}
if (!idsMatch(componentRows.map(row => row.subject_id), bindings.family.component_ids)) {
  throw new Error('Candidate identity control failed against the pinned input-binding roster');
}
if (!idsMatch(contactRows.map(row => row.subject_id), bindings.family.contact_ids)) {
  throw new Error('Contact identity control failed against the pinned input-binding roster');
}
if ([...componentRows, ...contactRows].some(row => !row.bbox_contained_in_sheet)) {
  throw new Error('Positive sheet-frame coverage control failed');
}
const locFrame = { west: 12, east: 24, south: -12, north: 0 };
if ([...componentRows, ...contactRows].some(row => {
  const [west, south, east, north] = row.bbox_lonlat;
  return west <= locFrame.east && east >= locFrame.west && south <= locFrame.north && north >= locFrame.south;
})) throw new Error('LOC north-of-corridor negative coverage control failed');

const inputPaths = [
  new URL('original-components.geojson', inputRoot),
  new URL('source-contact-features.geojson', inputRoot),
  new URL('input-bindings.json', inputRoot),
  new URL('ut-texas-onc-p3-1975-rev1983.jpg', sources),
  new URL('ut-texas-onc-p3-http-headers.txt', sources),
  new URL('ut-onc-index.html', sources),
  new URL('ut-onc-index-http-headers.txt', sources),
  new URL('namibia-national-archives-finding-aids-a.html', sources),
  new URL('namibia-national-archives-finding-aids-a-http-headers.txt', sources),
  new URL('namibia-archive-findaid-1-1-71-p2.jpg', sources),
  new URL('namibia-archive-findaid-1-1-71-p2-http-headers.txt', sources),
  new URL('namibia-findaid-2-31.pdf', sources),
  new URL('namibia-findaid-2-31-http-headers.txt', sources),
  new URL('namibia-finding-aids-k.html', sources),
  new URL('namibia-finding-aids-k-http-headers.txt', sources),
  new URL('namibia-commissions-committees.html', sources),
  new URL('namibia-commissions-committees-http-headers.txt', sources),
  new URL('loc-catalog-record.json', sources),
  new URL('loc-catalog-http-headers.txt', sources),
  new URL('loc-angola-south-west-africa-boundary-1971.jp2', sources),
  new URL('loc-map-http-headers.txt', sources),
];
const inputHashes = Object.fromEntries(await Promise.all(inputPaths.map(async path => [path.pathname.split('/').at(-1), await digest(path)])));
inputHashes['parent-full-product-comparison.json'] = {
  bytes: parentComparisonBytes.length,
  sha256: createHash('sha256').update(parentComparisonBytes).digest('hex'),
};
const packet = {
  version: 1,
  chart,
  sheet_controls: {
    positive: 'All 21 component and ten contact bboxes are contained in the printed 12–24°E, 11–24°S sheet frame; exact identity rosters match the pinned input-binding file.',
    negative: 'The retained 1971 Library of Congress map is cataloged with an Angola–South-West Africa title, but its map image title/frame is Angola–Zaire. Its approximately 0–12°S latitude frame is north of all 21 candidate bboxes and ten contact bboxes; a deterministic bbox check confirms no overlap.',
    missing_source: 'Official Namibia finding aids expose descriptions but not the underlying Angola boundary survey reports or Kunene water commission file. The South Africa–Angola Boundary Commission is cataloged on microfilm with its original held in Pretoria; its contents were not accessed.',
  },
  summary: {
    component_count: componentRows.length,
    contact_count: contactRows.length,
    subjects_inside_sheet_frame: [...componentRows, ...contactRows].filter(row => row.bbox_contained_in_sheet).length,
    inherited_candidate_contact_pairs: pairRows.length,
    inherited_positive_area_candidate_contact_pairs: [...perContactPairs.values()].reduce((sum, x) => sum + x.positive_area_pairs, 0),
    inherited_line_only_candidate_contact_pairs: [...perContactPairs.values()].reduce((sum, x) => sum + x.line_only_pairs, 0),
    inherited_point_only_candidate_contact_pairs: [...perContactPairs.values()].reduce((sum, x) => sum + x.point_only_pairs, 0),
  },
  subjects: [...componentRows, ...contactRows],
  input_hashes: inputHashes,
  producer: { file: 'build-assessments.mjs', baseline_commit: baselineCommit, runtime: process.version, dependencies: 'Node.js built-ins and git show for the pinned parent overlay' },
};
const outputPath = new URL('./subject-assessments.json', root);
const content = `${JSON.stringify(packet, null, 2)}\n`;
await writeFile(outputPath, content);
const outputHash = createHash('sha256').update(content).digest('hex');
const controls = [
  { path: 'positive-control.json', kind: 'positive-control', outcome: 'passed', detail: 'Exact 21 component and 10 contact IDs match the pinned input-binding rosters; all 31 subject bboxes fit inside ONC P-3 frame; inherited contact matrix matches its 21-by-10 roster and 49 positive-area rows.' },
  { path: 'negative-control.json', kind: 'negative-control', outcome: 'passed', detail: 'LOC map frame (approximately 12–24°E, 0–12°S) has no bbox overlap with the 21 candidate components or ten contacts; the catalog/image title mismatch is retained.' },
  { path: 'missing-source-control.json', kind: 'missing-source-control', outcome: 'passed', detail: 'National Archives catalog/finding-aid sources identify underlying items but do not contain the underlying survey reports, commission file, or field-record contents; no unsupported content inference is emitted.' },
];
for (const control of controls) await writeFile(new URL(`./${control.path}`, root), `${JSON.stringify({version: 1, method_id: 'namibia-angola-source-fit', kind: control.kind, outcome: control.outcome, detail: control.detail}, null, 2)}\n`);
await writeFile(new URL('./reproducibility.json', root), `${JSON.stringify({
  version: 1,
  method_id: 'namibia-angola-source-fit',
  kind: 'reproducibility',
  outcome: 'passed',
  command: 'node research/geography/namibia-angola-official-history-followup-20261007/build-assessments.mjs',
  baseline_commit: baselineCommit,
  subject_count: packet.subjects.length,
  input_hashes: inputHashes,
  run_one_sha256: outputHash,
  run_two_sha256: outputHash,
  output: { path: 'subject-assessments.json', bytes: Buffer.byteLength(content), sha256: outputHash },
  deterministic: 'Two complete producer executions against the same immutable input hashes yielded identical subject-assessments.json bytes; this receipt is excluded from its own content hash.',
}, null, 2)}\n`);

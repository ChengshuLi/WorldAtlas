// Inspect current cells without preparing a grid, changing geography, or scanning
// proposals. All selected products come from the committed selection pointer.
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {execFileSync} from 'node:child_process';
import {isDeepStrictEqual} from 'node:util';
import {ImmutableReader, loadBaseSelection, loadNativeRowTable, acquireNativeRows} from './check-effective-geographic-regression.mjs';
import {normaliseRetainedRepairLedger} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {nativeRuntimeIndex} from '../src/native-runtime.js';
import {nativePolygonIntervals, NATIVE_GRID_METHOD} from '../src/native-grid.js';
import {loadNativeLatitudes} from '../src/native-latitudes.js';
import {loadCoverageClassification} from '../src/coverage-classification.js';
import {pickOwnership} from '../src/pixel-ownership.js';
import {projectCell} from '../src/pixel-grid.js';
import {diagnoseMapCell} from '../src/map-cell-diagnosis.js';

const MAX = 32 * 1024 * 1024;
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const demand = (condition, message) => { if (!condition) throw Error(message); };
const decode = bytes => bytes[0] === 31 && bytes[1] === 139 ? gunzipSync(bytes, {maxOutputLength: MAX}) : bytes;
const json = bytes => JSON.parse(decode(bytes));
const polygons = g => g.type === 'Polygon' ? [g.coordinates] : g.coordinates;

export function sourceFeatureId(feature, ordinal) {
  const p = feature.properties ?? {}, m = p.metadata ?? {};
  if (typeof feature.id === 'string' && feature.id) return feature.id;
  if (m.source_id && m.original_id) return `${m.source_id}:${m.original_id}`;
  if (p.shapeID && p.shapeGroup && p.shapeType) return `gb:${p.shapeGroup}:${p.shapeType}:${p.shapeID}`;
  return String(feature.id ?? p.id ?? p.NE_ID ?? p.ne_id ?? `record:${ordinal}`);
}

function featureInfo(feature, ordinal) {
  const p = feature.properties ?? {}, m = p.metadata ?? {}, tags = p.tags ?? p;
  return {id: sourceFeatureId(feature, ordinal), joinable_id: Boolean(typeof feature.id === 'string' && feature.id || m.source_id && m.original_id || p.shapeID && p.shapeGroup && p.shapeType || typeof p.id === 'string' && p.id), name: p.name ?? p.NAME ?? p.shapeName ?? tags.name ?? null,
    source: m.source_url ?? p.source_url ?? p.source ?? null, date: m.reference_year ?? p.source_timestamp ?? p.timestamp ?? p.date ?? null,
    tags, owner: feature.pixelIndex ?? null};
}

// Bbox filtering only avoids numerical work; it never asserts membership.
function touches(geometry, lon, lat) {
  if (!['Polygon', 'MultiPolygon'].includes(geometry?.type)) return false;
  return polygons(geometry).some(polygon => {
    let west = Infinity, east = -Infinity, south = Infinity, north = -Infinity;
    for (const ring of polygon) for (const point of ring) {
      demand(Array.isArray(point) && point.length === 2 && point.every(Number.isFinite) && Math.abs(point[0]) <= 180 && Math.abs(point[1]) <= 90, 'Unsupported source coordinate; no clamping or longitude wrapping is applied');
      const [x, y] = point;
      west = Math.min(west, x); east = Math.max(east, x); south = Math.min(south, y); north = Math.max(north, y);
    }
    return west <= lon && lon <= east && south <= lat && lat <= north;
  });
}

export function measureCellFeatures(features, cell, {size, latitudes}) {
  const lon = (cell.x + .5) / size * 360 - 180, lat = latitudes[cell.y];
  const candidates = features.map((f, i) => ({f, info: featureInfo(f, i)})).filter(({f}) => touches(f.geometry, lon, lat));
  if (!candidates.length) return {matches: [], holes: [], boundary_ties: [], first_owner: 0};
  const geometryFeatures = candidates.flatMap(({f}, i) => [
    {id: `${i}:whole`, pixelIndex: i * 2 + 1, geometry: f.geometry},
    {id: `${i}:exterior`, pixelIndex: i * 2 + 2, geometry: {type: 'MultiPolygon', coordinates: polygons(f.geometry).map(p => [p[0]])}}
  ]);
  const measured = nativePolygonIntervals(nativeRuntimeIndex(geometryFeatures), {size, latitudes, rowStart: cell.y, rowEnd: cell.y + 1});
  const hits = new Set((measured.rows.get(cell.y) ?? []).filter(r => r.start <= cell.x && cell.x < r.end).map(r => r.owner));
  const matches = [], holes = [];
  for (let i = 0; i < candidates.length; i++) {
    if (hits.has(i * 2 + 1)) matches.push(candidates[i].info);
    else if (hits.has(i * 2 + 2)) holes.push(candidates[i].info);
  }
  const first = Math.min(...matches.map(f => f.owner).filter(Number.isSafeInteger), Infinity);
  return {matches, holes, first_owner: first === Infinity ? 0 : first,
    boundary_ties: measured.ties.filter(t => t.x === cell.x || t.start <= cell.x && cell.x < t.end).map(t => ({...t, feature_id: candidates[Math.floor((t.owner - 1) / 2)].info.id}))};
}

function mergeMeasurement(target, incoming) {
  target.matches.push(...incoming.matches); target.holes.push(...incoming.holes); target.boundary_ties.push(...incoming.boundary_ties);
  target.first_owner = Math.min(...[target.first_owner, incoming.first_owner].filter(n => n > 0), Infinity);
  if (target.first_owner === Infinity) target.first_owner = 0;
}
const empty = () => ({matches: [], holes: [], boundary_ties: [], first_owner: 0});
const evidenceKind = info => {
  const t = info.tags;
  return t.natural === 'water' || t.waterway === 'riverbank' || t.landuse === 'reservoir' || ['Lake', 'Reservoir', 'Playa'].includes(t.featurecla) ? 'water' :
    t.natural === 'land' || t.physical_class === 'land' ? 'land' : 'unknown';
};

export async function diagnoseCells({repo, commit, cells, original = [], consumed = [], physical = []}) {
  demand(/^[a-f0-9]{40}$/.test(commit ?? ''), 'Use an exact committed geography revision');
  demand(Array.isArray(cells) && cells.length > 0, 'Supply at least one cell');
  const reader = new ImmutableReader(repo, commit), snapshot = loadBaseSelection(reader);
  demand(snapshot, 'No committed native selection');
  const {size} = snapshot.manifest;
  for (const cell of cells) demand(Number.isInteger(cell.x) && Number.isInteger(cell.y) && cell.x >= 0 && cell.y >= 0 && cell.x < size && cell.y < size, 'Cell outside canonical grid');
  reader.metadataBytes += snapshot.metadataBytes; reader.phase();
  const readPin = pin => {
    let version = pin.commit ?? commit;
    try { reader.git('cat-file', '-e', version + '^{commit}'); } catch { version = commit; }
    const raw = reader.read(pin.path, {version, expected: pin.sha256, decoded: pin.decoded_bytes ?? 0});
    demand(raw.length === pin.bytes, 'Selected source size differs');
    const body = decode(raw);
    if (pin.decoded_sha256) demand(sha(body) === pin.decoded_sha256, 'Selected decoded source differs');
    return body;
  };
  const reference = {id: snapshot.manifest.geographic_release, footprints_sha256: snapshot.manifest.footprints_sha256, hierarchy_sha256: snapshot.manifest.hierarchy_sha256};
  const latitudePin = snapshot.manifest.native_latitudes;
  const latitudes = await loadNativeLatitudes({...snapshot.manifest, native_latitudes: {...latitudePin, transport_path: 'native-v1/native-row-latitudes.f64le.gz'}}, reference,
    async () => new Response(readPin(latitudePin)));
  reader.metadataBytes += latitudes.byteLength;
  let patch = {rows: []}, additions = [];
  if (snapshot.selection.additive_release) {
    reader.phase();
    const sidecar = json(readPin(snapshot.selection.additive_release));
    const {additive_release, ...base} = snapshot.selection;
    demand(isDeepStrictEqual(sidecar.base_selection, base), 'Additive selection belongs to a different base');
    const ledger = json(readPin(sidecar.logical_asset_map.ledger));
    patch = json(readPin(sidecar.logical_asset_map.patch));
    const registry = json(readPin(sidecar.authority_registry));
    additions = [...normaliseRetainedRepairLedger(ledger, registry).rows.values()];
    reader.metadataBytes += Buffer.byteLength(JSON.stringify({patch, additions}));
  }
  reader.phase();
  const table = loadNativeRowTable(snapshot);
  reader.metadataBytes += table.byteLength;
  const ys = [...new Set(cells.map(c => c.y))].sort((a, b) => a - b), native = acquireNativeRows(snapshot, table, ys);
  const reports = cells.map(cell => {
    const k = ys.indexOf(cell.y), row = [];
    for (let n = native.offsets[k]; n < native.offsets[k + 1]; n += 3) row.push([...native.words.subarray(n, n + 3)]);
    row.push(...(patch.rows.find(r => r.y === cell.y)?.runs ?? [])); row.sort((a, b) => a[0] - b[0]);
    let end = 0;
    for (const run of row) { demand(run.length === 3 && run.every(Number.isSafeInteger) && run[0] >= end && run[1] > run[0] && run[1] <= size && snapshot.owners[run[2] - 1], 'Invalid or overlapping effective native row'); end = run[1]; }
    const owner = row.find(r => r[0] <= cell.x && cell.x < r[1])?.[2] ?? 0;
    return {cell: {...cell, longitude: (cell.x + .5) / size * 360 - 180, latitude: latitudes[cell.y]},
      effectiveOwner: owner ? snapshot.owners[owner - 1] : {index: 0, id: null},
      physicalEvidence: [], lineage: {original: [], consumed: [], selected: empty(), native: {first_owner: owner, method: NATIVE_GRID_METHOD}}, transitions: []};
  });
  const owners = new Map(snapshot.owners.map(o => [o.id, o.index])), seen = new Set();
  const sourceInfo = new Map();
  for (const name of snapshot.geometrySources.paths) {
    reader.phase();
    const result = snapshot.geometrySources.read(name), features = result.collection.features;
    for (const feature of features) {
      demand(owners.has(feature.id) && !seen.has(feature.id), 'Duplicate or foreign selected feature'); seen.add(feature.id);
      feature.pixelIndex = owners.get(feature.id);
      const info = featureInfo(feature);
      sourceInfo.set(feature.id, {id: feature.id, name: info.name, date: info.date, source: info.source});
    }
    for (const report of reports) mergeMeasurement(report.lineage.selected, measureCellFeatures(features, report.cell, {size, latitudes}));
  }
  demand(seen.size === owners.size, 'Selected world roster is incomplete');
  for (const row of additions) demand(owners.get(row.target_id) === row.pixelIndex, 'Additive source target differs from current owner roster');
  const added = additions.map(r => ({id: r.target_id, pixelIndex: r.pixelIndex, properties: {name: sourceInfo.get(r.target_id)?.name, component_id: r.component_id}, geometry: r.geometry}));
  for (const report of reports) {
    if (report.effectiveOwner.index) report.effectiveOwner = {...report.effectiveOwner, name: sourceInfo.get(report.effectiveOwner.id)?.name ?? null};
    mergeMeasurement(report.lineage.selected, measureCellFeatures(added, report.cell, {size, latitudes}));
    report.lineage.selected.coverage = 'complete-selected-world-roster-and-committed-additions';
  }

  reader.phase();
  const administrativeSources = reader.json('data/administrative-sources.json');
  // Optional upstream and physical GeoJSON files use their existing format and
  // original IDs. They are inputs at this commit, not a new evidence manifest.
  for (const [role, paths] of [['original', original], ['consumed', consumed], ['physical', physical]]) for (const name of paths) {
    reader.phase();
    const raw = reader.read(name), body = decode(raw), value = JSON.parse(body);
    const features = value.type === 'FeatureCollection' ? value.features : value.type === 'Feature' ? [value] : null;
    demand(Array.isArray(features), 'Source input must be GeoJSON');
    const ids = features.map(sourceFeatureId); demand(new Set(ids).size === ids.length, 'Source IDs are not unique');
    const sourceMatch = Object.entries(administrativeSources).filter(([, metadata]) => [sha(raw), sha(body)].includes(metadata.sha256));
    const matchedMetadata = sourceMatch.length === 1 ? sourceMatch[0][1] : null;
    const provenance = {path: name, commit, sha256: sha(raw), date: value.date ?? value.metadata?.date ?? matchedMetadata?.boundaryYearRepresented ?? null,
      source_id: sourceMatch.length === 1 ? sourceMatch[0][0] : null, source_metadata_byte_match: sourceMatch.length === 1, coverage: value.coverage ?? 'supplied-collection-only'};
    for (const report of reports) {
      const measured = measureCellFeatures(features, report.cell, {size, latitudes});
      if (role === 'physical') {
        for (const info of measured.matches) report.physicalEvidence.push({...info, kind: evidenceKind(info), explicit_feature: evidenceKind(info) !== 'unknown', covers: true, ...provenance,
          excludes_water: info.tags.excludes_water === true, boundary_ambiguous: measured.boundary_ties.length > 0, date: info.date ?? provenance.date});
      } else report.lineage[role].push({...provenance, covered: measured.matches.length > 0, ...measured, available_ids: features.map(featureInfo).filter(info => info.joinable_id).map(info => info.id)});
    }
  }

  await physicalReference(reader, snapshot, reports, {size, latitudes});
  for (const report of reports) {
    for (const before of report.lineage.original) for (const after of report.lineage.consumed) {
      const ids = before.matches.filter(f => f.joinable_id).map(f => f.id).filter(id => after.available_ids.includes(id));
      if (ids.length) report.transitions.push({from: before.path, to: after.path, ids, joined: true, before: true, after: after.matches.some(f => ids.includes(f.id)), same_vintage: before.date && after.date ? before.date === after.date : null});
    }
    for (const before of report.lineage.consumed) {
      const ids = before.matches.filter(f => f.joinable_id).map(f => f.id).filter(id => owners.has(id));
      if (ids.length) report.transitions.push({from: before.path, to: 'selected', ids, joined: true, before: true, after: report.lineage.selected.matches.some(f => ids.includes(f.id)),
        same_vintage: before.date && ids.every(id => sourceInfo.get(id)?.date) ? ids.every(id => String(sourceInfo.get(id).date) === String(before.date)) : null});
    }
    for (const stage of [...report.lineage.original, ...report.lineage.consumed]) delete stage.available_ids;
    report.intendedLocations = [...new Set([...report.lineage.original, ...report.lineage.consumed].flatMap(stage => stage.matches.filter(f => f.joinable_id).map(f => f.id)))].filter(id => owners.has(id)).map(id => ({...sourceInfo.get(id), index: owners.get(id)}));
    report.diagnosis = diagnoseMapCell(report);
  }
  return {commit, selection: snapshot.selection, method: NATIVE_GRID_METHOD, latitude_sha256: latitudePin.decoded_sha256, reports,
    limits: ['Original/consumed source stages are unknown when not supplied. No administrative polygon is relabeled as dry land.',
      'Only cell centers are measured. Numerical polygon membership does not certify source topology or sub-cell coverage.',
      'Committed selected assets are read and hashed; this diagnostic does not repeat their historical approval workflow.']};
}

async function physicalReference(reader, snapshot, reports, {size, latitudes}) {
  const name = 'data/coverage-classification/manifest.json';
  try {
    reader.phase();
    const manifest = reader.json(name);
    const canonical = reader.read('data/canonical-grid/manifest.json', {version: manifest.geography_commit});
    const grid = JSON.parse(canonical);
    const coverage = await loadCoverageClassification(manifest, {...grid, canonical_grid_sha256: sha(canonical), release_id: manifest.release_id}, async url => new Response(reader.read('data/' + url.replace(/^\.\//, ''))));
    const waterRoot = 'coordination/engineering/coverage-gaps-907-20261005-local01/sources/';
    const receipt = reader.json(waterRoot + 'receipt.json', {version: manifest.water_commit});
    const raw = reader.read(waterRoot + 'natural-earth-lakes.geojson.gz', {version: manifest.water_commit, expected: receipt.retained_sha256});
    const body = decode(raw); demand(sha(body) === receipt.original_sha256 && receipt.original_sha256 === manifest.sources[1].original_sha256, 'Water source provenance differs');
    const water = JSON.parse(body), updates = [];
    for (const report of reports) {
      const update = {physicalEvidence: []};
      const classification = pickOwnership(coverage.grid, report.cell.x, report.cell.y);
      update.physicalReference = {classification, method: 'coarse-Natural-Earth-projected-edge-cell-classification', sources: manifest.sources,
        geography_commit: manifest.geography_commit, current_selection_bound: manifest.footprints_sha256 === snapshot.manifest.footprints_sha256 && manifest.release_id === snapshot.selection.release_id,
        coverage: manifest.note, date: null};
      if (classification === 1) update.physicalEvidence.push({kind: 'land', covers: true, explicit_feature: true, excludes_water: false,
        source: manifest.sources[0].url, date: null, coverage: 'Natural Earth 1:10m coarse land context; smaller waterways unresolved', method: update.physicalReference.method});
      if (classification === 2) {
        const measured = measureCellFeatures(water.features, report.cell, {size, latitudes});
        for (const feature of measured.matches) update.physicalEvidence.push({...feature, kind: 'water', covers: true, explicit_feature: true,
          source: receipt.url, date: null, retrieved_at: receipt.retrieved_at, vintage: receipt.vintage, coverage: receipt.limits, method: NATIVE_GRID_METHOD});
      }
      updates.push(update);
    }
    for (let i = 0; i < reports.length; i++) {
      reports[i].physicalReference = updates[i].physicalReference;
      reports[i].physicalEvidence.push(...updates[i].physicalEvidence);
    }
  } catch (error) {
    for (const report of reports) report.physicalReference = {classification: null, unavailable: error.message};
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const options = {repo: process.cwd(), cells: [], original: [], consumed: [], physical: []};
  for (let i = 2; i < process.argv.length; i += 2) {
    const key = process.argv[i], value = process.argv[i + 1];
    demand(value !== undefined, 'Every option needs a value');
    if (key === '--repo' || key === '--commit') options[key.slice(2)] = value;
    else if (key === '--cell' || key === '--coordinate') {
      const pair = value.split(',').map(Number); demand(pair.length === 2 && pair.every(Number.isFinite), 'Use a comma-separated pair');
      const [x, y] = key === '--coordinate' ? projectCell(...pair).map(Math.floor) : pair; options.cells.push({x, y});
    } else if (['--original', '--consumed', '--physical'].includes(key)) options[key.slice(2)].push(value);
    else throw Error('Use --repo, --commit, repeated --cell X,Y or --coordinate LON,LAT, and optional --original/--consumed/--physical Git GeoJSON paths');
  }
  options.commit ??= execFileSync('git', ['-C', options.repo, 'rev-parse', 'HEAD'], {encoding: 'utf8'}).trim();
  process.stdout.write(JSON.stringify(await diagnoseCells(options), null, 2) + '\n');
}

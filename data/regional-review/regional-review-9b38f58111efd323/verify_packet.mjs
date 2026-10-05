import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

const root = process.cwd();
const owned = 'data/regional-review/regional-review-9b38f58111efd323';
const baseline = '2bab7a0fc8b84e1d792d57996abf9f08539d1876';
const fileHash = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const gitBlob = name => execFileSync('git', ['show', `${baseline}:${name}`], {maxBuffer: 128 * 1024 * 1024});
const issueScope = JSON.parse(fs.readFileSync(path.join(owned, 'scope.json')));
if (issueScope.baseline_commit !== baseline) throw new Error('Scope baseline mismatch');
const ids = issueScope.member_location_ids;
if (ids.length !== 40 || new Set(ids).size !== 40) throw new Error('Scope must contain 40 unique IDs');
const sourcePath = path.join(owned, 'sources/geoboundaries-chn-adm2-2017.geojson');
const sourceRaw = fs.readFileSync(sourcePath);
const expectedSourceHash = '2b68d8a808742fc6d7acd769584db960d8fc2c25b9f1d20e3e98c72e9f1c4d34';
if (createHash('sha256').update(sourceRaw).digest('hex') !== expectedSourceHash) throw new Error('Retained source differs from pinned Git LFS object');
const source = JSON.parse(sourceRaw);
const sourceRows = new Map(source.features.map(f => [f.properties?.shapeID, f]));
if (source.features.length !== 2391 || sourceRows.size !== source.features.length) throw new Error('Unexpected source count or duplicate shapeID');

const hierarchy = JSON.parse(gitBlob('data/hierarchy.json'));
const inventory = JSON.parse(zlib.gunzipSync(gitBlob('data/macro-foundation/current-membership-inventory.json.gz')));
const area = inventory.find(x => x.id === issueScope.area_scope.id);
if (!area || area.member_location_ids.length !== 125) throw new Error('Pinned area inventory does not match issue scope');
const index = JSON.parse(gitBlob('data/world-index.json'));
const current = new Map();
for (const relative of index.parts) {
  const partName = `data/${relative}`;
  const parsed = JSON.parse(gitBlob(partName));
  for (const feature of parsed.features) {
    const id = feature.id ?? feature.properties?.id;
    if (id && (ids.includes(id) || area.member_location_ids.includes(id))) {
      if (current.has(id)) throw new Error(`Duplicate immutable subject ${id}`);
      current.set(id, {feature, path: partName, sha256: createHash('sha256').update(gitBlob(partName)).digest('hex')});
    }
  }
}
if (ids.some(id => !current.has(id))) throw new Error('One or more issue subjects absent from pinned world-index parts');
const missingAreaSources = area.member_location_ids.filter(id => !sourceRows.has(id.split(':').at(-1)));
if (missingAreaSources.length) throw new Error(`Area roster IDs absent from retained source: ${missingAreaSources.length}`);

const expectedParents = new Map(issueScope.province_scopes.map(x => [x.id, x.full_province_locations]));
const parentCounts = new Map([...expectedParents.keys()].map(id => [id, 0]));
const rows = [];
for (const id of ids) {
  const entry = current.get(id);
  const feature = entry.feature;
  const props = feature.properties ?? {};
  const sourceId = id.split(':').at(-1);
  const upstream = sourceRows.get(sourceId);
  const parentId = props.parent_id;
  const parent = hierarchy.find(x => x.id === parentId);
  const metadata = props.metadata ?? {};
  if (!parentCounts.has(parentId)) throw new Error(`Unexpected parent for scoped unit ${id}: ${parentId}`);
  parentCounts.set(parentId, parentCounts.get(parentId) + 1);
  if (props.name !== upstream.properties.shapeName) throw new Error(`Name mismatch between retained source and baseline for ${id}`);
  if (metadata.source_id !== 'gb:CHN:ADM2' || metadata.reference_year !== '2017' || metadata.source_role !== 'County Level') throw new Error(`Source descriptor mismatch for ${id}`);
  if (metadata.original_id !== sourceId || upstream.properties.shapeType !== 'ADM2' || upstream.properties.shapeGroup !== 'CHN') throw new Error(`Source identity mismatch for ${id}`);
  const geom = upstream.geometry;
  if (!geom || !['Polygon', 'MultiPolygon'].includes(geom.type)) throw new Error(`Unsupported geometry for ${id}`);
  const polygons = geom.type === 'Polygon' ? [geom.coordinates] : geom.coordinates;
  let vertices = 0, ringCount = 0, closedRings = 0;
  let west = Infinity, south = Infinity, east = -Infinity, north = -Infinity;
  for (const polygon of polygons) for (const ring of polygon) {
    ringCount++;
    if (ring.length && JSON.stringify(ring[0]) === JSON.stringify(ring.at(-1))) closedRings++;
    for (const point of ring) {
      if (!Array.isArray(point) || point.length < 2 || !Number.isFinite(point[0]) || !Number.isFinite(point[1]) || Math.abs(point[0]) > 180 || Math.abs(point[1]) > 90) throw new Error(`Invalid coordinate range for ${id}`);
      vertices++;
      west = Math.min(west, point[0]); south = Math.min(south, point[1]); east = Math.max(east, point[0]); north = Math.max(north, point[1]);
    }
  }
  if (closedRings !== ringCount) throw new Error(`Open coordinate ring for ${id}`);
  rows.push({
    id, source_shape_id: sourceId, source_name: upstream.properties.shapeName,
    parent_id: parentId, parent_name: parent?.name ?? null, baseline_feature_path: entry.path,
    baseline_feature_file_sha256: entry.sha256,
    feature_geometry_type: geom.type, polygon_parts: polygons.length, rings: ringCount, vertices,
    bbox_lon_lat: [west, south, east, north], coordinate_range_and_ring_closure: 'passed',
    geometry_topology: 'not assessed by a topology engine',
    source_metadata: {reference_year: metadata.reference_year, role: metadata.source_role, type: metadata.administrative_level, parent_source_level: metadata.parent_source_level, hierarchy_source: metadata.hierarchy_source}
  });
}
for (const [id, count] of expectedParents) if (parentCounts.get(id) !== count) throw new Error(`Parent count mismatch for ${id}`);
const scopeSet = new Set(ids);
if (area.member_location_ids.filter(id => scopeSet.has(id)).length !== ids.length) throw new Error('Issue subjects are not a subset of the pinned Yunnan area inventory');

const result = {
  verification_version: 1,
  generated_at: '2026-10-05',
  baseline_commit: baseline,
  input_pins: {
    issue_scope: {path: `${owned}/scope.json`, sha256: fileHash(path.join(owned, 'scope.json'))},
    retained_geojson: {path: `${owned}/sources/geoboundaries-chn-adm2-2017.geojson`, bytes: sourceRaw.length, sha256: expectedSourceHash},
    geojson_lfs_pointer: {path: `${owned}/sources/geoboundaries-chn-adm2-2017.lfs-pointer.txt`, sha256: fileHash(path.join(owned, 'sources/geoboundaries-chn-adm2-2017.lfs-pointer.txt'))},
    source_metadata: {path: `${owned}/sources/geoboundaries-chn-adm2-metadata.json`, sha256: fileHash(path.join(owned, 'sources/geoboundaries-chn-adm2-metadata.json'))},
    source_citation_terms: {path: `${owned}/sources/geoboundaries-citation-and-use.txt`, sha256: fileHash(path.join(owned, 'sources/geoboundaries-citation-and-use.txt'))},
    world_index: {path: 'data/world-index.json', sha256: createHash('sha256').update(gitBlob('data/world-index.json')).digest('hex')},
    hierarchy: {path: 'data/hierarchy.json', sha256: createHash('sha256').update(gitBlob('data/hierarchy.json')).digest('hex')},
    membership_inventory: {path: 'data/macro-foundation/current-membership-inventory.json.gz', sha256: createHash('sha256').update(gitBlob('data/macro-foundation/current-membership-inventory.json.gz')).digest('hex')}
  },
  results: {
    scoped_ids: ids.length, unique_scoped_ids: new Set(ids).size,
    scope_ids_found_once_in_pinned_world_index: ids.length,
    scope_ids_matched_once_to_retained_geojson: rows.length,
    all_pinned_yunnan_inventory_ids_in_retained_geojson: area.member_location_ids.length,
    source_geojson_feature_count: source.features.length,
    scoped_parent_counts: Object.fromEntries([...parentCounts].sort()),
    scoped_rows: rows
  },
  limits: [
    'These checks establish exact identity joins and basic coordinate/ring structure only; they do not test self-intersection, polygon validity, inter-unit gaps/overlaps, island completeness, source-to-official boundary alignment, or territorial accuracy.',
    'The issue owns 40 of 125 Yunnan inventory members. Matching the remaining 85 IDs to the same source is a roster control only, not a semantic review of those units.',
    'The source includes no county-to-prefecture parent field or official administrative code. Current hierarchy parents were produced from a separate 2020 humanitarian/HDX source and cannot be independently verified from this 2017 file alone.'
  ]
};
fs.writeFileSync(path.join(owned, 'reproduction-results.json'), `${JSON.stringify(result, null, 2)}\n`);
console.log(JSON.stringify({scoped_ids: rows.length, source_count: source.features.length, all_area_roster_ids_found: area.member_location_ids.length, parents: Object.fromEntries([...parentCounts].sort()), result_path: `${owned}/reproduction-results.json`}, null, 2));

import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '../../..');
const baseline = 'c28077da970ae39550e5edea790a266b060d3de5';
const git = (...args) => execFileSync('git', ['-C', repo, ...args], {maxBuffer: 32 * 1024 ** 2});
const sha = raw => createHash('sha256').update(raw).digest('hex');
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
const digest = value => sha(Buffer.from(JSON.stringify(canonical(value)) + '\n'));
const demand = (condition, message) => { if (!condition) throw Error(message); };
const head = git('rev-parse', 'HEAD').toString().trim();
demand(fs.readFileSync(fileURLToPath(import.meta.url)).equals(git('show', head + ':' + path.relative(repo, fileURLToPath(import.meta.url)))), 'Unfrozen executing code');
const pins = [];
function read(name, expected) {
  const raw = git('show', baseline + ':' + name);
  demand(raw.length <= 32 * 1024 ** 2, 'Ordinary input too large');
  const tree = git('ls-tree', '-z', baseline, '--', name).toString();
  const match = /^(100644) blob ([a-f0-9]{40})\t([^\0]+)\0$/.exec(tree);
  demand(match && match[3] === name, 'Missing nonordinary immutable input');
  const pin = {path: name, bytes: raw.length, sha256: sha(raw), mode: match[1], git_blob_oid: match[2]};
  if (expected) for (const key of ['bytes', 'sha256', 'mode', 'git_blob_oid']) if (expected[key] !== undefined) demand(pin[key] === expected[key], 'Selected input drift: ' + name + ' ' + key);
  pins.push(pin);
  return raw;
}
const output = path.join(here, 'vintages/current-neighbor-bindings-001');
demand(!fs.existsSync(output), 'Output exists');
for (let p = path.dirname(output); p !== repo; p = path.dirname(p)) if (fs.existsSync(p)) demand(!fs.lstatSync(p).isSymbolicLink(), 'Symlink output parent');
const candidatePath = path.relative(repo, path.join(here, 'vintages/physical-restoration-001/original-component.json'));
const candidateRaw = git('show', head + ':' + candidatePath);
const candidate = JSON.parse(candidateRaw);
demand(digest(candidate) === 'acd61551d2dbc9b6925e6d8c2d17cb210a6dcf6f3d80bbbadb64951660e3b746', 'Original feature drift');
function bounds(geometry) {
  const box = [Infinity, Infinity, -Infinity, -Infinity];
  const visit = value => {
    if (Array.isArray(value) && value.length >= 2 && value.every(Number.isFinite)) {
      box[0] = Math.min(box[0], value[0]); box[1] = Math.min(box[1], value[1]);
      box[2] = Math.max(box[2], value[0]); box[3] = Math.max(box[3], value[1]);
    } else if (Array.isArray(value)) value.forEach(visit);
  };
  if (geometry.type === 'GeometryCollection') for (const member of geometry.geometries) {
    const b = bounds(member); if (b) {visit(b.slice(0, 2)); visit(b.slice(2));}
  } else visit(geometry.coordinates);
  return box.every(Number.isFinite) ? box : null;
}
const box = bounds(candidate.geometry);
const intersects = b => b && b[0] <= box[2] && b[2] >= box[0] && b[1] <= box[3] && b[3] >= box[1];
const certificateName = 'coordination/engineering/melanesia363-additive-delivery-20261010/selected-integration/current-f02-coordinate/certificate.json.gz';
const certificateRaw = read(certificateName, {bytes: 7515239, sha256: '23aef083ceeabff7d76e7da2a6d047e9dc30b40a3e9b03e122492c4d41c9cd7e'});
const decoded = gunzipSync(certificateRaw, {maxOutputLength: 32 * 1024 ** 2});
demand(decoded.length === 18414409, 'Wrong complete certificate size');
const certificate = JSON.parse(decoded);
const selection = JSON.parse(read('data/ownership-selection.json'));
const bank = JSON.parse(read(selection.selected_geography.path, selection.selected_geography));
const index = JSON.parse(read(bank.world_index.path, bank.world_index));
const selectedSources = [...bank.unchanged_files, ...bank.overrides.map(row => row.after ?? row)];
demand(certificate.inputs.length === index.parts.length && certificate.entries.length === 49625, 'Incomplete selected certificate');
demand(JSON.stringify(certificate.inputs.map(x => x.path).sort()) === JSON.stringify(index.parts.map(x => 'data/' + x).sort()), 'Certificate omits indexed parts');
demand(certificate.binding.release.id === selection.release_id && certificate.binding.release.footprints_sha256 === bank.footprints_sha256, 'Certificate reference differs');
for (const input of certificate.inputs) {
  demand(git('ls-tree', '-z', baseline, '--', input.path).toString() === input.source.mode + ' blob ' + input.source.git_blob_oid + '\t' + input.path + '\0', 'Certificate source changed: ' + input.path);
  const selected = selectedSources.find(row => row.path === input.path);
  demand(selected && selected.git_blob_oid === input.source.git_blob_oid && selected.sha256 === input.whole_body_sha256, 'Certificate is not current selected source');
}
const identities = new Set();
for (const row of certificate.entries) {
  demand(row.length === certificate.entry_fields.length && !identities.has(row[0]), 'Duplicate or malformed complete owner row');
  identities.add(row[0]);
}
const hits = certificate.entries.filter(row => row[9].some(intersects));
const targets = [];
const parts = new Map();
for (const row of hits) {
  if (!parts.has(row[4])) {
    const input = certificate.inputs.find(input => input.path === row[4]);
    parts.set(row[4], JSON.parse(read(row[4], input.source)).features);
  }
  const feature = parts.get(row[4])[row[5]];
  demand(feature.id === row[0] && feature.properties.parent_id === row[2] && digest(feature) === row[6] && digest(feature.geometry) === row[7], 'Actual whole candidate-neighbor feature differs');
  targets.push({certificate_entry: row, feature});
}
const sidecar = JSON.parse(read(selection.additive_release.path, selection.additive_release));
const base = structuredClone(selection); delete base.additive_release;
demand(JSON.stringify(canonical(base)) === JSON.stringify(canonical(sidecar.base_selection)), 'Additive base selection differs');
const ledger = JSON.parse(read(sidecar.logical_asset_map.ledger.path, sidecar.logical_asset_map.ledger));
const geometryRows = [];
function scan(value, locator) {
  if (!value || typeof value !== 'object') return;
  if (['Polygon', 'MultiPolygon', 'GeometryCollection', 'LineString', 'MultiLineString', 'Point', 'MultiPoint'].includes(value.type)) {
    const b = bounds(value); geometryRows.push({locator, bounds: b, candidate_bbox_intersects: intersects(b)}); return;
  }
  for (const [key, child] of Object.entries(value)) scan(child, locator + '/' + key);
}
scan(ledger.rows, '/rows'); scan(ledger.current_targets, '/current_targets');
demand(geometryRows.length > 0 && geometryRows.every(row => !row.candidate_bbox_intersects), 'Current additive geometry requires actual predicate');
const result = {baseline, execution_commit: head, component_id: candidate.id, candidate_bounds: box, complete_owner_rows: certificate.entries.length, complete_source_parts: certificate.inputs.length, complete_additive_geometry_records: geometryRows.length, candidate_neighbors: targets, additive_geometry_screen: geometryRows, inputs: pins, old_certificate_vintage: certificate.binding.release.id, actual_selection: selection, method: 'Complete-coordinate certificate for conservative exclusions; authenticate actual whole features for every hit and all current additive geometry fields.', limits: ['Bounding boxes are exclusions only. Prior exact whole-target and HUN-neighbor predicate results apply only after their whole-feature hashes match.', 'No native cell or selected continuous integration is established by this metadata proof.']};
demand(pins.reduce((sum, p) => sum + p.bytes, 0) + decoded.length < 128 * 1024 ** 2, 'Complete phase budget exceeded');
fs.mkdirSync(output);
fs.writeFileSync(path.join(output, 'result.json'), JSON.stringify(result) + '\n', {flag: 'wx'});
console.log(JSON.stringify({neighbors: targets.map(x => x.feature.id), complete_owner_rows: result.complete_owner_rows, additive_geometries: geometryRows.length, peak_rss_bytes: process.resourceUsage().maxRSS * 1024}));

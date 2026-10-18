#!/usr/bin/env node
// Sanitized, path-portable reconstruction of the retained HND/NIC contact
// adapter. It is not the original invocation receipt.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import zlib from 'node:zlib';
import crypto from 'node:crypto';

function arg(name) {
  const i = process.argv.indexOf(name);
  return i < 0 ? null : process.argv[i + 1] ?? null;
}
const packetPath = arg('--packet');
const fixtureRoot = arg('--fixture-root');
const helperPath = arg('--helper');
const latitudePath = arg('--latitudes');
if (!packetPath || !fixtureRoot || !helperPath || !latitudePath) {
  throw new Error('Usage: node held-row-diagnostic-repro.mjs --packet PACKET.json --fixture-root FIXTURES --helper native-grid.js --latitudes native-row-latitudes.f64le');
}

const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const packet = JSON.parse(fs.readFileSync(packetPath, 'utf8'));
const helperBytes = fs.readFileSync(helperPath);
if (sha(helperBytes) !== packet.input_provenance.native_helper_sha256) {
  throw new Error('Native helper SHA-256 does not match the packet pin');
}
const { nativePolygonIntervals, polygonParts } = await import(pathToFileURL(path.resolve(helperPath)).href);

const size = packet.input_provenance.size;
const latitudeBytes = fs.readFileSync(latitudePath);
const latitudePin = packet.input_provenance.native_helper_path && packet.actual_scope_outcomes.HND.source_evidence.native_contract.native_latitudes;
if (!latitudePin || latitudePin.decoded_bytes !== size * 8 ||
    latitudeBytes.length !== latitudePin.decoded_bytes || sha(latitudeBytes) !== latitudePin.decoded_sha256) {
  throw new Error('Normative latitude vector size or SHA-256 mismatch');
}
const latitudes = new Float64Array(size);
for (let i = 0; i < size; i++) latitudes[i] = latitudeBytes.readDoubleLE(i * 8);

const evidenceByCountry = new Map();
for (const item of packet.published_evidence.country_source_evidence) {
  const file = path.join(fixtureRoot, 'evidence', item.country, 'source-evidence.json');
  evidenceByCountry.set(item.country, JSON.parse(fs.readFileSync(file, 'utf8')));
}
const memo = new Map();
function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
  return JSON.stringify(value);
}
function familyId(sourceId) { return sourceId.split(':').slice(0, 3).join(':'); }
function sourcePin(evidence, family) {
  for (const group of [...evidence.families, ...evidence.territorial_exclusion_sources]) {
    if (group.source_id === family || familyId(group.source_id) === family) {
      const part = group.parts?.[0];
      if (part) return part;
    }
  }
  throw new Error(`No pinned source body in evidence for ${family}`);
}
function parseWhole(file) {
  if (memo.has(file)) return memo.get(file);
  const bytes = fs.readFileSync(file);
  const decoded = file.endsWith('.gz') ? zlib.gunzipSync(bytes) : bytes;
  const value = JSON.parse(decoded.toString('utf8'));
  if (value.type !== 'FeatureCollection' || !Array.isArray(value.features)) throw new Error(`Invalid FeatureCollection: ${path.basename(file)}`);
  const result = { bytes, decoded, features: value.features };
  memo.set(file, result);
  return result;
}
function sourceFile(sourcePath) {
  const basename = path.basename(sourcePath);
  if (!basename || basename === '.' || basename === path.sep) throw new Error('Invalid source basename');
  return path.join(fixtureRoot, 'payloads', basename);
}
function getFeature(sourceId, ordinal, evidence) {
  const family = familyId(sourceId);
  const pin = sourcePin(evidence, family);
  const file = sourceFile(pin.path);
  const whole = parseWhole(file);
  const feature = whole.features[ordinal];
  if (!feature) throw new Error(`Missing feature ordinal ${ordinal} in ${family}`);
  if (whole.bytes.length !== pin.bytes || sha(whole.bytes) !== pin.sha256 ||
      whole.decoded.length !== pin.decoded_bytes || sha(whole.decoded) !== pin.decoded_sha256) {
    throw new Error(`Whole source body mismatch for ${family}`);
  }
  const actualId = `gb:${feature.properties?.shapeGroup}:${feature.properties?.shapeType}:${feature.properties?.shapeID}`;
  if (actualId !== sourceId) throw new Error(`Source ID mismatch at ${family} ordinal ${ordinal}`);
  return { feature, file, whole };
}
function getFeatureById(sourceId, evidence) {
  const family = familyId(sourceId);
  const pin = sourcePin(evidence, family);
  const file = sourceFile(pin.path);
  const whole = parseWhole(file);
  const ordinal = whole.features.findIndex(f => `gb:${f.properties?.shapeGroup}:${f.properties?.shapeType}:${f.properties?.shapeID}` === sourceId);
  if (ordinal < 0) throw new Error(`Positive source feature not found: ${sourceId}`);
  return { ...getFeature(sourceId, ordinal, evidence), ordinal };
}
function relation(geometry, y, x) {
  const polygons = polygonParts(geometry).map(poly => poly.map(ring => Float64Array.from(ring.flat())));
  const scan = nativePolygonIntervals([{ index: 1, polygons }], { size, latitudes, rowStart: y, rowEnd: y + 1 });
  const interior = (scan.rows.get(y) || []).some(span => span.start <= x && x < span.end);
  const ties = scan.ties.filter(t => t.y === y && (Object.hasOwn(t, 'x') ? t.x === x : t.start <= x && x < t.end)).map(t => t.kind);
  return ties.length ? { relation: 'boundary', ties: [...new Set(ties)] } : { relation: interior ? 'interior' : 'outside', ties: [] };
}
function bodyReceipt(file, whole) {
  return { source_path: path.basename(file), stored_bytes: whole.bytes.length, decoded_bytes: whole.decoded.length,
    stored_sha256: sha(whole.bytes), decoded_sha256: sha(whole.decoded), stored_encoding: file.endsWith('.gz') ? 'gzip' : 'uncompressed-materialization' };
}

const results = [];
for (const row of packet.rows) {
  const key = row.original_key;
  const country = row.owner.source_id.split(':')[1];
  const evidence = evidenceByCountry.get(country);
  if (!evidence) throw new Error(`Missing source evidence for ${country}`);
  const target = evidence.targets.find(t => t.pixelIndex === key.owner_index && t.target_id === row.owner.source_id);
  if (!target) throw new Error(`Target binding mismatch for ${country}/${key.owner_index}`);
  const y = key.y, x = key.x;
  const lon = (360 * x + 180 - 180 * size) / size;
  const positiveBody = getFeatureById(row.owner.source_id, evidence);
  const exclusions = [];
  for (const [index, exclusion] of target.territorial_exclusions.entries()) {
    if (exclusion.type === 'Polygon' || exclusion.type === 'MultiPolygon') {
      exclusions.push({ source_index: index, source_id: 'inline-archive-only',
        geometry_sha256: sha(Buffer.from(`${canonical(exclusion)}\n`)), relation: relation(exclusion, y, x) });
      continue;
    }
    const body = getFeature(exclusion.source_id, exclusion.feature_ordinal, evidence);
    const geometrySha = sha(Buffer.from(`${canonical(body.feature.geometry)}\n`));
    if (geometrySha !== exclusion.geometry_sha256) throw new Error(`Negative geometry SHA mismatch for ${exclusion.source_id}`);
    exclusions.push({ negative_ordinal: exclusion.negative_ordinal, source_id: exclusion.source_id,
      feature_ordinal: exclusion.feature_ordinal, feature_id: body.feature.properties.shapeID,
      ...bodyReceipt(body.file, body.whole), geometry_sha256: geometrySha, relation: relation(body.feature.geometry, y, x) });
  }
  results.push({ country, owner: key.owner_index, target: row.owner.source_id,
    cell: { y, x, longitude: lon, latitude: latitudes[y] },
    positive: relation(positiveBody.feature.geometry, y, x),
    derived_base_geometry_contact: relation(target.base_geometry, y, x),
    positive_geometry_sha256: sha(Buffer.from(`${canonical(positiveBody.feature.geometry)}\n`)),
    derived_base_geometry_sha256: sha(Buffer.from(`${canonical(target.base_geometry)}\n`)),
    positive_source: { source_id: row.owner.source_id, name: positiveBody.feature.properties.shapeName,
      feature_ordinal: positiveBody.ordinal, ...bodyReceipt(positiveBody.file, positiveBody.whole) },
    exclusions, source_evidence_commit: evidence.catalogue.commit,
    diagnostic_rule_sha256: packet.actual_scope_outcomes[country].diagnostic.rule_sha256,
    limitations: 'Centre contact under the authenticated existing native scan rule only; embedded target base geometry is reported separately from the exact pinned complete source feature. Not a legal, ownership, boundary, or hold-disposition conclusion.' });
}
process.stdout.write(JSON.stringify({ method: packet.input_provenance.method, size,
  latitude_bytes: latitudeBytes.length, results }, null, 2) + '\n');

import fs from 'node:fs';
import crypto from 'node:crypto';

const prefix = 'data/regional-review/regional-review-5cf69eed7fdff0b5';
const fullSourcePath = process.argv[2];
if (!fullSourcePath) {
  throw new Error('Pass a locally restored copy of the pinned full geoBoundaries source.');
}
const expected = {
  bytes: 120489189,
  sha256: '74012237384e53061aa63b6e20b9be24f94facfe615b52bbe72e62a81fa68ff0',
  features: 2327,
};
const rawBytes = fs.readFileSync(fullSourcePath);
const digest = crypto.createHash('sha256').update(rawBytes).digest('hex');
if (rawBytes.length !== expected.bytes || digest !== expected.sha256) {
  throw new Error(`Pinned source mismatch: bytes=${rawBytes.length}, sha256=${digest}`);
}
const raw = JSON.parse(rawBytes.toString('utf8'));
if (!Array.isArray(raw.features) || raw.features.length !== expected.features) {
  throw new Error(`Expected ${expected.features} pinned source features.`);
}
const inventory = JSON.parse(fs.readFileSync(`${prefix}/reproduction/scope-inventory.run-1.json`, 'utf8'));
const ids = inventory.subjects
  .filter((subject) => subject.source_id === 'gb:RUS:ADM2')
  .map((subject) => subject.source_original_id);
if (ids.length !== 185 || new Set(ids).size !== 185) {
  throw new Error('The pinned issue must provide exactly 185 unique geoBoundaries source IDs.');
}
const wanted = new Set(ids);
const features = raw.features.filter((feature) => wanted.has(feature.properties.shapeID));
const found = new Set(features.map((feature) => feature.properties.shapeID));
const missing = ids.filter((id) => !found.has(id));
if (missing.length || features.length !== ids.length) {
  throw new Error(`Scoped source mismatch: found=${features.length}, missing=${missing.length}`);
}
const subset = { type: raw.type, crs: raw.crs, features };
const output = `${prefix}/source/geoboundaries-rus-adm2-2017-scope-185-original-features.geojson`;
fs.writeFileSync(output, JSON.stringify(subset));
const rows = features.map((feature) => {
  const featureHash = crypto.createHash('sha256').update(JSON.stringify(feature)).digest('hex');
  return `${feature.properties.shapeID}\t${feature.properties.shapeName}\t${featureHash}`;
}).sort((a, b) => a.localeCompare(b));
fs.writeFileSync(`${prefix}/reproduction/geoboundaries-feature-hashes.tsv`, `${rows.join('\n')}\n`);
const baseIds = [...new Set(inventory.subjects
  .filter((subject) => subject.source_id.startsWith('resolve:') || subject.source_id.startsWith('natural-earth:'))
  .flatMap((subject) => subject.source_member_ids || [])
  .filter((id) => id.startsWith('gb:RUS:ADM2:'))
  .map((id) => id.slice('gb:RUS:ADM2:'.length)))].sort();
if (baseIds.length !== 8 || baseIds.some((id) => wanted.has(id))) {
  throw new Error('Expected exactly eight non-scoped source-member districts for physical adaptations.');
}
const wantedBase = new Set(baseIds);
const baseFeatures = raw.features.filter((feature) => wantedBase.has(feature.properties.shapeID));
if (baseFeatures.length !== baseIds.length) {
  throw new Error(`Supporting adaptation base mismatch: found=${baseFeatures.length}, expected=${baseIds.length}`);
}
const baseOutput = `${prefix}/source/geoboundaries-rus-adm2-2017-adaptation-base-8-original-features.geojson`;
fs.writeFileSync(baseOutput, JSON.stringify({ type: raw.type, crs: raw.crs, features: baseFeatures }));
const baseRows = baseFeatures.map((feature) => {
  const featureHash = crypto.createHash('sha256').update(JSON.stringify(feature)).digest('hex');
  return `${feature.properties.shapeID}\t${feature.properties.shapeName}\t${featureHash}`;
}).sort((a, b) => a.localeCompare(b));
fs.writeFileSync(`${prefix}/reproduction/geoboundaries-adaptation-base-hashes.tsv`, `${baseRows.join('\n')}\n`);
console.log(JSON.stringify({
  full_source_bytes: rawBytes.length,
  full_source_sha256: digest,
  full_source_features: raw.features.length,
  scoped_feature_count: features.length,
  scoped_output_sha256: crypto.createHash('sha256').update(fs.readFileSync(output)).digest('hex'),
  feature_hash_manifest_sha256: crypto.createHash('sha256').update(fs.readFileSync(`${prefix}/reproduction/geoboundaries-feature-hashes.tsv`)).digest('hex'),
  supporting_adaptation_base_feature_count: baseFeatures.length,
  supporting_adaptation_base_output_sha256: crypto.createHash('sha256').update(fs.readFileSync(baseOutput)).digest('hex'),
  supporting_adaptation_base_hash_manifest_sha256: crypto.createHash('sha256').update(fs.readFileSync(`${prefix}/reproduction/geoboundaries-adaptation-base-hashes.tsv`)).digest('hex'),
}, null, 2));

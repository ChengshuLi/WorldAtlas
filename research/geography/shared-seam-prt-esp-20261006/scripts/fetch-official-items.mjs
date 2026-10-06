#!/usr/bin/env node

// Preserve byte-exact public official OGC API responses. The IGN bbox query is
// used only to discover complete feature IDs; each returned feature is then
// fetched independently by its native item route.
import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const output = path.resolve(process.argv[2] ?? '');
if (!process.argv[2]) throw new Error('usage: fetch-official-items.mjs NEW_OUTPUT_DIRECTORY');
await mkdir(output, { recursive: false });
const records = [];

async function preserve(id, url, role) {
  const response = await fetch(url, {
    headers: { accept: 'application/geo+json, application/json;q=0.9', 'accept-encoding': 'identity', 'user-agent': 'WorldAtlas-source-evidence/1' },
    redirect: 'follow'
  });
  if (!response.ok) throw new Error(`${id}: HTTP ${response.status}`);
  const bytes = Buffer.from(await response.arrayBuffer());
  if (bytes.byteLength === 0 || bytes.byteLength > 32 * 1024 * 1024) throw new Error(`${id}: response size ${bytes.byteLength} exceeds bounded source-item policy`);
  const filename = `${id}.json`;
  await writeFile(path.join(output, filename), bytes, { flag: 'wx' });
  const record = {
    id, role, request_url: url, final_response_url: response.url,
    retrieved_at: new Date().toISOString(), status: response.status,
    content_type: response.headers.get('content-type'),
    content_length_header: response.headers.get('content-length'),
    content_encoding_header: response.headers.get('content-encoding'),
    etag: response.headers.get('etag'), last_modified: response.headers.get('last-modified'),
    bytes: bytes.byteLength, sha256: createHash('sha256').update(bytes).digest('hex'), filename
  };
  records.push(record);
  return JSON.parse(bytes.toString('utf8'));
}

const dgt = 'https://ogcapi.dgterritorio.gov.pt';
const ign = 'https://api-features.ign.es';
await preserve('dgt-municipios-collection', `${dgt}/collections/municipios?f=json`, 'DGT CAOP2025 collection metadata');
await preserve('dgt-municipios-queryables', `${dgt}/collections/municipios/queryables?f=json`, 'DGT CAOP2025 queryables');
for (const [id, nativeId] of [['nisa','1212'],['idanha-a-nova','0505'],['castelo-branco','0502'],['vila-velha-de-rodao','0511']]) {
  const item = await preserve(`dgt-municipios-${id}`, `${dgt}/collections/municipios/items/${nativeId}?f=json`, 'complete CAOP2025 native municipality item');
  const feature = item.features?.[0] ?? item;
  if (!feature.geometry || !feature.properties) throw new Error(`DGT ${nativeId} was not a complete geometry item`);
}

await preserve('ign-administrativeboundary-collection', `${ign}/collections/administrativeboundary?f=json`, 'IGN administrativeboundary collection metadata');
await preserve('ign-administrativeboundary-queryables', `${ign}/collections/administrativeboundary/queryables?f=json`, 'IGN administrativeboundary queryables');
const bboxURL = `${ign}/collections/administrativeboundary/items?bbox=-7.55,39.63,-6.85,40.07&limit=1000&f=json`;
const discovery = await preserve('ign-bbox-discovery-only', bboxURL, 'bbox-selected complete-feature discovery response; not a national source file');
const features = discovery.features ?? [];
if (!Array.isArray(features) || features.length === 0) throw new Error('IGN bbox discovery returned no features');
const ids = [...new Set(features.map(feature => String(feature.id ?? feature.properties?.gid)).filter(value => /^\d+$/.test(value)))].sort((a,b) => Number(a)-Number(b));
if (ids.length !== features.length) throw new Error('IGN bbox discovery had missing or duplicate native feature IDs');
for (const nativeId of ids) {
  const item = await preserve(`ign-administrativeboundary-${nativeId}`, `${ign}/collections/administrativeboundary/items/${nativeId}?f=json`, 'complete IGN native administrative-boundary item selected by bbox discovery');
  const feature = item.features?.[0] ?? item;
  if (!feature.properties || !Object.hasOwn(feature, 'geometry')) throw new Error(`IGN ${nativeId} lacks a complete feature item`);
}

const receipt = {
  version: 1,
  status: 'complete byte-exact public GET response preservation',
  bbox_interpretation: 'bbox selects which complete feature records are returned; it does not clip feature geometries',
  national_file_claim: false,
  records
};
await writeFile(path.join(output, 'response-receipt.json'), `${JSON.stringify(receipt, null, 2)}\n`, { flag: 'wx' });
process.stdout.write(`${JSON.stringify({ saved: records.length, output, discovery_features: ids.length, discovery_ids: ids, record_count: records.length }, null, 2)}\n`);

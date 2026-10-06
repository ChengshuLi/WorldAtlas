#!/usr/bin/env node
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';

const root = new URL('../sources/official-api-responses/', import.meta.url);
const discoveryDir = new URL('ign-administrativeunit-name-discovery/', root);
const itemDir = new URL('ign-administrativeunit-native-items/', root);
const names = [
  'Carbajo', 'Herrera de Alcántara', 'Cedillo', 'Santiago de Alcántara',
  'Alcántara', 'Zarza la Mayor', 'Cilleros', 'Membrío',
];

async function get(url) {
  const response = await fetch(url, {
    headers: {accept: 'application/geo+json, application/json', 'accept-encoding': 'identity'},
    signal: AbortSignal.timeout(60_000),
  });
  const bytes = Buffer.from(await response.arrayBuffer());
  return {
    bytes,
    receipt: {
      request_url: url,
      final_response_url: response.url,
      retrieved_at: new Date().toISOString(),
      http_status: response.status,
      content_type: response.headers.get('content-type'),
      content_length_header: response.headers.get('content-length'),
      content_encoding_header: response.headers.get('content-encoding'),
      etag: response.headers.get('etag'),
      last_modified: response.headers.get('last-modified'),
      bytes: bytes.length,
      sha256: createHash('sha256').update(bytes).digest('hex'),
    },
  };
}

async function save(directory, name, result) {
  const dataPath = new URL(`${name}.json`, directory);
  await fs.writeFile(dataPath, result.bytes, {flag: 'wx'});
  await fs.writeFile(new URL(`${name}-receipt.json`, directory), `${JSON.stringify(result.receipt, null, 2)}\n`, {flag: 'wx'});
  return {path: decodeURIComponent(dataPath.pathname.split('/').slice(-2).join('/')), ...result.receipt};
}

await fs.mkdir(discoveryDir, {recursive: true});
await fs.mkdir(itemDir, {recursive: true});
const records = [];
for (const name of names) {
  const params = new URLSearchParams({nameunit: name, limit: '10', f: 'json'});
  const queryUrl = `https://api-features.ign.es/collections/administrativeunit/items?${params}`;
  const query = await get(queryUrl);
  if (query.receipt.http_status !== 200) throw new Error(`Name query failed (${query.receipt.http_status}): ${name}`);
  const collection = JSON.parse(query.bytes.toString('utf8'));
  if (collection.numberMatched !== 1 || collection.numberReturned !== 1 || collection.features?.length !== 1) {
    throw new Error(`Name query did not identify exactly one full item: ${name}`);
  }
  const discovered = collection.features[0];
  if (discovered.properties?.nameunit !== name || discovered.properties?.country !== 'ES' || discovered.properties?.nationallevelname !== 'Municipio') {
    throw new Error(`Unexpected administrative identity returned for ${name}`);
  }
  const gid = String(discovered.id ?? discovered.properties?.gid);
  if (!/^\d+$/.test(gid)) throw new Error(`Missing native IGN gid for ${name}`);
  const queryRecord = await save(discoveryDir, `ign-administrativeunit-name-${gid}`, query);

  const itemUrl = `https://api-features.ign.es/collections/administrativeunit/items/${gid}?f=json`;
  const item = await get(itemUrl);
  if (item.receipt.http_status !== 200) throw new Error(`Native item failed (${item.receipt.http_status}): ${gid}`);
  const feature = JSON.parse(item.bytes.toString('utf8'));
  if (feature.type !== 'Feature' || String(feature.id ?? feature.properties?.gid) !== gid ||
      feature.properties?.nameunit !== name || feature.properties?.country !== 'ES' || !feature.geometry) {
    throw new Error(`Native item identity or full polygon geometry mismatch: ${gid}`);
  }
  const itemRecord = await save(itemDir, `ign-administrativeunit-${gid}`, item);
  records.push({gid, nameunit: name, country: feature.properties.country, nationallevelname: feature.properties.nationallevelname,
    geometry_type: feature.geometry.type, query_response: queryRecord, native_item_response: itemRecord});
}

const receipt = {
  version: 1,
  status: 'complete: eight distinct full native administrativeunit polygon items',
  collection: 'administrativeunit',
  collection_storage_crs: 'OGC:CRS84 as declared in collection metadata; GeoJSON coordinate order longitude, latitude',
  discovery_policy: 'Exact nameunit query selects the complete item; no bbox, clipping, simplification, reprojection or geometry modification.',
  records,
};
await fs.writeFile(new URL('response-receipt.json', itemDir), `${JSON.stringify(receipt, null, 2)}\n`, {flag: 'wx'});
console.log(JSON.stringify({status: receipt.status, items: records.map(({gid, nameunit}) => ({gid, nameunit}))}));

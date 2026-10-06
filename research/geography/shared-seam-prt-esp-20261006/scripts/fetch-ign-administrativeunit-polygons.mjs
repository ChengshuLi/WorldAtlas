#!/usr/bin/env node
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';

const root = new URL('../sources/official-api-responses/', import.meta.url);
const discoveryDir = new URL('ign-administrativeunit-name-discovery/', root);
const nativeCodeDiscoveryDir = new URL('ign-administrativeunit-nationalcode-discovery/', root);
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

async function existing(directory, prefix) {
  for (const filename of await fs.readdir(directory)) {
    if (!filename.startsWith(prefix) || !filename.endsWith('.json') || filename.endsWith('-receipt.json')) continue;
    const dataPath = new URL(filename, directory);
    const receiptPath = new URL(filename.replace(/\.json$/, '-receipt.json'), directory);
    try {
      const bytes = await fs.readFile(dataPath);
      const receipt = JSON.parse(await fs.readFile(receiptPath, 'utf8'));
      if (receipt.sha256 === createHash('sha256').update(bytes).digest('hex') && receipt.bytes === bytes.length) {
        return {bytes, receipt};
      }
    } catch {}
  }
  return null;
}

async function existingName(directory, expectedName) {
  for (const filename of await fs.readdir(directory)) {
    if (!filename.startsWith('ign-administrativeunit-name-') || !filename.endsWith('.json') || filename.endsWith('-receipt.json')) continue;
    const dataPath = new URL(filename, directory);
    const receiptPath = new URL(filename.replace(/\.json$/, '-receipt.json'), directory);
    try {
      const bytes = await fs.readFile(dataPath);
      const receipt = JSON.parse(await fs.readFile(receiptPath, 'utf8'));
      if (receipt.sha256 !== createHash('sha256').update(bytes).digest('hex') || receipt.bytes !== bytes.length) continue;
      const collection = JSON.parse(bytes.toString('utf8'));
      const queryName = new URL(receipt.request_url).searchParams.get('nameunit');
      if (queryName === expectedName || collection.features?.some(feature => feature.properties?.nameunit === expectedName)) return {bytes, receipt, filename};
    } catch {}
  }
  return null;
}

async function existingRootResponse(filename) {
  const dataUrl = new URL(filename, root);
  const receiptUrl = new URL(filename.replace(/\.json$/, '-receipt.json'), root);
  try {
    const bytes = await fs.readFile(dataUrl);
    const receipt = JSON.parse(await fs.readFile(receiptUrl, 'utf8'));
    if (receipt.sha256 === createHash('sha256').update(bytes).digest('hex') && receipt.bytes === bytes.length) {
      return {bytes, receipt, filename};
    }
  } catch {}
  return null;
}

await fs.mkdir(discoveryDir, {recursive: true});
await fs.mkdir(nativeCodeDiscoveryDir, {recursive: true});
await fs.mkdir(itemDir, {recursive: true});
const records = [];
for (const name of names) {
  const params = new URLSearchParams({nameunit: name, limit: '10', f: 'json'});
  const queryUrl = `https://api-features.ign.es/collections/administrativeunit/items?${params}`;
  const nameQuery = await existingName(discoveryDir, name) ?? await get(queryUrl);
  if (nameQuery.receipt.http_status !== 200) throw new Error(`Name query failed (${nameQuery.receipt.http_status}): ${name}`);
  const collection = JSON.parse(nameQuery.bytes.toString('utf8'));
  let query = nameQuery;
  let queryRecord;
  let nameQueryRecord;
  let codeQueryRecord;
  let resolution = 'unique complete native feature by exact nameunit query';
  if (collection.numberMatched === 0 && collection.numberReturned === 0 && collection.features?.length === 0) {
    nameQueryRecord = nameQuery.filename
      ? {path: `ign-administrativeunit-name-discovery/${nameQuery.filename}`, ...nameQuery.receipt}
      : (await existing(discoveryDir, 'ign-administrativeunit-no-match-6.json'))
        ? {path: 'ign-administrativeunit-name-discovery/ign-administrativeunit-no-match-6.json', ...nameQuery.receipt}
        : await save(discoveryDir, `ign-administrativeunit-no-match-${records.length + 1}`, nameQuery);
    const boundaryFiles = (await fs.readdir(new URL('ign-native-items/', root))).filter(filename => filename.endsWith('.json') && !filename.endsWith('-receipt.json'));
    let borderRecord;
    for (const filename of boundaryFiles) {
      const candidate = JSON.parse(await fs.readFile(new URL(filename, new URL('ign-native-items/', root)), 'utf8'));
      if (candidate.properties?.name_boundary?.split('#', 1)[0] === name) { borderRecord = candidate; break; }
    }
    const codeMatch = borderRecord?.properties?.nationalcode?.match(/^M(\d+)M/);
    if (!codeMatch) {
      records.push({nameunit: name, resolution: 'no exact nameunit match and no source nationalcode crosswalk', name_query_response: nameQueryRecord, query_response: nameQueryRecord, native_item_response: null});
      continue;
    }
    const nationalcode = codeMatch[1];
    const nativeCodeQueryUrl = `https://api-features.ign.es/collections/administrativeunit/items?nationalcode=${nationalcode}&limit=10&f=json`;
    query = await existingRootResponse('ign-administrativeunit-nationalcode-zarza-discovery.json') ?? await existing(nativeCodeDiscoveryDir, `ign-administrativeunit-nationalcode-${nationalcode}.json`) ?? await get(nativeCodeQueryUrl);
    if (query.receipt.http_status !== 200) throw new Error(`Native-code query failed (${query.receipt.http_status}): ${name}`);
    const nativeCodeCollection = JSON.parse(query.bytes.toString('utf8'));
    if (nativeCodeCollection.numberMatched !== 1 || nativeCodeCollection.numberReturned !== 1 || nativeCodeCollection.features?.length !== 1) {
      const codeQueryRecord = await save(nativeCodeDiscoveryDir, `ign-administrativeunit-nationalcode-${nationalcode}`, query);
      records.push({nameunit: name, resolution: 'native code returned no unique municipality feature', spanish_nationalcode: nationalcode, name_query_response: nameQueryRecord, query_response: codeQueryRecord, native_item_response: null});
      continue;
    }
    const candidate = nativeCodeCollection.features[0];
    if (candidate.properties?.nameunit !== name || candidate.properties?.country !== 'ES' || candidate.properties?.nationallevelname !== 'Municipio' || candidate.properties?.nationalcode !== nationalcode) {
      throw new Error(`Spanish line nationalcode did not map to the named IGN municipality: ${name}`);
    }
    const codeQueryFilename = query.filename;
    codeQueryRecord = codeQueryFilename
      ? {path: codeQueryFilename.startsWith('ign-administrativeunit-nationalcode-discovery/') ? codeQueryFilename : codeQueryFilename, ...query.receipt}
      : await save(nativeCodeDiscoveryDir, `ign-administrativeunit-nationalcode-${nationalcode}`, query);
    queryRecord = codeQueryRecord;
    query = nameQuery;
    collection.features = [candidate];
    resolution = 'unique complete native feature by nationalcode crosswalk; exact nameunit query returned zero';
  }
  if (collection.numberMatched !== 1 || collection.numberReturned !== 1 || collection.features?.length !== 1) {
    const queryRecord = await save(discoveryDir, `ign-administrativeunit-ambiguous-${records.length + 1}`, query);
    records.push({nameunit: name, resolution: 'query returned zero or multiple feature identities', query_response: queryRecord,
      candidates: collection.features?.map(feature => ({id: feature.id, nameunit: feature.properties?.nameunit, nationallevelname: feature.properties?.nationallevelname, country: feature.properties?.country})) ?? [], native_item_response: null});
    continue;
  }
  const discovered = collection.features[0];
  if (discovered.properties?.nameunit !== name || discovered.properties?.country !== 'ES' || discovered.properties?.nationallevelname !== 'Municipio') {
    throw new Error(`Unexpected administrative identity returned for ${name}`);
  }
  const gid = String(discovered.id ?? discovered.properties?.gid);
  if (!/^\d+$/.test(gid)) throw new Error(`Missing native IGN gid for ${name}`);
  if (!queryRecord) {
    const queryFilename = nameQuery.filename ?? (await fs.readdir(discoveryDir)).find(filename => filename.startsWith(`ign-administrativeunit-name-${gid}.json`));
    queryRecord = queryFilename
      ? {path: `ign-administrativeunit-name-discovery/${queryFilename}`, ...query.receipt}
      : await save(discoveryDir, `ign-administrativeunit-name-${gid}`, query);
  }

  const itemUrl = `https://api-features.ign.es/collections/administrativeunit/items/${gid}?f=json`;
  const item = await existing(itemDir, `ign-administrativeunit-${gid}.json`) ?? await get(itemUrl);
  if (item.receipt.http_status !== 200) throw new Error(`Native item failed (${item.receipt.http_status}): ${gid}`);
  const feature = JSON.parse(item.bytes.toString('utf8'));
  if (feature.type !== 'Feature' || String(feature.id ?? feature.properties?.gid) !== gid ||
      feature.properties?.nameunit !== name || feature.properties?.country !== 'ES' || !feature.geometry) {
    throw new Error(`Native item identity or full polygon geometry mismatch: ${gid}`);
  }
  const itemFilename = (await fs.readdir(itemDir)).find(filename => filename === `ign-administrativeunit-${gid}.json`);
  const itemRecord = itemFilename
    ? {path: `ign-administrativeunit-native-items/${itemFilename}`, ...item.receipt}
    : await save(itemDir, `ign-administrativeunit-${gid}`, item);
  records.push({gid, nameunit: name, resolution, country: feature.properties.country, nationallevelname: feature.properties.nationallevelname,
    geometry_type: feature.geometry.type, query_response: queryRecord, name_query_response: nameQueryRecord, code_query_response: codeQueryRecord,
    native_item_response: itemRecord});
}

const receipt = {
  version: 1,
  status: 'complete query audit; item availability is recorded separately for each requested municipality',
  collection: 'administrativeunit',
  requested_names: names,
  returned_native_item_count: records.filter(record => record.native_item_response !== null).length,
  collection_storage_crs: 'OGC:CRS84 as declared in collection metadata; GeoJSON coordinate order longitude, latitude',
  discovery_policy: 'Exact nameunit queries select features; if a line-item name query returns zero, its exact Spanish nationalcode prefix is queried and crosschecked against country, municipality level, name and code. Direct item routes return complete feature geometries. No bbox, clipping, simplification, reprojection or geometry modification.',
  records,
};
await fs.writeFile(new URL('response-receipt.json', itemDir), `${JSON.stringify(receipt, null, 2)}\n`);
console.log(JSON.stringify({status: receipt.status, items: records.map(({gid, nameunit}) => ({gid, nameunit}))}));

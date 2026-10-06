#!/usr/bin/env node

// Preserve full IGN-native items for every Portugal municipal-border line in
// the bounded discovery response, the Spain country-level record, and one
// interior-only negative control.
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

const [discoveryPathArg, outputArg] = process.argv.slice(2);
if (!discoveryPathArg || !outputArg) throw new Error('usage: fetch-selected-ign-items.mjs DISCOVERY_JSON NEW_OUTPUT_DIRECTORY');
const discoveryPath = path.resolve(discoveryPathArg);
const output = path.resolve(outputArg);
const discoveryBytes = await readFile(discoveryPath);
const discovery = JSON.parse(discoveryBytes);
const discoverySha = createHash('sha256').update(discoveryBytes).digest('hex');
const features = new Map((discovery.features ?? []).map(feature => [String(feature.id ?? feature.properties?.gid), feature]));
const selected = [
  { id: '5665057', role: 'municipal Portugal border item: Carbajo#Portugal' },
  { id: '5666602', role: 'municipal Portugal border item: Herrera de Alcántara#Portugal' },
  { id: '5674903', role: 'municipal Portugal border item: Cedillo#Portugal' },
  { id: '5680275', role: 'municipal Portugal border item: Santiago de Alcántara#Portugal' },
  { id: '5684705', role: 'municipal Portugal border item: Alcántara#Portugal' },
  { id: '5686837', role: 'municipal Portugal border item: Zarza la Mayor#Portugal' },
  { id: '5688358', role: 'municipal Portugal border item: Cilleros#Portugal' },
  { id: '5690193', role: 'municipal Portugal border item: Membrío#Portugal' },
  { id: '5702440', role: 'national-level Spain#Portugal item; legalstatus unpopulated in discovery' },
  { id: '5673087', role: 'interior-only Brozas#Villa del Rey negative control' }
];
for (const item of selected) if (!features.has(item.id)) throw new Error(`selected item ${item.id} absent from retained discovery source`);
await mkdir(output, { recursive: false });
const records = [];
const receiptPath = path.join(output, 'response-receipt.json');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function checkpoint(status, error) {
  await writeFile(receiptPath, `${JSON.stringify({ version: 1, status, discovery_sha256: discoverySha, bbox_interpretation: 'candidate selection only; direct native item routes below preserve full source feature responses', national_file_claim: false, ...(error ? { error } : {}), records }, null, 2)}\n`);
}
for (const item of selected) {
  const url = `https://api-features.ign.es/collections/administrativeboundary/items/${item.id}?f=json`;
  let response;
  for (let attempt = 0; attempt < 4; attempt++) {
    try {
      response = await fetch(url, { headers: { accept: 'application/geo+json, application/json;q=0.9', 'accept-encoding': 'identity', 'user-agent': 'WorldAtlas-source-evidence/1' }, redirect: 'follow', signal: AbortSignal.timeout(45000) });
      if (response.ok || response.status < 500 && response.status !== 429) break;
    } catch (error) { if (attempt === 3) throw new Error(`${item.id}: ${error.message}`); }
    if (attempt < 3) await delay(1000 * (2 ** attempt));
  }
  if (!response?.ok) {
    await checkpoint('partial', `${item.id}: HTTP ${response?.status ?? 'unavailable'} after retries`);
    throw new Error(`${item.id}: HTTP ${response?.status ?? 'unavailable'} after retries`);
  }
  const bytes = Buffer.from(await response.arrayBuffer());
  if (!bytes.length || bytes.length > 32 * 1024 * 1024) throw new Error(`${item.id}: response outside per-file evidence bounds`);
  const payload = JSON.parse(bytes.toString('utf8'));
  const feature = payload.features?.[0] ?? payload;
  if (!feature.properties || !Object.hasOwn(feature, 'geometry')) throw new Error(`${item.id}: response is not a complete feature item`);
  const filename = `ign-administrativeboundary-${item.id}.json`;
  await writeFile(path.join(output, filename), bytes, { flag: 'wx' });
  records.push({
    native_id: item.id, role: item.role, request_url: url, final_response_url: response.url,
    retrieved_at: new Date().toISOString(), http_status: response.status,
    content_type: response.headers.get('content-type'), content_length_header: response.headers.get('content-length'),
    content_encoding_header: response.headers.get('content-encoding'), etag: response.headers.get('etag'),
    last_modified: response.headers.get('last-modified'), bytes: bytes.length,
    sha256: createHash('sha256').update(bytes).digest('hex'), filename,
    properties: feature.properties,
    geometry_type: feature.geometry?.type ?? null,
    geometry_is_null: feature.geometry === null
  });
  await checkpoint('in-progress');
}
await checkpoint('complete: ten full native items plus the separately preserved discovery response');
process.stdout.write(`${JSON.stringify({ saved_items: records.length, discovery_sha256: discoverySha, output }, null, 2)}\n`);

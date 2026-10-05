import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const sources = [
  {
    year: 2018,
    layer: 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2018/MapServer/84',
  },
  {
    year: 2025,
    layer: 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/39',
  },
];
const fields = 'GEOID,STATE,COUNTY,NAME,BASENAME,LSADC,FUNCSTAT,COUNTYNS,AREALAND,AREAWATER';
for (const source of sources) {
  const metadataUrl = new URL(source.layer);
  metadataUrl.searchParams.set('f', 'pjson');
  const metadataResponse = await fetch(metadataUrl);
  if (!metadataResponse.ok) throw new Error(`${source.year} layer metadata failed: ${metadataResponse.status}`);
  const metadataBytes = Buffer.from(await metadataResponse.arrayBuffer());
  const metadata = JSON.parse(metadataBytes);
  if (!metadata.description?.includes(`${source.year === 2018 ? 'January 1, 2018' : 'January 1, 2025'} vintage`)) {
    throw new Error(`${source.year} service vintage did not match the expected date`);
  }
  const queryUrl = new URL(`${source.layer}/query`);
  queryUrl.searchParams.set('where', "STATE = '48'");
  queryUrl.searchParams.set('outFields', fields);
  queryUrl.searchParams.set('returnGeometry', 'true');
  queryUrl.searchParams.set('outSR', '4326');
  queryUrl.searchParams.set('f', 'geojson');
  const queryResponse = await fetch(queryUrl);
  if (!queryResponse.ok) throw new Error(`${source.year} Texas county query failed: ${queryResponse.status}`);
  const queryBytes = Buffer.from(await queryResponse.arrayBuffer());
  const collection = JSON.parse(queryBytes);
  if (collection.type !== 'FeatureCollection' || collection.features?.length !== 254) {
    throw new Error(`${source.year} Texas county query returned ${collection.features?.length ?? 'no'} features`);
  }
  const ids = collection.features.map((feature) => feature.properties.GEOID);
  if (new Set(ids).size !== 254 || ids.some((id) => !/^48\d{3}$/.test(id))) {
    throw new Error(`${source.year} county query has duplicate or non-Texas GEOIDs`);
  }
  const dir = path.join(root, `census-${source.year}`);
  await fs.mkdir(dir, {recursive: true});
  await fs.writeFile(path.join(dir, 'counties-layer-metadata.json'), metadataBytes, {flag: 'wx'});
  await fs.writeFile(path.join(dir, 'texas-counties.geojson'), queryBytes, {flag: 'wx'});
  console.log(JSON.stringify({
    year: source.year,
    vintage: metadata.description,
    layerUrl: source.layer,
    returnedFeatures: collection.features.length,
    metadataSha256: crypto.createHash('sha256').update(metadataBytes).digest('hex'),
    responseSha256: crypto.createHash('sha256').update(queryBytes).digest('hex'),
    responseBytes: queryBytes.length,
  }));
}

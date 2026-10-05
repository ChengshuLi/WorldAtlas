import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const sources = [
  {year: 2018, layer: 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2018/MapServer/84'},
  {year: 2025, layer: 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/39'},
];
const wantedStates = ['13', '21'];
const fields = 'GEOID,STATE,COUNTY,NAME,BASENAME,LSADC,FUNCSTAT,COUNTYNS,AREALAND,AREAWATER';
const digest = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');
for (const source of sources) {
  const retrievedAt = new Date().toISOString();
  const metadataUrl = new URL(source.layer);
  metadataUrl.searchParams.set('f', 'pjson');
  const metadataResponse = await fetch(metadataUrl);
  if (!metadataResponse.ok) throw new Error(`${source.year} layer metadata failed: ${metadataResponse.status}`);
  const metadataBytes = Buffer.from(await metadataResponse.arrayBuffer());
  const metadata = JSON.parse(metadataBytes);
  const expectedVintage = `January 1, ${source.year} vintage`;
  if (!metadata.description?.includes(expectedVintage)) throw new Error(`${source.year} service vintage mismatch`);
  const queryUrl = new URL(`${source.layer}/query`);
  queryUrl.searchParams.set('where', "STATE IN ('13','21')");
  queryUrl.searchParams.set('outFields', fields);
  queryUrl.searchParams.set('returnGeometry', 'true');
  queryUrl.searchParams.set('outSR', '4326');
  queryUrl.searchParams.set('f', 'geojson');
  const queryResponse = await fetch(queryUrl);
  if (!queryResponse.ok) throw new Error(`${source.year} county query failed: ${queryResponse.status}`);
  const queryBytes = Buffer.from(await queryResponse.arrayBuffer());
  const collection = JSON.parse(queryBytes);
  if (collection.type !== 'FeatureCollection' || collection.features?.length !== 279) {
    throw new Error(`${source.year} returned ${collection.features?.length ?? 'no'} features, expected 279`);
  }
  const ids = collection.features.map((feature) => feature.properties.GEOID);
  if (new Set(ids).size !== 279 || ids.some((id) => !/^(13|21)\d{3}$/.test(id))) throw new Error(`${source.year} roster is not unique Georgia/Kentucky counties`);
  const dir = path.join(root, `census-${source.year}`);
  await fs.mkdir(dir, {recursive: true});
  await fs.writeFile(path.join(dir, 'counties-layer-metadata.json'), metadataBytes, {flag: 'wx'});
  await fs.writeFile(path.join(dir, 'georgia-kentucky-counties.geojson'), queryBytes, {flag: 'wx'});
  const receipt = {
    source_id: `census-tigerweb-${source.year}`,
    layer_url: source.layer,
    metadata_url: metadataUrl.toString(),
    query_url: queryUrl.toString(),
    retrieval_started_at: retrievedAt,
    retrieval_completed_at: new Date().toISOString(),
    returned_feature_count: collection.features.length,
    state_fips: wantedStates,
    metadata_sha256: digest(metadataBytes),
    metadata_bytes: metadataBytes.length,
    response_sha256: digest(queryBytes),
    response_bytes: queryBytes.length,
    description: metadata.description,
    service_copyright: metadata.copyrightText ?? null,
    limitation: 'Census statistical geography and reference geometry; not a legal adjudication of each county line.',
  };
  await fs.writeFile(path.join(dir, 'retrieval.json'), JSON.stringify(receipt, null, 2) + '\n', {flag: 'wx'});
  console.log(JSON.stringify(receipt));
}

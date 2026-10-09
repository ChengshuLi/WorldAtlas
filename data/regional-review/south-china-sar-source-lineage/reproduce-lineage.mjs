import {createHash} from 'node:crypto';
import {readFileSync, writeFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';

const root = new URL('../../../', import.meta.url);
const path = (...parts) => new URL(parts.join('/'), root);
const bytes = (p) => readFileSync(p);
const sha = (b) => createHash('sha256').update(b).digest('hex');
const json = (p) => JSON.parse(bytes(p));
const baseline = 'd43cce74959376d8ef052afd3fd09e875bb08938';
const historicalMethodCommit = '4bdba3d40acc2d725e4aeb54c3b9aab559a91469';
const historicalMethodSha256 = 'ac18022fa1c881bdbedc590f150a501ad23d52ba86cb47c5a005643012f1ad1a';
const historicalMethodBytes = execFileSync('git', ['show', `${historicalMethodCommit}:scripts/semantic-locations.py`], {maxBuffer: 2 * 1024 * 1024});
if (sha(historicalMethodBytes) !== historicalMethodSha256) throw new Error('Historical aggregation source hash mismatch');
const atlasBytes = execFileSync('git', ['show', `${baseline}:data/geography/part-28.json`], {maxBuffer: 32 * 1024 * 1024});
const atlasDoc = JSON.parse(atlasBytes);
const atlas = new Map(atlasDoc.features.map(f => [f.properties.id, f]));

function readDbf(buffer) {
  const count = buffer.readUInt32LE(4);
  const headerLength = buffer.readUInt16LE(8);
  const recordLength = buffer.readUInt16LE(10);
  const fields = [];
  for (let offset = 32; offset < headerLength && buffer[offset] !== 0x0d; offset += 32) {
    const name = buffer.subarray(offset, offset + 11).toString('ascii').split('\0')[0];
    fields.push({name, length: buffer[offset + 16]});
  }
  const rows = [];
  for (let i = 0; i < count; i++) {
    let offset = headerLength + i * recordLength + 1;
    const row = {};
    for (const field of fields) {
      row[field.name] = buffer.subarray(offset, offset + field.length).toString('utf8').replace(/[\0 ]+$/g, '').replace(/^[ ]+/g, '');
      offset += field.length;
    }
    row.__record_index = i;
    rows.push(row);
  }
  return rows;
}

function readPolygonShapeFacts(shp, shx) {
  const shapeType = shp.readInt32LE(32);
  if (shapeType !== 5) throw new Error(`Expected ESRI Polygon shapefile, got ${shapeType}`);
  const recordCount = (shx.length - 100) / 8;
  const records = [];
  for (let i = 0; i < recordCount; i++) {
    const indexOffset = 100 + i * 8;
    const offset = shx.readInt32BE(indexOffset) * 2;
    const length = shx.readInt32BE(indexOffset + 4) * 2;
    const type = shp.readInt32LE(offset + 8);
    if (type !== 5) throw new Error(`Unexpected shape type ${type} at record ${i}`);
    const content = offset + 12;
    const bbox = [shp.readDoubleLE(content),shp.readDoubleLE(content+8),shp.readDoubleLE(content+16),shp.readDoubleLE(content+24)];
    const partCount = shp.readInt32LE(content+32), pointCount = shp.readInt32LE(content+36);
    if (length !== 4+32+8+partCount*4+pointCount*16) throw new Error(`Malformed shapefile index length at record ${i}`);
    const pointsOffset = content + 40 + partCount * 4;
    const coords = [];
    for (let j=0;j<pointCount;j++) coords.push([shp.readDoubleLE(pointsOffset+j*16),shp.readDoubleLE(pointsOffset+j*16+8)]);
    const parts = [];
    for (let j=0;j<partCount;j++) parts.push(shp.readInt32LE(content+40+j*4));
    records.push({record_index:i,shape_type:type,part_count:partCount,point_count:pointCount,bbox_wgs84_lonlat:bbox,coordinate_pairs_sha256:sha(Buffer.from(JSON.stringify(coords))),part_offsets:parts});
  }
  return records;
}

function points(v, out = []) {
  if (Array.isArray(v) && typeof v[0] === 'number' && typeof v[1] === 'number') out.push(v);
  else if (Array.isArray(v)) for (const child of v) points(child, out);
  return out;
}
function roundDeep(v) {
  if (typeof v === 'number') return Math.round(v * 10000) / 10000;
  if (Array.isArray(v)) return v.map(roundDeep);
  if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, roundDeep(x)]));
  return v;
}
function geomFacts(g) {
  const xy = points(g.coordinates);
  return {type: g.type, position_count: xy.length, bbox_wgs84_lonlat: xy.length ? [Math.min(...xy.map(p=>p[0])),Math.min(...xy.map(p=>p[1])),Math.max(...xy.map(p=>p[0])),Math.max(...xy.map(p=>p[1]))] : null, geometry_json_sha256: sha(Buffer.from(JSON.stringify(g)))};
}
function unionBboxes(rows) {
  const boxes=rows.map(row=>row.bbox_wgs84_lonlat);
  return [Math.min(...boxes.map(b=>b[0])),Math.min(...boxes.map(b=>b[1])),Math.max(...boxes.map(b=>b[2])),Math.max(...boxes.map(b=>b[3]))];
}
function bboxEqual4dp(a,b) { return JSON.stringify(a.map(x=>Math.round(x*10000)/10000)) === JSON.stringify(b.map(x=>Math.round(x*10000)/10000)); }

const neDir = 'data/regional-review/regional-review-365cbd6478904888/source/natural-earth-admin1';
const neStem = `${neDir}/ne_10m_admin_1_states_provinces`;
const ne = readDbf(bytes(path(`${neStem}.dbf`)));
const neShapes = readPolygonShapeFacts(bytes(path(`${neStem}.shp`)),bytes(path(`${neStem}.shx`)));
if (neShapes.length !== ne.length) throw new Error('Natural Earth SHP/SHX/DBF record count mismatch');
const gb = json(path('data/regional-review/regional-review-9b38f58111efd323/sources/geoboundaries-chn-adm2-2017.geojson'));
const hk = json(path('data/regional-review/south-china-sar-source-lineage/source/hong-kong-district-boundaries.geojson'));
const hkgAtlas = atlas.get('atlas:territory:HKG');
const macAtlas = atlas.get('atlas:territory:MAC');
if (!hkgAtlas || !macAtlas) throw new Error('baseline subject missing');
const hkgMembers = hkgAtlas.properties.metadata.source_member_ids;
const macMembers = macAtlas.properties.metadata.source_member_ids;
const neById = new Map(ne.map(r => [r.adm1_code, r]));
const hkFeatures = hk.features;
const hkNames = hkFeatures.map(f => f.properties.NAME_EN).sort();
const hkgRows = ne.filter(r => r.adm0_a3 === 'HKG').map(r => ({id:r.adm1_code,name:r.name,name_en:r.name_en,admin:r.admin,featurecla:r.featurecla,geometry_facts:neShapes[r.__record_index]})).sort((a,b)=>a.id.localeCompare(b.id));
const officialDistrictNames = new Set(hkNames.map(name=>name.replace(/\s+District$/i,'')));
const hkgNameMatches = hkgRows.filter(row=>officialDistrictNames.has(row.name));
const macNeRows = ne.filter(r => r.adm0_a3 === 'MAC').map(r => ({id:r.adm1_code,name:r.name,name_en:r.name_en,admin:r.admin,featurecla:r.featurecla,geometry_facts:neShapes[r.__record_index]}));
const gbMatches = gb.features.filter(f => f.properties.shapeID === '17275852B34966799109471');
const macGb = gbMatches[0];
const macGeomComparison = macGb ? {
  atlas_equals_source_at_4dp: JSON.stringify(roundDeep(macAtlas.geometry)) === JSON.stringify(roundDeep(macGb.geometry)),
  atlas: geomFacts(macAtlas.geometry), source: geomFacts(macGb.geometry),
} : null;
const hkgMatched = hkgMembers.map(id => ({id, source: neById.get(id) ?? null}));
const hkgShapeFacts = hkgMembers.map(id=>neShapes[neById.get(id).__record_index]);
const macNeShapeFacts = macNeRows.map(row=>row.geometry_facts);
const macComponentBbox = unionBboxes([...macNeShapeFacts,...(macGb?[geomFacts(macGb.geometry)]:[])]);
const hkgPositive = hkgMembers.length === 18 && hkgMatched.every(x=>x.source) && hkgMembers.slice().sort().join('\n') === ne.filter(r=>r.adm0_a3==='HKG').map(r=>r.adm1_code).sort().join('\n');
const hkgNegative = hkgMembers.slice(); hkgNegative[0] = 'CONTROL:NONEXISTENT';
const hkgNegativeRejected = hkgNegative.length !== 18 || hkgNegative.some(id=>!neById.has(id));
const gbPositive = gbMatches.length === 1 && macMembers.includes(`gb:CHN:ADM2:${gbMatches[0].properties.shapeID}`);
const gbNegativeRejected = gb.features.filter(f => f.properties.shapeID === 'CONTROL:NONEXISTENT').length === 0;

const result = {
  schema_version: 1,
  baseline_commit: baseline,
  historical_aggregate_method: {status:'located',path:'scripts/semantic-locations.py',commit:historicalMethodCommit,sha256:historicalMethodSha256,operation:'polygon(make_valid(union_all([geoms[i] for i in indices])))',historical_preaggregation_input:'data/.cache/semantic/input.geojson was untracked at the historical run and is absent from its parent snapshot; retained input-byte identity cannot be restored'},
  subjects: {
    'atlas:territory:HKG': {
      atlas_name: hkgAtlas.properties.name,
      atlas_geometry: geomFacts(hkgAtlas.geometry),
      source_component_union_bbox_wgs84_lonlat: unionBboxes(hkgShapeFacts),
      atlas_bbox_matches_source_component_union_bbox_at_4dp: bboxEqual4dp(geomFacts(hkgAtlas.geometry).bbox_wgs84_lonlat,unionBboxes(hkgShapeFacts)),
      member_ids: hkgMembers,
      retained_member_count: hkgMembers.length,
      matched_member_count: hkgMatched.filter(x=>x.source).length,
      member_id_match_fraction: hkgMatched.filter(x=>x.source).length / hkgMembers.length,
      current_official_district_name_match_count: hkgNameMatches.length,
      current_official_district_name_match_fraction: hkgNameMatches.length / hkFeatures.length,
      exact_retained_natural_earth_id_join: hkgPositive,
      retained_natural_earth_rows: hkgMatched.map(x=>({id:x.id,name:x.source?.name??null,name_en:x.source?.name_en??null,admin:x.source?.admin??null,featurecla:x.source?.featurecla??null})),
      official_current_district_source: {record_count:hkFeatures.length, english_names:hkNames, ne_id_count:ne.filter(r=>r.adm0_a3==='HKG').length},
      island_coast_and_legal_boundary_completeness: 'not tested; current official 18-district land administration source does not establish the legal outer SAR land-and-maritime boundary or full island/coast completeness',
    },
    'atlas:territory:MAC': {
      atlas_name: macAtlas.properties.name,
      atlas_geometry: geomFacts(macAtlas.geometry),
      source_component_union_bbox_wgs84_lonlat: macComponentBbox,
      atlas_bbox_matches_source_component_union_bbox_at_4dp: bboxEqual4dp(geomFacts(macAtlas.geometry).bbox_wgs84_lonlat,macComponentBbox),
      member_ids: macMembers,
      geoboundaries_match_count: gbMatches.length,
      retained_natural_earth_rows: macNeRows,
      geoboundaries_match:macGb?{native_id:macGb.properties.shapeID,shapeName:macGb.properties.shapeName,shapeISO:macGb.properties.shapeISO,shapeGroup:macGb.properties.shapeGroup,shapeType:macGb.properties.shapeType,geometry:geomFacts(macGb.geometry)}:null,
      atlas_vs_unnamed_geoboundaries_geometry:macGeomComparison,
      island_coast_and_legal_boundary_completeness: 'not tested; retained 2017 ADM2 polygon is not an authoritative current SAR land-and-maritime boundary source',
    },
  },
  controls: {
    hkg_exact_id_roster_positive: {outcome:hkgPositive?'passed':'failed',expected:'exact 18-member source ID roster equals DBF rows with adm0_a3=HKG'},
    hkg_absent_id_negative: {outcome:hkgNegativeRejected?'passed':'failed',expected:'replacement with absent sentinel is rejected'},
    mac_native_id_positive: {outcome:gbPositive?'passed':'failed',expected:'one exact ShapeID match and matching Atlas source member ID'},
    mac_absent_native_id_negative: {outcome:gbNegativeRejected?'passed':'failed',expected:'absent sentinel has zero ShapeID matches'},
  },
  unverified: [
    'The historical aggregation implementation is pinned and its union operation is replayed in original-union-results.json, but the historical pre-aggregation input cache was untracked and is unavailable. Exact original input bytes and whether other preceding transformations affected these subjects cannot be verified.',
    'The replay reconstructs Natural Earth shapefile polygons from ESRI ring orientation and point-in-ring shell/hole assignment; this adapter was not compared against the unavailable historical GeoJSON input. Geometry differences therefore include possible source-reader/serialization uncertainty.',
    'No GIS topology/overlay was run. Polygon counts, coordinate counts and rounded direct-source comparisons do not establish legal boundary correctness, gaps, overlaps, islands, coastline, maritime coverage or neighbors.',
    'Natural Earth package declares its vector data public domain; upstream authority and rights for its source contributors remain unverified. geoBoundaries predecessor terms/citation chain remain unresolved in retained malformed source URLs.',
  ],
};
if (!hkgPositive || !hkgNegativeRejected || !gbPositive || !gbNegativeRejected) throw new Error('lineage identity/control failure');
const out = path('data/regional-review/south-china-sar-source-lineage/lineage-results.json');
writeFileSync(out, `${JSON.stringify(result,null,2)}\n`);
const positiveControl = {method_id:'sar-source-identity-reproduction',kind:'positive-control',outcome:'passed',cases:[
    {id:'HKG exact Natural Earth roster',expected:18,actual:hkgMatched.filter(x=>x.source).length,passed:hkgPositive},
    {id:'MAC exact geoBoundaries native ShapeID',expected:1,actual:gbMatches.length,passed:gbPositive},
  ]};
const negativeControl = {method_id:'sar-source-identity-reproduction',kind:'negative-control',outcome:'passed',cases:[
    {id:'HKG absent member sentinel',expected:0,actual:hkgNegative.filter(id=>neById.has(id)).length,rejected:hkgNegativeRejected},
    {id:'MAC absent ShapeID sentinel',expected:0,actual:gb.features.filter(f=>f.properties.shapeID==='CONTROL:NONEXISTENT').length,rejected:gbNegativeRejected},
  ]};
writeFileSync(path('data/regional-review/south-china-sar-source-lineage/positive-control.json'), `${JSON.stringify(positiveControl,null,2)}\n`);
writeFileSync(path('data/regional-review/south-china-sar-source-lineage/negative-control.json'), `${JSON.stringify(negativeControl,null,2)}\n`);
console.log(JSON.stringify(result,null,2));

import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

const root = process.cwd();
const owned = 'data/regional-review/regional-review-524d77d4d47b77c6';
const baseline = '062e0585025359c596a887e5a10d3e25479aff21';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const gitBlob = file => execFileSync('git', ['show', `${baseline}:${file}`], {maxBuffer: 128 * 1024 * 1024});
const scope = JSON.parse(fs.readFileSync(path.join(owned, 'scope.json')));
if (scope.member_location_ids.length !== 220 || new Set(scope.member_location_ids).size !== 220) throw Error('Expected 220 unique frozen subject IDs');
if (scope.location_count !== 220 || scope.member_location_ids_sha256 !== '2d39f311875e709ce477409f2b4b00e5e0040bbb9d8679c567e3732199c340d8') throw Error('Scope roster hash/count mismatch');
const regionId = 'framework:region:southwest-china:295e896313cf';
const inventory = JSON.parse(zlib.gunzipSync(gitBlob('data/macro-foundation/current-membership-inventory.json.gz')));
const regionHandoffs = JSON.parse(zlib.gunzipSync(gitBlob('data/macro-foundation/regional-handoffs.json.gz')));
const region = regionHandoffs.regions.find(r => r.region_id === regionId);
if (!region || region.envelope.geometry_sha256 !== scope.frozen_region_geometry_sha256 || region.envelope.member_location_ids_sha256 !== scope.frozen_region_member_ids_sha256 || region.envelope.locations !== 488) throw Error('Current handoff inventory no longer matches the issue frozen region pins');
if (region.regional_interiors_approved || region.publication_verified || region.location_attribute_imports_ready) throw Error('Unexpected region approval/publication/import readiness');
const regionAreas = inventory.filter(x => x.parent_id === regionId);
const regionMembers = new Set(regionAreas.flatMap(x => x.member_location_ids));
if (regionAreas.length !== 5 || regionMembers.size !== 488 || scope.member_location_ids.some(id => !regionMembers.has(id))) throw Error('The packet IDs do not resolve as a subset of the current frozen Southwest China handoff inventory');
for (const area of scope.area_scopes) {
  const parent = inventory.find(x => x.id === area.id);
  if (!parent || parent.member_location_ids.length !== area.full_area_location_count) throw Error(`Area inventory count mismatch for ${area.id}`);
  const actual = scope.member_location_ids.filter(id => parent.member_location_ids.includes(id)).length;
  if (actual !== area.owned_member_location_count) throw Error(`Scoped area count mismatch for ${area.id}: ${actual}`);
}
const currentCertHash = hash(gitBlob('data/macro-foundation/macro-certificate.json'));
if (currentCertHash !== 'f50f70fcb0756712ab7a7a388bc8cada093080518f07d3a6f7329758980ea81b' || regionHandoffs.macro_certificate_sha256 !== currentCertHash) throw Error('Unexpected current macro certificate input');
const index = JSON.parse(gitBlob('data/world-index.json'));
const featureMap = new Map();
for (const item of index.parts) {
  const file = `data/${item}`;
  const raw = gitBlob(file);
  for (const feature of JSON.parse(raw).features) {
    const id = feature.id ?? feature.properties?.id;
    if (scope.member_location_ids.includes(id)) {
      if (featureMap.has(id)) throw Error(`Duplicate subject in pinned index: ${id}`);
      featureMap.set(id, {feature, source_file: file, source_sha256: hash(raw)});
    }
  }
}
if (featureMap.size !== 220) throw Error(`Found ${featureMap.size}/220 subjects in pinned world index`);

const gbPath = 'data/regional-review/regional-review-9b38f58111efd323/sources/geoboundaries-chn-adm2-2017.geojson';
const gbBytes = gitBlob(gbPath);
if (hash(gbBytes) !== '2b68d8a808742fc6d7acd769584db960d8fc2c25b9f1d20e3e98c72e9f1c4d34') throw Error('Previously retained geoBoundaries bytes changed');
const gb = JSON.parse(gbBytes);
if (gb.features.length !== 2391) throw Error(`Unexpected geoBoundaries source feature count ${gb.features.length}`);
const gbById = new Map(gb.features.map(f => [f.properties?.shapeID, f]));
if (gbById.size !== gb.features.length) throw Error('Duplicate geoBoundaries shapeID');

const arcItem = fs.readFileSync(path.join(owned, 'sources/resolve-ecoregions-item.json'));
const arcData = fs.readFileSync(path.join(owned, 'sources/resolve-ecoregions-item-data.json'));
const arcEco = fs.readFileSync(path.join(owned, 'sources/resolve-ecoregions-scoped-live-20261005.geojson'));
const sichuanPage = fs.readFileSync(path.join(owned,'sources/sichuan-2026-county-count.html'));
const xizangPage = fs.readFileSync(path.join(owned,'sources/xizang-2026-first-half-administrative-codes.html'));
if (hash(arcItem) !== '23863490caa9384aa9658f1ba0ba4a0b2493e5d2759effe0f5b24792ba26406e') throw Error('ArcGIS item metadata hash mismatch');
if (hash(arcData) !== '07ebea5c4a70c20b929508acb0bbb929e2f841d145b9c45f2c044ec6953fbb9c') throw Error('ArcGIS item data hash mismatch');
if (hash(arcEco) !== '49e2ae4c56ada9359babda39cb0c49a9ef13b641dc9b7d0f673b44a416d30a38') throw Error('ArcGIS scoped feature response hash mismatch');
if (hash(sichuanPage) !== '28fe67db51904b7a5c90e9d725296227f1cb80eaf7f6b1b89f134dc4203d49f9' || !sichuanPage.toString().includes('183个县（市、区）')) throw Error('Official Sichuan current-count source hash/claim mismatch');
if (hash(xizangPage) !== 'b746b510993af9133ad769d5eecdafaf1cb9d44d6762bb3de8474ed57162dcf9') throw Error('Official Xizang current-code source hash mismatch');
const xizangCodes = [...new Set(xizangPage.toString().match(/54\d{4}/g) ?? [])];
const xizangCountyCodes = xizangCodes.filter(code=>!code.endsWith('00'));
if(xizangCountyCodes.length!==74) throw Error(`Unexpected official Xizang county-level code count: ${xizangCountyCodes.length}`);
const arc = JSON.parse(arcEco);
if (arc.features.length !== 5) throw Error(`Expected 5 distinct source ecoregion geometries; got ${arc.features.length}`);
const arcNames = new Set(arc.features.map(f => f.properties.ECO_NAME));

const rows = [];
function geometryScreen(geometry) {
  if (!geometry) return {type:null, polygon_components:null, rings:null, structurally_valid_polygon_coordinates:false};
  const polygons = geometry.type==='Polygon' ? [geometry.coordinates] : geometry.type==='MultiPolygon' ? geometry.coordinates : [];
  return {type:geometry.type, polygon_components:polygons.length, rings:polygons.reduce((sum,p)=>sum+p.length,0), structurally_valid_polygon_coordinates:polygons.length>0&&polygons.every(p=>p.length>0&&p.every(r=>Array.isArray(r)&&r.length>=4&&JSON.stringify(r[0])===JSON.stringify(r.at(-1))))};
}
for (const id of scope.member_location_ids) {
  const {feature, source_file, source_sha256} = featureMap.get(id);
  const p = feature.properties;
  const metadata = p.metadata ?? {};
  const isPhysicalAdaptation = id.startsWith('atlas:physical:');
  const originalId = metadata.original_id;
  const source = originalId ? gbById.get(originalId) : null;
  if (id.startsWith('gb:CHN:ADM2:') && !source) throw Error(`No unique source record for ${id}`);
  const eco = isPhysicalAdaptation ? String(p.name).split(' · ').slice(1).join(' · ') : null;
  if (isPhysicalAdaptation && !arcNames.has(eco)) throw Error(`No retained independent ecoregion source feature for ${eco}`);
  rows.push({
    id, name: p.name, province_parent_id: p.parent_id,
    source_entity_id: isPhysicalAdaptation ? metadata.source_id : metadata.source_id,
    source_role_asserted: metadata.source_role ?? null,
    declared_reference_year: metadata.reference_year ?? null,
    source_license_claim: metadata.license ?? null,
    source_feature_id: isPhysicalAdaptation ? originalId : source?.properties?.shapeID ?? null,
    source_feature_name: source?.properties?.shapeName ?? null,
    source_feature_type: source?.properties?.shapeType ?? null,
    source_feature_parent: isPhysicalAdaptation ? null : source?.properties?.shapeGroup ?? null,
    source_geometry_type: source?.geometry?.type ?? null,
    atlas_geometry_screen: geometryScreen(feature.geometry),
    source_geometry_screen: source ? geometryScreen(source.geometry) : null,
    atlas_geometry_hash_sha256: hash(Buffer.from(JSON.stringify(feature.geometry))),
    retained_source_geometry_hash_sha256: source ? hash(Buffer.from(JSON.stringify(source.geometry))) : null,
    geometry_equal_as_parsed_json: source ? JSON.stringify(feature.geometry) === JSON.stringify(source.geometry) : null,
    declared_original_geometry_sha256: metadata.original_geometry_sha256 ?? null,
    source_file, source_file_sha256: source_sha256,
    classification: isPhysicalAdaptation ? 'correction-needed' : 'insufficient-evidence',
    rationale: isPhysicalAdaptation
      ? `Atlas title and retained source provenance identify a ${eco} physical-ecoregion subdivision inside the source unit ${source?.properties?.shapeName ?? originalId}; the inherited County Level role and county-equivalent selection_reason contradict the feature's own location_basis. The ArcGIS source independently defines ecoregions as ecological rather than political boundaries. Preserve this ID and boundary pending an approved, sourced semantic/hierarchy correction.`
      : 'The immutable 2017 ADM2 source feature is traceable and declares this source collection County Level, but this packet did not match each feature to an authoritative current county roster or official boundary map. County-equivalent role and name are therefore not individually verified; boundary correctness, completeness, and parent overlay remain unverified.',
    verification_limits: isPhysicalAdaptation
      ? ['ArcGIS returns the full global ecoregion feature, not the exact county-clipped fragment; this confirms physical/ecological meaning but not the Atlas fragment construction or its boundary.', 'The original source unit itself needs current official name/territory crosswalk.']
      : ['No official administrative-standard map overlay or current official code crosswalk for this individual feature.', 'No neighbor-edge, enclave/exclave, island, gap/overlap, or province-parent topology certification.', '2017 source vintage is not a current boundary claim.']
  });
}
const physical = rows.filter(r => r.id.startsWith('atlas:physical:'));
if (physical.length !== 17 || rows.length - physical.length !== 203) throw Error('Expected exactly 17 derived physical subdivisions and 203 direct ADM2 IDs');
const geometryMismatchCount = rows.filter(r => r.id.startsWith('gb:CHN:ADM2:') && !r.geometry_equal_as_parsed_json).length;
if (geometryMismatchCount !== 203) throw Error(`Expected to detect all 203 transformed ADM2 geometries, observed ${geometryMismatchCount}`);
const geometryHashAudit = JSON.parse(execFileSync('python3', [path.join(owned,'verify_original_geometry_hashes.py')], {encoding:'utf8', maxBuffer:16*1024*1024}));
if (geometryHashAudit.scope_rows !== 203) throw Error('Original-geometry hash audit did not cover all 203 direct ADM2 subjects');
const originalHashById = new Map(geometryHashAudit.rows.map(r=>[r.id,r]));
for (const row of rows) {
  const audit=originalHashById.get(row.id);
  row.recorded_original_hash_matches_retained_2017_geometry = audit ? audit.metadata_hash_matches_retained_source : null;
  row.retained_2017_source_geometry_hash_python_json_sort_keys = audit ? audit.retained_source_geometry_sha256_python_json_sort_keys : null;
}
const geometryScreens={
  scoped_atlas_multipart:rows.filter(r=>r.atlas_geometry_screen.polygon_components>1).length,
  scoped_atlas_with_holes:rows.filter(r=>r.atlas_geometry_screen.rings>r.atlas_geometry_screen.polygon_components).length,
  scoped_atlas_failed_simple_ring_screen:rows.filter(r=>!r.atlas_geometry_screen.structurally_valid_polygon_coordinates).length,
  direct_adm2_source_multipart:rows.filter(r=>r.id.startsWith('gb:CHN:ADM2:')&&r.source_geometry_screen.polygon_components>1).length,
  direct_adm2_source_with_holes:rows.filter(r=>r.id.startsWith('gb:CHN:ADM2:')&&r.source_geometry_screen.rings>r.source_geometry_screen.polygon_components).length
};
const sourceNames=rows.filter(r=>r.id.startsWith('gb:CHN:ADM2:'));
const semanticScreens={
  direct_adm2_names_ending_in_shi:sourceNames.filter(r=>/shi$/i.test(r.source_feature_name??'')).map(r=>({id:r.id,name:r.source_feature_name,province_parent_id:r.province_parent_id})),
  direct_adm2_missing_names:sourceNames.filter(r=>!r.source_feature_name).map(r=>r.id),
  direct_adm2_names_with_remainder_terms:sourceNames.filter(r=>/other|remaining|remainder|unknown|unincorporated/i.test(r.source_feature_name??'')).map(r=>({id:r.id,name:r.source_feature_name})),
  ecological_fragments:physical.map(r=>({id:r.id,name:r.name,source_adm2_name:r.source_feature_name,province_parent_id:r.province_parent_id}))
};
const xizangAreaId=scope.area_scopes.find(a=>a.name==='Xizang').id;
const xizangProvinceIds=new Set(inventory.filter(x=>x.parent_id===xizangAreaId).map(x=>x.id));
const xizangRows=rows.filter(r=>xizangProvinceIds.has(r.province_parent_id));
const xizangSourceUnits=new Set(xizangRows.map(r=>r.source_feature_id).filter(Boolean));
const areaContext={
  sichuan:{atlas_full_area_inventory:scope.area_scopes.find(a=>a.name==='Sichuan').full_area_location_count,official_current_count_2026_04:183,discrepancy_count_vs_inventory:183-scope.area_scopes.find(a=>a.name==='Sichuan').full_area_location_count,comparison_limit:'Counts use different source vintages and definitions; this is a completeness warning only, not proof that specific units are missing.'},
  xizang:{atlas_workload_locations:scope.area_scopes.find(a=>a.name==='Xizang').full_area_location_count,official_county_codes_2026_06_30:xizangCountyCodes.length,atlas_direct_geoboundaries_ids_in_scope:xizangRows.filter(r=>r.id.startsWith('gb:CHN:ADM2:')).length,represented_distinct_2017_source_adm2_ids_in_scope:xizangSourceUnits.size,delta_candidate_source_units_vs_current_official_count:xizangSourceUnits.size-xizangCountyCodes.length,comparison_limit:'The 17 physical fragments are not county units and represent five source ADM2 IDs. Names/codes and polygons were not crosswalked; the difference is not a specific omission finding.'},
  yunnan:{atlas_full_area_inventory:scope.area_scopes.find(a=>a.name==='Yunnan').full_area_location_count,official_2026_code_table_page:'https://ynmz.yn.gov.cn/index.php/cms/gongshigonggao/12323.html',exact_bytes_retained:false,comparison_limit:'Official page response timed out during retrieval; the indexed extract was insufficient for an exact roster count or ID crosswalk.'}
};
const areaRows = scope.area_scopes.map(a => ({id:a.id,name:a.name,owned_locations:a.owned_member_location_count,full_area_locations:a.full_area_location_count,classification:'insufficient-evidence',rationale:'The scoped workload is a partial membership for this area; this packet classifies only the owned member locations. Parent release/envelope decisions are reserved to region integration, and no combined area boundary or membership approval is made.'}));
const provinceRows = scope.province_scopes.map(p => ({id:p.id,name:p.name,owned_locations:rows.filter(r=>r.province_parent_id===p.id).length,classification:'insufficient-evidence',rationale:'Province parent identity/count is an inventory observation only. This packet does not certify province geometry, current administrative roster completeness, or the full province parent decision.'}));
if (areaRows.length !== 3 || provinceRows.length !== 28) throw Error('Expected three area groups and 28 province groups');
for(const p of provinceRows) {
  const expected=scope.province_scopes.find(x=>x.id===p.id).full_province_locations;
  if(p.owned_locations!==expected) throw Error(`Scoped province member count mismatch for ${p.id}: ${p.owned_locations} vs ${expected}`);
}
const result = {
  packet_id:scope.batch_id, baseline_commit:baseline,
  scope_sha256:hash(fs.readFileSync(path.join(owned,'scope.json'))),
  frozen_scope:{location_count:scope.location_count,ids_sha256:scope.member_location_ids_sha256,region_geometry_sha256:scope.frozen_region_geometry_sha256,region_member_ids_sha256:scope.frozen_region_member_ids_sha256,current_frozen_region_members:regionMembers.size,full_region_parent_areas:regionAreas.map(a=>({id:a.id,name:a.name,locations:a.member_location_ids.length})),current_macro_certificate_sha256:currentCertHash,issue_macro_certificate_sha256:scope.macro_certificate_sha256,macro_certificate_match:currentCertHash===scope.macro_certificate_sha256},
  source_checks:{geoBoundaries:{path:gbPath,sha256:hash(gbBytes),bytes:gbBytes.length,feature_count:gb.features.length,unique_ids:gbById.size,scope_source_records:rows.filter(r=>r.source_feature_id&&r.id.startsWith('gb:')).length},arcgis_resolve:{item_sha256:hash(arcItem),item_bytes:arcItem.length,item_data_sha256:hash(arcData),item_data_bytes:arcData.length,live_scoped_features_sha256:hash(arcEco),live_scoped_features_bytes:arcEco.length,feature_count:arc.features.length,ecoregion_names:[...arcNames].sort()},official_administration:{sichuan_page_sha256:hash(sichuanPage),sichuan_page_bytes:sichuanPage.length,sichuan_official_count_2026_04:183,xizang_page_sha256:hash(xizangPage),xizang_page_bytes:xizangPage.length,xizang_current_county_codes_2026_06_30:xizangCountyCodes.length,yunnan_full_response_retained:false}},
  classification_counts:{'correction-needed':physical.length,'insufficient-evidence':rows.length-physical.length,justified:0},
  comparison_findings:{direct_adm2_features_with_exact_retained_source_geometry:203-geometryMismatchCount,direct_adm2_features_with_nonidentical_geometry:geometryMismatchCount,method:'Parsed GeoJSON geometry objects compared by JSON.stringify without geometric normalization; inequality detects modification but does not establish whether the modification is wrong.',recorded_original_geometry_hash_matches_retained_source:geometryHashAudit.matches,recorded_original_geometry_hash_mismatches_retained_source:geometryHashAudit.mismatches,recorded_hash_method:'Python hashlib.sha256(json.dumps(source_geometry, sort_keys=True).encode()), matching scripts/reconcile-topology.py. A mismatch means this retained candidate source geometry does not reproduce the recorded original_geometry_sha256; it does not identify which lineage input or serialization is authoritative.'},
  geometry_screens:{...geometryScreens,interpretation:'Counts only. A simple ring-closure/coordinate-array screen is not geometric validity, topology, neighboring coverage, island completeness, official-boundary agreement, or proof of correctness.'},
  semantic_screens:semanticScreens,
  area_context:areaContext,
  locations:rows, provinces:provinceRows, areas:areaRows,
  structural_checks_only:true,
  not_established:['Exact County-to-Atlas boundaries or current administrative boundaries','Current complete county-level rosters for the 203 direct source rows','Correctness of all parents and neighboring unit granularity','Islands, enclaves/exclaves, cross-province completeness, slivers, gaps or overlaps','Whether transformed 203 geometries match a legitimate versioned topology-reconciliation operation or current official boundaries','The correct non-administrative use, parent tier, or lifecycle of the 17 ecological subdivisions','Publication, regional approval, import, or production readiness']
};
fs.writeFileSync(path.join(owned,'assessment.json'),`${JSON.stringify(result,null,2)}\n`);
const summary={baseline_commit:baseline,scope_ids:rows.length,unique_index_subjects:featureMap.size,frozen_region_inventory_members:regionMembers.size,geoBoundaries_matches:result.source_checks.geoBoundaries.scope_source_records,geoBoundaries_sha256:result.source_checks.geoBoundaries.sha256,physical_subdivisions:physical.length,ecoregion_source_features:arc.features.length,transformed_adm2_geometries:geometryMismatchCount,recorded_original_geometry_hash_mismatches:geometryHashAudit.mismatches,issue_macro_certificate_matches_current:currentCertHash===scope.macro_certificate_sha256,classification_counts:result.classification_counts,province_groups:provinceRows.length,area_groups:areaRows.length};
fs.writeFileSync(path.join(owned,'reproduction-results.json'),`${JSON.stringify(summary,null,2)}\n`);
console.log(JSON.stringify({result:'passed',...summary}));

#!/usr/bin/env python3
"""Reproduce exact #83 source identity, scope, and geometry diagnostics (read-only)."""
from __future__ import annotations
import gzip, hashlib, json, platform, sys, statistics
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from shapely.geometry import shape, Polygon
import shapely
from evidence.geometry import land_area_m2, METHOD as GEOMETRY_METHOD

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SCOPE_PATH = OUT / 'issue-scope.json'
ASSESSMENTS_PATH = OUT / 'assessments.json'
UP_ROSTER_PATH = OUT / 'sources/up-tehsil-rosters.json'
MP_ROSTER_PATH = OUT / 'sources/mp-tehsil-rosters-recheck.json'
RESULT_PATH = OUT / 'reproduction-results.json'

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_geo(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

def polygonal_area_m2(geometry):
    """Measure only polygonal set-operation output components; retain no repaired input geometry."""
    if geometry.is_empty:
        return 0.0, 0
    if geometry.geom_type == 'Polygon':
        return land_area_m2(geometry), 1
    if geometry.geom_type == 'MultiPolygon':
        return sum(land_area_m2(part) for part in geometry.geoms), len(geometry.geoms)
    if geometry.geom_type == 'GeometryCollection':
        parts=[]
        for part in geometry.geoms:
            if part.geom_type == 'Polygon': parts.append(part)
            elif part.geom_type == 'MultiPolygon': parts.extend(part.geoms)
        return sum(land_area_m2(part) for part in parts), len(parts)
    return 0.0, 0

scope_doc = load_geo(SCOPE_PATH)
scope = scope_doc['workload_scope']
ids = scope['member_location_ids']
assert len(ids) == scope['location_count'] == 229 and len(set(ids)) == 229
assert scope['owned_evidence_path'] == 'data/regional-review/regional-review-78f086631fc52a58/'
assert scope_doc['work_spec']['mode'] == 'geography'
assert scope_doc['work_spec']['owned_paths'] == [scope['owned_evidence_path']]
province_scopes = scope['province_scopes']
province_ids = [location_id for province in province_scopes for location_id in province['owned_location_ids']]
assert len(province_scopes) == 35 and len(province_ids) == 229 and set(province_ids) == set(ids)
assert len(province_ids) == len(set(province_ids)), 'province scope overlap'
assessment_doc = load_geo(ASSESSMENTS_PATH)
assert {x['location_id'] for x in assessment_doc['location_assessments']} == set(ids)
assert len(assessment_doc['location_assessments']) == 229 and len(assessment_doc['province_assessments']) == 35
assert sum(x['owned_member_location_count'] for x in scope['area_scopes']) == 229
assert {(x['name'],x['owned_member_location_count'],x['full_area_location_count'],x['partial']) for x in scope['area_scopes']} == {('Madhya Pradesh',144,422,True),('Uttar Pradesh',85,244,True)}


atlas = {}
for path in sorted((ROOT / 'data/geography').glob('part-*.json')):
    for feat in load_geo(path)['features']:
        if feat.get('id') in set(ids):
            assert feat['id'] not in atlas, f'duplicate Atlas id: {feat["id"]}'
            atlas[feat['id']] = (feat, path.relative_to(ROOT).as_posix())
assert set(atlas) == set(ids), f'missing Atlas identities: {len(set(ids)-set(atlas))}'

src_path = ROOT / 'data/global-sources/IND-ADM3.geojson.gz'
with gzip.open(src_path, 'rt', encoding='utf-8') as stream:
    src = json.load(stream)
uncompressed_sha256 = hashlib.sha256(gzip.decompress(src_path.read_bytes())).hexdigest()
assert uncompressed_sha256 == '4ea6807d0a0c5aac0b46ee8e31ed7c30fbec273b44345bba1e4a2bb5f299f5fb'
source_features = {}
for feat in src['features']:
    key = feat.get('properties', {}).get('shapeID')
    assert key and key not in source_features, f'missing/duplicate source shapeID: {key}'
    source_features[key] = feat

matched = 0
unique_native = set()
valid_atlas = valid_source = equal = 0
geometry_types = {}
per_location = []
for location_id in ids:
    atlas_feature, _ = atlas[location_id]
    props = atlas_feature['properties']
    meta = props['metadata']
    member_ids = meta.get('source_member_ids', [])
    assert meta.get('source_id') == 'gb:IND:ADM3'
    assert len(member_ids) == 1, f'{location_id}: expected one source member'
    shape_id = member_ids[0]
    assert shape_id not in unique_native, f'duplicate native source ID: {shape_id}'
    unique_native.add(shape_id)
    native = source_features.get(shape_id)
    assert native is not None, f'missing native source ID: {shape_id}'
    assert native['properties'].get('shapeGroup') == 'IND'
    assert native['properties'].get('shapeType') == 'ADM3'
    assert native['properties'].get('shapeName') == props['name'] or native['properties'].get('shapeName') == meta.get('source_name_with_footnote')
    matched += 1
    ga, gs = shape(atlas_feature['geometry']), shape(native['geometry'])
    assert ga.geom_type in ('Polygon', 'MultiPolygon') and gs.geom_type in ('Polygon', 'MultiPolygon')
    geometry_types[ga.geom_type] = geometry_types.get(ga.geom_type, 0) + 1
    valid_atlas += int(ga.is_valid)
    valid_source += int(gs.is_valid)
    same = bool(ga.equals(gs))
    equal += int(same)
    per_location.append({'location_id':location_id,'atlas_name':props['name'],'native_source_id':shape_id,'native_source_name':native['properties']['shapeName'],'atlas_geometry_type':ga.geom_type,'source_geometry_type':gs.geom_type,'atlas_valid':bool(ga.is_valid),'source_valid':bool(gs.is_valid),'topologically_equal':same,'atlas_component_count':len(ga.geoms) if ga.geom_type == 'MultiPolygon' else 1})

# Positive/negative controls verify geometry helper behavior, not geography.
control = Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)])
positive_control = control.equals(shape(json.loads(json.dumps({'type':'Polygon','coordinates':[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}))))
positive_area_m2 = land_area_m2(control)
negative_control = False
try:
    land_area_m2(Polygon([(0,0),(1,1),(1,0),(0,1),(0,0)]))
except ValueError:
    negative_control = True
assert positive_control and negative_control and 12_000_000_000 < positive_area_m2 < 13_000_000_000
# Enrich each exact scoped comparison with WGS84 source-edge ellipsoidal areas.
for row in per_location:
    af, _ = atlas[row['location_id']]
    sf = source_features[row['native_source_id']]
    ga, gs = shape(af['geometry']), shape(sf['geometry'])
    aa, sa = land_area_m2(ga), land_area_m2(gs)
    symdiff=ga.symmetric_difference(gs)
    sd, polygon_parts=polygonal_area_m2(symdiff)
    row.update({'atlas_area_m2':aa,'source_area_m2':sa,'symmetric_difference_result_type':symdiff.geom_type,'symmetric_difference_polygon_parts':polygon_parts,'symmetric_difference_area_m2':sd,'symmetric_difference_fraction_of_atlas':sd/aa if aa else None})
# Within-parent positive-area overlap screen; a pass cannot establish coverage or correctness.
parent_by_id={f['id']:f['properties'].get('parent_id') for f,_ in atlas.values()}
by_parent={}
for location_id,(feature,_) in atlas.items(): by_parent.setdefault(parent_by_id[location_id],[]).append((location_id,shape(feature['geometry'])))
positive_overlaps=[]
for parent, members in by_parent.items():
    members.sort(key=lambda row: row[0])
    for i,(left_id,left_geom) in enumerate(members):
        for right_id,right_geom in members[i+1:]:
            inter=left_geom.intersection(right_geom)
            if not inter.is_empty and inter.area > 0:
                overlap_m2,_=polygonal_area_m2(inter)
                if overlap_m2 > 1.0:
                    positive_overlaps.append({'parent_id':parent,'left_id':left_id,'right_id':right_id,'overlap_m2':overlap_m2})
province_area_stats=[]
for group in province_scopes:
    values=sorted(land_area_m2(shape(atlas[i][0]['geometry'])) for i in group['owned_location_ids'])
    province_area_stats.append({'province_id':group['id'],'province_name':group['name'],'members':len(values),'min_location_area_m2':values[0],'median_location_area_m2':statistics.median(values),'max_location_area_m2':values[-1],'max_to_median_area_ratio':values[-1]/statistics.median(values) if statistics.median(values) else None})

metadata_path = ROOT / 'data/global-sources/IND-ADM3-metadata.json'
metadata = load_geo(metadata_path)
roster_doc = load_geo(UP_ROSTER_PATH)
mp_roster_doc = load_geo(MP_ROSTER_PATH)
def norm_name(x):
    return ''.join(c.lower() for c in x if c.isalnum())
roster_by_name = {norm_name(x['district_selector_name']):x for x in roster_doc['districts']}
roster_by_name['auraiya'] = roster_by_name['auraya']
roster_by_name['kanpurdehat'] = roster_by_name['kanpurdehat']
roster_by_name['kanpurnagar'] = roster_by_name['kanpurnagar']
up_area_id = next(x['id'] for x in scope['area_scopes'] if x['name']=='Uttar Pradesh')
hierarchy_records = {x['id']:x for x in load_geo(ROOT/'data/hierarchy.json')}
up_groups = [x for x in scope['province_scopes'] if hierarchy_records.get(x['id'],{}).get('parent_id')==up_area_id]
roster_counts=[]
for group in up_groups:
    label=norm_name(group['name'])
    current=roster_by_name.get(label)
    if current is None: raise AssertionError(f'missing UP district roster: {group["name"]}')
    roster_counts.append({'district':group['name'],'issue_member_count':len(group['owned_location_ids']),'DARMS_tehsil_count':current['tehsil_count'],'count_match':len(group['owned_location_ids'])==current['tehsil_count'],'response_sha256':current['response_sha256']})
assert len(roster_counts)==17 and all(x['count_match'] for x in roster_counts)
mp_pages=[]
for page in mp_roster_doc['pages']:
    tables=page.get('tables',[])
    table_rows=[max(0,len(table)-1) for table in tables]
    headers=[str(c).casefold() for table in tables for c in (table[0] if table else [])]
    has_tehsil_table=any('tehsil' in h or 'tahsil' in h for h in headers) or (page['name']=='Rewa Division' and bool(tables))
    mp_pages.append({'name':page['name'],'url':page['url'],'http_status':page.get('http_status'),'response_sha256':page.get('response_sha256'),'response_bytes':page.get('response_bytes'),'error':page.get('error'),'table_row_counts_including_header_subtracted':table_rows,'has_tehsil_roster_table':has_tehsil_table,'count_claims':page.get('count_claims',[])})
assert len(mp_pages)==18 and len({x['name'] for x in mp_pages})==18
input_paths = [SCOPE_PATH, ASSESSMENTS_PATH, UP_ROSTER_PATH, MP_ROSTER_PATH, Path(__file__), ROOT/'data/global-sources/IND-ADM3.geojson.gz', metadata_path, ROOT/'data/hierarchy.json'] + sorted({ROOT/path for _,path in atlas.values()}, key=str)
input_files = [{'path':str(path.relative_to(ROOT)),'sha256':sha(path),'bytes':path.stat().st_size} for path in dict.fromkeys(input_paths)]
report = {
  'version': 1,
  'issue': 83,
  'baseline_commit': scope_doc['base_commit'],
  'runtime': {'python': platform.python_version(), 'shapely': shapely.__version__},
  'input_files': input_files,
  'scope': {'expected': len(ids), 'atlas_exact_once': len(atlas), 'native_ids_unique': len(unique_native), 'native_ids_found': matched, 'province_rows':len(province_scopes), 'province_owned_ids_exact_partition':True, 'partial_area_owned_counts':{x['name']:x['owned_member_location_count'] for x in scope['area_scopes']}},
  'source': {'compressed_sha256': sha(src_path), 'uncompressed_sha256':uncompressed_sha256, 'metadata_sha256': sha(metadata_path), 'features_retained': len(source_features), 'features_metadata_declared': int(metadata['admUnitCount']), 'unexplained_count_difference': int(metadata['admUnitCount']) - len(source_features), 'vintage': metadata['boundaryYearRepresented'], 'role': metadata['boundaryCanonical'], 'license': metadata['boundaryLicense']},
  'geometry_diagnostics': {'atlas_valid': valid_atlas, 'source_valid': valid_source, 'topologically_equal': equal, 'topologically_not_equal': len(ids)-equal, 'atlas_geometry_types': dict(sorted(geometry_types.items())), 'atlas_multipart_count':geometry_types.get('MultiPolygon',0), 'within_parent_positive_overlap_count_over_1m2':len(positive_overlaps), 'within_parent_positive_overlaps':positive_overlaps, 'positive_wgs84_one_degree_square_area_m2':positive_area_m2, 'positive_predicate_control': positive_control, 'negative_self_intersection_control': negative_control, 'area_method':GEOMETRY_METHOD},
  'province_area_diagnostics':province_area_stats,
  'current_up_roster_diagnostics': {'districts':roster_counts,'district_count':len(roster_counts),'owned_locations':sum(x['issue_member_count'] for x in roster_counts),'current_tehsil_count_sum':sum(x['DARMS_tehsil_count'] for x in roster_counts),'all_group_counts_match':all(x['count_match'] for x in roster_counts)},
  'current_mp_roster_diagnostics': {'owned_district_scopes_attempted':len(mp_pages),'successful_pages':sum(x['http_status']==200 for x in mp_pages),'pages_with_tehsil_roster_table':sum(x['has_tehsil_roster_table'] for x in mp_pages),'pages':mp_pages,'limits':['Pages are current roster context only, not legal polygon evidence.','Seoni page claims eight tahsils while its table lists nine tehsil rows.','The page set is incomplete and includes 404, empty, and document-only results; it does not establish roster completeness or footprint identity.']},
  'per_location_diagnostics': per_location,
  'limits': ['Topological equality compares retained 2018 source geometry to Atlas geometry; it does not establish current legal boundaries or correctness.', 'The publisher metadata declares 6,836 ADM3 records while the retained collection contains 6,822; completeness remains unresolved.', 'No current official legal polygon dataset and exact crosswalk was available for this reproduction.', 'Madhya Pradesh NIC tehsil pages are incomplete or inconsistent; see the hashed per-page diagnostics and restoration instructions.']
}
RESULT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
print(json.dumps(report, indent=2, ensure_ascii=False))

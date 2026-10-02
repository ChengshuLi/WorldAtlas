import json,gzip,hashlib,math
from pathlib import Path
from shapely import from_wkb
P=Path(__file__).parent;result=json.load(open(P/'result.json'));original=json.load(open(P/'scoped-entries.json'));assert len(result['entries'])==46 and {e['name'] for e in result['entries']}=={e['name'] for e in original};assert len({e['name'] for e in result['entries']})==46
count=0
for r in json.load(open(P/'gazetteer-source-inventory.json')):
 if r.get('http_status')!=200:continue
 b=gzip.decompress((P/r['compressed_path']).read_bytes());assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'];count+=1
assert count==105
geo=json.load(open(P/'geonames-source-inventory.json'))
for r in geo:
 assert 'error'not in r
 b=gzip.decompress((P/r['source_island_lines_path']).read_bytes());assert hashlib.sha256(b).hexdigest()==r['source_island_lines_sha256'];assert len(b.splitlines())==r['island_records'];assert len(json.load(open(P/r['island_records_path'])))==r['island_records']
assert len(geo)==25
cs=json.load(open(P/'components.json'))['components'];seen=set();families={}
for c in cs:
 key=(c['family'],c['gshhg_id']);assert key not in seen;seen.add(key);families[c['family']]=families.get(c['family'],0)+1
 b=gzip.decompress((P/c['candidate_geometry_path']).read_bytes());assert hashlib.sha256(b).hexdigest()==c['geometry_wkb_sha256'];g=from_wkb(b);assert g.is_valid and not g.is_empty;assert all(math.isfinite(a) for a in g.bounds);assert 0<=c['target_region_share']<=1
for e in result['entries']:assert families[e['name']]==e['independent_source_component_counts']['all_sizes']
m=json.load(open(P/'modern-candidate-review.json'));assert len(m['query_results'])==9 and len(m['candidates'])==26
for q in m['query_results']:
 b=gzip.decompress((P/q['original_path']).read_bytes());assert hashlib.sha256(b).hexdigest()==q['original_sha256']
 for r in q['closed_rings']:assert r['coordinates'][0]==r['coordinates'][-1] and all(x.get('version') and x.get('timestamp') for x in r['way_versions'])
for c in m['candidates']:
 b=gzip.decompress((P/c['geometry_path']).read_bytes());assert hashlib.sha256(b).hexdigest()==c['geometry_wkb_sha256'];g=from_wkb(b);assert g.is_valid and not g.is_empty and c['polygon_inside_query_bbox'];assert not c['installation_authorized'];assert 0<=c['current_location_union_overlap_share']<=1
 if c['approved_region_id'] is None:assert c['query']=='Minamitorishima'
 if 'source-candidate-missing-land' in c['status']:assert c['current_location_union_overlap_share']<.01 and not c['all_current_locations_within_0_001_degree']
assert m['summary']['missing_candidates']==22 and m['summary']['unresolved_named_route_candidates']==1 and m['summary']['inland_water_open_candidates']==0
water=json.load(open(P/'water-mask-review.json'));assert len(water['candidate_sources'])==11
for w in water['candidate_sources']:
 b=gzip.decompress((P/w['dryland_geometry_path']).read_bytes());assert hashlib.sha256(b).hexdigest()==w['dryland_geometry_sha256'];assert w['dryland_area_km2']<=w['outer_source_area_km2']+1e-9
checks=dict(version=1,verified_on='2026-10-02',complete_scoped_routes=46,original_gazetteer_pages_verified=105,geonames_original_selected_country_lines_verified=25,source_polygon_assets_verified=len(cs),modern_raw_xml_queries_verified=9,modern_dryland_candidate_assets_verified=26,full_source_water_hierarchy_masks_verified=11,geometry_and_source_hash_checks_passed=True,installed_changes=0,whole_archipelago_or_regional_approval=False)
(P/'validation.json').write_text(json.dumps(checks,separators=(',',':'))+'\n');print(json.dumps(checks))

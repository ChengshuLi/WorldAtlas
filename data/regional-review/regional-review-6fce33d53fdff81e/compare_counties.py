#!/usr/bin/env python3
"""Reproduce issue #432 identity/parent crosswalk and geometric screening.
Requires project's pinned Shapely/pyproj requirements. Never repairs geometry.
"""
import hashlib, json
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import transform
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = json.loads((OUT/'baseline-membership.json').read_text())
EXPECTED = {
 'geoBoundaries-2018': ('sources/geoboundaries-2018/geoBoundaries-USA-ADM2.geojson','81fdd384df8012e5007ed2994a8ab306352f3c48e32cd8ea99182195e8647f43'),
 'tigerweb-2026-counties': ('sources/census-tigerweb-2026/counties-ar-la-ok-2026.geojson','d0b1012ad2c7f8a4841e08f455a1359eb85402b045667e58282e7e2dc34eb7db'),
 'tiger-2025-coastal-sample': ('sources/census-tiger-2025/counties-coastal-sample-2025.geojson','8ee2607cad936795ea7914d0851260de95dfdc3a2a066687e62949a068c4aad5'),
}
for name,(rel,digest) in EXPECTED.items():
 raw=(OUT/rel).read_bytes()
 assert hashlib.sha256(raw).hexdigest()==digest, f'{name} digest mismatch'
state_fips={'framework:province:arkansas:6fd10bbe861b':'05','framework:province:louisiana:d516859f0536':'22','framework:province:oklahoma:61cefcfa5f2e':'40'}
ids={r['id'] for r in BASE['rows']}
atlas={}
for p in sorted((ROOT/'data/geography').glob('part-*.json')):
 for f in json.loads(p.read_text())['features']:
  if f['properties']['id'] in ids: atlas[f['properties']['id']]=f
assert len(atlas)==216
old=json.loads((OUT/EXPECTED['geoBoundaries-2018'][0]).read_text())['features']
old_by_id={f['properties']['shapeID']:f for f in old}
current=json.loads((OUT/EXPECTED['tigerweb-2026-counties'][0]).read_text())['features']
archive_sample=json.loads((OUT/EXPECTED['tiger-2025-coastal-sample'][0]).read_text())['features']
archive_by_geoid={f['properties']['GEOID']:f for f in archive_sample}
bykey={}
for f in current:
 p=f['properties']; bykey.setdefault((p['STATE'],p['BASENAME'].casefold()),[]).append(f)
assert len(current)==216
# Negative control: exact name alone is ambiguous; Louisiana Lafayette must be 22055, not Arkansas 05073.
assert bykey[('22','lafayette')][0]['properties']['GEOID']=='22055'
assert bykey[('05','lafayette')][0]['properties']['GEOID']=='05073'
assert bykey[('22','lafayette')][0]['properties']['GEOID'] != bykey[('05','lafayette')][0]['properties']['GEOID']
projector=Transformer.from_crs('EPSG:4326','EPSG:5070',always_xy=True).transform
rows=[]
for row in BASE['rows']:
 a=atlas[row['id']]; g=old_by_id[row['original_id']]; state=state_fips[row['parent_id']]
 matches=bykey.get((state,row['name'].casefold()),[])
 assert len(matches)==1, (row['id'],len(matches))
 c=matches[0]; cp=c['properties']; op=g['properties']
 assert op['shapeID']==row['original_id'] and op['shapeName']==row['name'] and op['shapeGroup']=='USA' and op['shapeType']=='ADM2', row['id']
 assert cp['STATE']==state and cp['GEOID']==state+cp['COUNTY']
 ga=shape(a['geometry']); gg=shape(g['geometry']); gc=shape(c['geometry'])
 assert ga.is_valid and gg.is_valid and gc.is_valid, row['id']
 pa=transform(projector,ga); pg=transform(projector,gg); pc=transform(projector,gc)
 atlas_source_iou=pa.intersection(pg).area/pa.union(pg).area
 iou=pa.intersection(pc).area/pa.union(pc).area
 tiger2025_iou=None
 if cp['GEOID'] in archive_by_geoid:
  check=shape(archive_by_geoid[cp['GEOID']]['geometry']); projected_check=transform(projector,check)
  tiger2025_iou=round(projected_check.intersection(pc).area/projected_check.union(pc).area,9)
 rows.append({'id':row['id'],'atlas_name':row['name'],'state_fips':state,'parent_framework_id':row['parent_id'],'census_geoid':cp['GEOID'],'census_name':cp['NAME'],'census_basename':cp['BASENAME'],'census_lsadc':cp['LSADC'],'census_funcstat':cp['FUNCSTAT'],'census_countycc':cp['COUNTYCC'],'geoBoundaries_shapeID':op['shapeID'],'geoBoundaries_shapeName':op['shapeName'],'identity_status':'unique-state-plus-exact-name','parent_code_match':True,'tiger2025_archive_sample_geoid':cp['GEOID'] if tiger2025_iou is not None else None,'tiger2025_vs_tigerweb2026_sample_iou':tiger2025_iou,'atlas_geometry_structurally_equal_to_raw_geoboundaries':a['geometry']==g['geometry'],'metric_method':'Atlas and Census GeoJSON RFC lon/lat; EPSG:5070; no geometry repair','geometry_metrics':{'atlas_area_km2':round(pa.area/1e6,5),'geoboundaries_raw_area_km2':round(pg.area/1e6,5),'census_area_km2':round(pc.area/1e6,5),'atlas_vs_geoboundaries_raw_iou':round(atlas_source_iou,8),'atlas_vs_geoboundaries_raw_symmetric_difference_km2':round(pa.symmetric_difference(pg).area/1e6,5),'intersection_over_union':round(iou,8),'symmetric_difference_km2':round(pa.symmetric_difference(pc).area/1e6,5)}})
with (OUT/'county-comparisons.jsonl').open('w') as fp:
 for r in rows: fp.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n')
# Confirm full official division membership including the Texas neighbor (outside #432).
states=json.loads((OUT/'sources/census-tigerweb-2026/state-parents-division-query.geojson').read_text())['features']
state_members=sorted((f['properties']['GEOID'],f['properties']['NAME'],f['properties']['REGION'],f['properties']['DIVISION']) for f in states)
assert state_members==[('05','Arkansas','3','7'),('22','Louisiana','3','7'),('40','Oklahoma','3','7'),('48','Texas','3','7')], state_members
watch={'22023','22045','22057','22075','22087','22101','22109','22113'}
assessments=[]; multipart=[]; components={}
for r in rows:
 geom=shape(atlas[r['id']]['geometry']); count=len(geom.geoms) if hasattr(geom,'geoms') else 1
 components[f'{geom.geom_type}:{count}']=components.get(f'{geom.geom_type}:{count}',0)+1
 if count>1: multipart.append({'id':r['id'],'name':r['atlas_name'],'geoid':r['census_geoid'],'components':count})
 r['classification']='insufficient-evidence'
 r['classification_basis']='Census independently supports the present county-equivalent identity/tier/parent, but the raw-to-Atlas geometry processing is undocumented and the source-catalog hash is unreconciled; cross-vintage spatial screens do not adjudicate legal boundary history.'
 r['boundary_signal']='large-coastal-screen-difference-follow-up' if r['census_geoid'] in watch else ('screen-difference-for-manual-check' if r['geometry_metrics']['intersection_over_union']<0.98 else 'no-large-screen-difference-not-proof-of-exact-boundaries')
 r['atlas_geometry_type']=geom.geom_type; r['atlas_component_count']=count; assessments.append(r)
with (OUT/'county-assessments.jsonl').open('w') as fp:
 for r in assessments: fp.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n')
summary={'scope_count':len(rows),'classification_counts':{'insufficient-evidence':len(rows)},'state_counts':{fips:sum(r['state_fips']==fips for r in rows) for fips in ('05','22','40')},'unique_geoid_count':len({r['census_geoid'] for r in rows}),'state_division_members':state_members,'baseline_vs_geoboundaries_min_iou':min(r['geometry_metrics']['atlas_vs_geoboundaries_raw_iou'] for r in rows),'baseline_vs_geoboundaries_avg_iou':round(sum(r['geometry_metrics']['atlas_vs_geoboundaries_raw_iou'] for r in rows)/len(rows),8),'baseline_vs_geoboundaries_max_iou':max(r['geometry_metrics']['atlas_vs_geoboundaries_raw_iou'] for r in rows),'atlas_geometries_coordinate_structure_different_from_source_count':sum(not r['atlas_geometry_structurally_equal_to_raw_geoboundaries'] for r in rows),'baseline_vs_geoboundaries_below_0_99_count':sum(r['geometry_metrics']['atlas_vs_geoboundaries_raw_iou']<0.99 for r in rows),'baseline_vs_census2026_min_iou':min(r['geometry_metrics']['intersection_over_union'] for r in rows),'baseline_vs_census2026_below_0_98_count':sum(r['geometry_metrics']['intersection_over_union']<0.98 for r in rows),'coastal_followup_ids':sorted(r['census_geoid'] for r in rows if r['boundary_signal']=='large-coastal-screen-difference-follow-up'),'tiger2025_sample_count':sum(r['tiger2025_vs_tigerweb2026_sample_iou'] is not None for r in rows),'tiger2025_sample_min_iou':min(r['tiger2025_vs_tigerweb2026_sample_iou'] for r in rows if r['tiger2025_vs_tigerweb2026_sample_iou'] is not None),'negative_control':{'same_name':'Lafayette','Louisiana_expected_geoid':bykey[('22','lafayette')][0]['properties']['GEOID'],'Arkansas_distinct_geoid':bykey[('05','lafayette')][0]['properties']['GEOID']}}
(OUT/'comparison-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(OUT/'geometry-review.json').write_text(json.dumps({'scope_count':len(rows),'valid_baseline_geometries':len(atlas),'geometry_type_component_counts':dict(sorted(components.items())),'multipart_units':multipart,'interpretation':'Multipart geometry is a screen only; it may represent valid detached islands or geometry treatment. It is not classified as a defect without dated source evidence.'},indent=2)+'\n')
print(json.dumps(summary,indent=2))

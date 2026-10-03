#!/usr/bin/env python3
"""Compare current Madagascar atlas scope with OCHA COD-AB reviewed 2026 layer."""
import json,gzip,pathlib,unicodedata,re
from shapely.geometry import shape
from shapely.ops import transform,unary_union
from pyproj import Transformer
HERE=pathlib.Path(__file__).resolve().parent; ROOT=HERE.parents[2]
S=json.loads((HERE/'issue-scope.json').read_text())
parts=json.loads((ROOT/'data/world-index.json').read_text())['parts']
cur={}
for part in parts:
 for f in json.loads((ROOT/'data'/part).read_text())['features']:
  if f['id'] in S['member_location_ids']:cur[f['id']]=f
H={x['id']:x for x in json.loads((ROOT/'data/hierarchy.json').read_text())}
def load(fn):return json.loads(gzip.decompress((HERE/'sources'/fn).read_bytes()))['features']
def norm(s):return re.sub(r'[^a-z0-9]+','',unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower())
tr=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform
def eq(f):return transform(tr,shape(f['geometry']))
def valid(g):return g if g.is_valid else g.make_valid()
def metric(a,b):
 a=valid(a);b=valid(b);u=a.union(b).area
 return {'source_area_km2':a.area/1e6,'current_area_km2':b.area/1e6,'symmetric_difference_percent':100*a.symmetric_difference(b).area/u if u else 0,'relative_area_change_percent':100*(b.area-a.area)/a.area if a.area else None,'source_valid':a.is_valid,'current_valid':b.is_valid}
new2=load('mdg-COD-AB-ADM2-2026-reviewed.geojson.gz');new1=load('mdg-COD-AB-ADM1-2026-reviewed.geojson.gz')
current2=[f for i,f in cur.items() if i.startswith('gb:MDG:ADM2:')]
by_name={norm(f['properties']['adm2_name']):f for f in new2}; new2geoms={norm(f['properties']['adm2_name']):eq(f) for f in new2}
rows=[]
for f in current2:
 p=f['properties']; name=p['name']; n=norm(name); o=by_name.get(n)
 if not o: rows.append({'atlas_id':f['id'],'atlas_name':name,'match':False}); continue
 met=metric(new2geoms[n],eq(f))
 rows.append({'atlas_id':f['id'],'atlas_name':name,'CODAB_ADM2_PCODE':o['properties']['adm2_pcode'],'CODAB_ADM1_name':o['properties']['adm1_name'],'CODAB_ADM1_PCODE':o['properties']['adm1_pcode'],'match':True,**met})
missing=[f for f in new2 if norm(f['properties']['adm2_name']) not in {norm(x['properties']['name']) for x in current2}]
impact=[]
for n in missing:
 g=eq(n); hits=[]
 for f in current2:
  i=g.intersection(eq(f)).area/1e6
  if i>0.01:hits.append({'atlas_id':f['id'],'atlas_name':f['properties']['name'],'intersection_km2':i,'intersection_of_new_unit_percent':100*(i*1e6)/g.area if g.area else 0})
 impact.append({'source_name':n['properties']['adm2_name'],'source_pcode':n['properties']['adm2_pcode'],'source_parent':n['properties']['adm1_name'],'area_km2':g.area/1e6,'overlapping_current_locations':sorted(hits,key=lambda x:x['intersection_km2'],reverse=True)})
# Province group structure compare against the newly reviewed source ADM1 set, highlighting explicit old-vintage name changes.
current_parent_names=sorted({x['province_name'] for x in json.loads((HERE/'subject-inventory.jsonl').read_text().splitlines()[0:1][0])}) if False else []
current_parent={}
for i,f in cur.items():
 if i.startswith('gb:MDG:ADM2:'):
  p=f['properties']['parent_id']; current_parent.setdefault(p,H.get(p,{}).get('name'))
new1_names={norm(f['properties']['adm1_name']):f['properties']['adm1_name'] for f in new1}
old_current=sorted(set(current_parent.values()),key=str.casefold)
report={'source':'OCHA COD-AB Madagascar current resource package version 01; dataset was reviewed 2026-07-06, administrative limits stated valid from 2018-08-10; CC BY-IGO','source_adm2_count':len(new2),'current_assigned_mdg_adm2_count':len(current2),'current_named_adm2_matches':sum(x['match'] for x in rows),'new_unmatched_source_adm2':impact,'per_matched_location':rows,'current_old_parent_names':old_current,'source_adm1_count':len(new1),'source_adm1_names':sorted(f['properties']['adm1_name'] for f in new1),'current_parent_name_count':len(old_current),'current_parent_names_missing_in_CODAB_normalized':[n for n in old_current if norm(n) not in new1_names],'CODAB_adm1_names_missing_from_current_parent_normalized':[n for n in sorted(new1_names.values()) if norm(n) not in {norm(x) for x in old_current}],'method':{'projection':'EPSG:6933 equal-area','comparison':'Name-matched exact COD-AB ADM2 unit polygon versus pinned current atlas member geometry; MakeValid only on ephemeral comparison copies. Unmatched current/source units remain explicit. New unmatched units intersected all current Madagascar-assigned feature polygons; intersections are diagnostic only.','limits':'OCHA metadata says current dataset is valid from 2018 and reviewed in 2026, not that it is a 2026 legal boundary gazette. Naming/count and geometry differences trigger source-history reconciliation, not unilateral edit.'}}
(HERE/'madagascar-current-COD-AB-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('OCHA ADM2/ADM1:',len(new2),len(new1),'matches',sum(x['match'] for x in rows),'unmatched',impact)
print('parent names',old_current)
print('ADM1 source names',report['source_adm1_names'])
print('name mismatches',report['current_parent_names_missing_in_CODAB_normalized'],report['CODAB_adm1_names_missing_from_current_parent_normalized'])
print('max source/current diff',max(x.get('symmetric_difference_percent',0) for x in rows))
# Entire region-parent source footprint versus bottom-up location unions; no parent polygons are edited.
from shapely.ops import unary_union
by_current_parent={}
for ident,f in cur.items():
 if ident.startswith('gb:MDG:ADM2:'):
  pid=f['properties']['parent_id'];by_current_parent.setdefault(pid,[]).append(f)
parent_unions={pid:unary_union([eq(f) for f in fs]) for pid,fs in by_current_parent.items()}
new1_by_name={norm(f['properties']['adm1_name']):f for f in new1}
parent_rows=[]
for name,srcf in sorted(new1_by_name.items()):
 sg=eq(srcf); hits=[]
 for pid,cg in parent_unions.items():
  inter=valid(sg).intersection(valid(cg)).area
  if inter>10000:
   pp=H[pid]
   hits.append({'current_province_id':pid,'current_province_name':pp['name'],'intersection_km2':inter/1e6,'percent_of_source_region':100*inter/valid(sg).area if valid(sg).area else 0,'percent_of_current_parent':100*inter/valid(cg).area if valid(cg).area else 0})
 parent_rows.append({'source_name':srcf['properties']['adm1_name'],'source_pcode':srcf['properties']['adm1_pcode'],'valid_on':srcf['properties']['valid_on'],'source_geometry_area_km2':valid(sg).area/1e6,'normalized_exact_current_name_match':next((H[pid]['name'] for pid in by_current_parent if norm(H[pid]['name'])==name),None),'spatial_intersections_with_current_parent_descendant_unions':sorted(hits,key=lambda x:x['intersection_km2'],reverse=True)})
report['region_parent_source_crosswalk']={'source_admin1_count':len(new1),'current_scoped_parent_count':len(parent_unions),'records':parent_rows,'interpretation':'Intersection matrix is a diagnostic crosswalk for all source and current parent groups. It does not select a replacement parent, infer legal authority or mutate the location-determined hierarchy.'}
(HERE/'madagascar-current-COD-AB-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('region overlap top per-source')
for r in parent_rows:
 print(r['source_name'],[(x['current_province_name'],round(x['percent_of_source_region'],2)) for x in r['spatial_intersections_with_current_parent_descendant_unions'][:3]])
# Whole Madagascar ADM2/ADM1 union comparisons and shared-edge overlap checks.
current_union=unary_union([eq(f) for f in current2]);source2_union=unary_union([new2geoms[norm(f['properties']['adm2_name'])] for f in new2]);source1_geoms=[eq(f) for f in new1];source1_union=unary_union(source1_geoms);current1_union=unary_union(list(parent_unions.values()))
def union_metric(a,b):
 a=valid(a);b=valid(b);u=a.union(b).area
 return {'source_union_area_km2':a.area/1e6,'current_union_area_km2':b.area/1e6,'intersection_percent_of_source_union':100*a.intersection(b).area/a.area if a.area else None,'symmetric_difference_percent':100*a.symmetric_difference(b).area/u if u else 0,'relative_area_change_percent':100*(b.area-a.area)/a.area if a.area else None,'source_valid':a.is_valid,'current_valid':b.is_valid,'source_component_count':len(a.geoms) if hasattr(a,'geoms') else 1,'current_component_count':len(b.geoms) if hasattr(b,'geoms') else 1}
def overlaps(geoms,labels,threshold_km2=.001):
 t=STRtree(geoms);out=[]
 for i,g in enumerate(geoms):
  for jx in t.query(g):
   j=int(jx)
   if j<=i:continue
   a=g.intersection(geoms[j]).area/1e6
   if a>threshold_km2:out.append({'a':labels[i],'b':labels[j],'intersection_km2':a})
 return out
from shapely.strtree import STRtree
report['partition_integrity']={'source_ADM2_feature_count':len(new2),'source_ADM2_feature_component_count_sum':sum(len(shape(f['geometry']).geoms) if shape(f['geometry']).geom_type=='MultiPolygon' else 1 for f in new2),'current_ADM2_feature_count':len(current2),'current_ADM2_feature_component_count_sum':sum(len(shape(f['geometry']).geoms) if shape(f['geometry']).geom_type=='MultiPolygon' else 1 for f in current2),'source_ADM2_interior_overlaps_over_0_001_km2':overlaps([new2geoms[norm(f['properties']['adm2_name'])] for f in new2],[f['properties']['adm2_name'] for f in new2]),'source_ADM1_interior_overlaps_over_0_001_km2':overlaps(source1_geoms,[f['properties']['adm1_name'] for f in new1]),'all_120_ADM2_union_vs_current_119_member_union':union_metric(source2_union,current_union),'all_24_ADM1_union_vs_current_22_parent_descendant_union':union_metric(source1_union,current1_union),'method':'Pairwise administrative source overlaps over 0.001 km2 reported for review. All union areas and intersections use equal-area EPSG:6933. Small internal overlaps below threshold, holes, offshore completeness and legal status need separate inspection.'}
(HERE/'madagascar-current-COD-AB-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('partition integrity',json.dumps(report['partition_integrity'],ensure_ascii=False,indent=2)[:3000])

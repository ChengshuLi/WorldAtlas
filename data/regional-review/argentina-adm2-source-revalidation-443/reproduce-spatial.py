#!/usr/bin/env python3
"""Scoped 2020 geoBoundaries / current official Georef polygon crosswalk.

Run from repository root with Shapely 2.x and pyproj installed:
  python data/regional-review/argentina-adm2-source-revalidation-443/reproduce-spatial.py
The 214-feature 2020 subset is lawfully retained here with restoration provenance linked
to #443's immutable full object. All of the 529 current Georef polygons are
used as comparison and neighbor context. Equal-area EPSG:6933 intersection shares
are screening evidence, not legal adjudication or publication approval.
"""
import csv, json, pathlib
from collections import Counter
import unicodedata
from shapely.geometry import shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree
from pyproj import Transformer

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWN = ROOT / 'data/regional-review/argentina-adm2-source-revalidation-443'
PARENT = ROOT / 'data/regional-review/regional-review-7cf674a63057d43f'
OLD = OWN / 'source/geoBoundaries-2020-scoped-214.geojson'
CURRENT = OWN / 'source/Georef-current/departamentos.geojson'
CSV = PARENT / 'findings/scoped-location-review.csv'
PROVINCE_CSV = PARENT / 'findings/scoped-province-review.csv'
OUT = OWN / 'findings'
OUT.mkdir(exist_ok=True)

with CSV.open(encoding='utf-8', newline='') as f:
    rows = list(csv.DictReader(f))
scoped = [r for r in rows if r['location_id'].startswith('gb:ARG:ADM2:')]
with PROVINCE_CSV.open(encoding='utf-8', newline='') as f:
    province_names = {r['province_id']: r['official_name_for_name_check'] for r in csv.DictReader(f)}
expected_ids = {r['original_id']: r for r in scoped}
with OLD.open(encoding='utf-8') as f:
    old = json.load(f)
old_features = old['features']
old_by = {ft['properties']['shapeID']: ft for ft in old_features}
assert len(old_features) == 214 and len(old_by) == 214
assert set(expected_ids) == set(old_by)

with CURRENT.open(encoding='utf-8') as f:
    current = json.load(f)['features']
assert len(current) == 529 and len({x['properties']['id'] for x in current}) == 529
project = Transformer.from_crs('EPSG:4326', 'EPSG:6933', always_xy=True).transform
def norm_name(v):
    return ''.join(c for c in unicodedata.normalize('NFKD', v.casefold()) if not unicodedata.combining(c))
def fixed(value, decimals): return f'{value:.{decimals}f}'
current_geoms = [transform(project, shape(ft['geometry'])) for ft in current]
current_byid = {ft['properties']['id']: (ft, geom) for ft, geom in zip(current, current_geoms)}
current_name_candidates = {}
for ft, geom in zip(current, current_geoms): current_name_candidates.setdefault(norm_name(ft['properties']['nombre']), []).append((ft,geom))

out_rows = []
scoped_current_pair_overlaps = {}
for source_id in sorted(expected_ids):
    rec = expected_ids[source_id]
    oldft = old_by[source_id]
    oldgeom = transform(project, shape(oldft['geometry']))
    if oldgeom.is_empty or not oldgeom.is_valid or oldgeom.area <= 0:
        old_valid = False
    else: old_valid = True
    hits=[]
    for ft, geom in zip(current, current_geoms):
        if oldgeom.intersects(geom):
            area = oldgeom.intersection(geom).area
            if area > 1.0: # suppress only sub-square-metre numerical slivers
                p=ft['properties']
                hits.append((area, p['id'], p['nombre'], p['provincia']['nombre'], p['categoria']))
    hits.sort(reverse=True)
    union_area = sum(h[0] for h in hits)
    hit_geoms = [(current_byid[h[1]][0],current_byid[h[1]][1]) for h in hits]
    for i in range(len(hit_geoms)):
        for j in range(i+1,len(hit_geoms)):
            fta,ga=hit_geoms[i]; ftb,gb=hit_geoms[j]
            overlap=ga.intersection(gb).intersection(oldgeom).area
            if overlap>1:
                ida,idb=sorted((fta['properties']['id'],ftb['properties']['id']))
                pair=scoped_current_pair_overlaps.setdefault((ida,idb),{'name_a':fta['properties']['nombre'] if ida==fta['properties']['id'] else ftb['properties']['nombre'],'province_a':fta['properties']['provincia']['nombre'] if ida==fta['properties']['id'] else ftb['properties']['provincia']['nombre'],'category_a':fta['properties']['categoria'] if ida==fta['properties']['id'] else ftb['properties']['categoria'],'name_b':ftb['properties']['nombre'] if idb==ftb['properties']['id'] else fta['properties']['nombre'],'province_b':ftb['properties']['provincia']['nombre'] if idb==ftb['properties']['id'] else fta['properties']['provincia']['nombre'],'category_b':ftb['properties']['categoria'] if idb==ftb['properties']['id'] else fta['properties']['categoria'],'overlap_area_m2':0.0,'scoped_ids':set()})
                pair['overlap_area_m2']+=overlap;pair['scoped_ids'].add(source_id)
    top = hits[0] if hits else (0,'','','','')
    named = current_name_candidates.get(norm_name(oldft['properties']['shapeName']), [])
    named_hits = sorted([(oldgeom.intersection(g).area,ft,g) for ft,g in named], key=lambda z:z[0], reverse=True)
    named_best = named_hits[0] if named_hits else (0,None,None)
    out_rows.append({
      'atlas_id':rec['location_id'],'atlas_name':rec['atlas_name'],'atlas_parent_id':rec['parent_id'],
      'source_2020_shape_id':source_id,'source_2020_name':oldft['properties']['shapeName'],
      'source_2020_admin_level':oldft['properties']['shapeType'],'source_2020_geometry_type':oldft['geometry']['type'],'source_2020_component_count':len(oldgeom.geoms) if oldgeom.geom_type == 'MultiPolygon' else 1,'source_2020_hole_count':sum(len(poly.interiors) for poly in (oldgeom.geoms if oldgeom.geom_type == 'MultiPolygon' else [oldgeom])),'source_2020_valid':old_valid,
      'old_area_km2_equal_area':fixed(oldgeom.area/1e6,6),
      'current_intersecting_feature_count':len(hits),'top_current_georef_id':top[1],
      'top_current_name':top[2],'top_current_province':top[3],'top_current_category':top[4],
      'top_share_of_old_area':fixed(top[0]/oldgeom.area,9) if oldgeom.area else '0.000000000',
      'current_union_coverage_of_old':fixed(unary_union([current_byid[h[1]][1] for h in hits]).intersection(oldgeom).area/oldgeom.area,9) if oldgeom.area and hits else '0.000000000',
      'current_overlap_excess_share':fixed(max(0, union_area-unary_union([current_byid[h[1]][1] for h in hits]).intersection(oldgeom).area)/oldgeom.area,9) if oldgeom.area and hits else '0.000000000',
      'all_current_intersections':json.dumps([{'id':h[1],'name':h[2],'province':h[3],'category':h[4]} for h in hits],ensure_ascii=False,separators=(',',':')),
      'same_normalized_name_candidate_count':len(named_hits),
      'best_same_name_candidate_id':named_best[1]['properties']['id'] if named_best[1] else '',
      'best_same_name_candidate_province':named_best[1]['properties']['provincia']['nombre'] if named_best[1] else '',
      'best_same_name_candidate_share_of_old_area':fixed(named_best[0]/oldgeom.area,9) if oldgeom.area and named_hits else '0.000000000',
      'best_same_name_candidate_symmetric_difference_share':fixed(oldgeom.symmetric_difference(named_best[2]).area/oldgeom.area,9) if oldgeom.area and named_hits else '0.000000000',
      'same_name_candidates':json.dumps([{'id':ft['properties']['id'],'province':ft['properties']['provincia']['nombre'],'category':ft['properties']['categoria']} for a,ft,g in named_hits],ensure_ascii=False,separators=(',',':')),
      'over_1sqm_sliver_count':sum(1 for h in hits if h[0] < 100),
      'top_five_current_hits':json.dumps([{'id':h[1],'name':h[2],'province':h[3],'category':h[4]} for h in hits[:5]],ensure_ascii=False,separators=(',',':')),
      'interpretation':'Overlay screen only. Georef is a current statistical/unit-normalization layer; positive-area winners do not establish legal boundary lineage or resolve 2020 vintage change.'
    })
with (OUT/'scoped-2020-to-current-georef-overlay.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(out_rows[0]));w.writeheader();w.writerows(out_rows)

summary={
 'method':'EPSG:6933 equal-area positive-area intersections; 1 m2 threshold; no automatic topology repair',
 'scoped_2020_feature_count':len(old_features),'scoped_unique_shapeID_count':len(old_by),'current_feature_count':len(current),
 'scoped_old_feature_count':len(scoped),'scoped_geometry_types':dict(Counter(ft['geometry']['type'] for ft in old_features)),
 'invalid_scoped_old_geometry_count':sum(not shape(ft['geometry']).is_valid for ft in old_features),
 'empty_scoped_old_geometry_count':sum(shape(ft['geometry']).is_empty for ft in old_features),
 'invalid_current_geometry_count':sum(not shape(ft['geometry']).is_valid for ft in current),
 'current_categories':dict(Counter(ft['properties']['categoria'] for ft in current)),
 'scoped_top_province_counts':dict(Counter(x['top_current_province'] for x in out_rows)),
 'scoped_parent_disagreement_ids':[x['atlas_id'] for x in out_rows if province_names.get(x['atlas_parent_id']) != x['top_current_province']],
 'scoped_low_coverage_ids':[x['atlas_id'] for x in out_rows if float(x['current_union_coverage_of_old']) < .99],
 'scoped_exact_normalized_top_name_matches':sum(norm_name(x['source_2020_name']) == norm_name(x['top_current_name']) for x in out_rows),
 'scoped_same_normalized_name_candidates':sum(x['same_normalized_name_candidate_count'] > 0 for x in out_rows),
 'scoped_unique_same_normalized_name_candidates':sum(x['same_normalized_name_candidate_count'] == 1 for x in out_rows),
 'scoped_exact_same_name_candidate_geometry_symdiff_gt_5pct':sum(x['same_normalized_name_candidate_count'] == 1 and float(x['best_same_name_candidate_symmetric_difference_share']) > .05 for x in out_rows),
 'scoped_current_source_overlap_pairs_gt_1sqm':len(scoped_current_pair_overlaps),
 'scoped_current_source_overlap_pairs_over_1hectare':sum(v['overlap_area_m2']>=10000 for v in scoped_current_pair_overlaps.values()),
 'scoped_geometry_type_counts':dict(Counter(x['source_2020_geometry_type'] for x in out_rows)),
 'scoped_component_count_total':sum(x['source_2020_component_count'] for x in out_rows),
 'scoped_interior_ring_count_total':sum(x['source_2020_hole_count'] for x in out_rows),
 'scoped_multi_candidate_ids':[x['atlas_id'] for x in out_rows if x['current_intersecting_feature_count'] > 1],
 'limitations':['Current Georef is official but its department level mixes departamentos, partidos and other statistical/territorial categories; it is not a legal-boundary certification.', 'The source years differ (2020 vs current API generation) and individual polygons may have changed.', 'Area overlays can expose mismatch candidates but cannot identify legal intent, validate coastal/island omissions, or adjudicate sub-resolution linework.', 'The full source unit counts are not comparable as direct equality because sources use different schemas and category rules.']
}
pair_rows=[]
for (ida,idb),v in sorted(scoped_current_pair_overlaps.items()): pair_rows.append({**{k:x for k,x in v.items() if k!='scoped_ids'},'georef_id_a':ida,'georef_id_b':idb,'scoped_subject_ids':'|'.join(sorted('gb:ARG:ADM2:'+x for x in v['scoped_ids'])),'interpretation':'Positive-area intersection inside at least one reviewed 2020 footprint; possible current-source overlap or vintage offset, not adjudicated.'})
if pair_rows:
 with (OUT/'scoped-current-georef-positive-area-overlaps.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(pair_rows[0]));w.writeheader();w.writerows(pair_rows)
old_overlap_rows=[]
scoped_items=sorted(old_by.items())
scoped_geoms=[transform(project,shape(ft['geometry'])) for _,ft in scoped_items]
tree=STRtree(scoped_geoms)
for i,(ida,fta) in enumerate(scoped_items):
 ga=scoped_geoms[i]
 for j in tree.query(ga,predicate='intersects'):
  j=int(j)
  if j<=i: continue
  idb,ftb=scoped_items[j]; area=ga.intersection(scoped_geoms[j]).area
  if area>1:
   old_overlap_rows.append({'shapeid_a':ida,'name_a':fta['properties']['shapeName'],'shapeid_b':idb,'name_b':ftb['properties']['shapeName'],'intersection_area_m2':round(area,3),'interpretation':'Positive area between two 2020 source subjects; source partition overlap candidate.'})
oldcols=['shapeid_a','name_a','shapeid_b','name_b','intersection_area_m2','interpretation']
with (OUT/'scoped-2020-internal-overlaps.csv').open('w',encoding='utf-8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=oldcols);w.writeheader();w.writerows(old_overlap_rows)
summary['scoped_2020_internal_overlap_pairs_gt_1sqm']=len(old_overlap_rows)
summary['scoped_2020_internal_overlap_pairs_over_1hectare']=sum(float(x['intersection_area_m2'])>=10000 for x in old_overlap_rows)
(OUT/'spatial-reproduction-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))

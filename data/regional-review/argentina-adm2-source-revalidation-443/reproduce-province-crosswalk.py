#!/usr/bin/env python3
"""Compare the retained 2006 geoBoundaries ADM1 layer with official current Georef provinces."""
import csv,json,pathlib
from collections import Counter
from shapely.geometry import shape
from shapely.ops import transform,unary_union
from pyproj import Transformer
ROOT=pathlib.Path(__file__).resolve().parents[3]
OWN=ROOT/'data/regional-review/argentina-adm2-source-revalidation-443'
PARENT=ROOT/'data/regional-review/regional-review-7cf674a63057d43f'
with (PARENT/'source/geoBoundaries-ARG-ADM1/geoBoundaries-ARG-ADM1.geojson').open() as f: old=json.load(f)['features']
with (OWN/'source/Georef-current/provincias.geojson').open() as f: current=json.load(f)['features']
project=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform
old_geo=[(ft,transform(project,shape(ft['geometry']))) for ft in old]
current_geo=[(ft,transform(project,shape(ft['geometry']))) for ft in current]
out=[]
for cf,cg in current_geo:
    hits=[]
    for of,og in old_geo:
        inter=og.intersection(cg).area
        if inter>1: hits.append((inter,of,og))
    hits.sort(key=lambda x:x[0],reverse=True)
    union=unary_union([x[2] for x in hits]) if hits else None
    out.append({'current_id':cf['properties'].get('id'),'current_name':cf['properties'].get('nombre'),
      'old_intersecting_feature_count':len(hits),'top_old_name':hits[0][1]['properties'].get('shapeName') if hits else '',
      'top_old_shape_id':hits[0][1]['properties'].get('shapeID') if hits else '',
      'top_old_share_of_current_area':f"{hits[0][0]/cg.area:.9f}" if hits else '0.000000000',
      'old_union_coverage_of_current':f"{union.intersection(cg).area/cg.area:.9f}" if hits else '0.000000000',
      'union_symmetric_difference_share':f"{cg.symmetric_difference(union).area/cg.area:.9f}" if hits else '1.000000000',
      'all_old_positive_overlaps':json.dumps([{'name':h[1]['properties'].get('shapeName'),'shapeID':h[1]['properties'].get('shapeID')} for h in hits],ensure_ascii=False,separators=(',',':'))})
outpath=OWN/'findings/2006-adm1-to-current-province-overlay.csv'
with outpath.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
summary={'old_feature_count':len(old),'old_unique_id_count':len({x['properties'].get('shapeID') for x in old}),
 'current_feature_count':len(current),'current_names':sorted(x['current_name'] for x in out),
 'geometry_types_old':dict(Counter(x['geometry']['type'] for x in old)),
 'invalid_old':sum(not shape(x['geometry']).is_valid for x in old),'invalid_current':sum(not shape(x['geometry']).is_valid for x in current),
 'old_count_below_99pct_current_coverage':sum(float(x['old_union_coverage_of_current'])<.99 for x in out),
 'unmatched_current_jurisdictions':[x['current_name'] for x in out if float(x['old_union_coverage_of_current'])<.99],
 'la_roja_to_current_la_rioja_top_share':float(next(x['top_old_share_of_current_area'] for x in out if x['current_name']=='La Rioja')),
 'buenos_aires_to_current_entre_rios_top_share':float(next(x['top_old_share_of_current_area'] for x in out if x['current_name']=='Entre Ríos')),
 'la_rioja_2006_union_coverage':float(next(x['old_union_coverage_of_current'] for x in out if x['current_name']=='La Rioja')),
 'entre_rios_2006_union_coverage':float(next(x['old_union_coverage_of_current'] for x in out if x['current_name']=='Entre Ríos')),
 'limitations':['The 2006 source lineage is not legally adjudicated; current Georef is sourced from IGN for territorial units but does not certify legal boundaries.',
 'Overlap does not determine the intended spelling or legal status of a historical feature.',
 'No automatic geometry repair; equal-area overlay is screening evidence.']}
(OWN/'findings/province-crosswalk-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))

from pathlib import Path
import json,gzip,hashlib
from shapely import from_wkb,orient_polygons
from shapely.geometry import shape
from pyproj import Geod
P=Path('/tmp/worldatlas-macro-coverage-africa-americas');R=Path('/workspace/WorldAtlas');e=json.load(open('/tmp/worldatlas-africa-americas-entries.json'));targets={i:n['name'] for n in e if n['name'] in ('Ceuta','Melilla') for i in n.get('location_ids',[])};footprints={};geod=Geod(ellps='WGS84')
for fn in json.load(open(R/'data/world-index.json'))['parts']:
 for f in json.load(open(R/'data'/fn))['features']:
  if f['id'] in targets:footprints[f['id']]=shape(f['geometry'])
 if len(footprints)==len(targets):break
land=from_wkb(gzip.decompress((P/'dry-land-candidates/1.wkb.gz').read_bytes()))
def area(g):
 if g.is_empty:return 0
 if g.geom_type=='Polygon':return abs(geod.geometry_area_perimeter(orient_polygons(g))[0])/1e6
 if hasattr(g,'geoms'):return sum(area(c) for c in g.geoms)
 return 0
rows=[]
for i,g in footprints.items():
 a=area(g);b=area(g.intersection(land));rows.append(dict(name=targets[i],location_id=i,reference_footprint_area_km2=a,gshhg_african_dry_land_support_km2=b,source_land_overlap_share=b/a,footprint_sha256=hashlib.sha256(g.wkb).hexdigest(),status='source-land-mainland-footprint-supported' if b/a>.5 else 'source-reference-position-needs-check',scope='Namedmainlandexclave wholeexistingatlasfootprintinindependentcontinentallandmask; doesnot certifyterritoryborderlegalaccuracy oralloffshoreislets'))
(P/'focused-mainland-evidence.json').write_text(json.dumps(rows,separators=(',',':')));print(json.dumps(rows))
report=json.load(open(P/'report.json'))
for r in report['entries']:
 if r['name'] in ('Ceuta','Melilla'):r['focused_mainland_source_comparison']=next(x for x in rows if x['name']==r['name']);r['named_associated_partial_or_near_offset_candidates']=[];r['named_findings']=[]
(P/'report.json').write_text(json.dumps(report,separators=(',',':')));Path('/tmp/worldatlas-macro-coverage-africa-americas.json').write_text(json.dumps(report,separators=(',',':')))

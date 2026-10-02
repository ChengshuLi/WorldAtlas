"""Remove non-area seam artifacts and retain source footnotes as aliases."""
import json,pathlib
from shapely.geometry import shape,mapping,Polygon
from shapely import union_all
D=pathlib.Path(__file__).resolve().parents[1]/'data'
def poly(g):
 if g.is_empty:return Polygon()
 if g.geom_type in ['Polygon','MultiPolygon']:return g
 return union_all([poly(x) for x in getattr(g,'geoms',[])])
counts={'footnotes':0,'nonarea_seams':0}
for part in json.loads((D/'world-index.json').read_text())['parts']:
 p=D/part;x=json.loads(p.read_text())
 for f in x['features']:
  g=shape(f['geometry'])
  if g.geom_type not in ['Polygon','MultiPolygon']:
   clean=poly(g);assert not clean.is_empty and abs(clean.area-g.area)<1e-12;f['geometry']=mapping(clean);f['properties']['metadata']['nonarea_seam_removed']=True;counts['nonarea_seams']+=1
  name=f['properties']['name']
  if name.endswith('*'):
   f['properties']['metadata']['source_name_with_footnote']=name;f['properties']['metadata']['search_aliases']=[name];f['properties']['name']=name.rstrip('*').strip();counts['footnotes']+=1
 p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
print(counts)

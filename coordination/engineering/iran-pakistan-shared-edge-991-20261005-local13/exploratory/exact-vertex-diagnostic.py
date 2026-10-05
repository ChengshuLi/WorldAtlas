import json,pathlib
from fractions import Fraction as F
from shapely.geometry import shape,Point
p=pathlib.Path('coordination/engineering/iran-pakistan-grid-proof-971-20261005-local11/results-v1/staged-neighbors.json');d=json.loads(p.read_text());component=shape(d['component']['geometry'])
before={f['id']:f for f in d['baseline']};candidates={f['id']:f for f in d['candidate']}
def rings(feature):
 g=feature['geometry'];return [r for poly in ([g['coordinates']]if g['type']=='Polygon'else g['coordinates'])for r in poly]
def determinant(a,b,c):
 a,b,c=([F(v)for v in point]for point in [a,b,c]);return(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
records=[]
for identity in d['subject_ids']:
 oldrings=rings(before[identity]);oldpoints={tuple(v)for r in oldrings for v in r};segments=[(a,b)for r in oldrings for a,b in zip(r,r[1:])]
 extra=[]
 for r in rings(candidates[identity]):
  for point in r[:-1]:
   if tuple(point)in oldpoints:continue
   p=Point(point)
   # Nearest original segment is diagnostic context, never an assignment/repair.
   from shapely.geometry import LineString
   a,b=min(segments,key=lambda e:LineString(e).distance(p));det=determinant(a,b,point)
   extra.append({'point':point,'component_covers':component.covers(p),'nearest_original_edge':[a,b],'exact_binary_rational_on_edge':det==0,'orientation_numerator':str(det.numerator),'orientation_denominator':str(det.denominator),'original_edge_distance_degrees':LineString([a,b]).distance(p)})
 records.append({'subject':identity,'introduced_vertex_count':len(extra),'introduced_outside_component_count':sum(not e['component_covers']for e in extra),'introduced_outside_noncollinear_count':sum(not e['component_covers']and not e['exact_binary_rational_on_edge']for e in extra),'vertices':extra})
pathlib.Path('.cache/shared-edge-991/exact-vertex-v1.json').write_text(json.dumps(records)+'\n');print(json.dumps([{k:v for k,v in r.items()if k!='vertices'}for r in records]))

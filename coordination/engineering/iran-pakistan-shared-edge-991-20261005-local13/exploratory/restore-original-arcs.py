exec(open('.cache/shared-edge-991/prototype.py').read().split('candidates={k:current[k].union')[0])
from shapely.geometry import Polygon
joint=json.loads(pathlib.Path('.cache/shared-edge-991/prototype-v1.json').read_text())[-1]
west,south,east,north=component.bounds
candidates={};retention={}
for country,geometry in joint['candidates'].items():
 old=mapping(current[country]);oldpolys=[old['coordinates']]if old['type']=='Polygon'else old['coordinates'];original_points={tuple(v)for p in oldpolys for r in p for v in r}
 polygons=[geometry['coordinates']]if geometry['type']=='Polygon'else geometry['coordinates'];restored=[];removed=[]
 for p in polygons:
  rings=[]
  for r in p:
   ring=[]
   for v in r[:-1]:
    x,y=v
    if tuple(v)not in original_points and not(west<=x<=east and south<=y<=north):removed.append(v)
    else:ring.append(v)
   if len(ring)<3:raise ValueError('Restoration erased a polygon ring')
   ring.append(ring[0]);rings.append(ring)
  restored.append(Polygon(rings[0],rings[1:]))
 candidates[country]=restored[0]if len(restored)==1 else MultiPolygon(restored)
 retention[country]={'removed_overlay_vertices_outside_edit_bbox':removed,'retained_original_vertex_count':len(original_points),'policy':'Exploratory restoration of unchanged original arcs outside the component bbox; never new coordinates, buffer, snap or proximity assignment. Not integration-ready.'}
assess('joint-face-restored-original-outside-arcs',candidates,retention)
pathlib.Path('.cache/shared-edge-991/restored-arcs-v1.json').write_text(json.dumps(results)+'\n')

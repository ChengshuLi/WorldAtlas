exec(open('.cache/shared-edge-991/check-joint-case.py').read().split('report=m.compare')[0])
from shapely.geometry import shape,mapping,Polygon,MultiPolygon
from shapely.geometry.polygon import orient
results=[]
for mode in ['raw-original-order','raw-preserve-original-anchor','trusted-preserve-original-anchor']:
 candidates=json.loads(json.dumps(after))
 for id in subjects:
  g=shape(candidates[id]['geometry']);old=shape(before[id]['geometry'])
  if mode.endswith('anchor'):
   if old.geom_type=='MultiPolygon':old=max(old.geoms,key=lambda p:p.area)
   g=orient(g,1 if old.exterior.is_ccw else -1)
   ring=list(g.exterior.coords);oldring=list(old.exterior.coords);start=next((p for p in oldring if p in ring),None)
   if start:
    idx=ring.index(start);r=ring[:-1];r=r[idx:]+r[:idx];r.append(r[0]);g=Polygon(r,[list(h.coords)for h in g.interiors])
   candidates[id]['geometry']=mapping(g)
 if mode.startswith('raw-'):m.canonical_land=lambda g:g
 else:
  from evidence.geometry import canonical_land
  m.canonical_land=canonical_land
 report=m.compare(before,candidates);summary={'mode':mode,'status':report['status'],'regressions':report['regressions'],'geometry_errors':report['geometry_errors'],'findings':[{'kind':f['properties']['kind'],'area':f['properties']['source_geometry_area_square_degrees'],'bounds':f['properties']['bounds']}for f in report['findings']['features']]};results.append({'summary':summary,'report':report,'candidate_features':candidates});print(json.dumps(summary))
pathlib.Path('.cache/shared-edge-991/order-diagnostic-v1.json').write_text(json.dumps(results)+'\n')

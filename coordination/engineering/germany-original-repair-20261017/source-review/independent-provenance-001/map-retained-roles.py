import runpy,json,pathlib,collections
import numpy as np
s=runpy.run_path('/workspace/shared/worldatlas-recovery/germany-independent-review/compare-official.py');P=s['P'];a=s['a'];an=s['an'];bn=s['bn'];f=json.loads((P/'gb-DEU-ADM3-original.geojson').read_text())['features'];assert len(f)==428
out=[]
for i,((starts,xy),feature) in enumerate(zip(a,f)):
 g=feature['geometry'];polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates'];rings=[np.asarray(r) for p in polys for r in p];original=[xy[x:y] for x,y in zip(starts,(*starts[1:],len(xy)))]
 from shapely import linestrings,points,STRtree
 def boundary_distance(first,second):
  segments=np.concatenate([np.stack((r[:-1],r[1:]),axis=1) for r in second]);tree=STRtree(linestrings(segments));_,d=tree.query_nearest(points(np.concatenate(first)),return_distance=True,all_matches=False);return float(d.max())
 worst=max(boundary_distance(rings,original),boundary_distance(original,rings))
 alternatives=[]
 for j,names in enumerate(an):
  if j==i or names['Name']!=feature['properties']['shapeName']:continue
  ss,xx=a[j];rr=[xx[x:y] for x,y in zip(ss,(*ss[1:],len(xx)))];d=max(boundary_distance(rings,rr),boundary_distance(rr,rings));alternatives.append(dict(record=j,distance_degrees=d));assert worst<d,(i,j,worst,d)
 assert feature['properties']['shapeName']==an[i]['Name']==bn[i]['NUTS_NAME'],(i,feature['properties']['shapeName'],an[i]['Name'],bn[i]['NUTS_NAME'])
 out.append(dict(same_name_alternatives=alternatives,shape_id=feature['properties']['shapeID'],name=feature['properties']['shapeName'],record=i,official_gf=bn[i]['GF'],official_nuts_code=bn[i]['NUTS_CODE'],max_boundary_distance_degrees=worst,retained_ring_count=len(rings),upstream_ring_count=len(original),retained_vertices=sum(len(r) for r in rings),upstream_vertices=len(xy)))
ids={r['shape_id']:r for r in out};joins=json.loads((P/'domestic-source-identity-receipt.json').read_text())['joins'];owners=[]
for j in joins:
 rs=[ids[x.split(':')[-1]] for x in j['source_atoms']];owners.append(dict(owner=j['owner'],target_id=j['target_id'],atoms=rs));assert len({x['official_nuts_code'] for x in rs})==1
r=dict(kind='independent-retained-shape-id-official-role-map',all_features=len(out),official_roles=dict(collections.Counter(x['official_gf'] for x in out)),owners=len(owners),consumed_atoms=sum(len(x['atoms']) for x in owners),maximum_boundary_distance_degrees=max(x['max_boundary_distance_degrees'] for x in out),consumed_roles=dict(collections.Counter(a['official_gf'] for o in owners for a in o['atoms'])),whole_source_map=out,consumed_owner_map=owners)
pathlib.Path('/workspace/shared/worldatlas-recovery/germany-independent-review/retained-role-map.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ('whole_source_map','consumed_owner_map')}))

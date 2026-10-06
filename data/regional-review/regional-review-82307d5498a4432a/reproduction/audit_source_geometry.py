#!/usr/bin/env python3
"""Non-repairing structural screen of original scoped GeoJSON geometry."""
import json
import pathlib
p=pathlib.Path(__file__).resolve().parents[1]
features=json.loads((p/'source/issue-396-scoped-geoboundaries-features.geojson').read_text())['features']
def coords_depth(x):
 if not isinstance(x,list): return []
 if x and isinstance(x[0],(int,float)): return [x]
 return sum((coords_depth(y) for y in x),[])
rows=[]
for f in sorted(features,key=lambda z:z['properties']['shapeID']):
 g=f.get('geometry') or {}; c=g.get('coordinates',[]); pts=coords_depth(c)
 if not pts: raise SystemExit('empty geometry '+f['properties']['shapeID'])
 polys=c if g.get('type')=='MultiPolygon' else [c] if g.get('type')=='Polygon' else None
 if polys is None: raise SystemExit('non-polygon geometry '+f['properties']['shapeID'])
 component_points=[coords_depth(poly) for poly in polys]
 rows.append({'subject_id':'gb:RUS:ADM2:'+f['properties']['shapeID'],'name':f['properties'].get('shapeName'),'geometry_type':g['type'],'polygon_components':len(polys),'component_bboxes_lon_lat':[[min(x[0] for x in part),min(x[1] for x in part),max(x[0] for x in part),max(x[1] for x in part)] for part in component_points],'holes':sum(max(0,len(poly)-1) for poly in polys),'coordinate_positions':len(pts),'bbox_lon_lat':[min(x[0] for x in pts),min(x[1] for x in pts),max(x[0] for x in pts),max(x[1] for x in pts)],'interpretation_limit':'Polygon component counts expose possible fragmentation only; no validity, topology, island completeness, area or legal-boundary conclusion.'})
result={'version':1,'scope_count':len(rows),'multi_polygon_count':sum(r['geometry_type']=='MultiPolygon' for r in rows),'multipart_component_count':sum(r['polygon_components'] for r in rows),'rows':rows,'method':'Read original source extract; count GeoJSON Polygon/MultiPolygon components, rings, coordinate positions and min/max coordinates; no repair or projection.','limits':['Multipart components can be disconnected territories, but this screen does not determine legal status or whether fragments are correct.','No ellipsoidal area calculation or boundary comparison was run; bundled Python runtime lacks pyproj required by repository helper.','Kemerovo is an inland oblast; this does not audit omitted inland islands or source omissions.']}
(p/'findings/source-geometry-screen.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')
print(json.dumps({'features':len(rows),'multi_polygon_features':result['multi_polygon_count'],'polygon_components':result['multipart_component_count'],'empty_or_nonpolygon':0}))

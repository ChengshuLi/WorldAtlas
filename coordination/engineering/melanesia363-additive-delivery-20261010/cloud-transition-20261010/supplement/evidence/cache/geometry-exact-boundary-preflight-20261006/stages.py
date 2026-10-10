exec((__import__('pathlib').Path('/Users/chengshuli/world-atlas-workspace/.cache/geometry-exact-boundary-preflight-20261006/probe.py')).read_text().split('sources=[]; pins=[]')[0])
from shapely import union_all
members={'portugal':[],'spain':[]}
for pin in brief['verified_official_polygon_inputs']:
 obj=json.loads(read(pin['path'],pin['sha256']));f=obj['features'][0] if obj['type']=='FeatureCollection' else obj;members['portugal' if pin['key'].startswith('dgt_') else 'spain'].append(transform(tr.transform,shape(f['geometry'])))
p=union_all(members['portugal']);s=union_all(members['spain']); stages={'portugal_union':p,'spain_union':s,'portugal_only_operand':p.difference(s),'spain_only_operand':s.difference(p),'both_operand':p.intersection(s),'neither_operand':p.union(s)}
report=json.loads((HOME/'report.json').read_bytes()); results=[]
for v in report['outside_vertex_provenance']:
 if v['nearest_round_equals_geos_output']: continue
 xy=v['output_vertex']['xy_epsg25829'];point=Point(xy); row={'output_xy':xy,'original_source':v['source_segment'],'gap_edge_index':v['gap_edge_index'],'stages':[]}; ga,gb=v['gap_projected_endpoints']; oa,ob=map(rat,v['source_segment']['projected_endpoints'])
 for name,geom in stages.items():
  rs=rings(shapely.geometry.mapping(geom)); segs=[(a,b) for ring in rs for a,b in zip(ring,ring[1:]) if a!=b];i=min(range(len(segs)),key=lambda i:LineString(segs[i]).distance(point)); a,b=segs[i]; r=intersection(ga,gb,a,b)
  row['stages'].append({'stage':name,'nearest_segment_endpoints':[a,b],'nearest_segment_distance_m':LineString([a,b]).distance(point),'both_endpoints_exactly_on_traced_original_source':all(cross(sub(rat(q),oa),sub(ob,oa))==0 for q in (a,b)),'rational_intersection_round_equals_output':r is not None and tuple(float(x) for x in r[0])==tuple(xy),'geos_direct_intersection_equals_output':LineString([ga,gb]).intersection(LineString([a,b])).equals(point)})
 results.append(row)
(HOME/'stage-provenance.json').write_text(json.dumps(results,indent=2,sort_keys=True)+'\n');print([(r['output_xy'],[q['stage'] for q in r['stages'] if q['geos_direct_intersection_equals_output']]) for r in results])

"""Exact ring closure/adjacent/area/hole checks and independent context counterexamples."""
exec(__import__('pathlib').Path(__file__).with_name('indexed_probe.py').read_text().split('points=np.asarray')[0])
def ray(p,r):
 inside=False
 for a,b in zip(r,r[1:]):
  if on(p,a,b):return 'boundary'
  if (a[1]>p[1])!=(b[1]>p[1]) and p[0]<a[0]+(p[1]-a[1])*(b[0]-a[0])/(b[1]-a[1]):inside=not inside
 return 'inside' if inside else 'outside'
results={}
for ctxt in ['CRS84-original-binary64','EPSG25829-projected-binary64']:
 rows=[]
 for src in source+[{'key':'original_gap','geometry':gap}]:
  status=[];areas=[];closed=True;adjacent=[];nesting=[];prepared=[]
  for pi,poly in enumerate(polys(src['geometry'])):
   rings=[]
   for ri,r in enumerate(poly):
    floats=[tuple(p[:2]) if ctxt.startswith('CRS84') else tr.transform(*p[:2]) for p in r];rats=[tuple(F(v) for v in p) for p in floats];rings.append(rats);closed&=rats[0]==rats[-1]
    area=sum(cross(a,b) for a,b in zip(rats,rats[1:]));areas.append({'polygon_index':pi,'ring_index':ri,'twice_signed_area':{'numerator':str(area.numerator),'denominator':str(area.denominator)},'exact_zero':area==0})
    corners=rats[:-1]
    for i,b in enumerate(corners):
     a,c=corners[i-1],corners[(i+1)%len(corners)]
     if a==b or b==c or (ori(a,b,c)==0 and (on(c,a,b) or on(a,b,c))):adjacent.append([pi,ri,i])
   for ri,hole in enumerate(rings[1:],start=1):
    state=ray(hole[0],rings[0]);nesting.append({'polygon_index':pi,'hole_ring':ri,'shell_state':state})
    for rj,other in enumerate(rings[1:ri],start=1):nesting.append({'polygon_index':pi,'hole_ring':ri,'other_hole_ring':rj,'hole_in_other':ray(hole[0],other),'other_in_hole':ray(other[0],hole)})
   prepared.append(rings)
  multipart=[]
  for i,rings in enumerate(prepared):
   for j,other in enumerate(prepared[i+1:],start=i+1):multipart.append({'components':[i,j],'first_shell_vertex_in_second_shell':ray(rings[0][0],other[0]),'second_shell_vertex_in_first_shell':ray(other[0][0],rings[0])})
  rows.append({'key':src['key'],'all_original_rings_closed':closed,'exact_ring_areas':areas,'adjacent_backtracking_or_zero_length':adjacent,'hole_nesting_checks':nesting,'multipart_containment_checks':multipart})
 results[ctxt]=rows
# Independent brute-force half-open ring classification for three projected domain failures.
r=json.loads((OUT/'report.json').read_bytes());projrows=json.loads((OUT/'EPSG25829-projected-binary64-rows.json').read_bytes());counter=[]
for row in projrows:
 if row['gap_state']=='inside':continue
 obs={'cell':row['cell'],'native_lonlat':row['point_lonlat'],'contexts':{}}
 for ctxt in results:
  pfloat=tuple(row['point_lonlat']) if ctxt.startswith('CRS84') else tr.transform(*row['point_lonlat']);p=tuple(F(v) for v in pfloat);rf=[tuple(q[:2]) if ctxt.startswith('CRS84') else tr.transform(*q[:2]) for q in polys(gap)[0][0]];rr=[tuple(F(v) for v in q) for q in rf];nearest=[]
  for ei,(a,b) in enumerate(zip(rr,rr[1:])):
   v=sub(b,a);w=sub(p,a);t=max(F(0),min(F(1),(w[0]*v[0]+w[1]*v[1])/(v[0]*v[0]+v[1]*v[1])));q=tuple(a[i]+t*v[i] for i in (0,1));d2=sum((p[i]-q[i])**2 for i in (0,1));nearest.append((d2,ei,t))
  d2,ei,t=min(nearest);obs['contexts'][ctxt]={'brute_exact_gap_state':ray(p,rr),'point_xy':pfloat,'nearest_original_gap_edge_index':ei,'nearest_original_edge_endpoints':rf[ei:ei+2],'exact_nearest_edge_t':{'numerator':str(t.numerator),'denominator':str(t.denominator)},'exact_nearest_squared_distance':{'numerator':str(d2.numerator),'denominator':str(d2.denominator)},'nearest_distance_display_only':float(d2)**0.5,'distance_units':'coordinate degrees' if ctxt.startswith('CRS84') else 'metres'}
 counter.append(obs)
(OUT/'topology-completion.json').write_text(json.dumps({'contexts':results,'projection_model_counterexamples':counter,'limits':['Exact encoded-source checks performed without GEOS validity substitution.','All real retained geometries are single Polygon components, so no real multipart containment experiment occurs here. Generic multipolygon controls remain separately covered in1190.','Nonadjacent ring contacts are in report.json; combined exact checks validate these encoded simple-ring sources, not legal/physical truth.']},sort_keys=True,indent=2)+'\n');print(json.dumps({'source_contexts':len(results),'closed':all(q['all_original_rings_closed'] for v in results.values() for q in v),'zero_area_count':sum(a['exact_zero'] for v in results.values() for q in v for a in q['exact_ring_areas']),'adjacent_failure_count':sum(len(q['adjacent_backtracking_or_zero_length']) for v in results.values() for q in v),'holes':[q['hole_nesting_checks'] for v in results.values() for q in v if q['hole_nesting_checks']],'counterexamples':[{k:v for k,v in q.items() if k!='contexts'}|{'states':{c:d['brute_exact_gap_state'] for c,d in q['contexts'].items()},'projected_outside_distance_m':q['contexts']['EPSG25829-projected-binary64']['nearest_distance_display_only']} for q in counter]}))

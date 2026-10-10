"""Independent closed interval sweep vs STRtree envelope candidates, every real point."""
exec(__import__('pathlib').Path(__file__).with_name('indexed_probe.py').read_text().split('points=np.asarray')[0])
import heapq,bisect
points=np.asarray([c['native_centre_lonlat'] for c in centres]);contexts={}
for ctxt in ['CRS84-original-binary64','EPSG25829-projected-binary64']:
 xy=points if ctxt.startswith('CRS84') else np.column_stack(tr.transform(points[:,0],points[:,1]));sources_report=[];point_totals=np.zeros(len(xy),dtype=int)
 for src in source+[{'key':'original_gap','geometry':gap}]:
  lines=[];bounds=[]
  for poly in polys(src['geometry']):
   for ring in poly:
    coords=[tuple(q[:2]) if ctxt.startswith('CRS84') else tr.transform(*q[:2]) for q in ring]
    for a,b in zip(coords,coords[1:]):
     lines.append(LineString([a,b]));bounds.append((min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])))
  tree=STRtree(lines);strpairs={tuple(sorted((int(a),int(b)))) for a,b in zip(*tree.query(lines)) if a!=b};sweep_pairs=set();active=set();ends=[];max_active_x=0
  for i in sorted(range(len(bounds)),key=lambda i:(bounds[i][0],i)):
   x0,y0,x1,y1=bounds[i]
   while ends and ends[0][0]<x0:
    _,j=heapq.heappop(ends);active.remove(j)
   for j in active:
    by0,by1=bounds[j][1],bounds[j][3]
    if y0<=by1 and by0<=y1:sweep_pairs.add(tuple(sorted((i,j))))
   active.add(i);heapq.heappush(ends,(x1,i));max_active_x=max(max_active_x,len(active))
  assert strpairs==sweep_pairs,(ctxt,src['key'],'topology-mismatch')
  xmax=max(b[2] for b in bounds);pairs=tree.query([box(float(p[0]),float(p[1]),max(float(p[0]),xmax),float(p[1])) for p in xy]);strcandidates=collections.defaultdict(set)
  for qi,si in zip(*pairs):strcandidates[int(qi)].add(int(si))
  starts=sorted(range(len(bounds)),key=lambda i:(bounds[i][1],i));cursor=0;active=set();ends=[];counts=np.zeros(len(xy),dtype=int);mismatches=[];max_active_y=0
  for qi in sorted(range(len(xy)),key=lambda qi:(xy[qi,1],qi)):
   x,y=xy[qi]
   while cursor<len(starts) and bounds[starts[cursor]][1]<=y:
    si=starts[cursor];cursor+=1;active.add(si);heapq.heappush(ends,(bounds[si][3],si))
   while ends and ends[0][0]<y:
    _,si=heapq.heappop(ends);active.remove(si)
   candidates={si for si in active if bounds[si][2]>=x};counts[qi]=len(candidates);max_active_y=max(max_active_y,len(active))
   if candidates!=strcandidates[qi]:mismatches.append({'point_index':qi,'interval_only':sorted(candidates-strcandidates[qi]),'strtree_only':sorted(strcandidates[qi]-candidates)})
  assert not mismatches,(ctxt,src['key'],'point-ray-mismatch');point_totals+=counts
  sources_report.append({'key':src['key'],'topology_candidate_sets_identical':strpairs==sweep_pairs,'topology_candidate_count':len(sweep_pairs),'max_active_topology_x_intervals':max_active_x,'point_candidate_sets_identical':not mismatches,'point_ray_candidate_total':int(counts.sum()),'max_point_ray_candidates':int(counts.max()),'point_ray_candidate_p95':int(np.sort(counts)[int(.95*(len(counts)-1))]),'max_active_query_y_intervals':max_active_y})
 contexts[ctxt]={'sources':sources_report,'all_member_point_candidate_total':int(point_totals.sum()),'max_all_member_point_candidates':int(point_totals.max()),'all_member_candidate_p95':int(np.sort(point_totals)[int(.95*(len(point_totals)-1))]),'perpoint_candidate_counts':point_totals.tolist()}
 print(json.dumps({'context':ctxt,'candidate_total':int(point_totals.sum()),'max_perpoint':int(point_totals.max()),'p95_perpoint':contexts[ctxt]['all_member_candidate_p95']}),flush=True)
(OUT/'independent-index-completeness.json').write_text(json.dumps({'contexts':contexts,'method':'Closed source-endpoint min/max x event sweep and y interval sweeps using unchanged finite Float64 comparisons; no interpolated cutoffs; every topology pair and every21,575point candidate set compared to STRtree before exact predicates.','limits':['Actual sourcepoint candidate completeness checked; generalized sweeps still need synthetic equal-event/degenerate/dateline/ring-topology controls before tracked implementation.','Performance and candidate counts describe retained contexts/inputs, not arbitrary global sources or production bounds.']},sort_keys=True,separators=(',',':'))+'\n')

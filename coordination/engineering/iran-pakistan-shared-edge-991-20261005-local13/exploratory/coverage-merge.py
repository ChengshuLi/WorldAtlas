exec(open('.cache/shared-edge-991/prototype.py').read().split('candidates={k:current[k].union')[0])
from shapely import coverage_union_all,coverage_is_valid
lines=union_all([current['IRN'].boundary,current['PAK'].boundary,component.boundary,*[g.boundary.intersection(component)for g in source.values()]])
faces=list(get_parts(polygonize(list(get_parts(lines)))))
assigned={k:[]for k in source};unknown=[]
for n,face in enumerate(faces):
 point=face.representative_point();prior=[k for k,g in current.items()if g.contains(point)]
 if len(prior)==1:assigned[prior[0]].append(face);continue
 if not component.contains(point):continue
 named=[k for k,g in source.items()if g.contains(point)]
 if len(named)==1:assigned[named[0]].append(face)
 else:unknown.append({'face':n,'area':face.area,'prior':prior,'sources':named})
print(json.dumps({'all_faces_coverage_valid':bool(coverage_is_valid(faces)),'assigned_valid':{k:bool(coverage_is_valid(v))for k,v in assigned.items()}}))
candidates={k:coverage_union_all(v)for k,v in assigned.items()};assess('joint-face-coverage-merge',candidates,{'faces':len(faces),'unknown':unknown})
pathlib.Path('.cache/shared-edge-991/coverage-merge-v1.json').write_text(json.dumps(results)+'\n')

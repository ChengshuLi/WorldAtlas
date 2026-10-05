exec(open('.cache/shared-edge-991/prototype.py').read().split('candidates={k:current[k].union')[0])
from shapely.geometry import Point
from fractions import Fraction as F
lines=union_all([current['IRN'].boundary,current['PAK'].boundary,component.boundary,*[g.boundary.intersection(component)for g in source.values()]])
faces=list(get_parts(polygonize(list(get_parts(lines)))))
records=[]
for n,face in enumerate(faces):
 p=face.representative_point();prior=[k for k,g in current.items()if g.contains(p)];inside=component.contains(p)
 if not prior and not inside:
  records.append({'face':n,'area':face.area,'bounds':face.bounds,'representative_point':mapping(p),'before_intersection_area':{k:face.intersection(g).area for k,g in current.items()},'component_intersection_area':face.intersection(component).area,'source_intersections':{k:face.intersection(g).area for k,g in source.items()},'geometry':mapping(face)})
pathlib.Path('.cache/shared-edge-991/unassigned-v1.json').write_text(json.dumps(records)+'\n')
print(json.dumps([{k:v for k,v in r.items()if k!='geometry'}for r in records]))

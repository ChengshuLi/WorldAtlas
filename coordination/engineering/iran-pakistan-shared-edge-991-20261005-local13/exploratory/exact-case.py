exec(open('.cache/shared-edge-991/prototype.py').read().split('candidates={k:current[k].union')[0])
from exact_arrangement import arrange,point,inside_ring,signed_area
from shapely.geometry import LineString

def rings(g):
 raw=mapping(g);return[[point(p)for p in r[:-1]]for polygon in ([raw['coordinates']]if raw['type']=='Polygon'else raw['coordinates'])for r in polygon]
polys={label:rings(g)for label,g in {**{'old:'+k:v for k,v in current.items()},**{'source:'+k:v for k,v in source.items()},'component':component}.items()}
segments=[]
for label,values in polys.items():
 for r in values:
  for a,b in zip(r,r[1:]+r[:1]):
   if not label.startswith('source:')or LineString([[float(v)for v in a],[float(v)for v in b]]).envelope.intersects(component.envelope):segments.append((a,b))
arrangement=arrange(segments)
def classify(p,rings):
 states=[inside_ring(p,r)for r in rings]
 if None in states:raise ValueError('Exact face point lies on classification boundary')
 return sum(states)%2==1
counts={};unknown=[];baseline_multiple=[];records=[]
for n,(ring,area,p)in enumerate(arrangement['faces']):
 labels={k:classify(p,r)for k,r in polys.items()};old=[k for k in current if labels['old:'+k]];named=[k for k in source if labels['source:'+k]]
 if old:after=old
 elif labels['component']and len(named)==1:after=named
 else:after=[]
 if len(old)>1:baseline_multiple.append(n)
 if not old and labels['component']and len(named)!=1:unknown.append(n)
 category='preserved'if old else'added:'+','.join(after)if after else'unknown'if labels['component']else'unassigned-outside'
 counts[category]=counts.get(category,0)+1
 records.append({'face':n,'category':category,'before':old,'after':after,'source_labels':named,'component':labels['component'],'area_numerator':str(area.numerator),'area_denominator':str(area.denominator),'ring':[[str(x),str(y)]for x,y in ring]})
result={'diagnostic_only':True,'original_segments':len(segments),'noded_edges':len(arrangement['edges']),'bounded_faces':len(arrangement['faces']),'negative_cycles':len(arrangement['negative']),'zero_area_walks':len(arrangement['zero']),'counts':counts,'unknown_component_faces':unknown,'preexisting_multiple_faces':baseline_multiple,'records':records,'limits':['Exact binary-rational source-coordinate model, not geographic/source approval. Disconnected/nested cycle and global reconstruction still require explicit validation before installation. No rounding derivative is accepted by this prototype.']}
pathlib.Path('.cache/shared-edge-991/exact-case-v1.json').write_text(json.dumps(result)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='records'}))

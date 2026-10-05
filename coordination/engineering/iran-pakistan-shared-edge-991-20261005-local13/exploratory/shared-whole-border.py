exec(open('.cache/shared-edge-991/prototype.py').read().split('candidates={k:current[k].union')[0])
from shapely.geometry import LineString
originals=[]
for index in [0,3]:
 entry=next(f for f in manifest['sources'][index]['files']if f['path'].endswith('full.json'));originals.append(json.loads(read(entry['path'])))
a,b=[{(e['type'],e['id']):e for e in response['elements']}for response in originals]
ways=sorted(k for k in a.keys()&b.keys()if k[0]=='way');shared=[]
for key in ways:
 if a[key]!=b[key]:raise ValueError('Shared source way differs')
 coordinates=[]
 for n in a[key]['nodes']:
  if a[('node',n)]!=b[('node',n)]:raise ValueError('Shared source node differs')
  p=a[('node',n)];coordinates.append((p['lon'],p['lat']))
 shared.append(LineString(coordinates))
outer=union_all([*current.values(),component]);line=union_all(shared).intersection(outer)
faces=list(get_parts(polygonize(list(get_parts(union_all([outer.boundary,line]))))))
assigned={k:[]for k in current};unknown=[]
for n,f in enumerate(faces):
 if not outer.contains(f.representative_point()):continue
 choices=[k for k,g in source.items()if g.contains(f.representative_point())]
 if len(choices)!=1:unknown.append({'face':n,'area':f.area,'source_labels':choices,'geometry':mapping(f)})
 else:assigned[choices[0]].append(f)
assess('one-outer-footprint-one-sourced-shared-border',{k:union_all(v)for k,v in assigned.items()},{'faces':len(faces),'unknown':unknown,'scope':'Exploratory wider pair-border repartition. Outside-component changes are not authorized for installation by current limited proof; retain and assess all changes.'})
pathlib.Path('.cache/shared-edge-991/shared-whole-border-v1.json').write_text(json.dumps(results)+'\n')

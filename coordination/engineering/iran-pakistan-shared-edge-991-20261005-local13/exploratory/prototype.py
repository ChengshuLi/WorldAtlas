import json,pathlib,subprocess,sys
sys.path.insert(0,str(pathlib.Path('scripts').resolve()))
from shapely.geometry import shape,mapping,GeometryCollection,MultiPolygon
from shapely import union_all,polygonize,get_parts
from evidence.geometry import canonical_land
read=lambda p:subprocess.check_output(['git','show','HEAD:'+p])
oldpath='coordination/engineering/iran-pakistan-native-seam-971-20261005-local09/reproduce.py'
ns={'__name__':'immutable_prior_native','__file__':str(pathlib.Path(oldpath).resolve())};exec(compile(read(oldpath),oldpath,'exec'),ns)
manifest=json.loads(read('coordination/engineering/iran-pakistan-joint-proposal-971-20261005-local10/evidence-quality.json'))
source={}
for country,index,relation in [('IRN',0,6555069),('PAK',3,3229274)]:
 sources=manifest['sources'][index]['files'];entry=next(f for f in sources if f['path'].endswith('full.json'))
 source[country],_=ns['assemble_osm_boundary'](json.loads(read(entry['path'])),relation)
d=json.loads(read('coordination/engineering/iran-pakistan-grid-proof-971-20261005-local11/results-v1/staged-neighbors.json'));pair=d['subject_ids'];current={k:shape(next(f['geometry'] for f in d['baseline'] if f['id']==ns['SUBJECTS'][k]))for k in source};component=shape(d['component']['geometry'])
results=[]
def assess(method,candidates,extra):
 a,b=candidates.values();oldoverlap=current['IRN'].intersection(current['PAK']);new=a.intersection(b).difference(oldoverlap)
 records={k:{'valid':g.is_valid,'type':g.geom_type,'lost':current[k].difference(g).area,'outside_component_added':g.difference(current[k]).difference(component).area,'outside_source_added':g.difference(current[k]).difference(source[k]).area}for k,g in candidates.items()}
 report={'method':method,'diagnostic_only':True,'new_overlap':new.area,'new_overlap_geometry':mapping(new),'uncovered_component':component.difference(union_all(list(candidates.values()))).area,'covers_component':union_all(list(candidates.values())).covers(component),'subjects':records,'extra':extra,'candidates':{k:mapping(v)for k,v in candidates.items()}}
 results.append(report);print(json.dumps({k:v for k,v in report.items()if k not in ['new_overlap_geometry','candidates']}))
candidates={k:current[k].union(component.intersection(g))for k,g in source.items()}
assess('direct-source-intersection-union',candidates,{})
# Construct a single full graph; source edges are included only within the component.
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
candidates={k:union_all(v)for k,v in assigned.items()};assess('joint-noded-face-partition',candidates,{'faces':len(faces),'assigned_counts':{k:len(v)for k,v in assigned.items()},'unknown':unknown,'classification':'representative-point exploratory only, not approved'})
pathlib.Path('.cache/shared-edge-991/prototype-v1.json').write_text(json.dumps(results)+'\n')

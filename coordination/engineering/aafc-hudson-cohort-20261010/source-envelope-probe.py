"""Bounded exact-source diagnostic; no acceptance or territorial inference."""
import sys,json,gzip,hashlib,subprocess,types,pathlib,resource
repo,commit,plan_path,vintage=sys.argv[1:]
def git(*args): return subprocess.check_output(['git','-C',repo,*args],stderr=subprocess.PIPE)
plan_raw=git('show',commit+':'+plan_path)
plan=json.loads(plan_raw)
helper=plan['helper']; raw=git('show',plan['baseline_commit']+':'+helper['path'])
assert len(raw)==helper['bytes'] and hashlib.sha256(raw).hexdigest()==helper['sha256']
m=types.ModuleType('pinned_immutable');m.__file__=str(pathlib.Path(repo)/helper['path']);exec(compile(raw,m.__file__,'exec'),m.__dict__)
b=m.Baseline(repo,plan['baseline_commit'],plan['inputs']+[helper])
# Output paths are admitted before any GIS operation. Original files are never overwritten.
out=m.NewVintage(b,plan['owned_path'],vintage,['source-envelope-result.json'])
def read(key):
 path=plan['paths'][key]; raw=b.pinned_bytes(path)
 if path.endswith('.gz'):
  raw=gzip.decompress(raw); assert len(raw)==plan['decoded'][key]['bytes'] and hashlib.sha256(raw).hexdigest()==plan['decoded'][key]['sha256']
 return json.loads(raw)
family=next(x for x in read('family') if x['id']==plan['family_id']);ids=set(family['component_ids']);assert len(ids)==len(family['component_ids'])==88
features=read('candidates')['features']; candidates=[]
for f in features:
 binding=[{'id':f['id'],'feature_sha256':m.sha256(m.canonical_json(f))}]
 identity='physical-component:'+m.sha256(m.canonical_json(binding))
 if identity in ids:candidates.append((identity,f))
assert len(candidates)==88 and {i for i,f in candidates}==ids
sources={k:read(k)['features'] for k in ['native','official_v22']}
import shapely
from shapely.geometry import shape,Polygon
assert hashlib.sha256(pathlib.Path(sys.executable).resolve().read_bytes()).hexdigest()==plan['runtime']['python_executable_sha256']
assert shapely.__version__=='2.1.2' and shapely.geos_version_string=='3.13.1'
# Preserve distinct source editions; no repair, simplification, buffering or rounding.
source_geoms={};source_descriptors={}
for edition,fs in sources.items():
 chosen=[f for f in fs if str(f['properties']['ECOREGION_ID'])=='45'];assert len(chosen)==1
 g=shape(chosen[0]['geometry']);assert g.is_valid and not g.is_empty
 source_geoms[edition]=g;source_descriptors[edition]={'feature_sha256':m.sha256(m.canonical_json(chosen[0])),'properties':chosen[0]['properties'],'valid':g.is_valid,'bounds_lonlat':list(g.bounds)}
rows=[]
for identity,f in sorted(candidates,key=lambda p: -p[1]['properties']['area_m2']):
 g=shape(f['geometry']);assert g.is_valid and g.geom_type=='Polygon' and not g.is_empty
 r={'component':identity,'fragment_id':f['id'],'fragment_feature_sha256':m.sha256(m.canonical_json(f)),'retained_fragment_area_m2':f['properties']['area_m2'],'candidate_planar_area_deg2':g.area,'bounds_lonlat':list(g.bounds),'source_comparisons':{}}
 for edition,s in source_geoms.items():
  overlap=g.intersection(s);remainder=g.difference(s)
  r['source_comparisons'][edition]={'covers_complete_candidate':s.covers(g),'literal_empty_remainder':remainder.is_empty,'overlap_planar_area_deg2':overlap.area,'uncovered_planar_area_deg2':remainder.area,'candidate_area_fraction_inside':overlap.area/g.area,'overlap_geometry_sha256':m.sha256(m.canonical_json(shapely.geometry.mapping(overlap))),'remainder_geometry_sha256':m.sha256(m.canonical_json(shapely.geometry.mapping(remainder)))}
 rows.append(r)
# Nonvacuous positive and adverse controls use the exact source as its own full candidate,
# then remove it entirely; the actual same predicates must distinguish these cases.
controls={}
for edition,s in source_geoms.items():
 empty=Polygon();controls[edition]={'positive_source_covers_itself':s.covers(s),'positive_self_remainder_empty':s.difference(s).is_empty,'negative_empty_source_does_not_cover':not empty.covers(s),'negative_complete_remainder_nonempty':not s.difference(empty).is_empty}
 assert all(controls[edition].values())
result={'version':1,'issue':1697,'baseline_commit':plan['baseline_commit'],'executed_commit':commit,'family_id':family['id'],'original_component_count':88,'source_descriptors':source_descriptors,'rows':rows,'controls':controls,'runtime':{'python':sys.version,'shapely':shapely.__version__,'geos':shapely.geos_version_string,'peak_rss_platform_units':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},'limits':['Diagnostic source-envelope comparison only; current target and complete neighbor/retired-member predicates have not been tested.','Retained area_m2 is original Natural Earth 10m-reference fragment measurement, not newly computed or verified current land area.','GeoJSON longitude/latitude convention used for exact binary64 planar predicates; all newly computed areas use square degrees, never metric interpretation.','Source ecological role cannot establish current territorial clipping, legal borders, water or historical cause.','Passing source coverage alone is not an accepted repair.']}
out.publish({'source-envelope-result.json':result});print(json.dumps({'rows':len(rows),'full_native':sum(x['source_comparisons']['native']['literal_empty_remainder'] for x in rows),'full_official':sum(x['source_comparisons']['official_v22']['literal_empty_remainder'] for x in rows),'largest':rows[0],'peak_rss_platform_units':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))

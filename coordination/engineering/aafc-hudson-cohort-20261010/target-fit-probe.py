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
out=m.NewVintage(b,plan['owned_path'],vintage,['target-fit-result.json','candidate-additions.json'])
def read(key):
 path=plan['paths'][key]; raw=b.pinned_bytes(path)
 if path.endswith('.gz'):
  raw=gzip.decompress(raw); b.admit('decoded-'+key,len(raw)); assert len(raw)==plan['decoded'][key]['bytes'] and hashlib.sha256(raw).hexdigest()==plan['decoded'][key]['sha256']
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
certificate=read('certificate')
selection=read('selection');bank=read('bank');index=read('world_index')
assert selection['selected_geography']['sha256']==m.sha256(b.pinned_bytes(plan['paths']['bank']))
assert bank['world_index']['sha256']==m.sha256(b.pinned_bytes(plan['paths']['world_index']))
assert bank['release_id']==selection['release_id']==certificate['binding']['selection']['release_id']
assert bank['changed_ids']==['atlas:physical:CAN-15:NWT','atlas:physical:CAN-25:NUN']
assert certificate['entry_fields']==['id','index','parent_id','parent_index','source','ordinal','whole_feature_sha256','geometry_sha256','effective_geometry_sha256','boxes']
# Rebind every actual selected source-body identity through current immutable tree.
assert len(certificate['inputs'])==len(index['parts'])==36
assert {x['path'] for x in certificate['inputs']}=={'data/'+x for x in index['parts']}
source_bindings=[]
for x in certificate['inputs']:
 s=x['source'];tree=git('ls-tree','-z',plan['baseline_commit'],'--',s['path']).decode().rstrip('\0');mode,kind,oid=tree.split('\t')[0].split()
 assert mode==s['mode'] and kind=='blob' and oid==s['git_blob_oid']
 source_bindings.append({'logical_path':x['path'],'actual_path':s['path'],'git_blob_oid':oid,'whole_body_sha256':x['whole_body_sha256']})
binding_raw=git('show',commit+':'+plan['feature_binding']['path']);assert len(binding_raw)==plan['feature_binding']['bytes'] and m.sha256(binding_raw)==plan['feature_binding']['sha256'];b.admit('feature-binding',len(binding_raw));bound=json.loads(binding_raw)
assert bound['selected_part']['sha256']==m.sha256(b.pinned_bytes(plan['paths']['selected_part']))
features=read('selected_part')['features'];entries={r[0]:r for r in certificate['entries']};assert len(entries)==49625
geoms=[shape(f['geometry']) for _,f in candidates];bbox=[min(g.bounds[0] for g in geoms),min(g.bounds[1] for g in geoms),max(g.bounds[2] for g in geoms),max(g.bounds[3] for g in geoms)]
def boxes_intersect(a,b):return a[0]<=b[2] and a[2]>=b[0] and a[1]<=b[3] and a[3]>=b[1]
hits=[r for r in certificate['entries'] if any(boxes_intersect(box,bbox) for box in r[9])]
assert {r[0] for r in hits}=={'atlas:physical:CAN-45:NUN','atlas:physical:CAN-30:NUN'}
selected={}
for r in hits:
 assert r[4]=='data/geography/part-29.json'
 f=features[r[5]];assert f['id']==r[0]
 binding_rows={x['id']:x for x in bound['rows']}
 assert binding_rows[r[0]]['ordinal']==r[5] and binding_rows[r[0]]['whole_feature_sha256']==r[6]
 selected[r[0]]=f
T=selected['atlas:physical:CAN-45:NUN'];target=shape(T['geometry']);neighbor=shape(selected['atlas:physical:CAN-30:NUN']['geometry']);assert target.is_valid and neighbor.is_valid
sidecar=read('sidecar');ledger=read('ledger')
assert selection['additive_release']['sha256']==m.sha256(b.pinned_bytes(plan['paths']['sidecar']))
assert sidecar['logical_asset_map']['ledger']['sha256']==m.sha256(b.pinned_bytes(plan['paths']['ledger']))
assert sidecar['base_selection']['selected_geography']==selection['selected_geography']
added_geometries=[]
for x in ledger['rows']:
 if 'geometry' in x:added_geometries.append(x['geometry'])
 else:assert x['disposition']=='awaiting-evidence'
for x in ledger['current_targets']:added_geometries.append(x['geometry'])
for x in added_geometries:
 assert not boxes_intersect(shape(x).bounds,bbox)
# Exact source uniqueness is checked across all retained source records that can intersect.
source_universes={}
for edition,fs in sources.items():
 all_shapes=[]
 for f in fs:
  s=shape(f['geometry'])
  if boxes_intersect(s.bounds,bbox):
   assert s.is_valid
   all_shapes.append((f['properties']['ECOREGION_ID'],s))
 source_universes[edition]=all_shapes
rows=[]
for identity,f in sorted(candidates,key=lambda p: -p[1]['properties']['area_m2']):
 g=shape(f['geometry']);assert g.is_valid
 proposed=target.union(g);gain=proposed.difference(target);loss=target.difference(proposed);difference=gain.symmetric_difference(g)
 other=neighbor.intersection(g)
 r={'component':identity,'fragment_id':f['id'],'retained_fragment_area_m2':f['properties']['area_m2'],'source_covering_ids':{},'other_source_positive_area_ids':{},'candidate_planar_area_deg2':g.area,'gain_planar_area_deg2':gain.area,'loss_empty':loss.is_empty,'gain_candidate_symmetric_difference_empty':difference.is_empty,'gain_candidate_symmetric_difference_area_deg2':difference.area,'union_valid':proposed.is_valid,'neighbor_positive_overlap_absent':other.area==0,'neighbor_intersection_area_deg2':other.area}
 for edition,universe in source_universes.items():
  r['source_covering_ids'][edition]=sorted({eid for eid,s in universe if s.covers(g)})
  r['other_source_positive_area_ids'][edition]=sorted({eid for eid,s in universe if eid!=45 and s.intersection(g).area>0})
 rows.append(r)
from shapely import union_all
addition=union_all(geoms);proposed=target.union(addition);gain=proposed.difference(target);loss=target.difference(proposed);diff=gain.symmetric_difference(addition)
cohort={'addition_valid':addition.is_valid,'proposal_valid':proposed.is_valid,'loss_empty':loss.is_empty,'gain_equals_addition_literal':diff.is_empty,'gain_addition_symmetric_difference_area_deg2':diff.area,'gain_planar_area_deg2':gain.area,'neighbor_positive_overlap_absent':neighbor.intersection(addition).area==0}
result={'version':1,'issue':1697,'executed_commit':commit,'baseline_commit':plan['baseline_commit'],'source_bindings':source_bindings,'target_feature_sha256':m.sha256(m.canonical_json(T)),'target_properties':T['properties'],'possible_base_neighbors':[r[0] for r in hits],'rows':rows,'cohort':cohort,'limits':['Complete selected base-source identity and conservative bbox proof reused from authenticated current-f02 certificate; all current ledger primitives and current-target geometries screened disjoint from the candidate bbox.','Retired-member context, physical land/shoreline observations and territorial role remain unqualified.','These are diagnostic proposals, not accepted repairs or native/selected delivery.']}
out.publish({'target-fit-result.json':result,'candidate-additions.json':{'type':'FeatureCollection','features':[{'type':'Feature','id':identity,'properties':{'target':'atlas:physical:CAN-45:NUN','original_fragment_id':f['id'],'status':'unqualified-source-fit-candidate'},'geometry':f['geometry']} for identity,f in candidates]}})
print(json.dumps({'cohort':cohort,'individual_exact':sum(r['loss_empty'] and r['gain_candidate_symmetric_difference_empty'] and r['neighbor_positive_overlap_absent'] and r['union_valid'] for r in rows),'source_unique':sum(all(r['source_covering_ids'][s]==[45] and not r['other_source_positive_area_ids'][s] for s in source_universes) for r in rows),'rows':len(rows),'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))

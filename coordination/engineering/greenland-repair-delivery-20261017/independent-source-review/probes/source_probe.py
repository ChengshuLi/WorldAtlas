import os,sys,json,gzip,hashlib,subprocess,pathlib,collections
import numpy as np, shapely
from shapely.geometry import shape
W=pathlib.Path(__file__).resolve().parents[1]; P=W/'coordination/engineering/greenland-repair-delivery-20261017'
HEAD='19858cf7aa887efad5d0c6ba0736d5672bf0aef5'; BASE='defe4dea8d79963350f34bd09fe80d1825049ed5'
consumed={}
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),*a],env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'})
def blob(commit,path):
 row=git('ls-tree','-z',commit,'--',path).rstrip(b'\0'); meta,name=row.split(b'\t');mode,kind,oid=meta.decode().split();assert name.decode()==path and kind=='blob' and mode in ['100644','100755']
 size=int(git('cat-file','-s',oid));assert size<=33554432
 b=git('cat-file','blob',oid);assert len(b)==size
 consumed[(commit,path)]={'commit':commit,'path':path,'bytes':len(b),'sha256':sha(b),'git_blob_oid':oid}
 return b

def read(d,decode=False):
 b=blob(d['commit'],d['path']);r=consumed[(d['commit'],d['path'])]
 for k in ['bytes','sha256','git_blob_oid']:assert k not in d or r[k]==d[k],(d['path'],k)
 if decode:
  b=gzip.decompress(b);assert len(b)<=33554432 and len(b)==d['decoded_bytes'] and sha(b)==d['decoded_sha256'];r.update(decoded_bytes=len(b),decoded_sha256=sha(b))
 return b

def local(path):return json.loads(blob(HEAD,'coordination/engineering/greenland-repair-delivery-20261017/'+path))
def load(d):return json.loads(read(d,d['path'].endswith('.gz')))
def geom_stats(g):return {'type':g.geom_type,'valid':bool(g.is_valid),'empty':bool(g.is_empty),'dimension':int(shapely.get_dimensions(g)),'coordinate_count':int(shapely.get_num_coordinates(g)),'bounds':list(g.bounds)}
e=local('native-inputs-001/source-evidence.json'); custody=local('source-review/input-custody.json');sc=local('source-review/source-custody.json'); sr=local('source-review/source-target-review.json');mem=local('source-review/complete-primary-membership.json')
source=json.loads(b''.join(read(d,True) for d in e['families'][0]['parts']));assert len(source['features'])==6 and source.get('crs',{}).get('properties',{}).get('name') in [None,'urn:ogc:def:crs:OGC:1.3:CRS84','urn:ogc:def:crs:EPSG::4326']
features={f['properties']['shapeID']:f for f in source['features']};assert len(features)==6
catalogue=load(e['catalogue']); assert sc['record'] in (catalogue if isinstance(catalogue,list) else next(v for v in catalogue.values() if isinstance(v,list) and sc['record'] in v))
roster=load(custody['roster']);lineage=load(custody['lineage']);owners=load(e['owner_roster']);semantic=load(e['source_membership']['lineage']); canonical=load(e['source_membership']['parts'][0]); canon={f['id']:f for f in canonical['features']}; own={r['index']:r for r in owners};lin={r['index']:r for r in lineage['locations']}; assert len(own)==len(owners)==len(lin)==49625
family_rows=[r for r in roster if r['source_id'].startswith('gb:GRL:ADM1:')];assert len(family_rows)==6
expected={r['source_id']:r['owners'] for r in family_rows};assert expected=={k:v for k,v in lineage['reverse'].items() if k.startswith('gb:GRL:ADM1:')}
all_owners=sorted(o for v in expected.values() for o in v);assert len(set(all_owners))==len(all_owners)==11
for sid,oset in expected.items():
 assert sid.removeprefix('gb:GRL:ADM1:') in features
 for o in oset:
  assert own[o]['id']==lin[o]['id'] and own[o]['province_id']==lin[o]['province_id'];f=canon[own[o]['id']];assert f['properties']['parent_id']==own[o]['province_id'];assert lin[o]['source_atoms']==[sid]
for s in mem['splits']:
 sid=s['source_id'];assert len(expected[sid])>1 and s['owners']==expected[sid]
 assert {f['id'] for f in s['descendants']}=={own[o]['id'] for o in expected[sid]}
 for f in s['descendants']:assert f==canon[f['id']]
 for row in s['semantic_changes']:assert row in semantic['changes'] and row['replaces']==[sid]
assert len(mem['splits'])==4 and sum(len(s['descendants']) for s in mem['splits'])==9
prior_d=local('source-review/prior-assessment-custody.json');prior_all=load(prior_d['original']);prior=local('source-review/greenland-prior-assessments.json');assert prior==[r for r in prior_all['subjects'] if r['id'] in prior_d['extracted_subject_ids']]
stages=local('source-stage/original-stage-inputs.json');stage_by={r['target']:r for r in stages}; report_targets={r['id']:r for r in sr['targets']}
for t in e['targets']:
 sid=t['id'];assert expected[sid]==[t['pixelIndex']];assert canon[sid]==stage_by[sid]['selected'];assert stage_by[sid]['consumed']==features[sid.removeprefix('gb:GRL:ADM1:')];assert t['base_geometry']==canon[sid]['geometry'];assert report_targets[sid]['target_metadata']==canon[sid]['properties']['metadata'];assert t['territorial_exclusions']==[]
for d in sr['method_pins']:read(d)
read(sr['selected_bank']);read(sr['selected_part']);read(custody['hierarchy']);read(custody['extractor']);queue=load(custody['queue']);package=local('source-stage/package.json')
def find_equal(x,target):
 if isinstance(x,dict):return x==target or any(find_equal(v,target) for v in x.values())
 if isinstance(x,list):return any(find_equal(v,target) for v in x)
 return False
assert find_equal(queue,package)
blocks=[]
for b in package['native_blocks']:blocks+=local('source-stage/frozen-block-%03d.json.gz'%b) if False else json.loads(gzip.decompress(blob(HEAD,'coordination/engineering/greenland-repair-delivery-20261017/source-stage/frozen-block-%03d.json.gz'%b)))
assert len(blocks)==62096 and sum(z-a for y,a,z,*_ in blocks)==502216
patch=local('source-stage/native-patch.json');diag=local('native-diagnostic-001/native-diagnostic.json');assert patch['rows']==diag['requested_rows']==diag['supported_rows'];assert all(r[3]=='assigned_cells' for row in diag['decision_rows'] for r in row['runs']);assert [{**row,'runs':[r[:3] for r in row['runs']]} for row in diag['decision_rows']]==patch['rows']
assert not diag['held_rows'] and not diag['held_cells'] and diag['first_failure'] is None
from_blocks=collections.defaultdict(list)
for y,a,z,oo,ss,cl in blocks:
 assert len(oo)==len(ss)==1 and cl=='land';assert ss==[next(r['source_index'] for r in family_rows if r['owners']==oo)];from_blocks[y].append([a,z,oo[0]])
assert [{'y':y,'runs':rr} for y,rr in sorted(from_blocks.items())]==patch['rows']
lat=np.frombuffer(read(e['native_latitudes'],True),dtype='<f8');assert len(lat)==262166
physical=load(e['physical_evidence']);read(e['physical_input']);read(e['physical_reproduction']); phys={r['target']:r for r in physical['results']}
result={'head':HEAD,'authority_checkpoint':'627e774149c0acb9b0197f1fd506ebb327b5f36e','reviewer':os.environ.get('CODEX_THREAD_ID'),'method':'Independent Shapely exact native-centre covers, literal raw roster/canonical/history joins; no production constructor reused for geometric decisions','runtime':{'shapely':shapely.__version__,'geos':shapely.geos_version_string,'numpy':np.__version__},'raw_source_crs':source.get('crs'),'features':[],'targets':[],'literal_history_equal':True,'split_originals':4,'split_descendants':9,'frozen_intervals':len(blocks),'native_patch_rows':len(patch['rows'])}
for sid,oo in expected.items():
 f=features[sid.removeprefix('gb:GRL:ADM1:')];g=shape(f['geometry']);assert g.is_valid;result['features'].append({'id':sid,'name':f['properties']['shapeName'],'owners':oo,**geom_stats(g)})
for t in e['targets']:
 sid=t['id'];owner=t['pixelIndex'];rows=[(r['y'],a,z) for r in patch['rows'] for a,z,o in r['runs'] if o==owner];xs=np.concatenate([np.arange(a,z,dtype=np.float64) for y,a,z in rows]);ys=np.concatenate([np.full(z-a,lat[y]) for y,a,z in rows]);xs=(xs+.5)/262166*360-180;points=shapely.points(xs,ys)
 def hits(g):
  shapely.prepare(g);return int(np.count_nonzero(shapely.covers(g,points)))
 source_hits={f['properties']['shapeName']:hits(shape(f['geometry'])) for f in features.values()};assert source_hits[canon[sid]['properties']['name']]==len(xs) and sum(source_hits.values())==len(xs)
 support_hits={};support_stats={}
 for key,value in phys[sid]['support'].items():
  gg=value if key=='hierarchy_disagreements' else {key:value}
  for k,v in gg.items():g=shape(v);support_hits[k]=hits(g);support_stats[k]=geom_stats(g)
 issue_hits=[]
 for issue in phys[sid]['issues']:
  assert set(issue)=={'reason','geometry'};g=shape(issue['geometry']);issue_hits.append({'reason':issue['reason'],'hits':hits(g),**geom_stats(g)})
 assert support_hits['mapped_land_support']==len(xs);assert all(v==0 for k,v in support_hits.items() if k!='mapped_land_support');assert all(r['hits']==0 for r in issue_hits)
 result['targets'].append({'id':sid,'owner':owner,'candidate_centres':len(xs),'source_hits':source_hits,'physical_hits':support_hits,'physical_geometries':support_stats,'issues':issue_hits,'selected_base_hits':hits(shape(t['base_geometry'])),'selected_source_intent':canon[sid]['properties']['metadata'].get('scale_review'),'selection_reason':canon[sid]['properties']['metadata']['selection_reason']})
 print(owner,len(xs),source_hits,support_hits,flush=True)
assert sum(r['candidate_centres'] for r in result['targets'])==502216
result['consumed']=list(consumed.values());result['unique_raw_plus_decoded_input_bytes']=sum(v['bytes']+v.get('decoded_bytes',0) for v in consumed.values());assert result['unique_raw_plus_decoded_input_bytes']<=268435456
out=W/'.review-greenland/source-probe-result.json';out.write_text(json.dumps(result,indent=2)+'\n');print('PASS',out,flush=True)

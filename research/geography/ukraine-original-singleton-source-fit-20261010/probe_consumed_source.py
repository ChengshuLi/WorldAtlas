import os,sys,json,gzip,hashlib,time,resource,pathlib,subprocess
START=time.monotonic(); ROOT=pathlib.Path(__file__).resolve().parents[3]; OWN='research/geography/ukraine-original-singleton-source-fit-20261010'; COMMIT='c28077da970ae39550e5edea790a266b060d3de5'
sys.path.insert(0,str(ROOT/'scripts'))
from evidence.immutable import Baseline,NewVintage,descriptor,canonical_json
from shapely.geometry import shape
import shapely,numpy
sha=lambda b:hashlib.sha256(b).hexdigest()
paths=['data/administrative-sources.json','scripts/administrative.py','scripts/evidence/immutable.py','scripts/evidence/exact_predicates.py','coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json','coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/payloads/541236815314006fd30cd216a42cd7aaca78fa7eb50423515ca8b96bc0b87014.bin']
pins=[descriptor(p,subprocess.check_output(['git','-C',str(ROOT),'show',COMMIT+':'+p])) for p in paths]
base=Baseline(ROOT,COMMIT,pins);dest=NewVintage(base,OWN+'/','consumed-source-probe-001',['result.json'])
index=json.loads(base.pinned_bytes(paths[-2]));raw=base.pinned_bytes(paths[-1]);assert sha(raw)=='541236815314006fd30cd216a42cd7aaca78fa7eb50423515ca8b96bc0b87014';decoded=gzip.decompress(raw);base.admit('decoded-original-components-004',len(decoded));assert sha(decoded)=='0a895961defbcf80f8cc2e97cd7253830f2720a2fb51b6d4439c53ef0d1f80d9'
cid='physical-component:6fd25496ae4a7635eef229d0cfd1eb8dc7d9c10c252d3255fe8d42d186e706d1';fs=json.loads(decoded)['features'];m=[(i,f) for i,f in enumerate(fs) if f['id']==cid];assert len(m)==1;ordinal,cf=m[0];assert sha(canonical_json(cf))=='acd61551d2dbc9b6925e6d8c2d17cb210a6dcf6f3d80bbbadb64951660e3b746';assert sha(canonical_json(cf['geometry']))=='92fbd683db1eab874c905ff1bf95cbb291a5d917d9986f40349e23c5a4e77ca7'
sourcepath=OWN+'/inputs/geoBoundaries-UKR-ADM2_simplified.geojson';sraw=(ROOT/sourcepath).read_bytes();base.admit(sourcepath,len(sraw));reg=json.loads(base.pinned_bytes('data/administrative-sources.json'))['gb:UKR:ADM2'];assert sha(sraw)==reg['sha256']=='c102ab08775ce4dc25a64e133bb7726a1b50715d31140e9846eaad26602631cb';source=json.loads(sraw);assert len(source['features'])==495
sid='74538382B77535249747568';sm=[f for f in source['features'] if f['properties']['shapeID']==sid];assert len(sm)==1;sf=sm[0];cg=shape(cf['geometry']);sg=shape(sf['geometry']);assert cg.is_valid and sg.is_valid and not cg.is_empty and not sg.is_empty
hits=[];bboxmatches=[]
for f in source['features']:
 g=shape(f['geometry']);assert g.is_valid and not g.is_empty
 a,b,c,d=g.bounds;x,y,z,w=cg.bounds
 if c<x or z<a or d<y or w<b:continue
 bboxmatches.append(f['properties']['shapeID']);inter=g.intersection(cg)
 if inter.area>0:hits.append(f['properties']['shapeID'])
rem=cg.difference(sg);same=cg.symmetric_difference(cg.intersection(sg));exact=base.load_modules({'exact_predicates':'scripts/evidence/exact_predicates.py'})['exact_predicates']
try:exact.prepare_geometry(cf['geometry']);exact_valid='supported-valid'
except Exception as e:exact_valid=type(e).__name__+': '+str(e)
r={'issue':1693,'component':cid,'batch':'gap-operational-batch:b139696d47c4fa03f8f73dbe','baseline':COMMIT,'original_containing_file':paths[-1],'original_ordinal':ordinal,'component_feature_sha256':sha(canonical_json(cf)),'component_geometry_sha256':sha(canonical_json(cf['geometry'])),'source':descriptor(sourcepath,sraw),'source_metadata':reg,'source_target':sf,'source_feature_sha256':sha(canonical_json(sf)),'source_entire_product_features':495,'source_bbox_candidate_ids':bboxmatches,'positive_area_source_ids':hits,'predicates':{'candidate_valid':cg.is_valid,'exact_binary64_candidate_validity':exact_valid,'source_target_covers_whole_component':sg.covers(cg),'unsupported_remainder_empty':rem.is_empty,'source_intersection_symmetric_difference_empty':same.is_empty,'only_target_positive_area_source':hits==[sid]},'unsupported_remainder':rem.__geo_interface__,'intersection_symmetric_difference':same.__geo_interface__,'candidate_area_coordinate_units_squared':cg.area,'retained_measured_fragment_area_m2':cf['properties']['measured_fragment_area_sum_m2'],'elapsed_seconds':time.monotonic()-START,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'runtime':{'python':sys.version,'shapely':shapely.__version__,'geos':shapely.geos_version_string,'numpy':numpy.__version__},'input_logical_bytes':sum(base.consumed.values()),'source_pins':pins,'producer_sha256':sha(pathlib.Path(__file__).read_bytes()),'disposition':'source-containment-only; no accepted repair','unverified':['physical/query premise','current target-parent-source-year binding','genuine uncovered addition','target-loss and exact candidate/gain conservation','complete current affected-neighbor non-overlap','native operator and continuous selected delivery'],'scientific_or_publication_approval':False}
assert r['peak_rss_bytes']<1024**3
print(json.dumps(dest.publish({'result.json':r})));print(json.dumps({k:r[k] for k in ['predicates','candidate_area_coordinate_units_squared','peak_rss_bytes','elapsed_seconds','input_logical_bytes']}))

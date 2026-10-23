import os,sys,json,gzip,hashlib,subprocess,collections,time,resource,struct,pathlib
import numpy as np
import shapely
from shapely.geometry import shape
from shapely.strtree import STRtree
D=pathlib.Path(__file__).resolve().parent;R=D.parent/'worldatlas-primary'
BASE='d4968ddc37aa3aa6105e9610c9e6fadbb368ba14';Q='b3914bbdd2b6fdcb5e4ae7c860494425fa2c27ea';ROOT='coordination/engineering/global-current-cell-work-queue-20261014/'
# Read-only, original-key-only predicate screening. No native production or qualification.
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));start=time.monotonic();pins=[]
def raw(p,commit=BASE):
 b=subprocess.check_output(['git','-c','protocol.allow=never','-C',str(R),'show',commit+':'+p],env={**os.environ,'GIT_NO_LAZY_FETCH':'1'});pins.append({'commit':commit,'path':p,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()});return b
def read(p,commit=BASE):
 b=raw(p,commit);return json.loads(gzip.decompress(b)if p.endswith('.gz')else b)
cat=read('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json');roster=read(ROOT+'source-feature-roster.json.gz',Q);rs=read(ROOT+'source-raster-summary.json',Q);ls=read(ROOT+'lineage-summary.json',Q)
rows_path=D.parent/'screen-next-repair-package-20261017/gb-USA-ADM2--repair-evaluation.json.gz';rows_raw=rows_path.read_bytes();rows=json.loads(gzip.decompress(rows_raw));rows_pin={'path':str(rows_path),'bytes':len(rows_raw),'sha256':hashlib.sha256(rows_raw).hexdigest()}
latpin=ls['latitudes'];latraw=gzip.decompress(raw(latpin['path'],latpin['commit']));assert len(latraw)==latpin['decoded_bytes'] and hashlib.sha256(latraw).hexdigest()==latpin['decoded_sha256'];lat=np.frombuffer(latraw,dtype='<f8');size=len(lat)
keys=[(y,x,owners[0],kind) for y,a,z,owners,sids,kind in rows for x in range(a,z)];assert len(keys)==107131 and len({(y,x,o)for y,x,o,k in keys})==107131
pts=shapely.points(np.array([((x+.5)*360/size-180,float(lat[y]))for y,x,o,k in keys]));tree=STRtree(pts);key_index={(y,x,o):i for i,(y,x,o,k)in enumerate(keys)}
expected=collections.defaultdict(set);contacts=[]
for y,a,z,owners,sids,kind in rows:
 foreign=[roster[i-1]for i in sids if not roster[i-1]['source_id'].startswith('gb:USA:')]
 for x in range(a,z):
  for s in sids:expected[roster[s-1]['source_id']].add(key_index[(y,x,owners[0])])
  if foreign:contacts.append({'y':y,'x':x,'owner_index':owners[0],'physical_class':kind,'foreign_source_ids':[f['source_id']for f in foreign],'all_foreign_ownerless':all(not f['owners']for f in foreign)})
assert len(contacts)==63 and all(c['all_foreign_ownerless']for c in contacts)
(D/'original-foreign-contact-keys.json').write_text(json.dumps({'original_denominator':107131,'keys':contacts,'count':len(contacts),'original_transport':rows_pin},indent=2)+'\n')
products=[];mismatches=[];contact_features=[];count=0;decoded=0
for p in cat['products']:
 pieces=[]
 for part in p['parts']:
  b=raw(part['path']);assert len(b)==part['bytes']and hashlib.sha256(b).hexdigest()==part['sha256'];d=gzip.decompress(b);assert len(d)==part['uncompressed_bytes']and hashlib.sha256(d).hexdigest()==part['uncompressed_sha256'];pieces.append(d)
 body=b''.join(pieces);assert len(body)==p['original_bytes']and hashlib.sha256(body).hexdigest()==p['original_sha256'];fs=json.loads(body)['features'];assert len(fs)==p['feature_count'];decoded+=len(body)
 ids=[p['key']+':'+f['properties']['shapeID']for f in fs];assert len(set(ids))==len(ids)
 roster_rows=[r for r in roster if r['family_index']==len(products)];assert [r['source_id']for r in roster_rows]==ids
 gs=shapely.from_geojson(json.dumps({'type':'FeatureCollection','features':fs})).geoms
 hits=tree.query(gs,predicate='covers'); actual=collections.defaultdict(set)
 for fi,pi in zip(*hits):actual[int(fi)].add(int(pi))
 union=set()
 for i,id in enumerate(ids):
  observed=actual.get(i,set());expect=expected.get(id,set());union.update(observed)
  if observed!=expect:mismatches.append({'source_id':id,'geometry_valid':bool(gs[i].is_valid),'only_point_predicate':[keys[k][:3]for k in sorted(observed-expect)],'only_original_native':[keys[k][:3]for k in sorted(expect-observed)]})
  if observed:contact_features.append({'source_id':id,'name':fs[i]['properties'].get('shapeName'),'feature_ordinal':i,'source_keys':len(observed),'owner_mapping':roster_rows[i]['owners'],'geometry_valid':bool(gs[i].is_valid),'bounds':list(gs[i].bounds)})
 products.append({'family':p['key'],'features':len(fs),'original_bytes':len(body),'original_sha256':p['original_sha256'],'point_predicate_contact_features':len(actual),'point_predicate_contact_keys':len(union),'raw_native_expected_contact_keys':len(set().union(*(expected.get(id,set())for id in ids)))})
 count+=len(fs)
 if len(products)%25==0:print('screened',len(products),'families',count,'features',flush=True)
 assert time.monotonic()-start<180,'180-second bounded screen deadline'
 del pieces,body,fs,gs,hits,actual
assert len(products)==368 and count==73567
out={'kind':'independent-whole-source-original-key-predicate-screen','baseline':BASE,'queue_commit':Q,'method':'Complete original payload authentication and exact-ID inventory; Shapely covers at 107131 original native cell-centre longitudes and pinned binary64 latitudes. This is a bounded diagnostic independent of native exact rational arithmetic. No full raster or source/native authority construction.','original_denominator':107131,'intervals':len(rows),'owners':len({k[2]for k in keys}),'all_source_families':len(products),'all_original_features':count,'all_decoded_source_bytes':decoded,'source_roster_matches_complete_product_order':True,'all_foreign_contacts_ownerless':True,'original_foreign_contact_keys':63,'products':products,'contact_features':contact_features,'native_vs_point_mismatches':mismatches,'seconds':round(time.monotonic()-start,3),'max_rss_bytes_linux':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'resource_allowance':{'address_space_bytes':2*1024**3,'wall_deadline_seconds':180,'sequential_whole_source_reads':True},'runtime':{'python':sys.version,'shapely':shapely.__version__},'inputs':pins,'original_transport':rows_pin,'limits':['Native rational arithmetic and half-open boundary conventions remain authoritative; point predicates are independent diagnostic evidence only.','Complete negative coverage of retained original corpus does not establish contemporary legal boundaries or physical interpretation.','All349 direct owners plus NYC and held Fairfax remain in the original denominator; no accepted repair credit is established.']}
(D/'complete-source-scope-screen.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['all_source_families','all_original_features','original_foreign_contact_keys','native_vs_point_mismatches','seconds','max_rss_bytes_linux']},indent=2))

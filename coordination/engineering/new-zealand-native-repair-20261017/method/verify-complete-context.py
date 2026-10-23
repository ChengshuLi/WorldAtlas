"""Derive original census membership and retain all external-source contrary hits.
Usage: python verify-complete-context.py READ_ONLY_REPO FRESH_OUTPUT
"""
import collections,gzip,hashlib,io,json,os,pathlib,resource,subprocess,sys,time
import numpy as np,shapely
from shapely.geometry import shape
W,O=map(lambda v:pathlib.Path(v).absolute(),sys.argv[1:]);H='d4968ddc37aa3aa6105e9610c9e6fadbb368ba14';S='1b7de4e59053fa2505b891ecd842fd70a6102a19';F='9e3c3d8169526c4283699d80dbf7b66fc6cfc044';P='coordination/engineering/new-zealand-native-repair-20261017/';Q='coordination/engineering/global-current-cell-work-queue-20261014/'
assert O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents))
pins={};total=0;MAX=64*1024*1024;PHASE=256*1024*1024;started=time.monotonic();sha=lambda b:hashlib.sha256(b).hexdigest();env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'}
def read(path,commit=H,expected=None):
 global total
 assert time.monotonic()-started<180 and path and not path.startswith('/') and all(x not in ['', '.', '..'] for x in path.split('/'))
 cmd=['git','-c','protocol.allow=never','-C',str(W)];meta,name=subprocess.check_output(cmd+['ls-tree','-z',commit,'--',path],env=env).rstrip(b'\0').split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644' and kind=='blob' and name.decode()==path
 size=int(subprocess.check_output(cmd+['cat-file','-s',oid],env=env));assert 0<size<=MAX
 b=subprocess.check_output(cmd+['cat-file','blob',oid],env=env);assert len(b)==size and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+b).hexdigest()==oid
 pin={'path':path,'commit':commit,'mode':mode,'git_blob_oid':oid,'bytes':size,'sha256':sha(b)}
 if expected:assert size==expected['bytes'] and sha(b)==expected['sha256']
 if path.endswith('.gz'):
  with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:d=f.read(MAX+1)
  assert len(d)<=MAX;pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
  if expected:assert len(b)==expected['decoded_bytes'] and sha(b)==expected['decoded_sha256']
 if (commit,path) not in pins:total+=size+pin.get('decoded_bytes',0)
 assert total<=PHASE;pins[(commit,path)]=pin;return b
js=lambda p,h=H:json.loads(read(p,h))
a=js(P+'source-stage/source-scope-assessment.json',S);roster=js(Q+'source-feature-roster.json.gz');catalogue=js('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json');census=js(Q+'source-census-summary.json');families={r['key']:r for r in catalogue['products']};assert len(families)==len(catalogue['products']);actual=collections.defaultdict(list)
for i,r in enumerate(roster):
 assert r['source_index']==i+1 and r['source_id'].rsplit(':',1)[0] in families
 actual[r['source_id'].rsplit(':',1)[0]].append(r)
assert set(actual)==set(families) and len(roster)==sum(r['feature_count'] for r in families.values())==census['features_processed'] and len(families)==census['products_processed'] and census['source_features_excluded']==[]
for k,rows in actual.items():assert len(rows)==families[k]['feature_count'] and len({r['source_id'] for r in rows})==len(rows) and [r['ordinal'] for r in rows]==list(range(len(rows)))
ownerless=[r for r in roster if not r['owners']];domestic=[r for r in ownerless if r['source_id'].startswith('gb:NZL:')];foreign=[r for r in ownerless if not r['source_id'].startswith('gb:NZL:')]
queue=js(Q+'source-package-queue.json');companion=next(p for p in queue['packages'] if p['package_id']=='gb-NZL-ADM2--physical-interpretation');segments=[]
for b in range(38,42):segments+=js(P+f'frozen-queue/block-{b:03}.json.gz',F)
cells=[(x,y,o[0]) for y,start,end,o,s,k in segments for x in range(start,end)];assert len(cells)==a['original_cells'];foreign_indices={r['source_index'] for r in foreign};original_hits=[r for r in segments if foreign_indices.intersection(r[4])];assert not original_hits
lp=next(p for p in a['inputs'] if 'native-row-latitudes' in p['path']);lat=np.frombuffer(read(lp['path'],lp['commit'],lp),dtype='<f8');pts=shapely.points([[(x+.5)/262166*360-180,lat[y]] for x,y,o in cells]);tree=shapely.STRtree(pts)
nepath='data/regional-review/regional-review-0c300e5f6ecdc793/sources/natural-earth-ca96624/ne_10m_admin_1_states_provinces.geojson.gz';neb=read(nepath);registry=js('data/sources.json');assert sha(neb)==registry['hashes']['ne_10m_admin_1_states_provinces'];ne=json.loads(neb);ids=[f['properties']['adm1_code'] for f in ne['features']];assert len(ids)==len(set(ids));hits=[];invalid=[];negative=[];keyset=set();tested=0
for ordinal,f in enumerate(ne['features']):
 if f['properties']['adm0_a3']=='NZL':continue
 tested+=1;g=shape(f['geometry']);ix=tree.query(g)
 if not len(ix):continue
 if not g.is_valid:invalid.append({'ordinal':ordinal,'id':f['properties']['adm1_code'],'bbox_cells':[[*cells[int(i)]] for i in ix]});continue
 ix=[int(i) for i in ix[shapely.covers(g,pts[ix])]]
 if ix:
  keyset.update(ix);negative.append(f);hits.append({'ordinal':ordinal,'id':f['properties']['adm1_code'],'country':f['properties']['adm0_a3'],'name':f['properties']['name'],'native_cells':[[*cells[i]] for i in sorted(ix)]})
countrykeys={tuple(k) for k in a['foreign_country_native_cells']};nekeys={cells[i] for i in keyset};assert not invalid
result={'version':1,'original_cells':len(cells),'original_source_products':len(families),'original_source_features':len(roster),'complete_family_checks':[{'source_id':k,'actual_features':len(v),'catalogue_features':families[k]['feature_count'],'original_sha256':families[k]['original_sha256']} for k,v in actual.items()],'original_ownerless_features':len(ownerless),'domestic_ownerless_features':domestic,'foreign_ownerless_features':len(foreign),'foreign_ownerless_candidate_cells':sum(r[2]-r[1] for r in original_hits),'natural_earth_complete_features':len(ne['features']),'natural_earth_foreign_features':tested,'foreign_natural_earth_hits':hits,'foreign_natural_earth_cells':len(nekeys),'invalid_foreign_bbox_contacts':invalid,'foreign_country_and_adm1_exact_keys_equal':nekeys==countrykeys,'physical_companion':companion,'inputs':list(pins.values()),'processing_bytes':total,'elapsed_seconds':time.monotonic()-started,'max_rss_linux_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limits':['Ownerless counts are derived from the complete authenticated original source roster, whose per-product identities and counts match the original complete catalogue and census; they are not arbitrary screening prerequisites.','Original-corpus source absence, coarse country references and Natural Earth ADM1 context do not certify current sovereignty or dry land.','All complete input features are preserved; only foreign records intersecting the original candidate centres supply additional explicit territorial negatives.','The entire separate physical-interpretation companion remains outside this repair denominator.']}
outputs={'complete-context.json':result,'foreign-adm1-features.geojson':{'type':'FeatureCollection','features':negative}}
encoded={n:(json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n').encode() for n,v in outputs.items()};assert total+sum(map(len,encoded.values()))<=PHASE and all(len(b)<=MAX for b in encoded.values());assert not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
for n,b in encoded.items():
 with (O/n).open('xb') as f:f.write(b)
with (O/'preparation.json').open('x') as f:json.dump({'complete':True,'outputs':{n:{'bytes':len(b),'sha256':sha(b)} for n,b in encoded.items()}},f);f.write('\n')
print(json.dumps({k:result[k] for k in ['original_cells','original_source_products','original_source_features','original_ownerless_features','foreign_ownerless_features','natural_earth_foreign_features','foreign_natural_earth_cells','processing_bytes','elapsed_seconds']}))

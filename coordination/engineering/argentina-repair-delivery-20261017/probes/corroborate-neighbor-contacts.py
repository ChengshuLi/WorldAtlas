"""Corroborate foreign contacts with complete neighboring-country original products.
Usage: python corroborate-neighbor-contacts.py REPO EXACT_METHOD_COMMIT FRESH_OUTPUT
Whole original geometries are never repaired or clipped. This supplements the
complete368-family census; it is not an exact-rational native qualification.
"""
import collections,gzip,hashlib,json,os,resource,subprocess,sys,time
import numpy as np
import shapely
from shapely.geometry import shape
from pathlib import Path
assert len(sys.argv)==4 and __debug__
R=Path(sys.argv[1]).absolute();C=sys.argv[2];O=Path(sys.argv[3]).absolute();H='d4968ddc37aa3aa6105e9610c9e6fadbb368ba14';Q='b3914bbdd2b6fdcb5e4ae7c860494425fa2c27ea';P='coordination/engineering/argentina-repair-delivery-20261017'
assert len(C)==40 and all(c in '0123456789abcdef'for c in C)
assert O.parent.is_dir()and not O.exists()and not O.is_symlink()and all(not p.is_symlink()for p in [R,O,*R.parents,*O.parents])
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda v:(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()
inputs={};total=0;start=time.monotonic();env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_TERMINAL_PROMPT':'0'}
def read(h,p,decode=False):
 global total
 assert len(h)==40 and all(c in '0123456789abcdef'for c in h)and not p.startswith('/')and all(x not in ('','.','..')for x in p.split('/'))
 def git(*args):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(R),*args],env=env,timeout=30)
 row=git('ls-tree','-z',h,'--',p).rstrip(b'\0');meta,name=row.split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644'and kind=='blob'and name.decode()==p
 n=int(git('cat-file','-s',oid));assert 0<n
 b=git('cat-file','blob',oid);assert len(b)==n and hashlib.sha1(b'blob '+str(n).encode()+b'\0'+b).hexdigest()==oid
 pin={'commit':h,'path':p,'mode':mode,'git_blob_oid':oid,'bytes':n,'sha256':sha(b)}
 if decode:
  import io
  with gzip.GzipFile(fileobj=io.BytesIO(b))as f:d=f.read()
  pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
 if(h,p)not in inputs:total+=n+pin.get('decoded_bytes',0)
 assert time.monotonic()-start<300;inputs[h,p]=pin;return b
assert read(C,P+'/probes/corroborate-neighbor-contacts.py')==Path(__file__).read_bytes()
js=lambda p,h=H,decode=False:json.loads(read(h,p,decode))
cat=js('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json');assert len(cat['products'])==368
roster=js('coordination/engineering/global-current-cell-work-queue-20261014/source-feature-roster.json.gz',Q,True);rmap={r['source_id']:r for r in roster};imap={r['source_index']:r for r in roster};assert len(rmap)==len(imap)==len(roster)==73567
line=js('coordination/engineering/global-current-cell-work-queue-20261014/lineage-summary.json');lp=line['latitudes'];lb=read(lp['commit'],lp['path'],True);pin=inputs[lp['commit'],lp['path']];assert pin['bytes']==lp['bytes']and pin['sha256']==lp['sha256']and len(lb)==lp['decoded_bytes']and sha(lb)==lp['decoded_sha256'];lat=np.frombuffer(lb,dtype='<f8');N=len(lat)
original=js(P+'/original-scope/original-intervals.json.gz',C,True);pre=js(P+'/original-scope/preliminary-source-holds.json',C);keys=[];expected={}
for y,a,z,ow,sids,k in original:
 assert len(ow)==1
 foreign=sorted(imap[i]['source_id']for i in sids if not imap[i]['source_id'].startswith('gb:ARG:'))
 for x in range(a,z):
  keys.append({'y':y,'x':x,'pixelIndex':ow[0],'physical_class':k})
  if foreign:expected[y,x]=foreign
assert len(keys)==28846 and len({(k['y'],k['x'])for k in keys})==28846 and len(expected)==1025
assert expected=={(k['y'],k['x']):k['original_source_ids']for k in pre['foreign_keys']}
# Correctly rounded binary64 representation of the same exact rational longitude.
# Point outcomes below remain explicitly supplementary to exact stock native logic.
xs=np.array([(360*k['x']+180-180*N)/N for k in keys]);ys=np.array([lat[k['y']]for k in keys]);bbox=[float(xs.min()),float(ys.min()),float(xs.max()),float(ys.max())]
products=[p for p in cat['products']if p['key'].split(':')[1]in {'BOL','BRA','CHL','PRY','URY'}];assert len(products)==10
observed=collections.defaultdict(set);interior=collections.defaultdict(set);boundary=collections.defaultdict(set);source_rows=[];families=[];invalid=[]
for rec in products:
 chunks=[]
 for cp in sorted(rec['parts'],key=lambda p:p['ordinal']):
  d=read(H,cp['path'],True);p=inputs[H,cp['path']];assert p['bytes']==cp['bytes']and p['sha256']==cp['sha256']and len(d)==cp['uncompressed_bytes']and sha(d)==cp['uncompressed_sha256'];chunks.append(d)
 b=b''.join(chunks);assert len(b)==rec['original_bytes']and sha(b)==rec['original_sha256'];fs=json.loads(b)['features'];assert len(fs)==rec['feature_count'];seen=set();family_hits=set()
 for ordinal,f in enumerate(fs):
  sid=rec['key']+':'+f['properties']['shapeID'];assert sid not in seen;seen.add(sid);rr=rmap[sid];assert rr['ordinal']==ordinal
  g=shape(f['geometry']);valid=bool(g.is_valid);row={'source_id':sid,'source_index':rr['source_index'],'ordinal':ordinal,'owners':rr['owners'],'whole_geometry_sha256':sha(canon(f['geometry'])),'geometry_type':g.geom_type,'geometry_valid':valid,'geometry_empty':bool(g.is_empty),'contact_cells':0,'strict_interior_cells':0,'boundary_cells':0}
  if not valid:row['invalid_reason']=shapely.is_valid_reason(g);invalid.append(sid)
  if not g.is_empty:
   a,c,z,d=g.bounds;ix=np.flatnonzero((xs>=a)&(xs<=z)&(ys>=c)&(ys<=d))
   if len(ix):
    cov=shapely.intersects_xy(g,xs[ix],ys[ix]);inside=shapely.contains_xy(g,xs[ix],ys[ix]);assert np.all(~inside|cov)
    for j,ci,ii in zip(ix,cov,inside):
     if ci:
      key=(keys[j]['y'],keys[j]['x']);observed[key].add(sid);family_hits.add(key);row['contact_cells']+=1
      if ii:interior[key].add(sid);row['strict_interior_cells']+=1
      else:boundary[key].add(sid);row['boundary_cells']+=1
  source_rows.append(row)
 assert seen=={sid for sid in rmap if sid.startswith(rec['key']+':')}
 families.append({'record':rec,'complete_features':len(fs),'observed_original_contact_cells':len(family_hits)});print(json.dumps({'family':rec['key'],'features':len(fs),'contact_cells':len(family_hits)}),flush=True)
 assert time.monotonic()-start<300
actual={k:sorted(v)for k,v in observed.items()};allkeys=sorted(set(actual)|set(expected));differences=[{'y':y,'x':x,'census_source_ids':expected.get((y,x),[]),'point_source_ids':actual.get((y,x),[])}for y,x in allkeys if expected.get((y,x),[])!=actual.get((y,x),[])]
contacts=[{**next(k for k in keys if(k['y'],k['x'])==(y,x)),'source_ids':actual[y,x],'strict_interior_source_ids':sorted(interior.get((y,x),set())),'boundary_source_ids':sorted(boundary.get((y,x),set()))}for y,x in sorted(actual)]
strict_cells=sum(bool(v)for v in interior.values());boundary_cells=sum(bool(v)for v in boundary.values())
assert strict_cells==sum(bool(k['strict_interior_source_ids'])for k in contacts)
assert boundary_cells==sum(bool(k['boundary_source_ids'])for k in contacts)
assert sum(len(k['strict_interior_source_ids'])for k in contacts)==sum(r['strict_interior_cells']for r in source_rows)
assert sum(len(k['boundary_source_ids'])for k in contacts)==sum(r['boundary_cells']for r in source_rows)
assert sum(len(k['source_ids'])for k in contacts)==sum(r['contact_cells']for r in source_rows)
assert all(sorted(set(k['strict_interior_source_ids'])|set(k['boundary_source_ids']))==k['source_ids']and not set(k['strict_interior_source_ids'])&set(k['boundary_source_ids'])for k in contacts)
result={'kind':'complete-neighbor-original-point-corroboration','original_cells':len(keys),'original_intervals':len(original),'original_owners':len({k['pixelIndex']for k in keys}),'complete_global_census_families':368,'complete_neighbor_products':len(families),'complete_neighbor_features':len(source_rows),'families':families,'sources':source_rows,'contacts':contacts,'foreign_original_contact_cells':len(actual),'contact_source_features':len({s for v in actual.values()for s in v}),'strict_interior_cells':strict_cells,'boundary_contact_cells':boundary_cells,'per_key_exact_source_id_census_equality':not differences,'differences':differences,'invalid_original_features':invalid,'invalid_original_contact_features':[r['source_id']for r in source_rows if not r['geometry_valid']and r['contact_cells']],'coordinate_convention':'Pinned native binary64 row latitudes and correctly rounded binary64 evaluation of exact rational longitude(360*x+180-180*size)/size; stock native authority retains exact rational predicates.','geometry_handling':'Every whole original feature from every retained level for BOL,BRA,CHL,PRY,URY; no owners filter, no geometry repair, no clipping or invalid-feature omission. Inclusive whole-feature bounds only prefilter point tests.','input_encoded_decoded_bytes':total,'inputs':list(inputs.values()),'runtime':{'python':sys.version,'numpy':np.__version__,'shapely':shapely.__version__,'geos':shapely.geos_version_string},'elapsed_seconds':time.monotonic()-start,'max_rss_bytes_linux':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'limits':['Supplementary corroboration of the complete368-family census; this regional screen is not the global exclusion scope.','Binary64 point predicates are not exact-rational stock native qualification. All boundary/difference/invalid outcomes are retained without correction or source approval.','All28,846 original keys are screened, including all held owners and classes.','Complete domestic ARG competitors and every whole foreign negative remain required in actual native construction.']}
encoded=canon(result);assert time.monotonic()-start<300
assert O.parent.is_dir()and not O.exists()and all(not p.is_symlink()for p in[O,*O.parents]);O.mkdir()
with(O/'neighbor-point-corroboration.json').open('xb')as f:f.write(encoded)
print(json.dumps({'original':28846,'neighbor_features':len(source_rows),'foreign_cells':len(actual),'features':result['contact_source_features'],'differences':len(differences),'invalid':len(invalid),'invalid_contacts':len(result['invalid_original_contact_features']),'output_bytes':len(encoded),'seconds':time.monotonic()-start}))

"""Authenticate complete KOR originals and actual named-city construction.
Exact ordinary Git inputs; no geometry repair, scientific receipts or byte caps.
Usage: python prepare-stage.py REPO EXACT_METHOD_COMMIT FRESH_OUTPUT
"""
import collections,gzip,hashlib,json,os,pathlib,subprocess,sys,time
import numpy as np
import shapely
from shapely.geometry import shape
assert len(sys.argv)==4 and __debug__
W=pathlib.Path(sys.argv[1]).absolute();C=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute()
H='3b3e9e675cfb37999d5665438f9fbf25bbd4238b';Q='b3914bbdd2b6fdcb5e4ae7c860494425fa2c27ea';P='coordination/engineering/korea-native-repair-20261017'
assert len(C)==40 and all(c in '0123456789abcdef'for c in C)
assert W.is_dir() and O.parent.is_dir() and not O.exists() and all(not p.is_symlink()for root in(W,O)for p in(root,*root.parents))
start=time.monotonic();inputs={};total=0;DEADLINE_SECONDS=1200
sha=lambda b:hashlib.sha256(b).hexdigest()
env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_TERMINAL_PROMPT':'0'}
def git(*args):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),*args],env=env,timeout=30)
def read(p,h=H):
 global total
 assert not p.startswith('/')and all(x not in('','.','..')for x in p.split('/'));assert time.monotonic()-start<DEADLINE_SECONDS
 row=git('ls-tree','-z',h,'--',p).rstrip(b'\0');meta,name=row.split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644'and kind=='blob'and name.decode()==p
 size=int(git('cat-file','-s',oid));assert 0<size
 b=git('cat-file','blob',oid);assert len(b)==size and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+b).hexdigest()==oid
 pin={'path':p,'commit':h,'mode':mode,'git_blob_oid':oid,'bytes':size,'sha256':sha(b)}
 if p.endswith('.gz'):
  import io
  with gzip.GzipFile(fileobj=io.BytesIO(b))as f:d=f.read()
  pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
 if(h,p)not in inputs:total+=size+pin.get('decoded_bytes',0)
 inputs[h,p]=pin;return b
js=lambda p,h=H:json.loads(read(p,h))
def exact(rows,key):
 out={}
 for r in rows:assert r[key]not in out;out[r[key]]=r
 assert out;return out

assert read(P+'/method/screen-foreign.py',C)==pathlib.Path(__file__).read_bytes()
cat=js('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json');rosterrows=js('coordination/engineering/global-current-cell-work-queue-20261014/source-feature-roster.json.gz',Q);roster=exact(rosterrows,'source_id');segments=js(P+'/original-scope/original-intervals.json.gz',C)
selection=js('data/ownership-selection.json');manifest=js(selection['manifest_path']);lat=manifest['native_latitudes'];b=read(lat['path'],lat['commit']);assert sha(b)==lat['decoded_sha256'];latitude=np.frombuffer(b,dtype='<f8')
cells=[(x,y,o[0])for y,a,z,o,ss,c in segments for x in range(a,z)];assert len(cells)==31206
xy=np.array([[(x+.5)/262166*360-180,latitude[y]]for x,y,o in cells]);points=shapely.points(xy);domain=(float(xy[:,0].min()),float(xy[:,1].min()),float(xy[:,0].max()),float(xy[:,1].max()));summaries=[];contacts=[];near=[];unresolved=[];seen=set()
for rec in cat['products']:
 family=rec['key'];chunks=[]
 for part in rec['parts']:
  d=read(part['path']);pin=inputs[H,part['path']];assert pin['bytes']==part['bytes']and pin['sha256']==part['sha256']and len(d)==part['uncompressed_bytes']and sha(d)==part['uncompressed_sha256']and sum(map(len,chunks))==part['offset'];chunks.append(d)
 raw=b''.join(chunks);assert len(raw)==rec['original_bytes']and sha(raw)==rec['original_sha256'];product=json.loads(raw);fs=product['features'];assert len(fs)==rec['feature_count'];ids=[];hits=0;tested=0;ownerless=0
 for ordinal,f in enumerate(fs):
  sid=family+':'+str(f['properties']['shapeID']);assert sid in roster and roster[sid]['ordinal']==ordinal and sid not in seen;seen.add(sid);ids.append(sid)
  if family.startswith('gb:KOR:'):continue
  rr=roster[sid];ownerless+=not rr['owners'];g=shape(f['geometry']);bounds=g.bounds
  assert len(bounds)==4 and all(np.isfinite(bounds))
  a,b,c,d=bounds
  if c<domain[0]or a>domain[2]or d<domain[1]or b>domain[3]:continue
  mask=(xy[:,0]>=a)&(xy[:,0]<=c)&(xy[:,1]>=b)&(xy[:,1]<=d);ind=np.flatnonzero(mask)
  if not len(ind):continue
  tested+=1;near.append({'source_id':sid,'owners':rr['owners'],'source_index':rr['source_index'],'whole_bounds':list(bounds),'candidate_centres_in_bounds':len(ind),'valid':bool(g.is_valid)})
  if not g.is_valid:unresolved.append({'source_id':sid,'reason':shapely.is_valid_reason(g),'native_keys':[cells[int(i)]for i in ind]});continue
  ix=ind[np.asarray(shapely.covers(g,points[ind]))];hits+=len(ix)
  if len(ix):contacts.append({'source_id':sid,'owners':rr['owners'],'source_index':rr['source_index'],'native_keys':[cells[int(i)]for i in ix]})
 assert len(set(ids))==len(fs)and set(ids)=={r['source_id']for r in rosterrows if r['source_id'].startswith(family+':')}
 summaries.append({'family':family,'complete_features':len(fs),'whole_original_bytes':rec['original_bytes'],'whole_original_sha256':rec['original_sha256'],'foreign_ownerless_features':ownerless,'foreign_candidate_bbox_features':tested,'foreign_contact_keys':hits})
 print(family,len(fs),tested,hits,flush=True)
assert len(summaries)==368 and len(seen)==73567
out={'kind':'complete-whole-original-foreign-negative-screen','baseline':H,'input_commit':C,'original_cells':31206,'whole_products':len(summaries),'whole_features':len(seen),'domain':domain,'complete_families':summaries,'whole_foreign_bbox_candidates':near,'foreign_contacts':contacts,'invalid_relevant_originals':unresolved,'foreign_contact_cells':len({tuple(k[:2])for r in contacts for k in r['native_keys']}),'invalid_relevant_cells':len({tuple(k[:2])for r in unresolved for k in r['native_keys']}),'native_exclusion_families':sorted({r['source_id'].rsplit(':',1)[0]for r in near}),'inputs':list(inputs.values()),'limits':['Every complete original product is authenticated and parsed sequentially; no original is clipped, repaired or substituted.','Whole-feature bounds exclude only sources provably disjoint from every requested centre. Exact predicates test each remaining complete original geometry, including ownerless sources.','This is original-product contrary evidence, not global sovereignty or current administrative-boundary clearance.','Invalid original geometry intersecting candidate bounds stays unresolved and is never repaired.'], 'seconds':time.monotonic()-start}
assert not O.exists()and all(not p.is_symlink()for p in(O,*O.parents));O.mkdir()
body=(json.dumps(out,separators=(',',':'),ensure_ascii=False)+'\n').encode()
with(O/'whole-original-negatives.json').open('xb')as f:f.write(body)
print(json.dumps({k:out[k]for k in ['whole_products','whole_features','foreign_contact_cells','invalid_relevant_cells','native_exclusion_families','seconds']}))

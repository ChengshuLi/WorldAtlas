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
start=time.monotonic();inputs={};total=0;DEADLINE_SECONDS=600
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

assert read(P+'/method/verify-original-scope.py',C)==pathlib.Path(__file__).read_bytes()
import bisect
R='coordination/engineering/global-current-cell-work-queue-20261014/'
queue=js(R+'source-package-queue.json',Q);package=next(p for p in queue['packages']if p['package_id']=='gb-KOR-ADM2--repair-evaluation');sc=js(R+'source-census-summary.json',Q);ph=js(R+'physical-unassigned-summary.json',Q);roster=js(R+'source-feature-roster.json.gz',Q);wanted=set(package['owners']);rows=[]
def block(kind,n):
 item=sc['blocks'][n]if kind=='source-candidates'else next(x for x in ph['phases'][n]['files']if x['kind']==kind);out=[]
 for part in item.get('parts',[{**item,'path':f'{kind}-block-{n:03d}.json.gz'}]):
  p=R+part['path'];b=read(p,Q);pin=inputs[Q,p];assert pin['sha256']==part['sha256']and sha(b)==part['decoded_sha256'];out.extend(json.loads(b))
 if 'parts'in item:assert sha((json.dumps(out,separators=(',',':'),ensure_ascii=False)+'\n').encode())==item['decoded_sha256']
 return out
def hits(a,z,rr):
 i=bisect.bisect_right(rr,a,key=lambda r:r[1])
 while i<len(rr)and rr[i][0]<z:
  aa,zz,*_=rr[i];lo=max(a,aa);hi=min(z,zz)
  if lo<hi:yield lo,hi
  i+=1
for n in package['native_blocks']:
 source=block('source-candidates',n);land={r['y']:r['runs']for r in block('physical-support',n)};water={r['y']:r['runs']for r in block('inland-water-support',n)}
 for row in source:
  for a,z,owners,sids in row['runs']:
   if len(owners)!=1 or owners[0]not in wanted:continue
   mapped=[i for i in sids if roster[i-1]['owners']]
   if min(roster[i-1]['family_index']for i in mapped)!=package['source_family_index']:continue
   for kind,rr in [('land',land.get(row['y'],[])),('inland-water',water.get(row['y'],[]))]:
    for aa,zz in hits(a,z,rr):rows.append([row['y'],aa,zz,owners,sids,kind])
retained=js(P+'/original-scope/original-intervals.json.gz',C);assert retained==rows and len(rows)==9449 and sum(z-a for y,a,z,*_ in rows)==31206 and {o[0]for y,a,z,o,s,k in rows}==wanted
result={'original_package':package['package_id'],'queue_commit':Q,'original_cells':31206,'original_intervals':9449,'original_owners':64,'exact_immutable_source_physical_rejoin_equals_retained_transport':True,'inputs':list(inputs.values()),'limits':['This authenticates complete original scope only; source/native qualification and selected delivery remain separate.']}
assert not O.exists()and all(not p.is_symlink()for p in(O,*O.parents));O.mkdir()
with(O/'original-transport-check.json').open('x')as f:json.dump(result,f,separators=(',',':'));f.write('\n')
print('Complete original source/physical rejoin equals all retained 31,206 keys and 9,449 intervals.')

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

assert read(P+'/method/reconcile-authority.py',C)==pathlib.Path(__file__).read_bytes()
segments=js(P+'/original-scope/original-intervals.json.gz',C);original={(x,y,ow[0])for y,a,z,ow,ss,k in segments for x in range(a,z)};assert len(original)==sum(z-a for y,a,z,*_ in segments)==31206 and len(segments)==9449
patch=js(P+'/source-stage-001/native-patch.json',C);pk={(x,r['y'],o)for r in patch['rows']for a,z,o in r['runs']for x in range(a,z)}
diag=js(P+'/native-diagnostic-001/native-diagnostic.json',C);dk={(x,r['y'],o)for r in diag['supported_rows']for a,z,o in r['runs']for x in range(a,z)};assert pk==dk==original and diag['held_cells']==0 and not diag['held_rows']
con=js(P+'/native-authority-001/constructor-result.json',C);ledger=con['ledger_rows'];assert len(ledger)==len({r['target_id']for r in ledger})==64 and all(r['disposition']=='assigned'for r in ledger)
ak={(x,r['y'],o)for t in ledger for r in t['native_rows']for a,z,o in r['runs']for x in range(a,z)};assert ak==original and sum(t['native_cells']for t in ledger)==31206
scope=js(P+'/source-stage-001/source-scope-assessment.json',C);owners={r['pixelIndex']:r for r in scope['target_checks']};counts=collections.Counter(o for x,y,o in original);assert all(counts[o]==v['candidate_cells']for o,v in owners.items())and {r['target_id']for r in ledger}=={r['id']for r in owners.values()}
physical=js(P+'/physical-001/whole-target-support.json',C);assert len(physical['results'])==120;issues=sum(len(r['issues'])for r in physical['results']);assert issues==34
foreign=js(P+'/foreign-001/whole-original-negatives.json',C);assert foreign['foreign_contact_cells']==foreign['invalid_relevant_cells']==0
result={'original_cells':31206,'original_intervals':9449,'original_owners':64,'supported_cells':31206,'held_cells':0,'supported_owners':64,'wholly_held_owners':0,'source_members':120,'complete_domestic_source_features':245,'complete_world_original_features':73567,'complete_world_original_products':368,'foreign_contact_cells':0,'invalid_relevant_original_cells':0,'whole_physical_issues':34,'city_aggregate_owners':5,'city_aggregate_cells':sum(counts[o]for o in [24,25,26,28,30]),'exact_original_patch_diagnostic_constructor_keys_equal':True,'owner_counts':[{'owner':o,'id':owners[o]['id'],'original_cells':counts[o],'supported_cells':counts[o],'held_cells':0}for o in sorted(counts)],'inputs':list(inputs.values()),'limits':['Source-relative qualification only. Current accepted owner-zero, selected conservation, emitted consumption and delivery are subsequent gates.','All original 31,206 land keys and 64 subjects remain; no physical companion or other original package is credited.','Whole physical issues, actual228 versus advertised229 source discrepancy, source dates/licenses and open regional reviews remain unchanged.']}
pin=lambda p:(read(p,C),inputs[C,p])[1]
binding=js(P+'/native-authority-001/authority-binding.json',C);quartet={k:pin(P+'/native-authority-001/'+n)for k,n in [('rule_preimage','original-rule-preimage.json'),('source_authority','authority-binding.json'),('ledger','constructor-result.json')]};quartet['native_patch']=binding['native_patch']
assert not O.exists()and all(not p.is_symlink()for p in(O,*O.parents));O.mkdir()
for name,v in [('original-scope-disposition.json',result),('native-authority-quartet.json',quartet)]:
 with(O/name).open('x')as f:json.dump(v,f,separators=(',',':'),ensure_ascii=False);f.write('\n')
print(json.dumps({k:v for k,v in result.items()if k not in ['owner_counts','inputs','limits']}))

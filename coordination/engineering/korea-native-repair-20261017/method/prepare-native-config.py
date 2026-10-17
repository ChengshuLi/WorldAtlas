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

assert read(P+'/method/prepare-native-config.py',C)==pathlib.Path(__file__).read_bytes()
assessment=js(P+'/source-stage-001/source-scope-assessment.json',C);stages=js(P+'/source-stage-001/original-stage-inputs.json',C);byatom={a:o for o in assessment['target_checks']for a in o['source_atoms']};segments=js(P+'/original-scope/original-intervals.json.gz',C);foreign=js(P+'/foreign-001/whole-original-negatives.json',C)
assert foreign['foreign_contact_cells']==foreign['invalid_relevant_cells']==0 and foreign['whole_products']==368 and foreign['whole_features']==73567
physical=js(P+'/physical-001/whole-target-support.json',C);support=exact(physical['results'],'target');assert len(support)==len(stages)==120
coverage=collections.defaultdict(lambda:collections.defaultdict(list))
for y,a,z,ow,ss,kind in segments:assert kind=='land'and len(ow)==1;coverage[ow[0]][y].append([a,z,'mapped_land_support'])
def merged(rs):
 out=[]
 for r in sorted(rs):
  if out and out[-1][1]==r[0]and out[-1][2]==r[2]:out[-1][1]=r[1]
  else:out.append(r.copy())
 assert all(a[1]<=b[0]for a,b in zip(out,out[1:]));return out
rows={o:[{'y':y,'runs':merged(rs)}for y,rs in sorted(ys.items())]for o,ys in coverage.items()};assert len(rows)==64 and sum(r[1]-r[0]for rs in rows.values()for row in rs for r in row['runs'])==31206
pin=lambda p,c=C:(read(p,c),inputs[c,p])[1]
catp='coordination/engineering/original-geography-source-corpus-20261006/catalogue.json';cat=js(catp);rec=next(r for r in cat['products']if r['key']=='gb:KOR:ADM2');parts=[pin(p['path'],H)for p in rec['parts']]
world=pin('data/world-index.json',H);projectionpath='data/macro-foundation/world-review-projection.json';projection=js(projectionpath);assert projection['current_pins']['location_index_sha256']==world['sha256'];cohort=[];cohortparts=[]
for name in projection['location_parts']:cohort.extend(js('data/'+name));cohortparts.append(inputs[H,'data/'+name])
assert len(cohort)==49625==len({r['id']for r in cohort});expected={r['id']for r in cohort if r.get('owner')=='Republic of Korea'};canonical=[];membership=[]
for p in assessment['membership_parts']:
 fs=js(p['path'],p['commit'])['features'];canonical.extend(f for f in fs if f['properties'].get('reference_owner')=='Republic of Korea');membership.append(inputs[p['commit'],p['path']])
assert {f['id']for f in canonical}==expected and len(canonical)==len(expected)==161
physicalpin=inputs[C,P+'/physical-001/whole-target-support.json'];targets=[];seen=set()
for s in stages:
 o=byatom[s['target']];own=o['pixelIndex'];t={'id':s['target'],'target_id':s['selected']['id'],'pixelIndex':own,'base_geometry':s['selected']['geometry'],'source_family':'gb:KOR:ADM2','source_receipt_sha256':physicalpin['sha256'],'coverage_classes':['mapped_land_support'],'territorial_exclusions':[]}
 if own not in seen:t['coverage_rows']=rows[own];seen.add(own)
 targets.append(t)
assert len(targets)==120 and len(seen)==64
config={'version':1,'selector':{'commit':H,'path':'data/ownership-selection.json'},'preparation_allowance':{'phaseBytes':1073741824,'rssBytes':1610612736},'territorial_exclusion_families':foreign['native_exclusion_families'],'compact_territorial_exclusions':True,'source_evidence':{'version':1,'kind':'source-target-native-evidence-v1','catalogue':inputs[H,catp],'families':[{'source_id':'gb:KOR:ADM2','parts':parts}],'physical_evidence':physicalpin,'physical_input':pin(P+'/source-stage-001/original-stage-inputs.json'),'physical_reproduction':pin('scripts/qualify-source-cohort.py',H),'source_membership':{'index':world,'lineage':pin('data/semantic-report.json',H),'parts':membership,'cohort_inventory':{'index':inputs[H,projectionpath],'parts':cohortparts}},'targets':targets}}
assert not O.exists()and all(not p.is_symlink()for p in(O,*O.parents));O.mkdir()
with(O/'source-evidence.json').open('x')as f:json.dump(config,f,separators=(',',':'),ensure_ascii=False);f.write('\n')
print(json.dumps({'original_cells':31206,'targets':64,'whole_source_members':120,'complete_country_cohort':161,'foreign_families':config['territorial_exclusion_families']}))

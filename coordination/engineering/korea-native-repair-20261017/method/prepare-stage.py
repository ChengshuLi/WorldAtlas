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

assert read(P+'/method/prepare-stage.py',C)==pathlib.Path(__file__).read_bytes()
screen=js(P+'/original-scope/screening.json',C);segments=js(P+'/original-scope/original-intervals.json.gz',C)
assert screen['package']['package_id']=='gb-KOR-ADM2--repair-evaluation' and screen['accepted_head']==H and screen['accepted_overlap_cells']==0
assert len(segments)==9449 and sum(z-a for y,a,z,*_ in segments)==31206
owners=exact(screen['owners'],'index');assert len(owners)==64
cat=js('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json');rosterrows=js('coordination/engineering/global-current-cell-work-queue-20261014/source-feature-roster.json.gz',Q);roster=exact(rosterrows,'source_id');lineage=js('coordination/engineering/global-current-cell-work-queue-20261014/lineage.json.gz',Q)
sources={};records=[]
for family,n in [('gb:KOR:ADM1',17),('gb:KOR:ADM2',228)]:
 rec=next(r for r in cat['products']if r['key']==family);chunks=[]
 for p in rec['parts']:
  d=read(p['path']);pin=inputs[H,p['path']];assert pin['bytes']==p['bytes']and pin['sha256']==p['sha256']and len(d)==p['uncompressed_bytes']and sha(d)==p['uncompressed_sha256'];assert sum(map(len,chunks))==p['offset'];chunks.append(d)
 b=b''.join(chunks);assert len(b)==rec['original_bytes']and sha(b)==rec['original_sha256'];product=json.loads(b);assert product['crs']['properties']['name']=='urn:ogc:def:crs:OGC:1.3:CRS84'
 fs={family+':'+f['properties']['shapeID']:f for f in product['features']};assert len(fs)==len(product['features'])==n and set(fs)=={r['source_id']for r in rosterrows if r['source_id'].startswith(family+':')}
 assert all(shape(f['geometry']).is_valid and not shape(f['geometry']).is_empty for f in fs.values());sources.update(fs);records.append(rec)
selection=js('data/ownership-selection.json');bp=selection['selected_geography'];bb=read(bp['path'],bp.get('commit',H));assert len(bb)==bp['bytes']and sha(bb)==bp['sha256'];bank=json.loads(bb)
# The complete bank is scanned read-only; only exact scoped selected records retained.
targets={};parts=[];targetids={o['id']for o in owners.values()};country_targets=[]
for bp in bank['unchanged_files']+bank['overrides']:
 if not bp['path'].startswith('data/geography/part-'):continue
 b=read(bp['path'],bp.get('commit',H));p=inputs[bp.get('commit',H),bp['path']];assert p['bytes']==bp['bytes']and p['sha256']==bp['sha256']
 fs=json.loads(b)['features'];matched=[f for f in fs if f['properties'].get('reference_owner')=='Republic of Korea']
 if matched:parts.append(p);country_targets+=matched
 targets.update({f['id']:f for f in fs if f['id']in targetids})
assert set(targets)==targetids
semantic=js('data/semantic-report.json');constructor=read('scripts/semantic-locations.py').decode();assert "korea_crosswalk.get(f['properties']['metadata']['original_id'],{}).get('admin1_code')==code"in constructor and 'union_all([geoms[i] for i in indices])'in constructor
crosswalk=semantic['korea_membership_crosswalk'];changes=exact(semantic['changes'],'id');stages=[];checks=[]
for index,o in sorted(owners.items()):
 f=targets[o['id']];m=f['properties']['metadata'];atoms=o['source_atoms'];assert shape(f['geometry']).is_valid and f['properties']['parent_id']==o['province_id']and f['properties']['name']==o['name']and f['properties']['reference_owner']=='Republic of Korea'
 if o['id'].startswith('atlas:city:'):
  code=o['id'].split('-')[-1];change=changes[o['id']];assert set(atoms)==set(m['source_member_ids'])==set(change['replaces']);assert len(atoms)=={24:16,25:25,26:10,28:5,30:5}[index]
  assert all(crosswalk[sources[a]['properties']['shapeID']]['admin1_code']==code for a in atoms)
  expected={sid for sid in sources if sid.startswith('gb:KOR:ADM2:')and crosswalk.get(sources[sid]['properties']['shapeID'],{}).get('admin1_code')==code};assert set(atoms)==expected
  scope='Complete named-city source district membership selected by the retained explicit GeoNames crosswalk; original pointsets only, not modern legal jurisdiction.'
 else:
  assert atoms==[o['id']]and m['source_id']=='gb:KOR:ADM2'and m['original_id']==sources[o['id']]['properties']['shapeID']and sources[o['id']]['properties']['shapeName']==o['name'];scope='Whole named original consumed district or county; source-relative restoration only.'
 for sid in atoms:
  assert lineage['reverse'][sid]==roster[sid]['owners']==[index];stages.append({'target':sid,'consumed':sources[sid],'selected':f})
 checks.append({'id':o['id'],'pixelIndex':index,'name':o['name'],'source_atoms':atoms,'metadata':m,'candidate_cells':o['original_cells'],'scope_decision':scope,'city_membership_crosswalk':{a:crosswalk[sources[a]['properties']['shapeID']]for a in atoms}if o['id'].startswith('atlas:city:')else {}})
assert len(stages)==120 and len({s['target']for s in stages})==120
manifest=js(selection['manifest_path']);lat=manifest['native_latitudes'];b=read(lat['path'],lat['commit']);assert sha(b)==lat['decoded_sha256'];latitude=np.frombuffer(b,dtype='<f8');assert len(latitude)==262166
cells=[(x,y,o[0],tuple(s))for y,a,z,o,s,c in segments for x in range(a,z)];assert len(set((x,y)for x,y,*_ in cells))==31206
points=shapely.points([[(x+.5)/262166*360-180,latitude[y]]for x,y,*_ in cells]);actual=[set()for _ in cells];members=[]
for sid,f in sources.items():
 ix=np.flatnonzero(shapely.covers(shape(f['geometry']),points));idx=roster[sid]['source_index']
 for i in ix:actual[i].add(idx)
 members.append({'id':sid,'source_index':idx,'owners':roster[sid]['owners'],'candidate_cells':len(ix)})
mismatch=[{'x':c[0],'y':c[1],'recorded':list(c[3]),'actual':sorted(a)}for c,a in zip(cells,actual)if set(c[3])!=a];assert not mismatch
rows=collections.defaultdict(list)
for y,a,z,o,s,c in segments:assert len(o)==1 and c=='land';rows[y].append([a,z,o[0]])
for y,runs in rows.items():
 merged=[]
 for r in sorted(runs):
  if merged and merged[-1][1]==r[0]and merged[-1][2]==r[2]:merged[-1][1]=r[1]
  else:merged.append(r.copy())
 assert all(a[1]<=b[0]for a,b in zip(merged,merged[1:]));rows[y]=merged
assessment={'version':1,'issue':2383,'baseline_commit':H,'input_commit':C,'original_cells':31206,'original_intervals':9449,'owners':64,'source_members':120,'complete_source_features':245,'target_checks':checks,'complete_sources':records,'all_source_members':members,'source_membership_mismatches':mismatch,'complete_country_targets':len(country_targets),'membership_parts':parts,'inputs':list(inputs.values()),'limits':['Complete consumed simplified original pointsets only; no present legal-jurisdiction, historical affiliation, regional approval or current dry-land certification.','Actual ADM2 product contains228 versus advertised229 features; missing-feature identity is not guessed.','GeoNames CC BY4.0 district membership attribution is distinct from ADM2 CC BY3.0 and ADM1 Public Domain metadata; represented2020/2021 dates are not acquisition dates.','Open regional reviews221/222/220/223 remain; no hierarchy or name changes.','Complete original native census records no foreign family at the exact requested centres; original whole foreign negatives still require separate applicability and actual native predicates.','This preparation is not scientific physical/native qualification.'], 'runtime':{'python':sys.version,'shapely':shapely.__version__,'numpy':np.__version__},'elapsed_seconds':time.monotonic()-start}
products={'original-stage-inputs.json':stages,'native-patch.json':{'rows':[{'y':y,'runs':r}for y,r in sorted(rows.items())]},'source-scope-assessment.json':assessment}
encoded={n:(json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n').encode()for n,v in products.items()};assert not O.exists()and all(not p.is_symlink()for p in(O,*O.parents));O.mkdir()
for n,b in encoded.items():
 with(O/n).open('xb')as f:f.write(b)
print(json.dumps({'complete':True,'cells':31206,'owners':64,'source_members':120,'outputs':{n:{'bytes':len(b),'sha256':sha(b)}for n,b in encoded.items()},'elapsed_seconds':time.monotonic()-start}))

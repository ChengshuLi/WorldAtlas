"""Prepare complete original Argentina source membership, retaining the CABA identity hold.
Usage: python prepare-source-stage.py REPO EXACT_INPUT_COMMIT FRESH_OUTPUT
Only pinned ordinary Git inputs are consumed. The immutable original-scope proof
binds all original intervals; source membership is independently rejoined here.
This custom adapter is required because the stock source qualifier is IDN-specific.
The unchanged stock physical and native entry points remain the delivery authority.
"""
import collections,gzip,hashlib,json,os,pathlib,subprocess,sys,time
import shapely
from shapely.geometry import shape
assert len(sys.argv)==4 and __debug__
W=pathlib.Path(sys.argv[1]).absolute();C=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute()
H='d4968ddc37aa3aa6105e9610c9e6fadbb368ba14';Q='b3914bbdd2b6fdcb5e4ae7c860494425fa2c27ea';P='coordination/engineering/argentina-repair-delivery-20261017';A='coordination/engineering/original-geography-source-corpus-20261006/catalogue.json';R='coordination/engineering/global-current-cell-work-queue-20261014/source-feature-roster.json.gz'
assert len(C)==40 and all(c in '0123456789abcdef'for c in C)
assert W.is_dir() and O.parent.is_dir() and not O.exists() and all(not p.is_symlink()for root in(W,O)for p in(root,*root.parents))
start=time.monotonic();inputs={};total=0
# Finite admission for this actual small source phase, not a scientific byte ceiling.
DEADLINE_SECONDS=300
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
method=read(P+'/probes/prepare-source-stage.py',C);assert sha(method)==sha(pathlib.Path(__file__).read_bytes())
screen=js(P+'/original-scope/screened-package.json',C);scope=js(P+'/original-scope/scope-screen.json',C);rows=js(P+'/original-scope/original-intervals.json.gz',C);baseline=js(P+'/original-scope/allocation-baseline-check.json',C);obligations=js(P+'/original-scope/existing-obligations.json',C)
assert screen['package']['package_id']=='gb-ARG-ADM2--repair-evaluation'and scope['original_transport_exact_immutable_block_equality']
assert len(rows)==10702 and sum(z-a for y,a,z,*_ in rows)==28846
owners=exact(screen['owners'],'index');assert len(owners)==115 and set(owners)==set(scope['package']['owners'])
keys=set();kinds=collections.Counter();byowner=collections.Counter();identity_hold=[];allnative=collections.defaultdict(list);positive=collections.defaultdict(list)
for y,a,z,ow,sids,kind in rows:
 assert len(ow)==1 and ow[0]in owners and kind in('land','inland-water')and isinstance(y,int)and 0<=a<z<=262166
 for x in range(a,z):assert(y,x,ow[0])not in keys;keys.add((y,x,ow[0]))
 kinds[kind]+=z-a;byowner[ow[0]]+=z-a;allnative[y].append([a,z,ow[0]])
 if ow[0]==7:identity_hold.append({'y':y,'start':a,'end':z,'pixelIndex':ow[0],'physical_class':kind,'source_feature_indices':sids,'reason':'CABA city aggregation includes 15 CABA communes plus Lanús and Avellaneda; original identity and membership contradiction remains open under issue941','issue':'https://github.com/ChengshuLi/WorldAtlas/issues/941'})
 else:positive[y].append([a,z,ow[0]])
assert kinds=={'land':27774,'inland-water':1072}and byowner[7]==32 and len(keys)==28846
assert byowner==collections.Counter({o['index']:o['candidate_cells']for o in owners.values()})
cat=js(A);rec=next(r for r in cat['products']if r['key']=='gb:ARG:ADM2');chunks=[]
for p in rec['parts']:
 d=read(p['path']);pin=inputs[H,p['path']];assert pin['bytes']==p['bytes']and pin['sha256']==p['sha256']and len(d)==p['uncompressed_bytes']and sha(d)==p['uncompressed_sha256'];chunks.append(d)
b=b''.join(chunks);assert len(b)==5502879==rec['original_bytes']and sha(b)==rec['original_sha256']=='cedee8710e49d9017327fc1d4b2dc536e95a82317dc94c3bac8d9404af6bf771';product=json.loads(b);assert product['crs']['properties']['name']=='urn:ogc:def:crs:OGC:1.3:CRS84'
sources={'gb:ARG:ADM2:'+f['properties']['shapeID']:f for f in product['features']};assert len(product['features'])==len(sources)==rec['feature_count']==525
roster_rows=js(R,Q);roster=exact([r for r in roster_rows if r['source_id'].startswith('gb:ARG:ADM2:')],'source_id');assert set(sources)==set(roster)
source_inventory=[]
for sid,f in sources.items():
 g=shape(f['geometry']);assert not g.is_empty and g.is_valid,(sid,shapely.is_valid_reason(g));source_inventory.append({'source_id':sid,'source_name':f['properties']['shapeName'],'geometry_sha256':sha(json.dumps(f['geometry'],separators=(',',':')).encode()),'source_index':roster[sid]['source_index'],'owners':roster[sid]['owners']})
metadata=js('data/administrative-sources.json')['gb:ARG:ADM2'];assert metadata['sha256']==rec['original_sha256']and metadata['boundaryYearRepresented']=='2020'and metadata['boundaryLicense']=='Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)'
selection=js('data/ownership-selection.json');bp=selection['selected_geography'];body=read(bp['path'],bp.get('commit',H));assert len(body)==bp['bytes']and sha(body)==bp['sha256'];bank=json.loads(body);features={}
for commit,path in sorted({(o['target_pin']['commit'],o['target_pin']['path'])for o in owners.values()}):
 pin=next(p for p in bank['unchanged_files']+bank['overrides']if p['commit']==commit and p['path']==path);d=read(path,commit);actual=inputs[commit,path];assert actual['bytes']==pin['bytes']and actual['sha256']==pin['sha256']
 if pin.get('encoding')=='gzip':assert len(d)==pin['decoded_bytes']and sha(d)==pin['decoded_sha256']
 features.update(exact(json.loads(d)['features'],'id'))
semantic=js('data/semantic-report.json');read('scripts/semantic-locations.py');read('scripts/consolidate-fragments.py');hierarchy=js('data/hierarchy.json')
stages=[];mappings=[];checks=[]
for index,o in sorted(owners.items()):
 f=features[o['id']];assert f['properties']==o['target_properties'];m=f['properties']['metadata'];atoms=o['source_atoms'];assert shape(f['geometry']).is_valid
 if index==7:
  assert f['id']=='atlas:city:ARG-5493'and len(atoms)==17 and set(atoms)==set(m['source_member_ids'])and m['location_basis']=='Source city territory: Federal District'
  expected={'Comuna '+str(n)for n in range(1,16)}|{'Lanús','Avellaneda'}
  assert {sources[a]['properties']['shapeName']for a in atoms}==expected
  change=next(c for c in semantic['changes']if c['id']==f['id']);assert set(change['replaces'])==set(atoms)and set(change['source_names'])==expected
  intent='Forensic whole-original physical support only; CABA 17-member city identity is held because 15 communes plus Lanús and Avellaneda do not establish the intended city scope'
 else:
  assert atoms==[f['id']]and m['source_id']=='gb:ARG:ADM2'and m['original_id']==sources[f['id']]['properties']['shapeID']and sources[f['id']]['properties']['shapeName']==o['name'];intent='Whole named original consumed department or partido; source-relative restoration only'
 for sid in atoms:
  assert o['source_reverse_owners'][sid]==roster[sid]['owners']==[index]
  stages.append({'target':sid,'consumed':sources[sid],'selected':f});mappings.append({'source_id':sid,'target_id':f['id'],'pixelIndex':index,'positive_request_eligible':index!=7})
 checks.append({'id':f['id'],'pixelIndex':index,'name':o['name'],'source_atoms':atoms,'candidate_cells':byowner[index],'scope_decision':intent,'metadata':m})
assert len(stages)==len({s['target']for s in stages})==131 and sum(m['positive_request_eligible']for m in mappings)==114

def patch(ys):
 out=[]
 for y,runs in sorted(ys.items()):
  rr=[]
  for r in sorted(runs):
   if rr and rr[-1][1]==r[0]and rr[-1][2]==r[2]:rr[-1][1]=r[1]
   else:rr.append(r.copy())
  assert all(a[1]<=b[0]for a,b in zip(rr,rr[1:]));out.append({'y':y,'runs':rr})
 return {'rows':out}
limits=['Complete consumed product is geoBoundaries-ARG-ADM2_simplified.geojson, distinct from the unsimplified upstream product.','The complete consumed source has 525 actual features versus 526 advertised; source completeness and legal-boundary authority remain unresolved.','2020 is the recorded source-represented year; source update 2023-01-19 and build 2023-12-12 are distinct dates, and product-specific retrieval time remains unknown.','Exact CC BY 3.0 IGO product metadata and separate provider attribution/modification requirements are retained, not an independent warranty of upstream permissions.','No present legal jurisdiction, current dry-land, historic boundary or historical affiliation approval.','Whole original membership and exact current lineage alone do not resolve source fitness or authorize a repair.','All complete foreign competitors, prior seven-component source-fitness applicability and independent review remain required.','CABA identity contradiction is an explicit 32-key hold; all 17 originals are retained for forensic physical evidence. Parent, Tierra del Fuego, source-vintage and reproduction obligations stay open.','This stage retains 131 whole source members for physical evidence; preliminary identity-only positive scope is 114 owners and 28,814 cells. It is not final requested or qualified authority.']
assessment={'version':1,'issue':2373,'baseline_commit':H,'input_commit':C,'original_queue_commit':Q,'original_cells':len(keys),'original_intervals':len(rows),'original_owners':len(owners),'physical_classes':dict(kinds),'whole_source_feature_count':len(sources),'physical_source_members':len(stages),'positive_source_members':114,'positive_owners':114,'positive_requested_cells':28814,'identity_held_cells':32,'source_product':rec,'recorded_metadata':metadata,'source_inventory':source_inventory,'target_checks':checks,'existing_obligation_issues':[r['number']for r in obligations],'inputs':list(inputs.values()),'runtime':{'python':sys.version,'shapely':shapely.__version__,'geos':shapely.geos_version_string},'limits':limits,'elapsed_seconds':time.monotonic()-start}

products={'original-stage-inputs.json':stages,'source-target-membership.json':mappings,'original-native-patch.json':patch(allnative),'positive-requested-native-patch.json':patch(positive),'identity-holds.json':identity_hold,'source-scope-assessment.json':assessment}
encoded={n:(json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n').encode()for n,v in products.items()};assert time.monotonic()-start<DEADLINE_SECONDS
assert O.parent.is_dir()and not O.exists()and all(not p.is_symlink()for p in(O,*O.parents));O.mkdir()
for n,b in encoded.items():
 with(O/n).open('xb')as f:f.write(b)
receipt={'complete':True,'source_native_authority':False,'input_encoded_decoded_bytes':total,'outputs':{n:{'bytes':len(b),'sha256':sha(b)}for n,b in encoded.items()},'operating_controls':{'immutable_exact_bytes':True,'complete_gzip_crc':True,'deadline_seconds':DEADLINE_SECONDS,'arbitrary_byte_ceiling':False},'elapsed_seconds':time.monotonic()-start}
with(O/'preparation.json').open('x')as f:f.write(json.dumps(receipt,separators=(',',':'))+'\n')
print(json.dumps(receipt))

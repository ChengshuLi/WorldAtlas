"""Prepare explicit Argentina original-negative native inputs after source-only holds.
Usage: python prepare-native-config.py REPO EXACT_INPUT_COMMIT FRESH_OUTPUT
The stock source-evidence command resolves compact references against all whole
original negatives. This adapter does not qualify source/native support.
"""
import collections,gzip,hashlib,json,os,pathlib,subprocess,sys,time
assert len(sys.argv)==4 and __debug__
W=pathlib.Path(sys.argv[1]).absolute();C=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();H='d4968ddc37aa3aa6105e9610c9e6fadbb368ba14';P='coordination/engineering/argentina-repair-delivery-20261017'
assert len(C)==40 and all(c in '0123456789abcdef'for c in C)and O.parent.is_dir()and not O.exists()and all(not p.is_symlink()for root in(W,O)for p in(root,*root.parents))
sha=lambda b:hashlib.sha256(b).hexdigest();inputs={};started=time.monotonic();total=0
env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_TERMINAL_PROMPT':'0'}
def git(*args):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),*args],env=env,timeout=30)
def read(p,c=C):
 global total
 assert not p.startswith('/')and all(x not in('','.','..')for x in p.split('/'))and time.monotonic()-started<300
 row=git('ls-tree','-z',c,'--',p).rstrip(b'\0');meta,name=row.split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644'and kind=='blob'and name.decode()==p
 size=int(git('cat-file','-s',oid));assert 0<size;b=git('cat-file','blob',oid);assert len(b)==size and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+b).hexdigest()==oid
 pin={'path':p,'commit':c,'mode':mode,'git_blob_oid':oid,'bytes':size,'sha256':sha(b)}
 if p.endswith('.gz'):
  import io
  with gzip.GzipFile(fileobj=io.BytesIO(b))as f:d=f.read()
  pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
 if(c,p)not in inputs:total+=size+pin.get('decoded_bytes',0)
 inputs[c,p]=pin;return b
js=lambda p,c=C:json.loads(read(p,c))
def pin(p,c=C):read(p,c);return inputs[c,p]
assert sha(read(P+'/probes/prepare-native-config.py'))==sha(pathlib.Path(__file__).read_bytes())
stages=js(P+'/source-stage-001/original-stage-inputs.json');mapping=js(P+'/source-stage-001/source-target-membership.json');byid={m['source_id']:m for m in mapping};assert len(byid)==len(mapping)==131
rows=js(P+'/original-scope/original-intervals.json.gz');holds=js(P+'/source-review/complete-scope-002/held-original-keys.json');assert len(holds)==6149
held={(r['y'],r['x'],r['pixelIndex']):r for r in holds};assert len(held)==6149
preheld={k for k,v in held.items()if any(reason!='foreign-whole-original-contact'for reason in v['reasons'])};foreign=set(held)-preheld;assert len(preheld)==5125 and len(foreign)==1024
wanted=collections.defaultdict(lambda:collections.defaultdict(list));patch_rows=collections.defaultdict(list);requested=set();retained=[]
for y,a,z,owners,sids,kind in rows:
 own=owners[0];classification='mapped_land_support'if kind=='land'else'mapped_inland_water_support';segments=[];begin=None
 for x in range(a,z):
  if(y,x,own)in preheld:
   if begin is not None:segments.append([begin,x]);begin=None
  else:
   requested.add((y,x,own))
   if begin is None:begin=x
 if begin is not None:segments.append([begin,z])
 for a,z in segments:wanted[own][y].append([a,z,classification]);patch_rows[y].append([a,z,own]);retained.append([y,a,z,owners,sids,kind])
assert len(requested)==23721 and len(wanted)==111 and foreign<=requested and not requested&preheld

def merge(runs):
 out=[]
 for r in sorted(runs):
  if out and out[-1][1]==r[0]and out[-1][2]==r[2]:out[-1][1]=r[1]
  else:out.append(r.copy())
 assert all(a[1]<=b[0]for a,b in zip(out,out[1:]));return out
coverage={own:[{'y':y,'runs':merge(rs)}for y,rs in sorted(ys.items())]for own,ys in wanted.items()};patch={'rows':[{'y':y,'runs':merge(rs)}for y,rs in sorted(patch_rows.items())]}
physical_path=P+'/physical-001/whole-target-support.json';physical=js(physical_path);physical_pin=inputs[C,physical_path];support={r['target']:r for r in physical['results']};assert len(support)==len(stages)==131
catp='coordination/engineering/original-geography-source-corpus-20261006/catalogue.json';cat=js(catp,H);rec=next(r for r in cat['products']if r['key']=='gb:ARG:ADM2');sourceparts=[pin(p['path'],H)for p in rec['parts']]
world=pin('data/world-index.json',H);projection_path='data/macro-foundation/world-review-projection.json';projection=js(projection_path,H);assert projection['current_pins']['location_index_sha256']==world['sha256'];cohort_parts=[];cohort_rows=[]
for name in projection['location_parts']:cohort_rows.extend(js('data/'+name,H));cohort_parts.append(inputs[H,'data/'+name])
assert len(cohort_rows)==projection['locations']==49625 and len({r['id']for r in cohort_rows})==49625
expected={r['id']for r in cohort_rows if r.get('owner')=='Argentina'};canonical=[];membership_parts=[]
for n in [0,28]:
 name=f'data/geography/part-{n}.json';canonical.extend(f for f in js(name,H)['features']if f['properties']['reference_owner']=='Argentina');membership_parts.append(inputs[H,name])
assert len(canonical)==len(expected)==509 and {f['id']for f in canonical}==expected
seen=set();targets=[]
for stage in stages:
 m=byid[stage['target']];own=m['pixelIndex']
 if own not in wanted:assert own in {7,8100,8196,8259};continue
 t={'id':stage['target'],'target_id':m['target_id'],'pixelIndex':own,'base_geometry':stage['selected']['geometry'],'source_family':'gb:ARG:ADM2','source_receipt_sha256':physical_pin['sha256'],'coverage_classes':[k for k in ['mapped_land_support','mapped_inland_water_support']if support[stage['target']]['support'][k].get('type')in['Polygon','MultiPolygon']and support[stage['target']]['support'][k].get('coordinates')],'territorial_exclusions':[]}
 assert t['coverage_classes']
 if own not in seen:t['coverage_rows']=coverage[own];seen.add(own)
 targets.append(t)
assert len(targets)==111 and seen==set(wanted)
config={'version':1,'selector':{'commit':H,'path':'data/ownership-selection.json'},'territorial_exclusion_families':['gb:BRA:ADM1','gb:CHL:ADM1','gb:CHL:ADM2','gb:PRY:ADM1'],'compact_territorial_exclusions':True,'source_evidence':{'version':1,'kind':'source-target-native-evidence-v1','catalogue':inputs[H,catp],'families':[{'source_id':'gb:ARG:ADM2','parts':sourceparts}],'physical_evidence':physical_pin,'physical_input':pin(P+'/source-stage-001/original-stage-inputs.json'),'physical_reproduction':pin('scripts/qualify-source-cohort.py',H),'source_membership':{'index':world,'lineage':pin('data/semantic-report.json',H),'parts':membership_parts,'cohort_inventory':{'index':inputs[H,projection_path],'parts':cohort_parts}},'targets':targets}}
assessment={'kind':'Argentina-native-request-source-hold-adaptation','baseline':H,'input_commit':C,'original_keys':28846,'identity_and_existing_fitness_held_keys':5125,'native_requested_keys':23721,'foreign_keys_retained_for_actual_native_veto':1024,'source_applicability_ceiling':22697,'native_requested_owners':111,'whole_physical_source_members':131,'positive_native_source_members':111,'complete_Argentina_reference_owner_cohort':509,'complete_inventory_parts':len(cohort_parts),'complete_world_owner_ids':len(cohort_rows),'request_physical_classes':dict(collections.Counter({k:sum(z-a for y,a,z,ow,si,c in retained if c==k)for k in ['land','inland-water']})),'inputs':list(inputs.values()),'limits':['Original source/physical production is not repeated. No native or selected authority is asserted.','All1024 foreign-contact keys not already held for intended-scope reasons remain in the diagnostic request to exercise actual complete original-negative predicates. The one foreign/Tierra-del-Fuego overlap remains in its whole-owner hold.','CABA32, prior source-fitness4 and Tierra-del-Fuego5089 keys are omitted only from positive requested coverage, never the original denominator or whole physical source evidence.','Complete domestic ARG originals and four complete foreign families remain source-unique negative predicates. No selected-owner filter or geometry substitution is used.','Compact negative references use accepted #2344 at this baseline and require exact full-original native expansion.']}
products={'source-evidence-config.json':config,'native-requested-patch.json':patch,'request-scope-accounting.json':assessment};encoded={n:(json.dumps(v,separators=(',',':'),ensure_ascii=False)+'\n').encode()for n,v in products.items()}
assert not O.exists()and all(not p.is_symlink()for p in(O,*O.parents));O.mkdir()
for n,b in encoded.items():
 with(O/n).open('xb')as f:f.write(b)
r={'complete':True,'inputs_encoded_decoded_bytes':total,'outputs':{n:{'bytes':len(b),'sha256':sha(b)}for n,b in encoded.items()},'seconds':time.monotonic()-started}
with(O/'preparation.json').open('x')as f:f.write(json.dumps(r,separators=(',',':'))+'\n')
print(json.dumps(r))

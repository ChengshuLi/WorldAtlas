"""Recover Germany's complete original source stages from immutable accepted inputs.
No source/physical/native qualification or selected delivery is performed here.
Usage: python prepare-original.py REPO EXACT_METHOD_COMMIT FRESH_OUTPUT
"""
import collections,gzip,hashlib,json,os,pathlib,subprocess,sys,time
import shapely
from shapely.geometry import shape
W=pathlib.Path(sys.argv[1]).absolute(); C=sys.argv[2]; O=pathlib.Path(sys.argv[3]).absolute()
H='282d14b4682f738fed6a0e6f3ee0d0e4b775d611'
P='coordination/engineering/germany-original-repair-20261017'
Q='coordination/engineering/global-current-cell-work-queue-20261014'
assert __debug__ and len(sys.argv)==4 and len(C)==40 and all(c in '0123456789abcdef' for c in C)
assert O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for root in (W,O) for p in (root,*root.parents))
env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_TERMINAL_PROMPT':'0','GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1'}
sha=lambda b:hashlib.sha256(b).hexdigest()
inputs={};start=time.monotonic()
def git(*args):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),*args],env=env)
def read(p,c=H):
 assert not p.startswith('/') and all(x not in ('','.','..') for x in p.split('/'))
 row=git('ls-tree','-z',c,'--',p).rstrip(b'\0');meta,name=row.split(b'\t');mode,kind,oid=meta.decode().split()
 assert mode=='100644' and kind=='blob' and name.decode()==p
 n=int(git('cat-file','-s',oid));b=git('cat-file','blob',oid)
 assert len(b)==n and hashlib.sha1(b'blob '+str(n).encode()+b'\0'+b).hexdigest()==oid
 pin={'commit':c,'path':p,'mode':mode,'git_blob_oid':oid,'bytes':n,'sha256':sha(b)}
 if p.endswith('.gz'): d=gzip.decompress(b);pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
 inputs[c,p]=pin
 return b
def js(p,c=H):return json.loads(read(p,c))
assert read(P+'/probes/prepare-original.py',C)==pathlib.Path(__file__).read_bytes()
queue=js(Q+'/source-package-queue.json');pkg=next(x for x in queue['packages'] if x['package_id']=='gb-DEU-ADM3--repair-evaluation')
assert pkg==js(P+'/original-intervals-001/package.json',C)
rows=[]
for b in pkg['native_blocks']:rows.extend(js(P+'/original-intervals-001/block-%03d.json.gz'%b,C))
assert len(rows)==pkg['interval_segments']==7499 and sum(z-a for y,a,z,*_ in rows)==pkg['native_cells']==27555
lineage=js(Q+'/lineage.json.gz');ownerRows={o['index']:o for o in lineage['locations']}
owners={i:ownerRows[i] for i in pkg['owners']};assert len(owners)==82
roster=js(Q+'/source-feature-roster.json.gz');byid={r['source_id']:r for r in roster};byindex={r['source_index']:r for r in roster}
assert len(byid)==len(byindex)==len(roster)==73567
keys=set();counts=collections.Counter();classes=collections.Counter();wanted=collections.defaultdict(list)
for y,a,z,oo,ss,kind in rows:
 assert len(oo)==1 and oo[0] in owners and kind in ('land','inland-water') and 0<=a<z<=262166
 assert all(i in byindex for i in ss)
 for x in range(a,z):assert(y,x) not in keys;keys.add((y,x))
 counts[oo[0]]+=z-a;classes[kind]+=z-a;wanted[y].append([a,z,oo[0]])
assert len(keys)==27555 and set(counts)==set(owners) and classes=={'land':27043,'inland-water':512}
catalogue=js('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json')
metadata=js('data/administrative-sources.json');products={};inventory=[]
for family,count,year,license in [(f'gb:DEU:ADM{n}',count,'2021','Data license Germany - Attribution - Version 2.0') for n,count in [(1,16),(2,38),(3,428)]]:
 rec=next(x for x in catalogue['products'] if x['key']==family);parts=[];offset=0
 for p in rec['parts']:
  assert p['ordinal']==len(parts) and p['offset']==offset
  d=read(p['path']);pin=inputs[H,p['path']]
  assert pin['bytes']==p['bytes'] and pin['sha256']==p['sha256'] and len(d)==p['uncompressed_bytes'] and sha(d)==p['uncompressed_sha256']
  parts.append(d);offset+=len(d)
 b=b''.join(parts);assert len(b)==rec['original_bytes'] and sha(b)==rec['original_sha256']
 fc=json.loads(b);assert fc['type']=='FeatureCollection' and fc['crs']['properties']['name']=='urn:ogc:def:crs:OGC:1.3:CRS84'
 fs={family+':'+f['properties']['shapeID']:f for f in fc['features']}
 assert len(fs)==len(fc['features'])==rec['feature_count']==rec['advertised_feature_count']==count
 assert set(fs)=={r['source_id'] for r in roster if r['source_id'].startswith(family+':')}
 assert metadata[family]['sha256']==rec['original_sha256'] and metadata[family]['boundaryYearRepresented']==year and metadata[family]['boundaryLicense']==license
 for sid,f in fs.items():
  g=shape(f['geometry']);inventory.append({'source_id':sid,'source_index':byid[sid]['source_index'],'source_name':f['properties']['shapeName'],'owners':byid[sid]['owners'],'geometry_valid':bool(g.is_valid),'geometry_empty':bool(g.is_empty),'validity':shapely.is_valid_reason(g),'whole_geometry_sha256':sha((json.dumps(f['geometry'],separators=(',',':'))+'\n').encode())})
 products[family]=(rec,fs)
selection=js('data/ownership-selection.json');bp=selection['selected_geography'];b=read(bp['path']);assert len(b)==bp['bytes'] and sha(b)==bp['sha256'];bank=json.loads(b)
world=js('data/world-index.json');features={};whole_cohort=[];parts=['data/geography/part-6.json','data/geography/part-28.json','data/geography/part-29.json']
for name in parts:
 assert name[5:] in world['parts'];ordinary=[x for x in bank['unchanged_files'] if x['path']==name];override=[x for x in bank['overrides'] if x['logical_path']==name]
 assert len(ordinary)+len(override)==1
 if ordinary:
  pin=ordinary[0];b=read(name);assert len(b)==pin['bytes'] and sha(b)==pin['sha256'] and inputs[H,name]['git_blob_oid']==pin['git_blob_oid']
 else:
  pin=override[0];assert pin['encoding']=='gzip';b=read(pin['path']);actual=inputs[H,pin['path']]
  assert all(actual[k]==pin[k] for k in ['bytes','sha256','git_blob_oid','decoded_bytes','decoded_sha256'])
  original={f['id']:f for f in js(name)['features']};selected=json.loads(b)['features']
  for f in selected:
   if f.get('properties',{}).get('reference_owner')=='Germany':assert f==original[f['id']] and f['id'] not in bank['changed_ids']
 fs=json.loads(b)['features'];assert not(set(features)&{f['id'] for f in fs});features.update({f['id']:f for f in fs})
 whole_cohort.extend(f['id'] for f in fs if f.get('properties',{}).get('reference_owner')=='Germany')
assert len(whole_cohort)==len(set(whole_cohort))==409
semantic=js('data/semantic-report.json');changes=collections.defaultdict(list)
for row in semantic['changes']:changes[row['id']].append(row)
for p in ['scripts/administrative.py','scripts/prepare.mjs','scripts/semantic-locations.py','scripts/consolidate-fragments.py']:read(p)
stages=[];mapping=[];decisions=[];all_atoms=set()
for owner,o in sorted(owners.items()):
 target=o['id'];f=features[target];m=f['properties']['metadata'];atoms=o['source_atoms']
 assert target not in bank['changed_ids'] and atoms and len(set(atoms))==len(atoms)
 assert f['properties']['reference_owner']=='Germany' and f['properties']['parent_id']==o['province_id'] and f['properties']['name']==o['name']
 if len(atoms)==1:
  assert atoms==[target] and m['source_id']=='gb:DEU:ADM3' and m['original_id']==target.split(':')[-1]
  assert not m.get('source_member_ids') and not m.get('replaces') and target not in changes
 else:
  assert len(atoms)==2 and set(m['source_member_ids'])==set(atoms)
  assert len(changes[target])==1;change=changes[target][0]
  assert set(change['replaces'])==set(atoms) and change['source']==m['source_url'] and change['basis']==m['location_basis']
  for atom in atoms:assert sum(atom in c.get('replaces',[]) for c in semantic['changes'])==1
 for sid in atoms:
  assert sid not in all_atoms;all_atoms.add(sid);source=products['gb:DEU:ADM3'][1][sid]
  assert byid[sid]['owners']==[owner] and source['properties']['shapeName']==o['name']
  stages.append({'target':sid,'consumed':source,'selected':f})
  mapping.append({'source_id':sid,'target_id':target,'pixelIndex':owner})
 decisions.append({'subject_id':target,'pixelIndex':owner,'original_cells':counts[owner],'name':o['name'],'metadata':m,'source_atoms':atoms,'intent':'Restore only supported original native keys to this exact existing owner. Preserve every original source atom and whole physical member; complete foreign negatives and source water roles remain mandatory. No present sovereignty claim.'})
assert len(stages)==len(mapping)==len(all_atoms)==100 and len(decisions)==82
patch=[]
for y,rr in sorted(wanted.items()):
 merged=[]
 for r in sorted(rr):
  if merged and merged[-1][1]==r[0] and merged[-1][2]==r[2]:merged[-1][1]=r[1]
  else:merged.append(r.copy())
 assert all(a[1]<=b[0] for a,b in zip(merged,merged[1:]));patch.append({'y':y,'runs':merged})
sidepin=selection['additive_release'];b=read(sidepin['path']);assert len(b)==sidepin['bytes'] and sha(b)==sidepin['sha256'];side=json.loads(b)
pp=side['logical_asset_map']['patch'];b=read(pp['path']);assert len(b)==pp['bytes'] and sha(b)==pp['sha256'];accepted=json.loads(b);overlaps=[]
assert sum(z-a for row in accepted['rows'] for a,z,own in row['runs'])==6028236
for row in accepted['rows']:
 for a,z,own in row['runs']:
  for aa,zz,oo in wanted.get(row['y'],[]):
   if max(a,aa)<min(z,zz):overlaps.append([row['y'],max(a,aa),min(z,zz),oo,own])
assert not overlaps
assessment={'issue':2410,'baseline_commit':H,'input_commit':C,'original_frozen_selection':queue['current_commit'],'original_cells':27555,'original_intervals':7499,'original_subjects':82,'original_land_cells':27043,'original_inland_water_cells':512,'whole_primary_features':428,'whole_context_features':54,'physical_source_members':100,'complete_Germany_canonical_cohort':whole_cohort,'accepted_native_overlap_cells':0,'source_inventory':inventory,'target_decisions':decisions,'complete_product_metadata':{k:metadata[k] for k in products},'source_products':[x[0] for x in products.values()],'inputs':list(inputs.values()),'elapsed_seconds':time.monotonic()-start,'limits':['Exact BKG/geoBoundaries historical licensing and 2021 source vintage are retained; they do not establish present legal or physical truth.','428 primary records have 401 unique names: original GF2 water extensions and GF4 land must remain distinct source shapes. No name-only identity or role inference is used.','All 82 existing owners and 100 source atoms remain explicit. Hamburg and multipart owners retain exact accepted semantic joins; no synthetic source union is substituted.','Whole physical/native qualification, full foreign negatives and native-base zero-owner checks remain pending.','Complete original water and land scope is unchanged. Separate regional acceptance and other package categories remain separate.']}
out={'original-intervals.json.gz':gzip.compress((json.dumps(rows,separators=(',',':'))+'\n').encode(),mtime=0),'original-stage-inputs.json':stages,'source-target-membership.json':mapping,'original-native-patch.json':{'rows':patch},'source-scope-assessment.json':assessment}
encoded={n:(v if isinstance(v,bytes) else (json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n').encode()) for n,v in out.items()}
assert not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
for n,b in encoded.items():
 with (O/n).open('xb') as f:f.write(b)
receipt={'complete':True,'method_commit':C,'outputs':{n:{'bytes':len(b),'sha256':sha(b)} for n,b in encoded.items()},'seconds':time.monotonic()-start}
with(O/'preparation.json').open('x')as f:json.dump(receipt,f,separators=(',',':'));f.write('\n')
print(json.dumps(receipt))

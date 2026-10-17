"""Recover South Africa's complete original source stages from immutable accepted inputs.
No source/physical/native qualification or selected delivery is performed here.
Usage: python prepare-original.py REPO EXACT_METHOD_COMMIT FRESH_OUTPUT
"""
import collections,gzip,hashlib,json,os,pathlib,subprocess,sys,time
import shapely
from shapely.geometry import shape
W=pathlib.Path(sys.argv[1]).absolute(); C=sys.argv[2]; O=pathlib.Path(sys.argv[3]).absolute()
H='282d14b4682f738fed6a0e6f3ee0d0e4b775d611'
P='coordination/engineering/south-africa-original-repair-20261017'
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
queue=js(Q+'/source-package-queue.json');pkg=next(x for x in queue['packages'] if x['package_id']=='gb-ZAF-ADM3--repair-evaluation')
assert pkg==js(P+'/original-extraction-001/package.json',C)
rows=[]
for b in pkg['native_blocks']:rows.extend(js(P+'/original-extraction-001/block-%03d.json.gz'%b,C))
assert len(rows)==pkg['interval_segments']==2542 and sum(z-a for y,a,z,*_ in rows)==pkg['native_cells']==4804
lineage=js(Q+'/lineage.json.gz');ownerRows={o['index']:o for o in lineage['locations']}
owners={i:ownerRows[i] for i in pkg['owners']};assert len(owners)==68
roster=js(Q+'/source-feature-roster.json.gz');byid={r['source_id']:r for r in roster};byindex={r['source_index']:r for r in roster}
assert len(byid)==len(byindex)==len(roster)==73567
keys=set();counts=collections.Counter();classes=collections.Counter();wanted=collections.defaultdict(list)
for y,a,z,oo,ss,kind in rows:
 assert len(oo)==1 and oo[0] in owners and kind in ('land','inland-water') and 0<=a<z<=262166
 assert all(i in byindex for i in ss)
 for x in range(a,z):assert(y,x) not in keys;keys.add((y,x))
 counts[oo[0]]+=z-a;classes[kind]+=z-a;wanted[y].append([a,z,oo[0]])
assert len(keys)==4804 and set(counts)==set(owners) and classes=={'land':4804}
catalogue=js('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json')
metadata=js('data/administrative-sources.json');products={};inventory=[]
for family,count,year,license in [
 ('gb:ZAF:ADM1',9,'2020','Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)'),
 ('gb:ZAF:ADM2',52,'2020','Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)'),
 ('gb:ZAF:ADM3',213,'2020','Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)')]:
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
pin=next(x for x in bank['unchanged_files'] if x['path']=='data/geography/part-28.json');b=read(pin['path']);assert len(b)==pin['bytes'] and sha(b)==pin['sha256'] and inputs[H,pin['path']]['git_blob_oid']==pin['git_blob_oid']
features={f['id']:f for f in json.loads(b)['features']};assert len(features)==len(json.loads(b)['features'])
semantic=js('data/semantic-report.json');changed={r['id'] for r in semantic['changes']}
for p in ['scripts/administrative.py','scripts/prepare.mjs','scripts/semantic-locations.py','scripts/consolidate-fragments.py']:read(p)
stages=[];mapping=[];decisions=[]
for owner,o in sorted(owners.items()):
 sid=o['id'];f=features[sid];source=products['gb:ZAF:ADM3'][1][sid];m=f['properties']['metadata']
 assert sid not in bank['changed_ids'] and sid not in changed
 assert o['source_atoms']==[sid] and byid[sid]['owners']==[owner] and m['source_id']=='gb:ZAF:ADM3' and m['original_id']==source['properties']['shapeID'] and m['source_role']=='Local municipality'
 assert source['properties']['shapeName']==o['name']==f['properties']['name']
 assert f['properties']['reference_owner']=='South Africa' and f['properties']['parent_id']==o['province_id']
 assert not m.get('source_member_ids') and not m.get('replaces')
 stages.append({'target':sid,'consumed':source,'selected':f});mapping.append({'source_id':sid,'target_id':sid,'pixelIndex':owner})
 decisions.append({'subject_id':sid,'pixelIndex':owner,'original_cells':counts[owner],'name':o['name'],'metadata':m,'source_name':source['properties']['shapeName'],'intent':'Restore only supported original native keys to the exact direct retained district source identity; retain whole original geometry, all domestic competitors, complete foreign negatives and physical issues. Source-relative identity support, not current legal boundaries or native authority.'})
patch=[]
for y,rr in sorted(wanted.items()):
 merged=[]
 for r in sorted(rr):
  if merged and merged[-1][1]==r[0] and merged[-1][2]==r[2]:merged[-1][1]=r[1]
  else:merged.append(r.copy())
 assert all(a[1]<=b[0] for a,b in zip(merged,merged[1:]));patch.append({'y':y,'runs':merged})
sidepin=selection['additive_release'];b=read(sidepin['path']);assert len(b)==sidepin['bytes'] and sha(b)==sidepin['sha256'];side=json.loads(b)
pp=side['logical_asset_map']['patch'];b=read(pp['path']);assert len(b)==pp['bytes'] and sha(b)==pp['sha256'];accepted=json.loads(b);overlaps=[]
for row in accepted['rows']:
 for a,z,own in row['runs']:
  for aa,zz,oo in wanted.get(row['y'],[]):
   if max(a,aa)<min(z,zz):overlaps.append([row['y'],max(a,aa),min(z,zz),oo,own])
assert not overlaps
assessment={'issue':2416,'baseline_commit':H,'input_commit':C,'original_frozen_selection':queue['current_commit'],'original_cells':4804,'original_intervals':2542,'original_subjects':68,'original_land_cells':4804,'original_inland_water_cells':0,'whole_primary_features':213,'whole_context_features':61,'physical_source_members':68,'accepted_native_overlap_cells':0,'source_inventory':inventory,'target_decisions':decisions,'complete_product_metadata':{k:metadata[k] for k in products},'source_products':[x[0] for x in products.values()],'inputs':list(inputs.values()),'elapsed_seconds':time.monotonic()-start,'limits':['The actual immutable upstream ZAF ADM3 archive retains a historical HDX license screenshot, OCHA ROSEA/Municipal Demarcation Board attribution, represented2020 and WGS84 CRS; it is not present-day legal boundary approval.', 'Current HDX landing was inaccessible in this run. No access restriction was bypassed. Original source ZIP and source metadata are retained under source-review/upstream-provenance-001; their supporting text/image was inspected.', 'All original68 owners have their complete source_atoms; all213 primary and61 domestic context features remain whole. BWA/MOZ contacts and all foreign original families require complete negative screening.', 'Source identity support does not resolve the independent current boundary/label/tier issues955/956. Existing names, parents, IDs and original source bytes remain unchanged.', 'Physical and native qualification, current owner-zero, selected conservation and actual emitted checks remain pending; no accepted map credit.']}
out={'original-intervals.json.gz':gzip.compress((json.dumps(rows,separators=(',',':'))+'\n').encode(),mtime=0),'original-stage-inputs.json':stages,'source-target-membership.json':mapping,'original-native-patch.json':{'rows':patch},'source-scope-assessment.json':assessment}
encoded={n:(v if isinstance(v,bytes) else (json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n').encode()) for n,v in out.items()}
assert not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
for n,b in encoded.items():
 with (O/n).open('xb') as f:f.write(b)
receipt={'complete':True,'method_commit':C,'outputs':{n:{'bytes':len(b),'sha256':sha(b)} for n,b in encoded.items()},'seconds':time.monotonic()-start}
with(O/'preparation.json').open('x')as f:json.dump(receipt,f,separators=(',',':'));f.write('\n')
print(json.dumps(receipt))

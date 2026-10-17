"""Authenticate complete Denmark source/target originals without qualifying repairs.
Usage: python prepare-source-stage.py REPO EXACT_METHOD_COMMIT FRESH_OUTPUT
All whole bodies come from immutable Git; fresh output and exact custody required.
"""
import collections,gzip,hashlib,json,os,pathlib,subprocess,sys,time
import shapely
from shapely.geometry import shape
assert len(sys.argv)==4 and __debug__
W=pathlib.Path(sys.argv[1]).absolute();C=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();H='2223d85bbe8b18585c221cc1329d115e8e774a42';Q='b3914bbdd2b6fdcb5e4ae7c860494425fa2c27ea';P='coordination/engineering/denmark-repair-delivery-20261017';A='coordination/engineering/original-geography-source-corpus-20261006/catalogue.json'
assert len(C)==40 and all(c in'0123456789abcdef'for c in C)and O.parent.is_dir()and not O.exists()and all(not p.is_symlink()for root in(W,O)for p in(root,*root.parents))
sha=lambda b:hashlib.sha256(b).hexdigest();inputs={};total=0;start=time.monotonic();env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_TERMINAL_PROMPT':'0'}
def git(*args):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),*args],env=env,timeout=30)
def read(p,c=H):
 global total
 assert not p.startswith('/')and all(x not in('','.','..')for x in p.split('/'))
 row=git('ls-tree','-z',c,'--',p).rstrip(b'\0');meta,name=row.split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644'and kind=='blob'and name.decode()==p
 n=int(git('cat-file','-s',oid));b=git('cat-file','blob',oid);assert n>0 and len(b)==n and hashlib.sha1(b'blob '+str(n).encode()+b'\0'+b).hexdigest()==oid
 pin={'commit':c,'path':p,'mode':mode,'git_blob_oid':oid,'bytes':n,'sha256':sha(b)}
 if p.endswith('.gz'):d=gzip.decompress(b);pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
 if(c,p)not in inputs:total+=n+pin.get('decoded_bytes',0)
 inputs[c,p]=pin;return b
js=lambda p,c=H:json.loads(read(p,c))
assert read(P+'/probes/prepare-source-stage.py',C)==pathlib.Path(__file__).read_bytes()
screen=js(P+'/original-scope/scope-screen.json',C);rows=js(P+'/original-scope/original-intervals.json.gz',C);checks=js(P+'/original-scope/current-target-pin-checks.json',C);owners={o['index']:o for o in screen['owners']};assert len(owners)==69 and screen['package']['package_id']=='gb-DNK-ADM2--repair-evaluation'and screen['accepted_head']==H and screen['accepted_overlap_cells']==0
assert len(rows)==7471 and sum(z-a for y,a,z,*_ in rows)==27783
keys=set();wanted=collections.defaultdict(list);counts=collections.Counter();roster=js('coordination/engineering/global-current-cell-work-queue-20261014/source-feature-roster.json.gz',Q);idx={r['source_index']:r for r in roster};byid={r['source_id']:r for r in roster};assert len(idx)==len(byid)==len(roster)==73567
for y,a,z,oo,ss,kind in rows:
 assert len(oo)==1 and oo[0]in owners and kind in ('land','inland-water')and 0<=a<z<=262166
 assert all(idx[i]['source_id'].startswith('gb:DNK:')for i in ss)
 for x in range(a,z):assert(y,x)not in keys;keys.add((y,x))
 wanted[y].append([a,z,oo[0]]);counts[oo[0]]+=z-a
assert len(keys)==27783 and set(counts)==set(owners)and all(counts[o]==owners[o]['original_cells']for o in owners)
cat=js(A);metadata=js('data/administrative-sources.json');products={};original_inventory=[]
for family,count in [('gb:DNK:ADM1',5),('gb:DNK:ADM2',98)]:
 rec=next(r for r in cat['products']if r['key']==family);parts=[];offset=0
 for p in rec['parts']:
  assert p['ordinal']==len(parts)and p['offset']==offset;d=read(p['path']);pin=inputs[H,p['path']];assert pin['bytes']==p['bytes']and pin['sha256']==p['sha256']and len(d)==p['uncompressed_bytes']and sha(d)==p['uncompressed_sha256'];parts.append(d);offset+=len(d)
 b=b''.join(parts);assert len(b)==rec['original_bytes']and sha(b)==rec['original_sha256'];fc=json.loads(b);assert fc['type']=='FeatureCollection'and fc['crs']['properties']['name']=='urn:ogc:def:crs:OGC:1.3:CRS84';fs={family+':'+f['properties']['shapeID']:f for f in fc['features']};assert len(fs)==len(fc['features'])==rec['feature_count']==rec['advertised_feature_count']==count and set(fs)=={r['source_id']for r in roster if r['source_id'].startswith(family+':')}
 assert metadata[family]['sha256']==rec['original_sha256']and metadata[family]['boundaryYearRepresented']==('2021'if family.endswith('ADM1')else '2018')and metadata[family]['boundaryLicense']==('Creative Commons Attribution 4.0 International (CC BY 4.0)'if family.endswith('ADM1')else 'Public Domain')
 for sid,f in fs.items():
  g=shape(f['geometry']);original_inventory.append({'source_id':sid,'source_index':byid[sid]['source_index'],'source_name':f['properties']['shapeName'],'owners':byid[sid]['owners'],'geometry_valid':bool(g.is_valid),'geometry_empty':bool(g.is_empty),'validity':shapely.is_valid_reason(g),'whole_geometry_sha256':sha((json.dumps(f['geometry'],separators=(',',':'))+'\n').encode())})
 products[family]=(rec,fs)
selection=js('data/ownership-selection.json');bp=selection['selected_geography'];b=read(bp['path']);assert len(b)==bp['bytes']and sha(b)==bp['sha256'];bank=json.loads(b);pin=next(p for p in bank['unchanged_files']if p['path']=='data/geography/part-6.json');b=read(pin['path'],pin['commit']);assert len(b)==pin['bytes']and sha(b)==pin['sha256'];features={f['id']:f for f in json.loads(b)['features']};current={f['id']:f for f in js('data/geography/part-6.json')['features']};assert len(checks['parts'])==1 and checks['parts'][0]['selected_pin']==pin
read('scripts/administrative.py');read('scripts/prepare.mjs');read('scripts/semantic-locations.py');read('scripts/consolidate-fragments.py');semantic=js('data/semantic-report.json');changed={r['id']for r in semantic['changes']};stages=[];mapping=[];decisions=[]
for owner,o in sorted(owners.items()):
 sid=o['id'];f=features[sid];source=products['gb:DNK:ADM2'][1][sid];m=f['properties']['metadata'];assert f==current[sid]and sid not in bank['changed_ids']and sid not in changed
 assert o['source_atoms']==[sid]and byid[sid]['owners']==[owner]and m['source_id']=='gb:DNK:ADM2'and m['original_id']==source['properties']['shapeID']and m['source_role']=='Municipality'
 assert source['properties']['shapeName']==o['name']==f['properties']['name']and f['properties']['reference_owner']=='Denmark'and f['properties']['parent_id']==o['province_id'];assert not m.get('source_member_ids')and not m.get('replaces')
 stages.append({'target':sid,'consumed':source,'selected':f});mapping.append({'source_id':sid,'target_id':sid,'pixelIndex':owner});decisions.append({'subject_id':sid,'pixelIndex':owner,'original_cells':counts[owner],'name':o['name'],'metadata':m,'source_name':source['properties']['shapeName'],'intent':'Complete exact consumed direct municipality original; no whole-province adoption, aggregation or inferred parent clipping. Source-relative eligibility only; physical/native checks and independent source review remain pending.'})
assert len(stages)==69 and len({s['target']for s in stages})==69
patch=[]
for y,rr in sorted(wanted.items()):
 merged=[]
 for r in sorted(rr):
  if merged and merged[-1][1]==r[0]and merged[-1][2]==r[2]:merged[-1][1]=r[1]
  else:merged.append(r.copy())
 assert all(a[1]<=b[0]for a,b in zip(merged,merged[1:]));patch.append({'y':y,'runs':merged})
assessment={'issue':2391,'baseline_commit':H,'input_commit':C,'original_queue_commit':Q,'original_cells':27783,'original_intervals':7471,'original_subjects':69,'original_land_cells':23874,'original_inland_water_cells':3909,'whole_primary_features':98,'whole_context_features':5,'physical_source_members':69,'source_inventory':original_inventory,'target_decisions':decisions,'complete_product_metadata':{k:metadata[k]for k in products},'source_products':[v[0]for v in products.values()],'inputs':list(inputs.values()),'elapsed_seconds':time.monotonic()-start,'limits':['ADM2 represented2018 and ADM1 represented2021 are product metadata, not inferred observation/retrieval dates.','Consumed simplified primary Public Domain and contextual CC BY 4.0 sources are retained.','Complete original-corpus native census contains no foreign contacts in exact keys; full original foreign bounds still require screening.','Source-relative municipality restoration is not current legal territory, historical geography or physical-fitness approval.','All 103 complete domestic source/context features remain present; original scope includes 3909 inland-water cells.','Separate mapping/physical companions and Nordic333/332 obligations remain open.','This source stage does not qualify native support or selected delivery.']}
out={'original-stage-inputs.json':stages,'source-target-membership.json':mapping,'original-native-patch.json':{'rows':patch},'source-scope-assessment.json':assessment};encoded={n:(json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n').encode()for n,v in out.items()};assert not O.exists()and all(not p.is_symlink()for p in(O,*O.parents));O.mkdir()
for n,b in encoded.items():
 with(O/n).open('xb')as f:f.write(b)
receipt={'complete':True,'input_encoded_decoded_bytes':total,'outputs':{n:{'bytes':len(b),'sha256':sha(b)}for n,b in encoded.items()},'seconds':time.monotonic()-start,'arbitrary_byte_ceiling':False}
with(O/'preparation.json').open('x')as f:json.dump(receipt,f,separators=(',',':'));f.write('\n')
print(json.dumps(receipt))

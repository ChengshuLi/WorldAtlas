"""Authenticate whole original UK source and target intent; exact native-centre screen.
Usage: python prepare-stage.py READ_ONLY_REPO FRESH_OUTPUT
This bounded custom operator uses immutable ordinary Git bodies and exclusive output.
No original geometry is repaired or replaced; unknown source fitness stays unknown.
"""
import collections,gzip,hashlib,json,os,pathlib,subprocess,sys,time
import numpy as np
import shapely
from shapely.geometry import shape
assert len(sys.argv)==3
W,O=map(lambda v:pathlib.Path(v).absolute(),sys.argv[1:]);H='a9f6ccadcc1bdea6185fcaf5eac7ec00f8c4551a';F='79d17bfd955e14f4e74d92a03ee29f213874cf90';P='coordination/engineering/uk-native-repair-20261017';Q='coordination/engineering/global-current-cell-work-queue-20261014/';OLD='research/geography/japan-nine-gap-family-source-fitness-20261007/'
assert W.is_dir() and O.parent.is_dir() and not O.exists()
assert all(not p.is_symlink() for root in (W,O) for p in (root,*root.parents))
started=time.monotonic();inputs={};total=0;MAX_FILE=64*1024*1024;MAX_PHASE=256*1024*1024
sha=lambda b:hashlib.sha256(b).hexdigest()
env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_TERMINAL_PROMPT':'0'}
def read(p,h=H):
 global total
 assert all(x not in ['','..','.'] for x in p.split('/')) and not p.startswith('/')
 row=subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'ls-tree','-z',h,'--',p],env=env).rstrip(b'\0');meta,name=row.split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644' and kind=='blob' and name.decode()==p
 size=int(subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'cat-file','-s',oid],env=env));assert 0<size<=MAX_FILE
 b=subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'cat-file','blob',oid],env=env);assert len(b)==size and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+b).hexdigest()==oid
 pin={'path':p,'commit':h,'mode':mode,'git_blob_oid':oid,'bytes':len(b),'sha256':sha(b)}
 if p.endswith('.gz'):
  import io
  with gzip.GzipFile(fileobj=io.BytesIO(b)) as stream:d=stream.read(MAX_FILE+1)
  assert len(d)<=MAX_FILE;pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
 if (h,p) not in inputs:total+=size+pin.get('decoded_bytes',0)
 assert total<=MAX_PHASE;inputs[(h,p)]=pin;return b
def js(p,h=H):return json.loads(read(p,h))
def exact(rows,key):
 out={}
 for r in rows:assert r[key] not in out;out[r[key]]=r
 assert out;return out
queue=js(Q+'source-package-queue.json');package=next(x for x in queue['packages'] if x['package_id']=='gb-GBR-ADM2--repair-evaluation');assert package['native_cells']==89390 and package['interval_segments']==19349 and len(package['owners'])==91
lineage=js(Q+'lineage.json.gz');allowners=exact(lineage['locations'],'index');owners={i:allowners[i] for i in package['owners']};roster_rows=js(Q+'source-feature-roster.json.gz');roster=exact(roster_rows,'source_id');rindex=exact(roster_rows,'source_index');assert len(roster)==73567
cat=js('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json');sources={};receipts=[]
for family,n in [('gb:GBR:ADM1',4),('gb:GBR:ADM2',216)]:
 record=next(x for x in cat['products'] if x['key']==family);pieces=[]
 for p in record['parts']:
  b=read(p['path']);pin=inputs[(H,p['path'])];assert pin['sha256']==p['sha256'] and pin['bytes']==p['bytes'] and len(b)==p['uncompressed_bytes'] and sha(b)==p['uncompressed_sha256'];pieces.append(b)
 b=b''.join(pieces);assert len(b)==record['original_bytes'] and sha(b)==record['original_sha256'];product=json.loads(b);assert product['crs']['properties']['name']=='urn:ogc:def:crs:OGC:1.3:CRS84';features=product['features'];assert len(features)==n
 ids=[family+':'+f['properties']['shapeID'] for f in features];assert len(set(ids))==n and ids==[r['source_id'] for r in roster_rows if r['source_id'].startswith(family+':')]
 assert all(shape(f['geometry']).is_valid for f in features);sources[family]=dict(zip(ids,features));receipts.append(record)
segments=[]
for block in range(18,22):segments+=js(P+f'/frozen-queue/block-{block:03}.json.gz',F)
assert len(segments)==19349 and sum(z-a for y,a,z,*_ in segments)==89390 and {o[0] for y,a,z,o,s,c in segments}==set(owners)
assert all(len(o)==1 and c in ['land','inland-water'] for y,a,z,o,s,c in segments)
selection=js('data/ownership-selection.json');bp=selection['selected_geography'];bb=read(bp['path'],bp.get('commit',H));assert len(bb)==bp['bytes'] and sha(bb)==bp['sha256'];bank=json.loads(bb);targets={};targetids={o['id'] for o in owners.values()}
for path in ['data/geography/part-9.json','data/geography/part-28.json']:
 pin=next(x for x in bank['unchanged_files']+bank['overrides'] if x['path']==path);body=read(path,pin['commit']);assert len(body)==pin['bytes'] and sha(body)==pin['sha256'];features=exact(json.loads(body)['features'],'id');targets.update({i:f for i,f in features.items() if i in targetids})
assert set(targets)==targetids
manifest=js(selection['manifest_path']);lat=manifest['native_latitudes'];b=read(lat['path'],lat['commit']);assert sha(b)==lat['decoded_sha256'];latitude=np.frombuffer(b,dtype='<f8');assert len(latitude)==262166
cells=[(x,y,o[0],tuple(s)) for y,a,z,o,s,c in segments for x in range(a,z)];points=shapely.points([[(x+.5)/262166*360-180,latitude[y]] for x,y,*_ in cells]);actual=[set() for _ in cells];members=[]
for family,features in sources.items():
 for ident,f in features.items():
  inds=np.flatnonzero(shapely.covers(shape(f['geometry']),points));sid=roster[ident]['source_index']
  for i in inds:actual[i].add(sid)
  members.append({'id':ident,'source_index':sid,'owners':roster[ident]['owners'],'candidate_cells':len(inds)})
mismatches=[{'x':c[0],'y':c[1],'recorded':list(c[3]),'actual':sorted(a)} for c,a in zip(cells,actual) if set(c[3])!=a];assert not mismatches,str(mismatches[:4])
foreign_roster=[r for r in roster_rows if not r['owners'] and not r['source_id'].startswith('gb:GBR:')]
assert not any(any(not rindex[s]['source_id'].startswith('gb:GBR:') for s in c[3]) for c in cells)
# The complete pinned country product is a separate coarse contrary-evidence screen.
country_path='data/retained-geographic-sources/namibia/natural-earth-reference-countries.geojson.gz';cb=read(country_path);registry=js('data/sources.json');assert sha(cb)==registry['hashes']['ne_10m_admin_0_countries'];country=json.loads(cb);country_checks=[];foreign_features=[];foreign_keys=set();invalid_countries=[]
for f in country['features']:
 g=shape(f['geometry']);code=f['properties']['ADM0_A3']
 if not g.is_valid:
  a,b,c,d=g.bounds;xy=shapely.get_coordinates(points);box=(xy[:,0]>=a)&(xy[:,0]<=c)&(xy[:,1]>=b)&(xy[:,1]<=d);invalid_countries.append({'code':code,'bounds':list(g.bounds),'candidate_centres_in_bounds':int(np.count_nonzero(box))});assert not np.any(box),'Invalid country source intersects candidate bounds';continue
 idx=np.flatnonzero(shapely.covers(g,points));n=len(idx)
 if n:country_checks.append({'code':code,'name':f['properties'].get('ADMIN'),'cells':n})
 if n and code!='GBR':foreign_features.append(f);foreign_keys.update(int(i) for i in idx)
# Authenticate the complete original Natural Earth product, including City's missing atom.
nepath='data/regional-review/regional-review-0c300e5f6ecdc793/sources/natural-earth-ca96624/ne_10m_admin_1_states_provinces.geojson.gz'
neb=read(nepath);assert sha(neb)==registry['hashes']['ne_10m_admin_1_states_provinces'];ne=json.loads(neb);assert len(ne['features'])==4596
city=next(f for f in ne['features'] if f['properties']['adm1_code']=='GBR-4809');assert city['properties']['woe_name']=='City of London' and city['properties']['region']=='Greater London' and shape(city['geometry']).is_valid
neUK=[f for f in ne['features'] if f['properties']['adm0_a3']=='GBR'];ne_checks=[]
for f in neUK:
 g=shape(f['geometry']);assert g.is_valid
 ix=np.flatnonzero(shapely.covers(g,points));ne_checks.append({'id':f['properties']['adm1_code'],'name':f['properties']['name'],'candidate_cells':len(ix),'owner_cells':dict(collections.Counter(str(cells[i][2]) for i in ix))})
methods={p:read(p).decode() for p in ['scripts/semantic-locations.py','scripts/geographic-regions.py','scripts/rebuild-framework.py']};assert 'union_all([geoms[i] for i in indices])' in methods['scripts/semantic-locations.py'];semantic=js('data/semantic-report.json');hierarchy=js('data/hierarchy.json');parents=[x for x in hierarchy if x['id'] in {o['province_id'] for o in owners.values()}];decisions=js('data/geographic-decisions/europe.json');metadata=js('data/administrative-sources.json')
stages=[];checks=[]
for index,o in sorted(owners.items()):
 t=targets[o['id']];m=t['properties']['metadata'];atoms=o['source_atoms'];assert t['properties']['parent_id']==o['province_id'] and t['properties']['reference_owner']=='United Kingdom' and t['properties']['name']==o['name'];assert shape(t['geometry']).is_valid
 if index==13:
  assert o['id']=='atlas:city:GBR-Greater London' and len(atoms)==33
  canonical=[a.removeprefix('natural-earth:adm1:') for a in atoms]
  change=next(c for c in semantic['changes'] if c['id']==o['id']);assert set(canonical)==set(m['source_member_ids'])==set(change['replaces'])
  scope='Whole 33-member mixed-source aggregate: 32 geoBoundaries borough atoms plus original Natural Earth City of London; neither a single-family aggregate nor a substitute modern boundary.'
 else:
  assert atoms==[o['id']] and m['source_id']=='gb:GBR:ADM2' and m['reference_year']=='2019' and m['source_role']=='Counties and Unitary Authorities';assert m['original_id']==sources['gb:GBR:ADM2'][o['id']]['properties']['shapeID'];scope='Whole named source county/unitary-authority territory; parent geographic portions do not clip the source.'
 for ident in atoms:
  assert lineage['reverse'][ident]==[index]
  if ident.startswith('natural-earth:'):
   assert index==13 and ident=='natural-earth:adm1:GBR-4809';source=city
  else:
   assert roster[ident]['owners']==[index];source=sources['gb:GBR:ADM2'][ident]
   if index!=13:assert source['properties']['shapeName']==o['name'],(index,source['properties']['shapeName'],o['name'])
  stages.append({'target':ident,'consumed':source,'selected':t})
 checks.append({'id':o['id'],'pixelIndex':index,'name':o['name'],'source_atoms':atoms,'metadata':m,'candidate_cells':sum(z-a for y,a,z,oo,ss,c in segments if oo==[index]),'scope_decision':scope})
assert len(stages)==123 and len({s['target'] for s in stages})==123
london=next(s['selected'] for s in stages if s['target']=='natural-earth:adm1:GBR-4809');londonunion=shapely.union_all([shape(s['consumed']['geometry']) for s in stages if s['selected']['id']==london['id']]);londondiff=shape(london['geometry']).symmetric_difference(londonunion)
# Construction later underwent source simplification/topology; preserve measured difference instead of asserting exact geometry identity.
londoncheck={'declared_members':33,'gb_members':32,'natural_earth_member':city,'complete_ne_features':4596,'complete_ne_decoded_bytes':len(neb),'complete_ne_sha256':sha(neb),'complete_uk_ne_members':len(neUK),'source_union_vs_current_symmetric_difference_degrees2':londondiff.area,'current_contains_city_source':shape(london['geometry']).covers(shape(city['geometry'])),'city_candidate_cells':int(sum(shapely.covers(shape(city['geometry']),points))),'method':'Read explicit accepted semantic replaces and selected source_member_ids; independently join all complete original geometry atoms. No source atom or original repair cell omitted.'}
rows=collections.defaultdict(list)
for y,a,z,o,s,c in segments:rows[y].append([a,z,o[0]])
for y,runs in rows.items():
 merged=[]
 for r in sorted(runs):
  if merged and merged[-1][1]==r[0] and merged[-1][2]==r[2]:merged[-1][1]=r[1]
  else:merged.append(r.copy())
 assert all(a[1]<=b[0] for a,b in zip(merged,merged[1:]));rows[y]=merged
limits=['Source-relative restoration only; no effective/current legal-jurisdiction, historical affiliation or current dry-land certification.','ADM2 represented-year 2019 and ADM1 represented-year 2021 remain distinct from 2023 update/build dates.','Complete original ADM2 Office for National Statistics Open Government Licence v3.0, ADM1 Eurostat CC BY 4.0, and Natural Earth public-domain roles remain distinct.','London is an explicit mixed-source aggregate; current stock positive single-family reconciliation does not itself qualify the whole 33-member target.','Foreign ownerless absence is relative to original 368-product native-centre census; complete Natural Earth country screen is coarse reference evidence, not sovereignty clearance.','Separate 13001-cell / 79-owner physical-interpretation companion excluded from repair credit; complete physical/native and current selected conservation remain subsequent obligations.']
assessment={'version':1,'issue':2343,'baseline_commit':H,'frozen_input_commit':F,'original_cells':89390,'original_segments':19349,'owners':91,'source_members':123,'complete_gb_source_feature_count':220,'source_membership_mismatches':mismatches,'complete_sources':receipts,'all_source_members':members,'target_checks':checks,'parent_records':parents,'retained_location_review':[x for x in decisions.get('location_review',[]) if targetids.intersection(x.get('ids',[]))],'foreign_ownerless_census_features':len(foreign_roster),'foreign_ownerless_candidate_cells':0,'country_product_features':len(country['features']),'country_reference_hits':country_checks,'invalid_country_records':invalid_countries,'foreign_country_reference_cells':len(foreign_keys),'foreign_country_native_cells':[[*cells[i][:3]] for i in sorted(foreign_keys)],'london_construction':londoncheck,'complete_uk_ne_native_hits':ne_checks,'recorded_metadata':{k:v for k,v in metadata.items() if k.startswith('gb:GBR:')},'inputs':list(inputs.values()),'limits':limits,'runtime':{'python':sys.version,'numpy':np.__version__,'shapely':shapely.__version__,'geos':shapely.geos_version_string},'elapsed_seconds':time.monotonic()-started}
products={'original-stage-inputs.json':stages,'native-patch.json':{'rows':[{'y':y,'runs':r} for y,r in sorted(rows.items())]},'source-scope-assessment.json':assessment,'original-package.json':package,'foreign-country-features.geojson':{'type':'FeatureCollection','features':foreign_features}}
encoded={n:(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n').encode() for n,d in products.items()};assert all(len(b)<=MAX_FILE for b in encoded.values()) and total+sum(map(len,encoded.values()))<=MAX_PHASE
assert all(not p.is_symlink() for p in (O,*O.parents)) and O.parent.is_dir() and not O.exists();O.mkdir();out={}
for n,b in encoded.items():
 with (O/n).open('xb') as f:f.write(b)
 out[n]={'bytes':len(b),'sha256':sha(b)}
with (O/'preparation.json').open('x') as f:f.write(json.dumps({'complete':True,'inputs_encoded_decoded_bytes':total,'outputs':out},separators=(',',':'))+'\n')
print(json.dumps({'complete':True,'cells':89390,'intervals':19349,'owners':91,'source_members':123,'foreign_country_reference_cells':len(foreign_keys),'london_cells':640,'city_native_hits':int(londoncheck['city_candidate_cells']),'elapsed_seconds':time.monotonic()-started}))

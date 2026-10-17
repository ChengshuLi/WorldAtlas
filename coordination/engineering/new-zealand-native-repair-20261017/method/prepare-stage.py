"""Authenticate whole original New Zealand source and target intent; exact native-centre screen.
Usage: python prepare-stage.py READ_ONLY_REPO FRESH_OUTPUT
This bounded custom operator uses immutable ordinary Git bodies and exclusive output.
No original geometry is repaired or replaced; unknown source fitness stays unknown.
"""
import collections,gzip,hashlib,json,os,pathlib,subprocess,sys,time
import numpy as np
import shapely
from shapely.geometry import shape
assert len(sys.argv)==3
W,O=map(lambda v:pathlib.Path(v).absolute(),sys.argv[1:]);H='d4968ddc37aa3aa6105e9610c9e6fadbb368ba14';F='9e3c3d8169526c4283699d80dbf7b66fc6cfc044';P='coordination/engineering/new-zealand-native-repair-20261017';Q='coordination/engineering/global-current-cell-work-queue-20261014/';OLD='research/geography/japan-nine-gap-family-source-fitness-20261007/'
assert W.is_dir() and O.parent.is_dir() and not O.exists()
assert all(not p.is_symlink() for root in (W,O) for p in (root,*root.parents))
started=time.monotonic();inputs={};total=0;MAX_FILE=64*1024*1024;MAX_PHASE=256*1024*1024
sha=lambda b:hashlib.sha256(b).hexdigest()
env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_TERMINAL_PROMPT':'0'}
def read(p,h=H):
 global total
 assert time.monotonic()-started<360
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
queue=js(Q+'source-package-queue.json');package=next(x for x in queue['packages'] if x['package_id']=='gb-NZL-ADM2--repair-evaluation');assert package['native_cells']==56626 and package['interval_segments']==17520 and len(package['owners'])==70
lineage=js(Q+'lineage.json.gz');allowners=exact(lineage['locations'],'index');owners={i:allowners[i] for i in package['owners']};roster_rows=js(Q+'source-feature-roster.json.gz');roster=exact(roster_rows,'source_id');rindex=exact(roster_rows,'source_index')
cat=js('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json');assert len(roster)==sum(p['feature_count'] for p in cat['products']);sources={};receipts=[]
for family in ['gb:NZL:ADM1','gb:NZL:ADM2']:
 record=next(x for x in cat['products'] if x['key']==family);n=record['feature_count'];pieces=[]
 for p in record['parts']:
  b=read(p['path']);pin=inputs[(H,p['path'])];assert pin['sha256']==p['sha256'] and pin['bytes']==p['bytes'] and len(b)==p['uncompressed_bytes'] and sha(b)==p['uncompressed_sha256'];pieces.append(b)
 b=b''.join(pieces);assert len(b)==record['original_bytes'] and sha(b)==record['original_sha256'];product=json.loads(b);assert product.get('crs',{}).get('properties',{}).get('name','urn:ogc:def:crs:OGC:1.3:CRS84')=='urn:ogc:def:crs:OGC:1.3:CRS84';features=product['features'];assert len(features)==n==record['feature_count']
 ids=[family+':'+f['properties']['shapeID'] for f in features];assert len(set(ids))==n and ids==[r['source_id'] for r in roster_rows if r['source_id'].startswith(family+':')]
 assert all(shape(f['geometry']).is_valid for f in features);sources[family]=dict(zip(ids,features));receipts.append({**record,'native_crs_declaration':product.get('crs'),'coordinate_interpretation':'Explicit OGC CRS84' if 'crs' in product else 'GeoJSON default longitude-latitude WGS84 per RFC 7946 section 4; no explicit native CRS member','coordinate_interpretation_reference':'https://datatracker.ietf.org/doc/html/rfc7946#section-4'})
segments=[]
for block in range(38,42):segments+=js(P+f'/frozen-queue/block-{block:03}.json.gz',F)
assert len(segments)==17520 and sum(z-a for y,a,z,*_ in segments)==56626 and {o[0] for y,a,z,o,s,c in segments}==set(owners)
assert all(len(o)==1 and c in ['land','inland-water'] for y,a,z,o,s,c in segments)
selection=js('data/ownership-selection.json');bp=selection['selected_geography'];bb=read(bp['path'],bp.get('commit',H));assert len(bb)==bp['bytes'] and sha(bb)==bp['sha256'];bank=json.loads(bb);targets={};targetids={o['id'] for o in owners.values()}
for path in ['data/geography/part-17.json']:
 pin=next(x for x in bank['unchanged_files']+bank['overrides'] if x['path']==path);body=read(path,pin['commit']);assert len(body)==pin['bytes'] and sha(body)==pin['sha256'];features=exact(json.loads(body)['features'],'id');targets.update({i:f for i,f in features.items() if i in targetids})
assert set(targets)==targetids
manifest=js(selection['manifest_path']);lat=manifest['native_latitudes'];b=read(lat['path'],lat['commit']);assert sha(b)==lat['decoded_sha256'];latitude=np.frombuffer(b,dtype='<f8');assert len(latitude)==262166
cells=[(x,y,o[0],tuple(s)) for y,a,z,o,s,c in segments for x in range(a,z)];points=shapely.points([[(x+.5)/262166*360-180,latitude[y]] for x,y,*_ in cells]);actual=[set() for _ in cells];members=[];pointtree=shapely.STRtree(points)
for family,features in sources.items():
 for ident,f in features.items():
  g=shape(f['geometry']);possible=pointtree.query(g);inds=possible[shapely.covers(g,points[possible])];sid=roster[ident]['source_index']
  for i in inds:actual[i].add(sid)
  members.append({'id':ident,'source_index':sid,'owners':roster[ident]['owners'],'candidate_cells':len(inds)})
mismatches=[{'x':c[0],'y':c[1],'recorded':list(c[3]),'actual':sorted(a)} for c,a in zip(cells,actual) if set(c[3])!=a];assert not mismatches,str(mismatches[:4])
foreign_roster=[r for r in roster_rows if not r['owners'] and not r['source_id'].startswith('gb:NZL:')]
assert not any(any(not rindex[s]['source_id'].startswith('gb:NZL:') for s in c[3]) for c in cells)
# The complete pinned country product is a separate coarse contrary-evidence screen.
country_path='data/retained-geographic-sources/namibia/natural-earth-reference-countries.geojson.gz';cb=read(country_path);registry=js('data/sources.json');assert sha(cb)==registry['hashes']['ne_10m_admin_0_countries'];country=json.loads(cb);country_checks=[];foreign_features=[];foreign_keys=set();invalid_countries=[]
for f in country['features']:
 g=shape(f['geometry']);code=f['properties']['ADM0_A3']
 if not g.is_valid:
  a,b,c,d=g.bounds;xy=shapely.get_coordinates(points);box=(xy[:,0]>=a)&(xy[:,0]<=c)&(xy[:,1]>=b)&(xy[:,1]<=d);invalid_countries.append({'code':code,'bounds':list(g.bounds),'candidate_centres_in_bounds':int(np.count_nonzero(box))});assert not np.any(box),'Invalid country source intersects candidate bounds';continue
 idx=np.flatnonzero(shapely.covers(g,points));n=len(idx)
 if n:country_checks.append({'code':code,'name':f['properties'].get('ADMIN'),'cells':n})
 if n and code!='NZL':foreign_features.append(f);foreign_keys.update(int(i) for i in idx)
# Authenticate explanatory methods and full original membership without replaying old preparation.
methods={p:read(p).decode() for p in ['scripts/semantic-locations.py','scripts/geographic-regions.py','scripts/rebuild-framework.py']};assert 'union_all([geoms[i] for i in indices])' in methods['scripts/semantic-locations.py'];semantic=js('data/semantic-report.json');hierarchy=js('data/hierarchy.json');parents=[x for x in hierarchy if x['id'] in {o['province_id'] for o in owners.values()}];decisions=js('data/geographic-decisions/oceania.json');metadata=js('data/administrative-sources.json')
stages=[];checks=[];aggregate_checks=[]
for index,o in sorted(owners.items()):
 t=targets[o['id']];m=t['properties']['metadata'];atoms=o['source_atoms'];assert t['properties']['parent_id']==o['province_id'] and t['properties']['reference_owner']=='New Zealand' and t['properties']['name']==o['name'];assert shape(t['geometry']).is_valid
 if len(atoms)>1:
  change=next(c for c in semantic['changes'] if c['id']==o['id']);assert set(atoms)==set(m['source_member_ids'])==set(change['replaces']) and len(atoms)==len(m['source_member_ids'])==len(change['replaces'])
  scope='Whole explicit source-member city aggregate; original construction joins existing member geometries, not a presumed contemporary municipal boundary.'
  union=shapely.union_all([shape(sources['gb:NZL:ADM2'][a]['geometry']) for a in atoms]);aggregate_checks.append({'id':o['id'],'name':o['name'],'source_members':atoms,'semantic_change':change,'source_union_current_symmetric_difference_degrees2':shape(t['geometry']).symmetric_difference(union).area,'scope':scope,'limit':'Squared-degree geometry difference is a method diagnostic, not physical area or current legal boundary evidence.'})
 else:
  assert atoms==[o['id']] and m['source_id']=='gb:NZL:ADM2' and m['reference_year']=='2021' and m['source_role'] in ['Territorial authority','Auckland local board area','Residual offshore territory outside territorial authorities'];assert m['original_id']==sources['gb:NZL:ADM2'][o['id']]['properties']['shapeID'];scope='Whole direct original '+m['source_role']+'; exact source identity is retained. '+m['selection_reason']
 for ident in atoms:
  assert lineage['reverse'][ident]==[index] and roster[ident]['owners']==[index];source=sources['gb:NZL:ADM2'][ident]
  assert len(atoms)==1;source_name=source['properties']['shapeName'] # Raw source spelling may contain retained mojibake; identity is exact shapeID, never name matching.
  stages.append({'target':ident,'consumed':source,'selected':t})
 checks.append({'id':o['id'],'pixelIndex':index,'name':o['name'],'source_atoms':atoms,'metadata':m,'candidate_cells':sum(z-a for y,a,z,oo,ss,c in segments if oo==[index]),'scope_decision':scope,'raw_source_name':source_name,'display_name_differs':source_name!=o['name']})
assert len(stages)==len({s['target'] for s in stages})==sum(len(o['source_atoms']) for o in owners.values())==70 and len(aggregate_checks)==0
rows=collections.defaultdict(list)
for y,a,z,o,s,c in segments:rows[y].append([a,z,o[0]])
for y,runs in rows.items():
 merged=[]
 for r in sorted(runs):
  if merged and merged[-1][1]==r[0] and merged[-1][2]==r[2]:merged[-1][1]=r[1]
  else:merged.append(r.copy())
 assert all(a[1]<=b[0] for a,b in zip(merged,merged[1:]));rows[y]=merged
limits=['Source-relative restoration only; no effective/current legal-jurisdiction, historical affiliation or current dry-land certification.','Original represented-year claims 2017/2021 remain distinct from update/build dates; retained CC BY 4.0 notices and actual source roles require separate interpretation.','Direct originals include territorial authorities, 21 Auckland local boards and one disconnected offshore residual. Generic source-family/canonical labels do not erase their distinct roles or open semantic questions. Exact ancestry does not alone establish native support.','Foreign ownerless absence is relative to the complete original-product native-centre census; complete Natural Earth country screen is coarse reference evidence, not sovereignty clearance.','Earlier New Zealand and Southwest Pacific regional, source-fitness and whole-candidate unknowns remain; all relevant physical/historical evidence is assessed separately.','Separate physical-interpretation companion excluded from repair credit; complete physical/native and current selected conservation remain subsequent obligations.']
assessment={'version':1,'issue':2370,'baseline_commit':H,'frozen_input_commit':F,'original_cells':sum(z-a for y,a,z,*_ in segments),'original_segments':len(segments),'owners':len(owners),'source_members':len(stages),'complete_source_feature_count':sum(len(v) for v in sources.values()),'source_membership_mismatches':mismatches,'complete_sources':receipts,'all_source_members':members,'target_checks':checks,'parent_records':parents,'retained_location_review':[x for x in decisions.get('location_review',[]) if targetids.intersection(x.get('ids',[]))],'foreign_ownerless_census_features':len(foreign_roster),'foreign_ownerless_candidate_cells':0,'country_product_features':len(country['features']),'country_reference_hits':country_checks,'invalid_country_records':invalid_countries,'foreign_country_reference_cells':len(foreign_keys),'foreign_country_native_cells':[[*cells[i][:3]] for i in sorted(foreign_keys)],'aggregate_construction':aggregate_checks,'recorded_metadata':{k:v for k,v in metadata.items() if k.startswith('gb:NZL:')},'inputs':list(inputs.values()),'limits':limits,'runtime':{'python':sys.version,'numpy':np.__version__,'shapely':shapely.__version__,'geos':shapely.geos_version_string},'elapsed_seconds':time.monotonic()-started}
products={'original-stage-inputs.json':stages,'native-patch.json':{'rows':[{'y':y,'runs':r} for y,r in sorted(rows.items())]},'source-scope-assessment.json':assessment,'original-package.json':package,'foreign-country-features.geojson':{'type':'FeatureCollection','features':foreign_features}}
encoded={n:(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n').encode() for n,d in products.items()};assert all(len(b)<=MAX_FILE for b in encoded.values()) and total+sum(map(len,encoded.values()))<=MAX_PHASE
assert all(not p.is_symlink() for p in (O,*O.parents)) and O.parent.is_dir() and not O.exists();O.mkdir();out={}
for n,b in encoded.items():
 with (O/n).open('xb') as f:f.write(b)
 out[n]={'bytes':len(b),'sha256':sha(b)}
with (O/'preparation.json').open('x') as f:f.write(json.dumps({'complete':True,'inputs_encoded_decoded_bytes':total,'outputs':out},separators=(',',':'))+'\n')
print(json.dumps({'complete':True,'cells':len(cells),'intervals':len(segments),'owners':len(owners),'source_members':len(stages),'foreign_country_reference_cells':len(foreign_keys),'elapsed_seconds':time.monotonic()-started}))

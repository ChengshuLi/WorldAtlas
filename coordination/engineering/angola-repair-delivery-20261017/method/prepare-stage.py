import collections,gzip,hashlib,json,os,pathlib,subprocess,sys,time
import numpy as np
import shapely
from shapely.geometry import shape
# Reproduce the bounded source/identity screen from exact accepted Git inputs.
# Usage: python prepare-stage.py READ_ONLY_REPO FROZEN_QUEUE_DIRECTORY FRESH_OUTPUT
assert len(sys.argv)==4, "Supply repository, frozen queue directory, and fresh output"
W,D,O=map(lambda value:pathlib.Path(value).absolute(),sys.argv[1:])
assert W.is_dir() and D.is_dir() and O.parent.is_dir()
assert all(not p.is_symlink() for root in (W,D,O) for p in (root,*root.parents))
assert not O.exists(), "Fresh source-stage output required"
H='579c2850ab0eb4bbcc1a6f41f8eb0563791208fe'
started=time.monotonic(); inputs={}
sha=lambda b:hashlib.sha256(b).hexdigest()
env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_TERMINAL_PROMPT':'0'}
def read(p,h=H):
 b=subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'show',h+':'+p],env=env)
 oid=subprocess.check_output(['git','-C',str(W),'rev-parse',h+':'+p],env=env,text=True).strip(); pin={'path':p,'commit':h,'mode':'100644','git_blob_oid':oid,'bytes':len(b),'sha256':sha(b)}
 if p.endswith('.gz'):
  d=gzip.decompress(b);pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
 inputs[(h,p)]=pin;return b
Q='coordination/engineering/global-current-cell-work-queue-20261014/'
queue=json.loads(read(Q+'source-package-queue.json'));assert inputs[(H,Q+'source-package-queue.json')]['sha256']=='78007430b6f9faedb188ef0619b7ff0a7a2cc7fff2ec9f1c41ee69936ec4ebd8'
package=next(x for x in queue['packages'] if x['package_id']=='gb-AGO-ADM2--repair-evaluation'); assert package['native_cells']==170526
lineage=json.loads(read(Q+'lineage.json.gz')); owner_set=set(package['owners']); owners={x['index']:x for x in lineage['locations'] if x['index'] in owner_set}; assert len(owners)==47
roster=json.loads(read(Q+'source-feature-roster.json.gz')); roster={x['source_id']:x for x in roster if x['family_index'] in (2,3,69,71,232,363)}; assert len(roster)==241
cat=json.loads(read('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json')); sources={}; receipts=[]
for family in ['gb:AGO:ADM1','gb:AGO:ADM2','gb:COD:ADM1','gb:COG:ADM1','gb:NAM:ADM1','gb:ZMB:ADM1']:
 record=next(x for x in cat['products'] if x['key']==family); pieces=[]
 for p in record['parts']:
  b=read(p['path']);pin=inputs[(H,p['path'])];assert pin['sha256']==p['sha256'] and len(b)==p['uncompressed_bytes'] and sha(b)==p['uncompressed_sha256'];pieces.append(b)
 b=b''.join(pieces);assert len(b)==record['original_bytes'] and sha(b)==record['original_sha256']; product=json.loads(b)
 assert product['crs']['properties']['name']=='urn:ogc:def:crs:OGC:1.3:CRS84'
 ids=[family+':'+f['properties']['shapeID'] for f in product['features']]
 assert ids==[x['source_id'] for x in sorted(roster.values(),key=lambda x:x['source_index']) if x['source_id'].startswith(family+':')]
 assert all(shape(f['geometry']).is_valid for f in product['features']); sources[family]=dict(zip(ids,product['features'])); receipts.append(record)
target_ids={x['id'] for x in owners.values()}; current={}
selection=json.loads(read('data/ownership-selection.json')); bank_pin=selection['selected_geography']; bank_raw=read(bank_pin['path']); assert len(bank_raw)==bank_pin['bytes'] and sha(bank_raw)==bank_pin['sha256']; bank=json.loads(bank_raw)
p=next(x for x in bank['overrides'] if x['logical_path']=='data/geography/part-29.json')
b=read(p['path'],p['commit']); observed=inputs[(p['commit'],p['path'])]
assert observed['bytes']==p['bytes'] and observed['sha256']==p['sha256'] and len(b)==p['decoded_bytes'] and sha(b)==p['decoded_sha256']
fs=json.loads(b)['features'];assert len({f['id'] for f in fs})==len(fs);current.update({f['id']:f for f in fs if f['id'] in target_ids})
assert set(current)==target_ids
admin_metadata=json.loads(read('data/administrative-sources.json'))
parent_hierarchy=json.loads(read('data/hierarchy.json'))
parent_records=[x for x in parent_hierarchy if x['id'] in {o['province_id'] for o in owners.values()}]
geographic_method=read('scripts/geographic-regions.py').decode();framework_method=read('scripts/rebuild-framework.py').decode()
assert 'province_parts[key].add(code)' in geographic_method and "parent_match=province_basis" in framework_method

# Exact frozen extractor outputs, verified separately against the stock extractor.
segments=[]
for b in [32,33,34,35]:
 name=f'block-{b:03}.json.gz'
 frozen=read('coordination/engineering/angola-repair-delivery-20261017/frozen-queue/'+name,'f6757e4662d3d13d246a5fa586e55da659a6c9e6')
 assert gzip.decompress((D/name).read_bytes())==frozen, 'Frozen extracted block differs from retained exact stock output'
 segments+=json.loads(frozen)
assert len(segments)==15252 and sum(z-a for y,a,z,*_ in segments)==170526 and {o[0] for y,a,z,o,s,c in segments}==owner_set
assert all(len(o)==1 and c in ('land','inland-water') for y,a,z,o,s,c in segments)
selection=json.loads(read('data/ownership-selection.json')); manifest=json.loads(read(selection['manifest_path'])); lat=manifest['native_latitudes'];latitudes=np.frombuffer(read(lat['path'],lat['commit']),dtype='<f8');assert len(latitudes)==262166
cells=[(x,y,o[0],tuple(s)) for y,a,z,o,s,c in segments for x in range(a,z)];points=shapely.points([[(x+.5)/262166*360-180,latitudes[y]] for x,y,*_ in cells]);actual=[set() for _ in cells];members=[]
for family,features in sources.items():
 for ident,f in features.items():
  hits=shapely.covers(shape(f['geometry']),points); indices=np.flatnonzero(hits);sid=roster[ident]['source_index']
  for i in indices:actual[i].add(sid)
  members.append({'id':ident,'source_index':sid,'owners':roster[ident]['owners'],'candidate_cells':len(indices)})
mismatch=[{'x':c[0],'y':c[1],'recorded':list(c[3]),'actual':sorted(a)} for c,a in zip(cells,actual) if set(c[3])!=a];assert not mismatch, str(mismatch[:10])
stages=[]; checks=[]; rows=collections.defaultdict(list)
for y,a,z,o,s,c in segments:rows[y].append([a,z,o[0]])
for y,runs in rows.items():
 runs.sort(); merged=[]
 for r in runs:
  if merged and merged[-1][1]==r[0] and merged[-1][2]==r[2]:merged[-1][1]=r[1]
  else:merged.append(r.copy())
 assert all(a[1]<=b[0] for a,b in zip(merged,merged[1:]));rows[y]=merged
for index,o in sorted(owners.items()):
 ident=o['id'];s=sources['gb:AGO:ADM2'][ident];t=current[ident];m=t['properties']['metadata'];sg=shape(s['geometry']);tg=shape(t['geometry'])
 assert o['source_atoms']==[ident] and lineage['reverse'][ident]==[index] and roster[ident]['owners']==[index]
 assert t['properties']['name']==o['name']==s['properties']['shapeName'] and t['properties']['reference_owner']=='Angola'
 assert m['source_id']=='gb:AGO:ADM2' and m['reference_year']=='2018' and m['source_role']=='Municipality' and m['original_id']==s['properties']['shapeID']
 assert t['properties']['parent_id']==o['province_id'] and m['location_basis']=='Published municipality territory, 2018 humanitarian source'
 assert sg.is_valid and tg.is_valid
 assert not any(m.get(k) for k in ['residual_overlap_repair','display_geometry_repaired'])
 stages.append({'target':ident,'consumed':s,'selected':t});checks.append({'id':ident,'pixelIndex':index,'name':o['name'],'source_atoms':o['source_atoms'],'metadata':m,'source_components':len(sg.geoms) if sg.geom_type=='MultiPolygon' else 1,'current_components':len(tg.geoms) if tg.geom_type=='MultiPolygon' else 1,'source_holes':sum(len(p.interiors) for p in (sg.geoms if sg.geom_type=='MultiPolygon' else [sg])),'positive_source_current_intersection':sg.intersection(tg).area>0,'current_holes':sum(len(p.interiors) for p in (tg.geoms if tg.geom_type=='MultiPolygon' else [tg])),'candidate_cells':sum(z-a for y,a,z,oo,ss,c in segments if oo==[index])})
reviews=[]
for continent in ['africa']:
 decisions=json.loads(read('data/geographic-decisions/'+continent+'.json'));reviews.extend(x for x in decisions.get('location_review',[]) if target_ids.intersection(x.get('ids',[])))
component_checks=[]
for index,o in sorted(owners.items()):
 sg=shape(sources['gb:AGO:ADM2'][o['id']]['geometry']);tg=shape(current[o['id']]['geometry']);pts=points[[i for i,c in enumerate(cells) if c[2]==index]];parts=list(sg.geoms) if sg.geom_type=='MultiPolygon' else [sg];hits_total=0
 for ordinal,g in enumerate(parts):
  hits=int(np.count_nonzero(shapely.covers(g,pts)));ties=int(np.count_nonzero(shapely.intersects(g.boundary,pts)));hits_total+=hits
  component_checks.append({'target_id':o['id'],'owner':index,'component':ordinal,'candidate_cells':hits,'candidate_boundary_ties':ties,'positive_current_intersection':g.intersection(tg).area>0,'bounds':list(g.bounds)})
 assert hits_total==len(pts)
assert sum(x['candidate_cells'] for x in component_checks)==170526
assert not any(x['candidate_boundary_ties'] for x in component_checks)
portions=[c for c in checks if c['metadata']['parent_match'].startswith('Geographic portion')];assert not portions

assessment={'version':1,'issue':2313,'baseline_commit':H,'original_cells':170526,'original_segments':15252,'owners':47,'complete_source_feature_count':241,'source_membership_mismatches':mismatch,'complete_sources':receipts,'all_source_members':members,'target_checks':checks,'component_checks':component_checks,'detached_component_candidate_cells':sum(x['candidate_cells'] for x in component_checks if not x['positive_current_intersection']),'parent_records':parent_records,'geographic_portion_targets':[x['id'] for x in portions],'administrative_source_metadata':admin_metadata,'retained_location_review':reviews,'inputs':list(inputs.values()),'method':'Authenticate complete original source families and frozen queue; independently compare Shapely covers at every native centre; preserve selected whole-feature identity, source role, lineage, names and explicit exclusions. Native constructor independently checks the complete original ADM2 source family. ADM1 members have no selected owner identities and remain retained contextual competitors, never invented location owners.','source_scope_decision':'All 47 selected targets expressly represent published municipality territory from the 2018 humanitarian source, with same-named exclusive original atoms. Source-relative restoration follows that retained declared territory, including detached components, subject to all complete source competitors, original physical evidence and exact current owner-zero. There is no current-law or current-component-overlap eligibility gate.','limits':['2018 humanitarian municipality-source-relative restoration only; no contemporary legal-jurisdiction equivalence is asserted.','The 2024 redivision and Cabinda ten-municipality boundaries remain unresolved in #1046 and #896.','Original custody #1423, shared seam #1243 and Namibia-water #1268/#1397 retain their distinct evidence and uncertainties; old completion/release grants no geographic approval.','Complete physical/native qualification and actual selected emitted-consumer verification remain subsequent gates.'],'runtime':{'python':sys.version,'numpy':np.__version__,'shapely':shapely.__version__,'geos':shapely.geos_version_string},'elapsed_seconds':time.monotonic()-started}
products={'original-stage-inputs.json':stages,'native-patch.json':{'rows':[{'y':y,'runs':r} for y,r in sorted(rows.items())]},'source-scope-assessment.json':assessment,'original-package.json':package}
assert all(not p.is_symlink() for p in (O,*O.parents)) and O.parent.is_dir() and not O.exists()
O.mkdir();out={}
for n,d in products.items():
 b=(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n').encode()
 with (O/n).open('xb') as stream:stream.write(b)
 out[n]={'bytes':len(b),'sha256':sha(b)}
with (O/'preparation.json').open('x') as stream:stream.write(json.dumps({'complete':True,'outputs':out},separators=(',',':'))+'\n')
print(json.dumps({'complete':True,'cells':170526,'segments':15252,'owners':47,'source_features':241,'membership_mismatches':len(mismatch),'recorded_topology_reconciliations':sum(bool(c['metadata'].get('topology_reconciled')) for c in checks),'detached_component_cells':assessment['detached_component_candidate_cells'],'elapsed_seconds':time.monotonic()-started}))

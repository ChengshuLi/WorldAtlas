import collections,gzip,hashlib,json,os,pathlib,subprocess,sys,time
import numpy as np
import shapely
from shapely.geometry import shape
R=pathlib.Path('/workspace/scratch/127991fc8b8e/iceland-repair-20261016')
W=pathlib.Path((R/'work-path').read_text()); H='5c65b213d005607e769af66d39bf03d4554882d6'
P='coordination/engineering/iceland-native-repair-20261016'; D=pathlib.Path('/workspace/scratch/127991fc8b8e/next-repair-handoff-20261016')
O=W/P/'source-stage'; assert not O.exists(); started=time.monotonic(); inputs={}
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
package=next(x for x in queue['packages'] if x['package_id']=='gb-ISL-ADM2--repair-evaluation'); assert package['native_cells']==79719
lineage=json.loads(read(Q+'lineage.json.gz')); owner_set=set(package['owners']); owners={x['index']:x for x in lineage['locations'] if x['index'] in owner_set}; assert len(owners)==61
roster=json.loads(read(Q+'source-feature-roster.json.gz')); roster={x['source_id']:x for x in roster if x['family_index'] in (160,161)}; assert len(roster)==82
cat=json.loads(read('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json')); sources={}; receipts=[]
for family in ['gb:ISL:ADM1','gb:ISL:ADM2']:
 record=next(x for x in cat['products'] if x['key']==family); pieces=[]
 for p in record['parts']:
  b=read(p['path']);pin=inputs[(H,p['path'])];assert pin['sha256']==p['sha256'] and len(b)==p['uncompressed_bytes'] and sha(b)==p['uncompressed_sha256'];pieces.append(b)
 b=b''.join(pieces);assert len(b)==record['original_bytes'] and sha(b)==record['original_sha256']; product=json.loads(b)
 assert product['crs']['properties']['name']=='urn:ogc:def:crs:OGC:1.3:CRS84'
 ids=[family+':'+f['properties']['shapeID'] for f in product['features']]
 assert ids==[x['source_id'] for x in sorted(roster.values(),key=lambda x:x['source_index']) if x['source_id'].startswith(family+':')]
 assert all(shape(f['geometry']).is_valid for f in product['features']); sources[family]=dict(zip(ids,product['features'])); receipts.append(record)
part=json.loads(read('data/geography/part-11.json')); target_ids={x['id'] for x in owners.values()}; current={f['id']:f for f in part['features'] if f['id'] in target_ids};assert set(current)==target_ids
# Exact frozen extractor outputs, verified separately against the stock extractor.
segments=[]
for b in [15,16,17]:segments+=json.load(gzip.open(D/f'iceland-extracted/block-{b:03}.json.gz'))
assert len(segments)==20402 and sum(z-a for y,a,z,*_ in segments)==79719 and {o[0] for y,a,z,o,s,c in segments}==owner_set
assert all(len(o)==1 and c=='land' for y,a,z,o,s,c in segments)
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
 ident=o['id'];s=sources['gb:ISL:ADM2'][ident];t=current[ident];m=t['properties']['metadata'];sg=shape(s['geometry']);tg=shape(t['geometry'])
 assert o['source_atoms']==[ident] and lineage['reverse'][ident]==[index] and roster[ident]['owners']==[index]
 assert t['properties']['name']==o['name']==s['properties']['shapeName'] and t['properties']['reference_owner']=='Iceland'
 assert m['source_id']=='gb:ISL:ADM2' and m['reference_year']=='2016' and m['source_role']=='Municipality' and m['original_id']==s['properties']['shapeID']
 assert t['properties']['parent_id']==o['province_id'] and m['selection_reason'].startswith('Named Municipalities territories')
 assert sg.is_valid and tg.is_valid and sg.intersection(tg).area>0
 assert not any(m.get(k) for k in ['topology_reconciled','residual_overlap_repair','display_geometry_repaired'])
 stages.append({'target':ident,'consumed':s,'selected':t});checks.append({'id':ident,'pixelIndex':index,'name':o['name'],'source_atoms':o['source_atoms'],'metadata':m,'source_components':len(sg.geoms) if sg.geom_type=='MultiPolygon' else 1,'current_components':len(tg.geoms) if tg.geom_type=='MultiPolygon' else 1,'source_holes':sum(len(p.interiors) for p in (sg.geoms if sg.geom_type=='MultiPolygon' else [sg])),'current_holes':sum(len(p.interiors) for p in (tg.geoms if tg.geom_type=='MultiPolygon' else [tg])),'candidate_cells':sum(z-a for y,a,z,oo,ss,c in segments if oo==[index])})
decisions=json.loads(read('data/geographic-decisions/europe.json'));reviews=[x for x in decisions.get('location_review',[]) if target_ids.intersection(x.get('ids',[]))]
assessment={'version':1,'issue':2271,'baseline_commit':H,'original_cells':79719,'original_segments':20402,'owners':61,'complete_source_feature_count':82,'source_membership_mismatches':mismatch,'complete_sources':receipts,'all_source_members':members,'target_checks':checks,'retained_location_review':reviews,'inputs':list(inputs.values()),'method':'Authenticate complete original source families and frozen queue; independently compare Shapely covers at every native centre; preserve selected whole-feature identity, source role, lineage, names and explicit exclusions. Native constructor independently checks the complete original ADM2 source family. ADM1 members have no selected owner identities and remain retained contextual competitors, never invented location owners.','source_scope_decision':'The selected metadata affirmatively defines these targets as named Municipalities territories with identical 2016 original source IDs and names. No target has a recorded topology/display exclusion. Restore supported original source components, including detached components, subject to physical support, competing owners and exact owner-zero. No component-current-overlap predicate is added.','limits':['2016 municipal-source relative restoration; no contemporary legal-jurisdiction certification.','2017 OSM/Wambacher ADM1 context retains ODbL 1.0, while ADM2 retains CC BY 4.0.','Existing regional semantic review and historical-import gates remain open.','Complete original physical/native qualification and current selected consumer verification are subsequent stages.'],'runtime':{'python':sys.version,'numpy':np.__version__,'shapely':shapely.__version__,'geos':shapely.geos_version_string},'elapsed_seconds':time.monotonic()-started}
products={'original-stage-inputs.json':stages,'native-patch.json':{'rows':[{'y':y,'runs':r} for y,r in sorted(rows.items())]},'source-scope-assessment.json':assessment,'original-package.json':package}
assert not O.exists();O.mkdir(parents=True);out={}
for n,d in products.items():
 b=(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n').encode();(O/n).write_bytes(b);out[n]={'bytes':len(b),'sha256':sha(b)}
(O/'preparation.json').write_text(json.dumps({'complete':True,'outputs':out},separators=(',',':'))+'\n')
print(json.dumps({'complete':True,'cells':79719,'segments':20402,'owners':61,'source_features':82,'membership_mismatches':len(mismatch),'recorded_topology_exclusions':0,'elapsed_seconds':time.monotonic()-started}))

"""Prepare globally dated, whole-location ownership; never carry through gaps."""
import subprocess
import collections,gzip,hashlib,json,pathlib,sqlite3,shutil
from shapely import STRtree,prepare,destroy_prepared,from_wkb
from shapely.geometry import shape
from majority import canonical,area,decide
R=pathlib.Path(__file__).resolve().parents[1];D=R/'data';OUT=D/'ownership-history';OUT.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
algorithm_files=['majority.py','prepare-ownership.py','ellipsoidal_area.py']
previous=read(OUT/'index.json') if (OUT/'index.json').exists() else None
index=read(D/'world-index.json');pi=read(D/'cliopatria/index.json');inputs={p:digest(D/p) for p in ['cliopatria/index.json']+list(dict.fromkeys('cliopatria/'+r['chunk'] for r in pi['records']))};inputs['algorithm']='strict-majority-wgs84-integral-v3';inputs['algorithm_sha256']=''.join(digest(R/'scripts'/p) for p in algorithm_files)
expected_footprints=subprocess.check_output(['node','scripts/stamp-prepared.mjs','--hash'],cwd=R,text=True).strip()
inputs['footprints_sha256']=expected_footprints
if (OUT/'candidate-recovery.json').exists():inputs['candidate_recovery_sha256']=digest(OUT/'candidate-recovery.json')
features=sorted([f for p in index['parts'] for f in read(D/p)['features']],key=lambda f:f['id']);locations=[canonical(shape(f['geometry'])) for f in features];tree=STRtree(locations)
chunks=list(dict.fromkeys(r['chunk'] for r in pi['records']));records=[{k:v for k,v in f.items() if k!='geometry'} for p in chunks for f in read(D/'cliopatria'/p)['features']]
# Supported non-example footprint overrides participate in derivation and cache keys.
versions=collections.defaultdict(list)
con=sqlite3.connect('file:'+str(D/'atlas.sqlite')+'?mode=ro',uri=True)
for id,start,end,raw in con.execute('SELECT location_id,valid_from,valid_to,geometry FROM boundaries WHERE is_example=0'):
 versions[id].append((start,end,canonical(shape(json.loads(raw)))))
con.close();inputs['boundary_versions']=hashlib.sha256(str([(id,[(a,b,g.wkb_hex) for a,b,g in v]) for id,v in sorted(versions.items())]).encode()).hexdigest()
if (OUT/'index.json').exists() and read(OUT/'index.json').get('inputs')==inputs:print('Ownership derivation cache is current');raise SystemExit
# Identity uses Wikidata when provided; a namespaced source ID otherwise.
entities={};record_owner=[]
for f in records:
 p=f['properties'];q=p.get('wikidata');key='owner:'+q if q else 'owner:cliopatria:'+hashlib.sha256((p.get('seshat_id') or p['name']).encode()).hexdigest()[:16]
 entities.setdefault(key,{'id':key,'kind':'owner','name':p['name'],'source':'Cliopatria v0.2.0-duplicate','source_url':pi['url']});record_owner.append(key)
# A disk-backed, per-source checkpoint bounds memory and resumes interrupted preparation.
totals=[area(g) for g in locations]
overlap_key=hashlib.sha256((expected_footprints+''.join(inputs[p] for p in sorted(inputs) if p.startswith('cliopatria/'))+inputs['algorithm_sha256']).encode()).hexdigest()
cache=R/'.cache/ownership-overlaps'/f'{overlap_key}.sqlite';cache.parent.mkdir(exist_ok=True)
measurements=sqlite3.connect(cache)
measurements.executescript('CREATE TABLE IF NOT EXISTS overlaps(location INTEGER,record INTEGER,share REAL,geometry BLOB,PRIMARY KEY(location,record)); CREATE TABLE IF NOT EXISTS source_geometry(record INTEGER PRIMARY KEY,geometry BLOB); CREATE TABLE IF NOT EXISTS progress(singleton INTEGER PRIMARY KEY,last_record INTEGER); INSERT OR IGNORE INTO progress VALUES(1,-1);')
completed=measurements.execute('SELECT last_record FROM progress WHERE singleton=1').fetchone()[0]
if completed>=0:print(f'Reusing overlap checkpoints through source {completed+1}/{len(records)}',flush=True)
j=-1
for chunk in chunks:
 raw=read(D/'cliopatria'/chunk)['features']
 for source_feature in raw:
  j+=1
  if j<=completed:continue
  g=canonical(shape(source_feature['geometry']));prepare(g)
  batch_measurements=[]
  for i in tree.query(g,predicate='intersects'):
   i=int(i);full=g.covers(locations[i]);clip=locations[i] if full else locations[i].intersection(g);share=1 if full else area(clip)/totals[i]
   if share>1e-8:batch_measurements.append((i,j,share,None if full else clip.wkb))
  measurements.executemany('INSERT OR REPLACE INTO overlaps VALUES(?,?,?,?)',batch_measurements)
  measurements.execute('INSERT OR REPLACE INTO source_geometry VALUES(?,?)',(j,g.wkb));destroy_prepared(g)
  measurements.execute('UPDATE progress SET last_record=? WHERE singleton=1',(j,))
  if j%100==0 or j==len(records)-1:measurements.commit();print(f'Ownership overlaps: {j+1}/{len(records)}',flush=True)
  del g,batch_measurements
 del raw
measurements.commit()
source='Bennett et al. (2025), Cliopatria v0.2.0-duplicate / Seshat; CC BY 4.0'
def prepare_location(i):
 f=features[i]
 measured=measurements.execute('SELECT record,share,geometry FROM overlaps WHERE location=? AND share>1e-8 ORDER BY record',(i,)).fetchall();candidates=[(j,share) for j,share,wkb in measured];interned={};clips={};memo={'areas':{}}
 for j,share,wkb in measured:
  if wkb and wkb not in interned:interned[wkb]=from_wkb(wkb)
  clips[j]=interned[wkb] if wkb else locations[i];memo['areas'][id(clips[j])]=totals[i]*share
 overrides=versions[f['id']]
 if overrides:
  for j,wkb in measurements.execute('SELECT record,geometry FROM source_geometry'):
   g=from_wkb(wkb)
   if j not in clips and any(g.intersects(v) for _,_,v in overrides):candidates.append((j,0))
 events=sorted({-3000,2027,*[t for j,_ in candidates for t in (records[j]['properties']['valid_from'],records[j]['properties']['valid_to'])],*[t for a,b,g in overrides for t in (a,b)]});rows=[]
 for start,end in zip(events,events[1:]):
  if start==0 or start>=2027 or end<=-3000:continue
  footprint=next((g for a,b,g in overrides if a<=start<b),locations[i]);active=[(j,s) for j,s in candidates if records[j]['properties']['valid_from']<=start<records[j]['properties']['valid_to'] and (footprint is not locations[i] or j in clips)]
  if not active:continue
  if len(active)==1 and footprint is locations[i]:
   j,share=active[0];result={'owner':record_owner[j] if share>.50000001 else None,'status':'derived' if share>.50000001 else 'no-majority','share':round(min(1,share),12),'coverage':round(min(1,share),12),'candidates':[[record_owner[j],round(min(1,share),12)]]}
  else:
   claims=collections.defaultdict(list)
   for j,_ in active:claims[record_owner[j]].append(clips[j] if footprint is locations[i] else from_wkb(measurements.execute('SELECT geometry FROM source_geometry WHERE record=?',(j,)).fetchone()[0]))
   result=decide(footprint,claims,totals[i] if footprint is locations[i] else None,preclipped=footprint is locations[i],cache=memo if footprint is locations[i] else None)
  winner=next((records[j]['properties']['name'] for j,_ in sorted(active,key=lambda v:(-v[1],records[v[0]]['id'])) if record_owner[j]==result['owner']),None)
  evidence={'owner_name':winner,'share':result['share'],'coverage':result['coverage'],'candidates':result['candidates'],'source_record_ids':[records[j]['id'] for j,_ in active],'footprint':'dated' if footprint is not locations[i] else 'reference'}
  row=[start,end,result['owner'],result['status'],evidence]
  if rows and rows[-1][1]==start and rows[-1][2:]==row[2:]:rows[-1][1]=end
  else:rows.append(row)
 return [f['id'],rows]
def prepare_part(task):
 part,start,end=task;batch=[prepare_location(i) for i in range(start,end)];statuses=collections.Counter(row[3] for id,rows in batch for row in rows)
 path=f'part-{part}.json.gz';raw=json.dumps(batch,separators=(',',':')).encode();(OUT/path).write_bytes(gzip.compress(raw,compresslevel=9,mtime=0))
 return {'path':path,'sha256':digest(OUT/path),'locations':len(batch)},dict(statuses)
def worker_init():
 global measurements
 measurements=sqlite3.connect('file:'+str(cache)+'?mode=ro',uri=True)
measurements.close()
import multiprocessing,os
parts=[];statuses=collections.Counter();intervals=0;done=0
workers=max(1,min(3,int(os.environ.get('ATLAS_PREP_WORKERS','3'))));tasks=[(n,i,min(i+1500,len(features))) for n,i in enumerate(range(0,len(features),1500))]
with multiprocessing.get_context('fork').Pool(workers,initializer=worker_init) as pool:
 for part,counts in pool.imap_unordered(prepare_part,tasks):
  parts.append(part);statuses.update(counts);done+=part['locations'];print(f'Ownership locations: {done}/{len(features)} ({workers} parallel workers)',flush=True)
parts.sort(key=lambda p:int(p['path'].split('-')[1].split('.')[0]));intervals=sum(statuses.values())
execution=[]
for p in algorithm_files:
 path='algorithms/exact/'+p;(OUT/path).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/'scripts'/p,OUT/path);execution.append({'path':path,'sha256':digest(OUT/path)})
initial=previous.get('initial_execution') if previous else None
if previous and not initial:
 initial={'inputs':previous['inputs'],'algorithms':[{'path':'algorithms/'+p,'sha256':digest(OUT/'algorithms'/p)} for p in ['majority.py','prepare-ownership.py']],'refinements':previous.get('refinements',[])}
manifest={'version':1,'inputs':inputs,'parts':parts,'entities':entities,'source':source,'source_url':pi['url'],'license':'CC BY 4.0','method':'majority-area','area_method':'WGS84 ellipsoid surface integral along straight longitude/latitude edges; 16-point Gauss-Legendre quadrature, centered antiderivative, compensated ring sums, antimeridian-normalized unions','threshold':.5,'locations':len(features),'intervals':intervals,'statuses':dict(statuses),'valid_from':-3000,'valid_to':2025,'note':'Uncovered land is part of the denominator. Conflicting claims and missing majorities resolve to null. No carry-forward outside source intervals. All cached partial-footprint areas were recomputed with the surface integral before exact decisions.','execution_algorithms':execution,'initial_execution':initial,'numerical_tolerances':{'majority_share_epsilon':1e-8,'candidate_share_epsilon':1e-8,'contradictory_overlap_share_epsilon':1e-6,'stored_share_decimal_places':12,'quadrature_order':16}}
(OUT/'index.json').write_text(json.dumps(manifest,separators=(',',':')));print(json.dumps({'locations':len(features),'intervals':intervals,'statuses':dict(statuses)}))

import runpy
runpy.run_path(str(R/'scripts/compact-ownership.py'),run_name='__main__')
subprocess.run(['node','scripts/stamp-prepared.mjs','ownership-history',expected_footprints],cwd=R,check=True)

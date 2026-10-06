#!/usr/bin/env python3
"""Stage exact ownership-v2 after an explicitly receipted footprint migration.

No published data, source snapshot, atlas database, or old overlap cache is edited.
Only location IDs whose footprint/date fingerprints changed are spatially derived.
"""
import argparse,collections,copy,gzip,hashlib,importlib.util,json,os,pathlib,shutil,sqlite3,subprocess,sys,tempfile
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parents[1]

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def dump(value):return json.dumps(value,separators=(',',':'),ensure_ascii=False)
def load(path):
 with (gzip.open(path,'rt') if str(path).endswith('.gz') else open(path)) as f:return json.load(f)
def safe_path(root,name):
 path=(root/name).resolve()
 if not path.is_relative_to(root.resolve()):raise ValueError('Asset path escapes source directory')
 return path
def write_gzip(path,value):
 raw=gzip.compress(dump(value).encode(),compresslevel=9,mtime=0);path.write_bytes(raw)
 return {'path':path.name,'sha256':sha(path)}
def retain_prior_archives(source,stage,index,names):
 """Keep earlier lineage receipts/rows across successive compact generations."""
 if not index.get('incremental_preparation'):return {}
 prefix='prior-archives/'+sha(source/'index.json');target=stage/prefix;target.mkdir(parents=True)
 retained={}
 for name in names:
  original=safe_path(source,name)
  if not original.exists():continue
  if original.is_symlink() or original.is_dir() and any(p.is_symlink() for p in original.rglob('*')):raise ValueError('Prior evidence archives must not contain symlinks')
  destination=safe_path(target,name);destination.parent.mkdir(parents=True,exist_ok=True)
  if original.is_dir():shutil.copytree(original,destination)
  else:shutil.copyfile(original,destination)
 for file in target.rglob('*'):
  if file.is_file():retained[file.relative_to(stage).as_posix()]=sha(file)
 return retained
def feature_snapshot(path):
 raw=load(path)
 if isinstance(raw,list):features=raw
 elif 'features' in raw:features=raw['features']
 elif 'parts' in raw:
  features=[]
  for part in raw['parts']:
   name=part if isinstance(part,str) else part['path'];asset=safe_path(path.parent,name)
   if isinstance(part,dict) and (sha(asset)!=part['sha256'] or asset.stat().st_size!=part['bytes']):raise ValueError('Snapshot shard checksum/size mismatch')
   body=load(asset)
   if isinstance(body,list):features.extend(body)
   elif isinstance(body,dict) and isinstance(body.get('features'),list):features.extend(body['features'])
   else:raise ValueError('Snapshot shard must contain features or an explicit feature array')
 else:raise ValueError('Expected explicit FeatureCollection/list or world-index manifest')
 result={}
 for f in features:
  id=f.get('id') or f.get('properties',{}).get('id')
  if not isinstance(id,str) or not id or id in result:raise ValueError('Missing or duplicate stable location ID')
  if f.get('properties',{}).get('id',id)!=id:raise ValueError('Conflicting location identity fields')
  if not f.get('geometry'):raise ValueError('Every location needs an explicit footprint')
  result[id]=f['geometry']
 return result

def published_footprint_hash(features):
 # Native JSON.stringify number formatting and localeCompare ordering are the
 # existing published contract; Python JSON serialization is not a substitute.
 code="const fs=require('node:fs'),c=require('node:crypto');let f=JSON.parse(fs.readFileSync(0,'utf8'));f.sort((a,b)=>a[0].localeCompare(b[0]));process.stdout.write(c.createHash('sha256').update(JSON.stringify(f)).digest('hex'));"
 return subprocess.check_output(['node','-e',code],input=dump(list(features.items())).encode(),cwd=ROOT).decode()

def exact_helpers(source,index):
 entries=index.get('execution_algorithms',[])
 if len(entries)!=3 or {pathlib.Path(e['path']).name for e in entries}!={'majority.py','prepare-ownership.py','ellipsoidal_area.py'}:raise ValueError('All three executed exact algorithm proofs are required')
 initial=index.get('initial_execution')
 if initial:
  for entry in initial['algorithms']:
   if sha(safe_path(source,entry['path']))!=entry['sha256']:raise ValueError('Initial executed algorithm hash mismatch')
  if ''.join(e['sha256'] for e in initial['algorithms'])!=initial['inputs']['algorithm_sha256']:raise ValueError('Initial execution receipt mismatch')
 for entry in entries:
  if sha(safe_path(source,entry['path']))!=entry['sha256']:raise ValueError('Executed algorithm hash mismatch')
 if ''.join(e['sha256'] for e in entries)!=index['inputs']['algorithm_sha256']:raise ValueError('Algorithm execution receipt mismatch')
 module_path=safe_path(source,next(e['path'] for e in entries if pathlib.Path(e['path']).name=='majority.py'))
 # Load the hash-verified archived helper, never current mutable script code.
 old=sys.modules.pop('ellipsoidal_area',None);sys.path.insert(0,str(module_path.parent))
 try:
  spec=importlib.util.spec_from_file_location('_incremental_exact_majority',module_path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 finally:
  sys.path.pop(0)
  if old is not None:sys.modules['ellipsoidal_area']=old
 return module

def boundary_versions(path,canonical,location_ids):
 from shapely.geometry import shape
 grouped=collections.defaultdict(list)
 for row in load(path):
  if isinstance(row,dict):
   if type(row.get('is_example'))!=bool:raise ValueError('Dated footprint object needs an explicit Boolean example flag')
   if row['is_example']:continue
   id,a,b,g=row['location_id'],row['valid_from'],row['valid_to'],row['geometry']
  elif isinstance(row,list) and len(row)==4:id,a,b,g=row
  else:raise ValueError('Expected dated footprint rows, with explicit example flag for object records')
  if id not in location_ids:raise ValueError('Dated footprint refers to absent snapshot location')
  if type(a)!=int or type(b)!=int or a==0 or b==0 or a>=b:raise ValueError('Invalid half-open dated footprint interval')
  geo=canonical(shape(json.loads(g) if isinstance(g,str) else g))
  if geo.is_empty:raise ValueError('Empty dated footprint')
  if any(a<end and start<b for start,end,_ in grouped[id]):raise ValueError('Overlapping non-example footprint overrides')
  grouped[id].append((a,b,geo))
 global_hash=hashlib.sha256(str([(id,[(a,b,g.wkb_hex) for a,b,g in vs]) for id,vs in sorted(grouped.items())]).encode()).hexdigest()
 per_id={id:hashlib.sha256(str([(a,b,g.wkb_hex) for a,b,g in grouped[id]]).encode()).hexdigest() for id in location_ids}
 return grouped,global_hash,per_id

def classify(before,after,bv,av,canonical):
 from shapely.geometry import shape
 fingerprints={}
 for tag,features,versions in [('before',before,bv),('after',after,av)]:
  fingerprints[tag]={}
  for id,raw in features.items():
   geometry=canonical(shape(raw))
   if geometry.is_empty:raise ValueError('Empty location footprint: '+id)
   fingerprints[tag][id]={'raw_geometry_sha256':hashlib.sha256(dump(raw).encode()).hexdigest(),'canonical_wkb_sha256':hashlib.sha256(geometry.wkb).hexdigest(),'boundary_versions_sha256':versions[id]}
 reused={id for id in before.keys() & after.keys() if fingerprints['before'][id]==fingerprints['after'][id]}
 return reused,set(after)-reused,set(before)-set(after),fingerprints

def check_receipt(receipt,before_hash,after_hash,changed,removed,added):
 if receipt.get('before_footprints_sha256')!=before_hash or receipt.get('after_footprints_sha256')!=after_hash:raise ValueError('Migration receipt footprint hash mismatch')
 for field,expected in [('changed_ids',changed-added),('removed_ids',removed),('added_ids',added)]:
  values=receipt.get(field)
  if not isinstance(values,list) or len(values)!=len(set(values)) or set(values)!=expected:raise ValueError('Migration receipt has incorrect '+field)
 if not receipt.get('source_evidence'):raise ValueError('Migration receipt requires source evidence')
 for relationship in receipt.get('relationships',[]):
  old=relationship.get('before_ids',[]);new=relationship.get('after_ids',[])
  if relationship.get('kind')=='source-backed-create':
   if old or not new or not set(new)<=set(added) or relationship.get('history_transfer') is not False:raise ValueError('Invalid source-backed creation relationship')
  elif not old or not new:raise ValueError('Invalid migration relationship')
  if not set(old)<=set(receipt['_before_ids']) or not set(new)<=set(receipt['_after_ids']):raise ValueError('Migration relationship refers to absent IDs')
 return True

def checked_sources(source,index):
 pi=load(source/'index.json');chunks=list(dict.fromkeys(r['chunk'] for r in pi['records']))
 expected={'cliopatria/index.json':sha(source/'index.json')}
 for chunk in chunks:expected['cliopatria/'+chunk]=sha(safe_path(source,chunk))
 actual={k:v for k,v in index['inputs'].items() if k.startswith('cliopatria/')}
 if actual!=expected:raise ValueError('Political source changed; unchanged-location reuse is unsafe. Run full preparation.')
 return pi,chunks

def source_owner(properties):
 return 'owner:'+properties['wikidata'] if properties.get('wikidata') else 'owner:cliopatria:'+hashlib.sha256((properties.get('seshat_id') or properties['name']).encode()).hexdigest()[:16]

def measure_changed(ids,after,versions,source,chunks,helpers,db):
 from shapely import STRtree,prepare,destroy_prepared,union_all
 from shapely.geometry import shape
 locations={id:helpers.canonical(shape(after[id])) for id in sorted(ids)}
 totals={id:helpers.area(g) for id,g in locations.items()}
 if any(not 0<total for total in totals.values()):raise ValueError('Location land denominator must be positive')
 query_geometries=[union_all([locations[id]]+[g for _,_,g in versions[id]]) for id in sorted(ids)];ordered=sorted(ids);tree=STRtree(query_geometries)
 db.executescript('CREATE TABLE source(record INTEGER PRIMARY KEY,id TEXT UNIQUE NOT NULL,properties TEXT NOT NULL,owner TEXT NOT NULL,geometry BLOB); CREATE TABLE overlap(location_id TEXT,record INTEGER,share REAL,clip BLOB,reference_candidate INTEGER,PRIMARY KEY(location_id,record));')
 count=0
 for chunk in chunks:
  for f in load(safe_path(source,chunk))['features']:
   props=f['properties'];a,b=props['valid_from'],props['valid_to']
   if type(a)!=int or type(b)!=int or a==0 or b==0 or a>=b:raise ValueError('Invalid political source interval')
   geo=helpers.canonical(shape(f['geometry']));prepare(geo);pending=[]
   for j in tree.query(geo,predicate='intersects'):
    id=ordered[int(j)];ref=locations[id];full=geo.covers(ref);clip=ref if full else ref.intersection(geo);share=1 if full else helpers.area(clip)/totals[id];eligible=share>1e-8
    if eligible or any(geo.intersects(g) for _,_,g in versions[id]):pending.append((id,count,share if eligible else 0,None if full else clip.wkb,int(eligible)))
   db.execute('INSERT INTO source VALUES(?,?,?,?,?)',(count,f['id'],dump(props),source_owner(props),geo.wkb if pending else None))
   db.executemany('INSERT INTO overlap VALUES(?,?,?,?,?)',pending);destroy_prepared(geo);count+=1
  db.commit();print('Scanned political source chunk',chunk,'records',count,flush=True)
 return locations,totals,count

def derive_location(id,location,total,overrides,helpers,db):
 from shapely import from_wkb
 measured=db.execute('SELECT o.record,o.share,o.clip,o.reference_candidate,s.id,s.properties,s.owner,s.geometry FROM overlap o JOIN source s ON s.record=o.record WHERE o.location_id=? ORDER BY o.reference_candidate DESC,o.record',(id,)).fetchall()
 candidates=[];clips={};memo={'areas':{}};interned={}
 for j,share,wkb,reference,rid,properties,owner,source_geo in measured:
  p=json.loads(properties);candidates.append((j,share,reference,rid,p,owner,source_geo))
  if reference:
   if wkb and wkb not in interned:interned[wkb]=from_wkb(wkb)
   clips[j]=interned[wkb] if wkb else location;memo['areas'][id_of(clips[j])]=total*share
 events=sorted({-3000,2027,*[t for _,_,_,_,p,_,_ in candidates for t in (p['valid_from'],p['valid_to'])],*[t for a,b,_ in overrides for t in (a,b)]});rows=[]
 for a,b in zip(events,events[1:]):
  if a==0 or a>=2027 or b<=-3000:continue
  footprint=next((g for start,end,g in overrides if start<=a<end),location)
  active=[c for c in candidates if c[4]['valid_from']<=a<c[4]['valid_to'] and (footprint is not location or c[0] in clips)]
  if not active:continue
  if len(active)==1 and footprint is location:
   j,share,_,rid,p,owner,_=active[0];result={'owner':owner if share>.50000001 else None,'status':'derived' if share>.50000001 else 'no-majority','share':round(min(1,share),12),'coverage':round(min(1,share),12),'candidates':[[owner,round(min(1,share),12)]]}
  else:
   claims=collections.defaultdict(list)
   for j,_,_,_,_,owner,g in active:claims[owner].append(clips[j] if footprint is location else from_wkb(g))
   result=helpers.decide(footprint,claims,total if footprint is location else None,preclipped=footprint is location,cache=memo if footprint is location else None)
  winner=next((c[4]['name'] for c in sorted(active,key=lambda c:(-c[1],c[3])) if c[5]==result['owner']),None)
  evidence={'owner_name':winner,'share':result['share'],'coverage':result['coverage'],'candidates':result['candidates'],'source_record_ids':[c[3] for c in active],'footprint':'dated' if footprint is not location else 'reference'}
  row=[a,b,result['owner'],result['status'],evidence]
  if rows and rows[-1][1]==a and rows[-1][2:]==row[2:]:rows[-1][1]=b
  else:rows.append(row)
 return rows

def id_of(value):return id(value)

def prepare(before_path,after_path,before_boundaries,after_boundaries,receipt_path,ownership,source,output,unknown_changed=False):
 ownership=ownership.resolve();source=source.resolve();output=output.resolve();wrapper_start_sha=sha(pathlib.Path(__file__))
 if output.exists():raise ValueError('Output must be a new staging directory')
 if output==ownership or output.is_relative_to(ownership) or ownership.is_relative_to(output) or output.is_relative_to(source):raise ValueError('Staging must be separate from immutable ownership/political sources')
 index=load(ownership/'index.json')
 if index.get('version')!=2:raise ValueError('Incremental preparation requires compact ownership-v2')
 helpers=exact_helpers(ownership,index);pi,chunks=checked_sources(source,index)
 before=feature_snapshot(before_path);after=before if before_path.resolve()==after_path.resolve() else feature_snapshot(after_path);bh=published_footprint_hash(before);ah=bh if before is after else published_footprint_hash(after)
 if index.get('footprints_sha256')!=bh or index['inputs'].get('footprints_sha256')!=bh:raise ValueError('Before snapshot does not match prepared ownership')
 bv,bvh,bvp=boundary_versions(before_boundaries,helpers.canonical,before);av,avh,avp=boundary_versions(after_boundaries,helpers.canonical,after)
 if index['inputs'].get('boundary_versions')!=bvh:raise ValueError('Before dated footprints do not match prepared ownership')
 reused,changed,removed,fingerprints=classify(before,after,bvp,avp,helpers.canonical);added=set(after)-set(before)
 receipt=load(receipt_path);receipt['_before_ids']=list(before);receipt['_after_ids']=list(after);check_receipt(receipt,bh,ah,changed,removed,added)
 old_order=sorted(before);new_order=sorted(after);old_positions={id:i for i,id in enumerate(old_order)};new_positions={id:i for i,id in enumerate(new_order)}
 for entry in index['parts']+index['evidence_parts']:
  if sha(safe_path(ownership,entry['path']))!=entry['sha256']:raise ValueError('Original ownership asset hash mismatch')
 output.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='ownership-incremental-',dir=output.parent) as temporary:
  work=pathlib.Path(temporary);db=sqlite3.connect(work/'lookup.sqlite');db.executescript('PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF; CREATE TABLE location(id TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE evidence(id INTEGER PRIMARY KEY,value TEXT UNIQUE NOT NULL);')
  dictionary=copy.deepcopy(index);offset=0
  for entry in index['evidence_parts']:
   rows=load(ownership/entry['path']);validate_evidence(rows,index)
   db.executemany('INSERT INTO evidence VALUES(?,?)',((offset+i,dump(v)) for i,v in enumerate(rows)));offset+=len(rows)
  if offset!=index['evidence_records']:raise ValueError('Original evidence count mismatch')
  original_intervals=0;kept_intervals=0;removed_parts=[];oldseen=set();statuses=collections.Counter();staged_parts=[]
  for n,entry in enumerate(index['parts']):
   rows=load(ownership/entry['path']);kept=[];archived=[]
   for id,intervals in rows:
    if id not in before or id in oldseen:raise ValueError('Original location identity coverage mismatch')
    oldseen.add(id);original_intervals+=len(intervals)
    validate_compact(intervals,index,offset)
    if id in reused:
     kept.append([id,intervals]);kept_intervals+=len(intervals);statuses.update(index['statuses_order'][r[3]] for r in intervals)
     db.execute('INSERT INTO location VALUES(?,?)',(id,dump(intervals)))
    else:archived.append([id,intervals])
   if kept:
    name='reuse-'+str(n)+'.json.gz';path=work/name
    if len(kept)==len(rows):shutil.copyfile(ownership/entry['path'],path);part={'path':name,'sha256':sha(path),'locations':len(kept),'reused_original_sha256':entry['sha256']}
    else:part={**write_gzip(path,kept),'locations':len(kept)}
    staged_parts.append(part)
   if archived:removed_parts.append({**write_gzip(work/('archive-'+str(n)+'.json.gz'),archived),'locations':len(archived)})
   del rows;db.commit();print('Validated/reused original part',n+1,'of',len(index['parts']),flush=True)
  if oldseen!=set(before) or original_intervals!=index['intervals']:raise ValueError('Original records do not exhaustively match before snapshot')
  owners={v:i for i,v in enumerate(dictionary['owner_ids'])};labels={v:i for i,v in enumerate(dictionary['labels'])};sources={v:i for i,v in enumerate(dictionary['source_ids'])}
  def intern(value,items,lookup):
   if value not in lookup:lookup[value]=len(items);items.append(value)
   return lookup[value]
  def encode(rows):
   nonlocal offset
   result=[]
   for a,b,owner,status,m in rows:
    if owner and owner not in owners:raise ValueError('Changed sources introduced an unverified owner identity')
    e=[intern(m['owner_name'],dictionary['labels'],labels) if m['owner_name'] else None,m['share'],m['coverage'],[[owners[c],s] for c,s in m['candidates']],[intern(rid,dictionary['source_ids'],sources) for rid in m['source_record_ids']],1 if m['footprint']=='dated' else 0];raw=dump(e);found=db.execute('SELECT id FROM evidence WHERE value=?',(raw,)).fetchone()
    if found:ei=found[0]
    else:ei=offset;db.execute('INSERT INTO evidence VALUES(?,?)',(offset,raw));offset+=1
    result.append([a,b,owners[owner] if owner else None,index['statuses_order'].index(status),ei])
   return result
  derived_count=0;source_records=0
  if unknown_changed:
   for id in sorted(changed):db.execute('INSERT INTO location VALUES(?,?)',(id,'[]'))
   if changed:staged_parts.append({**write_gzip(work/'unknown-changed.json.gz',[[id,[]] for id in sorted(changed)]),'locations':len(changed)})
  elif changed:
   geos,totals,source_records=measure_changed(changed,after,av,source,chunks,helpers,db)
   expected_ids={row[0] for row in db.execute('SELECT id FROM source')};listed_ids={r['id'] for r in pi['records']}
   if expected_ids!=listed_ids:raise ValueError('Political source chunk/index identity coverage mismatch')
   if any(owner not in owners for owner, in db.execute('SELECT DISTINCT owner FROM source')):raise ValueError('Source owner dictionary changed')
   batch=[]
   for id in sorted(changed):
    rows=encode(derive_location(id,geos[id],totals[id],av[id],helpers,db));validate_compact(rows,dictionary,offset);db.execute('INSERT INTO location VALUES(?,?)',(id,dump(rows)));derived_count+=len(rows);statuses.update(index['statuses_order'][r[3]] for r in rows);batch.append([id,rows])
    if len(batch)==1500:staged_parts.append({**write_gzip(work/('changed-'+str(len(staged_parts))+'.json.gz'),batch),'locations':len(batch)});batch=[];db.commit()
   if batch:staged_parts.append({**write_gzip(work/('changed-'+str(len(staged_parts))+'.json.gz'),batch),'locations':len(batch)})
  db.commit()
  if {id for id, in db.execute('SELECT id FROM location')}!=set(after):raise ValueError('Staged records lack exhaustive after-location coverage')
  # Exact unchanged tuples and unchanged evidence indices are checked exhaustively.
  for entry in index['parts']:
   for id,rows in load(ownership/entry['path']):
    if id in reused and db.execute('SELECT value FROM location WHERE id=?',(id,)).fetchone()[0]!=dump(rows):raise ValueError('Reused record-byte equivalence failed')
  evidence_parts=list(copy.deepcopy(index['evidence_parts']))
  for entry in evidence_parts:shutil.copyfile(ownership/entry['path'],work/entry['path'])
  for start in range(index['evidence_records'],offset,20000):
   rows=[json.loads(v) for v, in db.execute('SELECT value FROM evidence WHERE id>=? AND id<? ORDER BY id',(start,min(start+20000,offset)))];evidence_parts.append(write_gzip(work/('incremental-evidence-'+str(start)+'.json.gz'),rows))
  proof_dir=work/'algorithms';shutil.copytree(ownership/'algorithms',proof_dir);generation=sha(receipt_path)[:16]+'-'+wrapper_start_sha[:16];wrapper=proof_dir/('incremental/'+generation+'/prepare-ownership-incremental.py');wrapper.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(__file__,wrapper)
  for file in ['candidate-recovery.json','threshold-refinement.json']:
   if (ownership/file).exists():shutil.copyfile(ownership/file,work/file)
  mapping=[[id,old_positions.get(id),new_positions.get(id),'reused' if id in reused else 'removed' if id in removed else 'added' if id in added else 'changed',fingerprints['before'].get(id),fingerprints['after'].get(id)] for id in sorted(set(before)|set(after))]
  mapping_part=write_gzip(work/'location-identity-map.json.gz',mapping)
  archive={'original_index_sha256':sha(ownership/'index.json'),'original_index':index,'parts':removed_parts,'rule':'Lineage-only preservation. No owner/history assignment transfers from removed or changed IDs.'};(work/'archive-index.json').write_text(dump(archive))
  previous=index.get('incremental_preparation',{});previous_names=['prior-archives','migration-receipt.json','location-identity-map.json.gz']
  if previous.get('archive_path'):
   previous_names.append(previous['archive_path']);previous_names.extend(p['path'] for p in load(safe_path(ownership,previous['archive_path']))['parts'])
  retained_archives=retain_prior_archives(ownership,work,index,previous_names)
  dictionary.update(parts=staged_parts,evidence_parts=evidence_parts,evidence_records=offset,locations=len(after),intervals=kept_intervals+derived_count,statuses=dict(statuses),footprints_sha256=ah)
  dictionary['inputs']['footprints_sha256']=ah;dictionary['inputs']['boundary_versions']=avh
  dictionary['incremental_preparation']={'version':1,'original_index_sha256':sha(ownership/'index.json'),'wrapper':{'path':wrapper.relative_to(work).as_posix(),'sha256':sha(wrapper)},'migration_receipt_sha256':sha(receipt_path),'before_footprints_sha256':bh,'after_footprints_sha256':ah,'before_boundary_versions_sha256':bvh,'after_boundary_versions_sha256':avh,'identity_map':mapping_part,'reused_locations':len(reused),'changed_locations':len(changed-added),'added_locations':len(added),'removed_locations':len(removed),'reused_intervals':kept_intervals,'derived_intervals':derived_count,'source_records_scanned':source_records,'unknown_changed':bool(unknown_changed),'reused_row_bytes_exhaustively_verified':True,'archive_path':'archive-index.json','execution_note':'Original executed algorithm receipts remain immutable; only changed/new IDs are derived or explicitly unresolved. Direct attribute evidence is not migrated or overwritten.'}
  dictionary['incremental_preparation']['retained_prior_archives']=retained_archives
  for entry in staged_parts+evidence_parts:
   if sha(work/entry['path'])!=entry['sha256']:raise ValueError('Staged asset checksum mismatch')
  if sha(wrapper)!=wrapper_start_sha or sha(pathlib.Path(__file__))!=wrapper_start_sha:raise ValueError('Incremental executable changed during preparation')
  for entry in index['execution_algorithms']:
   if sha(work/entry['path'])!=entry['sha256']:raise ValueError('Executed source algorithm changed during preparation')
  for entry in index['parts']+index['evidence_parts']:
   if sha(safe_path(ownership,entry['path']))!=entry['sha256']:raise ValueError('Original source asset changed during preparation')
  checked_sources(source,index)
  if published_footprint_hash(feature_snapshot(before_path))!=bh or published_footprint_hash(feature_snapshot(after_path))!=ah:raise ValueError('Snapshot footprints changed during preparation')
  if boundary_versions(before_boundaries,helpers.canonical,before)[1]!=bvh or boundary_versions(after_boundaries,helpers.canonical,after)[1]!=avh:raise ValueError('Dated footprint input changed during preparation')
  if sha(receipt_path)!=dictionary['incremental_preparation']['migration_receipt_sha256'] or sha(ownership/'index.json')!=dictionary['incremental_preparation']['original_index_sha256']:raise ValueError('Source/migration receipt changed during preparation')
  (work/'index.json').write_text(dump(dictionary));shutil.copyfile(receipt_path,work/'migration-receipt.json');db.close();(work/'lookup.sqlite').unlink();shutil.copytree(work,output)
 return dictionary

def validate_evidence(rows,index):
 import math
 for e in rows:
  if not isinstance(e,list) or len(e)!=6:raise ValueError('Invalid compact evidence tuple')
  label,share,coverage,claims,records,dated=e
  if label is not None and (type(label)!=int or not 0<=label<len(index['labels'])):raise ValueError('Invalid evidence label index')
  if any(type(x) not in [int,float] or not math.isfinite(x) or not 0<=x<=1 for x in [share,coverage]):raise ValueError('Invalid evidence area share')
  if any(type(c[0])!=int or not 0<=c[0]<len(index['owner_ids']) or type(c[1]) not in [int,float] or not math.isfinite(c[1]) or not 0<=c[1]<=1 for c in claims):raise ValueError('Invalid evidence owner/share')
  if any(type(i)!=int or not 0<=i<len(index['source_ids']) for i in records) or dated not in [0,1]:raise ValueError('Invalid evidence source index/footprint flag')

def validate_compact(rows,index,evidence_count):
 previous=None
 for row in rows:
  if not isinstance(row,list) or len(row)!=5:raise ValueError('Invalid compact interval tuple')
  a,b,o,s,e=row
  if type(a)!=int or type(b)!=int or a==0 or b==0 or a>=b or a<index['valid_from'] or b>index['valid_to']:raise ValueError('Invalid compact date interval')
  if previous is not None and a<previous:raise ValueError('Overlapping dated ownership intervals')
  if o is not None and (type(o)!=int or not 0<=o<len(index['owner_ids'])):raise ValueError('Invalid compact owner index')
  if type(s)!=int or not 0<=s<len(index['statuses_order']) or type(e)!=int or not 0<=e<evidence_count:raise ValueError('Invalid compact evidence/status index')
  if (index['statuses_order'][s]=='derived')!=(o is not None):raise ValueError('Resolved owner disagrees with ownership status')
  previous=b

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ['before','after','before-boundaries','after-boundaries','receipt','output']:parser.add_argument('--'+name,type=pathlib.Path,required=True)
 parser.add_argument('--ownership',type=pathlib.Path,default=ROOT/'data/ownership-history');parser.add_argument('--source',type=pathlib.Path,default=ROOT/'data/cliopatria');parser.add_argument('--unknown-changed',action='store_true',help='Keep changed/new ownership unknown, retaining predecessor evidence without spatial derivation');args=parser.parse_args()
 result=prepare(args.before,args.after,args.before_boundaries,args.after_boundaries,args.receipt,args.ownership,args.source,args.output,args.unknown_changed)
 print(dump(result['incremental_preparation']))

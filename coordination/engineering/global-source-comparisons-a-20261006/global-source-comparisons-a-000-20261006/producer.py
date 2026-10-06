import pathlib,json,gzip,hashlib,subprocess,collections,time,math,platform,gc
import argparse,io,tarfile,zipfile
import shapely
from shapely import STRtree,union_all
from shapely.geometry import shape,mapping
from shapely.errors import GEOSException
parser=argparse.ArgumentParser();parser.add_argument('--repo',required=True);parser.add_argument('--producer-commit',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
R=pathlib.Path(args.repo).resolve();PACKET=pathlib.Path(__file__).resolve().parent;PREFIX=str(PACKET.relative_to(R));PRODUCER=args.producer_commit
assert len(PRODUCER)==40 and all(c in '0123456789abcdef' for c in PRODUCER)
assert subprocess.check_output(['git','show',PRODUCER+':'+PREFIX+'/producer.py'],cwd=R)==pathlib.Path(__file__).read_bytes()
O=pathlib.Path(args.output).resolve();O.mkdir(parents=True,exist_ok=False)
HEAD='a26f8d8b50e7349054b86e70d1e6e552a9a2b0fd';I='c6a26e1caba54e1b81a89fbda3a64fff56da323d';M='79ffb2ed04702e16f009e4675a8d74ef9bd09d4f';H='549cc2a863d4a487a662c2613e4d02888e39b5ba';S='7c7cdf2388e0e7200b937c2cfb440b53165d9d98';SP='coordination/engineering/worldwide-successor-1215-20261006/run-one/'
assert platform.python_version()=='3.12.14'and shapely.__version__=='2.1.2'and shapely.geos_version_string=='3.13.1'
def canon(v):return (json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
proc=subprocess.Popen(['git','cat-file','--batch'],cwd=R,stdin=subprocess.PIPE,stdout=subprocess.PIPE);pins=[]
def frozen(path):
 full=PREFIX+'/'+path;tree=subprocess.check_output(['git','ls-tree',PRODUCER,'--',full],cwd=R);assert tree.split()[0] in (b'100644',b'100755')
 proc.stdin.write((PRODUCER+':'+full+'\n').encode());proc.stdin.flush();h=proc.stdout.readline().split();assert h[1]==b'blob';b=proc.stdout.read(int(h[2]));assert len(b)==int(h[2]) and proc.stdout.read(1)==b'\n';pins.append({'commit':PRODUCER,'path':full,'bytes':len(b),'sha256':sha(b),'git_blob_oid':h[0].decode(),'mode':tree.split()[0].decode()});return b
import sys
helper_path=R/'scripts/evidence/immutable.py';helper_bytes=subprocess.check_output(['git','show',PRODUCER+':scripts/evidence/immutable.py'],cwd=R)
assert helper_path.read_bytes()==helper_bytes and sha(helper_bytes)=='b7ff607b7774595788396e94f08fc29d750e4032624eb93732a5735c1ddcf7fd'
sys.path.insert(0,str(R/'scripts'));from evidence.immutable import deterministic_gzip
pins.append({'commit':PRODUCER,'path':'scripts/evidence/immutable.py','bytes':len(helper_bytes),'sha256':sha(helper_bytes),'role':'actual imported preparation helper'})
aliases=json.loads(frozen('input-aliases.json'))['aliases'];alias_map={(p['original_commit'],p['original_path']):p for p in aliases};assert len(alias_map)==len(aliases)
def git(commit,path):
 p=alias_map[(commit,path)];b=frozen(p['owned_path']);assert len(b)==p['original_pin']['bytes'] and sha(b)==p['original_pin']['sha256'];return b

def decode(b,pin=None):
 if pin:assert len(b)==pin['bytes']and sha(b)==pin['sha256']
 raw=gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b
 if pin and 'uncompressed_sha256'in pin:assert len(raw)==pin['uncompressed_bytes']and sha(raw)==pin['uncompressed_sha256']
 return json.loads(raw)
cohortraw=frozen('scope.json');scope=json.loads(cohortraw);family_ids=set(scope['complete_family_ids']);targets={};families=[]
report=decode(git(HEAD,'coordination/engineering/worldwide-native-batches-1184-20261006/current-run-one/report.json'))
for pin in report['outputs']['current-batches']:
 for f in decode(git(HEAD,pin['path']),pin):
  if f['id'] in family_ids:
   assert len(f['component_ids'])==f['component_count'] and f['component_ids']==sorted(set(f['component_ids'])) and sha(canon(f['component_ids']))==f['component_ids_sha256'];families.append(f)
   for i in f['component_ids']:assert i not in targets;targets[i]=f
assert {f['id']for f in families}==family_ids and sorted(targets)==scope['complete_component_ids']
expected_families=len(families);expected_components=len(targets);source_ids=sorted({f['source_id'] for family in families for f in family['source_families']});assert source_ids==scope['source_ids']
registryraw=git(M,'data/administrative-sources.json');registry=json.loads(registryraw)
historical_sources=json.loads(gzip.decompress(frozen('historical-source-bindings.json.gz')));catalogue=json.loads(frozen('source-catalogue.json'));source_catalogue={p['key']:p for p in catalogue['products']}
if 'gb:IND:ADM3' in source_ids:registry['gb:IND:ADM3']=decode(git(M,'data/global-sources/IND-ADM3-metadata.json'))
# Exact raw source IDs map to recorded stable subjects through accepted full
# metadata, including aliases; no nearest or newly invented assignment.
contextreport=decode(git(H,'coordination/engineering/worldwide-contexts-1184-20261006/run-one/report.json'));subjectmap=collections.defaultdict(list)
for pin in contextreport['outputs']:
 for c in decode(git(H,pin['path']),pin):
  meta=c['original_metadata'];key=(meta.get('source_id'),meta.get('original_id'))
  if key[0]in source_ids and key[1]is not None:subjectmap[key].append({'id':c['id'],'original_feature_sha256':c['original_feature_sha256'],'reference_year':meta.get('reference_year'),'original_parent_id':c['original_parent_id']})
# Supplemental refinement aggregation joins only explicitly recorded source_member_ids.
  if meta.get('source_id')=='gb:IND:ADM3' and 'gb:IND:ADM3' in source_ids:
   assert meta.get('source_geography_sha256')=='4ea6807d0a0c5aac0b46ee8e31ed7c30fbec273b44345bba1e4a2bb5f299f5fb'
   for member in meta.get('source_member_ids',[]):
    subjectmap[('gb:IND:ADM3',member)].append({'id':c['id'],'original_feature_sha256':c['original_feature_sha256'],'reference_year':meta.get('reference_year'),'original_parent_id':c['original_parent_id'],'binding_recipe':'explicit-refinement-source_member_ids'})
products={};source_receipts=[]
for sid in source_ids:
 p=historical_sources[sid]['complete_source'];product=source_catalogue[sid];parts=[];offset=0
 for part in product['parts']:
  encoded=git('1c4b606d35614bd7c4990bb9da1098fa181c7fe8',part['path']);assert len(encoded)==part['bytes'] and sha(encoded)==part['sha256'];body=gzip.decompress(encoded)
  assert part['offset']==offset and len(body)==part['uncompressed_bytes'] and sha(body)==part['uncompressed_sha256'];parts.append(body);offset+=len(body)
 raw=b''.join(parts);assert len(raw)==product['original_bytes'] and sha(raw)==product['original_sha256'];del parts
 assert len(raw)==p['bytes']and sha(raw)==p['sha256']==registry[sid]['sha256'];v=json.loads(raw);assert v['type']=='FeatureCollection'and len(v['features'])==p['feature_count']
 geoms=[];rows=[];invalid=[]
 for n,f in enumerate(v['features']):
  props=f.get('properties',{});shapeid=props.get('shapeID');g=shape(f['geometry']);valid=g.is_valid and g.geom_type in ('Polygon','MultiPolygon')and not g.is_empty
  if not valid:invalid.append({'feature_index':n,'shapeID':shapeid,'geometry_type':g.geom_type,'is_valid':g.is_valid,'is_empty':g.is_empty})
  rows.append({'feature_index':n,'shapeID':shapeid,'feature_sha256':sha(canon(f)),'geometry_sha256':sha(canon(f['geometry'])),'recorded_stable_subjects':subjectmap.get((sid,shapeid),[]),'valid_polygon':valid});geoms.append(g)
 products[sid]={'geometries':geoms,'rows':rows,'tree':STRtree(geoms)}
 assert canon(rows)==canon(historical_sources[sid]['complete_features']) and canon(invalid)==canon(historical_sources[sid]['invalid_features']) and canon(registry[sid])==canon(historical_sources[sid]['registry_entry'])
 source_receipts.append({'source_id':sid,'original_raw_source_sha256':product['original_sha256'],'complete_feature_count':len(rows),'invalid_feature_count':len(invalid),'authenticated_complete_feature_bindings':'historical-source-bindings.json.gz','complete_source_binding_sha256':sha(canon(historical_sources[sid]))});print('full product indexed',sid,len(rows),'invalid',len(invalid),flush=True)
 del v,raw;gc.collect()
# Every initial cohort current component is a retained full original pointset.
inventory=decode(git(I,'coordination/engineering/worldwide-inventory-1164-20261006/run-one/report.json'));successor=decode(git(S,SP+'report.json'));spins={p['path']:p for p in successor['products']};cd=decode(git(S,SP+'components-delta.json.gz'),spins['components-delta.json.gz']);assert not set(targets)&set(cd['removed_ids']);current_upserts={f['id']:f for f in cd['upsert_records'] if f['id']in targets}
features={}
for pin in inventory['complete_products']['components']:
 path=next(p['path']for p in inventory['source_descriptors']if p['sha256']==pin['sha256']);b=git(M,path);collection=decode(b,pin);assert collection['type']=='FeatureCollection'
 for f in collection['features']:
  if f['id']in targets and f['id']not in current_upserts:assert f['id']not in features;features[f['id']]=f
features.update(current_upserts);assert set(features)==set(targets)
# Confirm exact accepted current family contents, not a hand-selected easy subset.
report=decode(git(HEAD,'coordination/engineering/worldwide-native-batches-1184-20261006/current-run-one/report.json'));actual_families={}
for pin in report['outputs']['current-batches']:
 for row in decode(git(HEAD,pin['path']),pin):
  if row['id']in {f['id']for f in families}:actual_families[row['id']]=row
assert all(canon(f)==canon(actual_families[f['id']])for f in families)
source_receipt_path=O/'complete-source-inputs.json.gz';source_receipt_path.write_bytes(deterministic_gzip(canon({'source_products':source_receipts,'actual_executed_input_pins':pins,'cohort_sha256':sha(cohortraw),'producer_commit':PRODUCER,'source_custody':'exact original raw aliases; complete_source fields preserve historical first-execution bindings and are not current consumed containing files'})))
outputs=[];batch=[];size=0;counts=collections.Counter();family_summary={};start=time.monotonic();processed=[];validity=collections.Counter()
def flush():
 global batch,size
 if not batch:return
 raw=canon(batch);p=O/('components-%03d.json.gz'%len(outputs));assert not p.exists();b=deterministic_gzip(raw);p.write_bytes(b);outputs.append({'path':str(p.relative_to(O)),'bytes':len(b),'sha256':sha(b),'decoded_bytes':len(raw),'decoded_sha256':sha(raw),'rows':len(batch)});batch=[];size=0

def geometry(g):return {'geometry':mapping(g),'geometry_sha256':sha(canon(mapping(g))),'geometry_type':g.geom_type,'is_empty':g.is_empty,'is_valid':g.is_valid,'planar_area_coordinate_units_squared':g.area,'planar_length_coordinate_units':g.length}
object_seen={};object_pins=[];object_buffer=[];object_size=0
objectdir=O/'source-union-objects';objectdir.mkdir(exist_ok=True)
def flush_objects():
 global object_buffer,object_size
 if not object_buffer:return
 raw=canon(object_buffer);p=objectdir/('objects-%04d.json.gz'%len(object_pins));assert not p.exists();b=deterministic_gzip(raw);p.write_bytes(b);object_pins.append({'path':str(p.relative_to(O)),'bytes':len(b),'sha256':sha(b),'decoded_bytes':len(raw),'decoded_sha256':sha(raw),'objects':len(object_buffer)});object_buffer=[];object_size=0
def preserve_union_object(value):
 global object_size
 body=canon(value);h=sha(body)
 if h not in object_seen:
  if len(body)>8*1024*1024:
   flush_objects();parts=[]
   for startbyte in range(0,len(body),8*1024*1024):
    part=body[startbyte:startbyte+8*1024*1024];p=objectdir/(h+'-part-%03d.bin'%len(parts));assert not p.exists();p.write_bytes(part);parts.append({'path':str(p.relative_to(O)),'bytes':len(part),'sha256':sha(part)})
   object_seen[h]={'geometry_sha256':h,'decoded_bytes':len(body),'codec':'canonical-json-exact-byte-fragments','parts':parts}
  else:
   row={'geometry_sha256':h,'geometry':value};n=len(canon(row))
   if object_buffer and object_size+n>8*1024*1024:flush_objects()
   object_buffer.append(row);object_size+=n;object_seen[h]={'geometry_sha256':h,'decoded_bytes':len(body),'codec':'canonical-json-object-in-indexed-shard'}
 return {'geometry_object_sha256':h,'canonical_geometry_bytes':len(body),'object_index':'source-union-object-index.json'}
historical_rows=json.loads(gzip.decompress(frozen('historical-original-rows.json.gz')));historical_by_id={v['component']:v for v in historical_rows};assert set(historical_by_id)==set(targets) and len(historical_by_id)==len(historical_rows)
# Exact original cohort/row order retains the measured ordinary capsule layout.
# This changes transport order only; every original pointset operation is preserved.
for binding in historical_rows:
 i=binding['component']
 f=features[i];family=targets[i];g=shape(f['geometry']);sources=sorted({x['source_id']for x in family['source_families']});row={'component':i,'family':family['id'],'source_products':sources,'original_component_commit':(None if i in current_upserts else M),'current_component_source_successor':S,'current_component_relation':('current-successor-upsert-full-feature-pointset' if i in current_upserts else 'retained-full-original-feature-pointset'),'full_component_feature_sha256':sha(canon(f)),'component_geometry_sha256':sha(canon(f['geometry'])),'dateline_connected':f['properties'].get('dateline_connected'),'coordinate_scope':'literal original GeoJSON lon/lat pointsets; no periodic wrapping, coordinate snapping, datum transformation or normalization','positive_area_feature_ids':[],'zero_area_feature_ids':[],'feature_intersections':[],'unknowns':[],'surface_status':'unverified','administrative_assignment':None,'cause_status':'unknown'}
 fs=family_summary.setdefault(family['id'],{'id':family['id'],'sources':sources,'best_rank':family['best_rank'],'expected_components':family['component_count'],'processed_components':0,'statuses':collections.Counter(),'positive_source_components':0,'uniquely_covered_recorded_subject_components':0,'existing_related_issues':family['existing_related_issues']});candidates=[];valid_geoms=[];queryrows=[]
 try:
  if not g.is_valid or g.is_empty or g.geom_type not in ('Polygon','MultiPolygon'):raise ValueError('invalid-empty-or-nonpolygon-component')
  for sid in sources:
   product=products[sid];indices=sorted(int(n)for n in product['tree'].query(g));queryrows.append({'source_id':sid,'whole_product_feature_count':len(product['rows']),'complete_bbox_candidate_indices':indices})
   for n in indices:
    meta=product['rows'][n];sg=product['geometries'][n];binding={'source_id':sid,**meta}
    if not meta['valid_polygon']:row['unknowns'].append({'status':'invalid-source-feature-in-query-envelope','binding':binding});continue
    valid_geoms.append(sg);ix=g.intersection(sg);full=sg.covers(g);descriptor={'binding':binding,'intersection':geometry(ix),'source_feature_covers_entire_component':full}
    row['feature_intersections'].append(descriptor)
    if not ix.is_empty:
     name={'source_id':sid,'feature_index':n,'shapeID':meta['shapeID'],'recorded_stable_subject_ids':[x['id']for x in meta['recorded_stable_subjects']]}
     if ix.area>0:row['positive_area_feature_ids'].append(name);candidates.append(descriptor)
     else:row['zero_area_feature_ids'].append(name)
  row['whole_product_bbox_queries']=queryrows
  if row['unknowns']:row['status']='unknown-invalid-source-candidate';row['component_geometry']=mapping(g)
  else:
   u=union_all(valid_geoms);ix=g.intersection(u);diff=g.difference(u);row['whole_relevant_source_union']=geometry(u);row['source_union_intersection']=geometry(ix);row['component_minus_source_union']=geometry(diff)
   validity['union_valid'if u.is_valid else'union_invalid']+=1;validity['intersection_valid'if ix.is_valid else'intersection_invalid']+=1;validity['difference_valid'if diff.is_valid else'difference_invalid']+=1
   if not(u.is_valid and ix.is_valid and diff.is_valid):row['status']='unknown-invalid-operation-output'
   elif ix.area==0:row['status']='zero-area-contact-only'if not ix.is_empty else'no-source-intersection-in-literal-domain'
   else:
    fs['positive_source_components']+=1
    unique=len(candidates)==1 and candidates[0]['source_feature_covers_entire_component'];subject=None
    if unique:
     b=candidates[0]['binding'];subjects=b['recorded_stable_subjects'];compatible=[s for s in subjects if s['reference_year']==registry[b['source_id']]['boundaryYearRepresented']]
     if len(subjects)==len(compatible)==1:subject=subjects[0]
    row['uniquely_covering_compatible_recorded_subject']=subject
    if subject:row['status']='one-compatible-recorded-subject-uniquely-covers-component';fs['uniquely_covered_recorded_subject_components']+=1
    else:row['status']='positive-source-coverage-mixed-partial-or-subject-unresolved'
 except (GEOSException,ValueError,TypeError,OverflowError)as e:
  row['status']='unknown-component-or-intersection-operation';row['unknowns'].append({'exception':type(e).__name__,'message':str(e)});row['component_geometry']=f['geometry'];row['whole_product_bbox_queries']=queryrows
 if 'whole_relevant_source_union' in row:
  descriptor=row['whole_relevant_source_union'];assert sha(canon(descriptor['geometry']))==descriptor['geometry_sha256'];descriptor['geometry']=preserve_union_object(descriptor['geometry'])
 counts[row['status']]+=1;fs['processed_components']+=1;fs['statuses'][row['status']]+=1;processed.append(i);b=canon(row)
 if batch and size+len(b)>8*1024*1024:flush()
 batch.append(row);size+=len(b)
 if len(processed)%250==0:
  (O/'checkpoint.json').write_bytes(canon({'processed':len(processed),'expected':expected_components,'complete_processed_ids_sha256':sha(canon(processed)),'counts':dict(counts),'outputs':outputs,'elapsed_seconds':time.monotonic()-start}));print('processed',len(processed),dict(counts),'elapsed',round(time.monotonic()-start,1),flush=True)
flush();flush_objects();objectindex=O/'source-union-object-index.json';objectindex.write_bytes(canon({'objects':object_seen,'shards':object_pins,'lossless_scope':'Only exact canonical union geometry objects deduplicated; intersections/differences/full per-feature intersection records preserved unchanged.'}));assert len(processed)==expected_components and set(processed)==set(targets)
for fs in family_summary.values():assert fs['processed_components']==fs['expected_components'];fs['statuses']=dict(fs['statuses'])
ordered=sorted(family_summary.values(),key=lambda f:(f['best_rank']['measured_impact'],f['id']));receipt={'status':'complete-explicit-additive-direct-source-geometry-coverage-screen','cohort_sha256':sha(cohortraw),'complete_families':expected_families,'complete_components':expected_components,'current_successor_upsert_components':sorted(current_upserts),'source_products':source_ids,'component_roster_sha256':sha(canon(sorted(targets))),'counts':dict(counts),'output_validity':dict(validity),'elapsed_seconds':time.monotonic()-start,'outputs':outputs,'complete_family_results':ordered,'source_input_receipt':{'path':str(source_receipt_path.relative_to(O)),'bytes':source_receipt_path.stat().st_size,'sha256':sha(source_receipt_path.read_bytes())},'source_union_object_index':{'path':str(objectindex.relative_to(O)),'bytes':objectindex.stat().st_size,'sha256':sha(objectindex.read_bytes())},'frozen_initial_kernel_sha256':sha(frozen('historical/screen.py')),'script_sha256':sha(pathlib.Path(__file__).read_bytes()),'producer_commit':PRODUCER,'package':scope['package'],'software':{'python':platform.python_version(),'shapely':shapely.__version__,'geos':shapely.geos_version_string},'limits':['Screen against whole consumed products using all bbox-candidate features, never just contacting subjects. Bounding-box-disjoint features cannot contribute to a literal-coordinate component intersection.','Country/product union extent is consumed input coverage, not actual dated land/water or legal boundary authority.','Full source and component pointsets preserved; no cutoffs, snapping, MakeValid, normalization or fill.','No periodic longitude wrapping performed; dateline interpretation remains an explicit separate limit.','One recorded compatible stable subject is observed source-geometry attribution, not administrative or ownership approval.','Source coverage does not identify exact historical execution cause or prove a safe repair.','Only this complete frozen package processed. Original eight historical cohorts each had one private-SHA scientific execution; new committed executions do not rewrite that provenance. Supplemental India source is distinct from original367administrative registry.']};p=O/'receipt.json';p.write_bytes(canon(receipt));print(json.dumps({'status':receipt['status'],'receipt':str(p),'counts':dict(counts),'elapsed_seconds':receipt['elapsed_seconds']}),flush=True);proc.terminate();proc.wait()

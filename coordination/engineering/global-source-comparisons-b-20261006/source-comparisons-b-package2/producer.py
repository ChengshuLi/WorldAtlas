"""Complete frozen literal-coordinate source comparisons; no repair or assignment."""
import pathlib,json,gzip,hashlib,subprocess,collections,time,math,platform,gc,argparse,datetime
import shapely
from shapely import STRtree,union_all
from shapely.geometry import shape,mapping
from shapely.errors import GEOSException
CASE=pathlib.Path(__file__).resolve().parent;R=CASE.parents[3]
parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--code-commit',required=True);args=parser.parse_args()
started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
O=pathlib.Path(args.output);assert not O.exists();O.mkdir(parents=True)
def canon(v):return (json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def verify_complete_roster(actual,expected):
 assert len(actual)==len(set(actual)) and sorted(actual)==sorted(expected),'duplicate or omitted complete member'
def verify_historical_row(row,expected_sha):
 assert sha(canon(row))==expected_sha,'historical scientific mismatch'
def authenticate(path):
 rel=str(path.relative_to(R));tree=subprocess.check_output(['git','ls-tree',args.code_commit,'--',rel],cwd=R);assert tree.split()[0]in(b'100644',b'100755')
 assert subprocess.check_output(['git','show',args.code_commit+':'+rel],cwd=R)==path.read_bytes(),rel
for name in ('producer.py','input-config.json','scope.json'):authenticate(CASE/name)
config=json.loads((CASE/'input-config.json').read_bytes());scope_raw=(CASE/'scope.json').read_bytes();assert sha(scope_raw)==config['scope_sha256'];scope=json.loads(scope_raw)
HEAD=config['native_snapshot_commit'];I=config['inventory_commit'];M=config['original_components_commit'];H=config['original_contexts_commit'];S=config['current_component_successor_commit'];SP='coordination/engineering/worldwide-successor-1215-20261006/run-one/'
assert platform.python_version()=='3.12.14'and shapely.__version__=='2.1.2'and shapely.geos_version_string=='3.13.1'
pins=[];aliases={(p['commit'],p['path']):p for p in config['immutable_aliases']}
def read_alias(p):
 path=CASE/p['alias'];assert path.is_file()and not path.is_symlink();authenticate(path);b=path.read_bytes();assert len(b)==p['bytes']and sha(b)==p['sha256'];raw=gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b;assert max(len(b),len(raw))<=32*1024*1024
 return b
# Original ordinary-file relation is retained; future execution reads exact aliases.
def git(commit,path):
 p=aliases[(commit,path)];b=read_alias(p);raw=gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b;assert len(raw)==p['decoded_bytes']and sha(raw)==p['decoded_sha256'];pins.append(p);return b
def decode(b,pin=None):
 if pin:assert len(b)==pin['bytes']and sha(b)==pin['sha256']
 raw=gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b
 if pin and 'uncompressed_sha256'in pin:assert len(raw)==pin['uncompressed_bytes']and sha(raw)==pin['uncompressed_sha256']
 return json.loads(raw)
report=decode(git(HEAD,'coordination/engineering/worldwide-native-batches-1184-20261006/current-run-one/report.json'));families=[]
for pin in report['outputs']['current-batches']:
 for row in decode(git(HEAD,pin['path']),pin):
  if row['id']in set(scope['complete_family_ids']):families.append(row)
assert len(families)==config['complete_families']and len({f['id']for f in families})==len(families)
targets={}
for f in families:
 assert f['component_ids']==sorted(set(f['component_ids']))and len(f['component_ids'])==f['component_count']and sha(canon(f['component_ids']))==f['component_ids_sha256']
 for i in f['component_ids']:assert i not in targets;targets[i]=f
verify_complete_roster(list(targets),scope['complete_component_ids']);assert len(targets)==config['complete_components']
expected_families=len(families);expected_components=len(targets);source_ids=sorted({x['source_id']for f in families for x in f['source_families']});assert source_ids==scope['source_ids']
cohortraw=scope_raw;cohortpath=CASE/'scope.json';registryraw=git(M,'data/administrative-sources.json');registry=json.loads(registryraw)
if 'gb:IND:ADM3' in source_ids:registry['gb:IND:ADM3']=decode(git(M,'data/global-sources/IND-ADM3-metadata.json'))
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
historical_sources={}
for p in config['historical_source_bindings']:
 b=read_alias(p);raw=gzip.decompress(b);assert sha(raw)==p['decoded_sha256']and len(raw)==p['decoded_bytes']
 for row in json.loads(raw):assert row['source_id']not in historical_sources;historical_sources[row['source_id']]=row
for product in sorted(config['source_products'],key=lambda p:p['key']):
 sid=product['key'];parts=[];offset=0
 for p in product['parts']:
  b=read_alias(p);raw=gzip.decompress(b);assert len(raw)==p['uncompressed_bytes']and sha(raw)==p['uncompressed_sha256']and offset==p['offset'];offset+=len(raw);parts.append(raw)
 raw=b''.join(parts);assert len(raw)==product['original_bytes']and sha(raw)==product['original_sha256']==registry[sid]['sha256'];v=json.loads(raw);assert v['type']=='FeatureCollection'and len(v['features'])==product['feature_count']
 p=historical_sources[sid]['complete_source']
 geoms=[];rows=[];invalid=[]
 for n,f in enumerate(v['features']):
  props=f.get('properties',{});shapeid=props.get('shapeID');g=shape(f['geometry']);valid=g.is_valid and g.geom_type in ('Polygon','MultiPolygon')and not g.is_empty
  if not valid:invalid.append({'feature_index':n,'shapeID':shapeid,'geometry_type':g.geom_type,'is_valid':g.is_valid,'is_empty':g.is_empty})
  rows.append({'feature_index':n,'shapeID':shapeid,'feature_sha256':sha(canon(f)),'geometry_sha256':sha(canon(f['geometry'])),'recorded_stable_subjects':subjectmap.get((sid,shapeid),[]),'valid_polygon':valid});geoms.append(g)
 products[sid]={'geometries':geoms,'rows':rows,'tree':STRtree(geoms)}
 source_receipts.append({'source_id':sid,'complete_source':p,'registry_entry':registry[sid],'complete_feature_count':len(rows),'invalid_features':invalid,'complete_features':rows});print('full product indexed',sid,len(rows),'invalid',len(invalid),flush=True)
 assert canon(rows)==canon(historical_sources[sid]['complete_features']);del v,raw,parts;gc.collect()
inventory=decode(git(I,'coordination/engineering/worldwide-inventory-1164-20261006/run-one/report.json'));successor=decode(git(S,SP+'report.json'));spins={p['path']:p for p in successor['products']};cd=decode(git(S,SP+'components-delta.json.gz'),spins['components-delta.json.gz']);assert not set(targets)&set(cd['removed_ids']);current_upserts={f['id']:f for f in cd['upsert_records'] if f['id']in targets}
features={}
for pin in inventory['complete_products']['components']:
 path=next(p['path']for p in inventory['source_descriptors']if p['sha256']==pin['sha256']);b=git(M,path);collection=decode(b,pin);assert collection['type']=='FeatureCollection'
 for f in collection['features']:
  if f['id']in targets and f['id']not in current_upserts:assert f['id']not in features;features[f['id']]=f
features.update(current_upserts);assert set(features)==set(targets)
b=(CASE/config['original_expected_records']).read_bytes();authenticate(CASE/config['original_expected_records']);expected_rows=json.loads(gzip.decompress(b));expected={x['component']:x for x in expected_rows};assert len(expected)==len(expected_rows)and set(expected)==set(targets);consistency=[]
outputs=[];batch=[];size=0;counts=collections.Counter();family_summary={};start=time.monotonic();processed=[];validity=collections.Counter()
def flush():
 global batch,size
 if not batch:return
 raw=canon(batch);p=O/('components-%03d.json.gz'%len(outputs));assert not p.exists();b=gzip.compress(raw,mtime=0);p.write_bytes(b);outputs.append({'path':str(p),'bytes':len(b),'sha256':sha(b),'decoded_bytes':len(raw),'decoded_sha256':sha(raw),'rows':len(batch)});batch=[];size=0

def geometry(g):return {'geometry':mapping(g),'geometry_sha256':sha(canon(mapping(g))),'geometry_type':g.geom_type,'is_empty':g.is_empty,'is_valid':g.is_valid,'planar_area_coordinate_units_squared':g.area,'planar_length_coordinate_units':g.length}
object_seen={};object_pins=[];object_buffer=[];object_size=0
objectdir=O/'source-union-objects';objectdir.mkdir(exist_ok=True)
def flush_objects():
 global object_buffer,object_size
 if not object_buffer:return
 raw=canon(object_buffer);p=objectdir/('objects-%04d.json.gz'%len(object_pins));assert not p.exists();b=gzip.compress(raw,mtime=0);p.write_bytes(b);object_pins.append({'path':str(p),'bytes':len(b),'sha256':sha(b),'decoded_bytes':len(raw),'decoded_sha256':sha(raw),'objects':len(object_buffer)});object_buffer=[];object_size=0
def preserve_union_object(value):
 global object_size
 body=canon(value);h=sha(body)
 if h not in object_seen:
  if len(body)>8*1024*1024:
   flush_objects();parts=[]
   for startbyte in range(0,len(body),8*1024*1024):
    part=body[startbyte:startbyte+8*1024*1024];p=objectdir/(h+'-part-%03d.bin'%len(parts));assert not p.exists();p.write_bytes(part);parts.append({'path':str(p),'bytes':len(part),'sha256':sha(part)})
   object_seen[h]={'geometry_sha256':h,'decoded_bytes':len(body),'codec':'canonical-json-exact-byte-fragments','parts':parts}
  else:
   row={'geometry_sha256':h,'geometry':value};n=len(canon(row))
   if object_buffer and object_size+n>8*1024*1024:flush_objects()
   object_buffer.append(row);object_size+=n;object_seen[h]={'geometry_sha256':h,'decoded_bytes':len(body),'codec':'canonical-json-object-in-indexed-shard'}
 return {'geometry_object_sha256':h,'canonical_geometry_bytes':len(body),'object_index':'source-union-object-index.json'}
for i in sorted(targets):
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
  descriptor=row['whole_relevant_source_union'];assert sha(canon(descriptor['geometry']))==descriptor['geometry_sha256'];union_value=descriptor['geometry'];descriptor['geometry']=preserve_union_object(descriptor['geometry'])
 historical_row=json.loads(canon(row))
 if expected[i]['union_transport']=='embedded'and 'whole_relevant_source_union'in historical_row:historical_row['whole_relevant_source_union']['geometry']=union_value
 verify_historical_row(historical_row,expected[i]['original_canonical_row_sha256'])
 if 'source_union_intersection'in row:
  union_positive=row['source_union_intersection']['planar_area_coordinate_units_squared']>0;individual_positive=any(x['intersection']['planar_area_coordinate_units_squared']>0 for x in row['feature_intersections'])
  if union_positive!=individual_positive:consistency.append({'component':i,'union_positive':union_positive,'individual_positive':individual_positive,'status':'unknown-operation-consistency-disagreement'})
 counts[row['status']]+=1;fs['processed_components']+=1;fs['statuses'][row['status']]+=1;processed.append(i);b=canon(row)
 if batch and size+len(b)>8*1024*1024:flush()
 batch.append(row);size+=len(b)
 if len(processed)%250==0:
  flush();(O/'checkpoint.json').write_bytes(canon({'processed':len(processed),'expected':expected_components,'complete_processed_ids_sha256':sha(canon(processed)),'counts':dict(counts),'outputs':outputs,'elapsed_seconds':time.monotonic()-start}));print('processed',len(processed),dict(counts),'elapsed',round(time.monotonic()-start,1),flush=True)
flush();flush_objects();objectindex=O/'source-union-object-index.json';objectindex.write_bytes(canon({'objects':object_seen,'shards':object_pins,'lossless_scope':'Exact canonical full union objects; complete intersection/difference/per-feature pointsets preserved.'}));assert len(processed)==expected_components and set(processed)==set(targets)
oldunknown=json.loads(gzip.decompress((CASE/'historical/operation-unknowns.json.gz').read_bytes()));assert {x['component']for x in oldunknown}=={x['component']for x in consistency};(O/'operation-consistency.json').write_bytes(canon(consistency))
for fs in family_summary.values():assert fs['processed_components']==fs['expected_components'];fs['statuses']=dict(fs['statuses'])
receipt={'started_utc':started_utc,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':['producer.py','--output',str(O),'--code-commit',args.code_commit],'status':'complete-immutable-source-comparison','code_commit':args.code_commit,'script_sha256':sha(pathlib.Path(__file__).read_bytes()),'scope_sha256':sha(scope_raw),'complete_families':expected_families,'complete_components':expected_components,'component_roster_sha256':sha(canon(sorted(targets))),'source_products':source_ids,'counts':dict(counts),'output_validity':dict(validity),'elapsed_seconds':time.monotonic()-start,'outputs':outputs,'source_union_object_index':{'path':str(objectindex),'bytes':objectindex.stat().st_size,'sha256':sha(objectindex.read_bytes())},'complete_family_results':sorted(family_summary.values(),key=lambda f:(f['best_rank']['measured_impact'],f['id'])),'historical_rows_verified':len(expected),'operation_consistency_unknowns':len(consistency),'immutable_input_aliases':pins,'source_input_products':config['source_products'],'software':{'python':platform.python_version(),'shapely':shapely.__version__,'geos':shapely.geos_version_string},'limits':['Literal GEOS longitude/latitude coordinate-unit squared areas and coordinate-unit lengths, not ellipsoidal areas or metres.','No periodic wrapping, snapping, normalization, repair, assignment, land/water or causal approval.','Historical private runs each had only one SHA-bound execution; these are separate immutable committed executions.','Source geometry coverage can include water and cannot approve administrative ownership.']}
(O/'report.json').write_bytes(canon(receipt));print(json.dumps({'status':receipt['status'],'components':expected_components,'counts':dict(counts),'unknowns':len(consistency)}),flush=True)

import pathlib,json,gzip,hashlib,subprocess,collections,time,math,platform,gc
import shapely
from shapely import STRtree,union_all
from shapely.geometry import shape,mapping
from shapely.errors import GEOSException
R=pathlib.Path('/Users/chengshuli/world-atlas-workspace/WorldAtlas');B=pathlib.Path('/Users/chengshuli/world-atlas-workspace/.cache/repair-readiness-1231-20261006');O=B/'direct-source-coverage-screen';HEAD='a26f8d8b50e7349054b86e70d1e6e552a9a2b0fd';I='c6a26e1caba54e1b81a89fbda3a64fff56da323d';M='79ffb2ed04702e16f009e4675a8d74ef9bd09d4f';H='549cc2a863d4a487a662c2613e4d02888e39b5ba';S='7c7cdf2388e0e7200b937c2cfb440b53165d9d98';SP='coordination/engineering/worldwide-successor-1215-20261006/run-one/'
assert platform.python_version()=='3.12.14'and shapely.__version__=='2.1.2'and shapely.geos_version_string=='3.13.1'
def canon(v):return (json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
proc=subprocess.Popen(['git','cat-file','--batch'],cwd=R,stdin=subprocess.PIPE,stdout=subprocess.PIPE);pins=[]
def git(commit,path):
 tree=subprocess.check_output(['git','ls-tree',commit,'--',path],cwd=R);assert tree.split()[0]in (b'100644',b'100755')
 proc.stdin.write((commit+':'+path+'\n').encode());proc.stdin.flush();h=proc.stdout.readline().split();assert h[1]==b'blob';b=proc.stdout.read(int(h[2]));assert len(b)==int(h[2])and proc.stdout.read(1)==b'\n';pins.append({'commit':commit,'path':path,'bytes':len(b),'sha256':sha(b),'git_blob_oid':h[0].decode(),'mode':tree.split()[0].decode()});return b

def decode(b,pin=None):
 if pin:assert len(b)==pin['bytes']and sha(b)==pin['sha256']
 raw=gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b
 if pin and 'uncompressed_sha256'in pin:assert len(raw)==pin['uncompressed_bytes']and sha(raw)==pin['uncompressed_sha256']
 return json.loads(raw)
cohortpath=B/'source-ready-administrative-direct-families.json';cohortraw=cohortpath.read_bytes();families=json.loads(cohortraw)['rows'];targets={}
for f in families:
 assert len(f['component_ids'])==f['component_count']and f['component_ids']==sorted(set(f['component_ids']))and sha(canon(f['component_ids']))==f['component_ids_sha256']
 for i in f['component_ids']:assert i not in targets;targets[i]=f
assert len(families)==251 and len(targets)==9785
source_ids=sorted({f['source_id']for family in families for f in family['source_families']});assert len(source_ids)==8
reusepath=B/'complete-reused-original-products.json';reuse=json.loads(reusepath.read_bytes());registryraw=git(M,'data/administrative-sources.json');registry=json.loads(registryraw)
# Exact raw source IDs map to recorded stable subjects through accepted full
# metadata, including aliases; no nearest or newly invented assignment.
contextreport=decode(git(H,'coordination/engineering/worldwide-contexts-1184-20261006/run-one/report.json'));subjectmap=collections.defaultdict(list)
for pin in contextreport['outputs']:
 for c in decode(git(H,pin['path']),pin):
  meta=c['original_metadata'];key=(meta.get('source_id'),meta.get('original_id'))
  if key[0]in source_ids and key[1]is not None:subjectmap[key].append({'id':c['id'],'original_feature_sha256':c['original_feature_sha256'],'reference_year':meta.get('reference_year'),'original_parent_id':c['original_parent_id']})
products={};source_receipts=[]
for sid in source_ids:
 p=reuse[sid]
 if p['source_kind']=='immutable-git-containing-file':
  b=git(p['commit'],p['paths'][0]);assert sha(b)==p['encoded_sha256'];raw=b
  for unused in range(p['decode_layers']):raw=gzip.decompress(raw)
 else:
  path=pathlib.Path(p['path']);assert path.is_file()and not path.is_symlink();raw=path.read_bytes()
 assert len(raw)==p['bytes']and sha(raw)==p['sha256']==registry[sid]['sha256'];v=json.loads(raw);assert v['type']=='FeatureCollection'and len(v['features'])==p['feature_count']
 geoms=[];rows=[];invalid=[]
 for n,f in enumerate(v['features']):
  props=f.get('properties',{});shapeid=props.get('shapeID');g=shape(f['geometry']);valid=g.is_valid and g.geom_type in ('Polygon','MultiPolygon')and not g.is_empty
  if not valid:invalid.append({'feature_index':n,'shapeID':shapeid,'geometry_type':g.geom_type,'is_valid':g.is_valid,'is_empty':g.is_empty})
  rows.append({'feature_index':n,'shapeID':shapeid,'feature_sha256':sha(canon(f)),'geometry_sha256':sha(canon(f['geometry'])),'recorded_stable_subjects':subjectmap.get((sid,shapeid),[]),'valid_polygon':valid});geoms.append(g)
 products[sid]={'geometries':geoms,'rows':rows,'tree':STRtree(geoms)}
 source_receipts.append({'source_id':sid,'complete_source':p,'registry_entry':registry[sid],'complete_feature_count':len(rows),'invalid_features':invalid,'complete_features':rows});print('full product indexed',sid,len(rows),'invalid',len(invalid),flush=True)
 del v,raw;gc.collect()
# Every initial cohort current component is a retained full original pointset.
inventory=decode(git(I,'coordination/engineering/worldwide-inventory-1164-20261006/run-one/report.json'));successor=decode(git(S,SP+'report.json'));spins={p['path']:p for p in successor['products']};cd=decode(git(S,SP+'components-delta.json.gz'),spins['components-delta.json.gz']);assert not set(targets)&set(cd['removed_ids'])and not set(targets)&{r['id']for r in cd['upsert_records']}
features={}
for pin in inventory['complete_products']['components']:
 path=next(p['path']for p in inventory['source_descriptors']if p['sha256']==pin['sha256']);b=git(M,path);collection=decode(b,pin);assert collection['type']=='FeatureCollection'
 for f in collection['features']:
  if f['id']in targets:assert f['id']not in features;features[f['id']]=f
assert set(features)==set(targets)
# Confirm exact accepted current family contents, not a hand-selected easy subset.
report=decode(git(HEAD,'coordination/engineering/worldwide-native-batches-1184-20261006/current-run-one/report.json'));actual_families={}
for pin in report['outputs']['current-batches']:
 for row in decode(git(HEAD,pin['path']),pin):
  if row['id']in {f['id']for f in families}:actual_families[row['id']]=row
assert all(canon(f)==canon(actual_families[f['id']])for f in families)
source_receipt_path=O/'complete-source-inputs.json';assert not source_receipt_path.exists();source_receipt_path.write_bytes(canon({'source_products':source_receipts,'inputs':pins,'cohort_sha256':sha(cohortraw),'cohort_path':str(cohortpath),'source_reuse_map_sha256':sha(reusepath.read_bytes())}))
outputs=[];batch=[];size=0;counts=collections.Counter();family_summary={};start=time.monotonic();processed=[];validity=collections.Counter()
def flush():
 global batch,size
 if not batch:return
 raw=canon(batch);p=O/('components-%03d.json.gz'%len(outputs));assert not p.exists();b=gzip.compress(raw,mtime=0);p.write_bytes(b);outputs.append({'path':str(p),'bytes':len(b),'sha256':sha(b),'decoded_bytes':len(raw),'decoded_sha256':sha(raw),'rows':len(batch)});batch=[];size=0

def geometry(g):return {'geometry':mapping(g),'geometry_sha256':sha(canon(mapping(g))),'geometry_type':g.geom_type,'is_empty':g.is_empty,'is_valid':g.is_valid,'planar_area_coordinate_units_squared':g.area,'planar_length_coordinate_units':g.length}
for i in sorted(targets):
 f=features[i];family=targets[i];g=shape(f['geometry']);sources=sorted({x['source_id']for x in family['source_families']});row={'component':i,'family':family['id'],'source_products':sources,'original_component_commit':M,'current_component_source_successor':S,'current_component_relation':'retained-full-original-feature-pointset','full_component_feature_sha256':sha(canon(f)),'component_geometry_sha256':sha(canon(f['geometry'])),'dateline_connected':f['properties'].get('dateline_connected'),'coordinate_scope':'literal original GeoJSON lon/lat pointsets; no periodic wrapping, coordinate snapping, datum transformation or normalization','positive_area_feature_ids':[],'zero_area_feature_ids':[],'feature_intersections':[],'unknowns':[],'surface_status':'unverified','administrative_assignment':None,'cause_status':'unknown'}
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
 counts[row['status']]+=1;fs['processed_components']+=1;fs['statuses'][row['status']]+=1;processed.append(i);b=canon(row)
 if batch and size+len(b)>8*1024*1024:flush()
 batch.append(row);size+=len(b)
 if len(processed)%250==0:
  flush();(O/'checkpoint.json').write_bytes(canon({'processed':len(processed),'expected':9785,'complete_processed_ids_sha256':sha(canon(processed)),'counts':dict(counts),'outputs':outputs,'elapsed_seconds':time.monotonic()-start}));print('processed',len(processed),dict(counts),'elapsed',round(time.monotonic()-start,1),flush=True)
flush();assert len(processed)==9785 and set(processed)==set(targets)
for fs in family_summary.values():assert fs['processed_components']==fs['expected_components'];fs['statuses']=dict(fs['statuses'])
ordered=sorted(family_summary.values(),key=lambda f:(f['best_rank']['measured_impact'],f['id']));receipt={'status':'complete-initial-direct-source-geometry-coverage-screen','cohort_sha256':sha(cohortraw),'initial_complete_families':251,'initial_complete_components':9785,'source_products':source_ids,'component_roster_sha256':sha(canon(sorted(targets))),'counts':dict(counts),'output_validity':dict(validity),'elapsed_seconds':time.monotonic()-start,'outputs':outputs,'complete_family_results':ordered,'source_input_receipt':{'path':str(source_receipt_path),'bytes':source_receipt_path.stat().st_size,'sha256':sha(source_receipt_path.read_bytes())},'script_sha256':sha(pathlib.Path(__file__).read_bytes()),'software':{'python':platform.python_version(),'shapely':shapely.__version__,'geos':shapely.geos_version_string},'limits':['Screen against whole consumed products using all bbox-candidate features, never just contacting subjects. Bounding-box-disjoint features cannot contribute to a literal-coordinate component intersection.','Country/product union extent is consumed input coverage, not actual dated land/water or legal boundary authority.','Full source and component pointsets preserved; no cutoffs, snapping, MakeValid, normalization or fill.','No periodic longitude wrapping performed; dateline interpretation remains an explicit separate limit.','One recorded compatible stable subject is observed source-geometry attribution, not administrative or ownership approval.','Source coverage does not identify exact historical execution cause or prove a safe repair.','Only initial251completefamilies/9785currentcomponents processed; IRN/PAK or other countries would be explicitly additive cohorts.']};p=O/'receipt.json';p.write_bytes(canon(receipt));print(json.dumps({'status':receipt['status'],'receipt':str(p),'counts':dict(counts),'elapsed_seconds':receipt['elapsed_seconds']}),flush=True);proc.terminate();proc.wait()

"""Restore every original row and geometry; do not repeat numerical science."""
import pathlib,json,gzip,hashlib,argparse,collections,copy

def canon(v):return (json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)+"\n").encode()
def sha(b):return hashlib.sha256(b).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--out',required=True);a=p.parse_args();root=pathlib.Path(__file__).parent;run=pathlib.Path(a.run)
scope=json.loads((root/'scope.json').read_bytes());expected=json.loads(gzip.decompress((root/'historical-original-rows.json.gz').read_bytes()));by_id={r['component']:r for r in expected};assert len(by_id)==len(expected)
report=json.loads((run/'receipt.json').read_bytes())
def checked_bytes(pin):
 path=run/pin['path'];assert not pathlib.Path(pin['path']).is_absolute() and '..' not in pathlib.Path(pin['path']).parts
 assert path.is_file() and not path.is_symlink();body=path.read_bytes();assert len(body)==pin['bytes'] and sha(body)==pin['sha256'] and len(body)<=32*1024*1024
 return body
def checked(pin):
 body=checked_bytes(pin)
 raw=gzip.decompress(body) if body[:2]==b'\x1f\x8b' else body
 if 'decoded_sha256' in pin:assert len(raw)==pin['decoded_bytes'] and sha(raw)==pin['decoded_sha256']
 assert max(len(raw),len(body))<=32*1024*1024;return json.loads(raw)
source_receipt=checked(report['source_input_receipt']);assert source_receipt['producer_commit']==report['producer_commit'] and source_receipt['cohort_sha256']==report['cohort_sha256'];assert sorted(v['source_id']for v in source_receipt['source_products'])==scope['source_ids']
index=checked(report['source_union_object_index']);objects={};scientific_pins=list(report['outputs'])+[report['source_input_receipt'],report['source_union_object_index']]
for pin in index['shards']:
 scientific_pins.append(pin)
 for row in checked(pin):
  assert row['geometry_sha256']==sha(canon(row['geometry'])) and row['geometry_sha256'] not in objects;objects[row['geometry_sha256']]=row['geometry']
for h,binding in index['objects'].items():
 if binding['codec']=='canonical-json-exact-byte-fragments':
  bodies=[]
  for pin in binding['parts']:
   body=checked_bytes(pin);bodies.append(body);scientific_pins.append(pin)
  raw=b''.join(bodies);assert sha(raw)==h;objects[h]=json.loads(raw)
 assert sha(canon(objects[h]))==h and len(canon(objects[h]))==binding['decoded_bytes']
assert set(objects)==set(index['objects'])
seen=set();used=set();counts=collections.Counter();unknown=[];witness=[];hashes=0
for pin in report['outputs']:
 rows=checked(pin);assert len(rows)==pin['rows']
 for row in rows:
  i=row['component'];assert i in by_id and i not in seen and row['family']==by_id[i]['family'];seen.add(i)
  assert row['administrative_assignment'] is None and row['cause_status']=='unknown' and row['surface_status']=='unverified'
  for field in ['source_union_intersection','component_minus_source_union']:
   if field in row:assert sha(canon(row[field]['geometry']))==row[field]['geometry_sha256'];hashes+=1
  for v in row['feature_intersections']:assert sha(canon(v['intersection']['geometry']))==v['intersection']['geometry_sha256'];hashes+=1
  if 'whole_relevant_source_union' in row:
   d=row['whole_relevant_source_union'];ref=d['geometry'];h=d['geometry_sha256'];assert ref['geometry_object_sha256']==h and ref['canonical_geometry_bytes']==len(canon(objects[h]));used.add(h);hashes+=1
   if by_id[i]['cohort']=='initial251':row=copy.deepcopy(row);row['whole_relevant_source_union']['geometry']=objects[h]
  assert sha(canon(row))==by_id[i]['canonical_original_row_sha256'], ('original full row changed',i)
  counts[row['status']]+=1
  unionarea=row.get('source_union_intersection',{}).get('planar_area_coordinate_units_squared');positive=any(v['intersection']['planar_area_coordinate_units_squared']>0 for v in row['feature_intersections'])
  if unionarea is not None and ((unionarea>0)!=positive):unknown.append(i)
  if row['status']=='one-compatible-recorded-subject-uniquely-covers-component':witness.append(i)
assert seen==set(scope['complete_component_ids'])==set(by_id) and used==set(objects) and dict(counts)==report['counts']
old_unknown=json.loads(gzip.decompress((root/'historical-operation-unknowns.json.gz').read_bytes()));old_witness=json.loads(gzip.decompress((root/'historical-witness-native-joins.json.gz').read_bytes()))
assert set(unknown)=={v['component']for v in old_unknown} and set(witness)=={v['component']for v in old_witness}
normalized=copy.deepcopy(report);normalized.pop('elapsed_seconds');scientific_hash=sha(canon({'full_result':normalized,'whole_artifacts':sorted(scientific_pins,key=lambda r:r['path'])}))
result={'outcome':'passed','complete_components':len(seen),'complete_families':len(scope['complete_family_ids']),'all_original_rows_equal':True,'full_geometry_hashes':hashes,'complete_witnesses':len(witness),'complete_operation_unknowns':len(unknown),'scientific_product_sha256':scientific_hash,'run_report_sha256':sha((run/'receipt.json').read_bytes()),'actual_verifier_sha256':sha(pathlib.Path(__file__).read_bytes()),'limits':['Complete pointset/row custody and numerical discrepancy retention; no land/water, ownership, cause or repair approval.','Verification is not a scientific execution.']}
out=pathlib.Path(a.out);assert not out.exists();out.write_bytes(canon(result));print(json.dumps(result))

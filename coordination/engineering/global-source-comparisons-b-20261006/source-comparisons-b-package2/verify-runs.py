"""Independent full ordinary readback: two executions plus every historical row."""
import pathlib,json,gzip,hashlib,argparse,collections,subprocess
CASE=pathlib.Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('run_one');parser.add_argument('run_two');parser.add_argument('receipt');args=parser.parse_args()
def canon(v):return(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def pinned(p):
 b=pathlib.Path(p['path']).read_bytes();assert len(b)==p['bytes']and sha(b)==p['sha256'];raw=gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b
 if 'decoded_sha256'in p:assert len(raw)==p['decoded_bytes']and sha(raw)==p['decoded_sha256']
 return json.loads(raw)
expected_rows=json.loads(gzip.decompress((CASE/'historical/expected-complete-records.json.gz').read_bytes()));expected={x['component']:x for x in expected_rows};assert len(expected_rows)==len(expected)
config=json.loads((CASE/'input-config.json').read_bytes());scope=json.loads((CASE/'scope.json').read_bytes());runs=[]
for directory in (args.run_one,args.run_two):
 directory=pathlib.Path(directory);report=json.loads((directory/'report.json').read_bytes());resolved=subprocess.check_output(['git','rev-parse',report['code_commit']+'^{commit}'],cwd=CASE.parents[3]).decode().strip();assert resolved=='c0bb4c62a725f9d170a9c26db4baa1c477cbc905';assert report['script_sha256']==sha((CASE/'producer.py').read_bytes());assert canon(report['source_input_products'])==canon(config['source_products']);assert report['scope_sha256']==sha((CASE/'scope.json').read_bytes())and report['source_products']==scope['source_ids'];assert all(p in config['immutable_aliases']for p in report['immutable_input_aliases']);assert report['complete_components']==len(expected)==config['complete_components'];objects={};index=json.loads((directory/'source-union-object-index.json').read_bytes())
 for p in index['shards']:
  for obj in pinned(p):
   h=obj['geometry_sha256'];assert h==sha(canon(obj['geometry']))and h not in objects;objects[h]=obj['geometry']
 assert set(objects)==set(index['objects'])==set(scope['whole_union_object_dependencies'])
 rows={};witness_ids=set();statuses=collections.Counter();family_rows=collections.defaultdict(list)
 for p in report['outputs']:
  for row in pinned(p):
   cid=row['component'];assert cid not in rows and cid in expected;binding=expected[cid];assert binding['family']==row['family'];family_rows[row['family']].append(cid)
   for field,oldhash in binding['expected_geometry_hashes'].items():assert row[field]['geometry_sha256']==oldhash
   actual=json.loads(canon(row))
   if 'whole_relevant_source_union'in row:
    ref=row['whole_relevant_source_union']['geometry'];h=ref['geometry_object_sha256'];assert h==row['whole_relevant_source_union']['geometry_sha256']and h in objects;assert len(canon(objects[h]))==ref['canonical_geometry_bytes']
    if binding['union_transport']=='embedded':actual['whole_relevant_source_union']['geometry']=objects[h]
   assert sha(canon(actual))==binding['original_canonical_row_sha256'],cid
   for field in ('source_union_intersection','component_minus_source_union'):
    if field in row:assert sha(canon(row[field]['geometry']))==row[field]['geometry_sha256']
   for x in row['feature_intersections']:assert sha(canon(x['intersection']['geometry']))==x['intersection']['geometry_sha256']
   if row['status']=='one-compatible-recorded-subject-uniquely-covers-component':witness_ids.add(cid)
   assert row['administrative_assignment']is None and row['surface_status']=='unverified'and row['cause_status']=='unknown';rows[cid]=sha(canon(row));statuses[row['status']]+=1
 assert sorted(rows)==scope['complete_component_ids']and sorted(family_rows)==sorted(scope['complete_family_ids']);assert dict(statuses)==report['counts']
 actual_unknown=json.loads((directory/'operation-consistency.json').read_bytes());historical_unknown=json.loads(gzip.decompress((CASE/'historical/operation-unknowns.json.gz').read_bytes()));assert {x['component']for x in actual_unknown}=={x['component']for x in historical_unknown}and len(actual_unknown)==len(historical_unknown)
 witness=json.loads(gzip.decompress((CASE/'historical/full-witness-joins.json.gz').read_bytes()))
 # Report status-count is crosschecked against every row above; no quadratic reread.
 assert witness_ids=={x['component']for x in witness}and len(witness_ids)==len(witness)
 runs.append({'directory':str(directory),'actual_report_sha256':sha((directory/'report.json').read_bytes()),'actual_code_commit':report['code_commit'],'rows':rows,'objects':{h:sha(canon(g))for h,g in objects.items()},'unknowns':actual_unknown,'counts':dict(statuses),'families':len(family_rows),'witnesses':len(witness),'files':[{'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size}for p in directory.rglob('*')if p.is_file()]})
assert runs[0]['rows']==runs[1]['rows']and runs[0]['objects']==runs[1]['objects']and runs[0]['unknowns']==runs[1]['unknowns']
scientific=sha(canon({'rows':runs[0]['rows'],'objects':runs[0]['objects'],'unknowns':runs[0]['unknowns']}))
receipt={'status':'PASS','full_original_canonical_rows_per_run':len(expected),'families_per_run':runs[0]['families'],'witnesses_per_run':runs[0]['witnesses'],'unknowns_per_run':len(runs[0]['unknowns']),'run_one_sha256':scientific,'run_two_sha256':scientific,'actual_runs':[{k:v for k,v in r.items()if k not in ('rows','objects','unknowns')}for r in runs],'limits':['Complete encoded/decoded transport and all canonical rows/geometry objects checked against original bindings; this reader does not rerun GEOS.','Two actual producer executions are separate from this independent readback.','No administrative, land/water, ownership or repair approval.']}
pathlib.Path(args.receipt).write_bytes(canon(receipt));print(json.dumps({k:v for k,v in receipt.items()if k!='actual_runs'},sort_keys=True))

"""Exhaustive actual-data invariants for the source-role overlay."""
import collections,gzip,hashlib,importlib.util,json,pathlib,sys,subprocess,copy
ROOT=pathlib.Path(__file__).resolve().parents[1]
def read(p):return json.loads(gzip.decompress(p.read_bytes())if str(p).endswith('.gz')else p.read_bytes())
d=read(ROOT/'data/source-policy-corrections/europe-v1.json.gz');index=read(ROOT/'data/world-index.json');features=[f for p in index['parts']for f in read(ROOT/'data'/p)['features']];by_id={f['id']:f for f in features};annotations={r['location_id']:r for r in d['location_annotations']};expected={f['id']for f in features if f['properties']['reference_owner']in ['Italy','Spain','Kosovo']}
assert set(annotations)==expected and len(annotations)==1001
assert len(annotations)==len(d['location_annotations'])
sha_json=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
units={u['id']:u for u in read(ROOT/'data/hierarchy.json')}
for id,row in annotations.items():
 f=by_id[id];m=f['properties']['metadata'];assert row['footprint_sha256']==sha_json(f['geometry']);assert row['current_metadata_sha256']==sha_json(m)
 assert row['before_annotation']=={key:m.get(key)for key in ['source_id','source_name','source_url','source_role','administrative_level','location_basis','reference_year','license']}
 chain=[];parent=f['properties']['parent_id']
 while parent:chain.append(parent);parent=units[parent]['parent_id']
 assert chain==row['parent_chain'];assert row['after_annotation']['reference_year']==m.get('reference_year');assert not row['after_annotation']['local_granularity_approved']
for correction in d['policy_corrections']:
 assert set(correction['location_ids'])=={id for id,row in annotations.items()if row['profile_iso']==correction['profile_iso']};assert not correction['semantic_complete'];assert correction['effective_from']is None
 assert sum(correction['role_counts'].values())==len(correction['location_ids'])
assert next(c for c in d['policy_corrections']if c['profile_iso']=='ESP')['continent_counts']=={'Europe':372,'Africa':12}
for p,digest in d['input_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest,p
spec=importlib.util.spec_from_file_location('correction_producer',ROOT/'scripts/prepare-europe-source-policy-corrections.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert module.build(d['source_evidence']['italy-current-source-properties']['request_receipts'])==d
sys.path.insert(0,str(ROOT/'scripts'));from source_policy_corrections import effective_source_policies,load_effective_source_policies
base=read(ROOT/'data/location-policy.json');before=copy.deepcopy(base);effective=effective_source_policies(base,d);assert base==before;assert effective_source_policies(effective,d)==effective;assert load_effective_source_policies(ROOT)==effective
script="import fs from 'node:fs';import {gunzipSync} from 'node:zlib';import {effectiveSourcePolicies} from './src/source-policy-corrections.js';const base=JSON.parse(fs.readFileSync('data/location-policy.json')),bundle=JSON.parse(gunzipSync(fs.readFileSync('data/source-policy-corrections/europe-v1.json.gz')));process.stdout.write(JSON.stringify(effectiveSourcePolicies(base,bundle)));"
assert json.loads(subprocess.check_output(['node','--input-type=module','-e',script],cwd=ROOT))==effective
changed=copy.deepcopy(base);changed['countries']['ITA']['role']='Unrelated unsourced edit'
try:effective_source_policies(changed,d)
except ValueError:pass
else:raise AssertionError('Unrelated policy changed without new evidence')
print('PASS: all 1,001 source-role classifications, all source/policy/footprint/metadata/parent pins, every country/continent total and reproducible producer; no semantic approval or active migration')

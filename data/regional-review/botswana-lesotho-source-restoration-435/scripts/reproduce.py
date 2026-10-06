#!/usr/bin/env python3
"""Reproduce exact scope, preserved ID/source lineage, and immutable input checks for #1136."""
import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
PACKET=ROOT/'data/regional-review/botswana-lesotho-source-restoration-435'
PRIOR=ROOT/'data/regional-review/regional-review-b9aef9289b79194e'
BASELINE='ebfc498397c64706177cc8d885d916d446fe19a8'
PINNED={
 'data/administrative-sources.json':'ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633',
 'data/geography/part-13.json':'90b032861ecae8a4df9a8b5386eccfb20a7243c264dbf79994b54c5297e6f6c1',
 'data/geography/part-2.json':'93eeb8f5dab7d8ca6c86593f7ab7b1310312757abcef33d4e7200a270624a1bf',
 'data/hierarchy.json':'568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b',
 'data/world-index.json':'a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03',
 'data/regional-review/regional-review-b9aef9289b79194e/findings/source-register.json':'f35089b4369f02119abe0973683c507643e7a3fe37b6a82706b7cb6e480e78cb',
}
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fail(msg): raise AssertionError(msg)
assess=[json.loads(s) for s in (PACKET/'findings/subject-assessments.jsonl').read_text().splitlines() if s]
prior=[json.loads(s) for s in (PRIOR/'findings/subject-roster.jsonl').read_text().splitlines() if s]
expected={x['id']:x for x in prior if x.get('area_name') in ('Botswana','Lesotho')}
actual={x['id']:x for x in assess}
if len(assess)!=45 or len(actual)!=45: fail('subject rows must contain 45 unique IDs')
if set(expected)!=set(actual): fail('subject inventory differs from immutable prior roster')
if sum(x['area_name']=='Botswana' for x in assess)!=35 or sum(x['area_name']=='Lesotho' for x in assess)!=10: fail('country scope count differs')
if sum(x['area_name']=='Botswana' and x['id'].startswith('atlas:physical:') for x in assess)!=13: fail('ecological fragment count differs')
if sum(x['area_name']=='Botswana' and x['id'].startswith('gb:BWA:ADM2:') for x in assess)!=22: fail('BWA source feature count differs')
if sum(x['area_name']=='Lesotho' and x['id'].startswith('gb:LSO:ADM1:') for x in assess)!=10: fail('LSO source feature count differs')
for i,r in actual.items():
 for k in ('name','area_name','parent_id','parent_name','source_original_id','source_id'):
  if r.get(k)!=expected[i].get(k): fail(f'prior lineage changed: {i} {k}')
features={}
for file in ('data/geography/part-2.json','data/geography/part-13.json'):
 for f in json.loads((ROOT/file).read_text())['features']:
  i=f.get('id')
  if i in actual:
   if i in features: fail('duplicate Atlas feature across parts: '+i)
   features[i]=(file,f)
if set(features)!=set(actual): fail('exact issue subject IDs do not resolve to Atlas geography files')
for path,expected_hash in PINNED.items():
 p=ROOT/path
 if not p.is_file() or digest(p)!=expected_hash: fail('pinned input mismatch: '+path)
for source,expected_hash in [
 ('sources/gb-BWA-ADM2-2015.geojson','466b6a2c45c81ade313403f7cfe004325079bbaa0cd06c97e7bc5c5b5c43db5e'),
 ('sources/gb-LSO-ADM1-2017.geojson','d2402f2fd99b06d894237e652f70d3e163b4e0cf5f95bb8e2227a1d5f3162a19')]:
 if digest(PACKET/source)!=expected_hash: fail('retained source bytes changed: '+source)
# Positive and negative controls are deliberately identity-only; neither certifies geometry.
positive=(len(actual)==45 and set(actual)==set(expected))
negative_test=list(assess)+[dict(assess[0])]
negative=(len({x['id'] for x in negative_test})!=len(negative_test))
if not positive or not negative: fail('control failed')
result={
 'version':1,'issue':1136,'baseline_commit':BASELINE,'outcome':'passed',
 'scope':{'expected_unique_ids':45,'matched_ids':len(actual),'botswana':35,'lesotho':10,'botswana_adm2_direct':22,'botswana_ecological_clips':13,'lesotho_adm1_districts':10},
 'lineage':'all source IDs, names, parent IDs/names and source IDs match the prior immutable subject roster',
 'atlas_feature_matches':{'part-2':sum(v[0]=='data/geography/part-2.json' for v in features.values()),'part-13':sum(v[0]=='data/geography/part-13.json' for v in features.values())},
 'pinned_inputs':{p:{'sha256':digest(ROOT/p),'expected_sha256':h,'matched':digest(ROOT/p)==h} for p,h in PINNED.items()},
 'retained_sources':{p:{'sha256':digest(PACKET/p),'expected_sha256':h,'matched':digest(PACKET/p)==h} for p,h in [('sources/gb-BWA-ADM2-2015.geojson','466b6a2c45c81ade313403f7cfe004325079bbaa0cd06c97e7bc5c5b5c43db5e'),('sources/gb-LSO-ADM1-2017.geojson','d2402f2fd99b06d894237e652f70d3e163b4e0cf5f95bb8e2227a1d5f3162a19')]},
 'controls':{'positive_exact_roster_and_lineage':'passed','negative_duplicate_subject_id':'passed'},
 'interpretation_limit':'Identity, lineage, and hash checks do not establish legal territorial meaning, currentness, boundary correctness, license beyond retained metadata, regional approval, publication, or import permission.'
}
(PACKET/'findings/reproduction.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,indent=2))

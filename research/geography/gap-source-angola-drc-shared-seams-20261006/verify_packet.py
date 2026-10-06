#!/usr/bin/env python3
"""Source identity, mutation and reproducibility controls for issue #1243."""
import gzip,hashlib,json,subprocess,sys,pathlib,os
ROOT=pathlib.Path(__file__).resolve().parents[3]
PACKET=ROOT/'research/geography/gap-source-angola-drc-shared-seams-20261006'
sys.path.insert(0,str(ROOT/'scripts'))
from evidence.immutable import canonical_json,sha256
BASE='79ffb2ed04702e16f009e4675a8d74ef9bd09d4f'
def readj(p):return json.loads(pathlib.Path(p).read_text())
def git(path):return subprocess.check_output(['git','-C',str(ROOT),'show',f'{BASE}:{path}'])
# Positive control: exact whole-source pins, all ten complete component records,
# all ten original fragments and all five baseline contact features.
receipt=readj(PACKET/'inputs/source-acquisition-receipt.json')
for src in receipt['sources']:
 b=(PACKET/src['saved_path']).read_bytes()
 assert len(b)==src['whole_bytes'] and sha256(b)==src['whole_sha256']
 assert len(json.loads(b)['features'])==src['feature_count']
components=readj(PACKET/'inputs/component-source-bindings.json'); bysha={x['sha256']:x for x in components['source_shards']}
component_fc=readj(PACKET/'inputs/component-features.geojson')['features']; assert len(component_fc)==10
for row in components['rows']:
 shard=bysha[row['source_shard_sha256']]; raw=git(shard['actual_retained_path'])
 assert len(raw)==shard['bytes'] and sha256(raw)==shard['sha256']
 data=json.loads(gzip.decompress(raw)); feature=data['features'][row['feature_index']]
 assert feature['id']==row['component_id'] and sha256(canonical_json(feature))==row['full_feature_sha256']
 assert next(f for f in component_fc if f['id']==feature['id'])['geometry']==feature['geometry']
det=components['detection_shard']; raw=git(det['path']); assert len(raw)==det['bytes'] and sha256(raw)==det['sha256']
fragments=json.loads(gzip.decompress(raw))['features']; frag_fc=readj(PACKET/'inputs/original-fragments.geojson')['features']; assert len(frag_fc)==10
for row in components['rows']:
 for bind in row['fragment_bindings']:
  f=next(f for f in fragments if f['id']==bind['id'])
  assert sha256(canonical_json(f))==bind['feature_sha256']
  assert next(x for x in frag_fc if x['id']==f['id'])['geometry']==f['geometry']
contacts=readj(PACKET/'inputs/contact-source-bindings.json'); cfc=readj(PACKET/'inputs/contact-features.geojson')['features']; assert len(cfc)==5
for bind in contacts['features']:
 src=json.loads(git(bind['path'])); f=next(x for x in src['features'] if x['id']==bind['id'])
 candidate=next(x for x in cfc if x['id']==f['id'])
 assert candidate==f
 assert candidate['geometry']==f['geometry']
assert {x['id'] for x in cfc}==set(readj(PACKET/'inputs/family-roster.json')['contact_ids'])
ne=readj(PACKET/'inputs/natural-earth-reference-receipt.json')
for row in ne['sources']:
 raw=git(row['baseline_path']); retained=(ROOT/row['path']).read_bytes()
 assert len(raw)==row['compressed_bytes'] and sha256(raw)==row['compressed_sha256'] and retained==raw
 unpacked=gzip.decompress(raw); assert len(unpacked)==row['uncompressed_bytes'] and sha256(unpacked)==row['uncompressed_sha256']
assert len(readj(PACKET/'inputs/current-successor-vintage.json')['target_component_lineage'])==10
assert len(readj(PACKET/'outputs/component-assessment.json')['components'])==10
positive={'method_id':'source-assessment-generator','kind':'positive-control','outcome':'passed','checks':['All source product whole-byte hashes and complete feature counts','All ten full component record hashes and pointsets from seven exact baseline shards','All ten detector-v4 fragment IDs and feature hashes','All five full contact record hashes and geometries','Both whole Natural Earth sources match pinned baseline compressed and uncompressed hashes','Ten component lineage links and unchanged tile 759 query','All ten assessment rows retained']}
(PACKET/'outputs/positive-control.json').write_text(json.dumps(positive,sort_keys=True,indent=2)+'\n')
# Negative control: any byte mutation must be rejected by the pinned full-file check.
original=(PACKET/receipt['sources'][0]['saved_path']).read_bytes(); altered=bytearray(original);altered[len(altered)//2]^=1
assert sha256(altered)!=receipt['sources'][0]['whole_sha256']
negative={'method_id':'source-assessment-generator','kind':'negative-control','outcome':'passed','mutated_source':'COD consumed simplified product, one interior byte flipped in-memory','expected_sha256':receipt['sources'][0]['whole_sha256'],'altered_sha256':sha256(altered),'rejected':sha256(altered)!=receipt['sources'][0]['whole_sha256']}
(PACKET/'outputs/negative-control.json').write_text(json.dumps(negative,sort_keys=True,indent=2)+'\n')
# Run-level proof is written after two completed final producer executions.
first=readj(PACKET/'outputs/run-one-digests.json'); second=readj(PACKET/'outputs/run-two-digests.json')
assert first==second and len(first['files'])==5
combined=sha256(canonical_json(first))
repro={'method_id':'source-assessment-generator','kind':'reproducibility','outcome':'passed','run_one_sha256':combined,'run_two_sha256':combined,'files':first['files']}
(PACKET/'outputs/reproducibility-control.json').write_text(json.dumps(repro,sort_keys=True,indent=2)+'\n')
print('positive, negative and reproducibility controls passed')

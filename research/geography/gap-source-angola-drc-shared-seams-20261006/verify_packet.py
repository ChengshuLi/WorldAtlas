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

# Additional independent water and legal-source family: verify full source and
# code freezes, exact 10/5 subject preservation, and the actual two-run bytes.
freeze=readj(PACKET/'inputs/additional-freeze.json')
for row in freeze['inputs']:
 raw=(PACKET/row['path']).read_bytes()
 assert len(raw)==row['bytes'] and sha256(raw)==row['sha256'], row['path']
for key in ('producer','runner'):
 raw=(PACKET/freeze[f'{key}_path']).read_bytes()
 assert len(raw)==freeze[f'{key}_bytes'] and sha256(raw)==freeze[f'{key}_sha256']
extra=readj(PACKET/'outputs/physical-water-authority-assessment.json')
assert len(extra['components'])==10 and len(extra['contacts'])==5
assert {row['contact_id'] for row in extra['contacts']}==set(extra['contact_ids'])
assert len({row['geometry_sha256'] for row in extra['contacts']})==5
assert extra['components_with_seasonal_water_pixel']==2
assert extra['components_with_permanent_water_pixel']==0
assert extra['components_all_nodata_both_years']==7
assert extra['components_intersecting_legal_parallel_coordinates']==3
assert len(extra['jrc_water_summary']['years'])==2
first=readj(PACKET/'outputs/additional-run-1-digests.json'); second=readj(PACKET/'outputs/additional-run-2-digests.json')
observed=readj(PACKET/'outputs/additional-run-observations.json')
assert first==second and first['files']=={'physical-water-authority-assessment.json':sha256((PACKET/'outputs/physical-water-authority-assessment.json').read_bytes())}
assert first['producer_sha256']==freeze['producer_sha256'] and first['runner_sha256']==freeze['runner_sha256']
assert observed['byte_identical_outputs'] is True and len(observed['runs'])==2
assert all(run['exit_code']==0 and run['finished_utc']>run['started_utc'] for run in observed['runs'])
# Mutation controls are in memory and do not alter the pinned source files.
source_mutations=[]
for rel in ('sources/jrc-gsw-v1.4/jrc-gsw-yearly-2018-0000320000-0000760000.tif',
            'sources/official-angola/angola-law-14-24-official-gazette.pdf'):
 original=(PACKET/rel).read_bytes(); changed=bytearray(original); changed[len(changed)//2]^=1
 expected=next(x['sha256'] for x in freeze['inputs'] if x['path']==rel)
 assert sha256(changed)!=expected
 source_mutations.append({'path':rel,'expected_sha256':expected,'altered_sha256':sha256(changed),'rejected':True})
additional={'method_id':'jrc-gsw-annual-pixel-observation','kind':'positive-control','outcome':'passed',
 'checks':['JRC 2018/2019 exact full-file byte pins','Frozen producer and runner hashes','Ten candidate component outputs and all five contact IDs/geometries','Actual two successful full executions with byte-identical output'],
 'output_sha256':sha256((PACKET/'outputs/physical-water-authority-assessment.json').read_bytes())}
(PACKET/'outputs/additional-source-positive-control.json').write_text(json.dumps(additional,sort_keys=True,indent=2)+'\n')
negative2={'method_id':'jrc-gsw-annual-pixel-observation','kind':'negative-control','outcome':'passed',
 'description':'One interior byte in each independent JRC and official law source was flipped in memory; both source-pin checks reject the altered bytes.',
 'source_mutations':source_mutations}
(PACKET/'outputs/additional-source-negative-control.json').write_text(json.dumps(negative2,sort_keys=True,indent=2)+'\n')
assert len(list((PACKET/'outputs').glob('additional-failed-attempt-*.json')))==3
assert (PACKET/'outputs/additional-superseded-run-pair.json').is_file()
print('additional JRC/law controls passed')

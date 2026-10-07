#!/usr/bin/env python3
"""Reproduce #927's source-feature and geometry representation checks from pinned bytes."""
import hashlib, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
BASE='72029cd16057199be441058c69dd783604541100'
PARENT='data/regional-review/regional-review-afee7ce9a5601ab2/'
PINS={
'data/world-index.json':'a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03',
'data/hierarchy.json':'568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b',
'data/administrative-sources.json':'ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633',
'data/validation/macro-publication-v5.json':'aae3967fde4f5bf92b3cb0b42c490c6c6a5921c7421dcdc9533f242afbd6a674',
'data/geography/part-25.json':'dada55df1b7f0f2a2b307f4aea071d0e48791e3105875755fe74a292a6763394'}
def blob(path, commit=BASE): return subprocess.check_output(['git','-C',str(ROOT),'show',f'{commit}:{path}'])
def sha(raw): return hashlib.sha256(raw).hexdigest()
def unique_subjects(features, target):
 rows=[f for f in features if f.get('id')==target]
 if len(rows)!=1: raise ValueError('subject must occur exactly once')
 return rows[0]
def verify_pin(raw, expected):
 if sha(raw)!=expected: raise ValueError('whole-file pin mismatch')
 return True
# Pin checks, and subject exact occurrence / source identity.
for p,h in PINS.items(): assert verify_pin(blob(p),h),(p,sha(blob(p)))
part=json.loads(blob('data/geography/part-25.json'))
id='gb:URY:ADM1:27058087B22084813565519'
subject=unique_subjects(part['features'],id)
positive_control={'method_id':'source-review','kind':'positive-control','outcome':'passed','evidence':'the pinned input contains the exact subject once'}
try:
 unique_subjects(part['features']+[subject],id)
 raise AssertionError('duplicate control unexpectedly accepted')
except ValueError:
 pass
negative_control={'method_id':'source-review','kind':'negative-control','outcome':'passed','evidence':'a duplicated subject is rejected'}
try:
 verify_pin(blob('data/world-index.json'),'0'*64)
 raise AssertionError('wrong-pin control unexpectedly accepted')
except ValueError:
 pass
pin_control={'method_id':'source-review','kind':'negative-control','outcome':'passed','evidence':'an altered whole-file pin is rejected'}
assert subject['properties']['name']=='Artigas'
assert subject['properties']['parent_id']=='framework:province:artigas:dc4b2e0fed20'
assert subject['properties']['metadata'].get('semantic_review',{}).get('status')=='open'
# Exact originals are read from parent packet; never mutate them.
old=json.loads(blob(PARENT+'ury-gb-2017.geojson'))
igm=json.loads(blob(PARENT+'ury-igm-current.geojson'))
assert sha(blob(PARENT+'ury-gb-2017.geojson'))=='9f4887205e7b359af2ef1e4f484ad071d2dc0d12d068f1d7b6c1cc6c2624d1cf'
assert sha(blob(PARENT+'ury-igm-current.geojson'))=='3cfa19c6be9d12bd159b236e15839f958656fdbe66ef19e38379cb54c141b3a7'
assert len(old['features'])==19 and len(igm['features'])==21
old_art=[f for f in old['features'] if f['properties'].get('shapeName')=='Artigas']
assert len(old_art)==1
# Features selected by stable source identity and precise contested attributes.
contested=[]
for f in igm['features']:
 p=f.get('properties',{})
 if p.get('nam') in ('Rincón de Maneco','Isla Brasileña'):
  contested.append({'id':f.get('id'),'name':p.get('nam'),'department':p.get('DEPTO'),'definition':p.get('DEF'),'text':p.get('TXT'),'observation':p.get('OBS'),'geometry_type':f.get('geometry',{}).get('type'),'coordinate_member_count':len(f.get('geometry',{}).get('coordinates',[]))})
assert len(contested)==2
byname={x['name']:x for x in contested}
assert byname['Rincón de Maneco']['id']==15 and byname['Rincón de Maneco']['department']=='ARTIGAS'
assert byname['Rincón de Maneco']['definition']=='Rincón de Maneco (Contestado)'
assert byname['Isla Brasileña']['id']==16 and byname['Isla Brasileña']['department']=='ARTIGAS'
assert byname['Isla Brasileña']['definition']=='Isla Brasileña (Contestada)'
assert all(x['text']=='Contestado.' for x in contested)
assert all(x['geometry_type']=='Polygon' and x['coordinate_member_count']>0 for x in contested)
result={
 'version':1,'issue':927,'baseline_commit':BASE,'subject_id':id,'subject_name':subject['properties']['name'],
 'parent_id':subject['properties']['parent_id'],'semantic_review':subject['properties']['metadata']['semantic_review']['status'],
 'source_features':{'geoBoundaries_2017_adm1_count':len(old['features']),'igm_current_count':len(igm['features']),'igm_regular_department_count':19,'igm_contested_feature_count':2,'igm_contested_features':sorted(contested,key=lambda x:x['id'])},
 'interpretation_limits':['IGM DEPTO assignment and contested attributes document that source map representation; they do not establish mutually agreed sovereignty, a normal second administrative tier, or whether either polygon belongs inside the ordinary Artigas department boundary.','This reproduction reads geometry type and coordinate-member presence only; it does not test topology, overlap, containment, area or legal boundaries.','The 2017 geoBoundaries ADM1 feature represents Artigas as a single ordinary ADM1 unit and does not encode these two separate contested records.'],
 'controls':[positive_control,negative_control,pin_control],
 'source_hashes':{'2017_geoBoundaries':sha(blob(PARENT+'ury-gb-2017.geojson')),'igm_current':sha(blob(PARENT+'ury-igm-current.geojson')),'part25':sha(blob('data/geography/part-25.json'))}
}
raw=(json.dumps(result,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode()
(OUT/'reproduction-results.json').write_bytes(raw)
print(json.dumps({'result_sha256':sha(raw),'features_checked':2,'old_adm1':len(old['features']),'igm_features':len(igm['features']),'pins_checked':len(PINS)},sort_keys=True))

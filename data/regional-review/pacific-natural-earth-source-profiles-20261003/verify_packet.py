#!/usr/bin/env python3
"""Reproduce exact scoped identity/count and settlement inventory checks."""
import json, pathlib, hashlib
ROOT=pathlib.Path(__file__).resolve().parent
read=lambda name:json.loads((ROOT/name).read_text())
scope=read('issue-scope.json'); ids=sorted(x['id'] for x in scope['locations'])
assert ids==['ASM-4998','ASM-4999','ASM-5000','ASM-5001','ASM-5002','WLF-4995','WLF-4996','WLF-4997']
assert scope['location_count']==len(ids)==8 and scope['province_count']==len(scope['province_wrappers'])==8
assert len(scope['areas'])==3
for x in scope['locations']:
 assert len(x['parent_chain'])==5 and [p['level'] for p in x['parent_chain']]==['province','area','region','subcontinent','continent']
 assert x['containing_file']=='data/geography/part-28.json'
ne=read('natural-earth-source-profiles.json'); records={r['location_id']:r for r in ne['records']}
assert set(records)==set(ids) and len(records)==8
for ident,r in records.items():
 attrs=r['natural_earth_identity']; assert attrs['adm1_code']==ident and attrs['featurecla']=='Admin-1 states provinces' and attrs['scalerank']==10 and attrs['type']==attrs['type_en']==''
assert len(read('location-assessments.json')['assessments'])==8
assert {x['id'] for x in read('location-assessments.json')['assessments']}==set(ids)
pa=read('province-assessments.json')['assessments']; assert len(pa)==8 and {x['child_location_id'] for x in pa}==set(ids) and all(x['child_count']==1 for x in pa)
areas=read('area-assessments.json')['assessments']; assert len(areas)==3
for a in areas:
 assert set(a['assigned_member_ids'])<=set(a['full_member_ids'])
 assert a['full_member_ids']==next(x['current_full_member_ids'] for x in scope['areas'] if x['id']==a['id'])
c=read('american-samoa-census-inventory.json'); w=read('wallis-futuna-insee-inventory.json')
assert c['tiger_cousub_feature_count']==16 and c['tiger_place_feature_count']==77
assert w['village_count']==36 and w['settlement_count_by_natural_earth_unit']=={'WLF-4995':6,'WLF-4996':21,'WLF-4997':9}
assert len(read('gshhg-screen.json')['nearby_candidate_records'])==99
print(json.dumps({'status':'passed','locations':8,'parent_chains':8,'province_wrappers':8,'areas':3,'AS_cousubs':16,'AS_places':77,'WF_villages':36,'natural_earth_records':8,'GSHHG_window_records':99},indent=2))

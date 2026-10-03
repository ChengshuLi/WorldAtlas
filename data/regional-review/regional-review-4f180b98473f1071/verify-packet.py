#!/usr/bin/env python3
"""Verify source hashes, exhaustive scope accounting, and review crosswalk artifacts."""
from __future__ import annotations
import collections,gzip,hashlib,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent
checks=[]
def check(name,ok):
 checks.append((name,bool(ok)));print(('PASS' if ok else 'FAIL')+' '+name)
def read(name):return json.loads((HERE/name).read_text())
# All packet JSON must parse.
for p in HERE.rglob('*.json'):
 try:json.loads(p.read_text())
 except Exception as e:check(f'valid JSON {p.relative_to(HERE)}: {e}',False)
subject=[json.loads(x) for x in (HERE/'subject-inventory.jsonl').read_text().splitlines()]
ids=[x['id'] for x in subject]
check('144 unique assigned location assessments',len(ids)==144 and len(set(ids))==144)
check('no pending location assessments',all(x.get('assessment_status') in ('justified','correction-needed','insufficient-evidence') and x.get('assessment') for x in subject))
check('per-location ledger explicit unresolved findings',all('uncertainties' in x for x in subject))
check('settlement disposition assessed for all 144 IDs',all(x.get('settlement_disposition') for x in subject))
counts=collections.Counter(x['assessment_status'] for x in subject)
check('location classification totals are 99/45',counts=={'justified':99,'insufficient-evidence':45})
prov=read('province-assessments.json');areas=read('area-assessments.json')
check('47 province assessments',len(prov['records'])==47 and prov['scope_count']==47)
check('all 47 province records classified',all(x['assessment_status'] in ('justified','correction-needed','insufficient-evidence') and x['assessment'] for x in prov['records']))
check('8 area assessments',len(areas['records'])==8 and areas['scope_count']==8)
check('all 8 area records classified',all(x['assessment_status'] in ('justified','correction-needed','insufficient-evidence') and x['assessment'] for x in areas['records']))
mdg=read('madagascar-2018-district-admin-crosswalk.json')
check('119 unique Madagascar district joins',len(mdg['records'])==119 and len({x['OCHA_ADM2_PCODE'] for x in mdg['records']})==119 and all(x['OCHA_ADM2_PCODE'] for x in mdg['records']))
check('complete Madagascar OCHA administrative totals',mdg['communes_total']==1579 and mdg['fokontany_total']==17465 and all(x['ADM3_communes_2018']>0 and x['ADM4_fokontany_2018']>0 for x in mdg['records']))
syc=read('seychelles-2019-region-district-crosswalk.json')
check('8 Seychelles region joins and 27 ADM3 districts',len(syc['records'])==8 and sum(x['2019_district_rows_assigned_to_region'] for x in syc['records'])==27)
cod=read('madagascar-current-COD-AB-review.json');pi=cod['partition_integrity']
check('120 COD-AB ADM2 source units, 119 name matches and one unassigned',cod['source_adm2_count']==120 and cod['current_assigned_mdg_adm2_count']==119 and cod['current_named_adm2_matches']==119 and len(cod['new_unmatched_source_adm2'])==1)
check('no COD-AB ADM2 source interior overlap >0.001km2',not pi['source_ADM2_interior_overlaps_over_0_001_km2'])
check('COD-AB ADM1 source count 24 vs current parents 22',cod['source_adm1_count']==24 and cod['current_parent_name_count']==22)
followups=read('followups.json')
check('three blocked bounded follow-ups linked to #482',sorted(set(x.get('created_issue') for x in followups['recommendations']))==[632,633,634] and all('bounded_scope' in x and x.get('required_evidence') for x in followups['recommendations']))
components=read('madagascar-disconnected-component-review.json')
check('55 Madagascar disconnected component leads screened',components['candidate_count']==55 and components['candidates_with_L1_intersection']==0)
check('all component leads have individual source names and positions',all(x.get('source_name') and x.get('source_pcode') and x.get('component_index') is not None and x.get('component_centroid_lonlat') for x in components['candidates']))
# Verify retained source hashes recorded in sources.json.
sources=read('sources.json');hash_fail=[];hash_count=0
for entry in sources.get('source_sets',[]):
 for fnkey,hashkey in [('retained_geometry_file','geometry_sha256'),('metadata_file','metadata_sha256'),('citation_file','citation_sha256')]:
  fn=entry.get(fnkey);expected=entry.get(hashkey)
  if fn and expected:
   p=HERE/fn;hash_count+=1
   if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:hash_fail.append((fn,'missing/mismatch',expected))
for entry in sources.get('additional_sources',[]):
 items=[]
 if isinstance(entry.get('resources'),list):items+=entry['resources']
 if entry.get('resource'):items.append(entry['resource'])
 for item in items:
  fn=item.get('retained_file')
  if not fn:continue
  p=HERE/fn;hash_count+=1
  if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=item.get('sha256'):hash_fail.append((fn,'missing/mismatch',item.get('sha256')))
check(f'all {hash_count} retained source hashes verified',not hash_fail)
if hash_fail:
 for x in hash_fail:print('HASH ERROR',x)
# Retained COD-AB gzip streams decompress to exact recorded ZIP member bytes.
for raw,gz,expected in [('mdg_admin2.geojson','mdg-COD-AB-ADM2-2026-reviewed.geojson.gz','f4a437a737e7b9c71b19db1eb41fc39abd9579aa95505471c6149b06be98c8b9'),('mdg_admin1.geojson','mdg-COD-AB-ADM1-2026-reviewed.geojson.gz','5820a206ddcef5a48385dba8f0eee9f5a23db2927580c7afe109c564f4edc47f')]:
 actual=hashlib.sha256(gzip.decompress((HERE/'sources'/gz).read_bytes())).hexdigest();check(f'exact restored COD-AB member bytes: {raw}',actual==expected)
print(f'CHECKS {sum(ok for _,ok in checks)}/{len(checks)}')
sys.exit(0 if all(ok for _,ok in checks) else 1)

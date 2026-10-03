#!/usr/bin/env python3
"""Verify issue 492 scope, source byte hashes and complete row accounting."""
import gzip,hashlib,json,pathlib
HERE=pathlib.Path(__file__).resolve().parent
scope=json.loads((HERE/'scope.json').read_text()); a=json.loads((HERE/'assessment.json').read_text()); reg=json.loads((HERE/'sources.json').read_text())
ids=scope['member_location_ids']; rows=a['locations']
assert len(ids)==194 and len(set(ids))==194
assert {x['location_id'] for x in rows}==set(ids) and len(rows)==194
assert all(x['full_parent_chain'] and x['decision'] for x in rows)
assert all(x['source_identity']['source_id']=='gb:COL:ADM2' and x['source_identity']['geoBoundaries_shape_id']==x['source_identity']['original_id'] for x in rows)
assert all(x['source_identity']['name_exact'] for x in rows)
assert all(x['settlement_review'].startswith('unresolved:') and x['disconnected_land_review'].startswith('unresolved:') for x in rows)
assert len(a['provinces'])==4 and sum(p['assigned_in_scope'] for p in a['provinces'])==194
assert all(p['decision']=='insufficient_evidence' for p in a['provinces'])
assert a['counts']=={'assessed':194,'source_ID_matches':194,'exact_source_name_matches':194,'justified':0,'correction_needed':0,'insufficient_evidence':194}
for s in reg['sources']:
 if s['id']=='geoboundaries-col-adm2-2020':
  p=HERE/s['retained_data']['path']; b=p.read_bytes();raw=gzip.decompress(b)
  assert len(b)==s['retained_data']['compressed_bytes'] and hashlib.sha256(b).hexdigest()==s['retained_data']['compressed_sha256']
  assert len(raw)==s['retained_data']['uncompressed_bytes'] and hashlib.sha256(raw).hexdigest()==s['retained_data']['uncompressed_sha256']
  d=json.loads(raw); assert len(d['features'])==1122
 if s['id']=='geoboundaries-col-adm2-metadata':
  b=(HERE/s['retained_path']).read_bytes();assert len(b)==s['bytes'] and hashlib.sha256(b).hexdigest()==s['sha256']
 if s['id']=='geoboundaries-col-adm1-parent-reference':
  p=HERE/s['retained_admin1_geojson']['path'];b=p.read_bytes();raw=gzip.decompress(b)
  assert len(b)==s['retained_admin1_geojson']['bytes_compressed'] and hashlib.sha256(b).hexdigest()==s['retained_admin1_geojson']['sha256_compressed']
  assert len(raw)==s['retained_admin1_geojson']['bytes_uncompressed'] and hashlib.sha256(raw).hexdigest()==s['retained_admin1_geojson']['sha256_uncompressed']
 for key in ('retained_metadata',):
  if key in s:
   b=(HERE/s[key]['path']).read_bytes();assert len(b)==s[key]['bytes'] and hashlib.sha256(b).hexdigest()==s[key]['sha256']
print(json.dumps({'verified':True,'assigned':194,'source_identity_matches':194,'province_cohorts':{p['name']:p['assigned_in_scope'] for p in a['provinces']},'source_registry_entries':len(reg['sources']),'all_location_rows_decisioned':194},ensure_ascii=False,indent=2))

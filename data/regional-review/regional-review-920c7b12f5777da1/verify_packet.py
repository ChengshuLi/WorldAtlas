#!/usr/bin/env python3
"""Verify the immutable scope/results and hashes of inputs retained in packet #376."""
from pathlib import Path
import gzip, hashlib, json, sys
P=Path(__file__).resolve().parent
scope=json.loads((P/'scope.json').read_text())
summary=json.loads((P/'findings/assessment-summary.json').read_text())
rows=[json.loads(s) for s in (P/'findings/location-assessments.jsonl').read_text().splitlines() if s.strip()]
ids=scope['member_location_ids']
assert len(ids)==188 and len(set(ids))==188
assert summary['member_count']==188 and summary['issue']==376
assert len(rows)==188 and [r['location_id'] for r in rows]==ids
assert len({r['location_id'] for r in rows})==188
counts={}
for row in rows: counts[row['classification']]=counts.get(row['classification'],0)+1
assert counts==summary['classifications']=={'justified':152,'insufficient-evidence':35,'correction-needed':1},counts
assert summary['igvsb_named_boundary_issue_feature_count']==69
assert summary['igvsb_overlap_zone_feature_count']==65
assert summary['igvsb_no_jurisdiction_zone_feature_count']==4
assert summary['screening_subsets']=={
 'municipal_role_parent_justified':152,
 'municipal_role_parent_insufficient':31,
 'physical_fragments_insufficient':4,
 'pseudo_territorial_unit_correction_needed':1,
 'municipal_rows_intersecting_zone_features':35,
 'zone_hit_rows_classified_justified_for_role_parent_only':31,
 'zone_hit_rows_classified_insufficient':4,
 'municipal_same_name_2016_match_but_parent_cover_below_0_98':24,
 'municipal_no_exact_normalized_name_match_in_2016_comparator':7
}
assert sum(r['source_id']=='gb:VEN:ADM2' for r in rows)==184
assert sum(r['source_id'] in {'resolve:464','resolve:466','resolve:490','resolve:572'} for r in rows)==4
assert summary['area_scope_partial'] is True and summary['issue_area_owned_member_count']==188 and summary['issue_area_full_member_count']==327
assert all(r.get('rationale') and r.get('uncertainty') and r.get('boundary_status') for r in rows)
assert next(r for r in rows if r['classification']=='correction-needed')['location_id']=='gb:VEN:ADM2:92452058B25675040918260'
register=json.loads((P/'source-register.json').read_text())
retained={}
for item in register['sources']:
 paths=item.get('retained_files') or ([item['retained_file']] if item.get('retained_file') else [])
 hashes=item.get('sha256_by_file') or {}
 for rel in paths:
  expected=hashes.get(rel[len('source/'):]) or item.get('sha256')
  if expected is None: raise AssertionError(f'no recorded hash: {rel}')
  path=P/rel
  if not path.exists(): raise AssertionError(f'register says retained but missing: {rel}')
  raw= gzip.decompress(path.read_bytes()) if rel.endswith('.gz') else path.read_bytes()
  actual=hashlib.sha256(raw).hexdigest()
  if actual!=expected: raise AssertionError(f'decompressed hash mismatch {rel}: {actual} != {expected}')
  key=rel.split('/')[-1]
  container_expected=item.get('container_sha256') or item.get('container_sha256_by_file',{}).get(key)
  if container_expected and hashlib.sha256(path.read_bytes()).hexdigest()!=container_expected: raise AssertionError(f'container hash mismatch {rel}')
  retained[rel]=actual
receipts={}
for rel, expected in register['response_receipts'].items():
 path=P/rel
 assert path.is_file(), f'missing response receipt: {rel}'
 actual=hashlib.sha256(path.read_bytes()).hexdigest()
 assert actual==expected, f'receipt hash mismatch {rel}: {actual} != {expected}'
 receipts[rel]=actual
for item in register['supporting_records']:
 path=P/item['retained_file']
 assert path.is_file(), f'missing supporting record: {item["retained_file"]}'
 actual=hashlib.sha256(path.read_bytes()).hexdigest()
 assert actual==item['sha256'], f'supporting record hash mismatch {item["retained_file"]}'
# Unlicensed/uncleared files are explicitly absent from the committed packet and restorably pinned.
for item in register['sources']:
 if item['id'] in {'IGVSB 2016 municipal boundaries','Venezuelan Organic Law on Municipal Public Power, Article 2'}:
  assert item['retained_file'] is None and item['sha256']
  assert 'restoration' in item
for filename in ['igvsb-municipal-boundaries-2024-provita.zip','municipal-law.pdf']:
 assert not (P/'source'/filename).exists(), f'uncleared source bytes must not be committed: {filename}'
assert (P/'restore_inputs.sh').is_file()
print(json.dumps({'issue':376,'members':len(rows),'classifications':counts,'retained_source_files_hash_checked':len(retained),'response_receipts_hash_checked':len(receipts),'supporting_records_hash_checked':len(register['supporting_records']),'area_scope_partial':True,'boundary_and_region_approval':'not established by this verifier'},indent=2))

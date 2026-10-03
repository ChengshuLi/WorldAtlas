#!/usr/bin/env python3
"""Reproducible scope, source-hash and land-screen evidence checks for issue #134."""
import hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
read=lambda p: json.loads((ROOT/p).read_text())
base=read('baseline-extract.json'); assessment=read('assessment.json'); manifest=read('sources-manifest.json'); screen=read('gshhg-land-screen.json'); issue=json.loads((ROOT/'issue-metadata.json').read_text()); claim=read('claim-receipt.json')['claim']
ids=set(base['scope_location_ids'])
block=re.search(r'<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->',issue['body'],re.S)
assert issue['number']==134 and block, 'actual issue metadata missing machine scope'
spec=json.loads(block.group(1))
assert spec['mode']=='geography' and spec['max_prs']==2 and spec['owned_paths']==['data/regional-review/regional-review-a5b86fc6ff2463cd/']
assert {'kind:work-item','type:geography'} <= {x['name'] for x in issue['labels']}
assert claim['active'] and claim['issue_number']==134 and claim['mode']=='geography' and claim['owned_paths']==spec['owned_paths']
assert len(ids)==24 and len(assessment['locations'])==24
assert {x['location_id'] for x in assessment['locations']}==ids
assert len(assessment['provinces'])==24 and {x['location_id'] for x in assessment['provinces']}==ids
assert len(assessment['areas'])==6 and assessment['scope_audit']['all_areas_with_owned_scope_inventoried']
assert all(len(base['complete_parent_chains'][i])>=6 and base['complete_parent_chains'][i][0]['id']==i for i in ids)
assert all(x['classification'] in {'justified-with-caveat','correction-needed','insufficient-evidence'} for x in assessment['locations'])
assert all(x['classification']=='insufficient-evidence' for x in assessment['provinces']+assessment['areas'])
for source in manifest['retained_sources']:
 for file in source.get('files',[]):
  p=ROOT/file['path']; raw=p.read_bytes(); assert len(raw)==file['bytes'],(p,len(raw),file['bytes']); assert hashlib.sha256(raw).hexdigest()==file['sha256'],p
assert screen['candidate_records_in_windows']==1463 and screen['positive_location_overlap_records']==45
assert set(screen['location_metrics'])==ids
assert set(screen['nearest_unmatched_land_candidates_per_location'])==ids
assert all(len(x)==10 for x in screen['nearest_unmatched_land_candidates_per_location'].values())
assert len(screen['all_gshhg_records_overlapping_locations'])==45
print(json.dumps({'locations':len(ids),'provinces':len(assessment['provinces']),'areas':len(assessment['areas']),'source_hashes_verified':sum(len(s.get('files',[])) for s in manifest['retained_sources']),'gshhg_candidates':screen['candidate_records_in_windows'],'gshhg_overlap_rows':len(screen['all_gshhg_records_overlapping_locations']),'result':'PASS'},indent=2))

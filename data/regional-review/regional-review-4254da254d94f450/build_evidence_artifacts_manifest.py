#!/usr/bin/env python3
"""Hash generated issue #485 review outputs separately from retained source inputs."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
paths=['assessment.json','bc-admin-group-geometry-screen.json','bc-area-union-screen.json','gshhg-scope-screen.json','ibc-bc-neighbor-screen.json','followups.json']
records=[]
for name in paths:
 b=(P/name).read_bytes();d=json.loads(b)
 if name=='assessment.json':count=len(d['locations']);units='assigned location rows'
 elif name=='bc-admin-group-geometry-screen.json':count=len(d['locations']);units='administrative groups; source members '+str(d['source_member_count'])
 elif name=='bc-area-union-screen.json':count=len(d['per_cd_assigned_area_coverage_pct']);units='2021 Census Division coverage ratios plus one BC union screen'
 elif name=='gshhg-scope-screen.json':count=d['scope_count'];units='assigned location land screens'
 elif name=='ibc-bc-neighbor-screen.json':count=len(d['selected_bc_adjacent_sections']);units='selected IBC section screens'
 else:count=len(d['items']);units='bounded issue follow-ups'
 records.append({'path':name,'bytes':len(b),'text_lines':b.count(b'\n'),'sha256':hashlib.sha256(b).hexdigest(),'record_count':count,'record_units':units})
out={'issue':485,'manifest_generated_utc':'2026-10-03','purpose':'Generated assessment and review-output byte/record accounting, separate from the source/input files in sources-manifest.json. Exact SHA-256 digests are over retained output bytes.','artifacts':records,'totals':{'artifact_file_count':len(records),'generated_artifact_bytes':sum(r['bytes'] for r in records),'generated_text_lines':sum(r.get('text_lines',0) for r in records),'assessment_location_rows':222,'bc_group_source_members':376,'bc_groups':19,'ecoregion_location_ids':38,'ecoregion_source_polygons':41,'gshhg_scope_rows':222,'ibc_section_rows':5}}
(P/'evidence-artifacts-manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out['totals'],indent=2))

#!/usr/bin/env python3
"""Build the supplemental whole-file review index for legacy issue #471."""
import hashlib,json
from pathlib import Path
OWN=Path(__file__).resolve().parent
REPO=OWN.parents[2]
index_path=OWN/'evidence-review-index.json'
scope=json.loads((OWN/'issue-scope-pinned.json').read_text(encoding='utf-8'))
receipt=json.loads((OWN/'baseline-receipt.json').read_text(encoding='utf-8'))
files=[]
for path in sorted(x for x in OWN.rglob('*') if x.is_file() and x!=index_path):
 data=path.read_bytes()
 files.append({'path':path.relative_to(REPO).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
result={'version':1,'kind':'supplemental evidence review index; legacy issue scope, not a policy-mandated evidence-quality v1 manifest','issue':471,'issue_url':'https://github.com/ChengshuLi/WorldAtlas/issues/471','baseline_commit':receipt['baseline_commit'],'issue_scope_sha256':hashlib.sha256((OWN/'issue-scope-pinned.json').read_bytes()).hexdigest(),'region_release':scope['release'],'macro_certificate_sha256':scope['macro_certificate_sha256'],'frozen_region_geometry_sha256':scope['frozen_region_geometry_sha256'],'frozen_region_member_ids_sha256':scope['frozen_region_member_ids_sha256'],'exact_subject_count':scope['location_count'],'exact_subject_ids_sha256_lf_separated':hashlib.sha256(('\n'.join(scope['member_location_ids'])+'\n').encode()).hexdigest(),'file_count_excluding_this_index':len(files),'files':files}
index_path.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'index':str(index_path),'files':len(files)},indent=2))

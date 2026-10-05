#!/usr/bin/env python3
"""Create a whole-file provenance index for independent review of legacy issue #71."""
import csv,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
REPO=ROOT.parents[2]
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
issue=json.load(open(ROOT/'issue-71-api.json')); scope=json.load(open(ROOT/'scope.json'))
rows=list(csv.DictReader(open(ROOT/'assessment.csv',newline='')))
scope_rows=list(csv.DictReader(open(ROOT/'scope-assessment.csv',newline='')))
files=[]
for p in sorted(ROOT.rglob('*')):
 if not p.is_file() or p==ROOT/'checks/evidence-review-index.json':continue
 files.append({'path':p.relative_to(REPO).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
baseline_inputs=[]
for p in sorted((REPO/'data/geography').glob('part-*.json'))+[REPO/'data/hierarchy.json']:
 baseline_inputs.append({'path':p.relative_to(REPO).as_posix(),'git_commit':base_commit,'bytes':p.stat().st_size,'sha256':sha(p)})
index={
 'version':1,
 'issue':71,
 'issue_url':issue.get('html_url','https://github.com/ChengshuLi/WorldAtlas/issues/71'),
 'legacy_evidence_policy':'Issue #71 predates the 2026-10-04 evidence-quality enforcement; this bounded whole-file index binds the exact scope, source snapshots, methods, generated result files and limits for the required independent review.',
 'author_worker_id':'codex-01a10948-7d38-75d0-bc01-4cc28ea41f49',
 'branch':'geography/regional-review-ef67318527f5f3a3',
 'baseline_commit':base_commit,
 'baseline_files_read_by_reproduction':baseline_inputs,
 'scope':{'member_count':len(scope['member_location_ids']),'member_location_ids_sha256':scope['member_location_ids_sha256'],'region_release':scope['release'],'frozen_region_geometry_sha256':scope['frozen_region_geometry_sha256'],'frozen_region_member_ids_sha256':scope['frozen_region_member_ids_sha256'],'macro_certificate_sha256':scope['macro_certificate_sha256'],'location_classification_counts':{v:sum(r['classification']==v for r in rows) for v in ('justified','correction-needed','insufficient-evidence')},'area_and_province_scope_classification_counts':{v:sum(r['classification']==v for r in scope_rows) for v in ('justified','correction-needed','insufficient-evidence')}},
 'review_outcome':'All 226 assigned locations are insufficient-evidence. The Istanbul province workload is correction-needed because an official current roster lists 39 districts and the baseline contains only 7. No region completeness/tier approval or automatic addition of the other 32 candidates.',
 'source_inventory_path':(ROOT/'source-files.json').relative_to(REPO).as_posix(),
 'files':files,
 'independent_review_must_inspect':['all 226 subject rows and exact source feature IDs','actual source vintage, role, completeness, license and parent information','Cyprus baseline vs geoBoundaries vs official DLS crosswalk limitations','Greek 2010 to ELSTAT 2021 census crosswalk method and license caveat','Turkey ADM2 973 versus metadata 999 source-level count discrepancy','official Istanbul 39-name to pinned source ID join: 7 present and 32 absent','Natural Earth four map-unit meanings and limits','component/scale/neighbor screens and their non-certification limits','issue #71 acceptance, the five blocked follow-ups and preserved pins']
}
path=ROOT/'checks/evidence-review-index.json'
path.write_text(json.dumps(index,indent=2,ensure_ascii=False)+'\n')
print('indexed',len(files),'packet files and',len(baseline_inputs),'exact baseline inputs; subjects',len(rows),'index_sha256',sha(path))

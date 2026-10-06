#!/usr/bin/env python3
"""Build whole-file input/output inventories and evidence manifest."""
import csv, hashlib, json, pathlib, subprocess

ROOT = pathlib.Path.cwd()
D = ROOT / 'data/regional-review/south-america-b4-area-validation-20261006'
OUT = D / 'output'
BASE = '93c901e1c0b44073233fd3d48d403985a0cf2c52'
WORKER = '01a10947-7d6e-7ba2-98a1-a9f91dedabfc'
sha = lambda b: hashlib.sha256(b).hexdigest()
scope = json.loads((D/'scope.json').read_text())
report = json.loads((OUT/'report.json').read_text())
source_register = json.loads(subprocess.check_output(['git','show',BASE+':data/regional-review/regional-review-9b6d6a9ecf8f6c3b/source/source-register.json']))

baseline_paths = [
 'data/hierarchy.json','data/world-index.json',
 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/scope/embedded-workload-scope.json',
 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/province-review.csv',
 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/area-review.csv',
 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/area-source-crosswalk.csv',
 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/reproduce-area-source-crosswalk.py',
 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/scope/companion-workload-scopes.json',
 'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/source/source-register.json'] + [f'data/geography/part-{i}.json' for i in (0,2,20,25,28,29)]
files=[]
for p in baseline_paths:
 b=subprocess.check_output(['git','show',f'{BASE}:{p}'])
 files.append({'path':p,'bytes':len(b),'sha256':sha(b),'hash_kind':'file-bytes'})
scope_pins=scope['issue_evidence_quality']['pins']
pin_files={
 'hierarchy':'data/hierarchy.json','world_index':'data/world-index.json',
 'original_scope':'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/scope/embedded-workload-scope.json',
 'parent_rows':'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/province-review.csv',
 'area_rows':'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/area-review.csv',
 'area_crosswalk':'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/area-source-crosswalk.csv',
 'area_reproducer':'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/reproduce-area-source-crosswalk.py',
 'companion_scopes':'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/scope/companion-workload-scopes.json',
 'source_register':'data/regional-review/regional-review-9b6d6a9ecf8f6c3b/source/source-register.json'}
assert set(scope_pins)==set(pin_files)
external=[{'path':'restored:/tdwg/tblLevel3.txt','bytes':9933,'sha256':'7eaf281dfbdca610c93938326c333d7c62d8e82ce3cba63b299d5a3a01d0003f','retrieved_at':'2026-10-06'}, {'path':'restored:/tdwg/tblLevel4.txt','bytes':17137,'sha256':'6fa350a0bb5939df0c665ae6cf253ddb0aa85fef6daa684c87ba400faf93b1c2','retrieved_at':'2026-10-06'}]
(OUT/'input-inventory.json').write_text(json.dumps({'baseline_commit':BASE,'files':files,'external_inputs':external},indent=2)+'\n')

second_dir=D/'scratch/run-two-output'
second_names=[p.name for p in second_dir.iterdir() if p.is_file()]
first={name:sha((OUT/name).read_bytes()) for name in second_names}
second={name:sha((second_dir/name).read_bytes()) for name in second_names}
assert first==second, 'Two complete output runs differ'
(OUT/'reproducibility.json').write_text(json.dumps({'method_id':'exact-roster-and-ancestry','kind':'reproducibility','outcome':'passed','runs':2,'outputs_sha256':first,'run_one_sha256':sha(json.dumps(first,sort_keys=True,separators=(',',':')).encode()),'run_two_sha256':sha(json.dumps(second,sort_keys=True,separators=(',',':')).encode())},indent=2)+'\n')

subject_files={r['subject_id']:r['source_part'] for r in csv.DictReader((OUT/'subject-parent-area.csv').open())}
outputs=[]
for p in sorted(x for x in D.rglob('*') if x.is_file() and 'scratch' not in x.relative_to(D).parts and x.name!='evidence-quality.json'):
 b=p.read_bytes(); outputs.append({'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':sha(b),'hash_kind':'file-bytes'})
output_map={x['path']:x for x in outputs}
input_digest=output_map['data/regional-review/south-america-b4-area-validation-20261006/output/input-inventory.json']['sha256']

def source(id,url,role,vintage,status,terms,restoration,limit,verification='unverified'):
 return {'id':id,'url':url,'role':role,'vintage':vintage,'retrieved_at':'2026-10-06','license':{'status':status,'terms':terms},'retention':'restoration-only','verification':verification,'restoration':restoration,'limit':limit,'temporal_status':'reference'}

sources=[
 source('atlas-pinned-ancestry','https://github.com/ChengshuLi/WorldAtlas/tree/'+BASE,'Native location IDs and pinned parent/area hierarchy used for roster checks.','Atlas main baseline 2026-10-06','unknown','Whole-file evidence is pinned by Git SHA-256; source license information remains in the original packet.','Read the baseline Git blobs listed under baseline.files at commit '+BASE+'.','Internal ancestry does not prove current legal borders or completeness.','verified'),
 source('tdwg-wgsrpd','https://github.com/tdwg/wgsrpd/tree/52da7828aba9d461dd133c27b3bd7a4407161f54/109-488-1-ED/2nd%20Edition','Level 3/4 botanical names and codes from the existing crosswalk.','Second Edition, commit 52da7828aba9d461dd133c27b3bd7a4407161f54','unknown','Reuse terms not located; raw files are not redistributed.','Restore the raw Level 3 and Level 4 tables at that commit and verify SHA-256 values in output/input-inventory.json.','Botanical recording units do not establish administrative hierarchy or political boundaries.'),
 source('geoboundaries-chile-adm3','https://github.com/wmgeolab/geoBoundaries/tree/9469f09592ced973a3448cf66b6100b741b64c0d','Historical Chile ADM3 source for the existing crosswalk.','Reference year 2020; source commit 9469f09592ced973a3448cf66b6100b741b64c0d','redistributable','geoBoundaries metadata reports CC BY 3.0 IGO; attribution required.','Restore 171783952-byte source and verify SHA-256 f3833ce1965394ae705e3793b50bdd007775b43da604251871deffed04f3bffd.','Full-country source exceeds input cap; existing one-to-one feature/name matching is not current legal boundary proof.'),
 source('subdere-chile-2023','https://ide.subdere.gov.cl/descargas/SHP/Limite_DPA_03082023.rar','Official Chile DPA source for current vintage and roster comparison.','2023 archive, updated 2023-08-03','unknown','No reuse license located in prior review.','Restore 262380302-byte archive and verify SHA-256 4c8dd01ca4ca7d8b111dac78b88cc8ac64c1af7b8ebe0c85a21eaab337ae3fd3.','Prior RAR5 extraction failed; roster/geometry audit and reuse clearance remain open.'),
 source('geoboundaries-paraguay-adm2','https://github.com/wmgeolab/geoBoundaries/tree/f549eab25a258603ea32c9dc6cb11b7657796478','Historical Paraguay ADM2 source for existing crosswalk.','Reference year 2012; commit f549eab25a258603ea32c9dc6cb11b7657796478','redistributable','geoBoundaries metadata reports CC BY 4.0; attribution required.','Restore 45589273-byte source and verify SHA-256 d42bd1f910070bf805e32dc46708230c91f58902a3c8792eda60928b22362858.','Historical roster; full source exceeds input cap and does not prove current legal alignment.'),
 source('ine-paraguay-2022','https://www.ine.gov.py/microdatos/cartografia-digital-2022.php','Official Paraguay statistical cartography and attributes.','Cartografía Digital 2022','redistributable','INE public information license requires attribution; prior use was attribute-only.','Retrieve official page and district attribute service; prior response hash is 3cf026dd552ac4128f97b68acbdb8e06aba08afdde13fa208185cb07447ae228.','INE describes the DPA lines as referential for statistics, not legal boundaries.'),
 source('paraguay-cadastre-study','https://www.catastro.gov.py/public/967e7c_ESTUDIO%20DE%20L%C3%8DMITES%20DISTRITALES%20DE%20LA%20REP%C3%9ABLICA%20DEL%20PARAGUAY.pdf','Primary technical/legal-context source for district limits.','Retrieved 2026-10-05','unknown','No redistribution terms located.','Restore 4079648-byte official PDF and verify SHA-256 c07fd97db9ee7063e377dd6df14f032847c16296a9c8354fe1179d3203762bd1.','Restoration-only research lead; no current district limits adjudicated.')]

metric_ids=['issue_1124_subjects','native_subject_matches','distinct_parent_ids','parent_rows','parent_assignments','companion_issue_444_members','companion_issue_446_members','companion_native_members_checked','companion_area_membership_mismatches','source_crosswalk_rows','source_crosswalk_reproduced_runs','chile_central_issue_members','chile_central_native_members','chile_north_issue_members','chile_north_native_members','chile_south_issue_members','chile_south_native_members','juan_fernandez_is_issue_members','juan_fernandez_is_native_members','paraguay_issue_members','paraguay_native_members']
metrics=[]
for k in metric_ids:
 unit='subjects' if ('members' in k or k in ['issue_1124_subjects','native_subject_matches','parent_assignments','companion_issue_444_members','companion_issue_446_members','companion_native_members_checked']) else 'rows' if k in ['distinct_parent_ids','parent_rows','source_crosswalk_rows'] else 'runs' if 'runs' in k else 'mismatches'
 metrics.append({'id':k,'value':report['metrics'][k],'unit':unit,'vintage':'baseline','input_sha256':input_digest,'evaluation_commit':BASE})

receipts=[{'path':o['path'],'status':'added'} for o in outputs]
receipts.append({'path':'data/regional-review/south-america-b4-area-validation-20261006/evidence-quality.json','status':'added'})
manifest={'version':1,'issue':1124,'lane':'geography','worker_id':WORKER,'subject_ids':scope['subject_ids'],'subject_ids_sha256':scope['subject_ids_sha256'],'baseline':{'commit':BASE,'files':files,'pins':scope_pins,'pin_files':pin_files,'subject_files':subject_files},'sources':sources,'outputs':outputs,'methods':[{'id':'exact-roster-and-ancestry','kind':'measurement','description':'Verify the exact pinned issue roster, parent membership and native hierarchy; check neighboring snapshots and reproduce the existing crosswalk twice.','software':'Python 3 standard library; Git immutable objects; Node.js 24 evidence validator.','units':'Subject IDs, parent/area assignments, descendant counts and output hashes.'}],'metrics':metrics,'summaries':[{'metric_id':'issue_1124_subjects','value':215,'unit':'subjects'},{'metric_id':'distinct_parent_ids','value':39,'unit':'rows'},{'metric_id':'companion_native_members_checked','value':660,'unit':'subjects'}],'conclusions':[{'text':'All 215 issue subjects map to the exact 39 parent rows and five area ancestries in the pinned Atlas baseline.','status':'supported','source_ids':['atlas-pinned-ancestry']},{'text':'The five area descendant counts match the pinned Atlas hierarchy and adjacent issue snapshots exhaust those target-area memberships.','status':'supported','source_ids':['atlas-pinned-ancestry']},{'text':'Existing crosswalk source labels do not establish current legal boundaries or completeness for Chile or Paraguay.','status':'unresolved','source_ids':['tdwg-wgsrpd','geoboundaries-chile-adm3','subdere-chile-2023','geoboundaries-paraguay-adm2','ine-paraguay-2022','paraguay-cadastre-study']}],'stages':{'research':'complete','implementation':'not-proposed','geographic_approval':'unapproved'},'commands':['python3 data/regional-review/south-america-b4-area-validation-20261006/validate_area_crosswalk.py --level3 PATH/tblLevel3.txt --level4 PATH/tblLevel4.txt --output-dir data/regional-review/south-america-b4-area-validation-20261006/output','node scripts/evidence-quality.mjs data/regional-review/south-america-b4-area-validation-20261006/evidence-quality.json','Check actual PR body and live premerge evidence manifest before submission.'],'validation':[{'method_id':'exact-roster-and-ancestry','kind':'positive-control','outcome':'passed','evidence_path':'data/regional-review/south-america-b4-area-validation-20261006/output/positive-control.json'},{'method_id':'exact-roster-and-ancestry','kind':'negative-control','outcome':'passed','evidence_path':'data/regional-review/south-america-b4-area-validation-20261006/output/negative-control.json'},{'method_id':'exact-roster-and-ancestry','kind':'reproducibility','outcome':'passed','evidence_path':'data/regional-review/south-america-b4-area-validation-20261006/output/reproducibility.json'}],'metric_bindings':[{'metric_id':k,'path':'data/regional-review/south-america-b4-area-validation-20261006/output/report.json','json_pointer':'/metrics/'+k} for k in metric_ids],'change_receipts':receipts,'rendered_tables':[]}
(D/'evidence-quality.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('manifest written',len(subject_files),'subjects',len(outputs),'outputs')

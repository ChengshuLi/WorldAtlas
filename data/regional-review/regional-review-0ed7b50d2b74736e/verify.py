#!/usr/bin/env python3
"""Rebuild and verify the exact #478 source-evidence packet outputs."""
from __future__ import annotations
import csv, gzip, hashlib, json, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
REPO=ROOT.parents[2]
COMMIT='e570f16236928fd5c5e359ab96e81399b55ccb26'
EXPECTED={
 'assessment.csv':226,
 'source-vintage-crosswalk.csv':1340,
 'geometry-components.csv':258,
 'settlement-point-anomalies.csv':504,
 'settlement-source-counts.csv':228,
 'city-name-spatial-screen.csv':1796,
 'current-unit-inventory.csv':836,
 'administrative-scope.csv':27,
 'admin1-source-comparison.csv':56,
 'neighbor-edge-screen.csv':11,
 'province-scale-screen.csv':228,
 'national-source-inventory.csv':3,
 'generated-data-accounting.json':None,
}
def check(ok,msg):
 if not ok: raise AssertionError(msg)
def sha(data):return hashlib.sha256(data).hexdigest()
def rows(name):return list(csv.DictReader((ROOT/name).open(encoding='utf-8')))
def outputs_hashes():return {n:sha((ROOT/n).read_bytes()) for n in EXPECTED}

scope=json.loads((ROOT/'scope.json').read_text())
issue=json.loads((ROOT/'issue-metadata.json').read_text())
ids=scope['member_location_ids']
check(len(ids)==226 and len(set(ids))==226,'issue subject roster must contain 226 unique members')
check(scope['published_region_baseline']['baseline_git_commit']==COMMIT,'truthful ancestor commit changed')
check(issue['number']==478 and issue['html_url'].endswith('/issues/478'),'issue metadata is not the actual #478 snapshot')
check(sha((ROOT/'issue-scope-pinned.json').read_bytes())==scope['issue_scope_sha256'],'pinned issue scope hash mismatch')
check(json.loads((ROOT/'issue-scope-pinned.json').read_text())['member_location_ids']==ids,'issue-pinned roster mismatch')
for path,want in scope['published_region_baseline']['authoritative_snapshot_hashes'].items():
 raw=subprocess.check_output(['git','show',f'{COMMIT}:{path}'],cwd=REPO)
 check(sha(raw)==want,f'ancestor baseline file hash mismatch: {path}')
projection=json.loads(gzip.decompress(subprocess.check_output(['git','show',f'{COMMIT}:data/macro-foundation/current-membership-projection.json.gz'],cwd=REPO)))
byid={x['id']:x for x in projection['locations']}
baseline=json.loads((ROOT/'baseline-members.json').read_text())
check([x['id'] for x in baseline]==ids,'baseline subject order differs from issue roster')
check(baseline==[byid[x] for x in ids],'baseline members/chains do not reproduce from ancestor projection')
receipt=json.loads((ROOT/'claim-receipt.json').read_text())
claim=receipt.get('claim',{})
check(receipt.get('issue_number')==478 and claim.get('worker_id') and claim.get('claim_id') and claim.get('active'),'reservation receipt missing issue/worker/claim')

# Every retained lawful source is checked against its compressed-byte receipt.
acq=json.loads((ROOT/'sources/acquisition.json').read_text())
def walk(x):
 if isinstance(x,dict):
  if isinstance(x.get('file'),str) and x.get('gzip_sha256'):
   path=ROOT/x['file'];data=path.read_bytes()
   check(len(data)==x['gzip_bytes'],f'compressed byte count mismatch: {x["file"]}')
   check(sha(data)==x['gzip_sha256'],f'compressed SHA mismatch: {x["file"]}')
   raw=gzip.decompress(data)
   check(len(raw)==x['restored_bytes'],f'restored byte count mismatch: {x["file"]}')
   check(sha(raw)==x['restored_sha256'],f'restored SHA mismatch: {x["file"]}')
  for value in x.values():walk(value)
 elif isinstance(x,list):
  for value in x:walk(value)
walk(acq)
context=json.loads((ROOT/'context-extract.json').read_text())
for record in context:
 source=REPO/record['source_archive']
 check(source.is_file() and sha(source.read_bytes())==record['source_archive_gzip_sha256'],f'ancestor WCA source missing or changed: {record["source_archive"]}')
 subset=(ROOT/record['file']).read_bytes()
 check(len(subset)==record['gzip_bytes'] and sha(subset)==record['gzip_sha256'],f'WCA subset compressed bytes/hash mismatch: {record["file"]}')
 restored=gzip.decompress(subset)
 check(len(restored)==record['restored_bytes'] and sha(restored)==record['restored_sha256'],f'WCA subset restored bytes/hash mismatch: {record["file"]}')
sen=json.loads((ROOT/'senegal-settlement-extract.json').read_text())
sen_archive=(ROOT/sen['source_archive']).read_bytes()
check(sha(sen_archive)==sen['source_archive_gzip_sha256'],'Senegal 2017 original source archive hash mismatch')
sen_subset=(ROOT/sen['file']).read_bytes()
check(len(sen_subset)==sen['gzip_bytes'] and sha(sen_subset)==sen['gzip_sha256'],'Senegal 2017 subset compressed bytes/hash mismatch')
sen_restored=gzip.decompress(sen_subset)
check(len(sen_restored)==sen['restored_bytes'] and sha(sen_restored)==sen['restored_sha256'],'Senegal 2017 subset restored bytes/hash mismatch')

before=outputs_hashes()
subprocess.run([sys.executable,str(ROOT/'build_assessment.py')],check=True,cwd=REPO,stdout=subprocess.DEVNULL)
once=outputs_hashes()
subprocess.run([sys.executable,str(ROOT/'build_assessment.py')],check=True,cwd=REPO,stdout=subprocess.DEVNULL)
twice=outputs_hashes()
check(once==twice,'two-run generator outputs are not byte-identical')
check(before==once,'checked-in generated outputs do not match source rebuild')
for name,count in EXPECTED.items():
 if count is not None:check(len(rows(name))==count,f'{name}: expected {count} data rows')
account=json.loads((ROOT/'generated-data-accounting.json').read_text())
check(account['baseline_commit']==COMMIT,'generated data ledger baseline commit mismatch')
check({x['path'] for x in account['outputs']}=={n for n in EXPECTED if n.endswith('.csv')},'generated data ledger file inventory mismatch')
for item in account['outputs']:
 raw=(ROOT/item['path']).read_bytes()
 check(len(raw)==item['bytes'] and sha(raw)==item['sha256'],f'generated table bytes/hash mismatch: {item["path"]}')
 check(len(rows(item['path']))==item['rows_excluding_header'],f'generated table row count mismatch: {item["path"]}')
check(sum(x['rows_excluding_header'] for x in account['outputs'])==account['generated_table_rows_excluding_headers'],'generated row total mismatch')
assessment=rows('assessment.csv')
check([x['id'] for x in assessment]==ids,'assessment does not preserve every issue subject exactly once and in order')
check(all(x['assessment_status']=='insufficient-evidence' for x in assessment),'unsupported geographic conclusion present')
check(sum(x['parent_assignment_assessment']=='supported' for x in assessment)==224,'parent candidate support count changed')
check(sum(x['parent_assignment_assessment']=='insufficient-evidence' for x in assessment)==2,'unresolved duplicate parent candidate count changed')
check(all(x['current_parent_label'] for x in assessment),'subject row lacks a current parent candidate/status')
scopes=rows('administrative-scope.csv')
check(sum(x['scope_level']=='province' for x in scopes)==24 and sum(x['scope_level']=='area' for x in scopes)==3,'area/province scope inventory incomplete')
for country,n in [('Nigeria',179),('Senegal',45),('Sierra Leone',2)]:
 check(sum(x['country']==country for x in assessment)==n,f'{country} assigned scope count changed')
print(json.dumps({'status':'passed','subjects':len(assessment),'area_and_province_scopes':len(scopes),
 'retained_source_hashes':'passed','ancestor_baseline_and_complete_chains':'passed','two_run_generator_reproducibility':'passed',
 'deterministic_outputs':outputs_hashes(),'parent_candidate_supported':224,'parent_candidate_unresolved':2,
 'geographic_status':'226 insufficient-evidence'},indent=2))

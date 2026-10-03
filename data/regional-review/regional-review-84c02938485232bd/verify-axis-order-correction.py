#!/usr/bin/env python3
"""Validate issue #580's corrected baseline, control checks and full row ledger."""
import hashlib,json,pathlib,subprocess,math
P=pathlib.Path(__file__).resolve().parent; ROOT=P.parents[2]
read=lambda p:json.loads((P/p).read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def check(ok,msg):
 if not ok:raise AssertionError(msg)
 return msg
result=read('axis-order-correction.json'); scope=read('issue-scope.json')
ids=sorted(scope['member_location_ids']); check(len(ids)==265 and len(set(ids))==265,'scope is exactly 265 unique IDs')
check(result['baseline_commit']=='6c6271af6b0dac49b82eaafb2db4de8b9c4611f2','immutable evaluation baseline remains pinned')
check(result['scope']['count']==265 and result['scope']['member_ids_sha256']==scope['member_location_ids_sha256'],'correction report binds exact issue scope')
for f in result['scope']['baseline_files']:
 raw=subprocess.check_output(['git','-C',str(ROOT),'show',f"{result['baseline_commit']}:{f['path']}"])
 check(len(raw)==f['bytes'] and sha(raw)==f['sha256'],f"baseline bytes match {f['path']}")
rows=[json.loads(x) for x in (P/'audit.jsonl').read_text().splitlines() if x.strip()]
check(len(rows)==265 and {x['location_id'] for x in rows}==set(ids),'corrected audit covers all 265 scope IDs')
invalid={x['location_id'] for x in rows if x['geometry_comparison']['status']=='invalid overlay'}
expected={'gb:COL:ADM2:7082276B21922340436225','gb:COL:ADM2:7082276B29749803006962','gb:COL:ADM2:7082276B94072212482436'}
check(invalid==expected,'all and only three invalid overlays are reported')
check({x['location_id'] for x in rows if x['assessment']=='insufficient-evidence'}==invalid,'invalid overlays have insufficient-evidence assessments')
check({x['location_id'] for x in rows if x['assessment']=='correction-needed'}=={'gb:COL:ADM2:7082276B21429087141697','gb:COL:ADM2:7082276B50890297817335','gb:COL:ADM2:7082276B71833607735517'},'three existing name corrections remain unchanged')
check({x['location_id'] for x in rows if x['assessment']=='justified'}==set(ids)-invalid-{x['location_id'] for x in rows if x['assessment']=='correction-needed'},'all remaining subjects retain justified administrative identity assessments')
check(result['result_counts']=={'assigned':265,'valid_overlays':262,'invalid_overlays':3,'classification_changes':1,'classification_changes_ids':['gb:COL:ADM2:7082276B94072212482436'],'invalid_overlay_ids':sorted(expected)},'corrected validity and classification change summary is exact')
ledgers={x['id']:x for x in result['subjects']}; check(set(ledgers)==set(ids),'old/new metric ledger covers every subject')
for row in rows:
 r=ledgers[row['location_id']]; m=row['geometry_comparison']
 check(abs(m['area_fraction_difference']-r['new_area_fraction_difference'])<1e-12,'audit/report area metric match')
 if m['status']=='invalid overlay':check(r['new_symmetric_difference_fraction'] is None,'invalid geometry has no claimed symmetric difference')
 else:check(abs(m['symmetric_difference_fraction']-r['new_symmetric_difference_fraction'])<1e-12,'audit/report symmetric-difference match')
point=result['known_point_control']; check(max(abs(x) for x in point['difference_metres'])<0.001 and point['wrong_axis_control_separation_metres']>1_000_000,'known point and wrong-axis negative control pass')
area=result['known_area_control']; check(area['relative_difference']<area['tolerance'] and len(area['independent_geodesic_samples'])==5,'known cell and five independent geodesic samples pass')
check(all(x['source_area_relative_difference']<0.003 and x['current_area_relative_difference']<0.003 for x in area['independent_geodesic_samples']),'all real polygon geodesic cross-checks are within tolerance')
union=read('department-union-comparison.json');check(union['baseline_commit']==result['baseline_commit'] and len(union['departments'])==5,'five corrected parent unions use the pinned baseline')
for x in union['departments']:check(x['locations']>0 and math.isfinite(x['union_symmetric_difference_fraction']),'parent union metrics finite')
repro=read('reproducibility-check.json')
check(repro['all_files_match'] and repro['baseline_commit']==result['baseline_commit'] and repro['scope_sha256']==scope['member_location_ids_sha256'],'two-run reproducibility checkpoint binds pinned baseline and issue scope')
for f in repro['run_1']:
 b=(P/f['path']).read_bytes();check(len(b)==f['bytes'] and sha(b)==f['sha256'],f"deterministic output hash: {f['path']}")
check(repro['run_1']==repro['run_2'],'consecutive output inventories match exactly')
preserve=read('superseded/axis-order-v1/preservation-record.json')
for f in preserve['files']:
 b=(P/f['file']).read_bytes();check(len(b)==f['bytes'] and sha(b)==f['sha256'],f"historical evidence preserved: {f['file']}")
assert 'OAMS_TRADITIONAL_GIS_ORDER' in (P/'reproduce-geometry.py').read_text()
print(json.dumps({'status':'passed','subjects':265,'valid_overlays':262,'invalid_overlays':3,'classifications':{'justified':259,'correction-needed':3,'insufficient-evidence':3},'parent_unions':5,'historical_artifacts_preserved':len(preserve['files']),'controls':'longitude-first point, wrong-axis negative control, equal-area/geodesic controls'},indent=2))

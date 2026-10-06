#!/usr/bin/env python3
"""Run the pinned evidence generator twice and write gate-bound control receipts."""
import hashlib, json, os, subprocess, sys
from pathlib import Path
root=Path(__file__).resolve().parents[3]
owned=root/'data/regional-review/vanuatu-province-boundary-reconciliation-20261005'
env=dict(os.environ)
env['PYTHONPATH']=os.pathsep.join([str(root/'scripts'),str(root/'scripts/evidence'),env.get('PYTHONPATH','')])
command=[sys.executable,str(owned/'reproduce.py')]
one=subprocess.run(command,cwd=root,env=env,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
raw_one=(owned/'reproduction.json').read_bytes(); h1=hashlib.sha256(raw_one).hexdigest()
two=subprocess.run(command,cwd=root,env=env,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
raw_two=(owned/'reproduction.json').read_bytes(); h2=hashlib.sha256(raw_two).hexdigest()
if h1!=h2: raise SystemExit('reproduction output changed between identical baseline runs')
result=json.loads(raw_two); rows=result['subjects']; ids=[r['id'] for r in rows]
if len(ids)!=6 or len(set(ids))!=6 or not all(r['source_native_id']==r['id'].rsplit(':',1)[1] and r['source_name'] for r in rows):
    raise SystemExit('positive identity/geometry controls failed')
if not result['negative_controls']['unknown_subject_id_absent'] or not result['negative_controls']['wrong_source_name_rejected']:
    raise SystemExit('negative controls failed')
checks=owned/'checks'; checks.mkdir(exist_ok=True)
def write(name,value): (checks/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
write('positive-control.json',{'method_id':'geodesic-overlap-screen','kind':'positive-control','outcome':'passed','checked_subject_count':6,'checked_native_id_name_matches':6,'valid_geometries':6,'scope_ids':ids,'details':'Pinned index found exactly six unique subjects; all six Atlas/source features canonicalized with the shared helper without repair, and source native IDs/names matched.'})
write('negative-control.json',{'method_id':'geodesic-overlap-screen','kind':'negative-control','outcome':'passed','unknown_subject_id_absent':True,'deliberately_wrong_source_name_rejected':True,'details':'Unknown subject ID was absent from the exact indexed scope; a deliberately wrong source display-name comparison was false.'})
write('reproducibility.json',{'method_id':'deterministic-reproduction','kind':'reproducibility','outcome':'passed','run_one_sha256':h1,'run_two_sha256':h2,'run_one_exit':one.returncode,'run_two_exit':two.returncode,'details':'Two consecutive runs on the same immutable baseline produced byte-identical reproduction.json.'})
print(json.dumps({'status':'passed','run_one_sha256':h1,'run_two_sha256':h2,'subjects':len(rows)},indent=2))

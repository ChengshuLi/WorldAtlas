#!/usr/bin/env python3
"""Verify the retained Census ZIP and write one exclusive, symlink-safe receipt."""
import argparse, hashlib, importlib.util, json, re, sys, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
OWNED = "data/regional-review/southeastern-county-vintage-978-erratum/"
def sha(raw): return hashlib.sha256(raw).hexdigest()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--script-sha256',required=True); ap.add_argument('--inventory-sha256',required=True); ap.add_argument('--runner-sha256',required=True)
    a=ap.parse_args(); script=Path(__file__).read_bytes(); invp=ROOT/(OWNED+'baseline-inventory-v2.json'); runnerp=ROOT/(OWNED+'reproduce-v2.py')
    if sha(script)!=a.script_sha256 or sha(invp.read_bytes())!=a.inventory_sha256 or sha(runnerp.read_bytes())!=a.runner_sha256: raise SystemExit('explicit code/inventory pin mismatch')
    inventory=json.loads(invp.read_bytes());
    spec=importlib.util.spec_from_file_location('reproduce_v2',runnerp); runner=importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
    ziprow=next(x for x in inventory['files'] if x['path'].endswith('cb_2018_us_county_500k.zip'))
    sys.path.insert(0,str(ROOT)); from scripts.evidence.immutable import Baseline
    base=Baseline(ROOT,inventory['commit'],inventory['files']); raw=base.read(ziprow['path'])
    if sha(raw)!=ziprow['sha256']: raise SystemExit('ZIP differs from immutable inventory')
    members=[]
    with zipfile.ZipFile(__import__('io').BytesIO(raw)) as archive:
        names=archive.namelist()
        if len(names)!=7 or len(names)!=len(set(names)): raise SystemExit('Unexpected ZIP member inventory')
        for name in names:
            if name.startswith('/') or '..' in Path(name).parts or '\\' in name: raise SystemExit('Unsafe ZIP member path')
            data=archive.read(name); members.append({'path':name,'encoded_bytes':archive.getinfo(name).compress_size,'decoded_bytes':len(data),'sha256':sha(data)})
    result={'version':2,'issue':1252,'baseline_commit':base.commit,'zip_path':ziprow['path'],'zip_sha256':sha(raw),'zip_encoded_bytes':len(raw),'inventory_sha256':a.inventory_sha256,'runner_sha256':a.runner_sha256,'reproduction_script_sha256':a.script_sha256,'members':members,'member_count':len(members),'decoded_member_bytes':sum(x['decoded_bytes'] for x in members),'largest_decoded_member_bytes':max(x['decoded_bytes'] for x in members),'member_limit_bytes':33554432,'all_members_below_32_mib':all(x['decoded_bytes']<33554432 for x in members),'original_1162_descriptor_count':inventory['original_1162_descriptor_count'],'original_1162_encoded_bytes':inventory['original_1162_encoded_bytes'],'reserve_bytes':8388608,'original_encoded_plus_decoded_zip_plus_reserve_bytes':inventory['original_1162_encoded_bytes']+sum(x['decoded_bytes'] for x in members)+8388608,'evidence_caps':{'single_file_bytes':33554432,'total_descriptor_bytes':268435456,'descriptor_count':512}}
    out=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode(); runner.exclusive_write(ROOT,OWNED+'archive-admission-reproduction.json',out)
    print(json.dumps({'path':OWNED+'archive-admission-reproduction.json','sha256':sha(out),'members':len(members)}))
if __name__=='__main__': main()

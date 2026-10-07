#!/usr/bin/env python3
"""Audited sequential execution wrapper for the frozen source extractor."""
import argparse, hashlib, json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent

def sha(b): return hashlib.sha256(b).hexdigest()
def main():
    p=argparse.ArgumentParser(); p.add_argument('--run-id',required=True,choices=['run-1','run-2']); p.add_argument('--repo',required=True); a=p.parse_args()
    run_dir=HERE/'runs'; out=run_dir/a.run_id/'output'; receipt=run_dir/(a.run_id+'-execution.json')
    if out.exists() or receipt.exists(): raise SystemExit('run directory or receipt already exists')
    start=datetime.now(timezone.utc).isoformat(); t=time.monotonic()
    lock_raw=(HERE/'frozen-execution.json').read_bytes(); lock=json.loads(lock_raw)
    cmd=[sys.executable,str(HERE/'source_extract.py'),'--repo',str(Path(a.repo).resolve()),'--run-id',a.run_id,'--output',str(out)]
    proc=subprocess.run(cmd,cwd=a.repo,text=True,capture_output=True)
    elapsed=time.monotonic()-t; end=datetime.now(timezone.utc).isoformat()
    outputs=[]
    if out.is_dir():
        for f in sorted(out.iterdir()):
            if f.is_file():
                b=f.read_bytes(); outputs.append({'path':f.relative_to(HERE).as_posix(),'bytes':len(b),'sha256':sha(b)})
    receipt_obj={'run_id':a.run_id,'started_utc':start,'ended_utc':end,'elapsed_seconds':elapsed,'argv':cmd,'working_directory':str(Path(a.repo).resolve()),'python_executable':sys.executable,'frozen_execution_sha256':sha(lock_raw),'frozen_code':lock['code'],'stdout':proc.stdout,'stderr':proc.stderr,'exit_code':proc.returncode,'complete_source_pass':proc.returncode==0,'outputs':outputs,'outputs_sha256':sha(json.dumps(outputs,sort_keys=True,separators=(',',':')).encode())}
    receipt.write_text(json.dumps(receipt_obj,indent=2)+'\n')
    print(json.dumps({'run_id':a.run_id,'exit_code':proc.returncode,'elapsed_seconds':elapsed,'outputs':len(outputs),'complete_source_pass':proc.returncode==0}))
    raise SystemExit(proc.returncode)
if __name__=='__main__': main()

#!/usr/bin/env python3
"""Run the frozen source-fitness producer twice and retain invocation receipts."""
import hashlib, json, os, platform, subprocess, sys, time
from pathlib import Path
import shapely
import numpy, pyproj
ROOT=Path(__file__).resolve().parent
WORKTREE=ROOT.parents[2]
PRODUCER=ROOT/'produce.py'
INPUTS=ROOT/'inputs'
PYTHON=Path(sys.executable).resolve()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(name):
    out=ROOT/'runs'/name
    if out.exists(): raise SystemExit(f'output already exists: {out}')
    before=sha(PRODUCER); started=time.time_ns()
    cmd=[str(PYTHON),str(PRODUCER),'--inputs',str(INPUTS),'--output',str(out)]
    proc=subprocess.run(cmd,cwd=WORKTREE,text=True,capture_output=True)
    ended=time.time_ns(); after=sha(PRODUCER)
    row={'run_id':name,'command':cmd,'cwd':str(WORKTREE),'started_unix_ns':started,'ended_unix_ns':ended,'exit_code':proc.returncode,'producer_sha256_before':before,'producer_sha256_after':after,'stdout':proc.stdout,'stderr':proc.stderr}
    if before!=after: row['outcome']='producer-changed-during-run'
    elif proc.returncode: row['outcome']='failed'
    else: row['outcome']='passed'
    (ROOT/'history'/f'{name}-invocation.json').write_text(json.dumps(row,sort_keys=True,indent=2)+'\n')
    return row

def main():
    start=sha(PRODUCER); a=run('run-one'); b=run('run-two'); end=sha(PRODUCER)
    summary={'status':'passed' if a['outcome']==b['outcome']=='passed' and start==end else 'failed','producer_sha256':start,'producer_sha256_after':end,'python':platform.python_version(),'platform':platform.platform(),'numpy':numpy.__version__,'pyproj':pyproj.__version__,'shapely':shapely.__version__,'geos':shapely.geos_version_string,'runs':[a['run_id'],b['run_id']]}
    if summary['status']=='passed':
      hashes=[]
      for name in summary['runs']:
        d=json.loads((ROOT/'runs'/name/'run-summary.json').read_text())
        hashes.append({k:v['sha256'] for k,v in d['outputs'].items()})
      summary['run_output_hashes']=hashes
      summary['identical']=hashes[0]==hashes[1]
      summary['status']='passed' if summary['identical'] else 'failed'
    (ROOT/'history'/'two-run-summary.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
    print(json.dumps(summary,sort_keys=True))
    if summary['status']!='passed': raise SystemExit(1)
if __name__=='__main__': main()

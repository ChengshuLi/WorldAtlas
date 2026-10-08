#!/usr/bin/env python3
"""Supervise the one admitted Norway geometry phase with RSS/time/process-group bounds."""
from __future__ import annotations
import datetime, hashlib, json, os, re, signal, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PYTHON=Path('/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12')
ENTRY=ROOT/'measure_norway_physical.py'
ADMISSION=ROOT/'geometry-run-admission-004.json'
RUNTIME=ROOT/'geometry-run-runtime-004.json'
CONSOLE=ROOT/'geometry-run-console-004.json'
RSS_CAP=805_306_368
TIME_LIMIT=900

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def memory_free_percent():
    raw=subprocess.run(["/usr/bin/memory_pressure","-Q"],capture_output=True,text=True,check=True).stdout
    match=re.search(r"System-wide memory free percentage: (\d+)%",raw)
    if not match: raise RuntimeError("cannot read live memory pressure")
    return int(match.group(1))
def rss_group(pgid):
    raw=subprocess.run(['/bin/ps','-axo','pid=,pgid=,rss='],capture_output=True,text=True,check=True).stdout
    rows=[]
    for line in raw.splitlines():
        cols=line.split()
        if len(cols)==3 and cols[1].isdigit() and int(cols[1])==pgid:
            rows.append({'pid':int(cols[0]),'rss_bytes':int(cols[2])*1024})
    return rows,sum(row['rss_bytes'] for row in rows)
def main():
    if not ADMISSION.exists() or RUNTIME.exists() or CONSOLE.exists(): raise SystemExit('missing fresh admission or prior output exists')
    admission=json.loads(ADMISSION.read_text())
    if admission.get('status')!='admitted' or admission.get('phase_rss_cap_bytes')!=RSS_CAP: raise SystemExit('admission does not match bounded runner')
    producer_sha=sha(ENTRY); plan_sha=sha(ROOT/'bounded-measurement-plan.json')
    if admission.get('producer_sha256')!=producer_sha or admission.get('plan_sha256')!=plan_sha: raise SystemExit('producer or plan changed after admission')
    start=time.monotonic(); wall_start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    p=subprocess.Popen([str(PYTHON),'-B',str(ENTRY)],cwd=ROOT.parents[2],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    pgid=p.pid; peak=0; samples=0; over=False; memory_low=False; min_live_free=int(admission["memory"]["system_free_percent"])
    while p.poll() is None:
        rows,group=rss_group(pgid); peak=max(peak,group); samples+=1
        if samples%10==0:
            live_free=memory_free_percent(); min_live_free=min(min_live_free,live_free)
            if live_free<20:
                memory_low=True
                os.killpg(pgid,signal.SIGTERM)
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(pgid,signal.SIGKILL)
                break
        if group>RSS_CAP:
            over=True
            os.killpg(pgid,signal.SIGTERM)
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(pgid,signal.SIGKILL)
            break
        if time.monotonic()-start>TIME_LIMIT:
            os.killpg(pgid,signal.SIGTERM)
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(pgid,signal.SIGKILL)
            break
        time.sleep(0.1)
    stdout,stderr=p.communicate()
    elapsed=time.monotonic()-start
    remaining,remaining_rss=rss_group(pgid)
    console={'stdout':stdout,'stderr':stderr,'exit_code':p.returncode}
    CONSOLE.write_text(json.dumps(console,indent=2)+'\n')
    result={'version':1,'status':'rss-cap-exceeded' if over else 'memory-low-guard' if memory_low else 'timeout' if elapsed>TIME_LIMIT else 'terminal','pid':p.pid,'pgid':pgid,'exit_code':p.returncode,'started_at':wall_start,'elapsed_seconds':round(elapsed,3),'peak_sampled_process_group_rss_bytes':peak,'rss_sample_count':samples,'rss_cap_bytes':RSS_CAP,'minimum_system_free_percent_during_run':20,'minimum_observed_system_free_percent':min_live_free,'time_limit_seconds':TIME_LIMIT,'terminal_process_group_empty':not remaining,'remaining_processes':remaining,'producer_sha256':producer_sha,'plan_sha256':plan_sha,'admission_sha256':sha(ADMISSION),'console_sha256':sha(CONSOLE)}
    RUNTIME.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if result['status']!='terminal' or p.returncode!=0 or remaining: raise SystemExit(1)
if __name__=='__main__': main()

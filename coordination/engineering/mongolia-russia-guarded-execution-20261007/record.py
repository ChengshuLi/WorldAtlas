"""Record a real isolated subprocess; no recovered output is relabeled as a run."""
import argparse,datetime,hashlib,json,os,subprocess,time
from pathlib import Path

HERE=Path(__file__).absolute().parent
REPO=HERE.parents[2]
PYTHON='/Users/chengshuli/world-atlas-workspace/.cache/991-author-slot-preserved-20261006-44ed0b44/ignored-cache/reference-repair-991/runtime-rasterio-1.4.3-py312-arm64/bin/python'

def record(commit,name,input_only=False):
    if not name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name):raise ValueError('Safe exclusive run name required')
    from importlib.util import spec_from_file_location,module_from_spec
    spec=spec_from_file_location('recorded_admission',HERE/'run.py');entry=module_from_spec(spec);spec.loader.exec_module(entry)
    out=REPO/'.cache'/name;entry.destination(out)
    logs=REPO/'.cache'/(name+'-execution');entry.destination(logs);logs.mkdir()
    command=['/usr/bin/time','-l',PYTHON,'-I',str(HERE/'run.py'),'--commit',commit,'--out',str(out)]
    if input_only:command+=['--input-only']
    start=datetime.datetime.now(datetime.timezone.utc).isoformat();mono=time.monotonic_ns();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    with (logs/'stdout').open('xb') as stdout,(logs/'stderr').open('xb') as stderr:
        p=subprocess.Popen(command,cwd=REPO,env=env,stdout=stdout,stderr=stderr);pid=p.pid;exit_code=p.wait()
    end=datetime.datetime.now(datetime.timezone.utc).isoformat();elapsed=(time.monotonic_ns()-mono)/1e9
    files={name:{'bytes':(logs/name).stat().st_size,'sha256':hashlib.sha256((logs/name).read_bytes()).hexdigest()}for name in ('stdout','stderr')}
    receipt={'execution_commit':commit,'mode':'input-only' if input_only else 'complete original48+8 comparison','command':command,'cwd':str(REPO),'environment':{'PYTHONDONTWRITEBYTECODE':'1','isolated_python':True},'actual_start_utc':start,'actual_end_utc':end,'elapsed_seconds':elapsed,'pid':pid,'exit_code':exit_code,'terminal_files':files,'recorder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'output_directory':str(out),'limits':['Native time/RSS is retained literally in stderr. Receipt records actual subprocess terminal status; a failed run is not scientific PASS.']}
    (logs/'execution.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'exit_code':exit_code,'receipt':str(logs/'execution.json'),'elapsed_seconds':elapsed}));return exit_code
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--name',required=True);p.add_argument('--input-only',action='store_true');a=p.parse_args();raise SystemExit(record(a.commit,a.name,a.input_only))

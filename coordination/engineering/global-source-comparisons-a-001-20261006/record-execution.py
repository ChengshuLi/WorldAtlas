"""Record one actual immutable producer execution; do not retry automatically."""
import argparse,datetime,json,pathlib,subprocess,sys,hashlib
CASE=pathlib.Path(__file__).resolve().parent;ROOT=CASE.parents[2]
p=argparse.ArgumentParser();p.add_argument('--producer-commit',required=True);p.add_argument('--run',required=True);p.add_argument('--record',required=True);p.add_argument('--log',required=True);a=p.parse_args()
assert len(a.producer_commit)==40 and all(c in '0123456789abcdef'for c in a.producer_commit)
run=pathlib.Path(a.run);record=pathlib.Path(a.record);log=pathlib.Path(a.log)
assert not run.exists()and not record.exists()and not log.exists()
for value in [run,record,log]:
 assert value.is_absolute() and '..' not in value.parts and value.resolve().is_relative_to(ROOT/'.cache')
 for parent in value.parents:
  if parent==ROOT:break
  assert not parent.is_symlink()
closure=[]
for name in ['producer.py','record-execution.py','stage-inputs.py','verify.py','controls.py','record-controls.py','record-reproducibility.py','retain-run.py','build-manifest.py']:
 path=CASE/name;assert path.is_file() and not path.is_symlink()
 rel=str(path.relative_to(ROOT));body=path.read_bytes();frozen=subprocess.check_output(['git','show',a.producer_commit+':'+rel],cwd=ROOT)
 assert body==frozen
 closure.append({'path':rel,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()})
command=[sys.executable,'-B',str(CASE/'producer.py'),'--repo',str(ROOT),'--producer-commit',a.producer_commit,'--output',str(run)]
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(v):record.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
v={'command':command,'actual_frozen_executable_closure':closure,'working_directory':str(ROOT),'started_utc':now(),'status':'running','environment':{'PYTHONDONTWRITEBYTECODE':'1'},'limits':['Actual numerical producer process; no automatic retry and no approval of physical water or repairs.']}
with log.open('xb')as stream:
 proc=subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT);v['pid']=proc.pid;write(v);status=proc.wait()
v.update(finished_utc=now(),exit_code=status,status='completed'if status==0 else'failed');write(v);print(json.dumps(v));sys.exit(status)

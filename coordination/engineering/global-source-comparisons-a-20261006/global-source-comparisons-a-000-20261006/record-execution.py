"""Record one actual immutable producer execution; do not retry automatically."""
import argparse,datetime,json,pathlib,subprocess,sys
CASE=pathlib.Path(__file__).resolve().parent;ROOT=CASE.parents[3]
p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--record',required=True);p.add_argument('--log',required=True);a=p.parse_args()
run=pathlib.Path(a.run);record=pathlib.Path(a.record);log=pathlib.Path(a.log)
assert not run.exists()and not record.exists()and not log.exists()
command=[sys.executable,'-B',str(CASE/'producer.py'),'--repo',str(ROOT),'--producer-commit','3b4ca9e9f42d692530a4139efe2bd8f72ce15723','--output',str(run)]
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(v):record.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
v={'command':command,'working_directory':str(ROOT),'started_utc':now(),'status':'running','environment':{'PYTHONDONTWRITEBYTECODE':'1'},'limits':['Actual numerical producer process; no automatic retry and no approval of physical water or repairs.']}
with log.open('xb')as stream:
 proc=subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT);v['pid']=proc.pid;write(v);status=proc.wait()
v.update(finished_utc=now(),exit_code=status,status='completed'if status==0 else'failed');write(v);print(json.dumps(v));sys.exit(status)

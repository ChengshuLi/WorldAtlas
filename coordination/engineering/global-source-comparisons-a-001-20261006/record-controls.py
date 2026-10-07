"""Record a real directed-control execution and shared-policy method bindings."""
import argparse,datetime,hashlib,json,pathlib,subprocess,sys
CASE=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=pathlib.Path(a.output);assert not out.exists()
def canon(v):return(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
command=[sys.executable,'-B',str(CASE/'controls.py'),'--output',str(out)]
start=datetime.datetime.now(datetime.timezone.utc).isoformat();result=subprocess.run(command,capture_output=True,text=True)
actual={'command':command,'started_utc':start,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'executed_controls_sha256':sha((CASE/'controls.py').read_bytes())}
out.mkdir(parents=True,exist_ok=True);(out/'actual-execution.json').write_bytes(canon(actual));assert result.returncode==0,actual
controls=json.loads(result.stdout.splitlines()[-1]);assert controls['outcome']=='passed'and len(controls['controls'])==15
for method in ['immutable-preparation','literal-source-intersections']:
 for kind in ['positive-control','negative-control']:
  row={'method_id':method,'kind':kind,'outcome':'passed','actual_execution_sha256':sha(canon(actual)),'actual_directed_result':controls,'limits':['Directed complete-pointset fixtures and retained historical discrepancy; not a complete numerical package execution or physical-water approval.']}
  (out/(method+'-'+kind+'.json')).write_bytes(canon(row))
print(json.dumps({'outcome':'passed','controls':len(controls['controls']),'actual_execution_sha256':sha(canon(actual))}))

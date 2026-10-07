"""Record a real directed-control execution and shared-policy method bindings."""
import argparse,datetime,hashlib,json,pathlib,subprocess,sys,re,platform,shapely
CASE=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--producer-commit',required=True);p.add_argument('--recorder-commit',required=True);a=p.parse_args()
ROOT=CASE.parents[2];PREFIX=str(CASE.relative_to(ROOT))
def authenticate(name,commit):
 assert re.fullmatch('[a-f0-9]{40}',commit), 'immutable full commit required'
 path=CASE/name;assert path.is_file() and not path.is_symlink()
 for parent in path.parents:
  assert not parent.is_symlink()
  if parent==ROOT:break
 tree=subprocess.check_output(['git','ls-tree',commit,'--',PREFIX+'/'+name],cwd=ROOT).split();assert tree[0] in (b'100644',b'100755')
 body=subprocess.check_output(['git','show',commit+':'+PREFIX+'/'+name],cwd=ROOT);assert body==path.read_bytes(),('executed module differs from immutable source',name)
 return body
def checked_cache_path(value,exists):
 path=pathlib.Path(value);assert path.is_absolute() and '..' not in path.parts and path.resolve().is_relative_to(ROOT/'.cache')
 for parent in [path,*path.parents]:assert not parent.is_symlink()
 assert path.exists()==exists
 return path
assert re.fullmatch('[a-f0-9]{40}',a.producer_commit) and re.fullmatch('[a-f0-9]{40}',a.recorder_commit)
assert platform.python_version()=='3.12.14' and shapely.__version__=='2.1.2' and shapely.geos_version_string=='3.13.1'
recorder_body=authenticate(pathlib.Path(__file__).name,a.recorder_commit)

for name in ['producer.py','record-execution.py','stage-inputs.py','verify.py','controls.py','record-controls.py','record-reproducibility.py','retain-run.py','build-manifest.py']:authenticate(name,a.producer_commit)
out=checked_cache_path(a.output,False)
def canon(v):return(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
command=[sys.executable,'-B',str(CASE/'controls.py'),'--output',str(out)]
start=datetime.datetime.now(datetime.timezone.utc).isoformat();result=subprocess.run(command,capture_output=True,text=True)
actual={'command':command,'started_utc':start,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'executed_controls_sha256':sha((CASE/'controls.py').read_bytes()),'executed_recorder_sha256':sha(recorder_body),'recorder_commit':a.recorder_commit,'producer_commit':a.producer_commit,'recorder_command':[sys.executable,'-B',*sys.argv],'runtime':{'python':platform.python_version(),'shapely':shapely.__version__,'geos':shapely.geos_version_string}}
out.mkdir(parents=True,exist_ok=True);(out/'actual-execution.json').write_bytes(canon(actual));assert result.returncode==0,actual
controls=json.loads(result.stdout.splitlines()[-1]);assert controls['outcome']=='passed'and len(controls['controls'])==25
for method in ['immutable-preparation','literal-source-intersections']:
 for kind in ['positive-control','negative-control']:
  row={'method_id':method,'kind':kind,'outcome':'passed','actual_execution_sha256':sha(canon(actual)),'actual_directed_result':controls,'limits':['Directed complete-pointset fixtures and retained historical discrepancy; not a complete numerical package execution or physical-water approval.']}
  (out/(method+'-'+kind+'.json')).write_bytes(canon(row))
print(json.dumps({'outcome':'passed','controls':len(controls['controls']),'actual_execution_sha256':sha(canon(actual))}))

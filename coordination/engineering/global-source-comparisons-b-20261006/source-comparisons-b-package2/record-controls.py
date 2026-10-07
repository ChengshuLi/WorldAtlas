"""Retain actual directed control execution and typed shared-policy receipts."""
import pathlib,json,hashlib,subprocess,datetime
CASE=pathlib.Path(__file__).resolve().parent
PYTHON='/Users/chengshuli/world-atlas-workspace/private-publisher-checks-20261004/python-env/bin/python'
def canon(v):return(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
command=[PYTHON,str(CASE/'controls.py')];started=datetime.datetime.now(datetime.timezone.utc).isoformat();run=subprocess.run(command,capture_output=True,text=True,check=True);result=json.loads(run.stdout.splitlines()[-1]);assert result['status']=='PASS'and len(result['controls'])==36
actual={'command':command,'started_utc':started,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr,'actual_result':result,'executed_controls_sha256':sha((CASE/'controls.py').read_bytes()),'limits':result['limits']};(CASE/'verification/controls-actual-result.json').write_bytes(canon(actual))
for method in ('immutable-preparation','literal-source-intersections'):
 for kind in ('positive-control','negative-control'):
  receipt={'method_id':method,'kind':kind,'outcome':'passed','actual_control_result':'controls-actual-result.json','actual_control_result_sha256':sha(canon(actual)),'controls':result['controls'],'producer_sha256':result['producer_sha256'],'limits':['Directed small real-loop/source-loader fixtures and historical numerical-disagreement branch; not full world regeneration or geographic approval.']};(CASE/'verification'/(method+'-'+kind+'.json')).write_bytes(canon(receipt))
print(json.dumps({'status':'PASS','controls':len(result['controls']),'actual_controls_sha256':actual['executed_controls_sha256']}))

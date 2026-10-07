"""Bind two actual complete verified executions; no numerical generation here."""
import argparse,hashlib,json,pathlib,subprocess,re,datetime,sys
CASE=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--one',required=True);p.add_argument('--two',required=True);p.add_argument('--out',required=True);p.add_argument('--producer-commit',required=True);p.add_argument('--recorder-commit',required=True);a=p.parse_args()
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
recorder_body=authenticate(pathlib.Path(__file__).name,a.recorder_commit)

verifier_body=authenticate('verify.py',a.producer_commit);out=checked_cache_path(a.out,False);started=datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(v):return(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
receipts=[]
for name in [a.one,a.two]:
 body=checked_cache_path(name,True).read_bytes();v=json.loads(body);assert v['outcome']=='passed'and v['all_original_rows_equal']and v['complete_components']==14708 and v['complete_families']==2282 and v['complete_witnesses']==317 and v['complete_operation_unknowns']==34
 assert v['producer_commit']==a.producer_commit and v['actual_verifier_sha256']==sha(verifier_body)
 receipts.append({'actual_verification':v,'whole_verification_sha256':sha(body)})
assert receipts[0]['actual_verification']['producer_commit']==receipts[1]['actual_verification']['producer_commit']
assert receipts[0]['actual_verification']['scientific_product_sha256']==receipts[1]['actual_verification']['scientific_product_sha256']
result={'method_id':'immutable-preparation','kind':'reproducibility','outcome':'passed','run_one_sha256':receipts[0]['actual_verification']['scientific_product_sha256'],'run_two_sha256':receipts[1]['actual_verification']['scientific_product_sha256'],'producer_commit':receipts[0]['actual_verification']['producer_commit'],'complete_verification_receipts':receipts,'recorder_execution':{'command':[sys.executable,'-B',*sys.argv],'started_utc':started,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'recorder_commit':a.recorder_commit,'actual_recorder_sha256':sha(recorder_body),'producer_commit':a.producer_commit,'status':'passed'},'limits':['Two actual numerical executions were verified independently. This comparison of verified receipts is not another numerical execution.','No physical land/water, ownership, processing-cause or repair approval.']}
with out.open('xb') as stream:stream.write(canon(result))
print(json.dumps({'outcome':'passed','scientific_product_sha256':result['run_one_sha256']}))

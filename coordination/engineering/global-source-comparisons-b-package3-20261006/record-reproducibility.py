"""Bind two actual complete verified executions; no numerical generation here."""
import argparse,hashlib,json,pathlib
CASE=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--one',required=True);p.add_argument('--two',required=True);p.add_argument('--out',required=True);a=p.parse_args();out=pathlib.Path(a.out);assert not out.exists()
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(v):return(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
receipts=[]
for name in [a.one,a.two]:
 body=pathlib.Path(name).read_bytes();v=json.loads(body);assert v['outcome']=='passed'and v['all_original_rows_equal']and v['complete_components']==14708 and v['complete_families']==3482 and v['complete_witnesses']==317 and v['complete_operation_unknowns']==34
 receipts.append({'actual_verification':v,'whole_verification_sha256':sha(body)})
assert receipts[0]['actual_verification']['producer_commit']==receipts[1]['actual_verification']['producer_commit']
assert receipts[0]['actual_verification']['scientific_product_sha256']==receipts[1]['actual_verification']['scientific_product_sha256']
result={'method_id':'immutable-preparation','kind':'reproducibility','outcome':'passed','run_one_sha256':receipts[0]['actual_verification']['scientific_product_sha256'],'run_two_sha256':receipts[1]['actual_verification']['scientific_product_sha256'],'producer_commit':receipts[0]['actual_verification']['producer_commit'],'complete_verification_receipts':receipts,'limits':['Two actual numerical executions were verified independently. This comparison of verified receipts is not another numerical execution.','No physical land/water, ownership, processing-cause or repair approval.']}
out.write_bytes(canon(result));print(json.dumps({'outcome':'passed','scientific_product_sha256':result['run_one_sha256']}))

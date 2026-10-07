"""Verify this package's complete short-name transport against actual frozen Git blobs."""
import argparse,gzip,hashlib,json,pathlib,subprocess
CASE=pathlib.Path(__file__).resolve().parent;ROOT=CASE.parents[3];COMMIT='3b4ca9e9f42d692530a4139efe2bd8f72ce15723'
p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=pathlib.Path(a.out);assert not out.exists()
def canon(v):return(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def checked(path,pin):
 assert path.is_file()and not path.is_symlink();body=path.read_bytes();assert len(body)==pin['bytes']and sha(body)==pin['sha256'];raw=gzip.decompress(body)if body[:2]==b'\x1f\x8b'else body;assert max(len(body),len(raw))<=32*1024*1024;assert len(raw)==pin['decoded_bytes']and sha(raw)==pin['decoded_sha256'];return body
mapping=json.loads((CASE/'delivery-input-aliases.json').read_bytes());assert mapping['frozen_producer_commit']==COMMIT
old_raw=(CASE/'input-aliases.json').read_bytes();old_path=str((CASE/'input-aliases.json').relative_to(ROOT));assert subprocess.check_output(['git','show',COMMIT+':'+old_path],cwd=ROOT)==old_raw
originals=json.loads(old_raw)['aliases'];expected={v['owned_path']:v['original_pin']for v in originals};rows=mapping['complete_aliases'];assert len(rows)==len(expected)==202 and {v['frozen_owned_path']for v in rows}==set(expected)and len({v['delivered_owned_path']for v in rows})==202
proc=subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
for row in rows:
 for key in ['frozen_owned_path','delivered_owned_path']:
  rel=pathlib.Path(row[key]);assert not rel.is_absolute()and '..'not in rel.parts and rel.parts[0]=='inputs'and len(rel.parts)==2
 assert row['sha256']==expected[row['frozen_owned_path']]['sha256']and row['bytes']==expected[row['frozen_owned_path']]['bytes']
 assert row['frozen_git_path']==str((CASE/row['frozen_owned_path']).relative_to(ROOT));body=checked(CASE/row['delivered_owned_path'],row)
 proc.stdin.write((COMMIT+':'+row['frozen_git_path']+'\n').encode());proc.stdin.flush();header=proc.stdout.readline().split();assert header[1]==b'blob'and header[0].decode()==row['frozen_git_blob_oid'];frozen=proc.stdout.read(int(header[2]));assert proc.stdout.read(1)==b'\n'and frozen==body
proc.terminate();proc.wait()
# Real reader negatives run on bounded local files, not another numerical execution.
fixture=out.parent/(out.stem+'-fixtures');fixture.mkdir(exist_ok=False);target=fixture/'body';target.write_bytes(b'raw');pin={'bytes':3,'sha256':sha(b'raw'),'decoded_bytes':3,'decoded_sha256':sha(b'raw')};assert checked(target,pin)==b'raw';target.write_bytes(b'bad')
try:checked(target,pin)
except AssertionError:pass
else:raise AssertionError('changed transport accepted')
target.unlink()
try:checked(target,pin)
except AssertionError:pass
else:raise AssertionError('missing transport accepted')
result={'outcome':'passed','complete_delivery_aliases':len(rows),'all_actual_frozen_git_bytes_equal':True,'encoded_unique_bytes':sum(v['bytes']for v in rows),'delivery_map_sha256':sha((CASE/'delivery-input-aliases.json').read_bytes()),'actual_verifier_sha256':sha(pathlib.Path(__file__).read_bytes()),'directed_controls':['actual delivery reader accepts exact whole bytes','actual delivery reader rejects changed whole bytes','actual delivery reader rejects missing file'],'limits':['Delivery path and whole-byte equality only; no scientific execution, physical classification or geography repair.']};out.write_bytes(canon(result));print(json.dumps(result))

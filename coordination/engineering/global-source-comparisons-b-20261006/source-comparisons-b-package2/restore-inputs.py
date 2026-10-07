"""Restore exact frozen execution paths from shorter delivery aliases; no science."""
import pathlib,json,hashlib,gzip,subprocess,argparse
PIN='c0bb4c62a725f9d170a9c26db4baa1c477cbc905'
MAP_SHA='1b23c9723bdd83ed54add068968b494a493fe954e7375b241ed3ac2a3a481799'
CASE=pathlib.Path(__file__).resolve().parent;ROOT=CASE.parents[3]
LIMIT=32*1024*1024
def sha(b):return hashlib.sha256(b).hexdigest()
def safe(root,relative):
 if not isinstance(relative,str) or '\\'in relative:raise ValueError('Unsafe alias path')
 p=pathlib.PurePosixPath(relative)
 if p.is_absolute()or any(x in ('','.','..')for x in relative.split('/')):raise ValueError('Unsafe alias path')
 result=root.joinpath(*p.parts)
 for candidate in [result,*result.parents]:
  if candidate==root.parent:break
  if candidate.is_symlink():raise ValueError('Symlink alias path')
 return result
def checked(path,row):
 if not path.is_file()or path.is_symlink():raise ValueError('Missing ordinary delivery alias')
 b=path.read_bytes()
 if len(b)>LIMIT or len(b)!=row['bytes']or sha(b)!=row['sha256']:raise ValueError('Encoded alias mismatch')
 raw=gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b
 if len(raw)>LIMIT or len(raw)!=row['decoded_bytes']or sha(raw)!=row['decoded_sha256']:raise ValueError('Decoded alias mismatch')
 return b
def git_bytes(relative):
 tree=subprocess.check_output(['git','ls-tree',PIN,'--',relative],cwd=ROOT).split()
 if not tree or tree[0]not in(b'100644',b'100755'):raise ValueError('Original Git path is not ordinary')
 return subprocess.check_output(['git','show',PIN+':'+relative],cwd=ROOT)
def validate(root,rows,expected,original_reader,prefix,delivery_prefix=None):
 delivery_prefix=delivery_prefix or prefix+'/inputs/'
 if len({r['original_path']for r in rows})!=len(rows)or len({r['delivered_path']for r in rows})!=len(rows):raise ValueError('Duplicate alias path')
 if len(rows)!=len(expected)or {r['original_path']for r in rows}!=expected:raise ValueError('Incomplete original alias roster')
 for r in rows:
  if not r['original_path'].startswith(prefix+'/inputs/')or not r['delivered_path'].startswith(delivery_prefix):raise ValueError('Alias outside input namespace')
  old=safe(root,r['original_path']);new=safe(root,r['delivered_path']);b=checked(new,r)
  if original_reader(r['original_path'])!=b:raise ValueError('Alias differs from actual original Git bytes')
  if old.exists():checked(old,r)
 return rows

def restore(create=True):
 map_path=safe(ROOT,str((CASE/'delivery-input-aliases.json').relative_to(ROOT)))
 if not map_path.is_file():raise ValueError('Missing ordinary delivery map')
 map_bytes=map_path.read_bytes()
 if sha(map_bytes)!=MAP_SHA:raise ValueError('Delivery map differs from reviewed whole map')
 mapping=json.loads(map_bytes);prefix=CASE.relative_to(ROOT).as_posix()
 if mapping['original_execution_commit']!=PIN:raise ValueError('Wrong original execution commit')
 for name in ('producer.py','input-config.json','scope.json'):
  p=safe(ROOT,prefix+'/'+name)
  if p.read_bytes()!=git_bytes(prefix+'/'+name):raise ValueError('Frozen execution file changed')
 config=json.loads((CASE/'input-config.json').read_bytes())
 expected={prefix+'/'+p['alias']for p in config['immutable_aliases']}
 expected.update(prefix+'/'+p['alias']for product in config['source_products']for p in product['parts'])
 rows=validate(ROOT,mapping['rows'],expected,git_bytes,prefix,str(CASE.parent.relative_to(ROOT))+'/i/')
 created=[]
 for r in rows:
  old=safe(ROOT,r['original_path'])
  if not create:continue
  if not old.exists():
   b=checked(safe(ROOT,r['delivered_path']),r)
   with old.open('xb')as f:f.write(b)
   created.append(r['original_path'])
  checked(old,r)
 return {'original_execution_commit':PIN,'complete_aliases':len(rows),'created_paths':created,'map_sha256':MAP_SHA,'science_executed':False,'validation_only':not create,'executed_guard_sha256':sha(pathlib.Path(__file__).read_bytes())}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--receipt');p.add_argument('--verify-only',action='store_true');a=p.parse_args();result=restore(not a.verify_only);body=json.dumps(result,sort_keys=True,indent=2)+'\n'
 if a.receipt:pathlib.Path(a.receipt).write_text(body)
 print(body)

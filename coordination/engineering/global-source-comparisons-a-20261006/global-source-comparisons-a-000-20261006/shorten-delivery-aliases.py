"""Shorten this package's delivery names; preserve every frozen input byte and path."""
import gzip,hashlib,json,pathlib,subprocess
CASE=pathlib.Path(__file__).resolve().parent;ROOT=CASE.parents[3];COMMIT='3b4ca9e9f42d692530a4139efe2bd8f72ce15723'
def canon(v):return(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
output=CASE/'delivery-input-aliases.json';assert not output.exists()
aliases=json.loads((CASE/'input-aliases.json').read_bytes())['aliases'];unique={}
for alias in aliases:
 old=alias['owned_path'];assert old.startswith('inputs/')and len(pathlib.Path(old).parts)==2
 if old in unique:assert unique[old]['sha256']==alias['original_pin']['sha256']
 else:unique[old]=alias['original_pin']
rows=[]
for ordinal,(old,pin)in enumerate(sorted(unique.items())):
 source=CASE/old;assert source.is_file()and not source.is_symlink();body=source.read_bytes();assert len(body)==pin['bytes']and sha(body)==pin['sha256']
 raw=gzip.decompress(body)if body[:2]==b'\x1f\x8b'else body;assert max(len(raw),len(body))<=32*1024*1024
 frozen=str(source.relative_to(ROOT));entry=subprocess.check_output(['git','ls-tree',COMMIT,'--',frozen],cwd=ROOT).split();assert entry[0]==b'100644'
 new='inputs/i%03d.bin'%ordinal;assert not(CASE/new).exists()
 rows.append({'frozen_owned_path':old,'frozen_git_path':frozen,'frozen_git_blob_oid':entry[2].decode(),'delivered_owned_path':new,'bytes':len(body),'sha256':sha(body),'decoded_bytes':len(raw),'decoded_sha256':sha(raw),'mode':'100644'})
# All original whole files are checked before the first mutation.
for row in rows:(CASE/row['frozen_owned_path']).rename(CASE/row['delivered_owned_path'])
for row in rows:
 body=(CASE/row['delivered_owned_path']).read_bytes();assert len(body)==row['bytes']and sha(body)==row['sha256']
result={'version':1,'frozen_producer_commit':COMMIT,'complete_aliases':rows,'encoded_unique_bytes':sum(v['bytes']for v in rows),'relation':'Every complete encoded/decoded original input is unchanged. Only candidate delivery filenames differ. input-aliases.json retains the actual frozen execution paths; this map binds them to delivered bytes.','reproduction':'producer.py loads all numerical inputs directly from immutable Git '+COMMIT+' and authenticates whole bytes. It does not read candidate delivery alias files from the filesystem. Preserve the original frozen commit and original remote author branch.','limits':['Delivery transport correction only; no scientific execution, input changes, source approval or geometry changes.']}
output.write_bytes(canon(result));print(json.dumps({'outcome':'passed','aliases':len(rows),'encoded_unique_bytes':result['encoded_unique_bytes'],'map_sha256':sha(canon(result))}))

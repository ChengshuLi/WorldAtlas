"""Verify complete retained Git-object inverses and original path Merkle proofs.
Published source aliases are explicit, not recreated world data or execution.
"""
import argparse,base64,gzip,hashlib,json,pathlib,subprocess,sys
FILE=32*1024*1024;PHASE=256*1024*1024
def sha(b):return hashlib.sha256(b).hexdigest()
def tree_rows(raw):
 at=0;rows={}
 while at<len(raw):
  space=raw.index(b' ',at);end=raw.index(b'\0',space);mode=raw[at:space].decode();name=raw[space+1:end].decode();oid=raw[end+1:end+21].hex();assert len(raw[end+1:end+21])==20 and name not in rows
  rows[name]=(mode,oid);at=end+21
 assert at==len(raw);return rows
def verify(value,compare=None):
 objects={}
 for oid,p in value['objects'].items():
  raw=base64.b64decode(p['base64'],validate=True);assert len(raw)==p['bytes'] and sha(raw)==p['sha256'] and len(raw)<=FILE
  assert hashlib.sha1((p['kind']+' '+str(len(raw))+'\0').encode()+raw).hexdigest()==oid;objects[oid]=(p['kind'],raw)
 compared=0
 for binding in value['bindings']:
  p=binding['original_pin'];kind,body=objects[p['commit']];assert kind=='commit'
  root=body.split(b'\n',1)[0];assert root==('tree '+binding['merkle_tree_path'][0]).encode()
  parts=p['path'].split('/');proof=binding['merkle_tree_path'];assert len(proof)==len(parts)
  for i,name in enumerate(parts):
   kind,body=objects[proof[i]];assert kind=='tree';mode,oid=tree_rows(body)[name]
   assert oid==(proof[i+1] if i+1<len(parts) else p['git_blob_oid'])
   if i+1==len(parts):assert mode==p['mode']
  if 'whole_object' in binding:
   kind,body=objects[binding['whole_object']];assert kind=='blob' and len(body)==p['bytes'] and ('sha256' not in p or sha(body)==p['sha256'])
  else:
   a=binding['published_whole_alias'];assert a['mode']==p['mode'] and a['git_blob_oid']==p['git_blob_oid']
   if compare:
    row=subprocess.check_output(['git','-C',compare,'ls-tree','-z',a['commit'],'--',a['path']]);meta,name=row.rstrip(b'\0').split(b'\t');mode,kind,oid=meta.decode().split();assert mode==a['mode'] and oid==a['git_blob_oid'] and name.decode()==a['path']
    size=int(subprocess.check_output(['git','-C',compare,'cat-file','-s',oid]));assert size==p['bytes'] and size<=FILE
    assert sys.getsizeof(value)+size+pathlib.Path(sys.executable).stat().st_size<PHASE
    body=subprocess.check_output(['git','-C',compare,'cat-file','blob',oid]);assert len(body)==p['bytes'] and ('sha256'not in p or sha(body)==p['sha256']);compared+=1
 return {'whole_objects':len(objects),'original_bindings':len(value['bindings']),'published_aliases_compared':compared,'producers_executed':False}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--compare-published');args=parser.parse_args()
 root=pathlib.Path(__file__).parent;pin=json.loads((root/'original-execution-custody-receipt.json').read_bytes());archive=root/'original-execution-custody.json.gz'
 assert archive.stat().st_size==pin['encoded_bytes']<=FILE and pin['decoded_bytes']<=FILE
 # Real ordinary input+decoded object tables+largest published body+runtime bound.
 git_bytes=sum(pathlib.Path(p).stat().st_size for p in ['/usr/bin/git','/Library/Developer/CommandLineTools/usr/bin/git'] if pathlib.Path(p).is_file())
 reserve=pin['encoded_bytes']+3*pin['decoded_bytes']+FILE+pathlib.Path(sys.executable).stat().st_size+git_bytes+pathlib.Path(__file__).stat().st_size+4*1024*1024
 assert reserve<=PHASE
 encoded=archive.read_bytes();assert sha(encoded)==pin['encoded_sha256'];body=gzip.decompress(encoded);assert len(body)==pin['decoded_bytes'] and sha(body)==pin['decoded_sha256']
 result=verify(json.loads(body),args.compare_published);result.update({'complete_prospective_bytes':reserve,'decoded_archive_bytes':len(body),'limits':pin['limits']});print(json.dumps(result,indent=2))
if __name__=='__main__':main()

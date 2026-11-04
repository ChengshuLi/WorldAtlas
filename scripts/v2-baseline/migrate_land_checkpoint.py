#!/usr/bin/env python3
"""Recover frozen-run checkpoint checksum encoding; does not resume a run.

Requires separately reviewed source equivalence and explicitly pinned old/new
scripts. Writes a new file and evidence manifest; never modifies the original.
"""
import argparse,copy,hashlib,json,math,os
from pathlib import Path

def sha(b):return hashlib.sha256(b).hexdigest()
def require(v,msg):
 if not v:raise ValueError(msg)
def migrate(src,old_script,new_script,dst):
 src,old_script,new_script,dst=map(Path,(src,old_script,new_script,dst));raw=src.read_bytes();e=json.loads(raw);p=e['payload'];require(p['schema']=='simple-v2-query-checkpoint-v1','wrong schema')
 old=sha(old_script.read_bytes());new=sha(new_script.read_bytes());require(p['identity']['code_sha256']['build_land_checkpoint.py']==old,'old script hash mismatch')
 restored=copy.deepcopy(p); converted={}
 for k,ds in restored['best'].items():
  root=int(k);require(str(root)==k and isinstance(ds,dict) and ds,'invalid component');v={}
  for c,d in ds.items():
   code=int(c);require(str(code)==c and 17<=code<=22 and type(d) in (float,int) and math.isfinite(d) and d>=0,'invalid distance');v[code]=d
  require(root not in converted,'duplicate root');converted[root]=v
 restored['best']=converted
 oldbody=json.dumps(restored,sort_keys=True,separators=(',',':'),allow_nan=False).encode();require(sha(oldbody)==e['sha256'],'old checkpoint checksum mismatch')
 updated=copy.deepcopy(p);updated['identity']['code_sha256']['build_land_checkpoint.py']=new
 body=json.dumps(updated,sort_keys=True,separators=(',',':'),allow_nan=False).encode();newraw=json.dumps({'payload':updated,'sha256':sha(body)},separators=(',',':'),allow_nan=False).encode()
 with open(dst,'xb') as f:f.write(newraw);f.flush();os.fsync(f.fileno())
 require(dst.read_bytes()==newraw,'destination readback mismatch')
 require(updated['best']==p['best'] and updated['queries']==p['queries'] and updated['next_row']==p['next_row'],'migration changed distances or cursor')
 evidence={'schema':'simple-v2-checkpoint-migration-research-v1','status':'complete-verified-migration-research-not-published','source_checkpoint_sha256':sha(raw),'destination_checkpoint_sha256':sha(newraw),'old_script_sha256':old,'new_script_sha256':new,'queries':p['queries'],'next_row':p['next_row'],'components':len(p['best']),'limitation':'Verifies encoding and data preservation only; separate review must establish code semantic equivalence. Existing checkpoint and active run were not modified.'}
 with open(str(dst)+'.migration.json','x') as f:json.dump(evidence,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 fd=os.open(dst.parent,os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
 try:os.fsync(fd)
 finally:os.close(fd)
 return evidence
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('checkpoint');p.add_argument('old_script');p.add_argument('new_script');p.add_argument('output');a=p.parse_args();print(json.dumps(migrate(a.checkpoint,a.old_script,a.new_script,a.output),indent=2))

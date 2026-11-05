#!/usr/bin/env /usr/bin/python3
"""Independent full-grid RLE comparison; both inputs are read-only references.

This is a check only; it never supplies labels to the source-derived build.
Run under watch_compare.py. Reports remain local and do not approve a switch.
"""
import argparse, hashlib, json, os, resource, shutil, struct, time
from pathlib import Path
import numpy as np

def need(value,message):
 if not value:raise ValueError(message)

def digest(path,guard):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  while True:
   block=f.read(1<<20)
   if not block:break
   h.update(block);guard()
 return h.hexdigest()

def require_guardian():
 parent=os.getppid();need(parent==os.getpgrp(),'monitored guardian required')
 try:
  args=Path(f'/proc/{parent}/cmdline').read_bytes().split(b'\0');valid=len(args)>=3 and Path(os.fsdecode(args[1])).resolve()==Path(__file__).with_name('guardian.py').resolve()
 except (OSError,ValueError):valid=False
 need(valid and os.getppid()==parent,'monitored guardian required')

def strict_json(raw):
 def unique(pairs):
  result={}
  for key,value in pairs:need(key not in result,'duplicate JSON key');result[key]=value
  return result
 def nonfinite(value):raise ValueError('nonfinite JSON number')
 return json.loads(raw,object_pairs_hook=unique,parse_constant=nonfinite)

class Rows:
 def __init__(self,rows,runs,height,width):
  self.a=np.fromfile(rows,dtype='<u4');self.fd=os.open(runs,os.O_RDONLY);self.width=width
  try:need(len(self.a)==height+1 and self.a[0]==0 and np.all(self.a[1:]>=self.a[:-1]) and os.fstat(self.fd).st_size==int(self.a[-1])*8,'invalid stream offsets or size')
  except BaseException:os.close(self.fd);self.fd=None;raise
 def row(self,y):
  a,b=map(int,self.a[y:y+2]);raw=os.pread(self.fd,(b-a)*8,a*8);need(len(raw)==(b-a)*8,'short row');r=np.frombuffer(raw,dtype='<u4').reshape(-1,2)
  need(len(r)>0 and int(r[-1,0])==self.width and r[0,0]>0 and np.all(r[1:,0]>r[:-1,0]),'invalid full-width row');return r
 def close(self):
  if self.fd is not None:os.close(self.fd);self.fd=None


def compare_row(a,b,width):
 x=i=j=matches=0;differences=[]
 while x<width:
  end=min(int(a[i,0]),int(b[j,0]));need(end>x,'comparison did not advance');aa,bb=int(a[i,1]),int(b[j,1]);n=end-x
  if aa==bb:matches+=n
  elif len(differences)<10:differences.append((x,end,aa,bb))
  x=end
  if x==int(a[i,0]):i+=1
  if x==int(b[j,0]):j+=1
 return matches,differences


def run(request,output):
 require_guardian();started=time.monotonic();request=Path(request).resolve(strict=True);out=Path(output).resolve();need(request.stat().st_size<=1<<20,'request too large');raw=request.read_bytes();need(len(raw)<=1<<20,'request too large');cfg=strict_json(raw)
 need(set(cfg)=={'schema','grid','inputs','limits'} and cfg['schema']=='full-grid-comparison-request-v1','invalid request');g=cfg['grid']
 need(set(g)=={'width','height'} and all(type(g[k]) is int and 0<g[k]<=1000000 for k in g),'invalid grid');w,h=g['width'],g['height']
 lim=cfg['limits'];need(set(lim)=={'minimum_memory_kib','minimum_free_bytes','max_rss_kib'} and all(type(v) is int and v>0 for v in lim.values()) and lim['minimum_memory_kib']>=1887437 and lim['minimum_free_bytes']>=2*1024**3 and lim['max_rss_kib']<=870400,'invalid resource limits')
 need(not out.exists() and out.parent.is_dir(),'new output directory required')
 def guard():
  with open('/proc/meminfo') as f:available=next((int(x.split()[1]) for x in f if x.startswith('MemAvailable:')),None)
  need(available is not None and available>=lim['minimum_memory_kib'],'memory floor reached');need(shutil.disk_usage(out.parent).free>=lim['minimum_free_bytes'],'disk floor reached');need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<=lim['max_rss_kib'],'process RSS limit reached')
 guard();inputs=cfg['inputs'];need(set(inputs)=={'baseline_rows','baseline_runs','candidate_rows','candidate_runs'},'invalid inputs');paths={}
 for name,pin in inputs.items():
  need(isinstance(pin,dict) and set(pin)=={'path','sha256'} and isinstance(pin['sha256'],str) and len(pin['sha256'])==64 and all(c in '0123456789abcdef' for c in pin['sha256']),'invalid pin');p=Path(pin['path']).resolve(strict=True);need(p.is_file() and digest(p,guard)==pin['sha256'],'input pin mismatch: '+name);paths[name]=p
 code=[Path(__file__).resolve()]
 for path in [request,*paths.values(),*code]:need(not out.is_relative_to(path.parent) and not path.is_relative_to(out),'output overlaps input or code')
 codehash={p.name:digest(p,guard) for p in code};a=Rows(paths['baseline_rows'],paths['baseline_runs'],h,w);b=Rows(paths['candidate_rows'],paths['candidate_runs'],h,w);matched=0;examples=[]
 try:
  for y in range(h):
   if y%64==0:guard()
   count,diffs=compare_row(a.row(y),b.row(y),w);matched+=count
   for x0,x1,old,new in diffs:
    if len(examples)<20:examples.append({'row':y,'start':x0,'end':x1,'baseline':old,'candidate':new})
 finally:a.close();b.close()
 for name,p in paths.items():need(digest(p,guard)==inputs[name]['sha256'],'input changed: '+name)
 need(request.read_bytes()==raw and {p.name:digest(p,guard) for p in code}==codehash,'request or code changed');guard()
 total=w*h;report={'schema':'full-grid-comparison-report-v1','status':'equal' if matched==total else 'different','total_cells':total,'matching_cells':matched,'different_cells':total-matched,'examples':examples,'inputs_sha256':{k:v['sha256'] for k,v in inputs.items()},'request_sha256':hashlib.sha256(raw).hexdigest(),'code_sha256':codehash,'elapsed_seconds':time.monotonic()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limitation':'Cell equality checks the supplied grids, not source provenance, geographic correctness or approval.'}
 out.mkdir(mode=0o700);tmp=out/'report.pending';final=out/'report.json';linked=False
 try:
  with tmp.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(tmp,final);linked=True;fd=os.open(out,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd);tmp.unlink();fd=os.open(out,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 except OSError as e:
  if linked or final.exists():raise RuntimeError('report marker may exist; inspect before retry') from e
  raise
 return report

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('request');p.add_argument('output');a=p.parse_args()
 try:print(json.dumps(run(a.request,a.output)))
 except Exception as e:raise SystemExit('error: '+str(e))

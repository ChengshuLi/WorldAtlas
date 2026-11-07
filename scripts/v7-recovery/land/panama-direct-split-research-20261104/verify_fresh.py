#!/usr/bin/python3
"""Independent interval sweep of fresh direct split against selected seed and stage-2.

All target-component cells must be covered once and match both baselines; no
assignment is inferred from a reference grid. The baselines are used only here.
"""
import hashlib,json,os,sys
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parent.parent
H,W=54614,131072
D=R/'panama-direct-split-fresh-output-20261104'
S=R/'actual-stage2-seed-output-retry-20261104'
B=R/'actual-stage2-geodesic-output-20261104'
C=R/'fresh-components-output-20261104'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def need(a,m):
 if not a:raise ValueError(m)
class Rows:
 def __init__(self,folder,rows,runs,n):
  self.a=np.fromfile(folder/rows,dtype='<u4');self.n=n;self.fd=os.open(folder/runs,os.O_RDONLY)
  try:
   need(len(self.a)==H+1 and self.a[0]==0 and np.all(self.a[1:]>=self.a[:-1]),'bad offsets '+str(folder))
   need(os.fstat(self.fd).st_size==int(self.a[-1])*n*4,'bad stream size '+str(folder))
  except BaseException:
   os.close(self.fd);self.fd=None;raise
 def row(self,y):
  start,stop=map(int,self.a[y:y+2]);raw=os.pread(self.fd,(stop-start)*self.n*4,start*self.n*4)
  need(len(raw)==(stop-start)*self.n*4,'short row')
  return np.frombuffer(raw,dtype='<u4').reshape(-1,self.n)
 def close(self):
  if self.fd is not None:os.close(self.fd);self.fd=None
 def __del__(self):
  if getattr(self,'fd',None) is not None:self.close()

def main():
 report=json.loads((D/'report.json').read_text()); root=report['component_id_current_generation_only']
 for path,h in report['inputs_sha256'].items():need(sha(R/path)==h,'changed input '+path)
 need(sha(D/'direct-rows.u32le')==report['direct_rows_sha256'] and sha(D/'direct-spans.u32le')==report['direct_spans_sha256'],'changed direct output')
 need(sha(S/'report.json')=='ade23ba357813c95cc7edde7cceb313a49fccabf4489b1f7f2944925d44645ce','changed seed report')
 need(sha(B/'report.json')=='9086511ba0fb64a9331847cc8271129c125cec4e0e873ab04ad719023a503a20','changed stage2 report')
 need(report.get('schema')=='panama-direct-source-split-prototype-v1' and report.get('status')=='unselected-research','unexpected direct report')
 seed=json.loads((S/'report.json').read_text());base=json.loads((B/'report.json').read_text())
 reference_pins={S/'rows.u32le':seed['seed_rows_sha256'],S/'runs.u32le':seed['seed_runs_sha256'],B/'rows.u32le':base['output_rows_sha256'],B/'runs.u32le':base['output_runs_sha256'],D/'direct-rows.u32le':report['direct_rows_sha256'],D/'direct-spans.u32le':report['direct_spans_sha256'],S/'report.json':'ade23ba357813c95cc7edde7cceb313a49fccabf4489b1f7f2944925d44645ce',B/'report.json':'9086511ba0fb64a9331847cc8271129c125cec4e0e873ab04ad719023a503a20',D/'report.json':sha(D/'report.json')}
 reference_pins.update({R/path:h for path,h in report['inputs_sha256'].items()})
 for p,h in reference_pins.items():need(sha(p)==h,'changed reference '+str(p))
 d=Rows(D,'direct-rows.u32le','direct-spans.u32le',3)
 c=Rows(C,'rows.u32le','runs.u32le',3)
 seedrows=Rows(S,'rows.u32le','runs.u32le',2)
 baserows=Rows(B,'rows.u32le','runs.u32le',2)
 cells=seedmatch=basematch=0;diff=[]
 for y in range(H):
  direct=d.row(y);components=c.row(y);comp=[(int(a),int(b)) for a,b,k in components if int(k)==root]
  target=[]
  for a,b,k in direct:
   a,b,k=int(a),int(b),int(k);need(0<=a<b<=W and k in (20,21) and (not target or target[-1][1]<=a),'invalid direct spans')
   if target and target[-1][1]==a:target[-1]=(target[-1][0],b)
   else:target.append((a,b))
  merged=[]
  for a,b in comp:
   if merged and merged[-1][1]==a:merged[-1]=(merged[-1][0],b)
   else:merged.append((a,b))
  need(target==merged,'target coverage mismatch at row '+str(y))
  for stream,kind in ((seedrows.row(y),'seed'),(baserows.row(y),'stage2')):
   need(len(stream) and stream[-1,0]==W and np.all(stream[1:,0]>stream[:-1,0]),'bad reference row')
   ends=stream[:,0]
   for a,b,k in direct:
    a,b,k=int(a),int(b),int(k);i=int(np.searchsorted(ends,a,side='right'));x=a
    while x<b:
     e=min(b,int(ends[i]));n=e-x
     if kind=='seed':cells+=n;seedmatch+=n*(int(stream[i,1])==k)
     else:basematch+=n*(int(stream[i,1])==k)
     if int(stream[i,1])!=k and len(diff)<20:diff.append([kind,y,x,e,k,int(stream[i,1])])
     x=e;i+=1
 for stream in (d,c,seedrows,baserows):stream.close()
 for p,h in reference_pins.items():need(sha(p)==h,'input changed during sweep '+str(p))
 out={'schema':'panama-fresh-split-independent-interval-sweep-v1','direct_report_sha256':sha(D/'report.json'),'seed_report_sha256':sha(S/'report.json'),'stage2_report_sha256':sha(B/'report.json'),'cells':cells,'seed_matching_cells':seedmatch,'stage2_matching_cells':basematch,'status':'passed' if cells==seedmatch==basematch==report['graph']['selected_cells'] else 'failed','examples':diff,'direct_and_component_coverage':'exact'}
 outpath=Path(__file__).with_name('fresh-verification.json');need(not outpath.exists(),'output exists');outpath.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out));need(cells==seedmatch==basematch and cells==report['graph']['selected_cells'],'mismatch')
if __name__=='__main__':main()

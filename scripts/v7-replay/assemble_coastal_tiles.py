#!/usr/bin/env python3
"""Assemble validated non-overlapping coastal tiles into a research layer."""
import argparse,gzip,hashlib,io,json,os
from pathlib import Path
import coastal_core as core
from decision_snapshot import read_snapshot
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exclusive_outputs import write_json_exclusive
from build_coastal_tile import sha


class HashReader:
 def __init__(self,raw):self.raw=raw;self.digest=hashlib.sha256()
 def read(self,n=-1):
  b=self.raw.read(n);self.digest.update(b);return b

def verify_spans(path,expected_sha,box,codes,expected_cells,expected_spans):
 x0,x1,y0,y1=box;last_y=y0-1;cells=spans=0
 with path.open('rb') as raw:
  reader=HashReader(raw)
  with gzip.GzipFile(fileobj=reader,mode='rb') as gz:
   with io.TextIOWrapper(gz,encoding='utf8') as f:
    for line in f:
     rec=json.loads(line);y=rec.get('row')
     if type(y) is not int or not (y0<=y<y1) or y<=last_y:raise ValueError('unordered or invalid tile row')
     last_y=y;end=x0
     if not isinstance(rec.get('spans'),list) or not rec['spans']:raise ValueError('empty or invalid tile row')
     for s in rec['spans']:
      a,b,c=s.get('start'),s.get('end'),s.get('code')
      if (type(a) is not int or type(b) is not int or type(c) is not int or not (x0<=a<b<=x1) or a<end
          or c not in codes or not s.get('rule_id') or not s.get('member_id')):raise ValueError('invalid tile span')
      cells+=b-a;spans+=1;end=b
  if reader.digest.hexdigest()!=expected_sha:raise ValueError('tile span hash mismatch')
 if cells!=expected_cells or spans!=expected_spans:raise ValueError('tile assignment count mismatch')


def cover(boxes,width,height):
 events={}
 for i,(x0,x1,y0,y1) in enumerate(boxes):
  if not (0<=x0<x1<=width and 0<=y0<y1<=height):raise ValueError('invalid tile bounds')
  events.setdefault(y0,[[],[]])[1].append((i,x0,x1));events.setdefault(y1,[[],[]])[0].append((i,x0,x1))
 ys=sorted(events)
 if not ys or ys[0]!=0 or ys[-1]!=height:raise ValueError('tile coverage gap')
 active={}
 for idx,y in enumerate(ys):
  for i,_,_ in events[y][0]:active.pop(i)
  for i,a,b in events[y][1]:active[i]=(a,b)
  if idx==len(ys)-1:break
  x=0
  for a,b in sorted(active.values()):
   if a!=x:raise ValueError('tile coverage gap or overlap')
   x=b
  if x!=width:raise ValueError('tile coverage gap or overlap')
 if active:raise ValueError('unclosed tile bounds')


def assemble(snapshot,snapshot_sha,entries,root,out,width,height,allow_selected_research=False):
 decision,pairs,_,_,_=core.policy(snapshot,allow_selected_research=allow_selected_research)
 root=root.resolve();out=out.resolve()
 if not out.is_relative_to(root):raise ValueError('output manifest must be within input root')
 tiles=[];boxes=[];baseline=None;total_cells=total_spans=0
 for entry in entries:
  p=(root/entry['manifest_path']).resolve()
  if not p.is_relative_to(root) or sha(p)!=entry['manifest_sha256']:raise ValueError('tile manifest path/hash mismatch')
  m=json.loads(p.read_text());cols=m.get('core_cols');rows=m.get('core_rows')
  if (m.get('schema')!='worldatlas-coastal-tile-candidate-v1' or m.get('status')!='partial-unverified-research-not-published'
      or m.get('grid')!={'width':width,'height':height,'angular_step_deg':360/width}
      or m.get('policy_id')!=decision['id'] or m.get('policy_definition')!=decision['definition']
      or m.get('decision_snapshot_sha256')!=snapshot_sha or m.get('decision_revision')!=snapshot['decision_revision']['id']
      or m.get('entity_revision')!=snapshot['decision_revision']['entity_revision']
      or not isinstance(cols,list) or len(cols)!=2 or not isinstance(rows,list) or len(rows)!=2
      or any(type(x) is not int for x in cols+rows)):
   raise ValueError('tile metadata mismatch')
  lineage={k:m.get(k) for k in ('inputs','algorithm_sha256','core_sha256','shore_sha256','geometry_sha256')}
  valid_sha=lambda v:isinstance(v,str) and len(v)==64 and all(c in '0123456789abcdef' for c in v)
  pins=lineage['inputs'];required_pins={'physical_rows_sha256','physical_runs_sha256','physical_report_sha256','land_rows_sha256','land_runs_sha256','land_report_sha256'}
  if (not isinstance(pins,dict) or set(pins)!=required_pins or not all(valid_sha(v) for v in pins.values())
      or not all(valid_sha(lineage[k]) for k in ('algorithm_sha256','core_sha256','shore_sha256','geometry_sha256'))):
   raise ValueError('tile lineage is incomplete')
  if baseline is None:baseline=lineage
  elif baseline!=lineage:raise ValueError('mixed coastal input lineage or algorithms')
  box=[*cols,*rows];boxes.append(box);span=(p.parent/m['span_file']['path']).resolve()
  if not span.is_relative_to(root):raise ValueError('tile span outside input root')
  verify_spans(span,m['span_file']['sha256'],box,{x[2] for x in pairs},m['assigned_cells'],m['span_count'])
  total_cells+=m['assigned_cells'];total_spans+=m['span_count']
  tiles.append({'core_cols':cols,'core_rows':rows,'span_file':{'path':os.path.relpath(span,out.parent),'sha256':m['span_file']['sha256']}})
 cover(boxes,width,height)
 return {'schema':'worldatlas-full-water-assignment-tiles-v1','status':'completed_unverified_candidate_not_published',
    'grid':{'width':width,'height':height,'angular_step_deg':360/width,'row_convention':'north-to-south; cell centers; half-open [start,end) x spans'},
    'coverage':{'complete':True,'meaning':'all tile cores cover grid; assignment coverage is generator assertion and geographic semantics remain unverified'},
    'source':{**baseline['inputs'],'decision_id':decision['id'],'policy_definition':decision['definition'],'policy_sha256':snapshot_sha,
       'decision_revision':snapshot['decision_revision']['id'],'entity_revision':snapshot['decision_revision']['entity_revision']},
    'algorithm_pins':{k:v for k,v in baseline.items() if k!='inputs'},'assigned_cells':total_cells,'span_count':total_spans,'tiles':tiles}


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('snapshot','snapshot-sha256','input-root','tile-list','out'):p.add_argument('--'+k,required=True)
 p.add_argument('--allow-unverified-snapshot',action='store_true');p.add_argument('--allow-draft',action='store_true');p.add_argument('--allow-selected-research-policy',action='store_true')
 a=p.parse_args()
 if not a.allow_unverified_snapshot:raise ValueError('unverified snapshot requires explicit research opt-in')
 if Path(a.snapshot).stat().st_size>16*1024*1024:raise ValueError('snapshot exceeds size limit')
 snap=read_snapshot(Path(a.snapshot),a.snapshot_sha256,allow_draft=a.allow_draft)
 root=Path(a.input_root);config=Path(a.tile_list).resolve()
 if not config.is_relative_to(root.resolve()):raise ValueError('tile list outside input root')
 entries=json.loads(config.read_text())['tiles'];out=Path(a.out)
 result=assemble(snap,a.snapshot_sha256,entries,root,out,131072,54614,allow_selected_research=a.allow_selected_research_policy)
 write_json_exclusive(out,result,indent=2)
 print(json.dumps({'status':result['status'],'tiles':len(result['tiles']),'assigned_cells':result['assigned_cells']}))

if __name__=='__main__':main()

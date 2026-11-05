#!/usr/bin/env python3
"""Reusable interval partition for bounded research validation.

The old topology-specific command and embedded source observations were retired.
This function accepts caller-supplied inputs and makes no geographic decision.
"""
import bisect, struct, sys
from array import array
from collections import Counter
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'audit/ocean-interfaces-20261103/fresh-water-partition'))
from partition_core import _DSU, split_eligible

def partition(rows, width, height, cuts, seeds, output):
    """rows(y) -> sorted disjoint eligible intervals. Output must not exist."""
    output=Path(output); output.mkdir(mode=0o700,parents=False,exist_ok=False)
    dsu=_DSU(); row_offsets=array('I',[0]); seednodes={}; prev=[]; cells=0
    with (output/'nodes.u32le').open('xb') as f:
        for y in range(height):
            raw=list(rows(y));
            if raw!=sorted(raw) or any(a<0 or a>=b or b>width for a,b in raw) or any(raw[i][1]>raw[i+1][0] for i in range(len(raw)-1)):
                raise ValueError(f'invalid selected intervals at row {y}')
            pieces=split_eligible(raw,sorted(cuts.horizontal.get(y,())),width); cur=[]
            for a,b in pieces:
                nid=dsu.add(); cur.append((a,b,nid)); cells+=b-a
                for code,(x,sy) in seeds.items():
                    if y==sy and a<=x<b:
                        if code in seednodes: raise ValueError('duplicate seed')
                        seednodes[code]=nid
                f.write(struct.pack('<III',a,b,nid))
            if prev:
                blocked=sorted(cuts.vertical.get(y-1,())); i=j=0
                while i<len(prev) and j<len(cur):
                    a,b,n=prev[i]; c,d,m=cur[j]; lo=max(a,c); hi=min(b,d)
                    if lo<hi and hi-lo>bisect.bisect_left(blocked,hi)-bisect.bisect_left(blocked,lo): dsu.union(n,m)
                    if b<=d:i+=1
                    if d<=b:j+=1
            if cur and cur[0][0]==0 and cur[-1][1]==width and y not in cuts.wrap:dsu.union(cur[0][2],cur[-1][2])
            if len(dsu.parent)>0xffffffff: raise OverflowError('too many nodes')
            row_offsets.append(len(dsu.parent)); prev=cur
    if set(seednodes)!=set(seeds): raise ValueError('missing seed')
    seedroots={dsu.find(n):code for code,n in seednodes.items()}
    if len(seedroots)!=len(seeds): raise ValueError('seeds of different labels connected')
    # Compress parents once, turning repeated node reads into direct indexed lookup.
    for n in range(len(dsu.parent)): dsu.parent[n]=dsu.find(n)
    root_codes={root:code for root,code in seedroots.items()}; counts=Counter(); residual=Counter(); spans=0
    outrows=array('I',[0]); resrows=array('I',[0]); resspans=0
    with (output/'nodes.u32le').open('rb') as inp,(output/'partition-spans.u32le').open('xb') as out,(output/'residual-spans.u32le').open('xb') as res:
        for y in range(height):
            nrow=row_offsets[y+1]-row_offsets[y]; data=inp.read(nrow*12)
            if len(data)!=nrow*12: raise ValueError('truncated node spool')
            current=[]; rr=[]
            for a,b,n in struct.iter_unpack('<III',data):
                root=dsu.parent[n]; code=root_codes.get(root)
                target=current if code is not None else rr; val=code if code is not None else root
                (counts if code is not None else residual)[val]+=b-a
                if target and target[-1][1]==a and target[-1][2]==val:target[-1]=(target[-1][0],b,val)
                else:target.append((a,b,val))
            for a,b,v in current:out.write(struct.pack('<III',a,b,v))
            for a,b,v in rr:res.write(struct.pack('<III',a,b,v))
            spans+=len(current); resspans+=len(rr); outrows.append(spans); resrows.append(resspans)
    if sum(counts.values())+sum(residual.values())!=cells:raise AssertionError('cell conservation failure')
    for filename,values in [('partition-rows.u32le',outrows),('residual-rows.u32le',resrows)]:
        np.asarray(values,dtype='<u4').tofile(output/filename)
    return {'selected_cells':cells,'node_count':len(dsu.parent),'seed_roots':{str(code):root for root,code in seedroots.items()},'cells_by_code':dict(counts),'residual_cells':sum(residual.values()),'residual_components':dict(residual),'partition_spans':spans,'residual_spans':resspans}


if __name__ == '__main__':
    raise SystemExit('Retired topology-specific CLI; use externally sourced decisions.')


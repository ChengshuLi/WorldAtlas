#!/usr/bin/env python3
"""Draft cut-partition for physical Eurasia and Americas; no prior label grid.

Nodes are split physical component RLE intervals. Four-neighbor adjacency is
blocked by pinned source-cut edges; seeded connected roots get candidate labels.
Unseeded roots are emitted separately, never guessed. Output is sparse
(start,end,code) triples, little-endian u32 with u32 row offsets.
"""
import bisect, hashlib, json, struct, sys, time
from array import array
from collections import Counter
from pathlib import Path
import numpy as np
from build_candidate import BASE, OUT, CR, CU, PINS, sha, W, H
sys.path.insert(0,str(BASE/'audit/ocean-interfaces-20261103/fresh-water-partition'))
from partition_core import CutEdges, split_eligible, _DSU

CODE={'Europe':19,'Asia':18,'North America':20,'South America':21}
SELECTED={650207,459650}

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

def main():
    started=time.time(); proposal=OUT/'topology-proposal.json'; p=json.loads(proposal.read_bytes()); proposal_hash=sha(proposal)
    for path,h in PINS.items():
        if sha(path)!=h:raise ValueError('input pin mismatch '+str(path))
    cuts=CutEdges()
    for r in p['routes']:
        path=Path(r['edge_file'])
        if sha(path)!=r['edge_sha256']:raise ValueError('edge pin mismatch '+str(path))
        c=CutEdges.read_u32le(path)
        for y,xx in c.horizontal.items():cuts.horizontal[y].update(xx)
        for y,xx in c.vertical.items():cuts.vertical[y].update(xx)
        cuts.wrap.update(c.wrap)
    offsets=np.memmap(CR,dtype='<u4',mode='r'); runs=np.memmap(CU,dtype='<u4',mode='r').reshape(-1,3)
    if len(offsets)!=H+1 or offsets[0]!=0 or offsets[-1]!=len(runs) or np.any(offsets[1:]<offsets[:-1]):raise ValueError('invalid component rows')
    def rows(y):
        row=runs[offsets[y]:offsets[y+1]]; return [(int(a),int(b)) for a,b,_ in row[np.isin(row[:,2],list(SELECTED))]]
    seeds={CODE[s['side']]:(s['grid_x'],s['grid_y']) for s in p['seed_proposals'] if s['side'] in CODE}
    out=OUT/'partition-draft-20261104'; result=partition(rows,W,H,cuts,seeds,out)
    for path,h in PINS.items():
        if sha(path)!=h:raise ValueError('input changed '+str(path))
    if sha(proposal)!=proposal_hash:raise ValueError('proposal changed')
    for r in p['routes']:
        if sha(Path(r['edge_file']))!=r['edge_sha256']:raise ValueError('edge file changed')
    result.update({'schema':'mainland-source-cut-partition-draft-v1','status':'local-unreviewed-not-production','grid':{'width':W,'height':H},'component_ids':sorted(SELECTED),'proposal_sha256':proposal_hash,'pins':p['pins'],'witnesses':[s for s in p['seed_proposals'] if s['side'] in CODE], 'outputs':{name:{'sha256':sha(out/name),'bytes':(out/name).stat().st_size} for name in ['partition-spans.u32le','partition-rows.u32le','residual-spans.u32le','residual-rows.u32le']},'elapsed_seconds':time.time()-started,'caveat':'Exploratory four-neighbor graph and left-oriented line tie; seed continent names and shore closure are draft policy. Unseeded components are not assigned. This is not evidence of reviewed decisions or production readiness; no V2/V6 continent grid is read.'})
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()

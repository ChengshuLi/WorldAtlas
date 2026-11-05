#!/usr/bin/env python3
"""Group diagnostic cells by local physical-mask connectivity, without relabeling them."""
import argparse,json
import numpy as np
from scipy.ndimage import label
from delta_side_screen import read_grid

def screen(rows,runs,bounds,differences,width,height,step,padding,connectivity):
    w,s,e,n=bounds;x0=max(0,int((w+180)//step)-padding);x1=min(width-1,int((e+180)//step)+padding+1)
    y0=max(0,int((90-n)//step)-padding);y1=min(height-1,int((90-s)//step)+padding+1)
    if x1-x0+1>10000 or y1-y0+1>10000 or (x1-x0+1)*(y1-y0+1)>10000000:raise ValueError('window too large')
    if len(rows)!=height+1 or rows[-1]*2!=len(runs):raise ValueError('bad grid index')
    runs=runs.reshape(-1,2);xs=np.arange(x0,x1+1);mask=np.zeros((y1-y0+1,len(xs)),dtype=bool)
    for y in range(y0,y1+1):
        row=runs[rows[y]:rows[y+1]]
        if not len(row) or row[-1,0]!=width or np.any(row[1:,0]<=row[:-1,0]):raise ValueError('invalid row')
        mask[y-y0,:]=row[np.searchsorted(row[:,0],xs,side='right'),1]==17
    structure=np.array([[0,1,0],[1,1,1],[0,1,0]]) if connectivity==4 else np.ones((3,3),dtype=int)
    labs,count=label(mask,structure=structure); edges=set(labs[0,:])|set(labs[-1,:])|set(labs[:,0])|set(labs[:,-1]);edges.discard(0)
    sizes=np.bincount(labs.ravel()); result={}
    for k,items in differences.items():
        groups={}
        for z in items:
            x,y=z['x'],z['y']
            if not(x0<=x<=x1 and y0<=y<=y1):raise ValueError('cell outside screen')
            i=int(labs[y-y0,x-x0])
            if not i:raise ValueError('difference cell is not physical land')
            groups[i]=groups.get(i,0)+1
        result[k]={'edge_open_cells':sum(v for i,v in groups.items() if i in edges),'locally_bounded_cells':sum(v for i,v in groups.items() if i not in edges),'groups':sorted([{'local_id':i,'difference_cells':v,'component_cells_in_window':int(sizes[i]),'touches_window_edge':i in edges} for i,v in groups.items()],key=lambda g:-g['difference_cells'])}
    return {'connectivity':connectivity,'padding_cells':padding,'window':[x0,y0,x1,y1],'local_component_count':int(count),'groups':result}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rows','runs','rows-sha','runs-sha','differences','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--width',type=int,required=True);p.add_argument('--height',type=int,required=True);p.add_argument('--step',type=float,required=True);p.add_argument('--padding',type=int,default=5);p.add_argument('--connectivity',type=int,choices=[4,8],default=4)
    a=p.parse_args();data=json.load(open(a.differences));rows=read_grid(a.rows,a.rows_sha);runs=read_grid(a.runs,a.runs_sha)
    if a.padding<0:raise ValueError('negative padding')
    out=screen(rows,runs,data['bounds'],data['differences'],a.width,a.height,a.step,a.padding,a.connectivity)
    out.update({'physical_rows_sha256':a.rows_sha,'physical_runs_sha256':a.runs_sha,'method':'local connected components; boundary-open does not prove mainland; bounded only within selected connectivity'})
    with open(a.output,'x') as f:json.dump(out,f)
    print(json.dumps(out))

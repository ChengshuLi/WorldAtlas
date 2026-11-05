"""Experimental priority-flood/D8 drainage roots on a regular metric raster."""
import heapq, math
import numpy as np
from numba import njit

@njit
def drainage(elevation, valid, cellsize):
    h,w=elevation.shape;size=h*w
    flood=np.full((h,w),np.inf,np.float64);parent=np.full(size,-2,np.int32)
    order=np.empty(size,np.int32);count=0
    heap=[(0.0,0)];heap.pop()
    for r in range(h):
        for c in range(w):
            i=r*w+c
            if not valid[r,c]:parent[i]=-3
            elif r==0 or c==0 or r==h-1 or c==w-1:
                flood[r,c]=elevation[r,c];parent[i]=-1;heapq.heappush(heap,(float(flood[r,c]),i))
    while heap:
        v,i=heapq.heappop(heap);order[count]=i;count+=1;r=i//w;c=i%w
        for dr in range(-1,2):
            for dc in range(-1,2):
                rr=r+dr;cc=c+dc
                if (dr!=0 or dc!=0) and 0<=rr<h and 0<=cc<w:
                    j=rr*w+cc
                    if parent[j]==-2:
                        parent[j]=i;flood[rr,cc]=max(v,elevation[rr,cc]);heapq.heappush(heap,(float(flood[rr,cc]),j))
    flow=parent.copy()
    for k in range(count):
        i=order[k];r=i//w;c=i%w
        if parent[i]<0:continue
        best=0.0
        for dr in range(-1,2):
            for dc in range(-1,2):
                rr=r+dr;cc=c+dc
                if (dr!=0 or dc!=0) and 0<=rr<h and 0<=cc<w and math.isfinite(flood[rr,cc]):
                    slope=(flood[r,c]-flood[rr,cc])/(cellsize*math.sqrt(dr*dr+dc*dc))
                    if slope>best:best=slope;flow[i]=rr*w+cc
    roots=np.full(size,-1,np.int32)
    for i in range(size):
        if flow[i]==-3 or flow[i]==-2:roots[i]=-2
        elif flow[i]==-1:roots[i]=i
    for i in range(size):
        if roots[i]!=-1:continue
        j=i;steps=0
        while roots[j]==-1:
            j=flow[j];steps+=1
            if j<0 or steps>size:raise ValueError('flow cycle or unconnected cell')
        target=roots[j];j=i
        while roots[j]==-1:
            nxt=flow[j];roots[j]=target;j=nxt
    return roots.reshape((h,w)),flood,flow.reshape((h,w))

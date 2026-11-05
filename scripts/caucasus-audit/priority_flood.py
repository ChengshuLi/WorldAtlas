"""Conservative bounded priority-flood and local D8 research primitives.

Array edges and neighbors of invalid cells are artificial outlets. This is not
an authoritative watershed, named-outlet mapping, or boundary-selection tool.
"""
import heapq
import math
import numpy as np
from scipy.ndimage import minimum_filter


def priority_flood(elevation, valid):
    z=np.asarray(elevation,dtype='float64')
    valid=np.asarray(valid,dtype=bool)
    if z.ndim!=2 or valid.shape!=z.shape or not valid.any() or not np.isfinite(z[valid]).all():
        raise ValueError('valid finite two-dimensional elevation grid required')
    height,width=z.shape
    boundary=valid & ~minimum_filter(valid.astype('uint8'),size=3,mode='constant',cval=0).astype(bool)
    filled=np.full(z.shape,np.nan)
    parent=np.full(z.shape,-2,dtype='int64')
    heap=[]
    for row,col in np.argwhere(boundary):
        row=int(row);col=int(col)
        filled[row,col]=z[row,col];parent[row,col]=-1
        heapq.heappush(heap,(filled[row,col],row,col))
    while heap:
        value,row,col=heapq.heappop(heap)
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                if not (dr or dc):continue
                nr,nc=row+dr,col+dc
                if 0<=nr<height and 0<=nc<width and valid[nr,nc] and parent[nr,nc]==-2:
                    parent[nr,nc]=row*width+col
                    filled[nr,nc]=max(z[nr,nc],value)
                    heapq.heappush(heap,(filled[nr,nc],nr,nc))
    if np.any(parent[valid]==-2):raise RuntimeError('unvisited valid pixels')
    return filled,parent


def trace(filled,valid,parent,start,dx_metres,dy_metres):
    z=np.asarray(filled);valid=np.asarray(valid,dtype=bool);parent=np.asarray(parent)
    if z.ndim!=2 or z.shape!=valid.shape or z.shape!=parent.shape:
        raise ValueError('matching two-dimensional arrays required')
    if not math.isfinite(dx_metres) or not math.isfinite(dy_metres) or min(dx_metres,dy_metres)<=0:
        raise ValueError('positive finite pixel distances required')
    height,width=z.shape;row,col=start
    if not(0<=row<height and 0<=col<width and valid[row,col]):return [],'invalid_start'
    path=[];seen=set()
    while len(path)<height*width:
        if (row,col) in seen:return path,'cycle'
        seen.add((row,col));path.append((row,col))
        if parent[row,col]==-1:
            return path,'crop_edge' if row in (0,height-1) or col in (0,width-1) else 'invalid_neighbor'
        best=0;target=None
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                if not(dr or dc):continue
                nr,nc=row+dr,col+dc
                if not(0<=nr<height and 0<=nc<width and valid[nr,nc]):continue
                slope=(z[row,col]-z[nr,nc])/math.hypot(dc*dx_metres,dr*dy_metres)
                if slope>best:best=slope;target=(nr,nc)
        if target is None:
            index=int(parent[row,col])
            if not 0<=index<height*width:return path,'invalid_parent'
            target=(index//width,index%width)
        row,col=target
    return path,'step_limit'

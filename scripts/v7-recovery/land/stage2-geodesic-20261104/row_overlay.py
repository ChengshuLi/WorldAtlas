"""Experimental numeric row overlay, independent of geography and policy.

No production caller uses this yet. Actual interval endpoints determine the
work; no pixel expansion, sampling, root cache ceiling or map-specific path.
"""
import numpy as np
import os

MAX_U32=(1<<32)-1


class RowStream:
    """Ordinary full-row I/O, avoiding Python unpacking for every record."""
    def __init__(self, rows, runs, height, columns):
        self.file=None
        if type(height) is not int or not 0<height<=MAX_U32 or columns not in (2,3):
            raise ValueError('invalid stream shape')
        if os.stat(rows).st_size!=(height+1)*4 or os.stat(runs).st_size%(columns*4):
            raise ValueError('invalid stream lengths')
        self.offsets=np.fromfile(rows,dtype='<u4');self.columns=columns;self.y=0
        count=os.stat(runs).st_size//(columns*4)
        if int(self.offsets[0])!=0 or int(self.offsets[-1])!=count or np.any(self.offsets[1:]<self.offsets[:-1]):
            raise ValueError('invalid stream offsets')
        self.file=open(runs,'rb')

    def next(self):
        if self.y+1>=len(self.offsets):raise ValueError('stream exhausted')
        length=(int(self.offsets[self.y+1])-int(self.offsets[self.y]))*self.columns*4
        raw=self.file.read(length)
        if len(raw)!=length:raise ValueError('truncated stream')
        self.y+=1
        return np.frombuffer(raw,dtype='<u4').reshape(-1,self.columns)

    def finish(self):
        if self.y!=len(self.offsets)-1 or self.file.read(1):raise ValueError('stream count mismatch')

    def close(self):
        if self.file is not None:self.file.close()


def records(values, columns):
    values=np.asarray(values)
    if (values.ndim!=2 or values.shape[1]!=columns or values.dtype.kind not in 'iu' or
            np.any(values<0) or np.any(values>MAX_U32)):
        raise ValueError('invalid uint32 row records')
    return values.astype(np.uint32,copy=False)


def full_row(values,width,allowed,label):
    values=records(values,2)
    if (not len(values) or int(values[-1,0])!=width or int(values[0,0])==0 or
            np.any(values[1:,0]<=values[:-1,0]) or not np.all(np.isin(values[:,1],allowed))):
        raise ValueError('invalid or incomplete '+label+' row')
    return values


def overlay(width,components,physical,seed):
    """Return cuts and component/physical/seed owners for each common span.

    Component owner -1 means a genuine gap; root zero is an ordinary identity.
    The source record index is returned rather than a lossy sentinel root.
    Redundantly split valid full rows are accepted, retaining all endpoints.
    """
    if type(width) is not int or not 0<width<=MAX_U32:raise ValueError('invalid row width')
    components=records(components,3)
    physical=full_row(physical,width,[1,17],'physical')
    seed=full_row(seed,width,[0,17,18,19,20,21,22],'seed')
    if len(components) and (np.any(components[:,0]>=components[:,1]) or
            np.any(components[:,1]>width) or np.any(components[1:,0]<components[:-1,1])):
        raise ValueError('overlapping or invalid component row')
    cuts=np.unique(np.concatenate((np.asarray([0,width],dtype=np.uint32),components[:,:2].ravel(),physical[:,0],seed[:,0])))
    left,right=cuts[:-1],cuts[1:]
    po=np.searchsorted(physical[:,0],left,side='right')
    so=np.searchsorted(seed[:,0],left,side='right')
    owner=np.full(len(left),-1,dtype=np.int64)
    if len(components):
        candidate=np.searchsorted(components[:,0],left,side='right')-1
        safe=np.maximum(candidate,0)
        present=(candidate>=0) & (left<components[safe,1])
        owner[present]=candidate[present]
    return left,right,owner,physical[po,1],seed[so,1]

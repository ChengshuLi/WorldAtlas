"""Numeric row overlay, independent of geography and policy.

Actual interval endpoints determine the
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

    def next_rows(self,count):
        if type(count) is not int or count<1 or self.y+count>=len(self.offsets):
            raise ValueError('invalid row batch')
        offsets=self.offsets[self.y:self.y+count+1].astype(np.int64)
        offsets-=int(offsets[0]);length=int(offsets[-1])*self.columns*4
        raw=self.file.read(length)
        if len(raw)!=length:raise ValueError('truncated stream')
        self.y+=count
        return offsets,np.frombuffer(raw,dtype='<u4').reshape(-1,self.columns)

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
    return _owners(width,components[:,0],components[:,1],physical[:,0],physical[:,1],seed[:,0],seed[:,1])


def _owners(length,starts,stops,physical_ends,physical_codes,seed_ends,seed_codes):
    cuts=np.unique(np.concatenate((np.asarray([0,length],dtype=np.uint64),starts,stops,physical_ends,seed_ends)))
    left,right=cuts[:-1],cuts[1:]
    po=np.searchsorted(physical_ends,left,side='right')
    so=np.searchsorted(seed_ends,left,side='right')
    owner=np.full(len(left),-1,dtype=np.int64)
    if len(starts):
        candidate=np.searchsorted(starts,left,side='right')-1
        safe=np.maximum(candidate,0)
        present=(candidate>=0) & (left<stops[safe])
        owner[present]=candidate[present]
    return left,right,owner,physical_codes[po],seed_codes[so]


def _row_ids(offsets,count):
    offsets=np.asarray(offsets)
    if (offsets.ndim!=1 or len(offsets)<2 or offsets.dtype.kind not in 'iu' or
            int(offsets[0])!=0 or int(offsets[-1])!=count or
            np.any(offsets<0) or np.any(offsets[1:]<offsets[:-1])):
        raise ValueError('invalid batch row offsets')
    sizes=np.diff(offsets.astype(np.int64))
    return offsets.astype(np.int64),sizes,np.repeat(np.arange(len(sizes),dtype=np.uint64),sizes)


def _full_batch(width,offsets,values,allowed,label):
    values=records(values,2);offsets,sizes,rows=_row_ids(offsets,len(values))
    if np.any(sizes==0):raise ValueError('incomplete '+label+' row')
    starts=np.r_[0,values[:-1,0]];starts[offsets[:-1]]=0
    if (np.any(starts>=values[:,0]) or np.any(values[:,0]>width) or
            np.any(values[offsets[1:]-1,0]!=width) or not np.all(np.isin(values[:,1],allowed))):
        raise ValueError('invalid or incomplete '+label+' row')
    return rows*np.uint64(width)+values[:,0],values[:,1]


def overlay_batch(width,component_offsets,components,physical_offsets,physical,seed_offsets,seed):
    """General interval overlay across ordinary row batches, without pixels.

    uint64 positions pack row and column exactly. Every original row endpoint
    is retained by both complete source streams, so gaps cannot cross rows.
    """
    if type(width) is not int or not 0<width<=MAX_U32:raise ValueError('invalid row width')
    components=records(components,3)
    offsets,_,rows=_row_ids(component_offsets,len(components));height=len(offsets)-1
    if height>MAX_U32 or len(physical_offsets)!=height+1 or len(seed_offsets)!=height+1:
        raise ValueError('batch row counts differ')
    if len(components) and (np.any(components[:,0]>=components[:,1]) or np.any(components[:,1]>width)):
        raise ValueError('invalid component row')
    starts=rows*np.uint64(width)+components[:,0];stops=rows*np.uint64(width)+components[:,1]
    if np.any(starts[1:]<stops[:-1]):raise ValueError('overlapping component row')
    pe,pc=_full_batch(width,physical_offsets,physical,[1,17],'physical')
    se,sc=_full_batch(width,seed_offsets,seed,[0,17,18,19,20,21,22],'seed')
    return _owners(width*height,starts,stops,pe,pc,se,sc)

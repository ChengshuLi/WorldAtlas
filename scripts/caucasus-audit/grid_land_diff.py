"""Compare two checksum-pinned exclusive-end row-run grids over a cell window.

Output is a research artifact; it is neither a geographic correction nor proof
that either grid is correct. Use the proper physical/label lineage for the task.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import numpy as np


def diff_row(a,b,start,end,width,land_codes):
    for grid in (a,b):
        if grid.ndim!=2 or grid.shape[1]!=2 or not len(grid) or grid[0,0]==0 or grid[-1,0]!=width or np.any(np.diff(grid[:,0].astype('int64'))<=0):
            raise ValueError('invalid exclusive-end row')
    if not 0<=start<end<=width:raise ValueError('invalid column window')
    i=int(np.searchsorted(a[:,0],start,side='right'))
    j=int(np.searchsorted(b[:,0],start,side='right'))
    x=start
    while x<end:
        stop=min(int(a[i,0]),int(b[j,0]),end);first,second=int(a[i,1]),int(b[j,1])
        if first!=second and first in land_codes and second in land_codes:
            yield x,stop,first,second
        x=stop
        if int(a[i,0])<=x:i+=1
        if int(b[j,0])<=x:j+=1


def verify(path,expected):
    digest=hashlib.sha256();size=0
    with gzip.open(path,'rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            digest.update(block);size+=len(block)
    if digest.hexdigest()!=expected:raise ValueError('decompressed hash mismatch: '+path)
    return size


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('first','second'):
        parser.add_argument('--'+name+'-rows',required=True)
        parser.add_argument('--'+name+'-runs',required=True)
        parser.add_argument('--'+name+'-rows-sha256',required=True)
        parser.add_argument('--'+name+'-runs-sha256',required=True)
    parser.add_argument('--width',type=int,required=True)
    parser.add_argument('--height',type=int,required=True)
    parser.add_argument('--row-window',type=int,nargs=2,required=True)
    parser.add_argument('--column-window',type=int,nargs=2,required=True)
    parser.add_argument('--land-code',type=int,action='append',required=True)
    parser.add_argument('--output',required=True,help='new private JSON output')
    args=parser.parse_args()
    r0,r1=args.row_window;c0,c1=args.column_window
    if args.width<=0 or args.height<=0 or not(0<=r0<r1<=args.height and 0<=c0<c1<=args.width):
        parser.error('invalid grid dimensions or window')
    lengths={}
    for name in ('first','second'):
        for typ in ('rows','runs'):
            lengths[(name,typ)]=verify(getattr(args,name+'_'+typ),getattr(args,name+'_'+typ+'_sha256'))
    offsets=[]
    for name,path in (('first',args.first_rows),('second',args.second_rows)):
        with gzip.open(path,'rb') as stream:values=np.frombuffer(stream.read(),dtype='<u4')
        if len(values)!=args.height+1 or values[0]!=0 or np.any(np.diff(values.astype('int64'))<=0):
            raise ValueError('invalid row offsets')
        if int(values[-1])*8!=lengths[(name,'runs')]:raise ValueError('row offsets do not match run stream')
        offsets.append(values)
    counts=Counter();spans=[]
    with gzip.open(args.first_runs,'rb') as first,gzip.open(args.second_runs,'rb') as second:
        for row in range(r0,r1):
            grids=[]
            for values,stream in zip(offsets,(first,second)):
                start,end=int(values[row]),int(values[row+1]);stream.seek(start*8)
                data=stream.read((end-start)*8)
                if len(data)!=(end-start)*8:raise ValueError('truncated run stream')
                grids.append(np.frombuffer(data,dtype='<u4').reshape(-1,2))
            for lo,hi,a,b in diff_row(grids[0],grids[1],c0,c1,args.width,set(args.land_code)):
                spans.append([row,lo,hi,a,b]);counts[(a,b)]+=hi-lo
    with open(args.output,'x',encoding='utf-8') as out:
        json.dump({'spans':spans,'counts':[{'first':a,'second':b,'cells':n} for (a,b),n in sorted(counts.items())]},out)
    print('shared-land differences:',sum(counts.values()),'spans:',len(spans))


if __name__=='__main__':main()

"""Exact shortcut: return True only if the entire crop and neighbor rows are water.

Used before edges_for_crop. No persistent state; no changes to classification or
boundary certification. Run against the same already-pinned physical inputs.
"""
import numpy as np

def water_only_crop(physical,land,bounds,width,height):
    rows,runs=physical
    lrows,lruns=land
    x0,x1,y0,y1=bounds
    if not 0<x1-x0<=width:raise ValueError('invalid crop')
    # The original edge extractor inspects one extra row each side.
    # Split the x interval at the antimeridian, exactly as crop() does.
    intervals=[]; x=x0
    while x<x1:
        xm=x%width;take=min(x1-x,width-xm)
        intervals.append((xm,xm+take));x+=take
    for y in range(max(0,y0-1),min(height,y1+1)):
        first,last=int(rows[y]),int(rows[y+1])
        ends=runs[2*first:2*last:2];vals=runs[2*first+1:2*last:2]
        if not len(ends) or int(ends[0])<=0 or int(ends[-1])!=width or np.any(ends[1:]<=ends[:-1]):
            raise ValueError(f'invalid RLE row {y}')
        lf,ll=int(lrows[y]),int(lrows[y+1]); lends=lruns[2*lf:2*ll:2]
        if not len(lends) or int(lends[0])<=0 or int(lends[-1])!=width or np.any(lends[1:]<=lends[:-1]):
            raise ValueError(f'invalid RLE row {y}')
        for start,stop in intervals:
            a=int(np.searchsorted(ends,start,side='right'))
            b=int(np.searchsorted(ends,stop-1,side='right'))+1
            # Invalid values or any land fall back to the full extractor.
            if np.any(vals[a:b]!=1):return False
    return True

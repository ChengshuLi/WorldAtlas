#!/usr/bin/env python3
"""Compare complete uint32 row/run grids against an explicitly pinned reference."""
import argparse
from collections import Counter
import hashlib
import time
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from exclusive_outputs import write_json_exclusive

NAMES=('rows.u32le','runs.u32le')

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def combined(directory):
    h=hashlib.sha256()
    for name in NAMES:
        with (directory/name).open('rb') as f:
            for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def open_grid(directory,height):
    rows,runs=(directory/n for n in NAMES)
    if rows.stat().st_size!=(height+1)*4 or runs.stat().st_size==0 or runs.stat().st_size%8:
        raise ValueError('invalid grid stream size')
    offsets=np.memmap(rows,dtype='<u4',mode='r');spans=np.memmap(runs,dtype='<u4',mode='r').reshape(-1,2)
    if offsets[0]!=0 or int(offsets[-1])!=len(spans) or np.any(offsets[1:]<=offsets[:-1]):
        raise ValueError('invalid grid row offsets')
    return offsets,spans

def row(grid,y,width):
    offsets,spans=grid;result=spans[int(offsets[y]):int(offsets[y+1])]
    ends=result[:,0]
    if not len(ends) or int(ends[-1])!=width or ends[0]==0 or np.any(ends[1:]<=ends[:-1]):
        raise ValueError(f'invalid grid row endpoints: {y}')
    return result

def compare(candidate,reference,width,height,reference_sha256,out):
    started=time.perf_counter();candidate=Path(candidate).resolve();reference=Path(reference).resolve();out=Path(out)
    if type(width) is not int or type(height) is not int or not 0<width<=0xffffffff or not 0<height<=0xffffffff:
        raise ValueError('invalid grid dimensions')
    if set(reference_sha256)!=set(NAMES) or any(not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for v in reference_sha256.values()):
        raise ValueError('explicit reference stream pins are required')
    if out.resolve() in [d/n for d in (candidate,reference) for n in NAMES]:
        raise ValueError('output overlaps a grid stream')
    before={label:{n:sha(d/n) for n in NAMES} for label,d in (('candidate',candidate),('reference',reference))}
    if before['reference']!=reference_sha256:raise ValueError('reference grid hash mismatch')
    old=open_grid(reference,height);new=open_grid(candidate,height);pairs=Counter();changed=0
    for y in range(height):
        a=row(old,y,width);b=row(new,y,width)
        # Validate every row even when streams are identical. Different legal
        # RLE segmentation may represent exactly the same cells.
        if np.array_equal(a,b):continue
        ends=np.union1d(a[:,0],b[:,0]);starts=np.r_[np.uint32(0),ends[:-1]]
        av=a[np.searchsorted(a[:,0],starts,side='right'),1];bv=b[np.searchsorted(b[:,0],starts,side='right'),1]
        for i in np.flatnonzero(av!=bv):
            n=int(ends[i])-int(starts[i]);changed+=n;pairs[f'{int(av[i])}->{int(bv[i])}']+=n
    after={label:{n:sha(d/n) for n in NAMES} for label,d in (('candidate',candidate),('reference',reference))}
    if after!=before:raise ValueError('grid input changed during comparison')
    report={'schema':'worldatlas-full-grid-comparison-v1','status':'same-cells' if changed==0 else 'different-cells',
            'grid':{'width':width,'height':height},'cells_compared':width*height,'changed_cells':changed,
            'pair_counts':dict(sorted(pairs.items())),'byte_identical':before['candidate']==before['reference'],
            'reference_sha256':before['reference'],'candidate_sha256':before['candidate'],
            'reference_combined_sha256':combined(reference),'candidate_combined_sha256':combined(candidate),
            'limitations':['Exact equality verifies reproduction, not independent geographic correctness or publication approval.']}
    if any(sha(d/n)!=before[label][n] for label,d in (('candidate',candidate),('reference',reference)) for n in NAMES):
        raise ValueError('grid input changed before comparison report')
    report['processing_elapsed_seconds']=time.perf_counter()-started
    write_json_exclusive(out,report)
    return report

def main(argv=None, *, emit=print):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('candidate','reference','reference-rows-sha256','reference-runs-sha256','out'):p.add_argument('--'+name,required=True)
    p.add_argument('--allow-different', action='store_true')
    p.add_argument('--width',type=int,required=True);p.add_argument('--height',type=int,required=True);a=p.parse_args(argv)
    report=compare(a.candidate,a.reference,a.width,a.height,dict(zip(NAMES,(a.reference_rows_sha256,a.reference_runs_sha256))),a.out)
    emit(f"{report['status']}: {report['changed_cells']} changed cells of {report['cells_compared']}")
    if report['changed_cells'] and not a.allow_different:raise SystemExit(1)

if __name__=='__main__':main()

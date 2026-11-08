#!/usr/bin/env python3
"""Independently check every emitted basin cell against pinned raster and physical RLE.

This verifies raster-to-span completeness, not polygon validity or whether GDAL's
rasterization embodies an approved geographic rule.
"""
import argparse, gzip, hashlib, json
import time
from pathlib import Path
import numpy as np
from decision_snapshot import read_snapshot, find_basin, find_source, participant_water_codes


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def main(argv=None, *, emit=print, shared_inputs=None):
    processing_started=time.perf_counter()
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--manifest-sha256',required=True)
    ap.add_argument('--physical-rows',type=Path,required=True)
    ap.add_argument('--physical-runs',type=Path,required=True)
    ap.add_argument('--policy',type=Path,required=True)
    ap.add_argument('--policy-sha256',required=True)
    ap.add_argument('--allow-draft-snapshot',action='store_true')
    args=ap.parse_args(argv)
    if sha(args.manifest)!=args.manifest_sha256: raise ValueError('manifest hash mismatch')
    manifest=json.loads(args.manifest.read_text()); root=args.manifest.parent
    source=manifest['source']; grid=manifest['grid']; W,H=int(grid['width']),int(grid['height'])
    snapshot=read_snapshot(args.policy,args.policy_sha256,allow_draft=args.allow_draft_snapshot)
    basin=find_basin(snapshot,source['decision_id']);catalog=find_source(snapshot,basin)
    rev=snapshot['decision_revision']
    if (source.get('policy_sha256')!=args.policy_sha256 or source.get('decision_revision')!=rev['id']
        or source.get('entity_revision')!=rev['entity_revision'] or source.get('decision_status')!=rev['status']
        or source.get('assignment_method')!=basin.get('assignment_method')
        or source.get('source_id')!=basin.get('source_id') or source.get('source_version')!=basin.get('source_version')
        or str(source.get('source_feature_id'))!=str(basin.get('source_feature_id'))
        or source.get('canonical_geometry_sha256')!=basin.get('geometry_sha256')
        or source.get('source_file_sha256')!=catalog.get('sha256')):
        raise ValueError('manifest does not match pinned decision and source')
    if basin['assignment_method']=='shared_nearest_assigned_shore' and source.get('tie_rules')!=basin.get('tie_rules'):
        raise ValueError('manifest tie rules do not match decision')
    allowed=set(participant_water_codes(snapshot,basin))
    if shared_inputs is None:
        if sha(args.physical_rows)!=source['physical_rows_sha256'] or sha(args.physical_runs)!=source['physical_runs_sha256']:
            raise ValueError('physical hash mismatch')
        rows=np.memmap(args.physical_rows,dtype='<u4',mode='r');runs=np.memmap(args.physical_runs,dtype='<u4',mode='r')
    else:
        from verified_water_inputs import VerifiedWaterInputs
        if not isinstance(shared_inputs,VerifiedWaterInputs):raise TypeError('a verified shared water input context is required')
        rows,runs=shared_inputs.grid('physical',args.physical_rows,source['physical_rows_sha256'],
                                    args.physical_runs,source['physical_runs_sha256'],W,H)
    if len(rows)!=H+1 or len(runs)%2 or int(rows[0])!=0 or int(rows[-1])!=len(runs)//2 or np.any(rows[1:]<=rows[:-1]):
        raise ValueError('invalid physical row offsets')
    meta=manifest['rasterization']; x0,x1,y0,y1=map(int,meta['bounds_columns_rows'])
    if not (0<=x0<x1<=W and 0<=y0<y1<=H): raise ValueError('invalid raster bounds')
    raster_path=root/'source-mask.dat'
    if raster_path.stat().st_size != (x1-x0)*(y1-y0) or sha(raster_path)!=meta['source_mask_sha256']:raise ValueError('source raster size or hash mismatch')
    raster=np.memmap(raster_path,dtype='u1',mode='r',shape=(y1-y0,x1-x0))
    if len(manifest['tiles'])!=1:raise ValueError('expected single tile')
    tile=manifest['tiles'][0]
    if tile.get('core_rows')!=[0,H] or tile.get('core_cols')!=[0,W]:raise ValueError('unexpected tile coverage')
    path=(root/tile['span_file']['path']).resolve()
    if not path.is_relative_to(root.resolve()) or sha(path)!=tile['span_file']['sha256']:
        raise ValueError('assignment path or hash mismatch')
    cells=spans=0; previous=-1
    with gzip.open(path,'rt',encoding='utf8') as f:
        it=iter(f); first=next(it,None); rec=json.loads(first) if first else None
        for y in range(y0,y1):
            if rec is not None and (type(rec.get('row')) is not int or rec['row']<y):raise ValueError('unordered or out-of-bounds row')
            first,last=int(rows[y]),int(rows[y+1]);ends=runs[2*first:2*last:2];vals=runs[2*first+1:2*last:2]
            if not len(ends) or int(ends[0])<=0 or int(ends[-1])!=W or np.any(ends[1:]<=ends[:-1]) or np.any(~np.isin(vals,[1,17])):
                raise ValueError(f'invalid physical row {y}')
            x=np.arange(x0,x1,dtype=np.uint32)
            expected=(raster[y-y0]!=0)&(vals[np.searchsorted(ends,x,side='right')]==1)
            actual=np.zeros(x1-x0,dtype=bool)
            if rec is not None and rec['row']==y:
                end=x0
                for z in rec.get('spans',[]):
                    a,b,code=z.get('start'),z.get('end'),z.get('code')
                    if type(a) is not int or type(b) is not int or type(code) is not int or not (x0<=a<b<=x1) or a<end or code not in allowed:
                        raise ValueError(f'invalid span row {y}')
                    actual[a-x0:b-x0]=True;end=b;spans+=1
                line=next(it,None);rec=json.loads(line) if line else None
            if not np.array_equal(expected,actual):
                raise ValueError(f'coverage mismatch in row {y}: missing={np.count_nonzero(expected&~actual)} extra={np.count_nonzero(actual&~expected)}')
            cells+=int(expected.sum())
        if rec is not None:raise ValueError('assignment has rows outside raster bounds')
    if cells!=manifest['physical_water_cells'] or spans!=manifest['span_count']:raise ValueError('manifest counts do not match')
    emit(json.dumps({'processing_elapsed_seconds':time.perf_counter()-processing_started,'status':'raster-to-span-match','cells':cells,'spans':spans,'raster_sha256':sha(raster_path),
                      'assignment_sha256':sha(path),'limitation':'does not independently validate source polygon semantics'}))

if __name__=='__main__':main()

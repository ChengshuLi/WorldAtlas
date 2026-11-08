#!/usr/bin/env python3
"""Check every global coastal point against the ordinary RLE shore extractor.

This is kernel QA on the request's explicitly described land generation, not a
normal final-land admission or a whole-water processing-time measurement.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'v7-replay'))
import shared_nearest
from verified_water_inputs import VerifiedWaterInputs
import verified_water_inputs,coastal_shore_index,snapshot_input
from benchmark_stage import digest,environment
from exclusive_outputs import create_directory_exclusive,write_json_exclusive,validate_fresh_output


def point_fingerprint(points):
    count=0 if points is None else len(points['lat'])
    hashes={}
    for name,dtype,shape in [('lat','<f8',(count,)),('lon','<f8',(count,)),
                             ('mids','<f8',(count,3)),('category','<u4',(count,))]:
        array=np.empty(shape,dtype=dtype) if points is None else np.ascontiguousarray(points[name],dtype=dtype)
        if array.shape!=shape:raise ValueError('shore point array shape mismatch')
        hashes[name]=hashlib.sha256(memoryview(array).cast('B') if array.size else b'').hexdigest()
    return {'cells':count,'sha256':hashes}


def query_pass(query, width, height, step, rows_per_block):
    started_utc=datetime.now(timezone.utc).isoformat();started=time.perf_counter()
    records=[];query_seconds=0.
    for row in range(0,height,rows_per_block):
        end=min(height,row+rows_per_block);before=time.perf_counter()
        try:points=query((0,width,row,end))
        except ValueError as error:
            if str(error)!='no participant shorelines in crop':raise
            points=None
        query_seconds+=time.perf_counter()-before
        records.append({'row_start':row,'row_end_exclusive':end,**point_fingerprint(points)})
    return records,{'query_call_seconds':query_seconds,'pass_wall_seconds_including_fingerprints':time.perf_counter()-started,
                    'started_utc':started_utc,'completed_utc':datetime.now(timezone.utc).isoformat()}


def run(request_path,out,*,rows_per_block=256,candidate_first=False):
    request_path=Path(request_path).resolve(strict=True);request=json.loads(request_path.read_bytes())
    if request.get('schema')!='worldatlas-shore-index-global-qa-request-v1':raise ValueError('wrong shoreline QA request schema')
    if type(rows_per_block) is not int or rows_per_block<=0:raise ValueError('row block must be a positive integer')
    specifications={key:{**spec,'path':Path(spec['path']) if Path(spec['path']).is_absolute() else request_path.parent/spec['path']}
                    for key,spec in request['inputs'].items()}
    evidence=[{**pin,'path':Path(pin['path']) if Path(pin['path']).is_absolute() else request_path.parent/pin['path']}
              for pin in request.get('source_evidence',[])]
    if any('size_bytes' in spec and spec['path'].stat().st_size!=spec['size_bytes'] for spec in specifications.values()):
        raise ValueError('source byte count mismatch')
    if any(digest(pin['path'])!=pin['sha256'] for pin in evidence):raise ValueError('source evidence hash mismatch')
    out=validate_fresh_output(request_path.parent,out,(request_path,*[s['path'] for s in specifications.values()],*[s['path'] for s in evidence]))
    sources={'benchmark':Path(__file__),**{module.__name__:Path(module.__file__) for module in
              (verified_water_inputs,shared_nearest,coastal_shore_index,snapshot_input)}}
    invocation={'schema':'worldatlas-global-shore-index-qa-v1','request_sha256':digest(request_path),
                'request_scope':request.get('scope'),'input_sha256':{key:spec['sha256'] for key,spec in specifications.items()},
                'code_sha256':{key:digest(path) for key,path in sources.items()},'environment':environment(),
                'numpy':np.__version__,'point_encoding':{'coordinates':'little-endian-float64','category':'little-endian-uint32'},
                'candidate_first':bool(candidate_first),'rows_per_block':rows_per_block}
    create_directory_exclusive(out);scratch=out/'scratch';scratch.mkdir()
    write_json_exclusive(out/'invocation.json',invocation,indent=2)
    width,height=request['grid']['width'],request['grid']['height'];step=360./width
    started=time.perf_counter()
    with VerifiedWaterInputs(specifications,width,height,work_root=scratch) as inputs:
        preparation=time.perf_counter()-started;generation=inputs.provenance()
        def grid(role):
            args=[item for kind in ('rows','runs') for item in
                  (specifications[role+'_'+kind]['path'],specifications[role+'_'+kind]['sha256'])]
            return inputs.grid(role,*args,width,height)
        physical,land=grid('physical'),grid('land');codes=list(range(17,23))
        queries={'reference':lambda bounds:shared_nearest.centers_for_crop(physical,land,bounds,width,height,step,codes),
                 'indexed':lambda bounds:inputs.shore_index.centers_for_crop(bounds,step,codes)}
        names=['indexed','reference'] if candidate_first else ['reference','indexed']
        records={};timings={}
        for name in names:records[name],timings[name]=query_pass(queries[name],width,height,step,rows_per_block)
        expected_cells=int(np.sum(inputs.shore_index.ends.astype(np.uint64)-inputs.shore_index.starts))
        final_check_started=time.perf_counter()
    exit_verification=time.perf_counter()-final_check_started
    if (digest(request_path)!=invocation['request_sha256']
        or any(digest(path)!=invocation['code_sha256'][key] for key,path in sources.items())
        or any(digest(pin['path'])!=pin['sha256'] for pin in evidence)):
        raise ValueError('shoreline QA request, code or evidence changed')
    if records['reference']!=records['indexed']:raise ValueError('global coastal point bytes differ')
    cells=sum(block['cells'] for block in records['indexed'])
    if cells!=expected_cells:raise ValueError('global coastal cell accounting differs')
    result={**invocation,'status':'every-global-coastal-point-and-category-byte-identical',
            'grid':{'width':width,'height':height},'coastal_cells':cells,'blocks':records['indexed'],
            'generation':generation,'generation_preparation_seconds':preparation,'generation_exit_verification_seconds':exit_verification,
            'timings':timings,'limitations':['These query timings are not a whole-water or prefill speedup.',
                'Generation preparation includes snapshot copying and global index construction; exit includes original source rehashing.',
                'The request describes the supplied land generation; this does not create a normal Stage 3 admission or geographic acceptance.']}
    write_json_exclusive(out/'report.json',result,indent=2)
    return result


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--request',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--rows-per-block',type=int,default=256);ap.add_argument('--candidate-first',action='store_true')
    args=ap.parse_args();result=run(args.request,args.out,rows_per_block=args.rows_per_block,candidate_first=args.candidate_first)
    print(json.dumps({key:result[key] for key in ('status','coastal_cells','generation_preparation_seconds','generation_exit_verification_seconds','timings')}))

#!/usr/bin/env python3
"""Compare complete reference/batched shoreline constructors on pinned grids."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'v7-replay'))
from verified_water_inputs import VerifiedWaterInputs
from coastal_shore_index import CoastalShoreIndex
from coastal_shore_index_batch import BatchedCoastalShoreIndex
import verified_water_inputs,coastal_shore_index,coastal_shore_index_batch,snapshot_input,shared_nearest
from benchmark_stage import digest,environment
from exclusive_outputs import create_directory_exclusive,write_json_exclusive,validate_fresh_output


def run(request_path,out,*,rows_per_batch=256,candidate_first=False):
    request_path=Path(request_path).resolve(strict=True);request=json.loads(request_path.read_bytes())
    if request.get('schema')!='worldatlas-shore-index-global-qa-request-v1':raise ValueError('wrong shoreline request schema')
    if type(rows_per_batch) is not int or rows_per_batch<=0:raise ValueError('positive row batch required')
    specifications={name:{**spec,'path':Path(spec['path']) if Path(spec['path']).is_absolute() else request_path.parent/spec['path']}
                    for name,spec in request['inputs'].items()}
    evidence=[{**pin,'path':Path(pin['path']) if Path(pin['path']).is_absolute() else request_path.parent/pin['path']}
              for pin in request.get('source_evidence',[])]
    if any(digest(pin['path'])!=pin['sha256'] for pin in evidence):raise ValueError('source evidence hash mismatch')
    out=validate_fresh_output(request_path.parent,out,(request_path,*[s['path'] for s in specifications.values()],*[s['path'] for s in evidence]))
    replay=Path(__file__).resolve().parent.parent/'v7-replay'
    if Path(coastal_shore_index_batch.__file__).resolve()!=replay/'coastal_shore_index_batch.py':
        raise ImportError('batched index resolved outside the selected checkout')
    sources={'benchmark':Path(__file__),**{module.__name__:Path(module.__file__) for module in
              (verified_water_inputs,coastal_shore_index,coastal_shore_index_batch,snapshot_input,shared_nearest)}}
    invocation={'schema':'worldatlas-shore-index-constructor-pair-v1','request_sha256':digest(request_path),
                'scope':request.get('scope'),'input_sha256':{name:spec['sha256'] for name,spec in specifications.items()},
                'code_sha256':{name:digest(path) for name,path in sources.items()},'environment':environment(),
                'numpy':np.__version__,'candidate_first':bool(candidate_first),'rows_per_batch':rows_per_batch}
    create_directory_exclusive(out);scratch=out/'scratch';scratch.mkdir()
    write_json_exclusive(out/'invocation.json',invocation,indent=2)
    width,height=request['grid']['width'],request['grid']['height'];started=time.perf_counter()
    with VerifiedWaterInputs(specifications,width,height,work_root=scratch) as inputs:
        preparation=time.perf_counter()-started
        def grid(role):
            args=[item for kind in ('rows','runs') for item in (specifications[role+'_'+kind]['path'],specifications[role+'_'+kind]['sha256'])]
            return inputs.grid(role,*args,width,height)
        physical,land=grid('physical'),grid('land')
        factories={'reference':lambda:CoastalShoreIndex(physical,land,width,height),
                   'batched':lambda:BatchedCoastalShoreIndex(physical,land,width,height,rows_per_batch=rows_per_batch)}
        names=['batched','reference'] if candidate_first else ['reference','batched'];timings={};indexes={}
        for name in names:
            write_json_exclusive(out/(name+'-started.json'),{'event':'constructor-about-to-start',
                'name':name,'at_utc':datetime.now(timezone.utc).isoformat()},indent=2)
            utc=datetime.now(timezone.utc).isoformat();before=time.perf_counter();indexes[name]=factories[name]()
            timings[name]={'constructor_seconds':time.perf_counter()-before,'started_utc':utc,'completed_utc':datetime.now(timezone.utc).isoformat()}
            write_json_exclusive(out/(name+'-timing.json'),{'status':'processing-finished-parity-not-yet-verified',
                **timings[name]},indent=2)
        arrays={}
        for key in ('offsets','starts','ends','codes'):
            left,right=(getattr(indexes[name],key) for name in ('reference','batched'))
            if left.dtype!=right.dtype or not np.array_equal(left,right):raise ValueError('shore index buffer differs: '+key)
            arrays[key]={'dtype':left.dtype.str,'shape':list(left.shape),'sha256':hashlib.sha256(memoryview(left).cast('B') if left.size else b'').hexdigest()}
        index=indexes['reference'];cells=int(np.sum(index.ends.astype(np.uint64)-index.starts));spans=len(index.starts)
        exit_started=time.perf_counter()
    exit_time=time.perf_counter()-exit_started
    if (digest(request_path)!=invocation['request_sha256']
        or any(digest(path)!=invocation['code_sha256'][name] for name,path in sources.items())
        or any(digest(pin['path'])!=pin['sha256'] for pin in evidence)):
        raise ValueError('index benchmark request, source or evidence changed')
    result={**invocation,'status':'all-index-offset-start-end-category-bytes-identical','grid':{'width':width,'height':height},
            'coastal_cells':cells,'coastal_spans':spans,'arrays':arrays,'timings':timings,
            'generation_preparation_seconds':preparation,'generation_exit_verification_seconds':exit_time,
            'limitations':['Generation preparation (including the verified generation own index) is excluded from both constructor intervals.',
                           'One pair is not cache-order-balanced or a whole-stage speed estimate.',
                           'The candidate inherits the unchanged reference crop-query method; the request scope is not a final-land admission.']}
    write_json_exclusive(out/'report.json',result,indent=2)
    return result


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--request',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--rows-per-batch',type=int,default=256);ap.add_argument('--candidate-first',action='store_true');a=ap.parse_args()
    result=run(a.request,a.out,rows_per_batch=a.rows_per_batch,candidate_first=a.candidate_first)
    print(json.dumps({key:result[key] for key in ('status','coastal_cells','coastal_spans','timings')}))

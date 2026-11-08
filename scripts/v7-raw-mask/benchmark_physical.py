#!/usr/bin/env python3
"""Time complete land/composition Python APIs against a pinned checkout.

Entry points and their local helpers are loaded from each selected checkout in
turn, without interpreter startup or a subprocess fallback.
"""
import argparse
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import importlib.util
import inspect
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
from osgeo import gdal
from build import sha


def compare_masks(a,b):
    if sha(a)==sha(b):return 0
    a,b=gdal.Open(str(a)),gdal.Open(str(b))
    if (a.RasterXSize,a.RasterYSize,a.GetGeoTransform())!=(b.RasterXSize,b.RasterYSize,b.GetGeoTransform()):
        raise ValueError('benchmark grids differ')
    different=0
    for y in range(0,a.RasterYSize,512):
        n=min(512,a.RasterYSize-y)
        different+=int(np.count_nonzero(a.ReadAsArray(0,y,a.RasterXSize,n)!=b.ReadAsArray(0,y,b.RasterXSize,n)))
    return different


def invoke(code,script,config,target,log):
    """Isolate checkout-local imports and restore the caller's modules after use."""
    code=Path(code).resolve();builder=code/script
    paths={}
    for directory in (code,code.parent):
        for path in directory.glob('*.py'):paths.setdefault(path.stem,path.resolve())
    pins={local:sha(path) for local,path in paths.items()}
    saved={name:sys.modules[name] for name in paths if name in sys.modules}
    previous_path=sys.path[:];name='_worldatlas_physical_benchmark'
    if name in sys.modules:raise ImportError('physical benchmark is already active')
    try:
        for local in paths:sys.modules.pop(local,None)
        sys.path[:0]=[str(code),str(code.parent)]
        spec=importlib.util.spec_from_file_location(name,builder)
        module=importlib.util.module_from_spec(spec);sys.modules[name]=module
        with redirect_stdout(log),redirect_stderr(log):
            spec.loader.exec_module(module)
            api=getattr(module,'run' if script=='rasterize_land.py' else 'main',None)
            if api is None:raise TypeError('physical benchmark requires a Python stage API')
            options={'emit':lambda *values,**kwargs:print(*values,**{**kwargs,'file':log})} if 'emit' in inspect.signature(api).parameters else {}
            inspect.signature(api).bind(config,target,**options)
            loaded={local:pins[local] for local in paths if local in sys.modules}
            for local in loaded:
                if Path(getattr(sys.modules[local],'__file__','')).resolve()!=paths[local]:
                    raise ImportError('physical benchmark helper resolved outside selected checkout: '+local)
            result=api(config,target,**options)
            for local in paths:
                if local in sys.modules:
                    if Path(getattr(sys.modules[local],'__file__','')).resolve()!=paths[local]:
                        raise ImportError('physical benchmark helper resolved outside selected checkout: '+local)
                    loaded.setdefault(local,pins[local])
            if any(sha(paths[local])!=digest for local,digest in loaded.items()):
                raise ValueError('physical benchmark helper changed during execution')
            return result,loaded
    finally:
        sys.path[:]=previous_path;sys.modules.pop(name,None)
        for local in paths:sys.modules.pop(local,None)
        sys.modules.update(saved)


def run(stage,config,baseline,output,repeats,discard=False):
    if stage not in ('land','compose') or type(repeats) is not int or repeats<1:
        raise ValueError('valid stage and positive repeat count required')
    output=Path(output).resolve();output.mkdir();(output/'runtime').mkdir()
    current=Path(__file__).resolve().parent
    baseline=Path(baseline).resolve()/'scripts/v7-raw-mask'
    script={'land':'rasterize_land.py','compose':'compose_physical.py'}[stage]
    result={'stage':stage,'configuration_sha256':sha(config),
        'baseline_script_sha256':sha(baseline/script),'candidate_script_sha256':sha(current/script),
        'execution_mode':'in-process-python-api','actual_interpreter':sys.executable,
        'timing_scope':'module loading and complete stage API; excludes interpreter startup and post-run comparison',
        'results':[]}
    previous={key:os.environ.get(key) for key in ('TMPDIR','TMP','TEMP','CPL_TMPDIR','SQLITE_TMPDIR')}
    try:
        os.environ.update({key:str(output/'runtime') for key in previous})
        for repeat in range(repeats):
            order=('baseline','candidate') if repeat%2==0 else ('candidate','baseline');runs={}
            for name in order:
                target=output/f'{repeat:02d}-{name}';code=baseline if name=='baseline' else current
                started_utc=datetime.now(timezone.utc).isoformat();started=time.perf_counter()
                with (output/f'{repeat:02d}-{name}.log').open('x') as log:
                    _,helpers=invoke(code,script,Path(config).resolve(),target,log)
                elapsed=time.perf_counter()-started;ended_utc=datetime.now(timezone.utc).isoformat()
                if sha(code/script)!=result[name+'_script_sha256'] or sha(config)!=result['configuration_sha256']:
                    raise ValueError('physical benchmark entrypoint or configuration changed')
                report_path=target/'report.json';producer=json.loads(report_path.read_bytes())
                mask='land.tif' if stage=='land' else 'physical-dry.tif'
                declared=producer.get('land_sha256') if stage=='land' else producer.get('output_sha256',{}).get(mask)
                if (producer.get('status')!='candidate-only' or
                        producer.get('configuration_sha256')!=result['configuration_sha256'] or sha(target/mask)!=declared):
                    raise ValueError('physical benchmark producer report or mask mismatch')
                runs[name]={'output':str(target),'seconds':elapsed,'started_at_utc':started_utc,
                    'ended_at_utc':ended_utc,'helper_sha256':helpers,
                    'producer_report_sha256':sha(report_path)}
            a,b=(Path(runs[name]['output']) for name in ('baseline','candidate'))
            mask='land.tif' if stage=='land' else 'physical-dry.tif'
            different=compare_masks(a/mask,b/mask)
            hashes={name:{mask:sha(Path(run['output'])/mask)} for name,run in runs.items()}
            if stage=='compose':
                for name,run in runs.items():
                    for stream in ('rows.u32le','runs.u32le'):hashes[name][stream]=sha(Path(run['output'])/stream)
                if any(hashes['baseline'][key]!=hashes['candidate'][key] for key in ('rows.u32le','runs.u32le')):
                    raise ValueError('physical run streams differ')
            entry={'repeat':repeat,'runs':runs,'output_sha256':hashes,'different_pixels':different,
                'speedup':runs['baseline']['seconds']/runs['candidate']['seconds']}
            result['results'].append(entry)
            (output/'benchmark.json').write_text(json.dumps(result,indent=2)+'\n')
            if different:raise ValueError('physical masks differ')
            if discard:
                entry['discarded_matching_outputs']=[]
                for filename,digest in hashes['baseline'].items():
                    if hashes['candidate'][filename]!=digest:continue
                    for name in runs:
                        path=Path(runs[name]['output'])/filename
                        if path.is_symlink() or sha(path)!=digest:raise ValueError('benchmark output changed before cleanup')
                        receipt={'path':str(path.relative_to(output)),'sha256':digest,'bytes':path.stat().st_size}
                        path.unlink();entry['discarded_matching_outputs'].append(receipt)
                (output/'benchmark.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    finally:
        for key,value in previous.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('land','compose'));parser.add_argument('config')
    parser.add_argument('baseline_checkout');parser.add_argument('output')
    parser.add_argument('--repeats',type=int,default=1)
    parser.add_argument('--discard-matching-outputs',action='store_true',help='remove only new byte-identical benchmark grid copies after verification; retain reports')
    args=parser.parse_args()
    if args.repeats<1:parser.error('repeats must be positive')
    print(json.dumps(run(args.stage,args.config,args.baseline_checkout,args.output,args.repeats,args.discard_matching_outputs),indent=2))

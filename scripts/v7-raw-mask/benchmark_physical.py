#!/usr/bin/env python3
"""Time full land/composition inputs against a pinned baseline checkout."""
import argparse
import json
import os
from pathlib import Path
import subprocess
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


def run(stage,config,baseline,output,repeats,discard=False):
    output=Path(output).resolve();output.mkdir();(output/'runtime').mkdir()
    current=Path(__file__).resolve().parent
    baseline=Path(baseline).resolve()/'scripts/v7-raw-mask'
    script={'land':'rasterize_land.py','compose':'compose_physical.py'}[stage]
    result={'stage':stage,'configuration_sha256':sha(config),
        'baseline_script_sha256':sha(baseline/script),'candidate_script_sha256':sha(current/script),'results':[]}
    env={**os.environ,**{key:str(output/'runtime') for key in ('TMPDIR','TMP','TEMP','CPL_TMPDIR','SQLITE_TMPDIR')}}
    for repeat in range(repeats):
        order=('baseline','candidate') if repeat%2==0 else ('candidate','baseline')
        runs={}
        for name in order:
            target=output/f'{repeat:02d}-{name}'
            code=baseline if name=='baseline' else current
            started=time.perf_counter()
            with (output/f'{repeat:02d}-{name}.log').open('xb') as log:
                subprocess.run([sys.executable,str(code/script),str(Path(config).resolve()),str(target)],
                    stdout=log,stderr=subprocess.STDOUT,check=True,env=env)
            runs[name]={'output':str(target),'seconds':time.perf_counter()-started}
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


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('land','compose'));parser.add_argument('config')
    parser.add_argument('baseline_checkout');parser.add_argument('output')
    parser.add_argument('--repeats',type=int,default=1)
    parser.add_argument('--discard-matching-outputs',action='store_true',help='remove only new byte-identical benchmark grid copies after verification; retain reports')
    args=parser.parse_args()
    if args.repeats<1:parser.error('repeats must be positive')
    print(json.dumps(run(args.stage,args.config,args.baseline_checkout,args.output,args.repeats,args.discard_matching_outputs),indent=2))
